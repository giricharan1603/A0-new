"""
app.py — RealRoute: Real-World A* Route Planner
Google Maps-style UI using real OpenStreetMap road networks.

Type any place (village, city, landmark) → get optimal route via A* algorithm.
CARTO map tiles with API key for professional map display.

MITS Madanapalle | AI Lab Mini-Project (23CSE109 / 23CSE208)
"""

import streamlit as st
import streamlit.components.v1 as components
import folium
from folium.plugins import AntPath
import pandas as pd

from core.geocoder  import geocode, haversine_km
from core.realworld_router import route_realworld

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RealRoute — A* Navigation",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CARTO TILES (API key embedded)
# ─────────────────────────────────────────────────────────────
CARTO_KEY = "cb1_3sam_1_2355f1d9cf8d0ccc9cceaf27"
CARTO_LIGHT = f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}@2x.png?api_key={CARTO_KEY}"
CARTO_DARK  = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}@2x.png?api_key={CARTO_KEY}"
CARTO_ATTR  = ('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
               'contributors &copy; <a href="https://carto.com/">CARTO</a>')

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
defaults = {
    "dark_mode":      True,
    "start_text":     "",
    "end_text":       "",
    "start_place":    None,   # dict: {display_name, short_name, lat, lon}
    "end_place":      None,
    "start_sugg":     [],
    "end_sugg":       [],
    "route_result":   None,
    "route_key":      None,
    "search_active":  None,   # "start" | "end" | None
    "travel_mode":    "drive",
    "run_benchmark":  True,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

T_DARK  = "#0A0F1E"
T_CARD  = "rgba(15,23,42,0.90)" if st.session_state.dark_mode else "rgba(255,255,255,0.92)"

# ─────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────
if st.session_state.dark_mode:
    T = dict(
        bg="#0A0F1E", card="rgba(15,23,42,0.92)", border="#1E3A5F",
        glass="rgba(15,23,42,0.80)", text="#E2E8F0", muted="#94A3B8",
        accent="#60A5FA", accent2="#A78BFA", green="#22C55E", red="#EF4444",
        step_bg="#0D1F12", step_brd="#16A34A",
        info_bg="#0C1F35", info_brd="#38BDF8",
        metric_bg="rgba(30,41,59,0.95)", metric_brd="#334155",
        hdr="linear-gradient(135deg,#060B18 0%,#0F2456 45%,#1A0A3A 100%)",
        sugg_bg="#0F1A2E", sugg_hover="#1A2D45",
        map_tiles=CARTO_DARK, route_color="#60A5FA",
        input_bg="#0F1A2E", input_brd="#1E3A5F",
    )
else:
    T = dict(
        bg="#EEF2FF", card="rgba(255,255,255,0.95)", border="#C7D7F5",
        glass="rgba(255,255,255,0.80)", text="#1E293B", muted="#64748B",
        accent="#2563EB", accent2="#7C3AED", green="#16A34A", red="#DC2626",
        step_bg="#F0FDF4", step_brd="#16A34A",
        info_bg="#EFF6FF", info_brd="#93C5FD",
        metric_bg="rgba(255,255,255,0.95)", metric_brd="#BFDBFE",
        hdr="linear-gradient(135deg,#1E3A8A 0%,#2563EB 55%,#4C1D95 100%)",
        sugg_bg="#F8FAFF", sugg_hover="#EFF6FF",
        map_tiles=CARTO_LIGHT, route_color="#2563EB",
        input_bg="#FFFFFF", input_brd="#C7D7F5",
    )

# ─────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Page */
  .stApp {{
    background: {T['bg']};
    background-image:
      radial-gradient(ellipse at 15% 10%, rgba(96,165,250,0.07) 0%, transparent 55%),
      radial-gradient(ellipse at 85% 90%, rgba(167,139,250,0.07) 0%, transparent 55%);
  }}
  #MainMenu, footer, .stDeployButton {{ visibility: hidden; }}

  /* Hero header */
  .hero {{
    background: {T['hdr']};
    border-radius: 20px;
    padding: 26px 36px 20px;
    margin-bottom: 0;
    position: relative; overflow: hidden;
    box-shadow: 0 10px 40px rgba(0,0,0,0.35);
  }}
  .hero::after {{
    content:'';position:absolute;inset:0;
    background:repeating-linear-gradient(45deg,transparent,transparent 50px,
      rgba(255,255,255,0.025) 50px,rgba(255,255,255,0.025) 100px);
  }}
  .hero-title {{
    font-size:2rem; font-weight:900; color:#fff;
    margin:0 0 4px; position:relative; z-index:1;
    letter-spacing:-0.02em;
  }}
  .hero-sub {{
    font-size:.92rem; color:rgba(255,255,255,0.75);
    margin:0; position:relative; z-index:1;
  }}
  .hero-pill {{
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(255,255,255,0.12);
    border:1px solid rgba(255,255,255,0.22);
    border-radius:20px; padding:4px 13px;
    font-size:0.75rem; color:#fff; margin:10px 6px 0 0;
    position:relative; z-index:1;
    backdrop-filter:blur(6px);
  }}

  /* Search card */
  .search-card {{
    background: {T['card']};
    border: 1px solid {T['border']};
    border-radius: 18px;
    padding: 20px 24px 16px;
    backdrop-filter: blur(14px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.14);
    margin-bottom: 0;
  }}
  .search-label {{
    font-size: 0.72rem; font-weight: 800;
    color: {T['muted']}; letter-spacing: 0.10em;
    text-transform: uppercase; margin-bottom: 6px;
  }}

  /* Suggestion buttons */
  .sugg-btn {{
    display: block; width: 100%;
    text-align: left; padding: 9px 14px;
    background: {T['sugg_bg']}; color: {T['text']};
    border: 1px solid {T['border']}; border-radius: 10px;
    font-size: 0.83rem; cursor: pointer;
    margin-bottom: 5px;
    transition: background 0.15s ease;
  }}
  .sugg-btn:hover {{ background: {T['sugg_hover']}; }}
  .sugg-name  {{ font-weight: 700; display:block; }}
  .sugg-full  {{ font-size: 0.74rem; color: {T['muted']}; display:block; margin-top:1px; }}

  /* Metric cards */
  .metrics-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin: 16px 0 8px;
  }}
  .m-card {{
    background: {T['metric_bg']};
    border: 1px solid {T['metric_brd']};
    border-radius: 14px; padding: 15px 16px;
    text-align: center;
    backdrop-filter: blur(8px);
    transition: transform .18s ease, box-shadow .18s ease;
  }}
  .m-card:hover {{ transform:translateY(-3px); box-shadow:0 8px 22px rgba(0,0,0,0.2); }}
  .m-icon  {{ font-size:1.4rem; margin-bottom:3px; }}
  .m-value {{ font-size:1.35rem; font-weight:800; color:{T['accent']}; line-height:1.1; }}
  .m-label {{ font-size:0.72rem; color:{T['muted']}; font-weight:600; margin-top:2px; }}
  .m-sub   {{ font-size:0.69rem; color:{T['green']}; font-weight:600; margin-top:3px; }}

  /* Step directions */
  .step-wrap {{
    background: {T['step_bg']};
    border-left: 4px solid {T['step_brd']};
    padding: 10px 14px; margin-bottom: 7px;
    border-radius: 0 10px 10px 0;
  }}
  .step-num {{
    display:inline-flex; align-items:center; justify-content:center;
    width:22px; height:22px; border-radius:50%;
    background:{T['step_brd']}; color:#fff;
    font-size:.7rem; font-weight:800; margin-right:7px; flex-shrink:0;
  }}
  .step-street {{ font-weight:700; color:{T['text']}; font-size:.86rem; }}
  .step-detail {{ color:{T['muted']}; font-size:.76rem; margin-top:3px; margin-left:29px; }}

  /* Arrived banner */
  .arrived {{
    background: linear-gradient(90deg,#15803D,#166534);
    border-radius: 10px; padding: 12px 18px;
    color: #fff; font-weight: 800; font-size: .95rem;
    text-align: center; margin-top: 10px;
    box-shadow: 0 4px 16px rgba(21,128,61,0.4);
  }}

  /* Place tag chip */
  .place-chip {{
    display:inline-flex; align-items:center; gap:7px;
    background:{T['info_bg']}; border:1px solid {T['info_brd']};
    border-radius:10px; padding:8px 14px; margin-bottom:8px;
    font-size:.82rem; font-weight:600; color:{T['text']};
  }}

  /* Section divider label */
  .sec-label {{
    font-size:.72rem; font-weight:800; color:{T['muted']};
    letter-spacing:.10em; text-transform:uppercase; margin:12px 0 6px;
  }}

  /* Streamlit overrides */
  .stTextInput input {{
    background: {T['input_bg']} !important;
    border-color: {T['input_brd']} !important;
    color: {T['text']} !important;
    border-radius: 10px !important;
    font-size: .9rem !important;
  }}
  .stTextInput label {{ color:{T['muted']} !important; font-weight:600; font-size:.8rem !important; }}
  .stTabs [data-baseweb="tab"] {{ color:{T['muted']}; font-weight:600; }}
  .stTabs [aria-selected="true"] {{ color:{T['accent']} !important; border-bottom-color:{T['accent']} !important; }}
  .stRadio label, .stCheckbox label {{ color:{T['text']} !important; }}
  .stButton button {{
    border-radius: 10px !important; font-weight: 700 !important;
  }}
  div[data-baseweb="select"] {{ border-radius: 10px !important; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;padding:14px 0 10px;">
      <div style="font-size:2rem;">🗺️</div>
      <div style="font-weight:900;font-size:1.1rem;color:{T['text']};">RealRoute</div>
      <div style="font-size:0.74rem;color:{T['muted']};">A* Real-World Navigation</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    lbl = "☀️  Light Mode" if st.session_state.dark_mode else "🌙  Dark Mode"
    if st.button(lbl, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    st.markdown(f"<div class='sec-label'>🚗 Travel Options</div>", unsafe_allow_html=True)

    mode = st.radio(
        "Mode",
        ["drive", "walk"],
        index=0 if st.session_state.travel_mode == "drive" else 1,
        format_func=lambda x: "🚗  Driving (~40 km/h avg)" if x == "drive" else "🚶  Walking (~5 km/h)",
    )
    if mode != st.session_state.travel_mode:
        st.session_state.travel_mode  = mode
        st.session_state.route_result = None
        st.rerun()

    bench = st.checkbox("⚡  Run A* vs Dijkstra benchmark", value=st.session_state.run_benchmark)
    if bench != st.session_state.run_benchmark:
        st.session_state.run_benchmark = bench

    st.markdown("---")
    st.markdown(f"<div class='sec-label'>📐 Algorithm</div>", unsafe_allow_html=True)
    st.caption("**A\\*** — Haversine heuristic $h(n)$. Prunes the search space for fast results on large road graphs.")
    st.caption("**Dijkstra** — $h(n)=0$. Exhaustive baseline. Guarantees same optimal path.")

    st.markdown("---")
    # Quick-access example routes
    st.markdown(f"<div class='sec-label'>🧪 Example Routes</div>", unsafe_allow_html=True)
    examples = [
        ("Madanapalle → Tirupati",    "Madanapalle, Andhra Pradesh",    "Tirupati, Andhra Pradesh"),
        ("Bangalore → Mysore",        "Bangalore, Karnataka",           "Mysore, Karnataka"),
        ("Hyderabad → Warangal",      "Hyderabad, Telangana",           "Warangal, Telangana"),
        ("Delhi → Agra",              "New Delhi, India",               "Agra, Uttar Pradesh"),
        ("Mumbai → Pune",             "Mumbai, Maharashtra",            "Pune, Maharashtra"),
    ]
    for label, s, e in examples:
        if st.button(f"📍 {label}", use_container_width=True, key=f"ex_{label}"):
            st.session_state.start_text   = s
            st.session_state.end_text     = e
            st.session_state.start_sugg   = []
            st.session_state.end_sugg     = []
            st.session_state.route_result = None
            # Auto-geocode the example
            with st.spinner("Locating…"):
                s_res = geocode(s, limit=1)
                e_res = geocode(e, limit=1)
            if s_res:
                st.session_state.start_place = s_res[0]
            if e_res:
                st.session_state.end_place = e_res[0]
            st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div style="font-size:.7rem;color:{T['muted']};text-align:center;line-height:1.7;">
      Road data © OpenStreetMap<br>Map tiles © CARTO<br>
      Algorithm: Custom A* · Haversine h(n)<br>
      23CSE109 / 23CSE208 · MITS Madanapalle
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-title">🗺️ RealRoute — A* Navigation Engine</div>
  <div class="hero-sub">Type any city, village, or landmark — get real road routes powered by A* pathfinding</div>
  <div>
    <span class="hero-pill">⚡ A* Algorithm</span>
    <span class="hero-pill">🌍 OpenStreetMap Data</span>
    <span class="hero-pill">🗺️ CARTO Map Tiles</span>
    <span class="hero-pill">📐 Dijkstra Benchmark</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SEARCH CARD
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="search-card">', unsafe_allow_html=True)
st.markdown('<div class="sec-label">🔍 Enter Route</div>', unsafe_allow_html=True)

col_s, col_mid, col_e, col_btn = st.columns([10, 1, 10, 3])

with col_s:
    start_input = st.text_input(
        "🚩 Start — city, village, landmark",
        value=st.session_state.start_text,
        placeholder="e.g. Madanapalle, Andhra Pradesh",
        key="start_input_box",
    )

with col_mid:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("⇄", help="Swap start and destination", use_container_width=True):
        st.session_state.start_text,  st.session_state.end_text   = (
            st.session_state.end_text,    st.session_state.start_text
        )
        st.session_state.start_place, st.session_state.end_place  = (
            st.session_state.end_place,   st.session_state.start_place
        )
        st.session_state.route_result = None
        st.rerun()

with col_e:
    end_input = st.text_input(
        "🎯 Destination — city, village, landmark",
        value=st.session_state.end_text,
        placeholder="e.g. Tirupati, Andhra Pradesh",
        key="end_input_box",
    )

with col_btn:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    find_btn = st.button("🔍  Find Route", type="primary", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HANDLE TEXT INPUT CHANGES → fetch suggestions
# ─────────────────────────────────────────────────────────────
if start_input != st.session_state.start_text:
    st.session_state.start_text  = start_input
    st.session_state.start_place = None
    st.session_state.route_result = None
    if len(start_input.strip()) >= 2:
        with st.spinner("Searching places…"):
            st.session_state.start_sugg = geocode(start_input, limit=5)
    else:
        st.session_state.start_sugg = []

if end_input != st.session_state.end_text:
    st.session_state.end_text  = end_input
    st.session_state.end_place = None
    st.session_state.route_result = None
    if len(end_input.strip()) >= 2:
        with st.spinner("Searching places…"):
            st.session_state.end_sugg = geocode(end_input, limit=5)
    else:
        st.session_state.end_sugg = []


# ─────────────────────────────────────────────────────────────
# SUGGESTIONS PANELS
# ─────────────────────────────────────────────────────────────
def render_suggestions(sugg_list, field: str):
    """Render clickable suggestion buttons. field = 'start' | 'end'"""
    if not sugg_list:
        return
    for i, s in enumerate(sugg_list):
        btn_key = f"{field}_sugg_{i}_{s['lat']:.4f}"
        if st.button(
            f"📍  {s['short_name']}\n{s['display_name'][:80]}",
            key=btn_key,
            use_container_width=True,
        ):
            if field == "start":
                st.session_state.start_place = s
                st.session_state.start_text  = s["short_name"]
                st.session_state.start_sugg  = []
            else:
                st.session_state.end_place = s
                st.session_state.end_text  = s["short_name"]
                st.session_state.end_sugg  = []
            st.session_state.route_result = None
            st.rerun()


sug_col_s, sug_col_e = st.columns(2)
with sug_col_s:
    if st.session_state.start_sugg and not st.session_state.start_place:
        st.markdown(f"<div class='sec-label'>Start suggestions</div>", unsafe_allow_html=True)
        render_suggestions(st.session_state.start_sugg, "start")

with sug_col_e:
    if st.session_state.end_sugg and not st.session_state.end_place:
        st.markdown(f"<div class='sec-label'>Destination suggestions</div>", unsafe_allow_html=True)
        render_suggestions(st.session_state.end_sugg, "end")


# ─────────────────────────────────────────────────────────────
# SELECTED PLACE CHIPS
# ─────────────────────────────────────────────────────────────
chip_col_s, chip_col_e = st.columns(2)
with chip_col_s:
    sp = st.session_state.start_place
    if sp:
        dist_disp = ""
        ep = st.session_state.end_place
        if ep:
            d = haversine_km(sp["lat"], sp["lon"], ep["lat"], ep["lon"])
            dist_disp = f"&nbsp;&middot;&nbsp; {d:.1f} km apart"
        muted = T["muted"]
        st.markdown(
            f'<div class="place-chip">🚩 <b>{sp["short_name"]}</b>'
            f'&nbsp;<span style="color:{muted};font-size:.74rem;">'
            f'({sp["lat"]:.4f}, {sp["lon"]:.4f})</span>'
            f'<span style="color:{muted};font-size:.74rem;">{dist_disp}</span></div>',
            unsafe_allow_html=True
        )

with chip_col_e:
    ep = st.session_state.end_place
    if ep:
        muted = T["muted"]
        st.markdown(
            f'<div class="place-chip">🎯 <b>{ep["short_name"]}</b>'
            f'&nbsp;<span style="color:{muted};font-size:.74rem;">'
            f'({ep["lat"]:.4f}, {ep["lon"]:.4f})</span></div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────
# FIND ROUTE TRIGGER
# ─────────────────────────────────────────────────────────────
sp = st.session_state.start_place
ep = st.session_state.end_place

if find_btn:
    # If places aren't picked yet, auto-geocode the typed text
    if not sp and st.session_state.start_text.strip():
        with st.spinner(f"Locating {st.session_state.start_text}…"):
            res = geocode(st.session_state.start_text, limit=1)
        if res:
            st.session_state.start_place = res[0]
            sp = res[0]
        else:
            st.error(f"❌ Could not find '{st.session_state.start_text}'. Try a more specific name.")

    if not ep and st.session_state.end_text.strip():
        with st.spinner(f"Locating {st.session_state.end_text}…"):
            res = geocode(st.session_state.end_text, limit=1)
        if res:
            st.session_state.end_place = res[0]
            ep = res[0]
        else:
            st.error(f"❌ Could not find '{st.session_state.end_text}'. Try a more specific name.")

    if sp and ep:
        route_key = (
            round(sp["lat"], 5), round(sp["lon"], 5),
            round(ep["lat"], 5), round(ep["lon"], 5),
            st.session_state.travel_mode,
        )
        if st.session_state.route_key != route_key:
            st.session_state.route_key = route_key
            d_km = haversine_km(sp["lat"], sp["lon"], ep["lat"], ep["lon"])
            with st.spinner(
                f"⬇️ Fetching road network ({d_km:.0f} km straight-line) · "
                f"Running A* & Dijkstra…"
            ):
                result = route_realworld(
                    start_lat=sp["lat"], start_lon=sp["lon"],
                    end_lat=ep["lat"],   end_lon=ep["lon"],
                    start_name=sp["short_name"],
                    end_name=ep["short_name"],
                    travel_mode=st.session_state.travel_mode,
                    run_benchmark=st.session_state.run_benchmark,
                )
            st.session_state.route_result = result
        st.rerun()


# ─────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────
result = st.session_state.route_result

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def _build_route_map(result, sp, ep) -> folium.Map:
    coords = result["path_coords"]
    lats   = [c[0] for c in coords]
    lons   = [c[1] for c in coords]

    fmap = folium.Map(
        location=[(min(lats)+max(lats))/2, (min(lons)+max(lons))/2],
        zoom_start=12,
        tiles=T["map_tiles"],
        attr=CARTO_ATTR,
        prefer_canvas=True,
    )
    fmap.fit_bounds(
        [[min(lats), min(lons)], [max(lats), max(lons)]],
        padding=[40, 40]
    )

    # Route shadow
    folium.PolyLine(coords, color="#000", weight=10, opacity=0.10).add_to(fmap)

    # Animated route line
    try:
        AntPath(
            locations=coords,
            color=T["route_color"], weight=6, opacity=0.92,
            delay=600, dash_array=[20, 40],
            tooltip=f"{result['distance_km']} km · {result['duration']}",
        ).add_to(fmap)
    except Exception:
        folium.PolyLine(coords, color=T["route_color"], weight=6, opacity=0.9).add_to(fmap)

    # Start marker
    folium.Marker(
        [sp["lat"], sp["lon"]],
        popup=folium.Popup(
            f"<b>🚩 Start</b><br>{sp['short_name']}<br>"
            f"<small>{sp['lat']:.5f}, {sp['lon']:.5f}</small>",
            max_width=200
        ),
        tooltip=f"🚩 {sp['short_name']}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(fmap)

    # End marker
    folium.Marker(
        [ep["lat"], ep["lon"]],
        popup=folium.Popup(
            f"<b>🎯 Destination</b><br>{ep['short_name']}<br>"
            f"<small>{ep['lat']:.5f}, {ep['lon']:.5f}</small>",
            max_width=200
        ),
        tooltip=f"🎯 {ep['short_name']}",
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    ).add_to(fmap)

    # Waypoint dots on route (every ~5th node, skip endpoints)
    step = max(1, len(coords) // 30)
    for i in range(step, len(coords) - step, step):
        folium.CircleMarker(
            location=coords[i],
            radius=3, color=T["route_color"],
            fill=True, fill_opacity=0.5, weight=1,
        ).add_to(fmap)

    return fmap


def _build_empty_map(center=(20.5937, 78.9629), zoom=5) -> folium.Map:
    """Default India-centered map when no route is computed."""
    return folium.Map(
        location=list(center),
        zoom_start=zoom,
        tiles=T["map_tiles"],
        attr=CARTO_ATTR,
        prefer_canvas=True,
    )


# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────
tab_map, tab_dirs, tab_algo = st.tabs([
    "🗺️  Route Map",
    "📋  Directions",
    "📊  Algorithm Analysis",
])

# ── TAB 1: MAP ───────────────────────────────────────────────
with tab_map:
    if result and result["status"] == "SUCCESS":
        # Metrics row
        cmp = result.get("comparison") or {}
        st.markdown(f"""
        <div class="metrics-grid">
          <div class="m-card">
            <div class="m-icon">📏</div>
            <div class="m-value">{result['distance_km']} km</div>
            <div class="m-label">Route Distance</div>
            <div class="m-sub">{result['distance_m']:.0f} m total</div>
          </div>
          <div class="m-card">
            <div class="m-icon">⏱️</div>
            <div class="m-value">{result['duration']}</div>
            <div class="m-label">Est. Travel Time</div>
            <div class="m-sub">{'~40 km/h avg' if st.session_state.travel_mode=='drive' else '~5 km/h walking'}</div>
          </div>
          <div class="m-card">
            <div class="m-icon">⚡</div>
            <div class="m-value">{result['astar']['nodes_expanded']:,}</div>
            <div class="m-label">A* Nodes Explored</div>
            <div class="m-sub">{result['astar']['execution_time_ms']:.1f} ms</div>
          </div>
          <div class="m-card">
            <div class="m-icon">🎯</div>
            <div class="m-value">{cmp.get('expansion_reduction_pct', '—')}%</div>
            <div class="m-label">Search Reduction</div>
            <div class="m-sub">vs Dijkstra baseline</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Network info banner
        st.markdown(
            f'<div style="font-size:.78rem;color:{T["muted"]};padding:5px 2px;margin-bottom:8px;">'
            f'🌐 <b>Network:</b> {result["network_desc"]} &nbsp;·&nbsp; '
            f'<b>Graph:</b> {result["graph_nodes"]:,} nodes, {result["graph_edges"]:,} edges &nbsp;·&nbsp; '
            f'<b>Path:</b> {len(result["path_coords"]):,} coordinates'
            f'</div>',
            unsafe_allow_html=True
        )

        fmap = _build_route_map(result, sp, ep)
        components.html(fmap._repr_html_(), height=560)

        for w in result.get("warnings", []):
            st.warning(w)

    elif result and result["status"] == "FAILED":
        st.error(f"❌ {result.get('error', 'Route failed.')}")
        for w in result.get("warnings", []):
            st.warning(w)
        st.info(
            "💡 Tips:\n"
            "- Try a **more specific** place name (add state/country)\n"
            "- Switch travel mode: some areas have no drive roads\n"
            "- Very remote areas may have sparse road data"
        )
        components.html(_build_empty_map()._repr_html_(), height=480)
    else:
        # Empty state — show India map with instructions
        st.markdown(
            f'<div style="text-align:center;padding:20px 0 12px;color:{T["muted"]};">'
            f'<div style="font-size:2.5rem;margin-bottom:8px;">🗺️</div>'
            f'<div style="font-size:1rem;font-weight:700;color:{T["text"]};">Enter a Start and Destination above</div>'
            f'<div style="font-size:.85rem;margin-top:4px;">Then click <b>Find Route</b> to compute the A* optimal path</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        components.html(_build_empty_map()._repr_html_(), height=500)


# ── TAB 2: DIRECTIONS ────────────────────────────────────────
with tab_dirs:
    if result and result["status"] == "SUCCESS":
        dirs = result["directions"]
        total = len(dirs)

        st.markdown(
            f'<div class="sec-label">Turn-by-Turn Directions — {total} steps · {result["distance_km"]} km</div>',
            unsafe_allow_html=True
        )

        # Journey start
        st.markdown(
            f'<div style="padding:9px 14px;background:{T["info_bg"]};border:1px solid {T["info_brd"]};"'
            f'border-radius:10px;margin-bottom:8px;font-size:.82rem;color:{T["text"]};">'
            f'📍 <b>Starting at</b> {result["start_name"]}</div>',
            unsafe_allow_html=True
        )

        # Directions in a scrollable area
        # We chunk into groups of 50 for performance
        MAX_STEPS_SHOWN = 100
        shown = dirs[:MAX_STEPS_SHOWN]

        for step in shown:
            seg_km = step["segment_meters"] / 1000
            cum_km = step["cumulative_meters"] / 1000
            st.markdown(
                f'<div class="step-wrap">'
                f'<span class="step-num">{step["step_number"]}</span>'
                f'<span class="step-street">{step["street"]}</span>'
                f'<div class="step-detail">'
                f'{step["segment_meters"]:.0f} m'
                f' &nbsp;·&nbsp; total {cum_km:.2f} km'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        if len(dirs) > MAX_STEPS_SHOWN:
            st.info(f"Showing first {MAX_STEPS_SHOWN} of {total} steps. Route continues…")

        st.markdown(
            f'<div class="arrived">🏁 Arrived at {result["end_name"]} · {result["distance_km"]} km</div>',
            unsafe_allow_html=True
        )
    else:
        st.info("🗺️ Compute a route first to see turn-by-turn directions.")


# ── TAB 3: ALGORITHM ANALYSIS ────────────────────────────────
with tab_algo:
    if result and result["status"] == "SUCCESS":
        astar_r = result.get("astar", {})
        dijk_r  = result.get("dijkstra")
        cmp     = result.get("comparison")

        if cmp:
            st.markdown(
                f'<div style="font-size:1.1rem;font-weight:800;color:{T["text"]};margin-bottom:14px;">'
                f'⚡ A* vs 🔵 Dijkstra — Live Comparison</div>',
                unsafe_allow_html=True
            )

            # Side-by-side algorithm cards
            ac, dc = st.columns(2)
            with ac:
                st.markdown(f"""
                <div class="m-card" style="text-align:left;padding:18px 20px;">
                  <div style="font-size:1rem;font-weight:800;color:{T['accent']};margin-bottom:10px;">⚡ A* Algorithm</div>
                  <div style="color:{T['muted']};font-size:.8rem;">Nodes Explored</div>
                  <div style="font-size:1.5rem;font-weight:800;color:{T['text']};">{astar_r.get('nodes_expanded',0):,}</div>
                  <div style="color:{T['muted']};font-size:.8rem;margin-top:8px;">Execution Time</div>
                  <div style="font-size:1.3rem;font-weight:800;color:{T['text']};">{astar_r.get('execution_time_ms',0):.1f} ms</div>
                  <div style="color:{T['muted']};font-size:.8rem;margin-top:8px;">Heuristic</div>
                  <div style="font-size:.9rem;color:{T['text']};">h(n) = Haversine distance</div>
                </div>
                """, unsafe_allow_html=True)

            with dc:
                dijk_nodes = dijk_r.get('nodes_expanded', 0) if dijk_r else '—'
                dijk_ms    = f"{dijk_r.get('execution_time_ms', 0):.1f}" if dijk_r else '—'
                st.markdown(f"""
                <div class="m-card" style="text-align:left;padding:18px 20px;">
                  <div style="font-size:1rem;font-weight:800;color:#818CF8;margin-bottom:10px;">🔵 Dijkstra</div>
                  <div style="color:{T['muted']};font-size:.8rem;">Nodes Explored</div>
                  <div style="font-size:1.5rem;font-weight:800;color:{T['text']};"> {dijk_nodes:,}</div>
                  <div style="color:{T['muted']};font-size:.8rem;margin-top:8px;">Execution Time</div>
                  <div style="font-size:1.3rem;font-weight:800;color:{T['text']};">{dijk_ms} ms</div>
                  <div style="color:{T['muted']};font-size:.8rem;margin-top:8px;">Heuristic</div>
                  <div style="font-size:.9rem;color:{T['text']};">h(n) = 0 (uninformed)</div>
                </div>
                """, unsafe_allow_html=True)

            # Key metrics
            st.markdown(f"""
            <div class="metrics-grid" style="margin-top:14px;">
              <div class="m-card">
                <div class="m-icon">📉</div>
                <div class="m-value">{cmp['expansion_reduction_pct']}%</div>
                <div class="m-label">Node Reduction</div>
                <div class="m-sub">A* explores fewer nodes</div>
              </div>
              <div class="m-card">
                <div class="m-icon">🚀</div>
                <div class="m-value">{cmp['speedup']}×</div>
                <div class="m-label">Speedup</div>
                <div class="m-sub">A* is faster by this factor</div>
              </div>
              <div class="m-card">
                <div class="m-icon">✅</div>
                <div class="m-value">{'100%' if cmp['is_optimal_match'] else '⚠️'}</div>
                <div class="m-label">Optimality</div>
                <div class="m-sub">{'Same distance ✓' if cmp['is_optimal_match'] else 'Distance mismatch!'}</div>
              </div>
              <div class="m-card">
                <div class="m-icon">🔢</div>
                <div class="m-value">{cmp['nodes_expanded_diff']:,}</div>
                <div class="m-label">Nodes Saved</div>
                <div class="m-sub">Dijkstra − A* expansions</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Bar chart comparison
            st.markdown(f"<div class='sec-label' style='margin-top:14px;'>Node Expansion Comparison</div>", unsafe_allow_html=True)
            chart_df = pd.DataFrame({
                "Algorithm": ["A*", "Dijkstra"],
                "Nodes Explored": [
                    cmp["astar_nodes"],
                    cmp["dijkstra_nodes"]
                ],
            }).set_index("Algorithm")
            st.bar_chart(chart_df, color=[T["accent"]])

            # Admissibility explanation
            st.markdown(f"""
            <div style="background:{T['info_bg']};border:1px solid {T['info_brd']};
                        border-radius:12px;padding:14px 18px;margin-top:10px;font-size:.83rem;color:{T['text']};">
              <b>🔬 Why A* is faster:</b> The Haversine heuristic $h(n)$ estimates the
              straight-line great-circle distance to the goal. Because $h(n) \\le h^*(n)$
              (never overestimates the true cost), A* is <b>admissible</b> — it prunes
              unpromising branches early, expanding only {cmp['expansion_reduction_pct']}% fewer
              nodes than Dijkstra while guaranteeing the same optimal path.
            </div>
            """, unsafe_allow_html=True)

        else:
            st.info("Enable 'Run A* vs Dijkstra benchmark' in the sidebar to see the comparison.")

        # Route metadata
        st.markdown(f"<div class='sec-label' style='margin-top:16px;'>Route Metadata</div>", unsafe_allow_html=True)
        meta_df = pd.DataFrame([{
            "Property":          "Start",
            "Value":             f"{result['start_name']} ({sp['lat']:.5f}, {sp['lon']:.5f})"
        }, {
            "Property":          "End",
            "Value":             f"{result['end_name']} ({ep['lat']:.5f}, {ep['lon']:.5f})"
        }, {
            "Property":          "Straight-line",
            "Value":             f"{haversine_km(sp['lat'], sp['lon'], ep['lat'], ep['lon']):.2f} km"
        }, {
            "Property":          "Route distance",
            "Value":             f"{result['distance_km']} km ({result['distance_m']:.0f} m)"
        }, {
            "Property":          "Est. duration",
            "Value":             result['duration']
        }, {
            "Property":          "Network type",
            "Value":             result['network_desc']
        }, {
            "Property":          "Graph size",
            "Value":             f"{result['graph_nodes']:,} nodes · {result['graph_edges']:,} edges"
        }, {
            "Property":          "Path waypoints",
            "Value":             f"{len(result['path_coords']):,} coordinates"
        }, {
            "Property":          "Snap dist (start)",
            "Value":             f"{result['snap_dist_start_m']} m from road"
        }, {
            "Property":          "Snap dist (end)",
            "Value":             f"{result['snap_dist_end_m']} m from road"
        }])
        st.dataframe(meta_df, use_container_width=True, hide_index=True)

    else:
        st.info("📊 Compute a route first to see the algorithm analysis.")

        # Explain the algorithms even before a route
        st.markdown(f"""
        <div style="background:{T['info_bg']};border:1px solid {T['info_brd']};
                    border-radius:12px;padding:18px 22px;margin-top:10px;font-size:.85rem;color:{T['text']};">
          <div style="font-weight:800;font-size:1rem;margin-bottom:10px;">📐 How the Algorithms Work</div>
          <b>A* Search</b> — Uses a priority queue with $f(n) = g(n) + h(n)$:<br>
          &bull; $g(n)$ = exact cost from start to current node (road distance in meters)<br>
          &bull; $h(n)$ = Haversine great-circle distance to goal (admissible heuristic)<br>
          &bull; Explores nodes in order of <i>estimated total cost</i> → prunes dead ends early<br><br>
          <b>Dijkstra</b> — Special case with $h(n) = 0$:<br>
          &bull; Explores nodes in order of exact cost from start only<br>
          &bull; Guaranteed optimal but explores many more nodes<br>
          &bull; Used as the gold-standard baseline to verify A* optimality
        </div>
        """, unsafe_allow_html=True)
