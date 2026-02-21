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
is_regular_season = datetime.now() >= datetime(2026, 3, 25)

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
                last_15_hr = s15_stats['hitting']['last15Games'].splits[0].stat.home_runs
        except Exception: pass

        # 🛡️ 4. Fetch Monthly stats safely
        try:
            m_stats = mlb.get_player_stats(player_id, stats=['byMonth'], groups=['hitting'], season=year, gameType=game_type)
            if 'hitting' in m_stats and 'byMonth' in m_stats['hitting'] and m_stats['hitting']['byMonth'].splits:
                for split in m_stats['hitting']['byMonth'].splits:
                    month_val = getattr(split, 'month', None)
                    if month_val:
                        monthly_hr[month_val] = split.stat.home_runs
        except Exception: pass
                        
        return season_hr, headshot_url, last_7_hr, last_15_hr, status, monthly_hr
    except Exception as e:
        print(f"API Error for {search_name}: {e}")
        return 0, None, 0, 0, "Unknown", {}

@st.cache_data(ttl=3600)
def get_league_leaders(pos_code, year=2026, game_type="R"):
    try:
        leaders = mlb.get_stats_leaders(leader_categories='homeRuns', stat_group='hitting', season=year, gameTypes=game_type, limit=10, position=pos_code)
        if leaders and hasattr(leaders[0], 'statleaders'):
            data = [{"Photo": f"https://securea.mlb.com/mlb/images/players/head_shot/{l.person.id}.jpg", 
                     "Player": l.person.fullname, "Team": l.team.name, "HR": l.value} for l in leaders[0].statleaders]
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_draft_data():
    try: return pd.read_csv(CSV_URL).dropna(subset=['Manager', 'Player'])
    except Exception as e: st.stop()

# --- 4. MAIN APP UI ---
st.title("⚾ 2026 Home Run League War Room")

st.sidebar.header("⚙️ League Settings")
season_mode = st.sidebar.radio("Season Phase:", ["Spring Training", "Regular Season"], index=1 if is_regular_season else 0)
api_year = 2026
api_game_type = "S" if season_mode == "Spring Training" else "R"

st.sidebar.divider()
if st.sidebar.button("🔄 Force Refresh All Data"):
    st.cache_data.clear()
    st.rerun()

roster_df = load_draft_data()
managers = roster_df['Manager'].unique().tolist()
all_team_data = {}

with st.spinner("Crunching live MLB stats, injury reports, & hot streaks..."):
    for m in managers:
        team_df = roster_df[roster_df['Manager'] == m].copy()
        # Unpack the 6 pieces of data
        stats_data = team_df['Player'].apply(lambda p: fetch_player_data(p, api_year, api_game_type))
        team_df['HR'] = stats_data.apply(lambda x: x[0])
        team_df['Photo'] = stats_data.apply(lambda x: x[1])
        team_df['Last 7 Days'] = stats_data.apply(lambda x: x[2])
        team_df['Last 15 Games'] = stats_data.apply(lambda x: x[3])
        team_df['Status'] = stats_data.apply(lambda x: x[4])
        team_df['Monthly Data'] = stats_data.apply(lambda x: x[5])
        
        # Apply the IL Ambulance emoji
        def format_name(row):
            if "IL" in str(row['Status']) or "Injured" in str(row['Status']): return f"🚑 {row['Player']}"
            return row['Player']
        team_df['Display Name'] = team_df.apply(format_name, axis=1)
        all_team_data[m] = team_df

# --- 5. TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Standings", "⚔️ Head-to-Head", "⚾ MLB Leaders", "⏪ 2025 Rewind", "📈 Pennant Race"])

with tab1:
    standings_data = [{"Manager": m, "Total HRs": all_team_data[m]['HR'].sum(), "Last 7 Days": all_team_data[m]['Last 7 Days'].sum(), "Last 15 Games": all_team_data[m]['Last 15 Games'].sum()} for m in managers]
    standings_df = pd.DataFrame(standings_data).sort_values(by="Total HRs", ascending=False).reset_index(drop=True)
    st.subheader(f"Current {season_mode} Standings")
    st.dataframe(standings_df, use_container_width=True)

    st.divider()
    st.subheader("📋 Full Roster Breakdown")
    
    manager_tabs = st.tabs([f"🧢 {m}'s Team" for m in managers])
    
    for i, m in enumerate(managers):
        with manager_tabs[i]:
            display_df = all_team_data[m][['Photo', 'Position', 'Display Name', 'MLB Team', 'HR', 'Last 7 Days', 'Last 15 Games']].sort_values(by="HR", ascending=False)
            st.dataframe(
                display_df, 
                hide_index=True, 
                use_container_width=True, 
                # 🖼️ FIX: Make Standings tab photos larger
                column_config={"Photo": st.column_config.ImageColumn("Photo", width="large")}
            )

with tab2:
    @st.fragment
    def render_matchup_analyzer():
        st.subheader("Matchup Analyzer")
        col1, col2 = st.columns(2)
        m1 = col1.selectbox("Select Away Team", managers, index=0, key="away_team_select")
        m2 = col2.selectbox("Select Home Team", managers, index=1 if len(managers) > 1 else 0, key="home_team_select")
        
        if m1 == m2: st.warning(f"⚠️ You selected {m1} for both teams!")
        elif m1 and m2:
            df1 = all_team_data[m1][['Position', 'Photo', 'Display Name', 'HR']].copy()
            df2 = all_team_data[m2][['Position', 'Photo', 'Display Name', 'HR']].copy()
            df1['match_key'] = df1.groupby('Position').cumcount()
            df2['match_key'] = df2.groupby('Position').cumcount()
            
            df1 = df1.rename(columns={'Photo': f'{m1} Photo', 'Display Name': f'{m1} Player', 'HR': f'{m1} HR'})
            df2 = df2.rename(columns={'Photo': f'{m2} Photo', 'Display Name': f'{m2} Player', 'HR': f'{m2} HR'})
            
            matchup_df = pd.merge(df1, df2, on=['Position', 'match_key'], how='outer').drop(columns=['match_key'])
            matchup_df[f'{m1} Player'] = matchup_df[f'{m1} Player'].fillna('---')
            matchup_df[f'{m2} Player'] = matchup_df[f'{m2} Player'].fillna('---')
            matchup_df[f'{m1} HR'] = matchup_df[f'{m1} HR'].fillna('-')
            matchup_df[f'{m2} HR'] = matchup_df[f'{m2} HR'].fillna('-')
            
            st.markdown("<br>", unsafe_allow_html=True)
            sc1, sc2, sc3 = st.columns([1, 2, 1])
            with sc2: st.metric(label=f"{m1} vs {m2}", value=f"{all_team_data[m1]['HR'].sum()} - {all_team_data[m2]['HR'].sum()}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(
                matchup_df, 
                hide_index=True, 
                use_container_width=True, 
                # 🖼️ FIX: Make Head-to-Head tab photos larger
                column_config={
                    f"{m1} Photo": st.column_config.ImageColumn("", width="large"), 
                    f"{m2} Photo": st.column_config.ImageColumn("", width="large")
                }
            )
    render_matchup_analyzer()

with tab3:
    @st.fragment
    def render_mlb_leaders():
        st.subheader("Top 10 Leaders by Position")
        pos_map = {"C": "Catcher", "1B": "1st Base", "2B": "2nd Base", "3B": "3rd Base", "SS": "Shortstop", "OF": "Outfield", "DH": "Designated Hitter"}
        selected_pos = st.selectbox("Select Position:", list(pos_map.keys()), format_func=lambda x: pos_map[x], key="leader_pos_select")
        leaders_df = get_league_leaders(selected_pos, api_year, api_game_type)
        if not leaders_df.empty: 
            st.dataframe(
                leaders_df, 
                hide_index=True, 
                use_container_width=True, 
                # 🖼️ FIX: Make MLB Leaders tab photos larger
                column_config={"Photo": st.column_config.ImageColumn("Photo", width="large")}
            )
        else: st.warning("No data available for this position yet.")
    render_mlb_leaders()

with tab4:
    st.subheader("⏪ The 2025 Alternate Universe")
    if st.button("Simulate 2025 Season"):
        with st.spinner("Traveling back in time to fetch 2025 stats..."):
            retro_team_data = {}
            for m in managers:
                team_df = roster_df[roster_df['Manager'] == m].copy()
                stats_data = team_df['Player'].apply(lambda p: fetch_player_data(p, 2025, "R"))
                team_df['2025 HR'] = stats_data.apply(lambda x: x[0])
                team_df['Photo'] = stats_data.apply(lambda x: x[1])
                retro_team_data[m] = team_df
            
            retro_standings = [{"Manager": m, "2025 Total HRs": retro_team_data[m]['2025 HR'].sum()} for m in managers]
            st.markdown("### 🏆 2025 Simulated Standings")
            st.dataframe(pd.DataFrame(retro_standings).sort_values(by="2025 Total HRs", ascending=False).reset_index(drop=True), use_container_width=True)
            
            st.divider()
            st.markdown("### 📋 2025 Player Contributions")
            cols = st.columns(len(managers))
            for i, m in enumerate(managers):
                with cols[i]:
                    st.markdown(f"### {m}'s Team")
                    display_df = retro_team_data[m][['Photo', 'Position', 'Player', '2025 HR']].sort_values(by="2025 HR", ascending=False)
                    st.dataframe(
                        display_df, 
                        hide_index=True, 
                        use_container_width=True, 
                        # 🖼️ FIX: Make 2025 Rewind tab photos larger
                        column_config={"Photo": st.column_config.ImageColumn("Photo", width="large")}
                    )

with tab5:
    st.subheader("📈 Monthly Home Run Pennant Race")
    st.info("Tracking total home runs hit by each manager's roster month-by-month.")
    
    chart_data = {}
    has_monthly_data = False
    
    for m in managers:
        manager_monthly = {}
        for monthly_dict in all_team_data[m]['Monthly Data']:
            for month, hrs in monthly_dict.items():
                manager_monthly[month] = manager_monthly.get(month, 0) + hrs
                has_monthly_data = True
        chart_data[m] = manager_monthly
        
    df_chart = pd.DataFrame(chart_data)
    
    if has_monthly_data and not df_chart.empty:
        df_chart = df_chart.sort_index()
        month_names = {3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September", 10: "October"}
        try: df_chart.index = df_chart.index.map(lambda x: month_names.get(int(x), f"Month {x}"))
        except: pass 
        st.line_chart(df_chart)
    else:
        st.warning("Not enough monthly data to build the pennant race chart yet. Check back when the season gets going!")

st.caption(f"Stats last synced from MLB API at {datetime.now().strftime('%I:%M:%S %p')}")
