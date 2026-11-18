import streamlit as st

st.set_page_config(
    page_title = "Deadlock Analytics",
    layout = "wide"
)

# page with poster-like discussion
summary_page = st.Page(
    "pages/summary.py",
    title = "Research Summary",
    default = True
)

# page for player stat  analysis
player_page = st.Page(
    "pages/player_analysis.py",
    title = "Player Analysis",
)

# page for full research paper
paper_page = st.Page(
    "pages/paper.py",
    title = "Research Paper",
)

pg = st.navigation(
    [summary_page, player_page, paper_page],
    position = "top"
)

pg.run()