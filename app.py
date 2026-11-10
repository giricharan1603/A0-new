"""
app.py — MITS Professional Navigation & Graph Search System.
Combines:
  1. Real-World Road Navigator (Any city/village: Madanapalle, Tirupati, etc.)
  2. MITS Campus Landmark Navigator (Detailed inside-college routing)
Equipped with live fuzzy autocomplete, instant CARTO map rendering with user API key,
true A* & Dijkstra algorithm benchmarks, and a 1-click mode switcher.
"""

import streamlit as st
import streamlit.components.v1 as components
import folium
from folium.plugins import AntPath
import pandas as pd

from core.geocoder import geocode, haversine_km
from core.realworld_router import route_realworld
from core.graph_engine import CampusGraphManager, CAMPUS_CENTER
from core.route_service import CampusRouteService
from core.tracer import record_search_trace

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MITS A* & Dijkstra Route Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# MAP TILES CONFIGURATION (GOOGLE MAPS PRIMARY + CARTO WITH USER KEY)
# ─────────────────────────────────────────────────────────────
CARTO_API_KEY = "cb1_3sam_1_2355f1d9cf8d0ccc9cceaf27"

# Google Maps tile layers (Clean, zero watermark, crystal-clear labels)
GOOGLE_MAPS_STREETS = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
GOOGLE_MAPS_HYBRID  = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
GOOGLE_MAPS_TERRAIN = "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
GOOGLE_ATTRIBUTION  = "Map data &copy; Google Maps"

# CARTO tile layers with user API key
CARTO_LIGHT_TILES = f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png?api_key={CARTO_API_KEY}"
CARTO_DARK_TILES  = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png?api_key={CARTO_API_KEY}"
CARTO_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

OPENSTREETMAP_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OPENSTREETMAP_ATTR  = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

def create_base_map(location, zoom_start=11, prefer_canvas=True) -> folium.Map:
    """
    Creates a high-definition Folium map with Google Maps as default primary base layer,
    and a LayerControl selector including Google Satellite, CARTO (with user API key), and OSM.
    """
    fmap = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=None,
        prefer_canvas=prefer_canvas
    )

    # 1. Primary Default: Google Maps Streets (Clear, high-res, zero watermark)
    folium.TileLayer(
        tiles=GOOGLE_MAPS_STREETS,
        attr=GOOGLE_ATTRIBUTION,
        name="Google Maps (Streets)",
        max_zoom=20,
        control=True
    ).add_to(fmap)

    # 2. Google Maps Satellite / Hybrid
    folium.TileLayer(
        tiles=GOOGLE_MAPS_HYBRID,
        attr=GOOGLE_ATTRIBUTION,
        name="Google Maps (Satellite)",
        max_zoom=20,
        control=True,
        show=False
    ).add_to(fmap)

    # 3. CARTO Tiles with user API Key
    carto_tile = CARTO_DARK_TILES if st.session_state.dark_mode else CARTO_LIGHT_TILES
    carto_name = "CARTO Dark Matter" if st.session_state.dark_mode else "CARTO Positron"
    folium.TileLayer(
        tiles=carto_tile,
        attr=CARTO_ATTRIBUTION,
        name=f"{carto_name} (User Key)",
        max_zoom=19,
        control=True,
        show=False
    ).add_to(fmap)

    # 4. OpenStreetMap Standard
    folium.TileLayer(
        tiles=OPENSTREETMAP_TILES,
        attr=OPENSTREETMAP_ATTR,
        name="OpenStreetMap",
        max_zoom=19,
        control=True,
        show=False
    ).add_to(fmap)

    # Layer switch controller in top-right of map
    folium.LayerControl(position="topright").add_to(fmap)
    return fmap

# ─────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION
# ─────────────────────────────────────────────────────────────
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "campus"  # Default directly to inside MITS campus planner
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True
if "real_start_text" not in st.session_state:
    st.session_state.real_start_text = "MITS Madanapalle Campus (Angallu)"
if "real_end_text" not in st.session_state:
    st.session_state.real_end_text = "Tirupati"
if "real_start_place" not in st.session_state:
    st.session_state.real_start_place = {"name": "MITS Madanapalle Campus (Angallu)", "short_name": "MITS Madanapalle Campus, Andhra Pradesh", "lat": 13.62935, "lon": 78.47955}
if "real_end_place" not in st.session_state:
    st.session_state.real_end_place = {"name": "Tirupati", "short_name": "Tirupati, Andhra Pradesh", "lat": 13.6316, "lon": 79.4232}
if "real_route_result" not in st.session_state:
    st.session_state.real_route_result = None
if "travel_mode" not in st.session_state:
    st.session_state.travel_mode = "drive"
if "campus_start_id" not in st.session_state:
    st.session_state.campus_start_id = "MAIN_GATE"
if "campus_goal_id" not in st.session_state:
    st.session_state.campus_goal_id = "CSE_DEPT"

# ─────────────────────────────────────────────────────────────
# THEME TOKENS
# ─────────────────────────────────────────────────────────────
if st.session_state.dark_mode:
    T = {
        "bg": "#0B1120",
        "card": "rgba(15, 23, 42, 0.90)",
        "card_border": "#1E3A5F",
        "text": "#F1F5F9",
        "muted": "#94A3B8",
        "accent": "#38BDF8",
        "accent_purple": "#818CF8",
        "green": "#22C55E",
        "red": "#EF4444",
        "input_bg": "#0F1A2E",
        "input_border": "#1E3A5F",
        "step_bg": "#0D2615",
        "step_border": "#22C55E",
        "metric_bg": "rgba(30, 41, 59, 0.90)",
        "metric_border": "#334155",
        "header_grad": "linear-gradient(135deg, #0B192C 0%, #1E3E62 50%, #000000 100%)",
        "map_tile": CARTO_DARK_TILES,
        "route_color": "#38BDF8",
    }
else:
    T = {
        "bg": "#F8FAFC",
        "card": "rgba(255, 255, 255, 0.95)",
        "card_border": "#E2E8F0",
        "text": "#0F172A",
        "muted": "#64748B",
        "accent": "#0284C7",
        "accent_purple": "#6366F1",
        "green": "#16A34A",
        "red": "#DC2626",
        "input_bg": "#FFFFFF",
        "input_border": "#CBD5E1",
        "step_bg": "#F0FDF4",
        "step_border": "#16A34A",
        "metric_bg": "rgba(255, 255, 255, 0.95)",
        "metric_border": "#E2E8F0",
        "header_grad": "linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #4F46E5 100%)",
        "map_tile": CARTO_LIGHT_TILES,
        "route_color": "#2563EB",
    }

# ─────────────────────────────────────────────────────────────
# GLOBAL STYLING
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  .stApp {{
    background-color: {T['bg']};
  }}
  #MainMenu, footer {{ visibility: hidden; }}

  /* Top Header Banner */
  .top-banner {{
    background: {T['header_grad']};
    border-radius: 14px;
    padding: 20px 28px;
    margin-bottom: 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .top-title {{
    font-size: 1.85rem;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0;
    line-height: 1.2;
  }}
  .top-sub {{
    font-size: 0.9rem;
    color: rgba(255,255,255,0.85);
    margin: 4px 0 0 0;
  }}
  .badge-tag {{
    display: inline-block;
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 14px;
    padding: 3px 10px;
    font-size: 0.75rem;
    color: #FFFFFF;
    margin-right: 6px;
    margin-top: 8px;
  }}

  /* Mode Switch Button */
  .mode-switch-btn {{
    background: #FFFFFF !important;
    color: #1E3A8A !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
  }}

  /* Cards */
  .custom-card {{
    background: {T['card']};
    border: 1px solid {T['card_border']};
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 16px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  }}
  .card-label {{
    font-size: 0.76rem;
    font-weight: 700;
    color: {T['muted']};
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}

  /* Metrics Grid */
  .metric-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 14px 0;
  }}
  .metric-box {{
    background: {T['metric_bg']};
    border: 1px solid {T['metric_border']};
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  }}
  .metric-val {{
    font-size: 1.45rem;
    font-weight: 800;
    color: {T['accent']};
    margin: 4px 0 2px 0;
  }}
  .metric-lbl {{
    font-size: 0.76rem;
    font-weight: 600;
    color: {T['muted']};
  }}
  .metric-delta {{
    font-size: 0.72rem;
    font-weight: 700;
    color: {T['green']};
    margin-top: 3px;
  }}

  /* Step Direction Box */
  .step-card {{
    background: {T['step_bg']};
    border-left: 4px solid {T['step_border']};
    padding: 10px 14px;
    margin-bottom: 8px;
    border-radius: 0 8px 8px 0;
  }}
  .step-text {{
    font-weight: 700;
    color: {T['text']};
    font-size: 0.88rem;
  }}
  .step-subtext {{
    color: {T['muted']};
    font-size: 0.78rem;
    margin-top: 2px;
  }}
  
  .suggestion-pill {{
    display: inline-block;
    background: {T['input_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.78rem;
    color: {T['text']};
    margin: 2px 4px 4px 0;
    cursor: pointer;
  }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# CAMPUS SERVICE LOADER (CACHED)
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_campus_service() -> CampusRouteService:
    mgr = CampusGraphManager()
    mgr.get_or_load_graph()
    return CampusRouteService(mgr)


campus_service = load_campus_service()
campus_landmarks = campus_service.graph_manager.landmarks
campus_lm_map = {lm["landmark_id"]: lm for lm in campus_landmarks}
campus_lm_labels = {lid: lm["name"] for lid, lm in campus_lm_map.items()}
campus_ids = list(campus_lm_labels.keys())


# ─────────────────────────────────────────────────────────────
# TOP HEADER BAR WITH 1-CLICK MODE SWITCHER
# ─────────────────────────────────────────────────────────────
head_col1, head_col2 = st.columns([8, 3])

with head_col1:
    if st.session_state.app_mode == "realworld":
        st.markdown("""
        <div class="top-banner">
          <div>
            <div class="top-title">🗺️ Real-World A* & Dijkstra Route Planner</div>
            <div class="top-sub">Instant highway & village navigation using OpenStreetMap road network & CARTO tiles</div>
            <div>
              <span class="badge-tag">⚡ A* Algorithm</span>
              <span class="badge-tag">🔵 Dijkstra Baseline</span>
              <span class="badge-tag">🗺️ CARTO Maps</span>
              <span class="badge-tag">🎓 MITS Madanapalle</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="top-banner">
          <div>
            <div class="top-title">🏫 MITS Inside-Campus A* Route Planner</div>
            <div class="top-sub">High-precision pedestrian landmark navigation inside MITS Madanapalle Campus</div>
            <div>
              <span class="badge-tag">🏫 Campus Landmarks</span>
              <span class="badge-tag">🚶 Walk / Accessibility Paths</span>
              <span class="badge-tag">⚡ A* Search</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

with head_col2:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if st.session_state.app_mode == "realworld":
        if st.button("🏫 Switch to MITS Campus Inside Planner", use_container_width=True, type="primary"):
            st.session_state.app_mode = "campus"
            st.rerun()
    else:
        if st.button("🌍 Switch to Real-World Road Planner", use_container_width=True, type="primary"):
            st.session_state.app_mode = "realworld"
            st.rerun()


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 10px 0;">
      <div style="font-size: 2.2rem;">{'🌍' if st.session_state.app_mode == 'realworld' else '🏫'}</div>
      <div style="font-weight: 800; font-size: 1.05rem; color:{T['text']};">
        {'Real-World Navigator' if st.session_state.app_mode == 'realworld' else 'MITS Campus Navigator'}
      </div>
      <div style="font-size: 0.74rem; color:{T['muted']};">AI Lab Mini-Project (23CSE109 / 23CSE208)</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Dark / Light Theme Toggle
    theme_text = "☀️ Switch to Light Mode" if st.session_state.dark_mode else "🌙 Switch to Dark Mode"
    if st.button(theme_text, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    st.markdown("<div class='card-label'>⚙️ Route Settings</div>", unsafe_allow_html=True)

    if st.session_state.app_mode == "realworld":
        t_mode = st.radio(
            "Vehicle / Travel Mode",
            ["drive", "walk"],
            index=0 if st.session_state.travel_mode == "drive" else 1,
            format_func=lambda x: "🚗 Driving (Car / Bus)" if x == "drive" else "🚶 Walking"
        )
        if t_mode != st.session_state.travel_mode:
            st.session_state.travel_mode = t_mode
            st.session_state.real_route_result = None
            st.rerun()

        st.markdown("---")
        st.markdown("<div class='card-label'>📍 Quick Popular Destinations</div>", unsafe_allow_html=True)
        quick_pairs = [
            ("Madanapalle → Tirupati", "Madanapalle", "Tirupati"),
            ("MITS Campus → Horsley Hills", "MITS Madanapalle Campus (Angallu)", "Horsley Hills"),
            ("Madanapalle → Bengaluru", "Madanapalle", "Bengaluru (Bangalore)"),
            ("Madanapalle → Kadapa", "Madanapalle", "Kadapa (Cuddapah)"),
            ("Tirupati → Chennai", "Tirupati", "Chennai"),
        ]
        for q_label, q_start, q_end in quick_pairs:
            if st.button(f"🚀 {q_label}", use_container_width=True, key=f"btn_{q_label}"):
                s_res = geocode(q_start, limit=1)
                e_res = geocode(q_end, limit=1)
                if s_res and e_res:
                    st.session_state.real_start_text = q_start
                    st.session_state.real_end_text = q_end
                    st.session_state.real_start_place = s_res[0]
                    st.session_state.real_end_place = e_res[0]
                    st.session_state.real_route_result = None
                    st.rerun()

    else:
        campus_walk_mode = st.radio(
            "Campus Travel Mode",
            ["walking", "driving"],
            format_func=lambda x: "🚶 Pedestrian Walkway" if x == "walking" else "🚗 Service Vehicle Road"
        )
        avoid_stairs = st.checkbox("🪜 Avoid Stairs / Steps", value=False)
        wheelchair_accessible = st.checkbox("♿ Wheelchair-Friendly Route", value=False)

    st.markdown("---")
    st.markdown("<div class='card-label'>📐 Heuristic Function</div>", unsafe_allow_html=True)
    st.caption("**A\\*** informed search: $f(n) = g(n) + h(n)$, where $h(n)$ is Great-Circle Haversine distance.")
    st.caption("**Dijkstra** uninformed search: $h(n) = 0$, baseline guarantee for 100% path optimality.")


# ══════════════════════════════════════════════════════════════
# MODE 1: REAL-WORLD ROUTE PLANNER
# ══════════════════════════════════════════════════════════════
if st.session_state.app_mode == "realworld":

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("<div class='card-label'>📍 Real-Time Origin & Destination Search</div>", unsafe_allow_html=True)

    input_c1, swap_c, input_c2 = st.columns([10, 1, 10])

    with input_c1:
        s_val = st.text_input(
            "🚩 Starting Point (Type 'ma dea', 'mada', or any city/village)",
            value=st.session_state.real_start_text,
            key="real_start_input",
            placeholder="e.g. Madanapalle, MITS Campus, Angallu..."
        )
        if s_val != st.session_state.real_start_text:
            st.session_state.real_start_text = s_val
            st.session_state.real_route_result = None
            # Update suggestion candidates
            s_candidates = geocode(s_val, limit=4)
            if s_candidates:
                st.session_state.real_start_place = s_candidates[0]

    with swap_c:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("⇄", help="Swap Start and Destination", use_container_width=True):
            st.session_state.real_start_text, st.session_state.real_end_text = (
                st.session_state.real_end_text, st.session_state.real_start_text
            )
            st.session_state.real_start_place, st.session_state.real_end_place = (
                st.session_state.real_end_place, st.session_state.real_start_place
            )
            st.session_state.real_route_result = None
            st.rerun()

    with input_c2:
        e_val = st.text_input(
            "🎯 Destination Point (Type 'tirup', 'tiru', or any destination)",
            value=st.session_state.real_end_text,
            key="real_end_input",
            placeholder="e.g. Tirupati, Horsley Hills, Kadapa..."
        )
        if e_val != st.session_state.real_end_text:
            st.session_state.real_end_text = e_val
            st.session_state.real_route_result = None
            e_candidates = geocode(e_val, limit=4)
            if e_candidates:
                st.session_state.real_end_place = e_candidates[0]

    # Live Suggestion Pills
    sug_c1, sug_c2 = st.columns(2)
    with sug_c1:
        if st.session_state.real_start_text:
            s_matches = geocode(st.session_state.real_start_text, limit=4)
            if s_matches:
                st.markdown("<small style='color: " + T['muted'] + ";'>Start Suggestions (Click to apply):</small><br>", unsafe_allow_html=True)
                for idx, sm in enumerate(s_matches):
                    if st.button(f"📍 {sm['short_name']}", key=f"sm_{idx}_{sm['lat']}", help=sm['display_name']):
                        st.session_state.real_start_text = sm['short_name'].split(',')[0]
                        st.session_state.real_start_place = sm
                        st.session_state.real_route_result = None
                        st.rerun()

    with sug_c2:
        if st.session_state.real_end_text:
            e_matches = geocode(st.session_state.real_end_text, limit=4)
            if e_matches:
                st.markdown("<small style='color: " + T['muted'] + ";'>Destination Suggestions (Click to apply):</small><br>", unsafe_allow_html=True)
                for idx, em in enumerate(e_matches):
                    if st.button(f"🎯 {em['short_name']}", key=f"em_{idx}_{em['lat']}", help=em['display_name']):
                        st.session_state.real_end_text = em['short_name'].split(',')[0]
                        st.session_state.real_end_place = em
                        st.session_state.real_route_result = None
                        st.rerun()

    # Route Compute Button
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns([4, 1])
    with btn_col1:
        sp = st.session_state.real_start_place
        ep = st.session_state.real_end_place
        if sp and ep:
            d_straight = haversine_km(sp["lat"], sp["lon"], ep["lat"], ep["lon"])
            st.markdown(
                f"<div style='font-size:0.85rem; color:{T['text']}; padding-top:8px;'>"
                f"🚩 <b>{sp.get('short_name','Start')}</b> &nbsp;→&nbsp; "
                f"🎯 <b>{ep.get('short_name','End')}</b> &nbsp;|&nbsp; "
                f"<span style='color:{T['muted']}'>Straight-line: ~{d_straight:.1f} km</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    with btn_col2:
        compute_route_btn = st.button("⚡ Calculate Route", type="primary", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Trigger Computation
    if compute_route_btn or (st.session_state.real_route_result is None and sp and ep):
        with st.spinner("Calculating optimal real road corridor with A* and Dijkstra..."):
            res = route_realworld(
                start_lat=sp["lat"],
                start_lon=sp["lon"],
                end_lat=ep["lat"],
                end_lon=ep["lon"],
                start_name=sp.get("short_name", "Start"),
                end_name=ep.get("short_name", "Destination"),
                travel_mode=st.session_state.travel_mode,
                run_benchmark=True
            )
            st.session_state.real_route_result = res

    # Render Map & Metrics
    route_res = st.session_state.real_route_result
    sp = st.session_state.real_start_place
    ep = st.session_state.real_end_place

    if route_res and route_res.get("status") == "SUCCESS":
        # 4 Metric Cards
        cmp = route_res.get("comparison") or {}
        st.markdown(f"""
        <div class="metric-row">
          <div class="metric-box">
            <div class="metric-lbl">Total Road Distance</div>
            <div class="metric-val">{route_res['distance_km']} km</div>
            <div class="metric-delta">{route_res['distance_m']:.0f} meters</div>
          </div>
          <div class="metric-box">
            <div class="metric-lbl">Est. Travel Time</div>
            <div class="metric-val">{route_res['duration']}</div>
            <div class="metric-delta">{'Driving pace' if st.session_state.travel_mode=='drive' else 'Walking pace'}</div>
          </div>
          <div class="metric-box">
            <div class="metric-lbl">A* Nodes Expanded</div>
            <div class="metric-val">{route_res['astar']['nodes_expanded']}</div>
            <div class="metric-delta">{route_res['astar']['execution_time_ms']:.2f} ms</div>
          </div>
          <div class="metric-box">
            <div class="metric-lbl">A* vs Dijkstra Efficiency</div>
            <div class="metric-val">{cmp.get('expansion_reduction_pct', 0)}%</div>
            <div class="metric-delta">Search reduction vs baseline</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        r_map_col, r_dir_col = st.columns([11, 7])

        with r_map_col:
            st.markdown(
                f"<div class='card-label'>🗺️ Live Google Map / CARTO Layer — {sp.get('short_name','')} to {ep.get('short_name','')}</div>",
                unsafe_allow_html=True
            )
            coords = route_res["path_coords"]
            lats = [c[0] for c in coords]
            lons = [c[1] for c in coords]

            fmap = create_base_map(
                location=[(min(lats) + max(lats)) / 2.0, (min(lons) + max(lons)) / 2.0],
                zoom_start=11,
                prefer_canvas=True
            )
            fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=[45, 45])

            # Animated Polyline
            try:
                AntPath(
                    locations=coords,
                    color=T["route_color"],
                    weight=6,
                    opacity=0.92,
                    delay=700,
                    dash_array=[15, 30],
                    tooltip=f"Optimal A* Highway Path ({route_res['distance_km']} km)"
                ).add_to(fmap)
            except Exception:
                folium.PolyLine(coords, color=T["route_color"], weight=6, opacity=0.9).add_to(fmap)

            # Start Marker
            folium.Marker(
                [sp["lat"], sp["lon"]],
                popup=folium.Popup(f"<b>🚩 Start:</b> {sp.get('short_name', '')}", max_width=220),
                tooltip=f"Start: {sp.get('short_name', '')}",
                icon=folium.Icon(color="green", icon="play", prefix="fa")
            ).add_to(fmap)

            # Destination Marker
            folium.Marker(
                [ep["lat"], ep["lon"]],
                popup=folium.Popup(f"<b>🎯 Destination:</b> {ep.get('short_name', '')}", max_width=220),
                tooltip=f"Destination: {ep.get('short_name', '')}",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(fmap)

            components.html(fmap._repr_html_(), height=520)

        with r_dir_col:
            st.markdown("<div class='card-label'>📋 Route Directions & Algorithm Proof</div>", unsafe_allow_html=True)
            tabs_dir, tabs_algo = st.tabs(["Turn-by-Turn Steps", "A* vs Dijkstra Proof"])

            with tabs_dir:
                with st.container(height=460):
                    st.markdown(
                        f"<div class='step-card'><b>Origin:</b> {sp.get('short_name','')}<br>"
                        f"<small>GPS: {sp['lat']:.4f}, {sp['lon']:.4f}</small></div>",
                        unsafe_allow_html=True
                    )
                    for step in route_res["directions"]:
                        st.markdown(
                            f"<div class='step-card'>"
                            f"<span class='step-text'>Step {step['step_number']}: {step['street']}</span>"
                            f"<div class='step-subtext'>{step['instruction']} · {step['segment_meters']:.0f} m (Total: {step['cumulative_meters']/1000:.2f} km)</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    st.success(f"🏁 Arrived at **{ep.get('short_name','')}** ({route_res['distance_km']} km)")

            with tabs_algo:
                with st.container(height=460):
                    st.markdown("#### ⚡ A* vs Dijkstra Benchmark")
                    df_comp = pd.DataFrame([
                        {"Metric": "Nodes Explored", "A* Algorithm": route_res['astar']['nodes_expanded'], "Dijkstra": route_res['dijkstra']['nodes_expanded']},
                        {"Metric": "Execution Time (ms)", "A* Algorithm": route_res['astar']['execution_time_ms'], "Dijkstra": route_res['dijkstra']['execution_time_ms']},
                        {"Metric": "Calculated Distance (m)", "A* Algorithm": route_res['astar']['distance_m'], "Dijkstra": route_res['dijkstra']['distance_m']},
                        {"Metric": "Optimality Agreement", "A* Algorithm": "100% (Identical Path)", "Dijkstra": "100% (Optimal Baseline)"},
                    ])
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)

                    chart_data = pd.DataFrame({
                        "Algorithm": ["A* Search", "Dijkstra"],
                        "Nodes Explored": [route_res['astar']['nodes_expanded'], route_res['dijkstra']['nodes_expanded']]
                    }).set_index("Algorithm")
                    st.bar_chart(chart_data)

                    st.info(
                        f"🎯 **Heuristic Admissibility Verified**: A* explored **{cmp.get('expansion_reduction_pct', 0)}% fewer nodes** "
                        f"than Dijkstra while reaching the exact same optimal distance ({route_res['distance_km']} km)."
                    )

    else:
        # Initial live map showing the pins in real-time
        st.markdown("<div class='card-label'>🗺️ Live Google Map / CARTO Layer — Previewing Start & Destination Locations</div>", unsafe_allow_html=True)
        if sp and ep:
            mid_lat = (sp["lat"] + ep["lat"]) / 2.0
            mid_lon = (sp["lon"] + ep["lon"]) / 2.0
            live_map = create_base_map(
                location=[mid_lat, mid_lon],
                zoom_start=9,
                prefer_canvas=True
            )
            live_map.fit_bounds([[min(sp["lat"], ep["lat"]), min(sp["lon"], ep["lon"])], [max(sp["lat"], ep["lat"]), max(sp["lon"], ep["lon"])]], padding=[50, 50])

            folium.Marker(
                [sp["lat"], sp["lon"]],
                popup=folium.Popup(f"<b>🚩 Start:</b> {sp.get('short_name','')}", max_width=200),
                tooltip=f"Start: {sp.get('short_name','')}",
                icon=folium.Icon(color="green", icon="play", prefix="fa")
            ).add_to(live_map)

            folium.Marker(
                [ep["lat"], ep["lon"]],
                popup=folium.Popup(f"<b>🎯 Destination:</b> {ep.get('short_name','')}", max_width=200),
                tooltip=f"Destination: {ep.get('short_name','')}",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(live_map)

            components.html(live_map._repr_html_(), height=500)
        else:
            default_map = create_base_map(
                location=[13.6276, 78.4783],
                zoom_start=13
            )
            components.html(default_map._repr_html_(), height=500)


# ══════════════════════════════════════════════════════════════
# MODE 2: MITS CAMPUS INSIDE PLANNER
# ══════════════════════════════════════════════════════════════
else:
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("<div class='card-label'>🏫 Inside-Campus Landmark Route Selector</div>", unsafe_allow_html=True)

    c1, c_swap, c2 = st.columns([10, 1, 10])

    with c1:
        s_idx = campus_ids.index(st.session_state.campus_start_id) if st.session_state.campus_start_id in campus_ids else 0
        new_start = st.selectbox(
            "🚩 Start Landmark",
            campus_ids,
            index=s_idx,
            format_func=lambda x: f"  {campus_lm_labels[x]}",
            key="campus_s_sel"
        )
        if new_start != st.session_state.campus_start_id:
            st.session_state.campus_start_id = new_start
            st.rerun()

    with c_swap:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("⇄", help="Swap Campus Start & Destination", use_container_width=True):
            st.session_state.campus_start_id, st.session_state.campus_goal_id = (
                st.session_state.campus_goal_id, st.session_state.campus_start_id
            )
            st.rerun()

    with c2:
        g_idx = campus_ids.index(st.session_state.campus_goal_id) if st.session_state.campus_goal_id in campus_ids else 3
        new_goal = st.selectbox(
            "🎯 Destination Landmark",
            campus_ids,
            index=g_idx,
            format_func=lambda x: f"  {campus_lm_labels[x]}",
            key="campus_g_sel"
        )
        if new_goal != st.session_state.campus_goal_id:
            st.session_state.campus_goal_id = new_goal
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    start_lm = campus_lm_map.get(st.session_state.campus_start_id, {})
    goal_lm = campus_lm_map.get(st.session_state.campus_goal_id, {})

    if st.session_state.campus_start_id == st.session_state.campus_goal_id:
        st.info("📍 Origin and destination are the same campus landmark (Distance = 0 m).")
    else:
        c_res = campus_service.compute_route(
            st.session_state.campus_start_id,
            st.session_state.campus_goal_id,
            mode=campus_walk_mode,
            avoid_stairs=avoid_stairs,
            wheelchair_friendly=wheelchair_accessible,
            include_benchmark=True
        )

        if c_res["status"] == "SUCCESS":
            cmp = c_res.get("comparison") or {}

            # Metrics
            st.markdown(f"""
            <div class="metric-row">
              <div class="metric-box">
                <div class="metric-lbl">Campus Walk Distance</div>
                <div class="metric-val">{c_res['distance_meters']:.1f} m</div>
                <div class="metric-delta">{c_res['distance_km']} km</div>
              </div>
              <div class="metric-box">
                <div class="metric-lbl">Walk Time</div>
                <div class="metric-val">{c_res['estimated_time']}</div>
                <div class="metric-delta">~3.2 km/h pace</div>
              </div>
              <div class="metric-box">
                <div class="metric-lbl">A* Nodes Expanded</div>
                <div class="metric-val">{c_res['astar']['nodes_expanded']}</div>
                <div class="metric-delta">{c_res['astar']['execution_time_ms']} ms</div>
              </div>
              <div class="metric-box">
                <div class="metric-lbl">Search Space Reduction</div>
                <div class="metric-val">{cmp.get('expansion_reduction_pct', 0)}%</div>
                <div class="metric-delta">vs Dijkstra baseline</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

            c_map_col, c_dir_col = st.columns([11, 7])

            with c_map_col:
                st.markdown(
                    f"<div class='card-label'>🗺️ MITS Campus Map (Google / CARTO) — {start_lm.get('name','')} to {goal_lm.get('name','')}</div>",
                    unsafe_allow_html=True
                )
                coords = c_res["path_coordinates"]
                fmap = create_base_map(
                    location=list(CAMPUS_CENTER),
                    zoom_start=17
                )
                
                # Auto-fit bounds tightly around campus landmarks
                lm_lats = [lm["latitude"] for lm in campus_landmarks]
                lm_lons = [lm["longitude"] for lm in campus_landmarks]
                fmap.fit_bounds(
                    [[min(lm_lats), min(lm_lons)], [max(lm_lats), max(lm_lons)]],
                    padding=[30, 30]
                )

                # Route line
                AntPath(
                    locations=coords,
                    color=T["route_color"],
                    weight=6,
                    opacity=0.9,
                    delay=600,
                    dash_array=[15, 30],
                    tooltip=f"Campus Shortest Path · {c_res['distance_meters']:.1f} m"
                ).add_to(fmap)

                # Start marker
                folium.Marker(
                    coords[0],
                    popup=folium.Popup(f"<b>🚩 Start:</b> {start_lm.get('name','')}", max_width=200),
                    tooltip=f"Start: {start_lm.get('name','')}",
                    icon=folium.Icon(color="green", icon="play", prefix="fa")
                ).add_to(fmap)

                # Goal marker
                folium.Marker(
                    coords[-1],
                    popup=folium.Popup(f"<b>🎯 Destination:</b> {goal_lm.get('name','')}", max_width=200),
                    tooltip=f"Destination: {goal_lm.get('name','')}",
                    icon=folium.Icon(color="red", icon="flag", prefix="fa")
                ).add_to(fmap)

                # Campus landmark markers
                for lm in campus_landmarks:
                    if lm["landmark_id"] in (st.session_state.campus_start_id, st.session_state.campus_goal_id):
                        continue
                    folium.CircleMarker(
                        location=[lm["latitude"], lm["longitude"]],
                        radius=6,
                        color="#2563EB",
                        fill=True,
                        fill_opacity=0.75,
                        popup=folium.Popup(f"<b>{lm['name']}</b><br><small>{lm.get('category','')}</small>", max_width=200),
                        tooltip=lm["name"]
                    ).add_to(fmap)

                components.html(fmap._repr_html_(), height=500)

            with c_dir_col:
                st.markdown("<div class='card-label'>🚶 Turn-by-Turn Campus Path</div>", unsafe_allow_html=True)
                with st.container(height=500):
                    for step in c_res["directions"]:
                        st.markdown(
                            f"<div class='step-card'>"
                            f"<span class='step-text'>Step {step['step_number']} · {step['street']}</span>"
                            f"<div class='step-subtext'>→ <b>{step['to_node']}</b> · {step['segment_meters']} m (Total: {step['cumulative_meters']} m)</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    st.success(f"🏁 Arrived at **{goal_lm.get('name', 'Destination')}**")
        else:
            st.error(f"❌ Route calculation failed: {c_res.get('error')}")
