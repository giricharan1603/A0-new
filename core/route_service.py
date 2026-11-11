"""
route_service.py - Campus routing coordinator: turn-by-turn directions,
accessibility filters, travel time estimation, and A* shortest & alternative paths.
"""

import math
from typing import Dict, List, Tuple, Optional, Any

from core.astar import astar_search, find_alternative_paths
from core.graph_engine import CampusGraphManager


# Realistic campus travel speeds
WALKING_SPEED_MPS = 0.9   # ≈ 3.2 km/h  (campus pace incl. doors, steps, waiting)
DRIVING_SPEED_MPS = 4.17  # ≈ 15.0 km/h (campus speed limit)


class CampusRouteService:
    def __init__(self, graph_manager: Optional[CampusGraphManager] = None):
        self.graph_manager = graph_manager or CampusGraphManager()
        self.graph = self.graph_manager.get_or_load_graph()
        self.blocked_edges: set = set()

    def add_temporary_block(self, u: Any, v: Any) -> None:
        """Temporarily blocks an edge (e.g. maintenance / construction detour)."""
        self.blocked_edges.add((u, v))

    def clear_blocks(self) -> None:
        """Clears all temporary route blocks."""
        self.blocked_edges.clear()

    def _resolve_node(self, id_or_coord: Any) -> Tuple[Any, Optional[str]]:
        """
        Resolves a landmark ID string or (lat, lon) tuple to a graph node ID.
        Returns (node_id, warning_message_or_None).
        """
        warning = None

        # Case 1: coordinate tuple / list
        if isinstance(id_or_coord, (tuple, list)):
            node, _, warning = self.graph_manager.snap_coordinate_to_node(
                id_or_coord[0], id_or_coord[1]
            )
            return node, warning

        # Case 2: already a valid graph node
        if id_or_coord in self.graph:
            return id_or_coord, None

        # Case 3: landmark catalog ID → snap to nearest node
        for lm in self.graph_manager.landmarks:
            if lm["landmark_id"] == id_or_coord:
                node, _, warning = self.graph_manager.snap_coordinate_to_node(
                    lm["latitude"], lm["longitude"]
                )
                return node, warning

        return id_or_coord, f"Landmark '{id_or_coord}' not found in catalog."

    def _build_edge_filter(self, mode: str, avoid_stairs: bool, wheelchair: bool):
        """Returns an edge predicate based on travel preferences."""
        blocked = self.blocked_edges

        def edge_filter(u, v, data):
            if (u, v) in blocked:
                return False
            if avoid_stairs and data.get("stairs", False):
                return False
            if wheelchair and not data.get("wheelchair", True):
                return False
            if mode == "driving" and data.get("highway", "") in ("footway", "pedestrian", "path", "steps"):
                return False
            return True

        return edge_filter

    @staticmethod
    def _format_time(total_seconds: float) -> str:
        """Formats seconds into a human-readable campus travel estimate."""
        minutes = math.ceil(total_seconds / 60)
        if minutes < 1:
            return "< 1 min"
        return f"~ {minutes} min"

    def compute_route(
        self,
        start: Any,
        goal: Any,
        mode: str = "walking",
        avoid_stairs: bool = False,
        wheelchair_friendly: bool = False,
        include_benchmark: bool = False,
    ) -> Dict[str, Any]:
        """
        Computes the optimal campus route between two landmarks or coordinates using A* search.
        Also finds alternative available walkways.

        Returns a result dict with keys:
          status, distance_meters, distance_km, estimated_time,
          path_nodes, path_coordinates, directions, alternatives,
          astar, warnings.
        """
        start_node, start_warn = self._resolve_node(start)
        goal_node, goal_warn = self._resolve_node(goal)
        warnings = [w for w in (start_warn, goal_warn) if w]

        # Fast connectivity pre-check (< 10 ms) — avoids exhaustive search on disconnected pairs
        if not self.graph_manager.verify_weak_connectivity(start_node, goal_node):
            return {
                "status": "FAILED",
                "error": "No connected path exists between origin and destination.",
                "distance_meters": 0.0,
                "directions": [],
                "alternatives": [],
                "astar": {"success": False, "nodes_expanded": 0, "execution_time_ms": 0.0},
                "warnings": warnings,
            }

        edge_filter = self._build_edge_filter(mode, avoid_stairs, wheelchair_friendly)

        # A* informed search for shortest path
        astar_res = astar_search(self.graph, start_node, goal_node, edge_filter=edge_filter)

        if not astar_res["success"]:
            return {
                "status": "FAILED",
                "error": astar_res.get("error", "No route found under current constraints."),
                "distance_meters": 0.0,
                "directions": [],
                "alternatives": [],
                "astar": astar_res,
                "warnings": warnings,
            }

        # Build path coordinates + turn-by-turn directions
        path_nodes = astar_res["path"]
        path_coords: List[Tuple[float, float]] = []
        directions: List[Dict] = []
        cumulative = 0.0

        for i, node in enumerate(path_nodes):
            nd = self.graph.nodes[node]
            path_coords.append((nd.get("y", 0.0), nd.get("x", 0.0)))

            if i < len(path_nodes) - 1:
                nxt = path_nodes[i + 1]
                edge = self.graph.get_edge_data(node, nxt, {})
                seg = edge.get("length", 0.0)
                cumulative += seg
                directions.append({
                    "step_number": i + 1,
                    "from_node": nd.get("name", f"Node {node}"),
                    "to_node": self.graph.nodes[nxt].get("name", f"Node {nxt}"),
                    "street": edge.get("name", "Campus Pathway"),
                    "segment_meters": round(seg, 1),
                    "cumulative_meters": round(cumulative, 1),
                })

        # Discover alternative paths
        raw_alts = find_alternative_paths(self.graph, start_node, goal_node, k=2, edge_filter=edge_filter)
        alternatives = []
        for idx, alt in enumerate(raw_alts):
            alt_coords = [(self.graph.nodes[n]["y"], self.graph.nodes[n]["x"]) for n in alt["path"]]
            alternatives.append({
                "path_nodes": alt["path"],
                "coords": alt_coords,
                "distance_m": alt["distance_m"],
                "distance_km": round(alt["distance_m"] / 1000.0, 3),
                "label": f"Alternative Pathway {idx + 1} ({alt['distance_m']:.1f} m)"
            })

        speed = DRIVING_SPEED_MPS if mode == "driving" else WALKING_SPEED_MPS
        travel_time = self._format_time(astar_res["distance_m"] / speed)

        if wheelchair_friendly:
            warnings.append("Accessibility routing based on available pathway tags.")

        return {
            "status": "SUCCESS",
            "start_node": start_node,
            "goal_node": goal_node,
            "mode": mode,
            "distance_meters": astar_res["distance_m"],
            "distance_km": round(astar_res["distance_m"] / 1000.0, 3),
            "estimated_time": travel_time,
            "path_nodes": path_nodes,
            "path_coordinates": path_coords,
            "directions": directions,
            "alternatives": alternatives,
            "astar": astar_res,
            "warnings": warnings,
        }
