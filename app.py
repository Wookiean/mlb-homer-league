import streamlit as st
import pandas as pd
import mlbstatsapi
from datetime import datetime

# --- 1. PAGE SETUP & CONFIG ---
st.set_page_config(page_title="2026 Home Run League", layout="wide", page_icon="⚾")

# --- BASEBALL THEME CSS ---
def apply_baseball_theme():
    st.markdown("""
    <style>
    /* Main background: Road Uniform Gray (much softer on the eyes) */
    .stApp {
        background-color: #D3D5D7;
    }
    
    /* Sidebar: Classic Scoreboard Green */
    [data-testid="stSidebar"] {
        background-color: #113C2B;
    }
    [data-testid="stSidebar"] * {
        color: #F4F4F0 !important;
    }

    /* Titles & Headers: Baseball Stitch Red */
    h1, h2, h3 {
        color: #C8102E !important;
        font-family: 'Trebuchet MS', Helvetica, sans-serif;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Scoreboard styling for Head-to-Head Metrics */
    [data-testid="stMetricValue"] {
        color: #FDB827 !important; /* Jumbotron Yellow */
        background-color: #111111;
        padding: 10px 20px;
        border-radius: 5px;
        border: 4px solid #333333;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        text-align: center;
        display: inline-block;
    }
    [data-testid="stMetricLabel"] {
        font-weight: bold;
        font-size: 18px;
        color: #113C2B;
    }

    /* Style the Tabs like Ash Wood Bats */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #E2D1B3; 
        border-radius: 8px;
        padding: 5px;
        border: 2px solid #C4A47C;
    }
    .stTabs [data-baseweb="tab"] {
        color: #113C2B;
        font-weight: bold;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #C8102E !important;
        color: #FFFFFF !important;
        border-radius: 5px;
    }
    
    /* Dataframe borders */
    [data-testid="stDataFrame"] {
        border: 2px solid #113C2B;
        border-radius: 5px;
        box-shadow: 3px 3px 8px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

apply_baseball_theme()

# --- 2. API SETUP & SPREADSHEET CONFIG ---
mlb = mlbstatsapi.Mlb()

SHEET_ID = "1Z6QaPLRVIU8kY9Fl4TGksk5uGM4ZzHVr5ebRifkoqKs"
GID = "317249395"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

is_regular_season = datetime.now() >= datetime(2026, 3, 25)

# --- 3. HELPER FUNCTIONS ---
@st.cache_data(ttl=3600)
def fetch_hr_count(player_name, season_type="2026REG"):
    try:
        players = mlb.get_people_id(player_name)
        if not players: return 0
        stats = mlb.get_player_stats(players[0], groups=['hitting'], types=['season'], season=season_type)
        if 'hitting' in stats and 'season' in stats['hitting']:
            return stats['hitting']['season'].splits[0].stat.home_runs
        return 0
    except Exception:
        return 0

@st.cache_data(ttl=3600)
def get_league_leaders(pos_code, season_type="2026REG"):
    try:
        leaders = mlb.get_stats_leaders(leader_categories='homeRuns', stat_group='hitting', season=season_type, limit=10, position=pos_code)
        if leaders and hasattr(leaders[0], 'statleaders'):
            data = [{"Player": l.person.fullname, "Team": l.team.name, "HR": l.value} for l in leaders[0].statleaders]
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_draft_data():
    try:
        df = pd.read_csv(CSV_URL)
        return df.dropna(subset=['Manager', 'Player'])
    except Exception as e:
        st.error(f"Failed to load spreadsheet. Error: {e}")
        st.stop()

# --- 4. MAIN APP UI ---
st.title("⚾ 2026 Home Run League War Room")

# Sidebar Controls
st.sidebar.header("⚙️ League Settings")
season_mode = st.sidebar.radio("Season Phase:", ["Spring Training", "Regular Season"], index=1 if is_regular_season else 0)
api_season_code = "2026PRE" if season_mode == "Spring Training" else "2026REG"

st.sidebar.divider()
if st.sidebar.button("🔄 Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

# Load Data
roster_df = load_draft_data()
managers = roster_df['Manager'].unique().tolist()

all_team_data = {}
with st.spinner("Crunching live MLB stats..."):
    for m in managers:
        team_df = roster_df[roster_df['Manager'] == m].copy()
        team_df['HR'] = team_df['Player'].apply(lambda p: fetch_hr_count(p, api_season_code))
        all_team_data[m] = team_df

# --- 5. TABS ---
tab1, tab2, tab3 = st.tabs(["🏆 Standings", "⚔️ Head-to-Head", "⚾ MLB Leaders"])

with tab1:
    standings_data = [{"Manager": m, "Total HRs": all_team_data[m]['HR'].sum()} for m in managers]
    standings_df = pd.DataFrame(standings_data).sort_values(by="Total HRs", ascending=False).reset_index(drop=True)
    
    st.subheader(f"Current {season_mode} Standings")
    st.dataframe(standings_df, use_container_width=True)

    st.divider()
    st.subheader("📋 Full Roster Breakdown")
    
    cols = st.columns(len(managers))
    for i, m in enumerate(managers):
        with cols[i]:
            st.markdown(f"### {m}'s Team")
            display_df = all_team_data[m][['Position', 'Player', 'MLB Team', 'HR']].sort_values(by="HR", ascending=False)
            st.dataframe(display_df, hide_index=True, use_container_width=True)

with tab2:
    st.subheader("Matchup Analyzer")
    col1, col2 = st.columns(2)
    m1 = col1.selectbox("Select Away Team", managers, index=0)
    m2 = col2.selectbox("Select Home Team", managers, index=1 if len(managers) > 1 else 0)
    
    if m1 and m2:
        df1 = all_team_data[m1][['Position', 'Player', 'HR']].rename(columns={'Player': f'{m1} Player', 'HR': f'{m1} HR'})
        df2 = all_team_data[m2][['Position', 'Player', 'HR']].rename(columns={'Player': f'{m2} Player', 'HR': f'{m2} HR'})
        
        matchup_df = pd.merge(df1, df2, on='Position', how='outer').fillna('-')
        
        # Display the custom Jumbotron metric
        st.markdown("<br>", unsafe_allow_html=True)
        score1 = all_team_data[m1]['HR'].sum()
        score2 = all_team_data[m2]['HR'].sum()
        
        sc1, sc2, sc3 = st.columns([1, 2, 1])
        with sc2:
             st.metric(label=f"{m1} vs {m2}", value=f"{score1} - {score2}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(matchup_df, hide_index=True, use_container_width=True)

with tab3:
    st.subheader("Top 10 Leaders by Position")
    pos_map = {"C": "Catcher", "1B": "1st Base", "2B": "2nd Base", "3B": "3rd Base", "SS": "Shortstop", "OF": "Outfield", "DH": "Designated Hitter"}
    selected_pos = st.selectbox("Select Position:", list(pos_map.keys()), format_func=lambda x: pos_map[x])
    
    leaders_df = get_league_leaders(selected_pos, api_season_code)
    if not leaders_df.empty:
        st.dataframe(leaders_df, hide_index=True, use_container_width=True)
    else:
        st.warning("No data available for this position yet.")

st.caption(f"Stats last synced from MLB API at {datetime.now().strftime('%I:%M:%S %p')}")
