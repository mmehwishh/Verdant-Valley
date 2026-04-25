# 🌾 VERDANT VALLEY - Multi-Agent AI Farming Simulation Game

![Python Version](https://img.shields.io/badge/Python-3.13-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.6.1-green)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)

## 📖 Overview
Verdant Valley is a grid-based farming simulation game where multiple autonomous AI agents interact in a dynamic environment. The system is fully AI-driven with no scripted behaviors. Agents include Farmer, Guard, Fox, and Rabbit, each with independent decision-making logic. The project integrates Artificial Intelligence, Pathfinding, Optimization, and Evolutionary Algorithms in a real-time simulation.

## 🎮 Gameplay
Objective: Maximize crop harvest while protecting the farm from animals. Farmer harvests and plants crops using A* pathfinding, Guard patrols and catches animals, Fox eats crops using Genetic Algorithm, Rabbit nibbles crops and slows growth using Genetic Algorithm.

## 🧠 Core AI Algorithms
A* Pathfinding uses f(n)=g(n)+h(n) with Manhattan distance and terrain costs, visualized with node expansion and path overlays.

CSP (Constraint Satisfaction Problem) is used for farm planning before each season with variables as grid cells, domain as crop types, and constraints like water proximity rules, sunflower edge placement, and no adjacent sunflowers using backtracking and forward checking.

Genetic Algorithm evolves animals after Winter with traits crop_attraction, guard_avoidance, speed, boldness. Fitness is (crops eaten × 10) + survival time with crossover (50%) and mutation (15%).

## 🎮 Controls
P = Pause/Resume  
ESC = Exit Menu  
R = Restart  
E = GA Stats  
TAB = Algorithm Panel  
N = Node Overlay  
M = Path Overlay  
Mouse = UI interactions  

## 🌦️ Seasons System
Spring, Summer, Autumn = normal farming  
Winter = only corn and carrot grow, water freezes  
Rain activates mud terrain, slows movement, and adds weather effects  

## 📊 Scoring System
Wheat = 50  
Sunflower = 40  
Corn = 60  
Tomato = 55  
Carrot = 35  
Catch Animal = 50  

## 🗂️ Project Structure
Verdant Valley/
├── main.py  
├── src/  
│   ├── agents/  
│   │   ├── base_agent.py  
│   │   ├── farmer.py  
│   │   ├── guard.py  
│   │   └── animal.py  
│   ├── algorithms/  
│   │   ├── astar.py  
│   │   └── csp.py  
│   └── world/  
│       ├── grid.py  
│       ├── season.py  
│       └── clock.py  
├── game_ui/  
│   ├── visualization_manager.py  
│   ├── ga_popup.py  
│   ├── csp_popup.py  
│   ├── year_end_screen.py  
│   └── rain_animation.py  
├── utils/  
│   ├── constants.py  
│   └── helpers.py  
└── assets/  

## 🚀 Installation
git clone https://github.com/yourusername/verdant-valley.git  
cd verdant-valley  
python -m venv venv  

venv\Scripts\activate (Windows)  
or  
source venv/bin/activate (Mac/Linux)  

pip install pygame numpy opencv-python  
python main.py  

## 🎯 Game Flow
Main Menu → Start Game → CSP Popup (Auto/Custom) → Gameplay → Crop Regeneration → Winter Ends → Genetic Algorithm Evolution → Year End Screen → Next Year  

## 🔧 Configuration
Edit utils/constants.py to change grid size, season duration, agent speeds, crop growth times, and scoring values.

## 📈 Visualization Features
TAB shows algorithm stats (A*, CSP)  
N shows node exploration  
M shows path visualization  
E shows genetic algorithm evolution dashboard  

## 👥 Team
Arwa Abbas  
Mehwish Zehra  
Asfand Ahmed  
