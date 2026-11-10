"""
osm_fetcher.py — Downloads and caches real-world road networks from
OpenStreetMap using OSMnx. Adapts the network type and road filter
based on the distance between start and destination.

Graph cache is stored as .pkl files so repeat queries are instant.
"""

import os
import math
import time
import pickle
import hashlib
import warnings
from typing import Tuple, Optional, Any

import networkx as nx

# Suppress noisy deprecation warnings from osmnx internals
warnings.filterwarnings("ignore", category=FutureWarning, module="osmnx")

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "graph_cache"
)
os.makedirs(CACHE_DIR, exist_ok=True)


# ── Distance thresholds (km) ───────────────────────────────────────────────────
WALK_THRESHOLD   =   5.0   # < 5 km  → walking network (footways + roads)
LOCAL_THRESHOLD  =  30.0   # < 30 km → all drive roads
MEDIUM_THRESHOLD = 120.0   # < 120 km → trunk/primary/secondary only
# ≥ 120 km → motorway/trunk/primary only


def _bbox_buffer(lat1, lon1, lat2, lon2, pct: float = 0.20):
    """Expand bounding box by pct (20%) on each side."""
    south = min(lat1, lat2)
    north = max(lat1, lat2)
    west  = min(lon1, lon2)
    east  = max(lon1, lon2)

    lat_pad = max((north - south) * pct, 0.03)   # at least ~3 km pad
    lon_pad = max((east  - west)  * pct, 0.04)

    return south - lat_pad, north + lat_pad, west - lon_pad, east + lon_pad


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a  = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _cache_key(lat1, lon1, lat2, lon2, net_type: str, road_filter: str) -> str:
    raw = f"{lat1:.4f},{lon1:.4f},{lat2:.4f},{lon2:.4f},{net_type},{road_filter}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _network_params(dist_km: float) -> Tuple[str, Optional[str]]:
    """
    Returns (network_type, custom_filter) based on straight-line distance.
    custom_filter=None means fetch all roads for that network_type.
    """
    if dist_km < WALK_THRESHOLD:
        return "walk", None
    elif dist_km < LOCAL_THRESHOLD:
        return "drive", None
    elif dist_km < MEDIUM_THRESHOLD:
        # Trunk + Primary + Secondary roads only
        cf = '["highway"~"trunk|primary|secondary|trunk_link|primary_link|secondary_link"]'
        return "drive", cf
    else:
        # Motorway + Trunk + Primary only  (large inter-city distances)
        cf = '["highway"~"motorway|trunk|primary|motorway_link|trunk_link|primary_link"]'
        return "drive", cf


def _load_cache(key: str) -> Optional[nx.DiGraph]:
    path = os.path.join(CACHE_DIR, f"{key}.pkl")
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            os.remove(path)
    return None


def _save_cache(key: str, G: nx.DiGraph) -> None:
    path = os.path.join(CACHE_DIR, f"{key}.pkl")
    try:
        with open(path, "wb") as f:
            pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass


def _multigraph_to_digraph(G_multi) -> nx.DiGraph:
    """Convert OSMnx MultiDiGraph → DiGraph, keeping shortest parallel edge."""
    G = nx.DiGraph()
    for node, data in G_multi.nodes(data=True):
        G.add_node(node, **data)
    for u, v, data in G_multi.edges(data=True):
        length = float(data.get("length", 1.0))
        if G.has_edge(u, v):
            if length < G[u][v].get("length", float("inf")):
                G[u][v].update(data)
                G[u][v]["length"] = length
        else:
            G.add_edge(u, v, **dict(data, length=length))
    return G


def fetch_graph(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    force_refresh: bool = False,
) -> Tuple[nx.DiGraph, float, str]:
    """
    Download (or load from cache) the road network between two GPS points.

    Args:
        lat1, lon1: Start coordinates.
        lat2, lon2: End coordinates.
        force_refresh: If True, re-download even if cache exists.

    Returns:
        (G, dist_km, network_description)
        G: NetworkX DiGraph with 'y','x' node attrs and 'length' edge attrs.
        dist_km: Straight-line distance between points.
        network_description: Human-readable string describing network type.
    """
    import osmnx as ox

    dist_km   = _haversine_km(lat1, lon1, lat2, lon2)
    net_type, cf = _network_params(dist_km)

    ckey = _cache_key(lat1, lon1, lat2, lon2, net_type, cf or "all")

    if not force_refresh:
        G = _load_cache(ckey)
        if G is not None:
            desc = _describe_network(dist_km, net_type, cf)
            return G, dist_km, desc

    # Compute buffered bounding box
    south, north, west, east = _bbox_buffer(lat1, lon1, lat2, lon2)

    ox.settings.log_console = False
    ox.settings.timeout     = 180

    if cf:
        G_raw = ox.graph_from_bbox(
            north=north, south=south, east=east, west=west,
            network_type=net_type,
            custom_filter=cf,
            simplify=True,
            retain_all=False,
        )
    else:
        G_raw = ox.graph_from_bbox(
            north=north, south=south, east=east, west=west,
            network_type=net_type,
            simplify=True,
            retain_all=False,
        )

    G = _multigraph_to_digraph(G_raw)
    _save_cache(ckey, G)

    desc = _describe_network(dist_km, net_type, cf)
    return G, dist_km, desc


def _describe_network(dist_km: float, net_type: str, cf: Optional[str]) -> str:
    if cf is None:
        return f"{'Walking' if net_type == 'walk' else 'Full drive'} network ({dist_km:.1f} km)"
    if "motorway" in cf and "primary" in cf and "trunk" in cf and "secondary" not in cf:
        return f"Highway network — motorway/trunk/primary ({dist_km:.1f} km)"
    return f"Major roads — trunk/primary/secondary ({dist_km:.1f} km)"


def snap_to_node(G: nx.DiGraph, lat: float, lon: float) -> Tuple[Any, float]:
    """
    Find the nearest graph node to (lat, lon).

    Returns:
        (node_id, snap_distance_m)
    """
    best_node = None
    best_dist = float("inf")
    for node, data in G.nodes(data=True):
        node_lat = float(data.get("y", 0.0))
        node_lon = float(data.get("x", 0.0))
        d = _haversine_km(lat, lon, node_lat, node_lon) * 1000.0
        if d < best_dist:
            best_dist = d
            best_node = node
    return best_node, round(best_dist, 1)


def get_node_coords(G: nx.DiGraph, node: Any) -> Tuple[float, float]:
    """Return (lat, lon) for a graph node."""
    data = G.nodes[node]
    return float(data.get("y", 0.0)), float(data.get("x", 0.0))


def path_to_coords(G: nx.DiGraph, path: list) -> list:
    """Convert a list of node IDs to a list of (lat, lon) tuples."""
    return [get_node_coords(G, n) for n in path]


def path_to_directions(G: nx.DiGraph, path: list) -> list:
    """
    Build turn-by-turn directions from a path node list.

    Returns:
        List of step dicts with keys:
            step_number, street, segment_meters, cumulative_meters,
            from_coords, to_coords
    """
    directions = []
    cumulative = 0.0

    for i in range(len(path) - 1):
        u, v     = path[i], path[i + 1]
        edge     = G.get_edge_data(u, v, {})
        seg      = float(edge.get("length", 0.0))
        cumulative += seg

        # Resolve street name from OSM edge data
        raw_name = edge.get("name", "")
        if isinstance(raw_name, list):
            raw_name = raw_name[0] if raw_name else ""
        ref  = edge.get("ref", "")
        if isinstance(ref, list):
            ref = ref[0] if ref else ""

        if raw_name:
            street = raw_name
        elif ref:
            street = ref
        else:
            hw = edge.get("highway", "road")
            if isinstance(hw, list):
                hw = hw[0]
            street = hw.replace("_", " ").title()

        from_coords = get_node_coords(G, u)
        to_coords   = get_node_coords(G, v)

        directions.append({
            "step_number":        i + 1,
            "street":             street,
            "segment_meters":     round(seg, 1),
            "cumulative_meters":  round(cumulative, 1),
            "from_coords":        from_coords,
            "to_coords":          to_coords,
        })

    return directions
