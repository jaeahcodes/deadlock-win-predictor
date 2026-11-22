import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import requests
import duckdb
import os
import time

@st.cache_resource
def load_database():

    con = duckdb.connect()

    con.execute("SET threads = 2;")
    con.execute("SET memory_limit = '4GB';")
    con.execute("SET preserve_insertion_order = false;")

    con.execute("""
        CREATE VIEW match_player AS
        SELECT *
        FROM read_parquet(
            'timeseries_parquet/*.parquet',
            union_by_name = true
        )
    """)

    return con

con = load_database()

# Import custom models, this allows for easier and cleaner use of streamlit dashboard,
# alongside better maintenance and readability.
from modules.visualizer import deadlockVisualizer
from modules.matchsearch import matchSearcher
# from modules.(MODEL) import winModeler 

def get_player_matches(match_id):
    
    searcher = matchSearcher(
        con = con,
        matchID = match_id
    )

    return searcher.findPlayerMatches(data="match_player")


def get_match_info(hero_id, team, match_id):
    searcher = matchSearcher(
    con = con,
    heroID = hero_id
    )

    return searcher.playerMatchInfo(
        data = "match_player",
        team = team,
        heroID = hero_id,
        matchID = match_id
    )
    
st.set_page_config(page_title = "Deadlock Win Predictor", layout = "wide")

def makeGraph(match_info, stats, name):
    stats = stats
    name = name
    
    fig = deadlockVisualizer.plotPlayerStats(
        min = match_info["minutes"].to_numpy(), 
        stat = match_info[stats].to_numpy(),
        stat_name = name)
    return fig

# initialize session state to save data when running
defaults = {
    "match_id": None,
    "team_id": None,
    "hero_id": None,
    "matches": None,
    "playerInfo": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# removes awkward padding before the title
# changes search bar color
st.markdown(
    body="""
    <style>
        .block-container {
            padding-top: 25px;
        }

        /* Match ID input */
        [data-testid="stSidebar"] input {
            background-color: #ffffff !important;
            color: #222222 !important;
            caret-color: #222222 !important;
        }
        
    </style>
""", unsafe_allow_html=True
)

#Title and description
st.title("Player Stat Analysis")
st.markdown("This app allows players to look up matches they have played, see stats over time in the game, and view predicted win rates. With this you can see what may have turned the tide at different points of gameplay, improving your strategies and become a better player!")

# Create input for player info to allow searching stats/games
st.sidebar.header("Match Search")

match_id = st.sidebar.text_input("Please enter a valid Deadlock match ID")

# logic to let players search for their matches
if st.sidebar.button("Search", type = "secondary", icon = ":material/database_search:"):
    if not match_id.strip():
        st.sidebar.error("Match ID not valid.")
    elif not match_id.strip().isdigit():
        st.sidebar.error("Match ID must be numeric.")
    else:
        st.session_state.match_id = int(match_id)
        
        matches = get_player_matches(match_id = st.session_state.match_id) # change when file finished
        
        st.session_state.matches = matches
        st.session_state.playerInfo = None
        st.session_state.hero_id = None
        st.session_state.team_id = None
        st.session_state.playerInfo = None
    
# logic to let players select matches
# gathers info from matches for graphing
if st.session_state.match_id is not None:
    if st.session_state.matches is not None:
        
        matches = st.session_state.matches
        st.sidebar.caption(f"Found {len(matches)} players for match with ID: {match_id}")
        
        if matches.empty:
            st.info("No matches with this ID in the dataset.")
        else:
            st.sidebar.subheader("Match History")
            
            # create a selectable dataframe with match information
            
            with st.sidebar.spinner("Loading info"):
                time.sleep(1)
            event = st.sidebar.dataframe(
                    matches[["match_id", "hero", "team",  "outcome"]],
                    use_container_width = True,
                    hide_index = True,
                    on_select = "rerun",
                    selection_mode = "single-row",
                    column_config = {
                    "match_id": st.column_config.NumberColumn("Match ID"),
                    "hero": st.column_config.TextColumn("Hero"),
                    "team": st.column_config.NumberColumn("Team"),
                    "outcome": st.column_config.TextColumn("Outcome")
                }
            )
            
            if event.selection.rows:
                
                selected_row = event.selection.rows[0]
            
                selected_player = matches.iloc[selected_row]
                
                selected_hero = int(selected_player["hero_id"])
                selected_team = int(selected_player["team"])
                
                # creates session state info when a new hero/team is selected
                if (
                    selected_hero != st.session_state.hero_id 
                    or selected_team != st.session_state.team_id):
                        st.session_state.hero_id = selected_hero
                        st.session_state.team_id = selected_team
                    
                        st.sidebar.caption(f"SELECTED HERO: {matches["hero"].iloc[selected_row]}")
                        
                    
                        st.session_state.playerInfo = get_match_info(
                            hero_id = selected_hero,
                            team = selected_team, 
                            match_id = st.session_state.match_id)
            else:
                st.session_state.hero_id = None
                st.session_state.team_id = None
                st.session_state.playerInfo = None
                
# logic which runs after match is selected, performs graphing and information lookup
if (
    st.session_state.playerInfo is not None 
    and not st.session_state.playerInfo.empty):
    
    st.subheader("Match Overview")
                    
    match_info = st.session_state.playerInfo        
    
    # creates columns showing off player stats
    c1, c2, c3, c4 = st.columns(4)
                    
    c1.metric("Kills", int(match_info["total_kills"].iloc[-1]))
    c2.metric("Deaths", int(match_info["total_deaths"].iloc[-1]))
    c3.metric("Assists", int(match_info["total_assists"].iloc[-1]))
    c4.metric("Net-worth", int(match_info["total_net_worth"].iloc[-1]))
    
    
    graphCol1, graphCol2, graphCol3 = st.columns(3)
    
    graphStats = ["player_kills", "player_deaths", "player_assists"]
    graphNames = ["Kills", "Deaths", "Assists"]
    
    graphColumns = [graphCol1, graphCol2, graphCol3]
    
    for stats, name, col in zip(graphStats, graphNames, graphColumns):
        fig = makeGraph(match_info, stats, name)
        
        with col:
            st.pyplot(fig)
            
    
    networthGraph = deadlockVisualizer.plotNetworth(match_info)
    st.pyplot(networthGraph)
# conditional format for when a player has no info selected
elif st.session_state.playerInfo is None:
    st.subheader("Match Overview")
    
    placeholder = "?"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kills", placeholder)
    c2.metric("Deaths", placeholder)
    c3.metric("Assists", placeholder)
    c4.metric("Net-worth", placeholder)
    
    st.subheader("Please enter a Deadlock match_id and select a player from the list to view your stats",
    text_alignment = "center")
    
