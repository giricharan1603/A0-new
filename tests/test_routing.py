"""
test_routing.py - Verification and Acceptance Tests for Campus Landmark A* Route Planner.
Tests TC-01 through TC-05 from PRD Section 9.
"""

import os
import sys
import pytest
import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.astar import astar_search, dijkstra_search, haversine_distance, compare_searches
from core.graph_engine import CampusGraphManager, create_mits_synthetic_campus_graph
from core.route_service import CampusRouteService


@pytest.fixture
def service():
    manager = CampusGraphManager()
    manager.get_or_load_graph()
    return CampusRouteService(manager)


def test_tc01_path_optimality_agreement(service):
    """
    TC-01: A* and baseline Dijkstra must return identical optimal path distances.
    """
    res = service.compute_route("MAIN_GATE", "CSE_BLOCK", mode="walking", include_benchmark=True)
    assert res["status"] == "SUCCESS"
    assert res["distance_meters"] > 0
    assert res["comparison"]["is_optimal_match"] is True
    assert abs(res["astar"]["distance_m"] - res["dijkstra"]["distance_m"]) < 0.1


def test_tc02_heuristic_admissibility(service):
    """
    TC-02: Haversine distance heuristic must never overestimate actual shortest path distance (h(n) <= h*(n)).
    """
    graph = service.graph
    nodes = list(graph.nodes())

    # Test admissibility across sampled pairs
    for i in range(min(5, len(nodes))):
        for j in range(i + 1, min(5, len(nodes))):
            u, v = nodes[i], nodes[j]
            coord_u = (graph.nodes[u]['y'], graph.nodes[u]['x'])
            coord_v = (graph.nodes[v]['y'], graph.nodes[v]['x'])
            h_val = haversine_distance(coord_u, coord_v)

            # True shortest path distance
            try:
                true_dist = nx.shortest_path_length(graph, u, v, weight='length')
                assert h_val <= true_dist + 1e-4, f"Heuristic violated admissibility between {u} and {v}: h={h_val} > true={true_dist}"
            except nx.NetworkXNoPath:
                pass


def test_tc03_search_space_pruning(service):
    """
    TC-03: A* must expand fewer nodes than Dijkstra on qualifying campus routes.
    """
    res = service.compute_route("MAIN_GATE", "PLAYGROUND", mode="walking", include_benchmark=True)
    assert res["status"] == "SUCCESS"
    cmp = res["comparison"]
    assert cmp["astar_nodes"] < cmp["dijkstra_nodes"], "A* failed to prune search space compared to Dijkstra"
    assert cmp["expansion_reduction_pct"] > 0


def test_tc04_disconnected_node_rejection(service):
    """
    TC-04: Disconnected destination rejected cleanly without crash.
    """
    # Create isolated disconnected node in graph
    service.graph.add_node("isolated_vertex", x=78.55, y=13.65, name="Isolated Island")
    res = service.compute_route("MAIN_GATE", "isolated_vertex", mode="walking")
    assert res["status"] == "FAILED"
    assert "No connected path" in res.get("error", "")


def test_tc05_identity_route(service):
    """
    TC-05: Start node == Goal node returns instantaneous 0.0m path.
    """
    res = service.compute_route("MAIN_GATE", "MAIN_GATE", mode="walking")
    assert res["status"] == "SUCCESS"
    assert res["distance_meters"] == 0.0
    assert len(res["path_nodes"]) == 1
    assert res["astar"]["nodes_expanded"] == 0
