# 🏫 Campus Landmark A* Route Planner

An intelligent geospatial campus navigation engine and benchmarking suite designed for university campuses. Built with OpenStreetMap (OSM) topological networks, an admissible **Haversine heuristic**, custom **A\*** and **Dijkstra** implementations, and an intuitive **Streamlit** interactive dashboard.

---

## 🌟 Key Features

1. **Custom A\* Search Engine ($f(n) = g(n) + h(n)$):**
   - Implemented from base principles using Python's `heapq` priority queue.
   - Admissible and consistent **Haversine Great-Circle distance** heuristic ($R = 6,371,000\text{ m}$).
   - MultiDiGraph to simplified DiGraph preprocessing retaining $\min(\text{length})$.

2. **Dijkstra Baseline & Benchmark Suite:**
   - Uninformed search baseline ($h(n) = 0$).
   - Direct verification of **100% path optimality agreement** between A\* and Dijkstra.
   - Measures search space reduction (achieves **> 40% node expansion reduction** across campus routes).

3. **Campus Navigation & Accessibility:**
   - Pre-configured catalog of campus landmarks (Academic blocks, Library, Hostels, Canteen, Sports complex).
   - Mode selection: **Walking** (pedestrian paths) and **Driving** (vehicular campus roads).
   - **Accessibility Controls**: Options to avoid stairs/steps and select wheelchair-friendly paths.
   - Turn-by-turn directions with segment distances and estimated travel times.

4. **Interactive Web Dashboard:**
   - **Route Navigator**: Visualizes optimal path polylines on an interactive Folium map with custom markers.
   - **Benchmark Analytics**: Side-by-side performance cards, comparison charts, and CSV/JSON export.
   - **Algorithm Learning Mode**: Step-by-step visual exploration of open frontier, closed set, $g(n)$, $h(n)$, and $f(n)$ values.

---

## 📁 Project Structure

```text
aoStar-project/
├── app.py                      # Streamlit interactive web dashboard
├── main.py                     # CLI router & automated benchmark suite
├── requirements.txt            # Python dependencies
├── core/
│   ├── astar.py                # Custom A*, Dijkstra, Haversine heuristic & comparisons
│   ├── graph_engine.py         # Graph loading, OSMnx/GraphML cache, DiGraph simplification, snapping
│   ├── route_service.py        # Turn-by-turn navigation, accessibility filters & travel time
│   └── tracer.py               # Step-by-step search trace recorder for learning mode
├── data/
│   ├── landmarks.json          # Pre-configured campus landmarks
│   └── graphs/                 # Cached GraphML network graphs
├── tests/
│   └── test_routing.py         # Acceptance tests (TC-01 to TC-05)
└── reports/
    └── benchmark_results.json  # Exported benchmark analytics
```

---

## 🚀 Quick Start

### 1. Prerequisites & Environment Setup
The project requires Python 3.10+. A virtual environment is pre-configured in `.venv`.

To activate the virtual environment:
```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Or install dependencies manually:
```bash
pip install -r requirements.txt
```

### 2. Launch the Streamlit Web UI
Run the interactive dashboard:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
Open your browser at `http://localhost:8501`.

### 3. Run the CLI Route Planner
Calculate an optimal path directly from the terminal:
```powershell
.\.venv\Scripts\python.exe main.py --start MAIN_GATE --goal CSE_BLOCK
```

To avoid stairs (e.g. for accessibility):
```powershell
.\.venv\Scripts\python.exe main.py --start MAIN_GATE --goal CSE_BLOCK --avoid-stairs
```

### 4. Run the Automated Benchmark Suite
Evaluate A\* vs Dijkstra across 10 campus routes:
```powershell
.\.venv\Scripts\python.exe main.py --benchmark
```

### 5. Run the Automated Test Suite
Verify acceptance criteria (TC-01 through TC-05):
```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## 📊 Benchmark Results

| Route | Distance (m) | A* Expanded | Dijkstra Expanded | Search Space Reduction | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Main Gate ➔ CSE Block | 337.3 m | 9 | 12 | **25.0%** | ✓ Optimal |
| Main Gate ➔ Canteen | 341.4 m | 5 | 13 | **61.5%** | ✓ Optimal |
| Central Library ➔ Boys Hostel | 306.1 m | 5 | 15 | **66.7%** | ✓ Optimal |
| Auditorium ➔ ECE Block | 206.3 m | 3 | 11 | **72.7%** | ✓ Optimal |
| Mech Block ➔ Sports Complex | 268.4 m | 4 | 11 | **63.6%** | ✓ Optimal |
| **Campus Overall** | - | **79 nodes** | **141 nodes** | **44.0% Reduction** | **100% Agreement** |
