# 🌾 VERDANT VALLEY - Multi-Agent AI Farming Simulation Game

![Python Version](https://img.shields.io/badge/Python-3.13-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.6.1-green)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

---

## 📖 Overview

Verdant Valley is a grid-based farming simulation game where multiple autonomous AI agents interact in a dynamic environment. The system is fully AI-driven with no scripted behaviors. Agents include Farmer, Guard, Fox, and Rabbit, each with independent decision-making logic.

The project integrates **Artificial Intelligence, Pathfinding, Optimization, and Evolutionary Algorithms** in a real-time simulation.

---

## 🎮 Gameplay

**Objective:** Maximize crop harvest while protecting the farm from animals.

- 👨‍🌾 **Farmer:** Harvests and plants crops using A* pathfinding
- 🛡️ **Guard:** Patrols and protects farm, catches animals
- 🦊 **Fox:** Eats crops using evolved behavior (Genetic Algorithm)
- 🐰 **Rabbit:** Nibbles crops and slows growth (Genetic Algorithm)

---

## 🧠 Core AI Algorithms

### 🔷 A* Pathfinding
Used by all agents for movement.

- Formula: f(n) = g(n) + h(n)
- Heuristic: Manhattan Distance
- Terrain-aware cost system (mud, grass, dirt, field)
- Visualized using node expansion + path overlays

---

### 🔷 CSP (Constraint Satisfaction Problem)
Used for farm planning before each season.

- Variables: grid cells  
- Domain: crop types  
- Constraints:
  - Water proximity rules
  - Sunflower only on edges
  - No adjacent sunflowers
- Solved using backtracking + forward checking

---

### 🔷 Genetic Algorithm (Animal Evolution)
Animals evolve after each Winter season.

- Chromosome traits:
  - crop_attraction
  - guard_avoidance
  - speed
  - boldness
- Fitness Function:
  - (crops eaten × 10) + survival time
- Operators:
  - Crossover (50%)
  - Mutation (15%)

---

## 🎮 Controls

- `P` → Pause / Resume  
- `ESC` → Exit to Menu  
- `R` → Restart Game  
- `E` → Genetic Algorithm Stats  
- `TAB` → Algorithm Visualization Panel  
- `N` → Node Exploration Overlay  
- `M` → Path Visualization Overlay  
- Mouse → UI interactions (plant, rain, season change)

---

## 🌦️ Seasons System

| Season | Duration | Effects |
|--------|----------|---------|
| Spring | 60s | Normal farming |
| Summer | 60s | Normal farming |
| Autumn | 60s | Normal farming |
| Winter | 60s | Only Corn & Carrot grow, water freezes |

**Rain System:**
- Activates mud terrain
- Slows movement speed
- Adds weather animation effects

---

## 📊 Scoring System

- Wheat → 50 points  
- Sunflower → 40 points  
- Corn → 60 points  
- Tomato → 55 points  
- Carrot → 35 points  
- Catch Animal (Guard) → 50 points  

---

## 🗂️ Project Structure
```bash 
Verdant Valley/
├── main.py # Game entry point
├── src/
│ ├── agents/
│ │ ├── base_agent.py # Common agent functions
│ │ ├── farmer.py # Farmer AI logic
│ │ ├── guard.py # Guard AI logic
│ │ └── animal.py # Fox & Rabbit with GA
│ ├── algorithms/
│ │ ├── astar.py # A* pathfinding
│ │ └── csp.py # CSP farm planner
│ └── world/environment/
│ ├── grid.py # Tile system, terrain
│ ├── season.py # Season & weather
│ └── clock.py # Game clock
├── game_ui/
│ ├── visualization_manager.py # TAB panel
│ ├── ga_popup.py # GA stats popup
│ ├── csp_popup.py # CSP layout popup
│ ├── year_end_screen.py # End of year screen
│ └── rain_animation.py # Rain effects
├── utils/
│ ├── constants.py # Game constants
│ └── helpers.py # Utility functions
└── assets/ # Sprites, images, audio
```


## 🚀 Installation

### Prerequisites
- Python 3.13 or higher
- pip package manager

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/verdant-valley.git
cd verdant-valley

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install pygame numpy opencv-python

# 5. Run the game
python main.py
```

## 🎯 Game Flow

Main Menu → Click START GAME
CSP Popup → Choose AUTO or CUSTOM crop layout
PLAYING → Agents start working
Crops run out → Regeneration popup appears
Winter ends → GA evolves animals → Year End Screen
CONTINUE → Next year with evolved animals

## 🔧 Configuration

Edit utils/constants.py to change:
Grid size (GRID_COLS, GRID_ROWS)
Season duration (SEASON_DURATION)
Agent speeds
Crop growth times
Scoring values

## 📈 Visualization Features

Feature	Key	Description
Algorithm Panel	TAB	Shows node counts, path costs, CSP backtracks
Node Overlay	N	Colored cells showing A* explored nodes
Path Overlay	M	Colored lines showing agent paths
GA Popup	E	Fitness scores, chromosomes, evolution history

## 👥 Team

Arwa Abbas	
Mehwish Zehra	
Asfand Ahmed	
