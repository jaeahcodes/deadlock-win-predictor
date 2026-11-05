import duckdb
import requests
import asyncio
import httpx
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
"""
This script executes in the following order:
(1) Creates a "data" folder if it doesn't already exist, and initializes a .duckdb file. Initializes an extraction log .txt file.
(2) Connects to DuckDB.
(3) Executes fetch manifest. Creates view table if it doesn't already exist, and populates it with the retrieved data.
"""

# 1. Initialize paths and logging
script_dir = Path(__file__).resolve().parent
base_dir = script_dir.parent.parent if script_dir.parent.name == "data_extraction" else script_dir.parent
data_dir = base_dir / "data"

db_path = str(data_dir / "deadlock.duckdb")
log_path = data_dir / "extraction_logs.txt"

def log_message(message: str):
    """Prints to terminal and appends to extraction_logs.txt simultaneously."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] CT")
    formatted_msg = f"---{timestamp}---\n{message}"
    print(message)

    with open(log_path, "a", encoding = "utf-8") as f:
        f.write(formatted_msg + "\n")

log_message(f"Starting Match Player Salts Data Extraction Run")

# 2. Connect  to DuckDB
con = duckdb.connect(db_path)
con.execute("SET threads = 1;")
con.execute("SET memory_limit = '8GB';")
con.execute("SET preserve_insertion_order = false;")

# 3. Fetch manifest
manifest = requests.get("https://data.deadlock-api.com/v1/manifest.json").json()
base = manifest["public_url"]

def get_file_slice(table: str, start_idx: int, end_idx: int) -> list[str]:
    """Helper to pull a specific non-overlapping slice of parquet files."""
    t = manifest["tables"][table]
    gen = t.get("generation", 0)
    file_list = [f"{base}/{f['key']}" for f in t["files"]
                 if t["policy"] == "snapshot" or f.get("generation", 0) == gen]
    return file_list[start_idx : end_idx]

SLICES = [(0, 15), (15, 23)]
TARGET_TABLES = ["match_salts", "match_player"]

def extract_match_player_salts_data(idx_slice: tuple, target_tables = TARGET_TABLES):
    start_no, end_no = idx_slice

    for name in target_tables:
        if name in manifest["tables"]: 
            file_urls = get_file_slice(name, start_no, end_no)
            if not file_urls:
                log_message(f"No more files available for {name} at index {start_no}. Skipping this table.")
                continue

            log_message(f"Creating view for {name} using files {start_no} to {end_no}...")
            con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet({file_urls!r}, union_by_name = true)")

    log_message("Phase 1: Extracting and inserting player features into persistent table")
    con.execute("""
        CREATE TABLE IF NOT EXISTS player_features AS 
        SELECT 
            m.match_id,
            mp.account_id,
            mp.hero_id,
            mp.team,
            mp.won,
            mp.net_worth,
            mp."stats.net_worth",
            mp."stats.gold_lane_creep",
            mp."stats.gold_neutral_creep",
            mp."stats.gold_player",
            mp.kills,
            mp.deaths,
            mp.assists,
            mp."stats.player_damage",
            mp."stats.player_damage_taken",
            mp."stats.ability_kills",
            mp."stats.headshot_kills",
            mp."stats.melee_kills",
            mp."stats.boss_damage",
            mp."stats.creep_damage",
            mp."stats.creep_kills",
            mp."items.item_id",
            mp."items.game_time_s",
            mp."items.sold_time_s",
            CASE WHEN mp.team = mp.winning_team THEN 1 ELSE 0 END AS label
        FROM match_salts m
        JOIN match_player mp ON m.match_id = mp.match_id
    """)

    con.execute("""
        INSERT INTO player_features
        SELECT 
            m.match_id,
            mp.account_id,
            mp.hero_id,
            mp.team,
            mp.won,
            mp.net_worth,
            mp."stats.net_worth",
            mp."stats.gold_lane_creep",
            mp."stats.gold_neutral_creep",
            mp."stats.gold_player",
            mp.kills,
            mp.deaths,
            mp.assists,
            mp."stats.player_damage",
            mp."stats.player_damage_taken",
            mp."stats.ability_kills",
            mp."stats.headshot_kills",
            mp."stats.melee_kills",
            mp."stats.boss_damage",
            mp."stats.creep_damage",
            mp."stats.creep_kills",
            mp."items.item_id",
            mp."items.game_time_s",
            mp."items.sold_time_s",
            CASE WHEN mp.team = mp.winning_team THEN 1 ELSE 0 END AS label
        FROM match_salts m
        JOIN match_player mp ON m.match_id = mp.match_id
        WHERE m.match_id NOT IN (SELECT DISTINCT match_id FROM player_features);
    """)

    log_message("Phase 2: Running inspection queries")
    stats_query = """
        SELECT
            COUNT(DISTINCT match_id) AS total_unique_matches,
            COUNT(*) AS total_player_rows,
            COUNT(*) / NULLIF(COUNT(DISTINCT match_id), 0) AS avg_players_per_match
        FROM player_features
    """
    stats_df = con.sql(stats_query).df()
    log_message(str(stats_df))

    log_message("Phase 3: Keeping only matches with 12 player data")
    full_match_query = """
        CREATE OR REPLACE TABLE player_features AS
        SELECT pf.*
        FROM player_features pf
        JOIN (
            SELECT match_id
            FROM player_features
            GROUP BY match_id
            HAVING COUNT(*) = 12
        ) complete_matches ON pf.match_id = complete_matches.match_id
    """
    con.execute(full_match_query)

    log_message("Phase 4: Re-running inspection queries")
    final_stats_df = con.sql(stats_query)
    log_message(str(final_stats_df))

    log_message("Extraction Run Finished Successfully")

match_id_query = """
    SELECT DISTINCT match_id
    FROM player_features
"""
MATCH_ID_LIST = [r[0] for r in con.execute(match_id_query).fetchall()]

async def fetch_metadata_async(batch_size: int = 5000):
    try:
        fetched_ids = set(r[0] for r in con.execute("SELECT DISTINCT match_id FROM match_metadata").fetchall())
    except Exception:
        fetched_ids = set()

    pending_match_ids = [mid for mid in MATCH_ID_LIST if mid not in fetched_ids]

    log_message(f"Total matches: {len(MATCH_ID_LIST)} | Already fetched: {len(fetched_ids)}")

    if not pending_match_ids:
        log_message("Metadata is fully up to date.")
        return

    chunks = [pending_match_ids[i : i + batch_size] for i in range(0, len(pending_match_ids), batch_size)]
    log_message(f"Split {len(pending_match_ids)} pending matches into {len(chunks)} batches of up to {batch_size}")
    semaphore = asyncio.Semaphore(15)

    async def fetch_one(client, mid):
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
        for chunk_idx, chunk in enumerate(chunks, 1):
            log_message(f"Processing batch {chunk_idx}/{len(chunks)} ({len(chunk)} matches)...")
            tasks = [fetch_one(client, mid) for mid in chunk]
            results = await asyncio.gather(*tasks)

            valid = [r for r in results if r is not None]
            if valid:
                df = pd.DataFrame(valid)
                con.append("match_metadata", df)
                log_message(f"Batch {chunk_idx} committed: Successfully inserted {len(valid)} records.")
            else: 
                log_message(f"Batch {chunk_idx} warning: No valid metadata returned for this chunk.")
            await asyncio.sleep(1.0)

    log_message("Metadata Ingestion Complete.")

def main_menu():
    while True:
        print("\n=================================")
        print("    DEADLOCK PIPELINE MANAGER    ")
        print("=================================")
        print("1. Extract Match Player & Salts Data (Parquet)")
        print("2. Extract Match Metadata (Async API)")
        print("3. Exit")
        choice = input("\nEnter your choice (1-3): ").strip()

        if choice == '1': 
            extract_match_player_salts_data_wrapper = getattr(sys.modules[__name__], 'extract_match_player_salts_data')
            extract_match_player_salts_data_wrapper()
        elif choice == '2':
            asyncio.run(fetch_metadata_async())
        elif choice == '3':
            print("Exiting pipeline.")
            break
        else: 
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main_menu()