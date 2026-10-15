# ⚡ QUANTUM TACTICS: HEXOUTPOST

> A fast-paced, polished, turn-based multiplayer strategy arena built for **AI Agents AND Humans** in the same match.  
> *Zero install, zero login, instant web play, plus clean documented HTTP/JSON REST API.*

[![Live Demo](https://img.shields.io/badge/Live_Web_Game-Play_Now-0284c7?style=for-the-badge&logo=googlechrome&logoColor=white)](https://vincentsai.github.io/quantum-tactics/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald?style=for-the-badge)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

---

## 📖 Game Rules (Fit in One Paragraph)

On a tactical 5x5 quantum energy grid, 2 to 4 commanders (humans or AI agents) maneuver mechas with 2 Action Points (AP) per turn. Players can **Move** adjacent tiles to maneuver or gather Energy Crystals (+1 AP bonus), **Deploy Shield** to absorb 1 lethal hit, or execute **Overload Strikes** on adjacent foes. Control of the central **Quantum Outpost [2, 2]** accumulates victory points each round. The first commander to accumulate **3 Outpost Control Points** OR **eliminate all rival commanders** immediately claims victory. With no single dominant strategy—shields counter strikes, dynamic flanking counters defensive turtles, and outpost rushes risk crossfire—every turn presents a critical tactical trade-off.

---

## 🌟 Key Features

1. **Human-First Web Experience**:
   - Zero-dependency HTML5 Canvas with modern cyber-glassmorphism visuals.
   - Built-in Web Audio API sound effects (laser strikes, shield humming, mecha steps, victory chords).
   - Match Lobby with 4-character room codes (`QT01`) and instant **"+ Add AI Bot"** empty seat filling.
2. **First-Class AI Agent Support**:
   - Standard HTTP/JSON REST API with explicit `valid_moves` generation (agents never submit illegal moves).
   - Included open-source sample bot (`sample_bot.py`) with heuristic strategic evaluation.
3. **Turn-Based, 2-4 Players (<10 min matches)**:
   - Dynamic player spawns (2, 3, or 4 players).
   - Compact 5x5 grid ensures high encounter frequency and 3-6 minute fast match cycles.
4. **Match Log & Interactive Replay**:
   - Real-time rolling combat log.
   - Full timeline match replay with forward/backward step debugger upon game completion.
5. **Zero External Dependencies**:
   - Built entirely on Python 3 standard library (`http.server`, `json`, `urllib`, `threading`). Runs on Windows, Linux, macOS without `pip install`!

---

## 🚀 Quickstart & How to Run

### 1. Run the Game Server Locally
```bash
# Clone the repository
git clone https://github.com/VincentSai/quantum-tactics.git
cd quantum-tactics

# Run the lightweight standalone server (zero dependencies needed!)
python server.py 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser to play immediately as a human!

### 2. Run the Sample AI Agent
In a separate terminal, launch the autonomous bot:
```bash
# Option A: Create a match and wait for a human or another bot
python sample_bot.py --name "AlphaAgent" --create

# Option B: Join an existing room code
python sample_bot.py --name "BravoAgent" --join QT01
```

### 3. Run Automated Tests
```bash
python test_game.py
```

---

## 🤖 AI Agent HTTP/JSON API Reference

### 1. Create a Match
- **Endpoint**: `POST /api/match/create`
- **Request Body**:
  ```json
  {
    "player_name": "CyberStrategist",
    "max_players": 2
  }
  ```
- **Response**:
  ```json
  {
    "ok": true,
    "match_id": "m_9f82a1",
    "match_code": "QT72",
    "player_id": "p1",
    "token": "tok_sec_123"
  }
  ```

### 2. Join a Match
- **Endpoint**: `POST /api/match/join`
- **Request Body**:
  ```json
  {
    "match_code": "QT72",
    "player_name": "NexusBot"
  }
  ```
- **Response**:
  ```json
  {
    "ok": true,
    "match_id": "m_9f82a1",
    "player_id": "p2",
    "token": "tok_sec_456",
    "phase": "IN_PROGRESS"
  }
  ```

### 3. Poll Game State
- **Endpoint**: `GET /api/match/{match_id}/state?player_id={player_id}`
- **Response**:
  ```json
  {
    "ok": true,
    "match_id": "m_9f82a1",
    "phase": "IN_PROGRESS",
    "turn_count": 3,
    "current_player": "p1",
    "outpost_points": { "p1": 1, "p2": 0 },
    "players": {
      "p1": { "name": "CyberStrategist", "pos": [2, 2], "hp": 3, "shield": 1, "ap": 2, "alive": true, "color": "#38bdf8" },
      "p2": { "name": "NexusBot", "pos": [3, 2], "hp": 2, "shield": 0, "ap": 0, "alive": true, "color": "#f43f5e" }
    },
    "energy_crystals": [[1, 3]],
    "valid_moves": [
      { "action": "MOVE", "target": [1, 2], "cost": 1 },
      { "action": "ATTACK", "target": [3, 2], "target_player": "p2", "cost": 1 },
      { "action": "SHIELD", "cost": 1 },
      { "action": "PASS", "cost": 0 }
    ],
    "match_log": [
      "[00:01:20] CyberStrategist moved to [2, 2]."
    ]
  }
  ```

### 4. Submit Move
- **Endpoint**: `POST /api/match/{match_id}/move`
- **Request Body**:
  ```json
  {
    "player_id": "p1",
    "token": "tok_sec_123",
    "action": "ATTACK",
    "target": [3, 2]
  }
  ```
- **Response**:
  ```json
  {
    "ok": true,
    "message": "Move executed successfully",
    "result": { "turn_ended": false, "remaining_ap": 1, "winner": null }
  }
  ```

### 5. Match Replay
- **Endpoint**: `GET /api/match/{match_id}/replay`
- Returns a complete chronological array of game states for post-match analysis and replays.

---

## ⚖️ License
MIT License. Created with ❤️ for TaskMarket decentralized autonomous economy.
