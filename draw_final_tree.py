# draw_final_tree.py (ソート機能修正版)

import json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import os

# --- スタイルの設定 ---
BOX_WIDTH, BOX_HEIGHT = 160, 70
H_SPACING, V_SPACING = 50, 80
SPOUSE_H_SPACING = 20
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_SIZE, SMALL_FONT_SIZE = 16, 12
LINE_WIDTH, SPOUSE_LINE_WIDTH = 2, 4
BG_COLOR = "white"

class PersonNode:
    """描画とレイアウト計算のための内部的な人物ノードクラス"""
    def __init__(self, person_data):
        self.id = person_data.get('id')
        self.data = person_data
        self.children, self.spouses, self.parents = [], [], []
        self.x = 0
        self.y = 0
        self.level = -1
        self.subtree_width = 0
        self.modifier = 0

def build_tree(persons_data, relationships_data):
    """JSONデータから家系図のノードツリーを構築する"""
    nodes = {p['id']: PersonNode(p) for p in persons_data}
    for rel in relationships_data:
        source_id, target_id = rel.get('source'), rel.get('target')
        if source_id in nodes and target_id in nodes:
            if rel['type'] == 'spouse':
                nodes[source_id].spouses.append(nodes[target_id])
                nodes[target_id].spouses.append(nodes[source_id])
            elif rel['type'] in ['parent_child', 'adopted']:
                nodes[source_id].children.append(nodes[target_id])
                nodes[target_id].parents.append(nodes[source_id])
    return nodes

def calculate_layout(nodes):
    """B.pdf形式に特化したレイアウト計算アルゴリズム"""
    roots = [node for node in nodes.values() if not node.parents]
    
    # ▼▼▼▼▼ ここが修正ポイントです ▼▼▼▼▼
    for node in nodes.values():
        # 子供を誕生日でソート（Noneを安全に扱う）
        node.children.sort(key=lambda c: c.data.get('birth_date') or '')
    # ▲▲▲▲▲ ここまでが修正ポイントです ▲▲▲▲▲

    # 世代レベルの割り当て
    for root in roots:
        queue = [(root, 0)]
        visited = {root.id}
        while queue:
            node, level = queue.pop(0)
            node.level = level
            for spouse in node.spouses:
                if spouse.id not in visited:
                    spouse.level = level
            for child in node.children:
                if child.id not in visited:
                    visited.add(child.id); queue.append((child, level + 1))
    
    levels = defaultdict(list)
    for node in nodes.values():
        if node.level != -1:
            levels[node.level].append(node)

    # X座標の計算（再帰的なボトムアップとトップダウン）
    node_order = []
    def post_order_traversal(node):
        if node in node_order: return
        for child in node.children: post_order_traversal(child)
        node_order.append(node)
    for root in roots: post_order_traversal(root)

    for node in node_order:
        if not node.children:
            node.subtree_width = BOX_WIDTH
        else:
            children_width = sum(c.subtree_width for c in node.children) + H_SPACING * (len(node.children) - 1)
            node.subtree_width = max(BOX_WIDTH, children_width)

    x_pos = 0
    for root in roots:
        root.x = x_pos + root.subtree_width / 2
        queue = [root]
        visited_pos = {root.id}
        while queue:
            node = queue.pop(0)
            
            for spouse in node.spouses:
                if spouse.id not in visited_pos:
                    spouse.x = node.x + BOX_WIDTH + SPOUSE_H_SPACING
            
            children_total_width = sum(c.subtree_width for c in node.children) + H_SPACING * (len(node.children) - 1)
            current_x = node.x - children_total_width / 2
            for child in node.children:
                child.x = current_x + child.subtree_width / 2
                current_x += child.subtree_width + H_SPACING
                if child.id not in visited_pos:
                    visited_pos.add(child.id); queue.append(child)
        x_pos += root.subtree_width + H_SPACING * 2

    positions = {n_id: (node.x, node.level * (BOX_HEIGHT + V_SPACING)) for n_id, node in nodes.items() if node.level != -1}
    return positions


def draw_tree(nodes, positions, output_path):
    """計算されたレイアウトを元に、Pillowで家系図を描画する"""
    if not positions: print("描画する人物がいません。"); return

    min_x, max_x = min(p[0] for p in positions.values()), max(p[0] for p in positions.values())
    min_y, max_y = min(p[1] for p in positions.values()), max(p[1] for p in positions.values())
    
    canvas_width = int(max_x - min_x + BOX_WIDTH*2)
    canvas_height = int(max_y - min_y + BOX_HEIGHT*2)
    img = Image.new('RGB', (canvas_width, canvas_height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE); small_font = ImageFont.truetype(FONT_PATH, SMALL_FONT_SIZE)
    x_offset, y_offset = -min_x + BOX_WIDTH, -min_y + BOX_HEIGHT/2

    for node in nodes.values():
        if node.id not in positions: continue
        px, py = positions[node.id][0] + x_offset, positions[node.id][1] + y_offset
        
        for spouse in node.spouses:
            if spouse.id in positions and node.id < spouse.id:
                spx = positions[spouse.id][0] + x_offset
                draw.line((px, py, spx, py), fill='black', width=SPOUSE_LINE_WIDTH)

        if node.children:
            parent_mid_x = px
            if node.spouses and node.spouses[0].id in positions:
                parent_mid_x = (px + positions[node.spouses[0].id][0] + x_offset) / 2
            
            draw.line((parent_mid_x, py + BOX_HEIGHT/2, parent_mid_x, py + BOX_HEIGHT/2 + V_SPACING/2), fill='gray', width=LINE_WIDTH)

            child_positions = [positions[c.id][0] + x_offset for c in node.children if c.id in positions]
            if child_positions:
                min_cx, max_cx = min(child_positions), max(child_positions)
                draw.line((min_cx, py + BOX_HEIGHT/2 + V_SPACING/2, max_cx, py + BOX_HEIGHT/2 + V_SPACING/2), fill='gray', width=LINE_WIDTH)
                for child in node.children:
                    if child.id in positions:
                        cx, cy = positions[child.id][0] + x_offset, positions[child.id][1] + y_offset
                        draw.line((cx, py + BOX_HEIGHT/2 + V_SPACING/2, cx, cy - BOX_HEIGHT/2), fill='gray', width=LINE_WIDTH)

    for node_id, pos in positions.items():
        px, py = pos[0] + x_offset, pos[1] + y_offset
        person = nodes[node_id].data
        color = 'skyblue' if person.get('gender') == 'M' else 'lightpink' if person.get('gender') == 'F' else 'lightgray'
        draw.rectangle((px - BOX_WIDTH/2, py - BOX_HEIGHT/2, px + BOX_WIDTH/2, py + BOX_HEIGHT/2), fill=color, outline='black', width=2)
        name, birth, death = person.get('name') or '', person.get('birth_date') or '', person.get('death_date') or ''
        draw.text((px, py - 18), name, font=font, fill='black', anchor='mm')
        draw.text((px, py), birth, font=small_font, fill='black', anchor='mm')
        if death: draw.text((px, py + 18), f"死亡: {death}", font=small_font, fill='black', anchor='mm')

    img.save(output_path)
    print(f"✅ 成功！ B.pdf形式の家系図を '{output_path}' に保存しました。")

if __name__ == "__main__":
    json_path = "output/family_tree_merged.json"
    output_image_path = "output/family_tree_professional.png"

    print(f"'{json_path}' から家系図データを読み込んでいます...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError: print(f"エラー: '{json_path}' が見つかりません。"); exit()
        
    nodes_map = build_tree(data['persons'], data['relationships'])
    positions = calculate_layout(nodes_map)
    if positions:
        draw_tree(nodes_map, positions, output_image_path)