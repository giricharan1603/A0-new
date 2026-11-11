"""
astar.py - Custom A* informed graph search algorithm with Haversine heuristic.
Provides optimal shortest path computation and k-alternative path discovery.
"""

import math
import heapq
import time
from itertools import count
from typing import Dict, List, Tuple, Optional, Any, Callable

import networkx as nx


EARTH_RADIUS_METERS = 6371000.0


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Computes the Great-Circle distance in meters between two (lat, lon) coordinates
    using the Haversine formula. Admissible and consistent for geographic graphs.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    
    # Clamp intermediate 'a' to [0.0, 1.0] to prevent domain errors with sqrt
    a = max(0.0, min(1.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_METERS * c


def astar_search(
    graph,
    start_node: Any,
    goal_node: Any,
    heuristic_func: Optional[Callable[[Any, Any], float]] = None,
    edge_filter: Optional[Callable[[Any, Any, Dict], bool]] = None
) -> Dict[str, Any]:
    """
    Executes informed A* search using a min-heap priority queue.
    
    Args:
        graph: NetworkX DiGraph or compatible graph with node coordinates and edge 'length'.
        start_node: Identifier of origin node.
        goal_node: Identifier of target node.
        heuristic_func: Function h(u, v) estimating distance in meters. If None, uses haversine on node lat/lon.
        edge_filter: Optional predicate (u, v, edge_data) -> bool. If returns False, edge is ignored.

    Returns:
        Dict containing:
            - success: bool
            - path: List[node_id]
            - distance_m: float
            - nodes_expanded: int
            - max_frontier_size: int
            - execution_time_ms: float
            - algorithm: "A*"
    """
    start_time = time.perf_counter()

    if start_node not in graph or goal_node not in graph:
        return {
            "success": False,
            "error": "Start or goal node does not exist in graph",
            "path": [],
            "distance_m": 0.0,
            "nodes_expanded": 0,
            "max_frontier_size": 0,
            "execution_time_ms": (time.perf_counter() - start_time) * 1000.0,
            "algorithm": "A*"
        }

    # Handle identity route
    if start_node == goal_node:
        return {
            "success": True,
            "path": [start_node],
            "distance_m": 0.0,
            "nodes_expanded": 0,
            "max_frontier_size": 1,
            "execution_time_ms": (time.perf_counter() - start_time) * 1000.0,
            "algorithm": "A*"
        }

    # Default heuristic resolver
    if heuristic_func is None:
        def h(u, v):
            u_coord = (graph.nodes[u]['y'], graph.nodes[u]['x'])
            v_coord = (graph.nodes[v]['y'], graph.nodes[v]['x'])
            return haversine_distance(u_coord, v_coord)
    else:
        h = heuristic_func

    # Priority queue setup: items are (f_score, tie_breaker_seq, current_node)
    seq = count()
    initial_h = h(start_node, goal_node)
    frontier = [(initial_h, next(seq), start_node)]
    
    came_from: Dict[Any, Any] = {}
    g_score: Dict[Any, float] = {start_node: 0.0}
    closed_set = set()

    nodes_expanded = 0
    max_frontier_size = len(frontier)

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        current_f, _, current = heapq.heappop(frontier)

        if current in closed_set:
            continue

        if current == goal_node:
            # Reconstruct path
            path = [current]
            curr = current
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            path.reverse()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": True,
                "path": path,
                "distance_m": round(g_score[current], 2),
                "nodes_expanded": nodes_expanded,
                "max_frontier_size": max_frontier_size,
                "execution_time_ms": round(elapsed_ms, 3),
                "algorithm": "A*"
            }

        closed_set.add(current)
        nodes_expanded += 1

        for neighbor in graph.neighbors(current):
            edge_data = graph.get_edge_data(current, neighbor, {})
            # Check edge filter (for restrictions or wheelchair accessible modes)
            if edge_filter is not None and not edge_filter(current, neighbor, edge_data):
                continue

            edge_cost = edge_data.get('length', 1.0)
            tentative_g = g_score[current] + edge_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                f_score = tentative_g + h(neighbor, goal_node)
                came_from[neighbor] = current
                heapq.heappush(frontier, (f_score, next(seq), neighbor))

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    return {
        "success": False,
        "error": "No reachable path found between start and destination",
        "path": [],
        "distance_m": 0.0,
        "nodes_expanded": nodes_expanded,
        "max_frontier_size": max_frontier_size,
        "execution_time_ms": round(elapsed_ms, 3),
        "algorithm": "A*"
    }


def find_alternative_paths(
    graph,
    start_node: Any,
    goal_node: Any,
    k: int = 2,
    edge_filter: Optional[Callable[[Any, Any, Dict], bool]] = None
) -> List[Dict[str, Any]]:
    """
    Finds up to k alternative paths using edge-penalty variant of A* search.
    Returns list of alternative path dictionaries.
    """
    primary = astar_search(graph, start_node, goal_node, edge_filter=edge_filter)
    if not primary["success"] or len(primary["path"]) < 2:
        return []

    alternatives = []
    excluded_edges = set()
    primary_path = primary["path"]

    # Try removing intermediate edges from primary path to force alternate branching
    for i in range(len(primary_path) - 1):
        if len(alternatives) >= k:
            break
        u, v = primary_path[i], primary_path[i+1]
        excluded = {(u, v), (v, u)}

        def alt_filter(edge_u, edge_v, data):
            if (edge_u, edge_v) in excluded or (edge_v, edge_u) in excluded:
                return False
            if edge_filter and not edge_filter(edge_u, edge_v, data):
                return False
            return True

        alt_res = astar_search(graph, start_node, goal_node, edge_filter=alt_filter)
        if alt_res["success"] and alt_res["path"] != primary_path:
            # Check if this alternate is already found
            already_have = any(a["path"] == alt_res["path"] for a in alternatives)
            if not already_have:
                alternatives.append(alt_res)

    return alternatives
