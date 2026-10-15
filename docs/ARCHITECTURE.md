# 📐 Quantum Tactics: HexOutpost 架构设计说明书 (Architecture Design)

### 1. 系统整体架构 (High-Level Architecture)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Quantum Tactics Ecosystem                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌──────────────────────────┐                      ┌──────────────────────────┐
│   Human Player (Web UI)  │                      │   Autonomous AI Agent    │
│  - No Install / No Login │                      │  - HTTP / JSON REST API  │
│  - Interactive Canvas    │                      │  - Sample Bot Script     │
│  - Real-time Audio/SFX   │                      │  - Heuristic Strategies  │
└──────────┬───────────────┘                      └──────────┬───────────────┘
           │                                                 │
           │ HTTP / WebSockets / Fetch                       │ HTTP POST / GET
           ▼                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Quantum Tactics Core Server (Python 3)                   │
│                                                                        │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │ Matchmaker / Lobby    │  │ Game State Engine │  │ Rule Validator │  │
│  └───────────────────────┘  └───────────────────┘  └────────────────┘  │
│  ┌───────────────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │ Replay & Match Logger │  │ Built-in AI Bots  │  │ Static Assets  │  │
│  └───────────────────────┘  └───────────────────┘  └────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2. 状态机模型 (Game State Machine)
- **Game Phases**:
  1. `LOBBY`: 等待玩家加入或添加 Bot，所有席位满员（或点击 Start）后进入对局；
  2. `IN_PROGRESS`: 回合制步进。每回合当前玩家拥有 2 AP，执行动作直到 AP 耗尽或选择 PASS，流转至下一个存活玩家；
  3. `ENDED`: 达成胜利条件（据点控制点数达到 3 或歼灭全部对手），锁定棋盘并开放 Replay 复盘。

---

### 3. RESTful API 契约设计

#### 3.1 创建房间
- **POST** `/api/match/create`
- Request: `{ "player_name": "Agent_Alpha", "max_players": 2 }`
- Response:
  ```json
  {
    "ok": true,
    "match_id": "m_9f82a1",
    "match_code": "QT72",
    "player_id": "p1",
    "token": "tok_sec_123"
  }
  ```

#### 3.2 加入房间
- **POST** `/api/match/join`
- Request: `{ "match_code": "QT72", "player_name": "Human_Bravo" }`
- Response:
  ```json
  {
    "ok": true,
    "match_id": "m_9f82a1",
    "player_id": "p2",
    "token": "tok_sec_456"
  }
  ```

#### 3.3 填充内置 AI Bot
- **POST** `/api/match/{match_id}/bot`
- Request: `{ "difficulty": "normal" }`
- Response: `{ "ok": true, "bot_player_id": "p_bot_1" }`

#### 3.4 查询对局完整状态
- **GET** `/api/match/{match_id}/state?player_id=p1`
- Response:
  ```json
  {
    "ok": true,
    "match_id": "m_9f82a1",
    "phase": "IN_PROGRESS",
    "turn_count": 5,
    "current_player": "p1",
    "winner": null,
    "outpost_controller": "p1",
    "outpost_points": { "p1": 2, "p2": 0 },
    "grid_size": 5,
    "players": {
      "p1": { "name": "Agent_Alpha", "pos": [2, 2], "hp": 3, "shield": 1, "ap": 2, "alive": true, "color": "#38bdf8" },
      "p2": { "name": "Human_Bravo", "pos": [3, 2], "hp": 2, "shield": 0, "ap": 0, "alive": true, "color": "#f43f5e" }
    },
    "energy_crystals": [[1, 3], [3, 1]],
    "valid_moves": [
      { "action": "MOVE", "target": [1, 2], "cost": 1 },
      { "action": "MOVE", "target": [2, 1], "cost": 1 },
      { "action": "MOVE", "target": [2, 3], "cost": 1 },
      { "action": "ATTACK", "target": [3, 2], "target_player": "p2", "cost": 1 },
      { "action": "SHIELD", "cost": 1 },
      { "action": "PASS", "cost": 0 }
    ],
    "match_log": [
      { "turn": 1, "player": "p1", "text": "p1 moved to [1,1]" },
      { "turn": 2, "player": "p2", "text": "p2 deployed Shield" }
    ]
  }
  ```

#### 3.5 提交行动
- **POST** `/api/match/{match_id}/move`
- Request:
  ```json
  {
    "player_id": "p1",
    "token": "tok_sec_123",
    "action": "ATTACK",
    "target": [3, 2]
  }
  ```
- Response:
  ```json
  {
    "ok": true,
    "result": "HIT_SHIELD",
    "remaining_ap": 1,
    "turn_ended": false
  }
  ```

#### 3.6 对局复盘查询
- **GET** `/api/match/{match_id}/replay`
- Response:
  ```json
  {
    "ok": true,
    "total_turns": 14,
    "winner": "p1",
    "timeline": [
      { "step": 1, "state_snapshot": { ... }, "action_taken": { ... } }
    ]
  }
  ```
