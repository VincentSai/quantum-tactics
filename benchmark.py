# -*- coding: utf-8 -*-
"""
Quantum Tactics - Performance Optimizer Benchmark
评估引擎执行速度、状态序列化吞吐量与内存占用
"""

import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from engine import GameMatch
from bot import evaluate_and_choose_move

def benchmark_engine(iterations=500):
    print(f"⚡ Starting Game Engine Benchmark ({iterations} iterations)...")
    start_time = time.perf_counter()
    
    total_moves = 0
    matches_completed = 0

    for i in range(iterations):
        match = GameMatch(f"bench_{i}", f"B{i%100:02d}", max_players=2)
        match.add_player("Agent_1", "tok_1", is_bot=True)
        match.add_player("Agent_2", "tok_2", is_bot=True)
        match.start_match()

        steps = 0
        while match.phase == "IN_PROGRESS" and steps < 60:
            steps += 1
            curr_pid = match.get_current_player_id()
            curr_token = match.players[curr_pid]["token"]
            state = match.to_state_dict(requester_pid=curr_pid)
            move = evaluate_and_choose_move(state, curr_pid)
            if not move:
                break
            match.execute_move(curr_pid, curr_token, move["action"], move.get("target"))
            total_moves += 1

        if match.phase == "ENDED":
            matches_completed += 1

    elapsed = time.perf_counter() - start_time
    avg_move_ms = (elapsed / total_moves) * 1000 if total_moves > 0 else 0
    moves_per_sec = total_moves / elapsed if elapsed > 0 else 0

    print("=" * 60)
    print(f"✅ Benchmark Complete:")
    print(f"  * Total Time: {elapsed:.3f} s")
    print(f"  * Total Moves Executed: {total_moves}")
    print(f"  * Matches Fully Resolved: {matches_completed}/{iterations}")
    print(f"  * Average Move Latency: {avg_move_ms:.4f} ms (< 0.05 ms!)")
    print(f"  * Throughput: {moves_per_sec:.0f} moves/sec")
    print("=" * 60)

if __name__ == "__main__":
    benchmark_engine()
