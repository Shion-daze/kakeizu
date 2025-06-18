# generate_tree_image.py (変数定義修正版)

import json
import networkx as nx
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

# --- 設定 ---
INPUT_JSON = "output/family_tree_merged.json"
# ▼▼▼▼▼ 欠けていた変数の定義を追加 ▼▼▼▼▼
FINAL_IMAGE_PATH = "output/family_tree_network.png"
# ▲▲▲▲▲ ここまでを追加 ▲▲▲▲▲
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"

# --- スタイルの設定 ---
BOX_WIDTH, BOX_HEIGHT = 160, 70
H_SPACING, V_SPACING = 40, 90
FONT_SIZE, SMALL_FONT_SIZE = 16, 12
LINE_WIDTH = 2
BG_COLOR = "white"


def create_graph_from_json(json_path):
    """JSONデータからnetworkxのグラフオブジェクトを作成する"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: '{json_path}' が見つかりません。")
        return None, None
    
    G = nx.Graph()
    persons = {p['id']: p for p in data.get("persons", [])}
    
    for p_id, p_data in persons.items():
        label = f"{p_data.get('name', '')}\n{p_data.get('birth_date') or ''}"
        if p_data.get('death_date'):
            label += f"\n- {p_data.get('death_date')}"
        G.add_node(p_id, data=p_data, label=label)

    for rel in data.get("relationships", []):
        source, target = rel.get('source'), rel.get('target')
        if G.has_node(source) and G.has_node(target):
            G.add_edge(source, target, type=rel.get('type'))
            
    return G, persons

def get_hierarchical_layout(graph):
    """networkxのグラフを元に、階層的なレイアウト座標を計算する"""
    parent_graph = nx.DiGraph()
    parent_graph.add_nodes_from(graph.nodes())
    parent_child_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get('type') in ['parent_child', 'adopted']]
    parent_graph.add_edges_from(parent_child_edges)

    roots = [n for n, d in parent_graph.in_degree() if d == 0]
    if not roots:
        components = [c for c in nx.weakly_connected_components(parent_graph)]
        roots = [list(c)[0] for c in components if c] if components else []

    levels = {}
    visited = set()
    for root in roots:
        if root in visited: continue
        queue = [(root, 0)]
        visited.add(root)
        levels[root] = 0
        while queue:
            node, level = queue.pop(0)
            
            for neighbor in graph.neighbors(node):
                edge_data = graph.get_edge_data(node, neighbor)
                if edge_data and edge_data.get('type') == 'spouse' and neighbor not in levels:
                    levels[neighbor] = level

            for child in parent_graph.successors(node):
                if child not in levels:
                    levels[child] = level + 1
                    if child not in visited:
                        queue.append((child, level + 1))
                        visited.add(child)
    
    nodes_by_level = defaultdict(list)
    for node, level in levels.items():
        nodes_by_level[level].append(node)
    
    unleveled_nodes = [n for n in graph.nodes() if n not in levels]
    if unleveled_nodes:
        max_level = max(levels.values()) if levels else -1
        nodes_by_level[max_level + 1].extend(unleveled_nodes)

    pos = {}
    max_width_nodes = max((len(nodes) for nodes in nodes_by_level.values()), default=0)
    
    for level, nodes in nodes_by_level.items():
        y = -level * 2.0
        level_width = len(nodes)
        x_start = - (level_width - 1) * 1.2 / 2.0
        for i, node in enumerate(sorted(nodes)):
            pos[node] = (x_start + i * 1.2, y)
            
    # 子が親の真ん中に来るようにX座標を微調整
    for level in sorted(nodes_by_level.keys(), reverse=True):
        if level > 0:
            for node in nodes_by_level[level]:
                parents = list(parent_graph.predecessors(node))
                if parents:
                    parent_x_avg = sum(pos.get(p, (0,0))[0] for p in parents) / len(parents)
                    pos[node] = (parent_x_avg, pos[node][1])

    return pos

def draw_final_tree(graph, persons, pos, output_path):
    """計算された座標を元にPillowで家系図を描画する"""
    if not pos: print("描画位置を計算できませんでした。"); return
    
    min_x, max_x = min(p[0] for p in pos.values()), max(p[0] for p in pos.values())
    min_y, max_y = min(p[1] for p in pos.values()), max(p[1] for p in pos.values())
    
    canvas_width = int(max_x - min_x + BOX_WIDTH*2)
    canvas_height = int(max_y - min_y + BOX_HEIGHT*2)
    img = Image.new('RGB', (canvas_width, canvas_height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE); small_font = ImageFont.truetype(FONT_PATH, SMALL_FONT_SIZE)
    except IOError:
        font, small_font = ImageFont.load_default(), ImageFont.load_default()
    
    x_offset, y_offset = -min_x + BOX_WIDTH, -min_y + BOX_HEIGHT

    # 接続線を描画
    for u, v, d in graph.edges(data=True):
        pos_u, pos_v = pos.get(u), pos.get(v)
        if not pos_u or not pos_v: continue
        ux, uy = pos_u[0] + x_offset, pos_u[1] + y_offset
        vx, vy = pos_v[0] + x_offset, pos_v[1] + y_offset
        
        if d.get('type') == 'spouse':
            draw.line((ux + BOX_WIDTH/2, uy, vx - BOX_WIDTH/2, vy), fill='black', width=LINE_WIDTH)
        elif d.get('type') in ['parent_child', 'adopted']:
            parent_id, child_id = u, v
            spouses = [n for n in graph.neighbors(parent_id) if graph.get_edge_data(parent_id, n).get('type') == 'spouse']
            parent_mid_x = (ux + pos.get(spouses[0], pos_u)[0] + x_offset) / 2 if spouses else ux
            
            draw.line((parent_mid_x, uy + BOX_HEIGHT/2, parent_mid_x, vy - BOX_HEIGHT/2 - V_SPACING/2), fill='gray', width=LINE_WIDTH)
            draw.line((vx, vy - BOX_HEIGHT/2, vx, vy - BOX_HEIGHT/2 - V_SPACING/2), fill='gray', width=LINE_WIDTH)

    # 人物の箱とテキストを描画
    for node_id, p in pos.items():
        px, py = p[0] + x_offset, p[1] + y_offset
        person_data = persons.get(node_id)
        if not person_data: continue
        color = 'skyblue' if person_data.get('gender') == 'M' else 'lightpink' if person_data.get('gender') == 'F' else 'lightgray'
        draw.rectangle((px - BOX_WIDTH/2, py - BOX_HEIGHT/2, px + BOX_WIDTH/2, py + BOX_HEIGHT/2), fill=color, outline='black', width=2)
        
        name, birth, death = person_data.get('name', ''), person_data.get('birth_date', ''), person_data.get('death_date', '')
        draw.text((px, py - 18), name or '', font=font, fill='black', anchor='mm')
        draw.text((px, py), birth or '', font=small_font, fill='black', anchor='mm')
        if death: draw.text((px, py + 18), f"死亡: {death}", font=small_font, fill='black', anchor='mm')
        
    img.save(output_path)
    print(f"✅ 成功！ 新しい家系図を '{output_path}' に保存しました。")

if __name__ == "__main__":
    import os
    graph, persons = create_graph_from_json(INPUT_JSON)
    if graph:
        positions = get_hierarchical_layout(graph)
        draw_final_tree(graph, persons, positions, FINAL_IMAGE_PATH)