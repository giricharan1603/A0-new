"""
main.py - Campus Landmark A* Route Planner (Command Line Interface & Route Runner).
Executes CLI routing and optimal A* path discovery across campus landmarks.
"""

import os
import sys
import json
import argparse
from typing import List, Dict

# Ensure UTF-8 console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure local modules are accessible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.graph_engine import CampusGraphManager
from core.route_service import CampusRouteService


def run_campus_routes(service: CampusRouteService):
    """
    Executes automated route evaluation across distinct campus routes.
    Demonstrates A* optimal path routing and node expansion statistics.
    """
    landmarks = service.graph_manager.landmarks
    if len(landmarks) < 2:
        print("[!] Not enough landmarks to run routes.")
        return

    test_pairs = [
        ("MAIN_ENTRANCE", "CSE_DEPARTMENT"),
        ("MAIN_ENTRANCE", "CANTEEN"),
        ("MAIN_ENTRANCE", "ADMIN_BLOCK"),
        ("MAIN_ENTRANCE", "GROUND"),
        ("ADMIN_BLOCK", "KK_BLOCK"),
        ("LIBRARY", "BOYS_HOSTEL"),
        ("GIRLS_HOSTEL", "CANTEEN"),
        ("AUDITORIUM", "EAST_BLOCK"),
        ("RESEARCH_BLOCK", "GYM_MITS"),
        ("MAIN_ENTRANCE", "BOYS_HOSTEL")
    ]

    print("=" * 80)
    print("[*] CAMPUS ROUTE PLANNER: A* INFORMED SEARCH EVALUATION")
    print("=" * 80)
    print(f"{'Origin -> Destination':<35} | {'Dist(m)':<8} | {'A* Exp':<7} | {'Time(ms)':<9} | {'Status'}")
    print("-" * 80)

    results = []
    total_a_exp = 0

    for start_id, goal_id in test_pairs:
        res = service.compute_route(start_id, goal_id, mode="walking")
        if res["status"] == "SUCCESS":
            d_m = res["distance_meters"]
            a_nodes = res["astar"]["nodes_expanded"]
            a_time = res["astar"]["execution_time_ms"]
            total_a_exp += a_nodes
            route_label = f"{start_id} -> {goal_id}"

            print(f"{route_label:<35} | {d_m:<8.1f} | {a_nodes:<7} | {a_time:<9.2f} | [OK] Shortest")
            results.append({
                "route": route_label,
                "distance_m": d_m,
                "astar_nodes": a_nodes,
                "astar_time_ms": a_time,
            })
        else:
            print(f"{start_id} -> {goal_id:<20} | FAILED: {res.get('error')}")

    print("-" * 80)
    print(f"TOTAL NODES EXPANDED: A* = {total_a_exp}")
    print("=" * 80)

    # Save routes report
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "benchmark_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[OK] Route report exported to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="MITS Campus Landmark A* Route Planner")
    parser.add_argument("--start", type=str, help="Start landmark ID or lat,lon")
    parser.add_argument("--goal", type=str, help="Goal landmark ID or lat,lon")
    parser.add_argument("--mode", type=str, default="walking", choices=["walking", "driving"])
    parser.add_argument("--benchmark", action="store_true", help="Run campus test routes")

    args = parser.parse_args()

    manager = CampusGraphManager()
    manager.get_or_load_graph(force_refresh=True)
    service = CampusRouteService(manager)

    if args.benchmark or (not args.start and not args.goal):
        run_campus_routes(service)
        return

    if args.start and args.goal:
        res = service.compute_route(args.start, args.goal, mode=args.mode)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
