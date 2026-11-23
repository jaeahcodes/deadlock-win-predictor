import os
from datetime import datetime
from pathlib import Path
import duckdb
import requests


MAX_TARGET_MATCHES = 30000
SLICES = [(0, 15), (15, 23), (23, 25), (25, 27)]
TARGET_TABLES = ["match_salts", "match_player"]

script_dir = Path(__file__).resolve().parent.parent
base_dir = script_dir.parent.parent if script_dir.parent.name == "scripts" else script_dir.parent
data_dir = base_dir / "data"
db_path = str(data_dir / "deadlock.duckdb")
log_path = data_dir / "extraction_logs.txt"

raw_metadata_dir = data_dir / "raw_metadata_parquet"
timeseries_dir = data_dir / "timeseries_parquet"

raw_metadata_dir.mkdir(exist_ok = True, parents = True)
timeseries_dir.mkdir(exist_ok = True, parents = True)

def resolve_dirs(
        raw_dir: str | Path | None = None,
        timeseries_dir_override: str | Path | None = None
) -> tuple[Path, Path]:
    """Resolves and creates raw metadata and timeseries Parquet output directories."""

    raw_path = Path(raw_dir) if raw_dir else raw_metadata_dir
    ts_path = Path(timeseries_dir_override) if timeseries_dir_override else timeseries_dir
    raw_path.mkdir(exist_ok = True, parents = True)
    ts_path.mkdir(exist_ok = True, parents = True)
    return raw_path, ts_path

def log_message(message: str) -> None:
    """Prints to terminal and appends to extraction_logs.txt simultaneously."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] CT")
    formatted_msg = f"---{timestamp}---\n{message}"
    print(message)
    with open(log_path, "a", encoding = 'utf-8') as f:
        f.write(formatted_msg + "\n")

def connect_to_db(database_path: str = db_path, read_only: bool = False):
    """Connects to DuckDB (creates file only if writeable and missing)."""
    db_file = Path(database_path)
    if not db_file.is_file() and read_only:
        log_message(f"Error: Read-only database file does not exist at the specified path.")
        return None

    if not db_file.is_file():
        log_message(f"Error: Database file does not exist at the specified path. Creating a new one.")
        con = duckdb.connect(database_path, read_only = False)
    else:
        con = duckdb.connect(database_path, read_only = read_only)

    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET threads = 1;")
    con.execute("SET preserve_insertion_order = false;")
    con.execute("SET memory_limit = '2GB';")

    return con


def fetch_manifest() -> dict:
    """Fetches the latest Deadlock API Parquet manifest."""
    return requests.get("https://data.deadlock-api.com/v1/manifest.json", timeout = 30).json()

def get_file_slice(
        table: str,
        start_idx: int,
        end_idx: int,
        manifest: dict | None = None
) -> list[str]:
    """Pulls a non-overlapping slice of Parquet URLs for a manifest table."""
    m = manifest or fetch_manifest()
    base = m["public_url"]
    t = m["tables"][table]
    gen = t.get("generation, 0")
    file_list = [
        f"{base}/{f['key']}"
        for f in t["files"]
        if t["policy"] == "snapshot" or f.get("generation", 0) == gen
    ]
    return file_list[start_idx: end_idx]
