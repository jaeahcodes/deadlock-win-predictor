import asyncio
import httpx
import duckdb
import os
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

"""
Deadlock Data Pipeline & Extraction Manager

This script serves as the centralized ingestion pipeline for ingesting, processing, and persisting Deadlock match telemetry, player statistics, and deep API JSON metadata into a local DuckDB database (deadlock.duckdb), with native AWS S3 Data Lake integration.

Usage:
    Run the script from the terminal to launch the interactive pipeline manager menu.
    $ python extract_data.py

"""

# 1. Initialize environment variables
load_dotenv()

# 2. Initialize paths and logging
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

# 3. Connect to DuckDB
con = duckdb.connect(db_path)
con.execute("INSTALL httpfs; LOAD httpfs;")

aws_region = os.getenv('AWS_REGION', 'us-east-1')
access_key = os.getenv('AWS_ACCESS_KEY_ID')
secret_key = os.getenv('AWS_SECRET_ACCESS_Key')

con.execute(f"SET s3_region = '{aws_region}';")
con.execute(f"SET s3_access_key_id = '{access_key}';")
con.execute(f"SET s3_secret_access_key = '{secret_key}';")

log_message("DuckDB successfully configured with S3 credentials.")

print(con.sql("SELECT * FROM glob('s3://deadlock-datalake-bucket-857745822625-us-east-2-an/');").df())

# 4. Fetch manifest
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
    log_message(f"Starting Match Player Salts Data Extraction Run")
    start_no, end_no = idx_slice

    for name in target_tables:
        if name in manifest["tables"]: 
            file_urls = get_file_slice(name, start_no, end_no)
            if not file_urls:
                log_message(f"No more files available for {name} at index {start_no}. Skipping this table.")
                continue

            log_message(f"Creating table for {name} using files {start_no} to {end_no}...")
            con.execute(f"CREATE OR REPLACE {name} AS SELECT * FROM read_parquet({file_urls!r}, union_by_name = true)")

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
    table_exists = con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'match_metadata'").fetchone()[0] > 0
    
    if table_exists:
        try:
            fetched_ids = set(r[0] for r in con.execute("SELECT DISTINCT m.match_info.match_id FROM match_metadata m").fetchall())
        except Exception:
            fetched_ids = set()
    else:
        fetched_ids = set()

    pending_match_ids = [mid for mid in MATCH_ID_LIST if mid not in fetched_ids]
    log_message(f"Total matches: {len(MATCH_ID_LIST)} | Already fetched: {len(fetched_ids)}")

    if not pending_match_ids:
        log_message("Metadata is fully up to date.")
        return

    chunks = [pending_match_ids[i : i + batch_size] for i in range(0, len(pending_match_ids), batch_size)]
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
        with tqdm(chunks, desc = "Overall Batches", unit = "batch") as batch_bar:
            for chunk_idx, chunk in enumerate(batch_bar, 1):
                tasks = [fetch_one(client, mid) for mid in chunk]
                results = await tqdm_asyncio.gather(*tasks, desc = f"Batch {chunk_idx} Requests", leave = False)

                valid = [r for r in results if r is not None]
                if valid:
                    df = pd.DataFrame(valid)
                    con.register('temp_df', df)
                    if not con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'match_metadata'").fetchone()[0] > 0:
                        con.execute("CREATE TABLE match_metadata AS SELECT * FROM temp_df;")
                    else:
                        con.execute("INSERT INTO match_metadata SELECT * FROM temp_df;")
                    con.unregister('temp_df')
                    batch_bar.set_postfix(inserted = len(valid))
                    log_message(f"Batch {chunk_idx} committed: Successfully inserted {len(valid)} records.")
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
            extract_match_player_salts_data()
        elif choice == '2':
            asyncio.run(fetch_metadata_async())
        elif choice == '3':
            print("Exiting pipeline.")
            break
        else: 
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()