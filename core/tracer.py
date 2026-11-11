"""
tracer.py - Records fine-grained search trace snapshots for the Educational Learning Mode.
Captures frontier evolution, open/closed sets, and g(n), h(n), f(n) computations for A*.
"""

import heapq
from itertools import count
from typing import Dict, List, Any, Optional
from core.astar import haversine_distance


def record_search_trace(
    graph,
    start_node: Any,
    goal_node: Any
) -> List[Dict[str, Any]]:
    """
    Simulates A* step-by-step and returns a timeline of trace snapshots.
    Each snapshot records:
      - step: int
      - current_node: id
      - current_name: str
      - current_coord: [lat, lon]
      - g_score, h_score, f_score: float
      - frontier: list of node IDs currently in queue
      - expanded_nodes: list of node IDs already closed
      - event: str ('start', 'expand', 'goal_reached', 'failed')
    """
    if start_node not in graph or goal_node not in graph:
        return []

    def h(u, v):
        u_coord = (graph.nodes[u]['y'], graph.nodes[u]['x'])
        v_coord = (graph.nodes[v]['y'], graph.nodes[v]['x'])
        return haversine_distance(u_coord, v_coord)

    seq = count()
    initial_h = h(start_node, goal_node)
    frontier = [(initial_h, next(seq), start_node)]

    came_from = {}
    g_score = {start_node: 0.0}
    closed_set = set()
    trace_events = []
    step_num = 1

    start_data = graph.nodes[start_node]
    trace_events.append({
        "step": step_num,
        "current_node": start_node,
        "current_name": start_data.get('name', f"Vertex {start_node}"),
        "current_coord": [start_data.get('y', 0.0), start_data.get('x', 0.0)],
        "g_score": 0.0,
        "h_score": round(initial_h, 1),
        "f_score": round(initial_h, 1),
        "frontier_count": len(frontier),
        "expanded_count": 0,
        "event": "start",
        "description": f"Initialized search at {start_data.get('name', start_node)}. h={initial_h:.1f} m"
    })

    while frontier:
        step_num += 1
        current_f, _, current = heapq.heappop(frontier)

        if current in closed_set:
            continue

        c_data = graph.nodes[current]
        g_c = g_score[current]
        h_c = h(current, goal_node)

        if current == goal_node:
            trace_events.append({
                "step": step_num,
                "current_node": current,
                "current_name": c_data.get('name', f"Vertex {current}"),
                "current_coord": [c_data.get('y', 0.0), c_data.get('x', 0.0)],
                "g_score": round(g_c, 1),
                "h_score": 0.0,
                "f_score": round(g_c, 1),
                "frontier_count": len(frontier),
                "expanded_count": len(closed_set),
                "event": "goal_reached",
                "description": f"Goal node {c_data.get('name', current)} reached! Optimal path distance: {g_c:.1f} m"
            })
            break

        closed_set.add(current)

        for neighbor in graph.neighbors(current):
            edge_data = graph.get_edge_data(current, neighbor, {})
            edge_cost = edge_data.get('length', 1.0)
            tentative_g = g_c + edge_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                h_val = h(neighbor, goal_node)
                f_val = tentative_g + h_val
                came_from[neighbor] = current
                heapq.heappush(frontier, (f_val, next(seq), neighbor))

        trace_events.append({
            "step": step_num,
            "current_node": current,
            "current_name": c_data.get('name', f"Vertex {current}"),
            "current_coord": [c_data.get('y', 0.0), c_data.get('x', 0.0)],
            "g_score": round(g_c, 1),
            "h_score": round(h_c, 1),
            "f_score": round(current_f, 1),
            "frontier_count": len(frontier),
            "expanded_count": len(closed_set),
            "event": "expand",
            "description": f"Expanded {c_data.get('name', current)}. Evaluated successors."
        })

    return trace_events
