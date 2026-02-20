import streamlit as st
import pandas as pd
import mlbstatsapi
from datetime import datetime

# --- 1. PAGE SETUP & CONFIG ---
st.set_page_config(page_title="2026 Home Run League", layout="wide", page_icon="⚾")
mlb = mlbstatsapi.Mlb()

# We use the direct CSV export link to completely bypass the "HTTP 400" authentication errors.
SHEET_ID = "1Z6QaPLRVIU8kY9Fl4TGksk5uGM4ZzHVr5ebRifkoqKs"
GID = "317249395"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

is_regular_season = datetime.now() >= datetime(2026, 3, 25)

# --- 2. API HELPER FUNCTIONS ---
@st.cache_data(ttl=3600) # Cache data for 1 hour so the app loads instantly on refresh
def fetch_hr_count(player_name, season_type="2026REG"):
    try:
        players = mlb.get_people_id(player_name)
        if not players: 
            return 0
        
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

# --- 3. DATA LOADING ---
@st.cache_data(ttl=300) # Re-check the Google Sheet every 5 minutes
def load_draft_data():
    try:
        df = pd.read_csv(CSV_URL)
        # Drop empty rows just in case
        return df.dropna(subset=['Manager', 'Player'])
    except Exception as e:
        st.error(f"Failed to load spreadsheet. Error: {e}")
        st.stop()

# --- 4. MAIN APP UI ---
st.title("⚾ 2026 Home Run League War Room")

# Sidebar Controls
st.sidebar.header("League Settings")
season_mode = st.sidebar.radio("Season Phase:", ["Spring Training", "Regular Season"], index=1 if is_regular_season else 0)
api_season_code = "2026PRE" if season_mode == "Spring Training" else "2026REG"

if st.sidebar.button("🔄 Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

# Load the raw spreadsheet data
roster_df = load_draft_data()
managers = roster_df['Manager'].unique().tolist()

# Process live stats for all teams
all_team_data = {}
with st.spinner("Crunching live MLB stats..."):
    for m in managers:
        team_df = roster_df[roster_df['Manager'] == m].copy()
        # Fetch HRs for each player in this manager's dataframe
        team_df['HR'] = team_df['Player'].apply(lambda p: fetch_hr_count(p, api_season_code))
        all_team_data[m] = team_df

# --- 5. TABS ---
tab1, tab2, tab3 = st.tabs(["🏆 Standings", "⚔️ Head-to-Head", "⚾ MLB Leaders"])

# TAB 1: STANDINGS
with tab1:
    # Calculate total points
    standings_data = [{"Manager": m, "Total HRs": all_team_data[m]['HR'].sum()} for m in managers]
    standings_df = pd.DataFrame(standings_data).sort_values(by="Total HRs", ascending=False).reset_index(drop=True)
    
    st.subheader(f"Current {season_mode} Standings")
    st.dataframe(standings_df, use_container_width=True)

    st.divider()
    st.subheader("📋 Full Roster Breakdown")
    
    # Create columns to display each manager's roster side-by-side
    cols = st.columns(len(managers))
    for i, m in enumerate(managers):
        with cols[i]:
            st.markdown(f"**{m}'s Team**")
            display_df = all_team_data[m][['Position', 'Player', 'MLB Team', 'HR']].sort_values(by="HR", ascending=False)
            st.dataframe(display_df, hide_index=True, use_container_width=True)

# TAB 2: HEAD-TO-HEAD
with tab3:
    st.subheader("Matchup Analyzer")
    col1, col2 = st.columns(2)
    m1 = col1.selectbox("Select Team 1", managers, index=0)
    m2 = col2.selectbox("Select Team 2", managers, index=1 if len(managers) > 1 else 0)
    
    if m1 and m2:
        df1 = all_team_data[m1][['Position', 'Player', 'HR']].rename(columns={'Player': f'{m1} Player', 'HR': f'{m1} HR'})
        df2 = all_team_data[m2][['Position', 'Player', 'HR']].rename(columns={'Player': f'{m2} Player', 'HR': f'{m2} HR'})
        
        # Merge on position to compare directly
        matchup_df = pd.merge(df1, df2, on='Position', how='outer').fillna('-')
        st.dataframe(matchup_df, hide_index=True, use_container_width=True)
        
        score1 = all_team_data[m1]['HR'].sum()
        score2 = all_team_data[m2]['HR'].sum()
        st.info(f"**Current Score:** {m1} **{score1}** — **{score2}** {m2}")

# TAB 3: MLB LEADERS
with tab2:
    st.subheader("Top 10 Leaders by Position")
    pos_map = {"C": "Catcher", "1B": "1st Base", "2B": "2nd Base", "3B": "3rd Base", "SS": "Shortstop", "OF": "Outfield", "DH": "Designated Hitter"}
    selected_pos = st.selectbox("Select Position:", list(pos_map.keys()), format_func=lambda x: pos_map[x])
    
    leaders_df = get_league_leaders(selected_pos, api_season_code)
    if not leaders_df.empty:
        st.dataframe(leaders_df, hide_index=True, use_container_width=True)
    else:
        st.warning("No data available for this position yet.")

st.caption(f"Last updated: {datetime.now().strftime('%I:%M:%S %p')}")
