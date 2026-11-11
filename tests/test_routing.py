"""
test_routing.py - Verification and Acceptance Tests for Campus Landmark A* Route Planner.
Tests A* optimality, admissibility, alternative path discovery, and network connectivity.
"""

import os
import sys
import pytest
import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.astar import astar_search, find_alternative_paths, haversine_distance
from core.graph_engine import CampusGraphManager, create_mits_synthetic_campus_graph
from core.route_service import CampusRouteService


@pytest.fixture
def service():
    manager = CampusGraphManager()
    manager.get_or_load_graph(force_refresh=True)
    return CampusRouteService(manager)


def test_tc01_astar_path_optimality(service):
    """
    TC-01: A* search must return optimal shortest path distance matching true graph shortest path.
    """
    res = service.compute_route("MAIN_ENTRANCE", "CSE_DEPARTMENT", mode="walking")
    assert res["status"] == "SUCCESS"
    assert res["distance_meters"] > 0
    true_shortest = nx.shortest_path_length(service.graph, "MAIN_ENTRANCE", "CSE_DEPARTMENT", weight="length")
    assert abs(res["distance_meters"] - true_shortest) < 0.1


def test_tc02_heuristic_admissibility(service):
    """
    TC-02: Haversine distance heuristic must never overestimate actual shortest path distance (h(n) <= h*(n)).
    """
    graph = service.graph
    nodes = list(graph.nodes())

    # Test admissibility across sampled pairs
    for i in range(min(6, len(nodes))):
        for j in range(i + 1, min(6, len(nodes))):
            u, v = nodes[i], nodes[j]
            coord_u = (graph.nodes[u]['y'], graph.nodes[u]['x'])
            coord_v = (graph.nodes[v]['y'], graph.nodes[v]['x'])
            h_val = haversine_distance(coord_u, coord_v)

            try:
                true_dist = nx.shortest_path_length(graph, u, v, weight='length')
                assert h_val <= true_dist + 0.05, f"Heuristic violated admissibility between {u} and {v}: h={h_val} > true={true_dist}"
            except nx.NetworkXNoPath:
                pass


def test_tc03_alternative_paths_discovery(service):
    """
    TC-03: System must discover available alternative paths between campus buildings.
    """
    res = service.compute_route("MAIN_ENTRANCE", "CANTEEN", mode="walking")
    assert res["status"] == "SUCCESS"
    assert "alternatives" in res
    assert res["distance_meters"] > 0


def test_tc04_disconnected_node_rejection(service):
    """
    TC-04: Disconnected destination rejected cleanly without crash.
    """
    service.graph.add_node("isolated_vertex", x=78.55, y=13.65, name="Isolated Island")
    res = service.compute_route("MAIN_ENTRANCE", "isolated_vertex", mode="walking")
    assert res["status"] == "FAILED"
    assert "No connected path" in res.get("error", "")


def test_tc05_identity_route(service):
    """
    TC-05: Start node == Goal node returns instantaneous 0.0m path.
    """
    res = service.compute_route("MAIN_ENTRANCE", "MAIN_ENTRANCE", mode="walking")
    assert res["status"] == "SUCCESS"
    assert res["distance_meters"] == 0.0
    assert len(res["path_nodes"]) == 1
    assert res["astar"]["nodes_expanded"] == 0


def test_tc06_all_17_landmarks_accessible(service):
    """
    TC-06: All 17 defined campus landmarks must exist in graph and be routable from Main Entrance.
    """
    landmarks = service.graph_manager.landmarks
    assert len(landmarks) >= 17
    for lm in landmarks:
        lid = lm["landmark_id"]
        res = service.compute_route("MAIN_ENTRANCE", lid, mode="walking")
        assert res["status"] == "SUCCESS", f"Landmark {lid} not reachable from MAIN_ENTRANCE"
