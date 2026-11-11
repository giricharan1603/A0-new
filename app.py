"""
app.py — MITS Professional Navigation & Graph Search System.
Combines:
  1. Real-World Road Navigator (Any city/village: Madanapalle, Tirupati, etc.)
  2. MITS Campus Landmark Navigator (Detailed inside-college routing for all 17 campus blocks)
Equipped with live fuzzy autocomplete, instant Google Maps / CARTO rendering,
pure A* informed search, multi-path visualization with green shortest-path highlight,
and draggable pin repositioning.
"""

import os
import html
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
    page_title="MITS A* Campus & Road Route Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# MAP TILES CONFIGURATION (GOOGLE MAPS PRIMARY + CARTO WITH ENV / PUBLIC SUPPORT)
# ─────────────────────────────────────────────────────────────
CARTO_API_KEY = os.getenv("CARTO_API_KEY", "")
carto_key_param = f"?api_key={CARTO_API_KEY}" if CARTO_API_KEY else ""

# Google Maps tile layers
GOOGLE_MAPS_STREETS = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
GOOGLE_MAPS_HYBRID  = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
GOOGLE_MAPS_TERRAIN = "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
GOOGLE_ATTRIBUTION  = "Map data &copy; Google Maps"

# CARTO tile layers
CARTO_LIGHT_TILES = f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png{carto_key_param}"
CARTO_DARK_TILES  = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png{carto_key_param}"
CARTO_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

OPENSTREETMAP_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
OPENSTREETMAP_ATTR  = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'


def create_base_map(location, zoom_start=11, prefer_canvas=True) -> folium.Map:
    """
    Creates a high-definition Folium map with Google Maps as default primary base layer,
    and a LayerControl selector including Google Satellite, CARTO, and OSM.
    """
    fmap = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=None,
        prefer_canvas=prefer_canvas
    )

    # 1. Primary Default: Google Maps Streets
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

    # 3. CARTO Tiles
    carto_tile = CARTO_DARK_TILES if st.session_state.get("dark_mode", False) else CARTO_LIGHT_TILES
    carto_name = "CARTO Dark Matter" if st.session_state.get("dark_mode", False) else "CARTO Positron"
    folium.TileLayer(
        tiles=carto_tile,
        attr=CARTO_ATTRIBUTION,
        name=carto_name,
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

    folium.LayerControl(position="topright").add_to(fmap)
    return fmap


# ─────────────────────────────────────────────────────────────
# STATE INITIALIZATION (SINGLE CLEAN SOURCE OF TRUTH)
# ─────────────────────────────────────────────────────────────
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "campus"  # 'realworld' or 'campus'
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "travel_mode" not in st.session_state:
    st.session_state.travel_mode = "drive"
if "campus_start_id" not in st.session_state:
    st.session_state.campus_start_id = "MAIN_ENTRANCE"
if "campus_goal_id" not in st.session_state:
    st.session_state.campus_goal_id = "ADMIN_BLOCK"

# Real-world single-source text state bound to widgets
if "origin_query" not in st.session_state:
    st.session_state.origin_query = "Madanapalle"
if "dest_query" not in st.session_state:
    st.session_state.dest_query = "Tirupati"

# Matched place dictionaries
if "real_start_place" not in st.session_state:
    st.session_state.real_start_place = {"name": "Madanapalle", "short_name": "Madanapalle, AP", "lat": 13.5558, "lon": 78.5015}
if "real_end_place" not in st.session_state:
    st.session_state.real_end_place = {"name": "Tirupati", "short_name": "Tirupati, AP", "lat": 13.6316, "lon": 79.4232}
if "real_route_result" not in st.session_state:
    st.session_state.real_route_result = None


# ─────────────────────────────────────────────────────────────
# LIFECYCLE SAFE CALLBACKS (RUN BEFORE WIDGETS INSTANTIATE)
# ─────────────────────────────────────────────────────────────
def on_origin_change():
    """Callback triggered on origin text edit."""
    q = st.session_state.origin_query.strip()
    if q:
        matches = geocode(q, limit=4)
        if matches:
            st.session_state.real_start_place = matches[0]
    st.session_state.real_route_result = None


def on_dest_change():
    """Callback triggered on destination text edit."""
    q = st.session_state.dest_query.strip()
    if q:
        matches = geocode(q, limit=4)
        if matches:
            st.session_state.real_end_place = matches[0]
    st.session_state.real_route_result = None


def swap_locations():
    """Safely swaps origin and destination before widgets render."""
    orig = st.session_state.origin_query
    dest = st.session_state.dest_query
    st.session_state.origin_query = dest
    st.session_state.dest_query = orig
    st.session_state.real_start_place, st.session_state.real_end_place = (
        st.session_state.real_end_place, st.session_state.real_start_place
    )
    st.session_state.real_route_result = None


def apply_quick_destination(sp, ep):
    """Safely applies quick destination pair before widgets render."""
    st.session_state.origin_query = sp["name"]
    st.session_state.dest_query = ep["name"]
    st.session_state.real_start_place = sp
    st.session_state.real_end_place = ep
    st.session_state.real_route_result = route_realworld(
        start_lat=sp["lat"],
        start_lon=sp["lon"],
        end_lat=ep["lat"],
        end_lon=ep["lon"],
        start_name=sp.get("short_name", "Start"),
        end_name=ep.get("short_name", "Destination"),
        travel_mode=st.session_state.travel_mode
    )


def apply_suggestion(target, place):
    """Safely applies suggestion pill before widgets render."""
    p_name = place["short_name"].split(",")[0].strip()
    if target == "start":
        st.session_state.origin_query = p_name
        st.session_state.real_start_place = place
    else:
        st.session_state.dest_query = p_name
        st.session_state.real_end_place = place
    st.session_state.real_route_result = None


# ─────────────────────────────────────────────────────────────
# THEME TOKENS
# ─────────────────────────────────────────────────────────────
if st.session_state.dark_mode:
    T = {
        "bg": "#050B1E",
        "card": "rgba(10, 18, 48, 0.96)",
        "card_border": "#0000FF",
        "text": "#FFFFFF",
        "muted": "#9BB2FF",
        "accent": "#3366FF",
        "green": "#00E676",
        "red": "#FF3B30",
        "step_bg": "#0B1536",
        "metric_bg": "rgba(10, 18, 48, 0.96)",
        "metric_border": "#0000FF",
        "header_grad": "linear-gradient(135deg, #0000FF 0%, #0012A3 60%, #050A30 100%)",
        "route_color": "#00C853",
    }
else:
    T = {
        "bg": "#F5F8FF",
        "card": "#FFFFFF",
        "card_border": "#D5E0FF",
        "text": "#0A0E27",
        "muted": "#4A5568",
        "accent": "#0000FF",
        "green": "#00A854",
        "red": "#E02020",
        "step_bg": "#F0F4FF",
        "metric_bg": "#FFFFFF",
        "metric_border": "#D5E0FF",
        "header_grad": "linear-gradient(135deg, #0000FF 0%, #0018D4 50%, #0000CC 100%)",
        "route_color": "#00C853",
    }

# ─────────────────────────────────────────────────────────────
# GLOBAL STYLING
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  .stApp {{
    background-color: {T['bg']};
    color: {T['text']};
  }}
  #MainMenu, footer {{ visibility: hidden; }}

  .top-banner {{
    background: {T['header_grad']};
    border-radius: 14px;
    padding: 22px 30px;
    margin-bottom: 20px;
    box-shadow: 0 8px 26px rgba(0, 0, 255, 0.22);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid rgba(255, 255, 255, 0.25);
  }}
  .top-title {{
    font-size: 1.9rem;
    font-weight: 800;
    color: #FFFFFF;
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.02em;
  }}
  .top-sub {{
    font-size: 0.92rem;
    color: rgba(255, 255, 255, 0.92);
    margin: 5px 0 0 0;
  }}
  .badge-tag {{
    display: inline-block;
    background: rgba(255, 255, 255, 0.18);
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 0.76rem;
    color: #FFFFFF;
    font-weight: 600;
    margin-right: 6px;
    margin-top: 10px;
  }}

  .stButton > button {{
    border-radius: 8px !important;
    font-weight: 700 !important;
    transition: all 0.2s ease !important;
  }}
  .stButton > button[kind="primary"] {{
    background-color: #0000FF !important;
    color: #FFFFFF !important;
    border: 1.5px solid #0000FF !important;
    box-shadow: 0 4px 14px rgba(0, 0, 255, 0.28) !important;
  }}
  .stButton > button[kind="primary"]:hover {{
    background-color: #0000CC !important;
    border-color: #0000CC !important;
    box-shadow: 0 6px 18px rgba(0, 0, 255, 0.40) !important;
    color: #FFFFFF !important;
  }}

  section[data-testid="stSidebar"] {{
    background-color: #FFFFFF !important;
    border-right: 1.5px solid #D5E0FF !important;
  }}

  .custom-card {{
    background: {T['card']};
    border: 1.5px solid {T['card_border']};
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 18px;
    box-shadow: 0 4px 18px rgba(0, 0, 255, 0.05);
  }}
  .card-label {{
    font-size: 0.78rem;
    font-weight: 800;
    color: #0000FF;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 10px;
  }}

  .metric-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 16px 0;
  }}
  .metric-box {{
    background: {T['metric_bg']};
    border: 1.5px solid {T['metric_border']};
    border-top: 4px solid #0000FF;
    border-radius: 12px;
    padding: 16px 18px;
    text-align: center;
    box-shadow: 0 4px 16px rgba(0, 0, 255, 0.06);
  }}
  .metric-val {{
    font-size: 1.6rem;
    font-weight: 800;
    color: #0000FF;
    margin: 4px 0 2px 0;
  }}
  .metric-lbl {{
    font-size: 0.74rem;
    font-weight: 700;
    color: #4A5568;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .metric-delta {{
    font-size: 0.74rem;
    font-weight: 700;
    color: #0000FF;
    margin-top: 3px;
  }}

  .step-card {{
    background: {T['step_bg']};
    border: 1px solid #D5E0FF;
    border-left: 5px solid #00C853;
    padding: 12px 16px;
    margin-bottom: 10px;
    border-radius: 0 8px 8px 0;
    box-shadow: 0 2px 8px rgba(0, 0, 255, 0.03);
  }}
  .step-text {{
    font-weight: 700;
    color: #0A0E27;
    font-size: 0.90rem;
  }}
  .step-subtext {{
    color: #4B5563;
    font-size: 0.78rem;
    margin-top: 2px;
  }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# CAMPUS SERVICE LOADER (CACHED)
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_campus_service() -> CampusRouteService:
    mgr = CampusGraphManager()
    mgr.get_or_load_graph(force_refresh=True)
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
            <div class="top-title">🗺️ Real-World A* Route Planner</div>
            <div class="top-sub">Instant highway, town & village navigation using OpenStreetMap road network & Google/CARTO tiles</div>
            <div>
              <span class="badge-tag">⚡ A* Informed Search</span>
              <span class="badge-tag">🟢 Shortest Path Highlight</span>
              <span class="badge-tag">🏘️ Village & City Bypass Steps</span>
              <span class="badge-tag">📍 Draggable Pins</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="top-banner">
          <div>
            <div class="top-title">🏫 MITS Inside-Campus A* Route Planner</div>
            <div class="top-sub">High-precision pedestrian landmark navigation across all 17 buildings in MITS Madanapalle Campus</div>
            <div>
              <span class="badge-tag">🏫 17 Campus Landmarks</span>
              <span class="badge-tag">🚶 Walkways & Corridors</span>
              <span class="badge-tag">⚡ A* Shortest Route in Green</span>
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
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
      <div style="font-size: 2.2rem;">{'🌍' if st.session_state.app_mode == 'realworld' else '🏫'}</div>
      <div>
        <div style="font-weight: 800; font-size: 1.1rem; color: #0000FF;">
          {'Real-World Navigator' if st.session_state.app_mode == 'realworld' else 'MITS Campus Navigator'}
        </div>
        <div style="font-size: 0.74rem; color: #4B5563;">
          {'Intercity & Village Road Network' if st.session_state.app_mode == 'realworld' else '17 Ground-Truth Campus Blocks'}
        </div>
      </div>
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
            ["drive", "bike"],
            index=0 if st.session_state.travel_mode == "drive" else 1,
            format_func=lambda x: "🚗 Driving (Car / Bus)" if x == "drive" else "🏍️ Bike / Two-Wheeler"
        )
        if t_mode != st.session_state.travel_mode:
            st.session_state.travel_mode = t_mode
            st.session_state.real_route_result = None
            st.rerun()

        st.markdown("---")
        st.markdown("<div class='card-label'>📍 Quick Popular Destinations</div>", unsafe_allow_html=True)
        quick_pairs = [
            ("Madanapalle → Tirupati",
             {"name": "Madanapalle", "short_name": "Madanapalle, AP", "display_name": "Madanapalle, Andhra Pradesh", "lat": 13.5558, "lon": 78.5015},
             {"name": "Tirupati",    "short_name": "Tirupati, AP",    "display_name": "Tirupati, Andhra Pradesh",    "lat": 13.6316, "lon": 79.4232}),
            ("MITS → Horsley Hills",
             {"name": "MITS Campus", "short_name": "MITS Campus (Angallu)", "display_name": "MITS Madanapalle Campus", "lat": 13.633266, "lon": 78.479932},
             {"name": "Horsley Hills", "short_name": "Horsley Hills, AP", "display_name": "Horsley Hills, AP", "lat": 13.6500, "lon": 78.3900}),
            ("Madanapalle → Bengaluru",
             {"name": "Madanapalle", "short_name": "Madanapalle, AP", "display_name": "Madanapalle, Andhra Pradesh", "lat": 13.5558, "lon": 78.5015},
             {"name": "Bengaluru",   "short_name": "Bengaluru, KA",   "display_name": "Bengaluru, Karnataka",         "lat": 12.9716, "lon": 77.5946}),
            ("Madanapalle → Kadapa",
             {"name": "Madanapalle", "short_name": "Madanapalle, AP", "display_name": "Madanapalle, Andhra Pradesh", "lat": 13.5558, "lon": 78.5015},
             {"name": "Kadapa",      "short_name": "Kadapa, AP",      "display_name": "Kadapa (Cuddapah), AP",        "lat": 14.4674, "lon": 78.8241}),
            ("Tirupati → Chennai",
             {"name": "Tirupati",  "short_name": "Tirupati, AP",  "display_name": "Tirupati, Andhra Pradesh", "lat": 13.6316, "lon": 79.4232},
             {"name": "Chennai",   "short_name": "Chennai, TN",   "display_name": "Chennai, Tamil Nadu",      "lat": 13.0827, "lon": 80.2707}),
        ]
        for q_label, q_sp, q_ep in quick_pairs:
            st.button(
                f"🚀 {q_label}",
                use_container_width=True,
                key=f"btn_{q_label}",
                on_click=apply_quick_destination,
                args=(q_sp, q_ep)
            )

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


# ══════════════════════════════════════════════════════════════
# MODE 1: REAL-WORLD ROUTE PLANNER
# ══════════════════════════════════════════════════════════════
if st.session_state.app_mode == "realworld":

    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("<div class='card-label'>📍 Origin & Destination Search</div>", unsafe_allow_html=True)

    input_c1, swap_c, input_c2 = st.columns([10, 1, 10])

    with input_c1:
        st.text_input(
            "🚩 Starting Point (Type town, village, or landmark)",
            key="origin_query",
            on_change=on_origin_change,
            placeholder="e.g. Madanapalle, MITS Campus, Angallu..."
        )

    with swap_c:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.button("⇄", help="Swap Start and Destination", use_container_width=True, on_click=swap_locations)

    with input_c2:
        st.text_input(
            "🎯 Destination Point (Type town, village, or landmark)",
            key="dest_query",
            on_change=on_dest_change,
            placeholder="e.g. Tirupati, Horsley Hills, Kadapa..."
        )

    # Live Suggestion Pills (Rendered dynamically below input boxes)
    sug_c1, sug_c2 = st.columns(2)
    with sug_c1:
        q_start = st.session_state.origin_query.strip()
        if q_start:
            s_matches = geocode(q_start, limit=4)
            if s_matches:
                st.markdown("<small style='color: #4A5568;'>💡 Start Suggestions (Click to apply):</small>", unsafe_allow_html=True)
                cols = st.columns(len(s_matches))
                for idx, sm in enumerate(s_matches):
                    with cols[idx]:
                        label = sm['short_name'].split(',')[0].strip()
                        st.button(
                            f"📍 {label}",
                            key=f"sug_s_{idx}_{sm['lat']}",
                            on_click=apply_suggestion,
                            args=("start", sm),
                            help=sm['display_name'],
                            use_container_width=True
                        )

    with sug_c2:
        q_end = st.session_state.dest_query.strip()
        if q_end:
            e_matches = geocode(q_end, limit=4)
            if e_matches:
                st.markdown("<small style='color: #4A5568;'>💡 Destination Suggestions (Click to apply):</small>", unsafe_allow_html=True)
                cols_e = st.columns(len(e_matches))
                for idx, em in enumerate(e_matches):
                    with cols_e[idx]:
                        label = em['short_name'].split(',')[0].strip()
                        st.button(
                            f"🎯 {label}",
                            key=f"sug_e_{idx}_{em['lat']}",
                            on_click=apply_suggestion,
                            args=("dest", em),
                            help=em['display_name'],
                            use_container_width=True
                        )

    # Route Summary & Compute Button
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns([4, 1])
    with btn_col1:
        sp = st.session_state.real_start_place
        ep = st.session_state.real_end_place
        if sp and ep:
            d_straight = haversine_km(sp["lat"], sp["lon"], ep["lat"], ep["lon"])
            safe_sp = html.escape(sp.get('short_name', 'Start'))
            safe_ep = html.escape(ep.get('short_name', 'End'))
            st.markdown(
                f"<div style='font-size:0.85rem; color:{T['text']}; padding-top:8px;'>"
                f"🚩 <b>{safe_sp}</b> &nbsp;→&nbsp; "
                f"🎯 <b>{safe_ep}</b> &nbsp;|&nbsp; "
                f"<span style='color:{T['muted']}'>Straight-line: ~{d_straight:.1f} km</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    with btn_col2:
        compute_route_btn = st.button("⚡ Calculate Route", type="primary", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Trigger Computation
    if compute_route_btn or (st.session_state.real_route_result is None and sp and ep):
        with st.spinner("Calculating optimal route with A* informed search..."):
            res = route_realworld(
                start_lat=sp["lat"],
                start_lon=sp["lon"],
                end_lat=ep["lat"],
                end_lon=ep["lon"],
                start_name=sp.get("short_name", "Start"),
                end_name=ep.get("short_name", "Destination"),
                travel_mode=st.session_state.travel_mode
            )
            st.session_state.real_route_result = res

    # Render Map & Metrics
    route_res = st.session_state.real_route_result
    sp = st.session_state.real_start_place
    ep = st.session_state.real_end_place

    if route_res and route_res.get("status") == "SUCCESS":
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
            <div class="metric-delta">{'Driving pace (Car/Bus)' if st.session_state.travel_mode=='drive' else 'Bike pace (~40 km/h)'}</div>
          </div>
          <div class="metric-box">
            <div class="metric-lbl">A* Nodes Expanded</div>
            <div class="metric-val">{route_res['astar']['nodes_expanded']}</div>
            <div class="metric-delta">{route_res['astar']['execution_time_ms']:.2f} ms</div>
          </div>
          <div class="metric-box">
            <div class="metric-lbl">Graph Size</div>
            <div class="metric-val">{route_res.get('graph_nodes', '—')}</div>
            <div class="metric-delta">{route_res.get('graph_edges', '—')} edges</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        r_map_col, r_dir_col = st.columns([11, 7])

        with r_map_col:
            safe_sname = html.escape(sp.get('short_name', 'Origin'))
            safe_ename = html.escape(ep.get('short_name', 'Destination'))
            st.markdown(
                f"<div class='card-label'>🗺️ Live Route Map & Pin Drag — {safe_sname} to {safe_ename}</div>",
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

            # 1. Draw available alternative paths FIRST in dashed grey
            alternatives = route_res.get("alternatives", [])
            for i, alt in enumerate(alternatives):
                folium.PolyLine(
                    alt["coords"],
                    color="#718096",
                    weight=4,
                    opacity=0.75,
                    dash_array="8 6",
                    tooltip=f"Alternative Route {i+1}: {alt.get('distance_km','?')} km"
                ).add_to(fmap)

            # 2. Highlight the SHORTEST PATH in vibrant GREEN (#00C853)
            try:
                AntPath(
                    locations=coords,
                    color="#00C853",
                    pulse_color="#B9F6CA",
                    weight=7,
                    opacity=0.95,
                    delay=600,
                    dash_array=[12, 24],
                    tooltip=f"⚡ Optimal Shortest A* Path: {route_res['distance_km']} km"
                ).add_to(fmap)
            except Exception:
                folium.PolyLine(coords, color="#00C853", weight=7, opacity=0.95).add_to(fmap)

            # 3. Add Draggable Start Pin (Green)
            folium.Marker(
                [sp["lat"], sp["lon"]],
                popup=folium.Popup(f"<b>🚩 Start:</b> {safe_sname}<br><small>💡 Drag pin to reposition on map</small>", max_width=240),
                tooltip=f"Start: {safe_sname} (Draggable Pin)",
                draggable=True,
                icon=folium.Icon(color="green", icon="play", prefix="fa")
            ).add_to(fmap)

            # 4. Add Draggable Destination Pin (Red)
            folium.Marker(
                [ep["lat"], ep["lon"]],
                popup=folium.Popup(f"<b>🎯 Destination:</b> {safe_ename}<br><small>💡 Drag pin to reposition on map</small>", max_width=240),
                tooltip=f"Destination: {safe_ename} (Draggable Pin)",
                draggable=True,
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(fmap)

            # 5. Route Paths Legend
            legend_html = f"""
            <div style="position:fixed;bottom:25px;left:25px;z-index:9999;background:white;
                        padding:10px 14px;border-radius:8px;border:1.5px solid #CBD5E0;
                        box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:0.82rem;font-family:sans-serif;">
              <b style="color:#1A202C;">Route Paths Legend</b><br>
              <span style="color:#00C853;font-size:1.2rem;font-weight:bold;">&#9644;&#9644;</span> <b style="color:#00C853;">Shortest Path (Green)</b><br>
              <span style="color:#718096;font-size:1.1rem;font-weight:bold;">- - -</span> <span style="color:#4A5568;">Alternative Available Routes ({len(alternatives)})</span>
            </div>"""
            fmap.get_root().html.add_child(folium.Element(legend_html))

            components.html(fmap._repr_html_(), height=520)

            # Pin drag / coordinate fine-tune controls
            st.markdown(
                "<div style='background:#F0F4FF; border:1px solid #C7D7FE; border-radius:8px; padding:12px 16px; margin-top:8px;'>"
                "<b style='color:#0000FF;'>📌 Pin Position Adjuster</b><br>"
                "<small style='color:#4A5568;'>Drag pins directly on the map above, or adjust coordinates below and click Apply to recalculate the route.</small>"
                "</div>",
                unsafe_allow_html=True
            )
            pin_c1, pin_c2, pin_c3 = st.columns([5, 5, 3])
            with pin_c1:
                new_slat = st.number_input("🚩 Start Latitude",  value=float(sp["lat"]), format="%.6f", step=0.001, key="pin_start_lat")
                new_slon = st.number_input("🚩 Start Longitude", value=float(sp["lon"]), format="%.6f", step=0.001, key="pin_start_lon")
            with pin_c2:
                new_elat = st.number_input("🎯 Dest. Latitude",  value=float(ep["lat"]), format="%.6f", step=0.001, key="pin_end_lat")
                new_elon = st.number_input("🎯 Dest. Longitude", value=float(ep["lon"]), format="%.6f", step=0.001, key="pin_end_lon")
            with pin_c3:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                if st.button("📍 Apply\nPin Positions", type="primary", use_container_width=True, key="apply_pin_btn"):
                    st.session_state.real_start_place = {
                        **sp, "lat": new_slat, "lon": new_slon,
                        "short_name": f"Adjusted Pin ({new_slat:.4f}, {new_slon:.4f})"
                    }
                    st.session_state.real_end_place = {
                        **ep, "lat": new_elat, "lon": new_elon,
                        "short_name": f"Adjusted Pin ({new_elat:.4f}, {new_elon:.4f})"
                    }
                    st.session_state.origin_query = f"{new_slat:.4f}, {new_slon:.4f}"
                    st.session_state.dest_query = f"{new_elat:.4f}, {new_elon:.4f}"
                    st.session_state.real_route_result = None
                    st.rerun()

        with r_dir_col:
            st.markdown("<div class='card-label'>🏘️ Turn-by-Turn Steps (Bypass Villages & Cities)</div>", unsafe_allow_html=True)
            if alternatives:
                alt_info = "  |  ".join([f"Alt {i+1}: {a.get('distance_km','?')} km" for i, a in enumerate(alternatives)])
                st.caption(f"🛤️ **{len(alternatives)} alternative route(s) in dashed grey** on the map  ·  {alt_info}")
            with st.container(height=560):
                st.markdown(
                    f"<div class='step-card'><b>🚩 Origin:</b> {safe_sname}<br>"
                    f"<small style='color:#0000FF;'>GPS: {sp['lat']:.4f}, {sp['lon']:.4f}</small></div>",
                    unsafe_allow_html=True
                )
                for step in route_res["directions"]:
                    safe_street = html.escape(step['street'])
                    safe_instr = html.escape(step['instruction'])
                    st.markdown(
                        f"<div class='step-card'>"
                        f"<span class='step-text'>📍 Step {step['step_number']}: {safe_street}</span>"
                        f"<div class='step-subtext'><b>{safe_instr}</b> &nbsp;·&nbsp; {step['segment_meters']:.0f} m (Cumulative: {step['cumulative_meters']/1000:.2f} km)</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                st.success(f"🏁 Arrived at **{safe_ename}** ({route_res['distance_km']} km)")
                st.info(f"⚡ A* Search: **{route_res['astar']['nodes_expanded']} nodes expanded** in {route_res['astar']['execution_time_ms']:.2f} ms")

    else:
        st.markdown("<div class='card-label'>🗺️ Live Map Preview</div>", unsafe_allow_html=True)
        if sp and ep:
            mid_lat = (sp["lat"] + ep["lat"]) / 2.0
            mid_lon = (sp["lon"] + ep["lon"]) / 2.0
            live_map = create_base_map(location=[mid_lat, mid_lon], zoom_start=9)
            live_map.fit_bounds([[min(sp["lat"], ep["lat"]), min(sp["lon"], ep["lon"])], [max(sp["lat"], ep["lat"]), max(sp["lon"], ep["lon"])]], padding=[50, 50])

            folium.Marker(
                [sp["lat"], sp["lon"]],
                popup=folium.Popup(f"<b>🚩 Start:</b> {html.escape(sp.get('short_name',''))}", max_width=200),
                tooltip="🚩 Start Pin (Draggable)",
                draggable=True,
                icon=folium.Icon(color="green", icon="play", prefix="fa")
            ).add_to(live_map)

            folium.Marker(
                [ep["lat"], ep["lon"]],
                popup=folium.Popup(f"<b>🎯 Destination:</b> {html.escape(ep.get('short_name',''))}", max_width=200),
                tooltip="🎯 Destination Pin (Draggable)",
                draggable=True,
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(live_map)

            components.html(live_map._repr_html_(), height=460)


# ══════════════════════════════════════════════════════════════
# MODE 2: MITS CAMPUS INSIDE PLANNER
# ══════════════════════════════════════════════════════════════
else:
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("<div class='card-label'>🏫 Inside-Campus Landmark Route Selector (All 17 Blocks)</div>", unsafe_allow_html=True)

    c1, c_swap, c2 = st.columns([10, 1, 10])

    def swap_campus():
        st.session_state.campus_start_id, st.session_state.campus_goal_id = (
            st.session_state.campus_goal_id, st.session_state.campus_start_id
        )

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
        st.button("⇄", help="Swap Campus Start & Destination", use_container_width=True, on_click=swap_campus)

    with c2:
        default_g_idx = campus_ids.index("ADMIN_BLOCK") if "ADMIN_BLOCK" in campus_ids else 0
        g_idx = campus_ids.index(st.session_state.campus_goal_id) if st.session_state.campus_goal_id in campus_ids else default_g_idx
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
            wheelchair_friendly=wheelchair_accessible
        )

        if c_res["status"] == "SUCCESS":
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
                <div class="metric-delta">{c_res['astar']['execution_time_ms']:.2f} ms</div>
              </div>
              <div class="metric-box">
                <div class="metric-lbl">A* Execution Time</div>
                <div class="metric-val">{c_res['astar'].get('execution_time_ms', 0):.2f} ms</div>
                <div class="metric-delta">Informed Haversine search</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

            c_map_col, c_dir_col = st.columns([11, 7])

            with c_map_col:
                safe_slm = html.escape(start_lm.get('name', 'Origin'))
                safe_glm = html.escape(goal_lm.get('name', 'Destination'))
                st.markdown(
                    f"<div class='card-label'>🗺️ MITS Campus Map — {safe_slm} to {safe_glm}</div>",
                    unsafe_allow_html=True
                )
                coords = c_res["path_coordinates"]
                fmap = create_base_map(
                    location=list(CAMPUS_CENTER),
                    zoom_start=17
                )

                # Fit bounds to campus buildings
                lm_lats = [lm["latitude"] for lm in campus_landmarks]
                lm_lons = [lm["longitude"] for lm in campus_landmarks]
                fmap.fit_bounds([[min(lm_lats), min(lm_lons)], [max(lm_lats), max(lm_lons)]], padding=[35, 35])

                # 1. Draw available alternative campus pathways in dashed grey
                campus_alts = c_res.get("alternatives", [])
                for i, alt in enumerate(campus_alts):
                    folium.PolyLine(
                        alt["coords"],
                        color="#718096",
                        weight=4,
                        opacity=0.75,
                        dash_array="6 8",
                        tooltip=f"Alternative Pathway {i+1}: {alt['distance_m']:.1f} m"
                    ).add_to(fmap)

                # 2. Highlight SHORTEST campus path in vibrant GREEN (#00C853)
                AntPath(
                    locations=coords,
                    color="#00C853",
                    pulse_color="#B9F6CA",
                    weight=6,
                    opacity=0.95,
                    delay=600,
                    dash_array=[15, 30],
                    tooltip=f"⚡ Campus Shortest Path: {c_res['distance_meters']:.1f} m"
                ).add_to(fmap)

                # Campus map legend
                c_legend_html = f"""
                <div style="position:fixed;bottom:25px;left:25px;z-index:9999;background:white;
                            padding:10px 14px;border-radius:8px;border:1.5px solid #CBD5E0;
                            box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:0.82rem;font-family:sans-serif;">
                  <b style="color:#1A202C;">Campus Paths Legend</b><br>
                  <span style="color:#00C853;font-size:1.2rem;font-weight:bold;">&#9644;&#9644;</span> <b style="color:#00C853;">Shortest Path (Green)</b><br>
                  <span style="color:#718096;font-size:1.1rem;font-weight:bold;">- - -</span> <span style="color:#4A5568;">Alternative Pathways ({len(campus_alts)})</span>
                </div>"""
                fmap.get_root().html.add_child(folium.Element(c_legend_html))

                # Start marker
                folium.Marker(
                    coords[0],
                    popup=folium.Popup(f"<b>🚩 Start:</b> {safe_slm}", max_width=200),
                    tooltip=f"Start: {safe_slm}",
                    icon=folium.Icon(color="green", icon="play", prefix="fa")
                ).add_to(fmap)

                # Goal marker
                folium.Marker(
                    coords[-1],
                    popup=folium.Popup(f"<b>🎯 Destination:</b> {safe_glm}", max_width=200),
                    tooltip=f"Destination: {safe_glm}",
                    icon=folium.Icon(color="red", icon="flag", prefix="fa")
                ).add_to(fmap)

                # Campus landmark markers for all 17 buildings
                for lm in campus_landmarks:
                    if lm["landmark_id"] in (st.session_state.campus_start_id, st.session_state.campus_goal_id):
                        continue
                    folium.CircleMarker(
                        location=[lm["latitude"], lm["longitude"]],
                        radius=6,
                        color="#0000FF",
                        fill=True,
                        fill_opacity=0.75,
                        popup=folium.Popup(f"<b>{html.escape(lm['name'])}</b><br><small>{html.escape(lm.get('category',''))}</small>", max_width=200),
                        tooltip=lm["name"]
                    ).add_to(fmap)

                components.html(fmap._repr_html_(), height=500)

            with c_dir_col:
                st.markdown("<div class='card-label'>🚶 Turn-by-Turn Campus Path</div>", unsafe_allow_html=True)
                if campus_alts:
                    alt_info = "  |  ".join([f"Alt {i+1}: {a['distance_m']:.1f} m" for i, a in enumerate(campus_alts)])
                    st.caption(f"🛤️ **{len(campus_alts)} alternative pathway(s) in dashed grey**  ·  {alt_info}")
                with st.container(height=500):
                    for step in c_res["directions"]:
                        safe_st = html.escape(step['street'])
                        safe_to = html.escape(step['to_node'])
                        st.markdown(
                            f"<div class='step-card'>"
                            f"<span class='step-text'>Step {step['step_number']} · {safe_st}</span>"
                            f"<div class='step-subtext'>→ <b>{safe_to}</b> · {step['segment_meters']} m (Cumulative: {step['cumulative_meters']} m)</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    st.success(f"🏁 Arrived at **{safe_glm}** ({c_res['distance_meters']:.1f} m)")
        else:
            st.error(f"❌ Route calculation failed: {c_res.get('error')}")
