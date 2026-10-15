# -*- coding: utf-8 -*-
"""
Quantum Tactics - Official Sample AI Agent
Demonstrates how autonomous AI agents connect, read game state, and submit moves via HTTP/JSON REST API.

Usage:
  1. Create a match and wait for opponent:
     python sample_bot.py --name "AlphaAgent" --create

  2. Join an existing match by room code:
     python sample_bot.py --name "BravoAgent" --join <ROOM_CODE>
"""

import sys
import time
import json
import argparse
import urllib.request
import urllib.error

DEFAULT_SERVER = "http://localhost:8080"
OUTPOST_POS = [2, 2]

def http_post(url, data):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Network error posting to {url}: {e}")
        return None

def http_get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Network error getting {url}: {e}")
        return None

def choose_strategic_move(state, my_pid):
    """
    Heuristic evaluation function for the agent.
    1. Lethal blow: eliminate low-health adjacent enemy.
    2. Shield if adjacent enemies threaten.
    3. Advance towards the central Quantum Outpost [2, 2] or grab Energy Crystals.
    """
    valid_moves = state.get("valid_moves", [])
    if not valid_moves:
        return None

    players = state.get("players", {})
    me = players.get(my_pid, {})
    my_pos = me.get("pos", [0, 0])
    my_hp = me.get("hp", 3)
    my_shield = me.get("shield", 0)

    best_move = None
    best_score = -9999

    for move in valid_moves:
        score = 0
        act = move["action"]
        target = move.get("target")

        if act == "ATTACK":
            target_pid = move.get("target_player")
            victim = players.get(target_pid, {})
            # Lethal priority
            if victim.get("shield", 0) == 0 and victim.get("hp", 1) <= 1:
                score += 2000
            elif victim.get("shield", 0) > 0:
                score += 400
            else:
                score += 600
            if victim.get("pos") == OUTPOST_POS:
                score += 500

        elif act == "MOVE":
            tx, ty = target
            cur_dist = abs(my_pos[0] - OUTPOST_POS[0]) + abs(my_pos[1] - OUTPOST_POS[1])
            new_dist = abs(tx - OUTPOST_POS[0]) + abs(ty - OUTPOST_POS[1])
            # Advance to outpost
            score += (cur_dist - new_dist) * 150
            if target == OUTPOST_POS:
                score += 600
            if target in state.get("energy_crystals", []):
                score += 250

        elif act == "SHIELD":
            enemies = [p for pid, p in players.items() if pid != my_pid and p.get("alive")]
            close_threat = any(abs(my_pos[0] - e["pos"][0]) + abs(my_pos[1] - e["pos"][1]) <= 2 for e in enemies)
            if close_threat and my_shield == 0:
                score += 350
            else:
                score += 20

        elif act == "PASS":
            score = -100

        if score > best_score:
            best_score = score
            best_move = move

    return best_move

def run_agent(server_url, agent_name, create_room=False, join_code=None):
    print("=" * 70)
    print(f"🤖 Starting Quantum Tactics AI Agent: {agent_name}")
    print(f"🌐 Target Server: {server_url}")
    print("=" * 70)

    match_id = None
    my_pid = None
    token = None

    if create_room:
        res = http_post(f"{server_url}/api/match/create", {"player_name": agent_name, "max_players": 2})
        if not res or not res.get("ok"):
            print(f"[!] Failed to create match: {res}")
            return
        match_id = res["match_id"]
        my_pid = res["player_id"]
        token = res["token"]
        code = res["match_code"]
        print(f"✅ Match Created! Match ID: {match_id} | Room Code: {code}")
        print(f"👉 Ask opponent to join via Room Code '{code}' or add a bot via web lobby.")
    elif join_code:
        res = http_post(f"{server_url}/api/match/join", {"match_code": join_code, "player_name": agent_name})
        if not res or not res.get("ok"):
            print(f"[!] Failed to join match with code {join_code}: {res}")
            return
        match_id = res["match_id"]
        my_pid = res["player_id"]
        token = res["token"]
        print(f"✅ Successfully joined match {match_id} as {my_pid}!")
    else:
        print("[!] Please specify --create or --join <ROOM_CODE>")
        return

    # Polling loop
    print("\n⏳ Entering match loop...")
    while True:
        state = http_get(f"{server_url}/api/match/{match_id}/state?player_id={my_pid}")
        if not state or not state.get("ok"):
            time.sleep(1)
            continue

        phase = state.get("phase")
        if phase == "LOBBY":
            print(f"[LOBBY] Waiting for players... ({len(state.get('players', {}))} joined)")
            time.sleep(1.5)
            continue

        if phase == "ENDED":
            winner = state.get("winner")
            reason = state.get("win_reason")
            if winner == my_pid:
                print(f"\n🎉 VICTORY! {agent_name} won the match! ({reason})")
            else:
                print(f"\n💀 DEFEAT! Winner: {winner} ({reason})")
            break

        curr_player = state.get("current_player")
        if curr_player == my_pid:
            me = state.get("players", {}).get(my_pid, {})
            print(f"\n▶️ Turn {state.get('turn_count')} - {agent_name}'s Turn (HP: {me.get('hp')}, AP: {me.get('ap')}, Pos: {me.get('pos')})")
            
            chosen = choose_strategic_move(state, my_pid)
            if chosen:
                act = chosen["action"]
                tgt = chosen.get("target")
                print(f"  👉 Deciding action: {act} -> target: {tgt}")
                
                m_res = http_post(f"{server_url}/api/match/{match_id}/move", {
                    "player_id": my_pid,
                    "token": token,
                    "action": act,
                    "target": tgt
                })
                if m_res and m_res.get("ok"):
                    print(f"  ✅ Move confirmed: {m_res.get('message')}")
                else:
                    print(f"  ❌ Move failed: {m_res.get('error') if m_res else 'Unknown'}")
            else:
                print("  ⚠️ No valid move, passing turn...")
                http_post(f"{server_url}/api/match/{match_id}/move", {
                    "player_id": my_pid,
                    "token": token,
                    "action": "PASS"
                })
            
            time.sleep(0.5)
        else:
            other = state.get("players", {}).get(curr_player, {})
            print(f"⌛ Waiting for opponent {other.get('name', curr_player)}'s move...", end="\r")
            time.sleep(0.8)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum Tactics AI Agent")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Server URL (default: http://localhost:8080)")
    parser.add_argument("--name", default="CyberStrategist", help="Agent Commander Name")
    parser.add_argument("--create", action="store_true", help="Create a new room and wait")
    parser.add_argument("--join", help="Join an existing room code")
    args = parser.parse_args()

    run_agent(args.server, args.name, create_room=args.create, join_code=args.join)
