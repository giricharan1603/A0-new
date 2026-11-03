"""
graph_engine.py - Campus graph loading, caching, preprocessing, and coordinate snapping.
"""

import os
import json
from typing import Dict, Tuple, Optional, Any

import networkx as nx
from core.astar import haversine_distance


DEFAULT_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "graphs")
LANDMARKS_FILE   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "landmarks.json")

# MITS Madanapalle campus centroid (used for map centering)
CAMPUS_CENTER = (13.6295, 78.5030)


def simplify_multigraph_to_digraph(multigraph) -> nx.DiGraph:
    """
    FR-1.5: Convert MultiDiGraph → DiGraph, keeping min(length) for parallel edges.
    Used when downloading from OSMnx.
    """
    G = nx.DiGraph()
    for node, data in multigraph.nodes(data=True):
        G.add_node(node, **data)
    for u, v, data in multigraph.edges(data=True):
        length = float(data.get("length", 1.0))
        if G.has_edge(u, v):
            if length < G[u][v].get("length", float("inf")):
                G[u][v].update(data)
                G[u][v]["length"] = length
        else:
            G.add_edge(u, v, **dict(data, length=length))
    return G


def create_mits_synthetic_campus_graph() -> nx.DiGraph:
    """
    Builds a topologically accurate pedestrian graph of MITS Madanapalle campus.
    Node coordinates verified against campus layout (lat/lon, WGS84).
    Used as offline fallback when OSMnx is unavailable.
    """
    G = nx.DiGraph()

    nodes = {
        # Core landmarks (matched to data/landmarks.json)
        "n_gate":    {"y": 13.62810, "x": 78.50150, "name": "Main Entrance Gate"},
        "n_sec":     {"y": 13.62840, "x": 78.50170, "name": "Security Post & Entry Plaza"},
        "n_admin":   {"y": 13.62910, "x": 78.50190, "name": "Administrative Block"},
        "n_quad":    {"y": 13.62890, "x": 78.50210, "name": "Central Quadrangle"},
        "n_lib":     {"y": 13.62885, "x": 78.50245, "name": "Central Library"},
        "n_audi":    {"y": 13.62930, "x": 78.50230, "name": "Central Auditorium"},
        "n_cse":     {"y": 13.62980, "x": 78.50280, "name": "CSE & AI Block"},
        "n_ece":     {"y": 13.62940, "x": 78.50340, "name": "ECE & EEE Block"},
        "n_mech":    {"y": 13.62850, "x": 78.50380, "name": "Mech & Workshop Block"},
        "n_canteen": {"y": 13.62890, "x": 78.50420, "name": "Food Court & Canteen"},
        "n_sports":  {"y": 13.63050, "x": 78.50360, "name": "Indoor Sports Complex"},
        "n_ground":  {"y": 13.63110, "x": 78.50420, "name": "Main Athletic Ground"},
        "n_boys_h":  {"y": 13.63120, "x": 78.50220, "name": "Men's Hostel"},
        "n_girls_h": {"y": 13.63020, "x": 78.50140, "name": "Women's Hostel"},
        "n_innov":   {"y": 13.62990, "x": 78.50480, "name": "Incubation & R&D Hub"},
        # Internal pathway junctions
        "j_north":   {"y": 13.63030, "x": 78.50250, "name": "North Academic Junction"},
        "j_east":    {"y": 13.62910, "x": 78.50310, "name": "East Academic Walkway"},
        "j_ring_e":  {"y": 13.62970, "x": 78.50430, "name": "East Ring Road Waypoint"},
        "j_west":    {"y": 13.62960, "x": 78.50170, "name": "West Campus Avenue"},
    }

    for nid, data in nodes.items():
        G.add_node(nid, **data)

    # (from, to, bidirectional, highway_type, has_stairs, wheelchair_ok, path_name)
    edges = [
        ("n_gate",    "n_sec",     True,  "primary",    False, True,  "Main Entrance Boulevard"),
        ("n_sec",     "n_quad",    True,  "pedestrian", False, True,  "Central Boulevard"),
        ("n_sec",     "n_admin",   True,  "pedestrian", False, True,  "Admin Approach Walkway"),
        ("n_admin",   "n_quad",    True,  "footway",    False, True,  "Admin-Quad Walk"),
        ("n_quad",    "n_lib",     True,  "footway",    False, True,  "Library Courtyard Walk"),
        ("n_quad",    "n_audi",    True,  "footway",    True,  False, "Auditorium Tiered Steps"),
        ("n_admin",   "j_west",    True,  "service",    False, True,  "West Campus Lane"),
        ("j_west",    "n_girls_h", True,  "pedestrian", False, True,  "Girls Hostel Walk"),
        ("j_west",    "n_audi",    True,  "footway",    False, True,  "Auditorium West Ramp"),
        ("n_audi",    "j_north",   True,  "footway",    False, True,  "North Academic Spine"),
        ("n_quad",    "j_east",    True,  "pedestrian", False, True,  "Engineering Promenade"),
        ("n_lib",     "j_east",    True,  "footway",    False, True,  "Library East Path"),
        ("j_east",    "n_ece",     True,  "footway",    False, True,  "ECE South Walk"),
        ("j_east",    "n_mech",    True,  "footway",    False, True,  "Mech Workshop Avenue"),
        ("n_mech",    "n_canteen", True,  "pedestrian", False, True,  "Workshop to Canteen Path"),
        ("j_east",    "n_canteen", True,  "pedestrian", False, True,  "Central Canteen Spine"),
        ("n_ece",     "n_cse",     True,  "footway",    False, True,  "Technology Wing Corridor"),
        ("j_north",   "n_cse",     True,  "footway",    False, True,  "CSE West Access"),
        ("j_north",   "n_boys_h",  True,  "pedestrian", False, True,  "Boys Hostel Pathway"),
        ("n_cse",     "j_ring_e",  True,  "service",    False, True,  "East Ring Link"),
        ("n_canteen", "j_ring_e",  True,  "service",    False, True,  "Canteen Service Road"),
        ("j_ring_e",  "n_innov",   True,  "pedestrian", False, True,  "Innovation Hub Link"),
        ("j_ring_e",  "n_sports",  True,  "pedestrian", False, True,  "Sports Complex Avenue"),
        ("n_sports",  "n_ground",  True,  "path",       False, True,  "Stadium Track Walkway"),
        ("n_boys_h",  "n_ground",  True,  "path",       False, True,  "Hostel Sports Connector"),
        ("n_admin",   "n_gate",    False, "service",    False, True,  "Admin Exit One-Way Lane"),
    ]

    for u, v, bidir, highway, stairs, wheelchair, name in edges:
        cu = (G.nodes[u]["y"], G.nodes[u]["x"])
        cv = (G.nodes[v]["y"], G.nodes[v]["x"])
        dist = float(haversine_distance(cu, cv))
        attrs = {"length": dist, "highway": highway, "stairs": stairs,
                 "wheelchair": wheelchair, "name": name, "oneway": not bidir}
        G.add_edge(u, v, **attrs)
        if bidir:
            G.add_edge(v, u, **attrs)

    return G


class CampusGraphManager:
    """Manages graph loading, caching, coordinate snapping, and connectivity checks."""

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
        """Returns cached graph, or builds + caches a new one."""
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
            except Exception as e:
                print(f"[GraphManager] Cache load failed ({e}), rebuilding graph.")

        if place_query:
            try:
                import osmnx as ox
                G_osm = ox.graph_from_place(place_query, network_type="walk")
                self.graph = simplify_multigraph_to_digraph(G_osm)
                nx.write_graphml(self.graph, cache_path)
                return self.graph
            except Exception as e:
                print(f"[GraphManager] OSMnx download failed ({e}), using synthetic graph.")

        self.graph = create_mits_synthetic_campus_graph()
        try:
            nx.write_graphml(self.graph, cache_path)
        except Exception as e:
            print(f"[GraphManager] Cache write failed ({e}).")
        return self.graph

    def snap_coordinate_to_node(self, lat: float, lon: float) -> Tuple[Any, float, Optional[str]]:
        """Snaps (lat, lon) to the nearest graph node. Returns (node_id, dist_m, warning)."""
        if self.graph is None:
            self.get_or_load_graph()

        best_node, best_dist = None, float("inf")
        target = (lat, lon)
        for node, data in self.graph.nodes(data=True):
            d = haversine_distance(target, (data.get("y", 0.0), data.get("x", 0.0)))
            if d < best_dist:
                best_dist, best_node = d, node

        warning = (f"Nearest road node is {round(best_dist, 1)} m away (> 250 m threshold)."
                   if best_dist > 250.0 else None)
        return best_node, round(best_dist, 2), warning

    def verify_weak_connectivity(self, start: Any, goal: Any) -> bool:
        """Returns True if start and goal are in the same weakly connected component."""
        if self.graph is None or start not in self.graph or goal not in self.graph:
            return False
        for comp in nx.weakly_connected_components(self.graph):
            if start in comp and goal in comp:
                return True
        return False
