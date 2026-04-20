"""
src/algorithms/astar.py - A* Pathfinding with Terrain Costs
"""

import heapq
from utils.helpers import manhattan, neighbors_4
from utils.constants import TILE_WATER, TILE_STONE, TILE_SNOW_STONE


class AStarResult:
    def __init__(self, path, explored, cost):
        self.path = path
        self.explored = explored
        self.cost = cost


def astar(grid, start, goal, cost_dict=None, agent_type=None, rain_active=False):
    """
    A* on the weighted grid.
    Returns AStarResult(path, explored, total_cost).
    path is [] if unreachable.
    """

    # agent_type and rain_active are now explicit parameters

    if cost_dict is None:
        if agent_type == "Farmer":
            from utils.constants import FARMER_COSTS
            cost_dict = FARMER_COSTS
        elif agent_type == "Guard":
            from utils.constants import GUARD_COSTS
            cost_dict = GUARD_COSTS
        elif agent_type == "Animal":
            from utils.constants import ANIMAL_COSTS
            cost_dict = ANIMAL_COSTS
        else:
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
            if tile is None:
                continue


            if callable(cost_dict):
                move_cost = cost_dict(tile)
            else:
                move_cost = cost_dict.get(tile.type, 1.0)

            if not isinstance(move_cost, (int, float)):
                continue
            move_cost = float(move_cost)

            if move_cost == float('inf'):
                continue

            # Frozen water tiles become walkable (ice)
            if tile.type == TILE_WATER and getattr(tile, "frozen", False):
                move_cost = 1.5  # walkable but slippery

            # Custom movement rules for role-specific terrain constraints.
            if agent_type in ("Farmer", "Guard"):
                if getattr(tile, "flooded", False):
                    move_cost = float("inf")
                elif getattr(tile, "muddy", False):
                    move_cost = float("inf")
                elif tile.type == 7:
                    move_cost = float("inf")
                else:
                    if callable(cost_dict):
                        move_cost = cost_dict(tile)
                    else:
                        move_cost = cost_dict.get(tile.type, 1.0)
            elif agent_type == "Animal":
                if callable(cost_dict):
                    move_cost = cost_dict(tile)
                else:
                    move_cost = cost_dict.get(tile.type, 1.0)

            if move_cost != float("inf"):
                if getattr(tile, "wet", False):
                    move_cost += 0.2
                if getattr(tile, "frozen", False):
                    move_cost += 0.45

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
