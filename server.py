# -*- coding: utf-8 -*-
"""
Quantum Tactics: HexOutpost - Game Server
零依赖、多线程 HTTP/JSON REST API 服务与静态前端托管
"""

import os
import sys
import json
import uuid
import string
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from engine import GameMatch
from bot import evaluate_and_choose_move

PORT = 8080
MATCHES = {}  # match_id -> GameMatch
CODE_TO_ID = {}  # match_code -> match_id
LOCK = threading.Lock()

def generate_room_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        code = "".join(random.choices(chars, k=4))
        if code not in CODE_TO_ID:
            return code

def trigger_bot_turns_if_needed(match):
    """
    如果当前轮到的玩家是内置 Bot，自动驱动其完成其回合的行动
    """
    max_steps = 15  # 防止意外死循环
    step_count = 0
    while match.phase == "IN_PROGRESS" and step_count < max_steps:
        curr_pid = match.get_current_player_id()
        if not curr_pid:
            break
        curr_player = match.players.get(curr_pid)
        if not curr_player or not curr_player.get("is_bot") or not curr_player.get("alive"):
            break
            
        step_count += 1
        state = match.to_state_dict(requester_pid=curr_pid)
        chosen_move = evaluate_and_choose_move(state, curr_pid)
        if not chosen_move:
            break
            
        action = chosen_move["action"]
        target = chosen_move.get("target")
        success, msg, res = match.execute_move(curr_pid, curr_player["token"], action, target)
        if not success:
            # 若决策非法，强行 pass
            match.execute_move(curr_pid, curr_player["token"], "PASS")
            break

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class GameRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        url_path = self.path.split("?")[0]
        query_str = self.path.split("?")[1] if "?" in self.path else ""
        query_params = {}
        if query_str:
            for pair in query_str.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query_params[k] = v

        # API: 获取比赛状态
        if url_path.startswith("/api/match/") and url_path.endswith("/state"):
            parts = url_path.split("/")
            match_id = parts[3]
            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._send_json({"ok": False, "error": "Match not found"}, 404)
                pid = query_params.get("player_id")
                # 检查是否需要触发 Bot 行动
                trigger_bot_turns_if_needed(match)
                state = match.to_state_dict(requester_pid=pid)
                return self._send_json(state, 200)

        # API: 获取回放数据
        elif url_path.startswith("/api/match/") and url_path.endswith("/replay"):
            parts = url_path.split("/")
            match_id = parts[3]
            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._send_json({"ok": False, "error": "Match not found"}, 404)
                return self._send_json({
                    "ok": True,
                    "match_id": match.match_id,
                    "winner": match.winner,
                    "win_reason": match.win_reason,
                    "timeline": match.replay_timeline
                }, 200)

        # 静态文件服务
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
        target_file = "index.html" if url_path in ["", "/"] else url_path.lstrip("/")
        full_path = os.path.join(web_dir, target_file)

        if os.path.exists(full_path) and os.path.isfile(full_path):
            content_type = "text/html; charset=utf-8"
            if full_path.endswith(".js"):
                content_type = "application/javascript; charset=utf-8"
            elif full_path.endswith(".css"):
                content_type = "text/css; charset=utf-8"
            elif full_path.endswith(".json"):
                content_type = "application/json; charset=utf-8"

            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        url_path = self.path.split("?")[0]

        # API: 创建房间
        if url_path == "/api/match/create":
            player_name = req_data.get("player_name", "Commander").strip() or "Commander"
            max_players = int(req_data.get("max_players", 2))
            with LOCK:
                match_id = f"m_{uuid.uuid4().hex[:8]}"
                match_code = generate_room_code()
                match = GameMatch(match_id, match_code, max_players)
                token = f"tok_{uuid.uuid4().hex[:12]}"
                pid, err = match.add_player(player_name, token, is_bot=False)
                MATCHES[match_id] = match
                CODE_TO_ID[match_code] = match_id

                return self._send_json({
                    "ok": True,
                    "match_id": match_id,
                    "match_code": match_code,
                    "player_id": pid,
                    "token": token
                }, 201)

        # API: 加入房间
        elif url_path == "/api/match/join":
            code = req_data.get("match_code", "").strip().upper()
            player_name = req_data.get("player_name", "Tactician").strip() or "Tactician"
            with LOCK:
                match_id = CODE_TO_ID.get(code)
                if not match_id or match_id not in MATCHES:
                    return self._send_json({"ok": False, "error": f"Invalid match code: {code}"}, 404)
                match = MATCHES[match_id]
                token = f"tok_{uuid.uuid4().hex[:12]}"
                pid, err = match.add_player(player_name, token, is_bot=False)
                if err:
                    return self._send_json({"ok": False, "error": err}, 400)
                
                # 若人数达到上限，自动开启对局
                if len(match.player_order) >= match.max_players:
                    match.start_match()
                    trigger_bot_turns_if_needed(match)

                return self._send_json({
                    "ok": True,
                    "match_id": match_id,
                    "match_code": code,
                    "player_id": pid,
                    "token": token,
                    "phase": match.phase
                }, 200)

        # API: 添加内置 Bot
        elif url_path.startswith("/api/match/") and url_path.endswith("/bot"):
            parts = url_path.split("/")
            match_id = parts[3]
            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._send_json({"ok": False, "error": "Match not found"}, 404)
                
                bot_name = f"QuantumBot-{random.randint(10, 99)}"
                token = f"tok_bot_{uuid.uuid4().hex[:8]}"
                pid, err = match.add_player(bot_name, token, is_bot=True)
                if err:
                    return self._send_json({"ok": False, "error": err}, 400)

                # 若满员自动开始
                if len(match.player_order) >= match.max_players:
                    match.start_match()
                    trigger_bot_turns_if_needed(match)

                return self._send_json({
                    "ok": True,
                    "match_id": match_id,
                    "bot_player_id": pid,
                    "bot_name": bot_name,
                    "phase": match.phase
                }, 200)

        # API: 手动启动对局
        elif url_path.startswith("/api/match/") and url_path.endswith("/start"):
            parts = url_path.split("/")
            match_id = parts[3]
            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._send_json({"ok": False, "error": "Match not found"}, 404)
                success, err = match.start_match()
                if not success:
                    return self._send_json({"ok": False, "error": err}, 400)
                trigger_bot_turns_if_needed(match)
                return self._send_json({"ok": True, "phase": match.phase}, 200)

        # API: 执行行动
        elif url_path.startswith("/api/match/") and url_path.endswith("/move"):
            parts = url_path.split("/")
            match_id = parts[3]
            pid = req_data.get("player_id")
            token = req_data.get("token")
            action = req_data.get("action")
            target = req_data.get("target")

            with LOCK:
                match = MATCHES.get(match_id)
                if not match:
                    return self._send_json({"ok": False, "error": "Match not found"}, 404)
                success, msg, res = match.execute_move(pid, token, action, target)
                if not success:
                    return self._send_json({"ok": False, "error": msg}, 400)
                
                # 执行完之后，驱动后续的 Bot
                trigger_bot_turns_if_needed(match)
                return self._send_json({
                    "ok": True,
                    "message": msg,
                    "result": res,
                    "state": match.to_state_dict(requester_pid=pid)
                }, 200)

        else:
            self._send_json({"ok": False, "error": "Endpoint not found"}, 404)

def run_server(port=PORT):
    server_address = ("0.0.0.0", port)
    httpd = ThreadedHTTPServer(server_address, GameRequestHandler)
    print(f"🚀 Quantum Tactics Server running at http://localhost:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(p)
