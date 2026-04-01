import streamlit as st
import pandas as pd
import mlbstatsapi
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. PAGE SETUP & CONFIG ---
st.set_page_config(page_title="2026 Home Run League", layout="wide", page_icon="⚾")

# 🔄 Start the Auto-Refresher (Runs every 5 minutes / 300,000 milliseconds)
st_autorefresh(interval=300000, limit=None, key="war_room_refresh")

# --- BASEBALL THEME CSS ---
def apply_baseball_theme():
    st.markdown("""
    <style>
    /* Main background: Road Uniform Gray */
    .stApp {background-color: #D3D5D7;}
    /* Sidebar: Classic Scoreboard Green */
    [data-testid="stSidebar"] {background-color: #113C2B;}
    [data-testid="stSidebar"] * {color: #F4F4F0 !important;}
    /* Titles & Headers: Baseball Stitch Red */
    h1, h2, h3 {
        color: #C8102E !important; font-family: 'Trebuchet MS', Helvetica, sans-serif;
        font-weight: 800; text-transform: uppercase; letter-spacing: 1px;
    }
    /* Scoreboard styling for Head-to-Head Metrics */
    [data-testid="stMetricValue"] {
        color: #FDB827 !important; background-color: #111111;
        padding: 10px 20px; border-radius: 5px; border: 4px solid #333333;
        font-family: 'Courier New', Courier, monospace; font-weight: bold;
        text-align: center; display: inline-block;
    }
    [data-testid="stMetricLabel"] {font-weight: bold; font-size: 18px; color: #113C2B;}
    /* Style the Tabs like Ash Wood Bats */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #E2D1B3; border-radius: 8px; padding: 5px; border: 2px solid #C4A47C;
    }
    .stTabs [data-baseweb="tab"] {color: #113C2B; font-weight: bold; font-size: 16px;}
    .stTabs [aria-selected="true"] {background-color: #C8102E !important; color: #FFFFFF !important; border-radius: 5px;}
    /* Dataframe borders */
    [data-testid="stDataFrame"] {border: 2px solid #113C2B; border-radius: 5px; box-shadow: 3px 3px 8px rgba(0,0,0,0.1);}
    </style>
    """, unsafe_allow_html=True)

apply_baseball_theme()

# --- 2. API SETUP & SPREADSHEET CONFIG ---
mlb = mlbstatsapi.Mlb()
SHEET_ID = "1Z6QaPLRVIU8kY9Fl4TGksk5uGM4ZzHVr5ebRifkoqKs"
GID = "317249395"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# --- 3. HELPER FUNCTIONS ---
API_NAME_MAP = {
    "Jr. Caminero": "Junior Caminero", "Jose Ramirez": "José Ramírez", "Eugenio Suarez": "Eugenio Suárez",
    "Vladimir Guerrero": "Vladimir Guerrero Jr.", "Jazz Chisholm": "Jazz Chisholm Jr.", 
    "Ronald Acuna Jr.": "Ronald Acuña Jr.", "Lourdes Gurriel": "Lourdes Gurriel Jr.", 
    "Teoscar Hernandez": "Teoscar Hernández", "Luis Robert": "Luis Robert Jr."
}

@st.cache_data(ttl=3600)
def fetch_player_data(player_name, year=2026, game_type="R"):
    search_name = API_NAME_MAP.get(player_name, player_name)
    try:
        players = mlb.get_people_id(search_name)
        if not players: return 0, None, 0, 0, "Active", {}
        
        player_id = players[0]
        headshot_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{player_id}.jpg"
        
        # 🚑 Fetch injury status
        status = "Active"
        try:
            person = mlb.get_person(player_id)
            if hasattr(person, 'status') and hasattr(person.status, 'description'):
                status = person.status.description
        except Exception:
            pass
        
        season_hr, last_7_hr, last_15_hr, monthly_hr = 0, 0, 0, {}
        
        # 🛡️ 1. Fetch Season HRs safely
        try:
            s_stats = mlb.get_player_stats(player_id, stats=['season'], groups=['hitting'], season=year, gameType=game_type)
            if 'hitting' in s_stats and 'season' in s_stats['hitting'] and s_stats['hitting']['season'].splits:
                season_hr = s_stats['hitting']['season'].splits[0].stat.home_runs
        except Exception: pass

        # 🛡️ 2. Fetch Last 7 Days safely
        try:
            s7_stats = mlb.get_player_stats(player_id, stats=['last7Days'], groups=['hitting'], season=year, gameType=game_type)
            if 'hitting' in s7_stats and 'last7Days' in s7_stats['hitting'] and s7_stats['hitting']['last7Days'].splits:
                last_7_hr = s7_stats['hitting']['last7Days'].splits[0].stat.home_runs
        except Exception: pass

        # 🛡️ 3. Fetch Last 15 Games safely
        try:
            s15_stats = mlb.get_player_stats(player_id, stats=['last15Games'], groups=['hitting'], season=year, gameType=game_type)
            if 'hitting' in s15_stats and 'last15Games' in s15_stats['hitting'] and s15_stats['hitting']['last15Games'].splits:
                last_15_hr = s15_stats
