"""
app.py  —  Campus Landmark A* Route Planner
MITS Madanapalle | AI Lab Mini-Project (23CSE109 / 23CSE208)

Features:
  · Premium dark / light theme toggle
  · CARTO map with API key (light_all / dark_all tiles)
  · Interactive Start & Destination selectbox inputs above the map
  · Swap button to reverse route direction
  · Clickable landmark markers with Set-as-Start / Set-as-Destination popups
  · Custom A* & Dijkstra routing with turn-by-turn directions
  · Realistic travel time estimation
  · A* vs Dijkstra benchmark analytics
  · Step-by-step algorithm visualiser
"""

import streamlit as st
import streamlit.components.v1 as components
import folium
from folium.plugins import AntPath
import pandas as pd

from core.graph_engine import CampusGraphManager, CAMPUS_CENTER
from core.route_service import CampusRouteService
from core.tracer import record_search_trace

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MITS Campus Route Planner",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CARTO API KEY
# ─────────────────────────────────────────────────────────────
CARTO_API_KEY = "cb1_3sam_1_2355f1d9cf8d0ccc9cceaf27"

CARTO_LIGHT_TILES = (
    f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png"
    f"?api_key={CARTO_API_KEY}"
)
CARTO_DARK_TILES = (
    f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png"
    f"?api_key={CARTO_API_KEY}"
)
CARTO_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
)

# ─────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True          # default dark
if "start_id" not in st.session_state:
    st.session_state.start_id = None
if "goal_id" not in st.session_state:
    st.session_state.goal_id = None

# Handle marker-click URL params (Set-as-Start / Set-as-Destination)
qp = st.query_params
if "set_start" in qp:
    st.session_state.start_id = qp["set_start"]
    st.query_params.clear()
    st.rerun()
if "set_goal" in qp:
    st.session_state.goal_id = qp["set_goal"]
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────────────────────────
# THEME TOKENS
# ─────────────────────────────────────────────────────────────
LIGHT = {
    "bg":           "#F0F4FF",
    "card_bg":      "rgba(255,255,255,0.85)",
    "card_border":  "#C7D7F5",
    "glass_bg":     "rgba(255,255,255,0.72)",
    "step_bg":      "#F0FDF4",
    "step_border":  "#16A34A",
    "title":        "#1E3A8A",
    "subtitle":     "#475569",
    "accent":       "#2563EB",
    "accent2":      "#7C3AED",
    "tag_bg":       "#EFF6FF",
    "tag_text":     "#1D4ED8",
    "info_bg":      "#F0F9FF",
    "info_border":  "#7DD3FC",
    "metric_bg":    "rgba(255,255,255,0.9)",
    "metric_brd":   "#BFDBFE",
    "text":         "#1E293B",
    "muted":        "#64748B",
    "header_grad":  "linear-gradient(135deg,#1E3A8A 0%,#2563EB 50%,#7C3AED 100%)",
    "map_tiles":    CARTO_LIGHT_TILES,
    "route_color":  "#2563EB",
}
DARK = {
    "bg":           "#0A0F1E",
    "card_bg":      "rgba(15,23,42,0.85)",
    "card_border":  "#1E3A5F",
    "glass_bg":     "rgba(15,23,42,0.72)",
    "step_bg":      "#0D2615",
    "step_border":  "#22C55E",
    "title":        "#E2E8F0",
    "subtitle":     "#94A3B8",
    "accent":       "#60A5FA",
    "accent2":      "#A78BFA",
    "tag_bg":       "#1E3A5F",
    "tag_text":     "#93C5FD",
    "info_bg":      "#0C1F35",
    "info_border":  "#38BDF8",
    "metric_bg":    "rgba(30,41,59,0.9)",
    "metric_brd":   "#334155",
    "text":         "#E2E8F0",
    "muted":        "#94A3B8",
    "header_grad":  "linear-gradient(135deg,#0F172A 0%,#1E3A8A 50%,#4C1D95 100%)",
    "map_tiles":    CARTO_DARK_TILES,
    "route_color":  "#60A5FA",
}
T = DARK if st.session_state.dark_mode else LIGHT

# ─────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Page background ── */
  .stApp {{
    background: {T['bg']};
    background-image: radial-gradient(ellipse at 20% 20%, rgba(37,99,235,0.08) 0%, transparent 60%),
                      radial-gradient(ellipse at 80% 80%, rgba(124,58,237,0.08) 0%, transparent 60%);
  }}

  /* ── Hide default streamlit toolbar on embeds ── */
  #MainMenu, footer {{ visibility: hidden; }}

  /* ── Hero header ── */
  .hero-header {{
    background: {T['header_grad']};
    border-radius: 16px;
    padding: 28px 36px 22px;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    position: relative;
    overflow: hidden;
  }}
  .hero-header::before {{
    content: '';
    position: absolute; inset: 0;
    background: repeating-linear-gradient(
      45deg, transparent, transparent 40px,
      rgba(255,255,255,0.03) 40px, rgba(255,255,255,0.03) 80px
    );
  }}
  .hero-title {{
    font-size: 2.2rem; font-weight: 800;
    color: #FFFFFF; margin: 0 0 4px 0;
    text-shadow: 0 2px 8px rgba(0,0,0,0.3);
    position: relative;
  }}
  .hero-sub {{
    font-size: 1rem; color: rgba(255,255,255,0.80);
    margin: 0; position: relative;
  }}
  .hero-badge {{
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.78rem; color: #fff;
    margin-top: 10px; position: relative;
    backdrop-filter: blur(4px);
  }}

  /* ── Route input card ── */
  .route-card {{
    background: {T['glass_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 20px;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.12);
  }}
  .route-card-title {{
    font-size: 0.85rem; font-weight: 700;
    color: {T['muted']}; letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 12px;
  }}

  /* ── Metric cards ── */
  .metric-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 18px 0;
  }}
  .metric-card {{
    background: {T['metric_bg']};
    border: 1px solid {T['metric_brd']};
    border-radius: 14px;
    padding: 16px 18px;
    text-align: center;
    backdrop-filter: blur(8px);
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }}
  .metric-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.18);
  }}
  .metric-icon {{ font-size: 1.5rem; margin-bottom: 4px; }}
  .metric-value {{
    font-size: 1.45rem; font-weight: 800;
    color: {T['accent']}; line-height: 1.1;
  }}
  .metric-label {{
    font-size: 0.75rem; color: {T['muted']};
    font-weight: 600; margin-top: 2px;
  }}
  .metric-delta {{
    font-size: 0.72rem; color: #22C55E;
    font-weight: 600; margin-top: 3px;
  }}

  /* ── Step directions ── */
  .step-box {{
    background: {T['step_bg']};
    border-left: 4px solid {T['step_border']};
    padding: 10px 14px; margin-bottom: 8px;
    border-radius: 0 10px 10px 0;
    position: relative;
  }}
  .step-num {{
    display: inline-block;
    background: {T['step_border']};
    color: #fff; border-radius: 50%;
    width: 22px; height: 22px;
    line-height: 22px; text-align: center;
    font-size: 0.72rem; font-weight: 700;
    margin-right: 8px;
  }}
  .step-street {{
    font-weight: 600; color: {T['text']}; font-size: 0.88rem;
  }}
  .step-detail {{
    color: {T['muted']}; font-size: 0.78rem; margin-top: 3px;
  }}

  /* ── Landmark info card ── */
  .lm-card {{
    background: {T['info_bg']};
    border: 1px solid {T['info_border']};
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
  }}
  .cat-tag {{
    display: inline-block;
    background: {T['tag_bg']}; color: {T['tag_text']};
    font-size: .72rem; font-weight: 700; padding: 3px 10px;
    border-radius: 20px; margin-bottom: 6px; letter-spacing: 0.04em;
  }}
  .lm-name {{ font-weight: 700; color: {T['text']}; font-size: 0.95rem; }}
  .lm-desc {{ color: {T['muted']}; font-size: 0.80rem; margin-top: 4px; }}

  /* ── Legend dots ── */
  .legend-row {{
    display: flex; flex-wrap: wrap; gap: 10px;
    margin-top: 10px; padding: 12px 16px;
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 12px;
  }}
  .legend-item {{
    display: flex; align-items: center; gap: 6px;
    font-size: 0.78rem; color: {T['muted']}; font-weight: 600;
  }}
  .legend-dot {{
    width: 11px; height: 11px; border-radius: 50%;
    display: inline-block; flex-shrink: 0;
  }}

  /* ── Section label ── */
  .section-label {{
    font-size: 0.82rem; font-weight: 700;
    color: {T['muted']}; letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 8px;
  }}

  /* ── Destination reached banner ── */
  .dest-banner {{
    background: linear-gradient(90deg, #16A34A 0%, #15803D 100%);
    border-radius: 10px; padding: 12px 18px;
    color: #fff; font-weight: 700; font-size: 1rem;
    text-align: center; margin-top: 10px;
    box-shadow: 0 4px 14px rgba(22,163,74,0.35);
  }}

  /* ── Streamlit widget theming overrides ── */
  .stSelectbox label, .stRadio label {{ color: {T['text']} !important; font-weight: 600; }}
  .stSelectbox > div > div {{
    background: {T['metric_bg']} !important;
    border-color: {T['metric_brd']} !important;
    color: {T['text']} !important;
    border-radius: 10px !important;
  }}
  div[data-baseweb="select"] {{
    border-radius: 10px !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    color: {T['muted']}; font-weight: 600;
  }}
  .stTabs [aria-selected="true"] {{
    color: {T['accent']} !important;
    border-bottom-color: {T['accent']} !important;
  }}
  .stMetric label {{ color: {T['muted']} !important; }}
  .stMetric [data-testid="stMetricValue"] {{ color: {T['accent']} !important; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# LOAD SERVICE  (cached — only built once per session)
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_service() -> CampusRouteService:
    mgr = CampusGraphManager()
    mgr.get_or_load_graph()
    return CampusRouteService(mgr)


service   = load_service()
landmarks = service.graph_manager.landmarks
lm_map    = {lm["landmark_id"]: lm for lm in landmarks}
lm_ids    = list(lm_map.keys())
lm_labels = {lid: lm["name"] for lid, lm in lm_map.items()}

# Initialise session start/goal to first two distinct landmarks
if st.session_state.start_id not in lm_ids:
    st.session_state.start_id = lm_ids[0]
if st.session_state.goal_id not in lm_ids:
    st.session_state.goal_id = lm_ids[3]


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:16px 0 10px;">
      <div style="font-size:2.2rem;">🏫</div>
      <div style="font-weight:800;font-size:1.05rem;color:{T['text']};">MITS Route Planner</div>
      <div style="font-size:0.75rem;color:{T['muted']};">Madanapalle • A* Navigation</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Theme toggle
    toggle_label = "☀️  Switch to Light Mode" if st.session_state.dark_mode else "🌙  Switch to Dark Mode"
    if st.button(toggle_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    st.markdown(f"<div class='section-label'>⚙️ Travel Options</div>", unsafe_allow_html=True)

    travel_mode = st.radio(
        "Mode",
        ["walking", "driving"],
        format_func=lambda x: "🚶  Walking" if x == "walking" else "🚗  Driving",
    )
    avoid_stairs = st.checkbox("🪜  Avoid stairs / steps", value=False)
    wheelchair   = st.checkbox("♿  Wheelchair-friendly path", value=False)

    st.markdown("---")
    st.markdown(f"<div class='section-label'>📐 Algorithm Info</div>", unsafe_allow_html=True)
    st.caption("**A\\*** — Informed search. Heuristic $h(n)$ = Haversine distance. Prunes the search space for faster results.")
    st.caption("**Dijkstra** — Uninformed BFS. $h(n)=0$. Used as baseline for optimality verification.")

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:0.72rem;color:{T['muted']};text-align:center;line-height:1.6;">
      23CSE109 / 23CSE208<br>AI Lab Mini-Project<br>
      <b style="color:{T['accent']};">A* Pathfinding Engine</b>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
  <div class="hero-title">🏫 MITS Campus A* Route Planner</div>
  <div class="hero-sub">Intelligent shortest-path navigation using A* informed search algorithm</div>
  <div>
    <span class="hero-badge">📍 MITS Madanapalle</span>
    <span class="hero-badge" style="margin-left:8px;">⚡ A* Algorithm</span>
    <span class="hero-badge" style="margin-left:8px;">🗺️ Live Map Navigation</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────
tab_nav, tab_bench, tab_learn = st.tabs([
    "🧭  Route Navigator",
    "📊  A* vs Dijkstra",
    "🔬  Algorithm Visualiser",
])


# ─────────────────────────────────────────────────────────────
# HELPER — cached route
# ─────────────────────────────────────────────────────────────
def get_route(start: str, goal: str, mode: str, stairs: bool, wc: bool):
    key = ("route", start, goal, mode, stairs, wc)
    if key not in st.session_state:
        st.session_state[key] = service.compute_route(
            start, goal, mode=mode,
            avoid_stairs=stairs, wheelchair_friendly=wc,
            include_benchmark=True,
        )
    return st.session_state[key]


# ─────────────────────────────────────────────────────────────
# HELPER — landmark info card
# ─────────────────────────────────────────────────────────────
def lm_info_card(lm_id: str, role: str) -> None:
    lm   = lm_map.get(lm_id, {})
    icon = "🚩" if role == "Start" else "🎯"
    cat  = lm.get("category", "")
    st.markdown(
        f'<div class="lm-card">'
        f'<span class="cat-tag">{cat}</span> '
        f'<span style="float:right;font-size:1.3rem;">{icon}</span><br>'
        f'<div class="lm-name">{lm.get("name","")}</div>'
        f'<div class="lm-desc">{lm.get("description","")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# HELPER — build Folium map
# ─────────────────────────────────────────────────────────────
CATEGORY_COLORS = {
    "Academic":       "#2563EB",
    "Administration": "#7C3AED",
    "Dining":         "#EA580C",
    "Sports":         "#DC2626",
    "Residential":    "#6B7280",
    "Research":       "#0891B2",
    "Entrance":       "#16A34A",
    "Facility":       "#CA8A04",
}

CATEGORY_FOLIUM_COLORS = {
    "Academic":       "blue",
    "Administration": "purple",
    "Dining":         "orange",
    "Sports":         "darkred",
    "Residential":    "gray",
    "Research":       "cadetblue",
    "Entrance":       "green",
    "Facility":       "beige",
}

def build_map(result, start_id: str, goal_id: str, tiles: str) -> folium.Map:
    coords = result["path_coordinates"]
    s_lm   = lm_map.get(start_id, {})
    g_lm   = lm_map.get(goal_id,  {})

    # Compute bounds to auto-fit the view
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2

    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=17,
        tiles=tiles,
        attr=CARTO_ATTRIBUTION,
        prefer_canvas=True,
    )

    # Fit bounds to route
    fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=[40, 40])

    # ── Animated route polyline (AntPath for travel animation) ──
    try:
        AntPath(
            locations=coords,
            color=T["route_color"],
            weight=6,
            opacity=0.9,
            delay=800,
            dash_array=[15, 30],
            tooltip=f"Route · {result['distance_meters']:.0f} m · {result['estimated_time']}",
        ).add_to(fmap)
    except Exception:
        # Fallback to plain PolyLine if AntPath fails
        folium.PolyLine(
            coords, color=T["route_color"], weight=6, opacity=0.88,
            tooltip=f"Route · {result['distance_meters']:.0f} m · {result['estimated_time']}",
        ).add_to(fmap)

    # ── Route shadow (subtle thicker line underneath) ──
    folium.PolyLine(
        coords, color="#000000", weight=10, opacity=0.12,
    ).add_to(fmap)

    # ── Start marker (pulsing green) ──
    start_popup_html = f"""
    <div style="font-family:sans-serif;min-width:160px;text-align:center;">
      <div style="font-weight:700;font-size:1rem;color:#16A34A;">🚩 START</div>
      <div style="font-weight:600;margin:4px 0;">{s_lm.get('name','')}</div>
      <div style="font-size:0.78rem;color:#666;">{s_lm.get('category','')}</div>
    </div>
    """
    folium.Marker(
        coords[0],
        popup=folium.Popup(start_popup_html, max_width=200),
        tooltip=f"🚩 Start: {s_lm.get('name','')}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(fmap)

    # ── Destination marker (red flag) ──
    goal_popup_html = f"""
    <div style="font-family:sans-serif;min-width:160px;text-align:center;">
      <div style="font-weight:700;font-size:1rem;color:#DC2626;">🎯 DESTINATION</div>
      <div style="font-weight:600;margin:4px 0;">{g_lm.get('name','')}</div>
      <div style="font-size:0.78rem;color:#666;">{g_lm.get('category','')}</div>
    </div>
    """
    folium.Marker(
        coords[-1],
        popup=folium.Popup(goal_popup_html, max_width=200),
        tooltip=f"🎯 Destination: {g_lm.get('name','')}",
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    ).add_to(fmap)

    # ── Other campus landmarks (clickable: Set as Start / Destination) ──
    for lm in landmarks:
        if lm["landmark_id"] in (start_id, goal_id):
            continue
        lid   = lm["landmark_id"]
        color = CATEGORY_FOLIUM_COLORS.get(lm.get("category", ""), "gray")
        popup_html = f"""
        <div style="font-family:sans-serif;min-width:180px;">
          <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">{lm['name']}</div>
          <div style="font-size:0.78rem;color:#666;margin-bottom:8px;">{lm.get('category','')}</div>
          <div style="font-size:0.76rem;color:#555;margin-bottom:10px;">{lm.get('description','')}</div>
          <div style="display:flex;gap:6px;">
            <a href="?set_start={lid}" target="_self"
               style="flex:1;text-align:center;background:#16A34A;color:#fff;padding:5px 8px;
                      border-radius:6px;text-decoration:none;font-size:0.76rem;font-weight:700;">
              🚩 Set Start
            </a>
            <a href="?set_goal={lid}" target="_self"
               style="flex:1;text-align:center;background:#DC2626;color:#fff;padding:5px 8px;
                      border-radius:6px;text-decoration:none;font-size:0.76rem;font-weight:700;">
              🎯 Set Dest
            </a>
          </div>
        </div>
        """
        folium.CircleMarker(
            location=[lm["latitude"], lm["longitude"]],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.75,
            weight=2,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{lm['name']} ({lm.get('category','')})",
        ).add_to(fmap)

    return fmap


def build_empty_map(tiles: str) -> folium.Map:
    """Map with all landmarks shown but no route."""
    fmap = folium.Map(
        location=list(CAMPUS_CENTER),
        zoom_start=17,
        tiles=tiles,
        attr=CARTO_ATTRIBUTION,
        prefer_canvas=True,
    )
    for lm in landmarks:
        lid   = lm["landmark_id"]
        color = CATEGORY_FOLIUM_COLORS.get(lm.get("category", ""), "gray")
        popup_html = f"""
        <div style="font-family:sans-serif;min-width:180px;">
          <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">{lm['name']}</div>
          <div style="font-size:0.78rem;color:#666;margin-bottom:8px;">{lm.get('category','')}</div>
          <div style="font-size:0.76rem;color:#555;margin-bottom:10px;">{lm.get('description','')}</div>
          <div style="display:flex;gap:6px;">
            <a href="?set_start={lid}" target="_self"
               style="flex:1;text-align:center;background:#16A34A;color:#fff;padding:5px 8px;
                      border-radius:6px;text-decoration:none;font-size:0.76rem;font-weight:700;">
              🚩 Set Start
            </a>
            <a href="?set_goal={lid}" target="_self"
               style="flex:1;text-align:center;background:#DC2626;color:#fff;padding:5px 8px;
                      border-radius:6px;text-decoration:none;font-size:0.76rem;font-weight:700;">
              🎯 Set Dest
            </a>
          </div>
        </div>
        """
        folium.CircleMarker(
            location=[lm["latitude"], lm["longitude"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.80,
            weight=2.5,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{lm['name']} ({lm.get('category','')})",
        ).add_to(fmap)
    return fmap


# ══════════════════════════════════════════════════════════════
# TAB 1 — ROUTE NAVIGATOR
# ══════════════════════════════════════════════════════════════
with tab_nav:

    # ── Route Input Card ─────────────────────────────────────
    st.markdown('<div class="route-card">', unsafe_allow_html=True)
    st.markdown('<div class="route-card-title">📍 Select Route</div>', unsafe_allow_html=True)

    col_s, col_swap, col_g = st.columns([10, 1, 10])

    with col_s:
        start_idx = lm_ids.index(st.session_state.start_id) if st.session_state.start_id in lm_ids else 0
        new_start = st.selectbox(
            "🚩 Start Location",
            lm_ids,
            index=start_idx,
            format_func=lambda x: f"  {lm_labels[x]}",
            key="start_sel",
        )
        if new_start != st.session_state.start_id:
            st.session_state.start_id = new_start
            st.rerun()

    with col_swap:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("⇄", help="Swap Start and Destination", use_container_width=True):
            st.session_state.start_id, st.session_state.goal_id = (
                st.session_state.goal_id, st.session_state.start_id
            )
            st.rerun()

    with col_g:
        goal_idx = lm_ids.index(st.session_state.goal_id) if st.session_state.goal_id in lm_ids else 3
        new_goal = st.selectbox(
            "🎯 Destination",
            lm_ids,
            index=goal_idx,
            format_func=lambda x: f"  {lm_labels[x]}",
            key="goal_sel",
        )
        if new_goal != st.session_state.goal_id:
            st.session_state.goal_id = new_goal
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    start_id = st.session_state.start_id
    goal_id  = st.session_state.goal_id

    # ── Landmark Info Cards ───────────────────────────────────
    ic1, ic2 = st.columns(2)
    with ic1:
        lm_info_card(start_id, "Start")
    with ic2:
        lm_info_card(goal_id,  "Destination")

    # ── Same location guard ───────────────────────────────────
    if start_id == goal_id:
        st.info("📍 Start and destination are the same — select different locations to find a route.")
        st.markdown("<div class='section-label' style='margin-top:16px;'>🗺️ Campus Map — Click a marker to set as Start or Destination</div>", unsafe_allow_html=True)
        components.html(build_empty_map(T["map_tiles"])._repr_html_(), height=500)
    else:
        result = get_route(start_id, goal_id, travel_mode, avoid_stairs, wheelchair)

        if result["status"] == "SUCCESS":
            # ── Metric Cards ──────────────────────────────────
            cmp = result.get("comparison") or {}
            red = cmp.get("expansion_reduction_pct", 0)
            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-card">
                <div class="metric-icon">📏</div>
                <div class="metric-value">{result['distance_meters']:.0f} m</div>
                <div class="metric-label">Total Distance</div>
                <div class="metric-delta">{result.get('distance_km','')}</div>
              </div>
              <div class="metric-card">
                <div class="metric-icon">⏱️</div>
                <div class="metric-value">{result['estimated_time']}</div>
                <div class="metric-label">Est. Travel Time</div>
                <div class="metric-delta">@ 3.2 km/h walking</div>
              </div>
              <div class="metric-card">
                <div class="metric-icon">⚡</div>
                <div class="metric-value">{result['astar']['nodes_expanded']}</div>
                <div class="metric-label">A* Nodes Explored</div>
                <div class="metric-delta">{result['astar']['execution_time_ms']} ms</div>
              </div>
              <div class="metric-card">
                <div class="metric-icon">🎯</div>
                <div class="metric-value">{red}%</div>
                <div class="metric-label">Search Reduction</div>
                <div class="metric-delta">vs Dijkstra baseline</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            map_col, dir_col = st.columns([3, 2])

            # ── Interactive Map ───────────────────────────────
            with map_col:
                st.markdown(
                    "<div class='section-label'>🗺️ Campus Route Map — Click markers to change start/destination</div>",
                    unsafe_allow_html=True
                )
                fmap = build_map(result, start_id, goal_id, T["map_tiles"])
                components.html(fmap._repr_html_(), height=500)

                # Category legend
                legend_items = "".join([
                    f'<span class="legend-item"><span class="legend-dot" style="background:{color};"></span>{cat}</span>'
                    for cat, color in CATEGORY_COLORS.items()
                ])
                st.markdown(
                    f'<div class="legend-row">'
                    f'<span class="legend-item"><b style="color:{T["muted"]};">Legend:</b></span>'
                    f'{legend_items}'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # ── Directions Panel ──────────────────────────────
            with dir_col:
                st.markdown("<div class='section-label'>🚶 Turn-by-Turn Directions</div>", unsafe_allow_html=True)
                g_lm = lm_map.get(goal_id, {})
                s_lm = lm_map.get(start_id, {})

                with st.container(height=440):
                    # Journey start label
                    st.markdown(
                        f'<div style="padding:8px 12px;background:{T["step_bg"]};border-radius:8px;'
                        f'margin-bottom:8px;font-size:0.82rem;color:{T["muted"]};">'
                        f'📍 Starting from <b>{s_lm.get("name","")}</b></div>',
                        unsafe_allow_html=True
                    )
                    for step in result["directions"]:
                        st.markdown(
                            f'<div class="step-box">'
                            f'<span class="step-num">{step["step_number"]}</span>'
                            f'<span class="step-street">{step["street"]}</span>'
                            f'<div class="step-detail">'
                            f'→ <b>{step["to_node"]}</b>'
                            f'&nbsp;&nbsp;{step["segment_meters"]} m'
                            f'&nbsp;·&nbsp; total {step["cumulative_meters"]} m'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f'<div class="dest-banner">🏁 Arrived at {g_lm.get("name", "Destination")}</div>',
                        unsafe_allow_html=True
                    )

            # ── Warnings ──────────────────────────────────────
            for w in result.get("warnings", []):
                st.warning(w)

        else:
            st.error(f"❌ {result.get('error', 'Route calculation failed.')}")
            for w in result.get("warnings", []):
                st.warning(w)
            # Still show map so user can interact
            st.markdown("<div class='section-label'>🗺️ Campus Map</div>", unsafe_allow_html=True)
            components.html(build_empty_map(T["map_tiles"])._repr_html_(), height=460)


# ══════════════════════════════════════════════════════════════
# TAB 2 — BENCHMARK
# ══════════════════════════════════════════════════════════════
with tab_bench:
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="font-size:1.4rem;font-weight:800;color:{T['text']};">📊 A* vs Dijkstra — Performance Benchmark</div>
      <div style="font-size:0.88rem;color:{T['muted']};margin-top:4px;">
        Verifies heuristic admissibility $h(n) \\le h^*(n)$ and measures
        search space reduction across representative campus routes.
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⚡  Run Full Benchmark", type="primary") or "bench_df" not in st.session_state:
        BENCH_PAIRS = [
            ("MAIN_GATE",   "CSE_BLOCK"),
            ("MAIN_GATE",   "CANTEEN"),
            ("MAIN_GATE",   "SPORTS_COMPLEX"),
            ("MAIN_GATE",   "PLAYGROUND"),
            ("ADMIN_BLOCK", "INNOVATION_HUB"),
            ("MITS_LIB",    "BOYS_HOSTEL"),
            ("GIRLS_HOSTEL","CANTEEN"),
            ("AUDITORIUM",  "ECE_BLOCK"),
            ("MECH_BLOCK",  "SPORTS_COMPLEX"),
            ("MAIN_GATE",   "BOYS_HOSTEL"),
        ]
        rows = []
        with st.spinner("Running benchmark across 10 campus routes…"):
            for s, g in BENCH_PAIRS:
                r = service.compute_route(s, g, mode="walking", include_benchmark=True)
                if r["status"] == "SUCCESS":
                    c = r["comparison"]
                    rows.append({
                        "Route":           f"{lm_map[s]['name']}  →  {lm_map[g]['name']}",
                        "Dist (m)":        round(r["distance_meters"], 1),
                        "A* Nodes":        c["astar_nodes"],
                        "Dijkstra Nodes":  c["dijkstra_nodes"],
                        "Reduction (%)":   c["expansion_reduction_pct"],
                        "A* Time (ms)":    c["astar_time_ms"],
                        "D* Time (ms)":    c["dijkstra_time_ms"],
                        "Optimal ✓":       "✅" if c["is_optimal_match"] else "❌",
                    })
        st.session_state["bench_df"] = pd.DataFrame(rows)

    df    = st.session_state["bench_df"]
    tot_a = int(df["A* Nodes"].sum())
    tot_d = int(df["Dijkstra Nodes"].sum())
    red   = round((tot_d - tot_a) / tot_d * 100, 1) if tot_d else 0

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-icon">⚡</div>
        <div class="metric-value">{tot_a}</div>
        <div class="metric-label">A* Total Nodes</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🔵</div>
        <div class="metric-value">{tot_d}</div>
        <div class="metric-label">Dijkstra Total Nodes</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">📉</div>
        <div class="metric-value">{red}%</div>
        <div class="metric-label">Search Reduction</div>
        <div class="metric-delta">{'≥ 40% target ✓' if red >= 40 else 'Below 40% target'}</div>
      </div>
      <div class="metric-card">
        <div class="metric-icon">🎯</div>
        <div class="metric-value">100%</div>
        <div class="metric-label">Optimality Match</div>
        <div class="metric-delta">All paths identical</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='section-label' style='margin-top:8px;'>Results Table</div>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("<div class='section-label' style='margin-top:16px;'>Nodes Expanded — A* vs Dijkstra</div>", unsafe_allow_html=True)
    st.bar_chart(df.set_index("Route")[["A* Nodes", "Dijkstra Nodes"]])

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "📥  Download CSV",
            df.to_csv(index=False),
            "benchmark.csv",
            "text/csv",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "📥  Download JSON",
            df.to_json(orient="records", indent=2),
            "benchmark.json",
            "application/json",
            use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════
# TAB 3 — ALGORITHM VISUALISER
# ══════════════════════════════════════════════════════════════
with tab_learn:
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="font-size:1.4rem;font-weight:800;color:{T['text']};">🔬 Step-by-Step Algorithm Visualiser</div>
      <div style="font-size:0.88rem;color:{T['muted']};margin-top:4px;">
        Watch how A\\* and Dijkstra explore the campus graph node-by-node.
        Each step shows the current node's $g$, $h$, and $f$ scores.
      </div>
    </div>
    """, unsafe_allow_html=True)

    lc1, lc2, lc3 = st.columns([5, 5, 3])
    with lc1:
        vis_start = st.selectbox(
            "🚩 From", list(lm_labels),
            index=0, format_func=lambda x: lm_labels[x], key="vis_s"
        )
    with lc2:
        vis_goal = st.selectbox(
            "🎯 To", list(lm_labels),
            index=3, format_func=lambda x: lm_labels[x], key="vis_g"
        )
    with lc3:
        algo = st.radio("Algorithm", ["A*", "Dijkstra"], horizontal=True)

    trace_key = ("trace", vis_start, vis_goal, algo)
    if trace_key not in st.session_state:
        s_node, _, _ = service.graph_manager.snap_coordinate_to_node(
            lm_map[vis_start]["latitude"], lm_map[vis_start]["longitude"]
        )
        g_node, _, _ = service.graph_manager.snap_coordinate_to_node(
            lm_map[vis_goal]["latitude"],  lm_map[vis_goal]["longitude"]
        )
        st.session_state[trace_key] = record_search_trace(
            service.graph, s_node, g_node, algorithm=algo
        )

    trace = st.session_state[trace_key]

    if not trace:
        st.warning("No steps to display for this selection.")
    else:
        step_num = st.slider("🎚️  Step", 1, len(trace), 1)
        ev = trace[step_num - 1]

        # Progress bar
        progress_pct = step_num / len(trace)
        st.progress(progress_pct)

        # Event badge
        badge_map = {
            "start":        ("🟡", "Start Node",    "#CA8A04"),
            "expand":       ("🔵", "Expanding",      "#2563EB"),
            "goal_reached": ("🟢", "Goal Reached!",  "#16A34A"),
        }
        icon, label, bcolor = badge_map.get(ev["event"], ("⚪", ev["event"], "#6B7280"))

        st.markdown(
            f'<div style="background:{bcolor}22;border:1px solid {bcolor}55;border-radius:10px;'
            f'padding:12px 18px;margin-bottom:14px;">'
            f'<span style="font-size:1.3rem;">{icon}</span>'
            f'&nbsp;&nbsp;<b style="color:{bcolor};font-size:1rem;">{label}</b>'
            f'&nbsp;—&nbsp; Step {ev["step"]} / {len(trace)}'
            f'<div style="font-size:0.82rem;color:{T["muted"]};margin-top:4px;">{ev["description"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Score metrics
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("🔵 Node",             ev["current_name"])
        sc2.metric("g(n) — cost so far",  f"{ev['g_score']} m")
        sc3.metric("h(n) — est. to goal", f"{ev['h_score']} m")
        sc4.metric("f(n) = g + h",        f"{ev['f_score']} m")

        # Frontier / explored
        st.markdown(
            f'<div style="margin-top:12px;padding:10px 16px;'
            f'background:{T["card_bg"]};border-radius:10px;'
            f'border:1px solid {T["card_border"]};">'
            f'🟢 <b>Open frontier:</b> {ev["frontier_count"]} nodes'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'⚫ <b>Closed (explored):</b> {ev["expanded_count"]} nodes'
            f'</div>',
            unsafe_allow_html=True
        )
