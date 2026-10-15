# -*- coding: utf-8 -*-
"""
Quantum Tactics: HexOutpost - Core Game Engine
纯 Python 零外部依赖游戏状态机与裁判引擎
"""

import copy
import random
import time

OUTPOST_POS = [2, 2]
BOARD_SIZE = 5
MAX_OUTPOST_POINTS = 3
INITIAL_HP = 3
INITIAL_AP = 2

PLAYER_SPAWNS = [
    [0, 0],  # P1: Top-Left (Blue)
    [4, 4],  # P2: Bottom-Right (Red)
    [0, 4],  # P3: Top-Right (Emerald)
    [4, 0]   # P4: Bottom-Left (Amber)
]

PLAYER_COLORS = ["#38bdf8", "#f43f5e", "#10b981", "#f59e0b"]

class GameMatch:
    def __init__(self, match_id, match_code, max_players=2):
        self.match_id = match_id
        self.match_code = match_code.upper()
        self.max_players = max(2, min(4, max_players))
        self.phase = "LOBBY"  # LOBBY, IN_PROGRESS, ENDED
        self.turn_count = 0
        self.current_player_idx = 0
        self.winner = None
        self.win_reason = ""
        self.created_at = time.time()
        
        self.players = {}  # pid -> { name, token, pos, hp, shield, ap, alive, color, is_bot }
        self.player_order = []  # [pid1, pid2, ...]
        self.outpost_points = {}  # pid -> count
        self.energy_crystals = [[1, 3], [3, 1]]  # 能量晶体位置
        self.match_log = []
        self.replay_timeline = []

    def add_player(self, name, token, is_bot=False):
        if len(self.player_order) >= self.max_players:
            return None, "Room is full"
        if self.phase != "LOBBY":
            return None, "Match already started"
            
        slot_idx = len(self.player_order)
        pid = f"p{slot_idx + 1}"
        spawn_pos = PLAYER_SPAWNS[slot_idx]
        color = PLAYER_COLORS[slot_idx]

        player_data = {
            "id": pid,
            "name": name,
            "token": token,
            "pos": list(spawn_pos),
            "hp": INITIAL_HP,
            "shield": 0,
            "ap": INITIAL_AP,
            "alive": True,
            "color": color,
            "is_bot": is_bot
        }
        self.players[pid] = player_data
        self.player_order.append(pid)
        self.outpost_points[pid] = 0
        
        self.log(f"{name} joined the room as {pid}")
        self._record_snapshot(f"Player {name} joined")
        return pid, None

    def start_match(self):
        if len(self.player_order) < 2:
            return False, "Need at least 2 players to start"
        self.phase = "IN_PROGRESS"
        self.turn_count = 1
        self.current_player_idx = 0
        curr_p = self.players[self.player_order[0]]
        curr_p["ap"] = INITIAL_AP
        self.log(f"Match started! Round 1, Player {curr_p['name']} turn.")
        self._record_snapshot("Match started")
        return True, None

    def get_current_player_id(self):
        if not self.player_order:
            return None
        return self.player_order[self.current_player_idx]

    def get_valid_moves(self, pid):
        if self.phase != "IN_PROGRESS":
            return []
        if pid != self.get_current_player_id():
            return []
            
        p = self.players[pid]
        if not p["alive"] or p["ap"] <= 0:
            return []

        moves = []
        px, py = p["pos"]
        occupied_positions = {tuple(other["pos"]): other_id for other_id, other in self.players.items() if other["alive"] and other_id != pid}

        # 1. 移动 MOVE (上下左右相邻 1 格且未被占据)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = px + dx, py + dy
            if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                if (nx, ny) not in occupied_positions:
                    moves.append({
                        "action": "MOVE",
                        "target": [nx, ny],
                        "cost": 1,
                        "description": f"Move to [{nx}, {ny}]"
                    })

        # 2. 攻击 ATTACK (距离 1 格以内的相邻敌对目标)
        for other_id, other in self.players.items():
            if other_id != pid and other["alive"]:
                ox, oy = other["pos"]
                dist = abs(px - ox) + abs(py - oy)
                if dist == 1:
                    moves.append({
                        "action": "ATTACK",
                        "target": [ox, oy],
                        "target_player": other_id,
                        "cost": 1,
                        "description": f"Attack {other['name']} at [{ox}, {oy}]"
                    })

        # 3. 部署护盾 SHIELD (若当前无护盾)
        if p["shield"] < 1:
            moves.append({
                "action": "SHIELD",
                "cost": 1,
                "description": "Deploy Quantum Forcefield"
            })

        # 4. 放弃/结束回合 PASS
        moves.append({
            "action": "PASS",
            "cost": 0,
            "description": "End turn early"
        })

        return moves

    def execute_move(self, pid, token, action, target=None):
        if self.phase != "IN_PROGRESS":
            return False, "Match is not in progress", None
        if pid != self.get_current_player_id():
            return False, f"Not your turn. Current turn: {self.get_current_player_id()}", None
            
        p = self.players[pid]
        if p["token"] != token:
            return False, "Invalid authentication token", None
        if not p["alive"]:
            return False, "Player is eliminated", None

        action = action.upper()
        valid_moves = self.get_valid_moves(pid)
        
        # 验证 action 是否合法
        is_valid = False
        target_pos = list(target) if target else None
        
        for vm in valid_moves:
            if vm["action"] == action:
                if action in ["MOVE", "ATTACK"]:
                    if target_pos == vm.get("target"):
                        is_valid = True
                        break
                else:
                    is_valid = True
                    break

        if not is_valid:
            return False, f"Illegal move: action={action}, target={target}", None

        event_text = ""
        # 执行动作
        if action == "PASS":
            p["ap"] = 0
            event_text = f"{p['name']} passed remaining AP."
        elif action == "MOVE":
            p["pos"] = target_pos
            p["ap"] -= 1
            event_text = f"{p['name']} moved to {target_pos}."
            # 检查是否采集到能量晶体
            if target_pos in self.energy_crystals:
                self.energy_crystals.remove(target_pos)
                p["ap"] += 1
                event_text += " Captured Energy Crystal (+1 AP bonus)!"
        elif action == "SHIELD":
            p["shield"] = 1
            p["ap"] -= 1
            event_text = f"{p['name']} deployed Quantum Shield."
        elif action == "ATTACK":
            # 找到被攻击目标
            target_pid = None
            for oid, o in self.players.items():
                if o["alive"] and o["pos"] == target_pos:
                    target_pid = oid
                    break
            
            p["ap"] -= 1
            if target_pid:
                victim = self.players[target_pid]
                if victim["shield"] > 0:
                    victim["shield"] = 0
                    event_text = f"{p['name']} struck {victim['name']}, shattering their Shield!"
                else:
                    victim["hp"] -= 1
                    event_text = f"{p['name']} hit {victim['name']} for 1 damage (HP: {victim['hp']})!"
                    if victim["hp"] <= 0:
                        victim["alive"] = False
                        victim["hp"] = 0
                        event_text += f" 💥 {victim['name']} was ELIMINATED!"

        self.log(event_text)
        self._record_snapshot(event_text)

        # 检查是否达成歼灭获胜
        alive_players = [pl for pl in self.players.values() if pl["alive"]]
        if len(alive_players) == 1:
            self.winner = alive_players[0]["id"]
            self.win_reason = f"Elimination: All opposing commanders destroyed."
            self.phase = "ENDED"
            self.log(f"🏆 Victory! {alive_players[0]['name']} won by {self.win_reason}")
            self._record_snapshot(f"Winner declared: {self.winner}")
            return True, "Winner declared", {"turn_ended": True, "winner": self.winner}

        # 如果当前玩家 AP 耗尽，流转回合
        turn_ended = False
        if p["ap"] <= 0:
            turn_ended = True
            self._advance_turn()

        return True, "Move executed successfully", {
            "turn_ended": turn_ended,
            "remaining_ap": p["ap"],
            "winner": self.winner
        }

    def _advance_turn(self):
        # 检查前哨占领状态
        outpost_occupant = None
        for pid, pl in self.players.items():
            if pl["alive"] and pl["pos"] == OUTPOST_POS:
                outpost_occupant = pid
                break

        if outpost_occupant:
            self.outpost_points[outpost_occupant] += 1
            occ_name = self.players[outpost_occupant]["name"]
            self.log(f"⚡ Central Outpost controlled by {occ_name}! (Points: {self.outpost_points[outpost_occupant]}/{MAX_OUTPOST_POINTS})")
            if self.outpost_points[outpost_occupant] >= MAX_OUTPOST_POINTS:
                self.winner = outpost_occupant
                self.win_reason = f"Domination: Controlled Central Outpost for {MAX_OUTPOST_POINTS} rounds."
                self.phase = "ENDED"
                self.log(f"🏆 Victory! {occ_name} won by {self.win_reason}")
                self._record_snapshot(f"Winner declared: {self.winner}")
                return

        # 寻找下一个存活玩家
        for _ in range(len(self.player_order)):
            self.current_player_idx = (self.current_player_idx + 1) % len(self.player_order)
            next_pid = self.player_order[self.current_player_idx]
            if self.players[next_pid]["alive"]:
                self.turn_count += 1
                next_p = self.players[next_pid]
                next_p["ap"] = INITIAL_AP
                self.log(f"Round {self.turn_count}: {next_p['name']}'s turn.")
                break

    def log(self, text):
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.match_log.append(f"[{timestamp}] {text}")
        if len(self.match_log) > 60:
            self.match_log.pop(0)

    def _record_snapshot(self, action_desc):
        snapshot = {
            "step": len(self.replay_timeline) + 1,
            "action": action_desc,
            "phase": self.phase,
            "turn_count": self.turn_count,
            "current_player": self.get_current_player_id(),
            "winner": self.winner,
            "outpost_points": dict(self.outpost_points),
            "players": {
                pid: {
                    "name": p["name"],
                    "pos": list(p["pos"]),
                    "hp": p["hp"],
                    "shield": p["shield"],
                    "alive": p["alive"],
                    "color": p["color"]
                } for pid, p in self.players.items()
            }
        }
        self.replay_timeline.append(snapshot)

    def to_state_dict(self, requester_pid=None):
        outpost_controller = None
        for pid, pl in self.players.items():
            if pl["alive"] and pl["pos"] == OUTPOST_POS:
                outpost_controller = pid
                break

        curr_pid = self.get_current_player_id()
        valid_moves = []
        if requester_pid and requester_pid == curr_pid and self.phase == "IN_PROGRESS":
            valid_moves = self.get_valid_moves(requester_pid)

        return {
            "ok": True,
            "match_id": self.match_id,
            "match_code": self.match_code,
            "phase": self.phase,
            "turn_count": self.turn_count,
            "current_player": curr_pid,
            "winner": self.winner,
            "win_reason": self.win_reason,
            "outpost_pos": OUTPOST_POS,
            "outpost_controller": outpost_controller,
            "outpost_points": dict(self.outpost_points),
            "max_outpost_points": MAX_OUTPOST_POINTS,
            "board_size": BOARD_SIZE,
            "players": {
                pid: {
                    "id": p["id"],
                    "name": p["name"],
                    "pos": p["pos"],
                    "hp": p["hp"],
                    "shield": p["shield"],
                    "ap": p["ap"],
                    "alive": p["alive"],
                    "color": p["color"],
                    "is_bot": p["is_bot"]
                } for pid, p in self.players.items()
            },
            "energy_crystals": [list(c) for c in self.energy_crystals],
            "valid_moves": valid_moves,
            "match_log": list(self.match_log)
        }
