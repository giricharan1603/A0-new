# 🏫 MITS Campus & Real-World A* Route Planner

An intelligent geospatial navigation system designed for MITS Madanapalle campus and regional intercity travel. Built with OpenStreetMap (OSM) topological road networks, Google Maps & CARTO basemaps, an admissible **Haversine heuristic**, custom **A\*** search implementation, and an interactive **Streamlit** dashboard.

---

## 🌟 Key Features

1. **Custom A\* Search Engine ($f(n) = g(n) + h(n)$):**
   - Implemented from base principles using Python's `heapq` priority queue.
   - Admissible and consistent **Haversine Great-Circle distance** heuristic ($R = 6,371,000\text{ m}$).
   - Fast sub-millisecond execution with guaranteed path optimality.

2. **Real-World & Campus Navigation Modes:**
   - **Real-World Road Navigator**: Intercity and village highway navigation across Andhra Pradesh, Karnataka, Tamil Nadu, and Telangana.
   - **17 MITS Campus Blocks**: Ground-truth calibrated coordinates for all academic blocks, hostels, sports facilities, library, canteen, and gates.
   - **Accessibility & Modes**: Walking (pedestrian pathways) and Driving (service roads) with stair avoidance and wheelchair routing.

3. **Draggable Pins & Interactive Maps:**
   - Drag-and-drop Start and Destination pins directly on the live map to fine-tune locations.
   - Coordinate inputs with instant recalculation.

4. **Village & City Bypass Directions:**
   - Replaces cryptic road/highway numbers with human-friendly directions indicating towns, villages, and cities passed through or bypassed along the route.

5. **Multi-Path Discovery with Green Shortest Path:**
   - Displays all available alternative routes in dashed lines with distances.
   - Highlights the optimal shortest path in **vivid Green (`#00C853`)** with animated pulses.

---

## 📁 Project Structure

```text
aoStar-project/
├── app.py                      # Streamlit interactive web dashboard
├── main.py                     # CLI router & route evaluation suite
├── requirements.txt            # Python dependencies
├── core/
│   ├── astar.py                # Custom A* search, alternative paths & Haversine heuristic
│   ├── geocoder.py             # Fuzzy autocomplete and coordinate resolution
│   ├── graph_engine.py         # 17 MITS Campus landmarks, graph loading, cache & snapping
│   ├── places_data.py          # Curated database of towns, villages, and regional cities
│   ├── realworld_router.py     # OSRM corridor topology & village bypass directions
│   ├── route_service.py        # Campus turn-by-turn directions & accessibility
│   └── tracer.py               # Step-by-step search trace recorder for learning mode
├── data/
│   ├── landmarks.json          # 17 calibrated MITS campus landmarks
│   └── graphs/                 # Cached GraphML network graphs
├── tests/
│   └── test_routing.py         # Verification tests (TC-01 to TC-06)
└── reports/
    └── benchmark_results.json  # Exported route analytics
```

---

## 🚀 Quick Start

### 1. Launch the Streamlit Web UI
Run the interactive dashboard:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
Open your browser at `http://localhost:8501`.

### 2. Run the CLI Route Planner
Calculate an optimal path directly from the terminal:
```powershell
.\.venv\Scripts\python.exe main.py --start MAIN_ENTRANCE --goal CSE_DEPARTMENT
```

### 3. Run Campus Test Routes
```powershell
.\.venv\Scripts\python.exe main.py --benchmark
```

### 4. Run Automated Tests
Verify all acceptance criteria:
```powershell
.\.venv\Scripts\pytest.exe -v
```
