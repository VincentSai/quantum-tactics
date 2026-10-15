# -*- coding: utf-8 -*-
"""
Quantum Tactics - Autonomous Strategy Bot
启发式战略决策引擎 (可作为内置 Bot 或独立外部 HTTP Agent 核心)
"""

OUTPOST_POS = [2, 2]

def evaluate_and_choose_move(game_state, bot_pid):
    """
    输入 game_state 字典和 bot_pid，返回最佳合法 move 字典
    """
    valid_moves = game_state.get("valid_moves", [])
    if not valid_moves:
        return None

    players = game_state.get("players", {})
    me = players.get(bot_pid, {})
    my_pos = me.get("pos", [0, 0])
    my_hp = me.get("hp", 3)
    my_shield = me.get("shield", 0)

    # 找到所有存活敌人
    enemies = [p for pid, p in players.items() if pid != bot_pid and p.get("alive")]

    scored_moves = []
    for move in valid_moves:
        score = 0
        action = move["action"]
        target = move.get("target")

        # 1. 攻击行动评估
        if action == "ATTACK":
            target_pid = move.get("target_player")
            victim = players.get(target_pid, {})
            victim_hp = victim.get("hp", 1)
            victim_shield = victim.get("shield", 0)
            
            # 若能斩首直接得分爆发
            if victim_shield == 0 and victim_hp <= 1:
                score += 1000
            elif victim_shield > 0:
                score += 350
            else:
                score += 500

            # 如果受害者正占领前哨，优先级大幅提升
            if victim.get("pos") == OUTPOST_POS:
                score += 400

        # 2. 移动行动评估
        elif action == "MOVE":
            tx, ty = target
            # 距离中央前哨的距离
            current_dist_to_center = abs(my_pos[0] - OUTPOST_POS[0]) + abs(my_pos[1] - OUTPOST_POS[1])
            new_dist_to_center = abs(tx - OUTPOST_POS[0]) + abs(ty - OUTPOST_POS[1])
            
            # 靠近前哨加分
            score += (current_dist_to_center - new_dist_to_center) * 150
            
            # 直接占领前哨巨幅加分
            if target == OUTPOST_POS:
                score += 450

            # 吃到能量晶体加分
            if target in game_state.get("energy_crystals", []):
                score += 200

            # 若血量低且向敌人靠近则轻微减分，拉开距离保命
            if my_hp <= 1 and my_shield == 0:
                for enemy in enemies:
                    epos = enemy.get("pos")
                    old_edist = abs(my_pos[0] - epos[0]) + abs(my_pos[1] - epos[1])
                    new_edist = abs(tx - epos[0]) + abs(ty - epos[1])
                    if new_edist < old_edist:
                        score -= 100

        # 3. 护盾行动评估
        elif action == "SHIELD":
            # 检查是否有敌人在身旁 (威胁距离 <= 2)
            threat_nearby = any(abs(my_pos[0] - e["pos"][0]) + abs(my_pos[1] - e["pos"][1]) <= 2 for e in enemies)
            if threat_nearby:
                score += 300
            else:
                score += 50

        # 4. PASS 行动 (默认低优先级兜底)
        elif action == "PASS":
            score = 10

        scored_moves.append((score, move))

    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return scored_moves[0][1] if scored_moves else None
