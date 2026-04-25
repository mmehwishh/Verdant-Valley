# 🌾 VERDANT VALLEY - Multi-Agent AI Farming Simulation

![Python Version](https://img.shields.io/badge/Python-3.13-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.6.1-green)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

## 📖 Overview

Verdant Valley is a grid-based farming simulation where autonomous AI agents (Farmer, Guard, Fox, Rabbit) interact in a dynamic environment. All decisions are driven by AI algorithms - no scripted behaviors.

## 🎮 Gameplay

**Goal:** Harvest as many crops as possible while protecting them from animals.

| Agent | Role | Behavior |
|-------|------|----------|
| 👨‍🌾 Farmer | Harvests crops | A* pathfinding, avoids animals, plants crops |
| 🛡️ Guard | Protects farm | Patrols waypoints, alerts, chases, catches animals |
| 🦊 Fox | Destroys crops | Eats crops, evolves via Genetic Algorithm |
| 🐰 Rabbit | Nibbles crops | Reduces crop stage, evolves via Genetic Algorithm |

## 🧠 Algorithms Used

### A* Search (Pathfinding)
- Used by Farmer, Guard, and Animals  
- Formula: `f(n) = g(n) + h(n)` with Manhattan distance heuristic  
- Accounts for weighted terrain (mud, grass, dirt, field)  
- Visualized with colored node overlays and path lines  

### CSP (Constraint Satisfaction Problem)
- Runs before each season to plan farm layout  
- Each field tile = variable, crop types = domain  
- Constraints: water proximity, sunflower on edges, no adjacent sunflowers  
- Backtracking with forward checking  

### Genetic Algorithm (Animal Evolution)
- Runs at end of Winter season  
- Chromosome traits: crop_attraction, guard_avoidance, speed, boldness  
- Fitness = (crops eaten × 10) + survival time  
- Crossover (50% mix) + Mutation (15% chance)  

## 🎮 Controls

| Key | Action |
|-----|--------|
| `P` | Pause / Resume |
| `ESC` | Quit to Main Menu |
| `R` | Restart Game |
| `E` | Open GA Popup (Evolution Stats) |
| `TAB` | Toggle Algorithm Visualizer Panel |
| `N` | Toggle Node Expansion Overlay |
| `M` | Toggle Path Overlays |
| `Mouse` | Click buttons (Plant, Rain, Change Season) |

## 🌦️ Weather & Seasons

| Season | Duration | Effects |
|--------|----------|---------|
| Spring | 60 sec | Normal farming |
| Summer | 60 sec | Normal farming |
| Autumn | 60 sec | Normal farming |
| Winter | 60 sec | Only Corn & Carrot grow, water freezes |

**Rain:** Click RAINING button → mud floods, movement slows, animation plays  

## 📊 Scoring System

| Action | Points |
|--------|--------|
| Harvest Wheat | 50 |
| Harvest Sunflower | 40 |
| Harvest Corn | 60 |
| Harvest Tomato | 55 |
| Harvest Carrot | 35 |
| Catch Animal (Guard) | 50 |

## 🗂️ Project Structure
```bash
Verdant Valley/
├── main.py
├── src/
│ ├── agents/
│ │ ├── base_agent.py
│ │ ├── farmer.py
│ │ ├── guard.py
│ │ └── animal.py
│ ├── algorithms/
│ │ ├── astar.py
│ │ └── csp.py
│ └── world/environment/
│ ├── grid.py
│ ├── season.py
│ └── clock.py
├── game_ui/
│ ├── visualization_manager.py
│ ├── ga_popup.py
│ ├── csp_popup.py
│ ├── year_end_screen.py
│ └── rain_animation.py
├── utils/
│ ├── constants.py
│ └── helpers.py
└── assets/
```


## 🚀 Installation

### Prerequisites
- Python 3.13 or higher  
- pip package manager  

### Steps

```bash
git clone https://github.com/Arwa-Abbas/verdant-valley.git
cd verdant-valley

python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install pygame numpy opencv-python

python main.py
```

## 🎯 Game Flow

Main Menu → Click START GAME  
CSP Popup → Choose AUTO or CUSTOM crop layout  
PLAYING → Agents start working  
Crops run out → Regeneration popup appears  
Winter ends → GA evolves animals → Year End Screen  
CONTINUE → Next year with evolved animals  

---

## 🔧 Configuration

Edit `utils/constants.py` to change:

- Grid size (GRID_COLS, GRID_ROWS)  
- Season duration (SEASON_DURATION)  
- Agent speeds  
- Crop growth times  
- Scoring values  

---

## 📈 Visualization Features

| Feature | Key | Description |
|--------|-----|-------------|
| Algorithm Panel | TAB | Shows node counts, path costs, CSP backtracks |
| Node Overlay | N | Colored cells showing A* explored nodes |
| Path Overlay | M | Colored lines showing agent paths |
| GA Popup | E | Fitness scores, chromosomes, evolution history |

---

## 👥 Team

| Arwa Abbas |
| Mehwish Zehra |
| Asfand Ahmed |
