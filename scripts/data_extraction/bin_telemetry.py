import argparse
import os
from tqdm import tqdm

from common import connect_to_db, log_message, resolve_dirs

def clean_and_bin_metadata(
    batch_size: int = 100,
    bin_seconds: int = 180, 
    raw_dir: str | None = None,
    timeseries_dir_override: str | None = None
) -> None:
    """Reads staged raw metadata Parquet files, bins timestamps, and exports ZSTD Parquet file parts."""
    raw_path, ts_path = resolve_dirs(
        raw_dir = raw_dir,
        timeseries_dir_override = timeseries_dir_override
    )

    raw_parts = sorted(raw_path.glob("metadata_part_*.parquet"))
    if not raw_parts:
        log_message(f"No raw metadata Parquet files found in the specified path to clean and bin.")
        return

    con = connect_to_db(read_only = True)
    if con is None:
        return

    raw_glob = str(raw_path / "*.parquet")
    log_message(f"Starting {bin_seconds}s Telemetery Binning...")

    total_rows = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{raw_glob}', union_by_name = true)"
    ).fetchone()[0]
    con.complete()
    log_message(f"Total staged metadata rows to process: {total_rows:,}")

    offsets = list(range(0, total_rows, batch_size))
    with tqdm(offsets, desc = f"Binning ({bin_seconds}s)", unit = "batch") as pbar:
        for offset in pbar:
            batch_num = offset // batch_size
            out_file = os.path.join(ts_path, f"tick_stats_part_{batch_num:04d}.parquet")

            if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                pbar.set_postfix(status = f"Skipped part_{batch_num:04d}")
                continue

            query = f"""
                COPY (
                    WITH match_batch AS (
                        SELECT match_info
                        FROM read_parquet('{raw_glob}', union_by_name = true)
                        LIMIT {batch_size} OFFSET {offset}
                    ),
                    raw_ticks AS (
                        SELECT
                            m.match_info.match_id AS match_id,
                            m.match_info.start_time AS match_start_time,
                            m.match_info.game_mode AS game_mode,
                            m.match_info.match_mode AS match_mode,
                            m.match_info.match_outcome AS match_outcome,
                            m.match_info.winning_team AS winning_team,
                            p.team AS team,
                            p.account_id AS player_account_id,
                            p.player_slot AS player_slot,
                            p.kills AS total_kills,
                            p.deaths AS total_deaths,
                            p.assists AS total_assists,
                            p.net_worth AS total_net_worth,
                            p.hero_id AS hero_id,
                            p.last_hits AS total_last_hits,
                            p.denies AS total_denies,
                            p.ability_points AS total_ability_points,
                            p.assigned_lane AS assigned_lane,
                            p."level" AS player_level_at_end,
                            p.abandon_match_time_s AS abandon_match_time_s,
                            CAST(ROUND(s.time_stamp_s / {float(bin_seconds)}) * {bin_seconds} AS INTEGER) AS stat_time_stamp_s,
                            s.net_worth AS player_net_worth,
                            s.gold_player AS gold_player,
                            s.gold_lane_creep AS gold_lane_creep,
                            s.gold_neutral_creep AS gold_neutral_creep,
                            s.gold_player_orbs AS gold_player_orbs,
                            s.gold_lane_creep_orbs AS gold_lane_creep_orbs,
                            s.gold_neutral_creep_orbs AS gold_neutral_creep_orbs,
                            s.gold_boss AS gold_boss,
                            s.gold_boss_orb AS gold_boss_orb,
                            s.gold_treasure AS gold_treasure,
                            s.gold_denied AS gold_denied,
                            s.gold_death_loss AS gold_death_loss,
                            s.kills AS player_kills,
                            s.deaths AS player_deaths,
                            s.assists AS player_assists,
                            s.creep_kills AS creep_kills,
                            s.neutral_kills AS neutral_kills,
                            s.creep_damage AS creep_damage,
                            s.player_damage AS player_damage,
                            s.neutral_damage AS neutral_damage,
                            s.boss_damage AS boss_damage,
                            s.denies AS player_denies,
                            s.player_healing AS player_healing,
                            s.self_healing AS self_healing,
                            s.player_damage_taken AS player_damage_taken,
                            s.max_health AS player_max_health,
                            s.weapon_power AS weapon_power,
                            s.tech_power AS tech_power,
                            s.shots_hit AS shots_hit,
                            s.shots_missed AS shots_missed,
                            s.hero_bullets_hit AS hero_bullets_hit,
                            s.hero_bullets_hit_crit AS hero_bullets_hit_crit,
                            s.damage_mitigated AS damage_mitigated,
                            s."level" AS player_level,
                            s.player_barriering AS player_barriering,
                            s.teammate_healing AS teammate_healing,
                            s.bullet_kills AS bullet_kills,
                            s.melee_kills AS melee_kills,
                            s.ability_kills AS ability_kills,
                            s.headshot_kills AS headshot_kills,
                            g."source" AS gold_source,
                            g.kills AS gold_source_kills,
                            g.damage AS gold_source_damage,
                            g.gold AS gold_source_amount,
                            g.gold_orbs AS gold_source_orbs
                        FROM match_batch AS m
                        CROSS JOIN UNNEST(m.match_info.players) AS t1(p)
                        CROSS JOIN UNNEST(p.stats) AS t2(s)
                        LEFT JOIN UNNEST(s.gold_sources) t3(g) ON TRUE
                        WHERE m.match_info IS NOT NULL
                        AND p.stats IS NOT NULL
                    )
                    SELECT
                        match_id,
                        team,
                        hero_id,
                        stat_time_stamp_s,
                        gold_source,
                        game_mode,
                        match_mode,
                        winning_team,
                        player_account_id,
                        player_slot,
                        MAX(match_outcome) AS match_outcome,
                        MAX(total_kills) AS total_kills,
                        MAX(total_deaths) AS total_deaths,
                        MAX(total_assists) AS total_assists,
                        MAX(total_net_worth) AS total_net_worth,
                        MAX(total_last_hits) AS total_last_hits,
                        MAX(total_denies) AS total_denies,
                        MAX(total_ability_points) AS total_ability_points,
                        MAX(assigned_lane) AS assigned_lane,
                        MAX(player_level_at_end) AS player_level_at_end,
                        MAX(abandon_match_time_s) AS abandon_match_time_s,
                        MAX(player_net_worth) AS player_net_worth,
                        MAX(gold_player) AS gold_player,
                        MAX(gold_lane_creep) AS gold_lane_creep,
                        MAX(gold_neutral_creep) AS gold_neutral_creep,
                        MAX(gold_player_orbs) AS gold_player_orbs,
                        MAX(gold_lane_creep_orbs) AS gold_lane_creep_orbs,
                        MAX(gold_neutral_creep_orbs) AS gold_neutral_creep_orbs,
                        MAX(gold_boss) AS gold_boss,
                        MAX(gold_boss_orb) AS gold_boss_orb,
                        MAX(gold_treasure) AS gold_treasure,
                        MAX(gold_denied) AS gold_denied,
                        MAX(gold_death_loss) AS gold_death_loss,
                        MAX(player_kills) AS player_kills,
                        MAX(player_deaths) AS player_deaths,
                        MAX(player_assists) AS player_assists,
                        MAX(creep_kills) AS creep_kills,
                        MAX(neutral_kills) AS neutral_kills,
                        MAX(creep_damage) AS creep_damage,
                        MAX(player_damage) AS player_damage,
                        MAX(neutral_damage) AS neutral_damage,
                        MAX(boss_damage) AS boss_damage,
                        MAX(player_denies) AS player_denies,
                        MAX(player_healing) AS player_healing,
                        MAX(self_healing) AS self_healing,
                        MAX(player_damage_taken) AS player_damage_taken,
                        MAX(player_max_health) AS player_max_health,
                        MAX(weapon_power) AS weapon_power,
                        MAX(tech_power) AS tech_power,
                        MAX(shots_hit) AS shots_hit,
                        MAX(shots_missed) AS shots_missed,
                        MAX(hero_bullets_hit) AS hero_bullets_hit,
                        MAX(hero_bullets_hit_crit) AS hero_bullets_hit_crit,
                        MAX(damage_mitigated) AS damage_mitigated,
                        MAX(player_level) AS player_level,
                        MAX(player_barriering) AS player_barriering,
                        MAX(teammate_healing) AS teammate_healing,
                        MAX(bullet_kills) AS bullet_kills,
                        MAX(melee_kills) AS melee_kills,
                        MAX(ability_kills) AS ability_kills,
                        MAX(headshot_kills) AS headshot_kills,
                        SUM(gold_source_amount) AS gold_source_amount,
                        SUM(gold_source_orbs) AS gold_source_orbs,
                        MAX(gold_source_kills) AS gold_source_kills,
                        MAX(gold_source_damage) AS gold_source_damage
                    FROM raw_ticks
                    GROUP BY
                        match_id,
                        team,
                        hero_id,
                        stat_time_stamp_s,
                        gold_source,
                        game_mode,
                        match_mode,
                        winning_team,
                        player_account_id,
                        player_slot
                    ORDER BY match_id, team, hero_id, stat_time_stamp_s
                ) TO '{out_file}' (
                    FORMAT PARQUET,
                    COMPRESSION ZSTD,
                    COMPRESSION_LEVEL 6,
                    ROW_GROUP_SIZE 100000
                );
                """
            con.execute(query)
            pbar.set_postfix(status = f"Exported part_{batch_num:04d}")

    con.close()
    log_message(f"Parquet Export & {bin_seconds}s Binning Complete.")


def parse_args():
    parser = argparse.ArgumentParser(description = "Clean and time-bin staged metadata Parquet files.")
    parser.add_argument("--batch-size", type = int, default = 100)
    parser.add_argument("--bin-seconds", type = int, default = 180)
    parser.add_argument("--raw-dir", type = str, default = None)
    parser.add_argument("--timeseries-dir", type = str, default = None)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    clean_and_bin_metadata(
        batch_size = args.batch_size,
        bin_seconds = args.bin_seconds,
        raw_dir = args.raw_dir,
        timeseries_dir_override = args.timeseries_dir
    )
