import streamlit as st
import mlbstatsapi
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# Initialize MLB API
mlb = mlbstatsapi.Mlb()

# --- CONFIGURATION ---
# The URL for your new "Tidy" spreadsheet
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1Z6QaPLRVIU8kY9Fl4TGksk5uGM4ZzHVr5ebRifkoqKs/edit"
is_regular_season = datetime.now() >= datetime(2026, 3, 25)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []

# --- API FUNCTIONS ---
@st.cache_data(ttl=3600)
def fetch_hr_count(player_name, season_type="2026REG"):
    try:
        players = mlb.get_people_id(player_name)
        if not players: return 0
        stats = mlb.get_player_stats(players[0], groups=['hitting'], types=['season'], season=season_type)
        return stats['hitting']['season'].splits[0].stat.home_runs if 'hitting' in stats and 'season' in stats['hitting'] else 0
    except: return 0

@st.cache_data(ttl=3600)
def get_top_ten_by_position(pos_code, season_type="2026REG"):
    try:
        leaders = mlb.get_stats_leaders(leader_categories='homeRuns', stat_group='hitting', season=season_type, limit=10, position=pos_code)
        # Using lowercase 'fullname' for API compatibility
        data = [{"Player": l.person.fullname, "Team": l.team.name, "HR": l.value} for l in leaders[0].statleaders]
        return pd.DataFrame(data)
    except: return pd.DataFrame(columns=["Player", "Team", "HR"])

# --- APP UI ---
st.set_page_config(page_title="2026 Homer Draft", layout="wide", page_icon="⚾")
st.title("⚾ 2026 Home Run League War Room")

# Sidebar
season_mode = st.sidebar.radio("Season Phase:", ["Spring Training", "Regular Season"], index=1 if is_regular_season else 0)
api_season_code = "2026PRE" if season_mode == "Spring Training" else "2026REG"

if st.sidebar.button("🔄 Refresh All Data"):
    st.cache_data.clear()

# 1. Connect and Load Data from the new 'Draft_Data' tab
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    # Adding ttl=0 ensures it pulls the latest data and doesn't get stuck on an old error
    df_raw = conn.read(spreadsheet=spreadsheet_url, worksheet="Draft_Data", ttl=0)
    
    # Clean up any empty rows and map managers to their players
    df_raw = df_raw.dropna(subset=['Manager', 'Player'])
    managers = {m: df_raw[df_raw['Manager'] == m]['Player'].tolist() for m in df_raw['Manager'].unique()}
except Exception as e:
    st.error(f"Error loading [Draft Data]({spreadsheet_url}). Check that the tab name is exactly 'Draft_Data'. Error: {e}")
    st.stop()

# 2. Fetch Live Stats
all_team_data = {}
with st.spinner("Fetching live stats from MLB..."):
    for m, roster in managers.items():
        # We find the position from the spreadsheet for each player
        p_data = []
        for p in roster:
            pos = df_raw[df_raw['Player'] == p]['Position'].iloc[0]
            p_data.append({"Position": pos, "Player": p, "HR": fetch_hr_count(p, api_season_code)})
        all_team_data[m] = pd.DataFrame(p_data)

# Main Navigation
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Standings", "⚾ Leaders", "⚔️ Head-to-Head", "👀 Watchlist"])

# --- TAB 1: STANDINGS ---
with tab1:
    standings = [{"Manager": m, "Points": df_m['HR'].sum()} for m, df_m in all_team_data.items()]
    standings_df = pd.DataFrame(standings).sort_values(by="Points", ascending=False)
    st.subheader(f"Current Standings ({season_mode})")
    st.table(standings_df)

    # Draft Recap Section
    st.divider()
    st.subheader("🌱 Season Recap & Momentum")
    all_players = []
    for m, df_m in all_team_data.items():
        for _, row in df_m.iterrows():
            all_players.append({"Manager": m, "Player": row["Player"], "HR": row["HR"]})
    
    recap_df = pd.DataFrame(all_players).sort_values(by="HR", ascending=False)
    if not recap_df.empty and recap_df['HR'].max() > 0:
        top_player = recap_df.iloc[0]
        st.info(f"🔥 **Draft Steal:** {top_player['Player']} ({top_player['Manager']}) with {top_player['HR']} HRs!")
    else:
        st.info("No home runs recorded yet for this season phase.")

# --- TAB 2: POSITION LEADERS ---
with tab2:
    pos_map = {"C": "Catcher", "1B": "1st Base", "2B": "2nd Base", "3B": "3rd Base", "SS": "Shortstop", "OF": "Outfield", "DH": "DH"}
    sel_pos = st.selectbox("View Top 10 Leaders by Position:", list(pos_map.keys()), format_func=lambda x: pos_map[x])
    ldf = get_top_ten_by_position(sel_pos, api_season_code)
    st.dataframe(ldf, use_container_width=True, hide_index=True)

# --- TAB 3: HEAD-TO-HEAD ---
with tab3:
    col1, col2 = st.columns(2)
    m1 = col1.selectbox("Select Manager 1", list(managers.keys()), index=0)
    m2 = col2.selectbox("Select Manager 2", list(managers.keys()), index=1)
    
    # Merge the two teams based on position to compare side-by-side
    comp_df = all_team_data[m1].merge(all_team_data[m2], on="Position", suffixes=(f" ({m1})", f" ({m2})"))
    st.dataframe(comp_df, use_container_width=True, hide_index=True)
    
    s1, s2 = all_team_data[m1]["HR"].sum(), all_team_data[m2]["HR"].sum()
    st.metric(label="Score Comparison", value=f"{s1} vs {s2}", delta=int(s1-s2), delta_color="normal")

# --- TAB 4: WATCHLIST ---
with tab4:
    new_p = st.text_input("Add a player to watch (e.g., a free agent):")
    if st.button("Add to List"):
        if new_p: st.session_state.watchlist.append(new_p); st.rerun()
    
    if st.session_state.watchlist:
        st.write("### Your Watchlist")
        for p in st.session_state.watchlist:
            hr = fetch_hr_count(p, api_season_code)
            st.write(f"- **{p}**: {hr} HRs")
        if st.button("Clear List"):
            st.session_state.watchlist = []
            st.rerun()

st.caption(f"Data last synced with MLB API at {datetime.now().strftime('%H:%M:%S')}")
