# -*- coding: utf-8 -*-
"""
Quantum Tactics - Automated Test Suite
验证核心规则、移动碰撞、护盾防御、胜负判决与 AI 算法
"""

import unittest
from engine import GameMatch, OUTPOST_POS
from bot import evaluate_and_choose_move

class TestQuantumTactics(unittest.TestCase):
    def setUp(self):
        self.match = GameMatch("test_match_1", "TEST", max_players=2)
        self.p1_id, _ = self.match.add_player("Alice", "tok_alice")
        self.p2_id, _ = self.match.add_player("Bob", "tok_bob")

    def test_room_creation_and_start(self):
        self.assertEqual(len(self.match.player_order), 2)
        success, _ = self.match.start_match()
        self.assertTrue(success)
        self.assertEqual(self.match.phase, "IN_PROGRESS")
        self.assertEqual(self.match.get_current_player_id(), "p1")

    def test_movement_and_bounds(self):
        self.match.start_match()
        # Alice pos [0, 0] -> 合法移动为 [1, 0] 或 [0, 1]
        valid_moves = self.match.get_valid_moves("p1")
        targets = [m["target"] for m in valid_moves if m["action"] == "MOVE"]
        self.assertIn([1, 0], targets)
        self.assertIn([0, 1], targets)
        self.assertNotIn([0, 0], targets)
        self.assertNotIn([-1, 0], targets)

        # 移动到 [1, 0]
        succ, _, res = self.match.execute_move("p1", "tok_alice", "MOVE", [1, 0])
        self.assertTrue(succ)
        self.assertEqual(self.match.players["p1"]["pos"], [1, 0])
        self.assertEqual(self.match.players["p1"]["ap"], 1)

    def test_shield_defense(self):
        self.match.start_match()
        # Alice 开启护盾
        succ, _, res = self.match.execute_move("p1", "tok_alice", "SHIELD")
        self.assertTrue(succ)
        self.assertEqual(self.match.players["p1"]["shield"], 1)
        self.assertEqual(self.match.players["p1"]["ap"], 1)

        # 把 Bob 瞬移到 Alice 相邻位置 [1, 0]
        self.match.players["p2"]["pos"] = [1, 0]
        
        # 让 Alice AP 耗尽换 Bob
        self.match.execute_move("p1", "tok_alice", "PASS")
        self.assertEqual(self.match.get_current_player_id(), "p2")

        # Bob 攻击 Alice
        succ, _, res = self.match.execute_move("p2", "tok_bob", "ATTACK", [0, 0])
        self.assertTrue(succ)
        # Alice 护盾被打破，血量仍为 3
        self.assertEqual(self.match.players["p1"]["shield"], 0)
        self.assertEqual(self.match.players["p1"]["hp"], 3)

        # Bob 再次攻击 Alice
        succ, _, res = self.match.execute_move("p2", "tok_bob", "ATTACK", [0, 0])
        self.assertTrue(succ)
        # Alice 掉血，HP 变为 2
        self.assertEqual(self.match.players["p1"]["hp"], 2)

    def test_elimination_victory(self):
        self.match.start_match()
        # 将 Bob 设定为 1 HP 且无护盾，与 Alice 相邻
        self.match.players["p2"]["pos"] = [0, 1]
        self.match.players["p2"]["hp"] = 1
        self.match.players["p2"]["shield"] = 0

        # Alice 攻击 Bob
        succ, _, res = self.match.execute_move("p1", "tok_alice", "ATTACK", [0, 1])
        self.assertTrue(succ)
        self.assertEqual(self.match.phase, "ENDED")
        self.assertEqual(self.match.winner, "p1")
        self.assertIn("Elimination", self.match.win_reason)

    def test_domination_victory(self):
        self.match.start_match()
        # Alice 站在中央据点 [2, 2]
        self.match.players["p1"]["pos"] = list(OUTPOST_POS)
        
        # 3 个回合占领据点
        for round_idx in range(1, 4):
            self.match.execute_move("p1", "tok_alice", "PASS")
            if self.match.phase == "ENDED":
                break
            self.match.execute_move("p2", "tok_bob", "PASS")

        self.assertEqual(self.match.phase, "ENDED")
        self.assertEqual(self.match.winner, "p1")
        self.assertIn("Domination", self.match.win_reason)

    def test_ai_bot_decision(self):
        self.match.start_match()
        state = self.match.to_state_dict(requester_pid="p1")
        chosen = evaluate_and_choose_move(state, "p1")
        self.assertIsNotNone(chosen)
        self.assertIn(chosen["action"], ["MOVE", "ATTACK", "SHIELD", "PASS"])

if __name__ == "__main__":
    unittest.main()
