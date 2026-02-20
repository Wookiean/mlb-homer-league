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
    /* Main background: Road Uniform Gray */
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

# This dictionary translates plain spreadsheet names to exact MLB API names
API_NAME_MAP = {
    "Jr. Caminero": "Junior Caminero",
    "Jose Ramirez": "José Ramírez",
    "Eugenio Suarez": "Eugenio Suárez",
    "Vladimir Guerrero": "Vladimir Guerrero Jr.",
    "Jazz Chisholm": "Jazz Chisholm Jr.",
    "Ronald Acuna Jr.": "Ronald Acuña Jr.",
    "Lourdes Gurriel": "Lourdes Gurriel Jr.",
    "Teoscar Hernandez": "Teoscar Hernández",
    "Luis Robert": "Luis Robert Jr."
}

@st.cache_data(ttl=3600)
def fetch_player_data(player_name, year=2026, game_type="R"):
    # Intercept the name and translate it if it is in our map
    search_name = API_NAME_MAP.get(player_name, player_name)
    
    try:
        players = mlb.get_people_id(search_name)
        if not players: 
            print(f"Still can't find: {search_name}")
            return 0, None
        
        player_id = players[0]
        headshot_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{player_id}.jpg"
        
        stats = mlb.get_player_stats(player_id, stats=['season'], groups=['hitting'], season=year, gameType=game_type)
        if 'hitting' in stats and 'season' in stats['hitting']:
            return stats['hitting']['season'].splits[0].stat.home_runs, headshot_url
        return 0, headshot_url
    except Exception as e:
        print(f"API Error for {search_name}: {e}")
        return 0, None

@st.cache_data(ttl=3600)
def get_league_leaders(pos_code, year=2026, game_type="R"):
    try:
        leaders = mlb.get_stats_leaders(leader_categories='homeRuns', stat_group='hitting', season=year, gameType=game_type, limit=10, position=pos_code)
        if leaders and hasattr(leaders[0], 'statleaders'):
            data = []
            for l in leaders[0].statleaders:
                pid = l.person.id
                h_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{pid}.jpg"
                data.append({"Photo": h_url, "Player": l.person.fullname, "Team": l.team.name, "HR": l.value})
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

api_year = 2026
api_game_type = "S" if season_mode == "Spring Training" else "R"

st.sidebar.divider()
if st.sidebar.button("🔄 Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

# Load Data
roster_df = load_draft_data()
managers = roster_df['Manager'].unique().tolist()

all_team_data = {}
with st.spinner("Crunching live MLB stats & generating headshots..."):
    for m in managers:
        team_df = roster_df[roster_df['Manager'] == m].copy()
        # Fetch data tuple (HR, URL) and split into two columns
        stats_data = team_df['Player'].apply(lambda p: fetch_player_data(p, api_year, api_game_type))
        team_df['HR'] = stats_data.apply(lambda x: x[0])
        team_df['Photo'] = stats_data.apply(lambda x: x[1])
        all_team_data[m] = team_df

# --- 5. TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Standings", "⚔️ Head-to-Head", "⚾ MLB Leaders", "⏪ 2025 Rewind"])

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
            display_df = all_team_data[m][['Photo', 'Position', 'Player', 'MLB Team', 'HR']].sort_values(by="HR", ascending=False)
            st.dataframe(
                display_df, 
                hide_index=True, 
                use_container_width=True,
                column_config={"Photo": st.column_config.ImageColumn("Photo")}
            )

with tab2:
    st.subheader("Matchup Analyzer")
    col1, col2 = st.columns(2)
    m1 = col1.selectbox("Select Away Team", managers, index=0)
    m2 = col2.selectbox("Select Home Team", managers, index=1 if len(managers) > 1 else 0)
    
    if m1 and m2:
        df1 = all_team_data[m1][['Position', 'Photo', 'Player', 'HR']].rename(columns={'Photo': f'{m1} Photo', 'Player': f'{m1} Player', 'HR': f'{m1} HR'})
        df2 = all_team_data[m2][['Position', 'Photo', 'Player', 'HR']].rename(columns={'Photo': f'{m2} Photo', 'Player': f'{m2} Player', 'HR': f'{m2} HR'})
        
        matchup_df = pd.merge(df1, df2, on='Position', how='outer').fillna('-')
        
        st.markdown("<br>", unsafe_allow_html=True)
        score1 = all_team_data[m1]['HR'].sum()
        score2 = all_team_data[m2]['HR'].sum()
        
        sc1, sc2, sc3 = st.columns([1, 2, 1])
        with sc2:
             st.metric(label=f"{m1} vs {m2}", value=f"{score1} - {score2}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(
            matchup_df, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                f"{m1} Photo": st.column_config.ImageColumn(""),
                f"{m2} Photo": st.column_config.ImageColumn("")
            }
        )

with tab3:
    st.subheader("Top 10 Leaders by Position")
    pos_map = {"C": "Catcher", "1B": "1st Base", "2B": "2nd Base", "3B": "3rd Base", "SS": "Shortstop", "OF": "Outfield", "DH": "Designated Hitter"}
    selected_pos = st.selectbox("Select Position:", list(pos_map.keys()), format_func=lambda x: pos_map[x])
    
    leaders_df = get_league_leaders(selected_pos, api_year, api_game_type)
    if not leaders_df.empty:
        st.dataframe(
            leaders_df, 
            hide_index=True, 
            use_container_width=True,
            column_config={"Photo": st.column_config.ImageColumn("Photo")}
        )
    else:
        st.warning("No data available for this position yet.")

with tab4:
    st.subheader("⏪ The 2025 Alternate Universe")
    st.info("How would your current 2026 roster have performed last year? Click below to run the simulation based on official 2025 MLB Regular Season totals.")
    
    if st.button("Simulate 2025 Season"):
        with st.spinner("Traveling back in time to fetch 2025 stats..."):
            retro_team_data = {}
            for m in managers:
                team_df = roster_df[roster_df['Manager'] == m].copy()
                stats_data = team_df['Player'].apply(lambda p: fetch_player_data(p, 2025, "R"))
                team_df['2025 HR'] = stats_data.apply(lambda x: x[0])
                team_df['Photo'] = stats
