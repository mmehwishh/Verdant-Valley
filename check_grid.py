# check_grid.py - Run this FIRST
import sys
import os

# Force reload without cache
for mod in list(sys.modules.keys()):
    if "constants" in mod or "grid" in mod:
        del sys.modules[mod]

from utils.constants import GRID_COLS, GRID_ROWS

print(f"📁 CONSTANTS says: {GRID_COLS} columns x {GRID_ROWS} rows")

from src.world.environment.grid import Grid

my_grid = Grid()
print(f"📁 GRID says: {my_grid.cols} columns x {my_grid.rows} rows")

print("\n" + "=" * 50)
if my_grid.cols == 18 and my_grid.rows == 14:
    print("✅✅✅ YOUR CODE IS CORRECT! Grid is 18x14! ✅✅✅")
    print(
        "The problem is VISUAL - you are just seeing 16 columns because of the camera/view?"
    )
else:
    print(f"❌❌❌ PROBLEM! Grid is {my_grid.cols}x{my_grid.rows}")
    print("❌❌❌ Should be 18x14")
    print("\n🔧 SEND ME THESE FILES:")
    print("1. utils/constants.py")
    print("2. src/world/environment/grid.py")
