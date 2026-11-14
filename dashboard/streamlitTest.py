import streamlit as st
import duckdb
import pandas as pd
import requests
import plotly.express as px


# get parquet files from Deadlock API
manifest = requests.get("https://data.deadlock-api.com/v1/manifest.json").json()
base = manifest["public_url"]

def urls(table: str, limit: int = 50) -> list[str]:
    t = manifest["tables"][table]
    gen = t.get("generation", 0)
    file_list = [f"{base}/{f['key']}" for f in t["files"]
        if t["policy"] == "snapshot" or f.get("generation", 0) == gen]
    return file_list[-limit:]

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")

con.execute("SET threads = 2;")
con.execute("SET memory_limit = '4GB';")
con.execute("SET preserve_insertion_order = false;")

file_urls = urls("match_player", limit=30)
con.execute(f"CREATE VIEW match_player AS SELECT * FROM read_parquet({file_urls!r}, union_by_name = true)")

st.title("Deadlock Match View Test")

accountId = st.text_input("Enter your Steam account ID:")

# generate a table of matches for a given account ID
if accountId: 
    if not accountId.isdigit():
        st.error("Please enter a valid Steam account ID (numeric only).")
    else:
        player_matches = con.execute("""
            SELECT 
                match_id,
                duration_s,
                start_time
            FROM match_player
            WHERE account_id = ?
            ORDER BY start_time DESC
            """, [int(accountId)]).df()
        if player_matches.empty:
            st.warning("No matches found for this account ID.")
        else:
            st.success(f"Found {len(player_matches)} matches for account ID {accountId}.")
            
            match_options = player_matches["match_id"].tolist() if not player_matches.empty else []
            
            # allow for a user to select a match from the table and view stats
            selected_match = st.selectbox("Select a match to view your stats:",
                            match_options,
                            format_func = lambda x: (
                            f"Match ID: {x} | "
                            f"Duration: {player_matches.loc[player_matches["match_id"] == x, "duration_s"].iloc[0]} seconds |"
                            f"Start Time: {player_matches.loc[player_matches["match_id"] == x, "start_time"].iloc[0]}"
                            )
                        )
            st.write(f"Selected Match ID: {selected_match}")

            
            # generate a table of stats from the selected match
            match_stats = con.execute("""
                SELECT *
                from match_player
                WHERE match_id = ?
                and account_id = ?
                """, [selected_match, int(accountId)]).df()
            
            row = match_stats.iloc[0]
            
            timestamps = row["stats.time_stamp_s"]
            timeline = pd.DataFrame({
                "timestamp": timestamps})
            
            # extract all arrays with stats
            
            for col in match_stats.columns:
                if col.startswith("stats.") and col != "stats.time_stamp_s":
                    
                    values = row[col]
                    
                    if values is not None and len(values) == len(timestamps):
                        timeline[col.replace("stats.", "")] = values
            
            
            timeline["minutes"] = timeline["timestamp"] / 60
            
            for col in timeline.columns:
                timeline[col] = pd.to_numeric(
                    timeline[col], 
                    errors="coerce"
                    ).astype('float64')
            
            # match overview
            
            st.subheader("Match Overview")
            
            c1, c2, c3 = st.columns(3)
            
            c1.metric("Kills", int(timeline["kills"].iloc[-1]))
            c2.metric("Deaths", int(timeline["deaths"].iloc[-1]))
            c3.metric("Assists", int(timeline["assists"].iloc[-1]))
            
            # timeline visualizations
            
            stat_options = {
                "Kills": "kills",
                "Deaths": "deaths",
                "Assists": "assists",
                "Net Worth": "net_worth",
                "Creep Kills": "creep_kills",
                "Player Damage": "player_damage",
                "Damage Taken": "player_damage_taken",
                "Healing": "player_healing",
                "Level": "level"
            }
            
            selected_stat = st.selectbox(
                "Select a stat to visualize over time:",
                list(stat_options.keys())
            )
            
            column = stat_options[selected_stat]
            
            
            st.line_chart(
            timeline,
            x = "minutes",
            y = column
            )

        # raw data
        with st.expander("View Match Timeline Data"):
            st.dataframe(timeline, use_container_width=True)

elif accountId:
    st.error("Account ID must be numeric.")