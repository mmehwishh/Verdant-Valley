"""
src/algorithms/astar.py - A* Pathfinding with Terrain Costs
"""

import heapq
from utils.helpers import manhattan, neighbors_4


class AStarResult:
    def __init__(self, path, explored, cost):
        self.path = path
        self.explored = explored
        self.cost = cost


def astar(grid, start, goal, cost_dict=None):
    """
    A* on the weighted grid.
    Returns AStarResult(path, explored, total_cost).
    path is [] if unreachable.
    """
    if cost_dict is None:
        from utils.constants import TILE_COST
        cost_dict = TILE_COST

    if start == goal:
        return AStarResult([start], set(), 0)

    open_heap = []
    heapq.heappush(open_heap, (0, 0, start))

    came_from = {start: None}
    g_cost = {start: 0}
    explored = set()

    while open_heap:
        f, g, current = heapq.heappop(open_heap)

        if current in explored:
            continue
        explored.add(current)

        if current == goal:
            path = _reconstruct(came_from, goal)
            return AStarResult(path, explored, g)

        col, row = current
        for nc, nr in neighbors_4(col, row, grid.cols, grid.rows):
            tile = grid.get(nc, nr)
            move_cost = cost_dict.get(tile.type if tile else None, 1.0)

            # Skip impassable tiles
            if move_cost == float("inf"):
                continue

            new_g = g + move_cost
            if new_g < g_cost.get((nc, nr), float("inf")):
                g_cost[(nc, nr)] = new_g
                h = manhattan((nc, nr), goal)
                heapq.heappush(open_heap, (new_g + h, new_g, (nc, nr)))
                came_from[(nc, nr)] = current

    return AStarResult([], explored, float("inf"))


def _reconstruct(came_from, node):
    path = []
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path
