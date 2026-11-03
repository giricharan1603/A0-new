"""
main.py - Campus Landmark A* Route Planner (Command Line Interface & Benchmark Runner).
Executes CLI routing, A* vs Dijkstra benchmarks, and test scenarios.
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
from core.astar import compare_searches


def run_benchmark_suite(service: CampusRouteService):
    """
    Executes automated benchmark evaluation across distinct campus routes.
    Demonstrates optimality agreement and node expansion reduction.
    """
    landmarks = service.graph_manager.landmarks
    if len(landmarks) < 2:
        print("[!] Not enough landmarks to run benchmarks.")
        return

    test_pairs = [
        ("MAIN_GATE", "CSE_BLOCK"),
        ("MAIN_GATE", "CANTEEN"),
        ("MAIN_GATE", "SPORTS_COMPLEX"),
        ("MAIN_GATE", "PLAYGROUND"),
        ("ADMIN_BLOCK", "INNOVATION_HUB"),
        ("MITS_LIB", "BOYS_HOSTEL"),
        ("GIRLS_HOSTEL", "CANTEEN"),
        ("AUDITORIUM", "ECE_BLOCK"),
        ("MECH_BLOCK", "SPORTS_COMPLEX"),
        ("MAIN_GATE", "BOYS_HOSTEL")
    ]

    print("=" * 80)
    print("[*] CAMPUS ROUTE PLANNER: A* vs DIJKSTRA BENCHMARK EVALUATION")
    print("=" * 80)
    print(f"{'Origin -> Destination':<35} | {'Dist(m)':<8} | {'A* Exp':<7} | {'Dijk Exp':<8} | {'Reduction':<10} | {'Status'}")
    print("-" * 80)

    results = []
    total_a_exp = 0
    total_d_exp = 0

    for start_id, goal_id in test_pairs:
        res = service.compute_route(start_id, goal_id, mode="walking", include_benchmark=True)
        if res["status"] == "SUCCESS":
            cmp = res["comparison"]
            d_m = res["distance_meters"]
            a_nodes = cmp["astar_nodes"]
            d_nodes = cmp["dijkstra_nodes"]
            red_pct = f"{cmp['expansion_reduction_pct']}%"
            match = "[OK] Optimal" if cmp["is_optimal_match"] else "[!] Mismatch"

            total_a_exp += a_nodes
            total_d_exp += d_nodes
            route_label = f"{start_id} -> {goal_id}"

            print(f"{route_label:<35} | {d_m:<8.1f} | {a_nodes:<7} | {d_nodes:<8} | {red_pct:<10} | {match}")
            results.append({
                "route": route_label,
                "distance_m": d_m,
                "astar_nodes": a_nodes,
                "dijkstra_nodes": d_nodes,
                "reduction_pct": cmp["expansion_reduction_pct"],
                "astar_time_ms": cmp["astar_time_ms"],
                "dijkstra_time_ms": cmp["dijkstra_time_ms"],
                "optimal_match": cmp["is_optimal_match"]
            })
        else:
            print(f"{start_id} -> {goal_id:<20} | FAILED: {res.get('error')}")

    print("-" * 80)
    overall_red = round(((total_d_exp - total_a_exp) / total_d_exp) * 100.0, 1) if total_d_exp > 0 else 0
    print(f"TOTAL NODES EXPANDED: A* = {total_a_exp} | Dijkstra = {total_d_exp} | Overall Reduction: {overall_red}%")
    print("=" * 80)

    # Save benchmark report
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = os.path.join(reports_dir, "benchmark_results.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[OK] Benchmark report exported to: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Campus Landmark A* Route Planner CLI")
    parser.add_argument("--start", type=str, default="MAIN_GATE", help="Origin landmark ID")
    parser.add_argument("--goal", type=str, default="CSE_BLOCK", help="Destination landmark ID")
    parser.add_argument("--mode", type=str, choices=["walking", "driving"], default="walking", help="Travel mode")
    parser.add_argument("--avoid-stairs", action="store_true", help="Avoid stairs and steps")
    parser.add_argument("--wheelchair", action="store_true", help="Enable wheelchair accessibility")
    parser.add_argument("--benchmark", action="store_true", help="Run full benchmark test suite across campus")

    args = parser.parse_args()

    manager = CampusGraphManager()
    service = CampusRouteService(manager)

    if args.benchmark:
        run_benchmark_suite(service)
        return

    print(f"[*] Calculating route from '{args.start}' to '{args.goal}' ({args.mode})...")
    res = service.compute_route(
        args.start,
        args.goal,
        mode=args.mode,
        avoid_stairs=args.avoid_stairs,
        wheelchair_friendly=args.wheelchair,
        include_benchmark=True
    )

    if res["status"] != "SUCCESS":
        print(f"[!] Routing Failed: {res.get('error')}")
        if res.get("warnings"):
            for w in res["warnings"]:
                print(f"    - {w}")
        return

    print("\n" + "=" * 60)
    print(f"[*] OPTIMAL CAMPUS ROUTE SUMMARY")
    print("=" * 60)
    print(f"  * Distance:       {res['distance_meters']} meters ({res['distance_km']} km)")
    print(f"  * Estimated Time: {res['estimated_time']}")
    print(f"  * Path Vertices:  {len(res['path_nodes'])} vertices traversed")

    if res.get("comparison"):
        cmp = res["comparison"]
        print("\n[*] ALGORITHM PERFORMANCE (A* vs DIJKSTRA):")
        print(f"  * Nodes Expanded: A* = {cmp['astar_nodes']}  |  Dijkstra = {cmp['dijkstra_nodes']} (Reduction: {cmp['expansion_reduction_pct']}%)")
        print(f"  * Execution Time: A* = {cmp['astar_time_ms']}ms | Dijkstra = {cmp['dijkstra_time_ms']}ms (Speedup: {cmp['speedup']}x)")
        print(f"  * Optimality:     {'100% Agreement (Distances Identical)' if cmp['is_optimal_match'] else 'Discrepancy Detected'}")

    print("\n[*] TURN-BY-TURN DIRECTIONS:")
    for step in res["directions"]:
        print(f"  {step['step_number']}. Along {step['street']:<30} -> {step['to_node']:<25} ({step['segment_meters']}m)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
