"""
realworld_router.py — End-to-end routing coordinator for real-world locations.

Ties together:
  - geocoder.py      (place name → GPS)
  - osm_fetcher.py   (GPS → road graph)
  - core/astar.py    (A* search — unchanged)
  - core/astar.py    (Dijkstra — unchanged)
"""

import math
from typing import Dict, Any, Optional

from core.astar import astar_search, dijkstra_search, compare_searches
from core.osm_fetcher import (
    fetch_graph, snap_to_node, path_to_coords, path_to_directions
)

# Travel speeds (m/s)
WALK_SPEED_MPS   = 1.4    # ~5 km/h brisk walk / pedestrian
DRIVE_SPEED_MPS  = 11.1   # ~40 km/h avg city/highway drive


def _format_duration(seconds: float) -> str:
    """Format seconds to a human-readable string."""
    total_min = int(math.ceil(seconds / 60))
    if total_min < 1:
        return "< 1 min"
    if total_min < 60:
        return f"~{total_min} min"
    hours   = total_min // 60
    minutes = total_min % 60
    if minutes == 0:
        return f"~{hours} hr"
    return f"~{hours} hr {minutes} min"


def route_realworld(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_name: str = "Start",
    end_name: str   = "Destination",
    travel_mode: str = "drive",
    run_benchmark: bool = True,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Compute the optimal real-world route between two GPS coordinates.

    Args:
        start_lat/lon:  Origin GPS coordinates.
        end_lat/lon:    Destination GPS coordinates.
        start_name:     Human-readable origin label.
        end_name:       Human-readable destination label.
        travel_mode:    "drive" | "walk"
        run_benchmark:  Also run Dijkstra for comparison metrics.
        force_refresh:  Re-download OSM graph even if cached.

    Returns:
        Dict with keys:
            status ("SUCCESS" | "FAILED"), error,
            distance_m, distance_km, duration, network_desc,
            path_coords, directions,
            astar, dijkstra, comparison,
            graph_nodes, graph_edges, snap_dist_start_m, snap_dist_end_m
    """

    # ── 1. Fetch road network ────────────────────────────────────────────────
    try:
        G, dist_km, net_desc = fetch_graph(
            start_lat, start_lon, end_lat, end_lon,
            force_refresh=force_refresh,
        )
    except Exception as exc:
        return {
            "status": "FAILED",
            "error":  f"Road network download failed: {exc}",
            "distance_m": 0.0,
            "directions": [],
            "astar": {"success": False, "nodes_expanded": 0, "execution_time_ms": 0.0},
            "dijkstra": None,
            "comparison": None,
        }

    # ── 2. Snap to nearest graph nodes ───────────────────────────────────────
    start_node, snap_start = snap_to_node(G, start_lat, start_lon)
    end_node,   snap_end   = snap_to_node(G, end_lat,   end_lon)

    warnings = []
    if snap_start > 500:
        warnings.append(
            f"Start snapped to road {snap_start:.0f} m away — "
            f"precise location may differ."
        )
    if snap_end > 500:
        warnings.append(
            f"Destination snapped to road {snap_end:.0f} m away — "
            f"precise location may differ."
        )

    if start_node is None or end_node is None:
        return {
            "status": "FAILED",
            "error":  "Could not find road nodes near the selected coordinates.",
            "distance_m": 0.0,
            "directions": [],
            "astar": {"success": False, "nodes_expanded": 0, "execution_time_ms": 0.0},
            "dijkstra": None, "comparison": None,
            "warnings": warnings,
        }

    if start_node == end_node:
        return {
            "status":     "FAILED",
            "error":      "Start and destination map to the same road node.",
            "distance_m": 0.0,
            "directions": [],
            "astar": {"success": False, "nodes_expanded": 0, "execution_time_ms": 0.0},
            "dijkstra": None, "comparison": None,
            "warnings": warnings,
        }

    # ── 3. Build edge filter for travel mode ─────────────────────────────────
    def edge_filter(u, v, data):
        hw = data.get("highway", "")
        if isinstance(hw, list):
            hw = hw[0] if hw else ""
        if travel_mode == "drive":
            foot_only = {"footway", "pedestrian", "path", "steps",
                         "cycleway", "bridleway", "corridor"}
            return hw not in foot_only
        return True  # walk: allow all

    # ── 4. A* search ────────────────────────────────────────────────────────
    astar_res = astar_search(G, start_node, end_node, edge_filter=edge_filter)

    if not astar_res["success"]:
        return {
            "status": "FAILED",
            "error":  (
                astar_res.get("error") or
                "No route found. Try a different travel mode or check connectivity."
            ),
            "distance_m": 0.0,
            "directions": [],
            "astar": astar_res,
            "dijkstra": None, "comparison": None,
            "warnings": warnings,
        }

    # ── 5. Dijkstra benchmark ────────────────────────────────────────────────
    dijkstra_res = None
    comparison   = None
    if run_benchmark:
        dijkstra_res = dijkstra_search(G, start_node, end_node, edge_filter=edge_filter)
        comparison   = compare_searches(astar_res, dijkstra_res)

    # ── 6. Build path geometry + directions ──────────────────────────────────
    path        = astar_res["path"]
    path_coords = path_to_coords(G, path)
    # Inject exact start/end coords as first/last point for precision
    path_coords[0]  = (start_lat, start_lon)
    path_coords[-1] = (end_lat,   end_lon)

    directions  = path_to_directions(G, path)

    # ── 7. Travel time estimate ───────────────────────────────────────────────
    speed_mps = DRIVE_SPEED_MPS if travel_mode == "drive" else WALK_SPEED_MPS
    duration  = _format_duration(astar_res["distance_m"] / speed_mps)

    dist_m  = astar_res["distance_m"]
    dist_km = round(dist_m / 1000.0, 2)

    return {
        "status":           "SUCCESS",
        "start_name":       start_name,
        "end_name":         end_name,
        "distance_m":       dist_m,
        "distance_km":      dist_km,
        "duration":         duration,
        "network_desc":     net_desc,
        "path_coords":      path_coords,
        "directions":       directions,
        "astar":            astar_res,
        "dijkstra":         dijkstra_res,
        "comparison":       comparison,
        "graph_nodes":      G.number_of_nodes(),
        "graph_edges":      G.number_of_edges(),
        "snap_dist_start_m": snap_start,
        "snap_dist_end_m":   snap_end,
        "warnings":         warnings,
    }
