# generate_final_tree.py

import json
import networkx as nx
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import os

# --- 設定 ---
INPUT_JSON = "output/family_tree_merged.json"
OUTPUT_IMAGE = "output/family_tree_final.png"
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"

# --- スタイル設定 ---
BOX_WIDTH, BOX_HEIGHT = 160, 70
H_SPACING, V_SPACING = 50, 100
FONT_SIZE, SMALL_FONT_SIZE = 16, 12
LINE_WIDTH = 2
BG_COLOR = "white"

def create_graph_from_json(json_path):
    """JSONデータからグラフオブジェクトと人物辞書を作成する"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError: return None, None
    
    G = nx.DiGraph()
    persons = {p['id']: p for p in data.get("persons", [])}
    for p_id, p_data in persons.items():
        G.add_node(p_id, data=p_data)

    for rel in data.get("relationships", []):
        source, target = rel.get('source'), rel.get('target')
        if G.has_node(source) and G.has_node(target):
            if rel.get('type') in ['parent_child', 'adopted']:
                G.add_edge(source, target)
            elif rel.get('type') == 'spouse':
                if 'spouses' not in G.nodes[source]: G.nodes[source]['spouses'] = []
                if 'spouses' not in G.nodes[target]: G.nodes[target]['spouses'] = []
                G.nodes[source]['spouses'].append(target)
                G.nodes[target]['spouses'].append(source)
    return G, persons

def get_hierarchical_layout(graph):
    """Graphvizエンジンで基本レイアウトを計算し、プログラムで最終調整する"""
    print("--- 専門エンジンによるレイアウト計算を開始 ---")
    try:
        # Graphvizの'dot'エンジンが階層レイアウトを自動計算
        pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot')
    except Exception as e:
        print(f"Graphvizエラー: {e}\nGraphvizとpygraphvizのインストールを確認してください。"); return None

    # 夫婦が隣り合うようにX座標を調整
    for node_id in graph.nodes():
        spouses = graph.nodes[node_id].get('spouses', [])
        if spouses and node_id < spouses[0]:
            main_pos, spouse_pos = pos.get(node_id), pos.get(spouses[0])
            if main_pos and spouse_pos:
                avg_y = (main_pos[1] + spouse_pos[1]) / 2
                pos[node_id] = (main_pos[0], avg_y)
                pos[spouses[0]] = (main_pos[0] + BOX_WIDTH + H_SPACING, avg_y)
    
    # 【重なり解消ロジック】同じ階層のノードが重ならないようにX座標を調整
    print("--- レイアウトの最終調整（重なり解消）を開始 ---")
    levels = defaultdict(list)
    for node_id, p in pos.items(): levels[round(p[1])].append(node_id)
    
    for level in sorted(levels.keys()):
        sorted_nodes = sorted(levels[level], key=lambda n: pos[n][0])
        for i in range(len(sorted_nodes) - 1):
            node1, node2 = sorted_nodes[i], sorted_nodes[i+1]
            dist = pos[node2][0] - pos[node1][0]
            if dist < BOX_WIDTH + H_SPACING:
                offset = (BOX_WIDTH + H_SPACING - dist) / 2
                for n_id in sorted_nodes[:i+1]: pos[n_id] = (pos[n_id][0] - offset, pos[n_id][1])
                for n_id in sorted_nodes[i+1:]: pos[n_id] = (pos[n_id][0] + offset, pos[n_id][1])
    return pos

def draw_final_tree(graph, persons, pos, output_path):
    """計算された座標を元に、本格的な家系図を描画する"""
    print("--- 本格的な家系図の描画を開始 ---")
    if not pos: print("描画位置を計算できませんでした。"); return
    
    min_x, max_x = min(p[0] for p in pos.values()), max(p[0] for p in pos.values())
    min_y, max_y = min(p[1] for p in pos.values()), max(p[1] for p in pos.values())
    
    canvas_width = int(max_x - min_x + BOX_WIDTH * 2); canvas_height = int(max_y - min_y + BOX_HEIGHT * 2)
    img = Image.new('RGB', (canvas_width, canvas_height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    try: font, small_font = ImageFont.truetype(FONT_PATH, FONT_SIZE), ImageFont.truetype(FONT_PATH, SMALL_FONT_SIZE)
    except IOError: font, small_font = ImageFont.load_default(), ImageFont.load_default()
    
    x_offset, y_offset = -min_x + BOX_WIDTH, -min_y + BOX_HEIGHT

    # ▼▼▼▼▼ 線の描画ロジックを全面的に修正 ▼▼▼▼▼
    for node_id in graph.nodes():
        if node_id not in pos: continue
        
        # 夫婦線
        spouses = graph.nodes[node_id].get('spouses', [])
        if spouses and node_id < spouses[0] and spouses[0] in pos:
            px, py = pos[node_id][0] + x_offset, canvas_height - (pos[node_id][1] + y_offset)
            spx, spy = pos[spouses[0]][0] + x_offset, canvas_height - (pos[spouses[0]][1] + y_offset)
            draw.line((px + BOX_WIDTH/2, py, spx - BOX_WIDTH/2, spy), fill='black', width=LINE_WIDTH)

        # 親子線
        children = list(graph.successors(node_id))
        if children:
            px, py = pos[node_id][0] + x_offset, canvas_height - (pos[node_id][1] + y_offset)
            parent_mid_x = px
            # 配偶者がいれば、その中心から線を下ろす
            if spouses and spouses[0] in pos:
                spx = pos[spouses[0]][0] + x_offset
                parent_mid_x = (px + spx) / 2
            
            # 親から下に伸びるT字の縦線
            draw.line((parent_mid_x, py + BOX_HEIGHT/2, parent_mid_x, py + BOX_HEIGHT/2 + V_SPACING/2), fill='gray', width=LINE_WIDTH)
            
            child_positions = [pos[c_id] for c_id in children if c_id in pos]
            if child_positions:
                min_child_x, max_child_x = min(p[0] for p in child_positions), max(p[0] for p in child_positions)
                child_line_y = py + BOX_HEIGHT/2 + V_SPACING/2
                draw.line((min_child_x + x_offset, child_line_y, max_child_x + x_offset, child_line_y), fill='gray', width=LINE_WIDTH)
            
                for child_id in children:
                    if child_id in pos:
                        cx, cy = pos[child_id][0] + x_offset, canvas_height - (pos[child_id][1] + y_offset)
                        draw.line((cx, child_line_y, cx, cy - BOX_HEIGHT/2), fill='gray', width=LINE_WIDTH)

    # ▲▲▲▲▲ 線の描画ロジックここまで ▲▲▲▲▲

    # 人物の箱とテキストを描画
    for node_id, p_data in graph.nodes(data=True):
        if node_id not in pos: continue
        person_data = p_data['data']
        px, py = pos[node_id][0] + x_offset, canvas_height - (pos[node_id][1] + y_offset)
        color = 'skyblue' if person_data.get('gender') == 'M' else 'lightpink' if person_data.get('gender') == 'F' else 'lightgray'
        draw.rectangle((px - BOX_WIDTH/2, py - BOX_HEIGHT/2, px + BOX_WIDTH/2, py + BOX_HEIGHT/2), fill=color, outline='black', width=2)
        name, birth, death = person_data.get('name', ''), person_data.get('birth_date', ''), person_data.get('death_date', '')
        draw.text((px, py - 18), name or '', font=font, fill='black', anchor='mm')
        draw.text((px, py), birth or '', font=small_font, fill='black', anchor='mm')
        if death: draw.text((px, py + 18), f"死亡: {death}", font=small_font, fill='black', anchor='mm')
        
    img.save(output_path)
    print(f"✅ 成功！家系図を '{output_path}' に保存しました。")

if __name__ == "__main__":
    print("--- 最終家系図生成プロセスを開始 ---")
    graph, persons = create_graph_from_json(INPUT_JSON)
    if graph and persons:
        positions = get_hierarchical_layout(graph)
        if positions:
            draw_final_tree(graph, persons, positions, OUTPUT_IMAGE)