# Tank Game

**Tank Game** is inspired by the classic Wii Tanks game, offering enhanced mechanics and expanded content.

## Features

- 🎯 **50 Levels**  
- 🤖 **19 Enemy Types**  
- 💥 **Ricochet Mechanics**  
- 🧠 **Smart AI Behavior**  

The first 20 levels closely replicate the original Wii Tanks gameplay. The final 30 levels feature unique challenges and introduce **10 brand-new enemy units**.

---

## Installation

Follow the steps below to get **Tank Game** up and running on your machine:

### 1. Install (Only works with python 3.12)

```bash
git clone https://github.com/Frode-Henrol/Tank_game
cd Tank_game
pip install -r requirements.txt
python -m tankgame
```

## Included Scripts

- `main.py` – Runs the main game.
- `map_maker.py` – Tool for creating custom maps.

---

## Map Maker Guidelines

> ⚠️ The map maker is a basic tool and not foolproof. Please follow these guidelines to avoid issues:

- Draw **polygons clockwise** to ensure proper collision detection.
- Avoid polygons with **fewer than 3 points** — this will crash the game.
- **Place the player tank first**, before placing any enemies.

### Quick Map Testing

To quickly test a map:
1. Save the map without a name or name it `map_test1`.
2. Run `main.py`.
3. Navigate to **Settings** → **Quick Play**.

---

Enjoy the game, and happy tanking!
