"""
graph_engine.py - MITS Campus graph loading, caching, coordinate snapping,
and exact image-calibrated pathway topology built on user ground-truth coordinates.
"""

import os
import json
from typing import Dict, Tuple, Optional, Any

import networkx as nx
from core.astar import haversine_distance


DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "graphs")
LANDMARKS_FILE   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "landmarks.json")

# Campus Centroid from exact user coordinates
CAMPUS_CENTER = (13.6285, 78.4768)


def create_mits_synthetic_campus_graph() -> nx.DiGraph:
    """
    Builds the precise pedestrian and vehicle road graph of MITS Madanapalle campus
    calibrated with the exact user coordinates matching the annotated satellite layout.
    """
    G = nx.DiGraph()

    # Exact Landmark coordinates provided by user
    nodes = {
        # North Campus & Hostel Areas
        "MAIN_GATE":           {"y": 13.63051, "x": 78.47781, "name": "Highway Intersection / Main Entrance Road"},
        "BOYS_HOSTEL":         {"y": 13.63248, "x": 78.47761, "name": "Boys Hostel Entrance Area"},
        "GIRLS_HOSTEL":        {"y": 13.63152, "x": 78.47863, "name": "Girls Hostel Area"},
        # Central Zone
        "MITS_GROUND":         {"y": 13.62923, "x": 78.47641, "name": "MITS Ground"},
        "J_CENTRAL":           {"y": 13.62850, "x": 78.47710, "name": "Central Boulevard Junction"},
        # South Campus & Academic Buildings
        "PLACEMENT_OFFICE":    {"y": 13.62774, "x": 78.47649, "name": "Placement Office Block Entrance"},
        "ADMIN_COURTYARD":     {"y": 13.62719, "x": 78.47656, "name": "Main Internal Courtyard & Block Core"},
        "GYM_UPPER":           {"y": 13.62778, "x": 78.47545, "name": "MITS Gym & Sports Room (Upper section)"},
        "GYM_MAIN":            {"y": 13.62725, "x": 78.47547, "name": "MITS Gym and Sports Room (Main facility)"},
        "SW_ACADEMIC_BLOCK":   {"y": 13.62657, "x": 78.47546, "name": "Southwestern Academic Block Corner"},
        "BOTTOM_WALKWAY":      {"y": 13.62678, "x": 78.47639, "name": "Bottom Center Walkway"},
        "AUDITORIUM_ENTRANCE": {"y": 13.62656, "x": 78.47697, "name": "Auditorium & Seminar Halls Entrance"},
    }

    for nid, data in nodes.items():
        G.add_node(nid, **data)

    # Walkway & roadway topology connecting the buildings
    # (u, v, bidirectional, highway_type, has_stairs, wheelchair_ok, path_name)
    edges = [
        # North Campus links
        ("MAIN_GATE",           "BOYS_HOSTEL",         True,  "primary",    False, True,  "North Boys Hostel Avenue"),
        ("MAIN_GATE",           "GIRLS_HOSTEL",        True,  "pedestrian", False, True,  "Girls Hostel Approach"),
        ("BOYS_HOSTEL",         "GIRLS_HOSTEL",        True,  "pedestrian", False, True,  "Hostel Cross-Connector"),
        # Entrance to Central Ground & Spine
        ("MAIN_GATE",           "J_CENTRAL",           True,  "primary",    False, True,  "Central Campus Boulevard"),
        ("MAIN_GATE",           "MITS_GROUND",         True,  "path",       False, True,  "Ground North Access Path"),
        ("J_CENTRAL",           "MITS_GROUND",         True,  "pedestrian", False, True,  "Ground East Pavilion Walk"),
        ("J_CENTRAL",           "PLACEMENT_OFFICE",    True,  "primary",    False, True,  "Placement Approach Spine"),
        # Academic Core & West Gym Wing
        ("PLACEMENT_OFFICE",    "ADMIN_COURTYARD",     True,  "pedestrian", False, True,  "Academic Central Quadrangle"),
        ("PLACEMENT_OFFICE",    "GYM_UPPER",           True,  "footway",    False, True,  "North-West Sports Promenade"),
        ("GYM_UPPER",           "GYM_MAIN",            True,  "footway",    False, True,  "Sports Hall Corridor"),
        ("GYM_MAIN",            "SW_ACADEMIC_BLOCK",   True,  "footway",    False, True,  "West Academic Walkway"),
        ("SW_ACADEMIC_BLOCK",   "BOTTOM_WALKWAY",      True,  "footway",    False, True,  "South Academic Promenade"),
        ("ADMIN_COURTYARD",     "BOTTOM_WALKWAY",      True,  "footway",    False, True,  "Courtyard South Link"),
        ("BOTTOM_WALKWAY",      "AUDITORIUM_ENTRANCE", True,  "footway",    False, True,  "Auditorium Plaza Walk"),
        ("ADMIN_COURTYARD",     "AUDITORIUM_ENTRANCE", True,  "footway",    False, True,  "Auditorium East Corridor"),
        ("ADMIN_COURTYARD",     "GYM_MAIN",            True,  "footway",    False, True,  "Central-Gym Cross Corridor"),
        ("MITS_GROUND",         "GYM_UPPER",           True,  "path",       False, True,  "Ground-Gym Connector"),
    ]

    for u, v, bidir, highway, stairs, wheelchair, name in edges:
        cu = (G.nodes[u]["y"], G.nodes[u]["x"])
        cv = (G.nodes[v]["y"], G.nodes[v]["x"])
        dist = float(haversine_distance(cu, cv))
        attrs = {
            "length": round(dist, 2),
            "highway": highway,
            "stairs": stairs,
            "wheelchair": wheelchair,
            "name": name,
            "oneway": not bidir
        }
        G.add_edge(u, v, **attrs)
        if bidir:
            G.add_edge(v, u, **attrs)

    return G


class CampusGraphManager:
    """Manages campus graph loading, caching, coordinate snapping, and connectivity checks."""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.graph: Optional[nx.DiGraph] = None
        self.landmarks: list = []
        self._load_landmarks()

    def _load_landmarks(self) -> None:
        if os.path.exists(LANDMARKS_FILE):
            with open(LANDMARKS_FILE, "r", encoding="utf-8") as f:
                self.landmarks = json.load(f)

    def get_or_load_graph(self, place_query: Optional[str] = None, force_refresh: bool = False) -> nx.DiGraph:
        """Returns cached graph, or builds and saves the image-calibrated graph."""
        cache_path = os.path.join(self.cache_dir, "campus_graph.graphml")

        if not force_refresh and os.path.exists(cache_path):
            try:
                G = nx.read_graphml(cache_path)
                for _, d in G.nodes(data=True):
                    d["x"] = float(d.get("x", 0.0))
                    d["y"] = float(d.get("y", 0.0))
                for _, _, d in G.edges(data=True):
                    d["length"] = float(d.get("length", 1.0))
                    d["stairs"] = str(d.get("stairs", "False")).lower() == "true"
                    d["wheelchair"] = str(d.get("wheelchair", "True")).lower() != "false"
                self.graph = G
                return self.graph
            except Exception:
                pass

        self.graph = create_mits_synthetic_campus_graph()
        try:
            nx.write_graphml(self.graph, cache_path)
        except Exception:
            pass
        return self.graph

    def snap_coordinate_to_node(self, lat: float, lon: float) -> Tuple[Any, float, Optional[str]]:
        """Snaps (lat, lon) to the nearest graph node."""
        if self.graph is None:
            self.get_or_load_graph()

        best_node, best_dist = None, float("inf")
        target = (lat, lon)
        for node, data in self.graph.nodes(data=True):
            d = haversine_distance(target, (data.get("y", 0.0), data.get("x", 0.0)))
            if d < best_dist:
                best_dist, best_node = d, node

        warning = (f"Nearest pathway node is {round(best_dist, 1)} m away (> 200 m threshold)."
                   if best_dist > 200.0 else None)
        return best_node, round(best_dist, 2), warning

    def verify_weak_connectivity(self, start: Any, goal: Any) -> bool:
        """Returns True if start and goal are connected."""
        if self.graph is None or start not in self.graph or goal not in self.graph:
            return False
        for comp in nx.weakly_connected_components(self.graph):
            if start in comp and goal in comp:
                return True
        return False
