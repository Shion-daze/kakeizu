# draw_family_tree.py (最終版)

import json
from PIL import Image, ImageDraw, ImageFont

BOX_WIDTH, BOX_HEIGHT = 140, 60
H_SPACING, V_SPACING = 40, 60
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_SIZE, SMALL_FONT_SIZE = 14, 11

def build_data_structures(data):
    persons = {int(p['id']): p for p in data.get('persons', [])}
    for p_id in persons:
        persons[p_id]['children'] = []
        persons[p_id]['spouses'] = []
    for rel in data.get('relationships', []):
        source_id, target_id = int(rel['source']), int(rel['target'])
        if source_id not in persons or target_id not in persons: continue
        if rel['type'] == 'spouse':
            persons[source_id]['spouses'].append(target_id)
            persons[target_id]['spouses'].append(source_id)
        elif rel['type'] in ['parent_child', 'adopted']:
            persons[source_id]['children'].append(target_id)
    return persons

def get_tree_layout(persons):
    positions = {}
    subtree_widths = {}
    
    # 世代とレベルを計算
    generations = {p_id: -1 for p_id in persons}
    all_children_ids = {child_id for p in persons.values() for child_id in p.get('children', [])}
    roots = {p_id for p_id in persons if p_id not in all_children_ids}

    def assign_generation(p_id, gen):
        if generations[p_id] == -1 or gen < generations[p_id]:
            generations[p_id] = gen
            for child_id in persons[p_id].get('children', []):
                assign_generation(child_id, gen + 1)
            for spouse_id in persons[p_id].get('spouses', []):
                if generations[spouse_id] == -1:
                    assign_generation(spouse_id, gen)
    
    for root_id in sorted(list(roots)):
        assign_generation(root_id, 0)
    
    # 世代ごとにグループ化
    levels = defaultdict(list)
    for p_id, gen in generations.items():
        if gen != -1:
            levels[gen].append(p_id)

    # 座標を計算
    y_pos = 0
    for gen in sorted(levels.keys()):
        level_nodes = sorted(levels[gen])
        x_pos_start = -(len(level_nodes) - 1) * (BOX_WIDTH + H_SPACING) / 2
        for i, p_id in enumerate(level_nodes):
            positions[p_id] = (x_pos_start + i * (BOX_WIDTH + H_SPACING), y_pos)
        y_pos += BOX_HEIGHT + V_SPACING
        
    # 親の位置に基づいて子のX座標を調整（オプション、より良いレイアウトのため）
    for gen in sorted(levels.keys()):
        if gen > 0:
            for p_id in levels[gen]:
                parent_x_coords = [positions[parent_id][0] for parent_id, person in persons.items() if p_id in person.get('children', []) and parent_id in positions]
                if parent_x_coords:
                    positions[p_id] = (sum(parent_x_coords)/len(parent_x_coords), positions[p_id][1])

    return positions


def draw_tree(persons, positions, output_path):
    if not positions: return
    max_x = max(pos[0] for pos in positions.values()) + BOX_WIDTH
    min_x = min(pos[0] for pos in positions.values()) - BOX_WIDTH
    max_y = max(pos[1] for pos in positions.values()) + BOX_HEIGHT
    
    canvas_width = int(max_x - min_x); canvas_height = int(max_y + V_SPACING)
    img = Image.new('RGB', (canvas_width, canvas_height), 'white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    small_font = ImageFont.truetype(FONT_PATH, SMALL_FONT_SIZE)
    x_offset, y_offset = -min_x + H_SPACING, V_SPACING/2

    # 接続線を描画
    for p_id, person in persons.items():
        if p_id not in positions: continue
        px, py = positions[p_id][0] + x_offset, positions[p_id][1] + y_offset
        # 夫婦の線
        for spouse_id in person.get('spouses', []):
            if spouse_id in positions and p_id < spouse_id:
                sp, sy = positions[spouse_id][0] + x_offset, positions[spouse_id][1] + y_offset
                draw.line((px, py + BOX_HEIGHT/2, sp, sy + BOX_HEIGHT/2), fill='black', width=2)
        # 親子線
        if person.get('children'):
            child_y = py + BOX_HEIGHT + V_SPACING
            parent_mid_y = py + BOX_HEIGHT/2
            draw.line((px, parent_mid_y, px, parent_mid_y + V_SPACING/2), fill='black', width=2)
            child_xs = [positions[c_id][0] + x_offset for c_id in person['children'] if c_id in positions]
            if child_xs:
                draw.line((min(child_xs), parent_mid_y + V_SPACING/2, max(child_xs), parent_mid_y + V_SPACING/2), fill='black', width=2)
                for cx in child_xs:
                     draw.line((cx, parent_mid_y + V_SPACING/2, cx, child_y - BOX_HEIGHT/2), fill='black', width=2)

    # 人物の箱を描画
    for p_id, pos in positions.items():
        person = persons.get(p_id)
        if not person: continue
        px, py = pos[0] + x_offset, pos[1] + y_offset
        color = 'lightblue' if person.get('gender') == 'M' else 'lightpink' if person.get('gender') == 'F' else 'lightgray'
        draw.rectangle((px - BOX_WIDTH/2, py - BOX_HEIGHT/2, px + BOX_WIDTH/2, py + BOX_HEIGHT/2), fill=color, outline='black', width=1)
        name, birth, death = person.get('name') or '', person.get('birth_date') or '', person.get('death_date') or ''
        draw.text((px, py - 18), name, font=font, fill='black', anchor='mm')
        draw.text((px, py), birth, font=small_font, fill='black', anchor='mm')
        if death: draw.text((px, py + 15), f"- {death}", font=small_font, fill='black', anchor='mm')

    img.save(output_path)


if __name__ == "__main__":
    from collections import defaultdict
    json_path = "output/family_tree_merged.json"
    output_image_path = "output/family_tree_final.png"
    print(f"'{json_path}' から家系図データを読み込んでいます...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: '{json_path}' が見つかりません。")
        exit()
        
    persons = build_data_structures(data)
    positions = get_tree_layout(persons)
    draw_tree(persons, positions, output_image_path)
    print(f"✅ 成功！ 本格的な家系図を '{output_image_path}' に保存しました。")