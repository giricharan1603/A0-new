"""
graph_engine.py - MITS Campus graph loading, caching, coordinate snapping,
and exact pathway topology built on user ground-truth coordinates for all 17 landmarks.
"""

import os
import json
from typing import Dict, Tuple, Optional, Any

import networkx as nx
from core.astar import haversine_distance


DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "graphs")
LANDMARKS_FILE   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "landmarks.json")

# Campus Centroid from exact user coordinates
CAMPUS_CENTER = (13.6305, 78.4790)


def create_mits_synthetic_campus_graph() -> nx.DiGraph:
    """
    Builds the precise pedestrian and vehicle road graph of MITS Madanapalle campus
    calibrated with the exact user coordinates matching all 17 buildings and entrance gates.
    """
    G = nx.DiGraph()

    # Exact Landmark coordinates provided by user
    nodes = {
        # Hostels & North Entrances
        "BOYS_HOSTEL":          {"y": 13.635310725303418, "x": 78.47995995131583, "name": "Boys Hostel"},
        "GIRLS_HOSTEL":         {"y": 13.633584065818326, "x": 78.48037618774832, "name": "Girls Hostel"},
        "MAIN_ENTRANCE":        {"y": 13.63326569120756,  "x": 78.47993151017306, "name": "Main Entrance Gate"},
        "GROUND":               {"y": 13.6317268849427,   "x": 78.47892675592605, "name": "MITS Ground"},
        "SECOND_ENTRANCE_GATE": {"y": 13.63120555378248,  "x": 78.47991112664288, "name": "2nd Entrance Gate"},

        # Upper Academic / North-West Wing
        "KK_BLOCK":             {"y": 13.630631316583221, "x": 78.47800468202081, "name": "KK Block"},
        "ANNAPURNA_BLOCK":      {"y": 13.630680021017103, "x": 78.47771239599888, "name": "Annapurna Block"},
        "CSE_DEPARTMENT":       {"y": 13.62997889621131,  "x": 78.47793038746299, "name": "CSE Department"},
        "GYM_MITS":             {"y": 13.629873082329585, "x": 78.47779665004937, "name": "Gym of MITS"},
        "RESEARCH_BLOCK":       {"y": 13.629588347481315, "x": 78.47775425845094, "name": "Research Block"},

        # Central & Administrative Zone
        "ADMIN_BLOCK":          {"y": 13.630295828147474, "x": 78.47938541367722, "name": "Admin Block"},
        "CIRCULAR_BLOCK":       {"y": 13.629865727426015, "x": 78.47860757305733, "name": "Circular Block"},
        "LIBRARY":              {"y": 13.62966240681394,  "x": 78.478323258912,   "name": "Library"},
        "SOUTH_BLOCK":          {"y": 13.62945704620792,  "x": 78.47864634976034, "name": "South Block"},

        # East Wing & Amenities
        "AUDITORIUM":           {"y": 13.629662406813559, "x": 78.47892407372923, "name": "Auditorium"},
        "EAST_BLOCK":           {"y": 13.62976406714236,  "x": 78.47937468484294, "name": "East Block"},
        "CANTEEN":              {"y": 13.629756247118724, "x": 78.4796831388747,  "name": "Canteen"},
    }

    for nid, data in nodes.items():
        G.add_node(nid, **data)

    # Walkway and roadway network connecting all campus buildings
    # Format: (u, v, bidirectional, highway_type, has_stairs, wheelchair_ok, name)
    edges = [
        # North Spine & Hostels
        ("BOYS_HOSTEL",          "MAIN_ENTRANCE",        True, "primary",    False, True,  "Hostel Main Access Road"),
        ("BOYS_HOSTEL",          "GIRLS_HOSTEL",         True, "pedestrian", False, True,  "Hostel Cross-Way"),
        ("GIRLS_HOSTEL",         "MAIN_ENTRANCE",        True, "pedestrian", False, True,  "Girls Hostel Avenue"),
        ("MAIN_ENTRANCE",        "SECOND_ENTRANCE_GATE", True, "primary",    False, True,  "Main Campus Boulevard"),
        ("MAIN_ENTRANCE",        "GROUND",               True, "path",       False, True,  "North Sports Walkway"),
        ("GROUND",               "SECOND_ENTRANCE_GATE", True, "pedestrian", False, True,  "East Ground Promenade"),

        # 2nd Entrance Gate to Academic Core & Admin
        ("SECOND_ENTRANCE_GATE", "ADMIN_BLOCK",          True, "primary",    False, True,  "Administrative Avenue"),
        ("SECOND_ENTRANCE_GATE", "EAST_BLOCK",           True, "pedestrian", False, True,  "East Academic Link"),
        ("GROUND",               "KK_BLOCK",             True, "pedestrian", False, True,  "Ground-KK Connector Walk"),
        ("GROUND",               "CIRCULAR_BLOCK",       True, "pedestrian", False, True,  "Central Ground Boulevard"),

        # Admin & East Complex
        ("ADMIN_BLOCK",          "CIRCULAR_BLOCK",       True, "pedestrian", False, True,  "Admin-Circular Promenade"),
        ("ADMIN_BLOCK",          "EAST_BLOCK",           True, "pedestrian", False, True,  "Admin East Corridor"),
        ("EAST_BLOCK",           "CANTEEN",              True, "pedestrian", False, True,  "Canteen Walkway"),
        ("ADMIN_BLOCK",          "CANTEEN",              True, "footway",    False, True,  "Admin Canteen Walk"),
        ("EAST_BLOCK",           "AUDITORIUM",           True, "footway",    False, True,  "East-Auditorium Concourse"),

        # Circular Block Hub Connections
        ("CIRCULAR_BLOCK",       "AUDITORIUM",           True, "footway",    False, True,  "Auditorium Plaza Walk"),
        ("CIRCULAR_BLOCK",       "SOUTH_BLOCK",          True, "footway",    False, True,  "South Block Promenade"),
        ("CIRCULAR_BLOCK",       "LIBRARY",              True, "footway",    False, True,  "Library Central Corridor"),
        ("CIRCULAR_BLOCK",       "CSE_DEPARTMENT",       True, "footway",    False, True,  "CSE Academic Spine"),
        ("CIRCULAR_BLOCK",       "KK_BLOCK",             True, "footway",    False, True,  "KK Block Approach"),

        # North-West Academic Wing (KK, Annapurna, CSE, Gym, Research)
        ("KK_BLOCK",             "ANNAPURNA_BLOCK",      True, "footway",    False, True,  "KK-Annapurna Corridor"),
        ("KK_BLOCK",             "CSE_DEPARTMENT",       True, "footway",    False, True,  "KK-CSE Connector"),
        ("ANNAPURNA_BLOCK",      "CSE_DEPARTMENT",       True, "footway",    False, True,  "Annapurna-CSE Walk"),
        ("ANNAPURNA_BLOCK",      "GYM_MITS",             True, "footway",    False, True,  "Sports Annex Pathway"),
        ("CSE_DEPARTMENT",       "GYM_MITS",             True, "footway",    False, True,  "CSE-Gym Walkway"),
        ("GYM_MITS",             "RESEARCH_BLOCK",       True, "footway",    False, True,  "Gym-Research Walkway"),
        ("CSE_DEPARTMENT",       "LIBRARY",              True, "footway",    False, True,  "CSE-Library Pathway"),
        ("RESEARCH_BLOCK",       "LIBRARY",              True, "footway",    False, True,  "Research-Library Promenade"),

        # South & Auditorium Connections
        ("LIBRARY",              "SOUTH_BLOCK",          True, "footway",    False, True,  "Library South Wing"),
        ("SOUTH_BLOCK",          "AUDITORIUM",           True, "footway",    False, True,  "South-Auditorium Link"),
        ("AUDITORIUM",           "CANTEEN",              True, "footway",    False, True,  "Auditorium-Canteen Court"),
    ]

    for u, v, bidir, highway, stairs, wheelchair, name in edges:
        cu = (G.nodes[u]["y"], G.nodes[u]["x"])
        cv = (G.nodes[v]["y"], G.nodes[v]["x"])
        dist = float(haversine_distance(cu, cv))
        attrs = {
            "length": round(dist, 4),
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
                # Verify that all 17 landmarks are present
                if G.number_of_nodes() >= 17:
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
