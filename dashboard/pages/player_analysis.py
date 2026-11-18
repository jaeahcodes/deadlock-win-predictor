import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import requests
import duckdb
import os

### ONLY USED WHILE NO DATABASE PRESENT
@st.cache_resource
def load_database():

    manifest = requests.get(
        "https://data.deadlock-api.com/v1/manifest.json",
        timeout=30
    ).json()

    base = manifest["public_url"]

    def urls(table: str, limit: int = 50) -> list[str]:
        t = manifest["tables"][table]
        gen = t.get("generation", 0)

        file_list = [
            f"{base}/{f['key']}"
            for f in t["files"]
            if t["policy"] == "snapshot"
            or f.get("generation", 0) == gen
        ]

        return file_list[-limit:]

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    con.execute("SET threads = 2;")
    con.execute("SET memory_limit = '4GB';")
    con.execute("SET preserve_insertion_order = false;")

    file_urls = urls("match_player", limit=30)

    con.execute(
        f"""CREATE VIEW match_player AS
        SELECT * FROM read_parquet(
            {file_urls!r},
            union_by_name = true
        )"""
    )

    return con


con = load_database()

# Import custom models, this allows for easier and cleaner use of streamlit dashboard,
# alongside better maintenance and readability.
from modules.visualizer import deadlockVisualizer
from modules.matchsearch import matchSearcher
# from modules.(MODEL) import winModeler 

def get_player_matches(account_id):
    searcher = matchSearcher(
        con = con,
        accountID = account_id
    )

    return searcher.findPlayerMatches(data="match_player")


def get_match_info(account_id, match_id):
    searcher = matchSearcher(
        con = con,
        accountID = account_id
    )

    return searcher.playerMatchInfo(
        data = "match_player",
        accountID = account_id,
        matchID = match_id
    )
    
st.set_page_config(page_title = "Deadlock Win Predictor", layout = "wide")

# initialize session state to save data when running
defaults = {
    "account_id": None,
    "match_id": None,
    "matches": None,
    "playerInfo": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
    
#Title and description
st.title("Player Stat Analysis")
st.markdown("This app allows players to look up matches they have played, see stats over time in the game, and view predicted win rates. With this you can see what may have turned the tide at different points of gameplay, improving your strategies and become a better player!")

# Create input for player info to allow searching stats/games
st.sidebar.header("Player Search")

account_id = st.sidebar.text_input("Please enter a valid SteamID (Steam3ID)")

if st.sidebar.button("Search"):
    if not account_id.strip():
        st.sidebar.error("Please enter a SteamID")
    elif not account_id.strip().isdigit():
        st.sidebar.error("SteamID must be numeric.")
    else:
        st.session_state.account_id = int(account_id)
        st.session_state.match_id = None
        
        matches = get_player_matches(account_id = st.session_state.account_id) # change when file finished
        
        st.session_state.matches = matches
        st.session_state.playerInfo = None
    
if st.session_state.account_id is not None:
    if st.session_state.matches is not None:
        
        matches = st.session_state.matches
        st.sidebar.success(f"Found {len(matches)} matches for account ID " 
                    f"{st.session_state.account_id}.")
        
        if matches.empty:
            st.info("No matches in the available dataset.")
        else:
            st.sidebar.subheader("Match History")
            
            # create a selectable dataframe with match information
            event = st.sidebar.dataframe(
                matches[["match_id", "start_time", "duration_s", "hero_name"]],
                use_container_width = True,
                hide_index = True,
                on_select = "rerun",
                selection_mode = "single-row"
            )
            
            if event.selection.rows:
                
                selected_row = event.selection.rows[0]
            
                selected_match = int(matches.iloc[selected_row]["match_id"])
                
                if selected_match != st.session_state.match_id:
                    st.session_state.match_id = selected_match
                    
                
                    st.session_state.playerInfo = get_match_info(
                        account_id = st.session_state.account_id,
                        match_id = st.session_state.match_id)
                    
                st.sidebar.success(f"SELECTED MATCH {st.session_state.match_id}")
                
    
    

