import argparse
import asyncio
import httpx
import pandas as pd
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

from common import (
    MAX_TARGET_MATCHES,
    get_file_slice,
    log_message,
    resolve_dirs,
    connect_to_db
)

def _sanitize_for_parquet(obj):
    """Replaces empty dicts with None so PyArrow does not infer zero-field structs."""
    if isinstance(obj, dict):
        cleaned = {k: _sanitize_for_parquet(v) for k, v in obj.items()}
        return cleaned if len(cleaned) > 0 else None
    if isinstance(obj, list):
        return[_sanitize_for_parquet(item) for item in obj]

async def fetch_metadata_async(
    max_matches: int = MAX_TARGET_MATCHES,
    batch_size: int = 200,
    slice_start: int = 0,
    slice_end: int = 30,
    raw_dir: str | None = None
) -> None:
    """Asynchronously fetch match metadata and stage each batch as a ZSTD Parquet file."""
    raw_path, _ = resolve_dirs(raw_dir = raw_dir)
    log_message(f"Fetching match IDs from manifest...")

    con = connect_to_db(read_only = False)

    file_urls = get_file_slice("match_salts", slice_start, slice_end)
    match_id_list = []
    if file_urls:
        con.execute(
            f"CREATE OR REPLACE TEMP TABLE manifest_match_ids AS SELECT DISTINCT match_id FROM read_parquet({file_urls!r})"
        )
        match_id_list = [
            r[0] for r in con.execute(f"SELECT match_id FROM manifest_match_ids").fetchall()
        ]
        con.complete()
    else:
        log_message("Warning: No manifest file URLs returned for match_salts.")

    existing_parts = sorted(raw_path.glob("metadata_part_*.parquet"))
    fetched_ids = set()
    if existing_parts:
        raw_glob = str(raw_path / "*.parquet")
        try:
            fetched_ids = set(
                r[0] for r in con.execute(
                    f"SELECT DISTINCT match_info.match_id FROM read_parquet('{raw_glob}', union_by_name = true)"
                ).fetchall()
            )
            con.complete()
        except Exception as e:
            log_message(f"Warning reading exiting raw metadata files: {e}")
    con.close()

    pending_match_ids = [mid for mid in match_id_list if mid not in fetched_ids]
    log_message(
        f"Metadata Target: {max_matches:,} | Already Fetched: {len(fetched_ids):,} | "
        f"Pending: {len(pending_match_ids):,}"
    )

    if len(fetched_ids) >= max_matches or not pending_match_ids:
        log_message("Metadata extraction up to date; nothing new to fetch.")
        return

    next_part_idx = len(existing_parts)
    chunks = [pending_match_ids[i : i + batch_size] for i in range(0, len(pending_match_ids), batch_size)]
    semaphore = asyncio.Semaphore(15)

    async def fetch_one(client: httpx.AsyncClient, mid: int):
        url = f"https://api.deadlock-api.com/v1/matches/{mid}/metadata"
        async with semaphore:
            try:
                res = await client.get(url, timeout = 15.0)
                if res.status_code == 200:
                    return res.json()
            except Exception:
                pass
            return None

    async with httpx.AsyncClient() as client:
        with tqdm(chunks, desc = "Metadata Batches", unit = "batch", leave = False) as batch_bar:
            for chunk_idx, chunk in enumerate(batch_bar, 1):
                tasks = [fetch_one(client, mid) for mid in chunk]
                results = await tqdm_asyncio.gather(*tasks, desc = f"Batch {chunk_idx}", leave = False)

                valid = [_sanitize_for_parquet(r) for r in results if r is not None]
                if valid:
                    out_file = raw_path / f"metadata_part_{next_part_idx:04d}.parquet"
                    pd.DataFrame(valid).to_parquet(out_file, compression = 'zstd', index = False)
                    next_part_idx += 1
                    batch_bar.set_postfix(saved = len(valid))
                await asyncio.sleep(1.0)
    
    log_message("Metadata Parquet Staging Complete.")

def parse_args():
    parser = argparse.ArgumentParser(description = "Stage Deadlock match metadata to ZSTD Parquet.")
    parser.add_argument("--max-matches", type = int, default = MAX_TARGET_MATCHES)
    parser.add_argument("--batch-size", type = int, default = 1000)
    parser.add_argument("--slice-start", type = int, default = 0)
    parser.add_argument("--slice-end", type = int, default = 30)
    parser.add_argument("--raw-dir", type = str, default = None)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        fetch_metadata_async(
            max_matches = args.max_matches,
            batch_size = args.batch_size,
            slice_start = args.slice_start,
            slice_end = args.slice_end,
            raw_dir = args.raw_dir
        )
    )