import os
import time
import requests
import polars as pl
from datetime import datetime, timedelta, timezone

SQL_URL = "https://api.deadlock-api.com/v1/sql"

# i don't get a whole week I need to change this name eventually
OUTPUT_FILE = "/Users/taha/Desktop/Capstone/deadlock_ranked_20m_last_week.parquet"

def fetch_chunk_matches(start_dt: datetime, end_dt: datetime) -> pl.DataFrame:
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    query = f"""
    SELECT
        match_id,
        any_value(start_time) AS start_time,
        any_value(duration_s) AS duration_s,
        any_value(winning_team) = 'Team0' AS team0_won,
        any_value(average_badge_team0) AS badge_team0,
        any_value(average_badge_team1) AS badge_team1,
        SUM(souls_20m) FILTER (WHERE team = 'Team0') AS team0_souls_20m,
        SUM(souls_20m) FILTER (WHERE team = 'Team1') AS team1_souls_20m,
        SUM(kills_20m) FILTER (WHERE team = 'Team0') AS team0_kills_20m,
        SUM(kills_20m) FILTER (WHERE team = 'Team1') AS team1_kills_20m,
        SUM(deaths_20m) FILTER (WHERE team = 'Team0') AS team0_deaths_20m,
        SUM(deaths_20m) FILTER (WHERE team = 'Team1') AS team1_deaths_20m,
        SUM(assists_20m) FILTER (WHERE team = 'Team0') AS team0_assists_20m,
        SUM(assists_20m) FILTER (WHERE team = 'Team1') AS team1_assists_20m,
        SUM(creeps_20m) FILTER (WHERE team = 'Team0') AS team0_creeps_20m,
        SUM(creeps_20m) FILTER (WHERE team = 'Team1') AS team1_creeps_20m,
        SUM(denies_20m) FILTER (WHERE team = 'Team0') AS team0_denies_20m,
        SUM(denies_20m) FILTER (WHERE team = 'Team1') AS team1_denies_20m,
        SUM(damage_20m) FILTER (WHERE team = 'Team0') AS team0_damage_20m,
        SUM(damage_20m) FILTER (WHERE team = 'Team1') AS team1_damage_20m,
        SUM(level_20m) FILTER (WHERE team = 'Team0') AS team0_level_20m,
        SUM(level_20m) FILTER (WHERE team = 'Team1') AS team1_level_20m,
        list(hero_id) FILTER (WHERE team = 'Team0') AS team0_heroes,
        list(hero_id) FILTER (WHERE team = 'Team1') AS team1_heroes,
        any_value("objectives.destroyed_time_s") AS obj_times_s,
        any_value("objectives.team") AS obj_teams
    FROM (
        SELECT
            match_id,
            start_time,
            duration_s,
            winning_team,
            average_badge_team0,
            average_badge_team1,
            team,
            hero_id,
            "objectives.destroyed_time_s",
            "objectives.team",
            "stats.net_worth"[idx] AS souls_20m,
            "stats.kills"[idx] AS kills_20m,
            "stats.deaths"[idx] AS deaths_20m,
            "stats.assists"[idx] AS assists_20m,
            "stats.creep_kills"[idx] AS creeps_20m,
            "stats.denies"[idx] AS denies_20m,
            "stats.player_damage"[idx] AS damage_20m,
            "stats.level"[idx] AS level_20m
        FROM (
            SELECT
                match_id,
                start_time,
                duration_s,
                winning_team,
                average_badge_team0,
                average_badge_team1,
                team,
                hero_id,
                "objectives.destroyed_time_s",
                "objectives.team",
                "stats.net_worth",
                "stats.kills",
                "stats.deaths",
                "stats.assists",
                "stats.creep_kills",
                "stats.denies",
                "stats.player_damage",
                "stats.level",
                len(list_filter("stats.time_stamp_s", lambda t: t <= 1200)) AS idx
            FROM match_player
            WHERE match_mode = 'Ranked'
              AND game_mode = 'Normal'
              AND match_outcome = 'TeamWin'
              AND duration_s >= 1200
              AND start_time >= TIMESTAMPTZ '{start_str}'
              AND start_time < TIMESTAMPTZ '{end_str}'
        )
        WHERE idx > 0
    )
    GROUP BY match_id
    HAVING count(*) = 12
    """.strip()

    attempt = 0
    while True:
        resp = requests.get(SQL_URL, params={"query": query}, timeout=120)
        if resp.status_code in (429, 503):
            attempt += 1
            retry_header = resp.headers.get("Retry-After")
            wait = int(float(retry_header)) if retry_header else min(15 * attempt, 60)
            print(f"  Rate limited ({resp.status_code}), sleeping {wait}s before retry...")
            time.sleep(wait)
            continue
        if resp.status_code in (400, 504):
            raise RuntimeError(f"HTTP {resp.status_code}:\n{resp.text}")
        resp.raise_for_status()
        payload = resp.json()
        rows = payload if isinstance(payload, list) else payload.get("data", [])
        
        # count obj at 20mins
        if rows:
            for row in rows:
                times = row.pop("obj_times_s", []) or []
                teams = row.pop("obj_teams", []) or []
                row["team0_objectives_taken_20m"] = sum(
                    1 for t, tm in zip(times, teams) if 0 < t <= 1200 and tm == "Team1"
                )
                row["team1_objectives_taken_20m"] = sum(
                    1 for t, tm in zip(times, teams) if 0 < t <= 1200 and tm == "Team0"
                )

        return pl.DataFrame(rows)

# rate limit means save what you can while you can
frames = []
if os.path.exists(OUTPUT_FILE):
    existing_df = pl.read_parquet(OUTPUT_FILE)
    frames.append(existing_df)
    print(f"Loaded {len(existing_df)} existing matches from {OUTPUT_FILE}")

now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
chunk_hours = 12
total_chunks = (2 * 24) // chunk_hours

for i in range(total_chunks, 0, -1):
    chunk_start = now - timedelta(hours=i * chunk_hours)
    chunk_end = chunk_start + timedelta(hours=chunk_hours)
    print(f"Fetching {chunk_start.strftime('%Y-%m-%d %H:%M')} to {chunk_end.strftime('%Y-%m-%d %H:%M')}...")
    
    df_chunk = fetch_chunk_matches(chunk_start, chunk_end)
    print(f"  -> Retrieved {len(df_chunk)} matches")
    frames.append(df_chunk)

    # Concat and drop dupes
    combined = pl.concat(frames).unique(subset=["match_id"])
    combined.write_parquet(OUTPUT_FILE)
    print(f"  -> Saved checkpoint ({len(combined)} total matches so far)")
    
    time.sleep(15)

print(f"Finished! All chunks saved to {OUTPUT_FILE}.")