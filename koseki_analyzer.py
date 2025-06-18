# koseki_analyzer.py

import sys
import os
import json
import glob
from collections import defaultdict
import networkx as nx
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# --- グローバル設定 ---
PAGES_OUTPUT_DIR = "output/pages"
MERGED_JSON_PATH = "output/family_tree_merged.json"
FINAL_IMAGE_PATH = "output/family_tree_final.png"
FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
BOX_WIDTH, BOX_HEIGHT = 160, 70
H_SPACING, V_SPACING = 40, 90
FONT_SIZE, SMALL_FONT_SIZE = 16, 12
LINE_WIDTH, BG_COLOR = 2, "white"

# --- 機能ごとの関数定義 ---

def process_and_synthesize(pdf_path):
    """【ステップ1】PDFを解析し、統合されたJSONデータを作成する"""
    from pdf2image import convert_from_path
    from google.cloud import vision
    import vertexai
    from vertexai.generative_models import GenerativeModel
    from io import BytesIO

    # --- AIによるページごとの解析 ---
    print("--- AIによる自動解析を開始 ---")
    load_dotenv()
    try:
        vertexai.init(location="asia-northeast1")
        vision_client = vision.ImageAnnotatorClient()
        llm_model = GenerativeModel("gemini-1.5-pro")
    except Exception as e:
        print(f"Google Cloudの初期化に失敗: {e}"); return False

    try:
        images = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"PDF変換エラー: {e}\n'poppler'が必要です (brew install poppler)"); return False
        
    print(f"{len(images)}ページを処理します。")
    os.makedirs(PAGES_OUTPUT_DIR, exist_ok=True)

    for i, image in enumerate(images):
        page_num = i + 1
        print(f"  - ページ {page_num} を処理中...")
        with BytesIO() as buf:
            image.save(buf, format="PNG")
            ocr_response = vision_client.text_detection(image=vision.Image(content=buf.getvalue()))
        page_text = ocr_response.full_text_annotation.text
        if not page_text.strip(): continue

        prompt = f"""
# 命令書
あなたは日本の戸籍制度を熟知した専門家です。以下の【1ページ分のOCRテキスト】から、人物情報と血縁・婚姻関係を厳密に抽出し、JSON形式で出力してください。
# 重要ルール
- **最重要**: 「父 阿吹軍一」「母 ハナコ」のような記述を見つけたら、`relationships`に`parent_child`として必ず追加してください。
- **推論**: 「長男」「長女」という記述は、そのページの戸主との親子関係を示唆します。これも`parent_child`として追加してください。
- 氏名が不完全な場合（例：ハナコ）でも、文脈から氏が推測できれば補完してください（例：阿吹 ハナコ）。
# 抽出ルール
- **persons**:
    - `id`: 人物の氏名を仮のIDとしてください。（例: "阿吹 軍一"）
    - `name`, `gender`, `birth_date`, `death_date`, `notes`: 読み取れる情報を記載。
- **relationships**:
    - `type`: `spouse`(夫婦), `parent_child`(親子), `adopted`(養親子)
    - `source`: 関係の元となる人物の氏名ID
    - `target`: 関係の先となる人物の氏名ID
# OCRテキスト:
---
{page_text}
---
# 出力形式 (JSONのみ):
"""
        try:
            llm_response = llm_model.generate_content(prompt)
            json_str = llm_response.text
            if json_str.strip().startswith("```json"):
                json_str = json_str.strip()[7:-3].strip()
            page_json_path = os.path.join(PAGES_OUTPUT_DIR, f"page_{page_num}_data.json")
            with open(page_json_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        except Exception as e:
            print(f"  - ページ {page_num} のLLM解析中にエラー: {e}")
    print("\n--- 全ページの解析が完了 ---")

    # --- データの統合 ---
    print("--- AI解析結果の統合処理を開始 ---")
    all_persons_by_name, all_relationships = {}, []
    json_files = sorted(glob.glob(os.path.join(PAGES_OUTPUT_DIR, "*.json")))
    if not json_files:
        print(f"エラー: '{PAGES_OUTPUT_DIR}' に解析済みJSONファイルが見つかりません。"); return False

    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except json.JSONDecodeError: continue
            for p_data in data.get("persons", []):
                name = p_data.get("name", "").replace(" ", "").replace("　", "")
                if not name: continue
                if name not in all_persons_by_name: all_persons_by_name[name] = p_data
                else:
                    for k, v in p_data.items():
                        if v and not all_persons_by_name[name].get(k): all_persons_by_name[name][k] = v
            for r_data in data.get("relationships", []):
                all_relationships.append(r_data)

    final_persons, name_to_id, current_id = [], {}, 1
    for name, p_data in sorted(all_persons_by_name.items()):
        name_to_id[name] = current_id
        p_data['id'] = current_id; final_persons.append(p_data); current_id += 1
        
    final_relationships, rel_set = [], set()
    for rel in all_relationships:
        s_name, t_name = rel.get("source", "").replace(" ", ""), rel.get("target", "").replace(" ", "")
        if s_name in name_to_id and t_name in name_to_id:
            s_id, t_id, r_type = name_to_id[s_name], name_to_id[t_name], rel.get("type")
            rel_tuple = (r_type, tuple(sorted((s_id, t_id)))) if r_type == "spouse" else (r_type, s_id, t_id)
            if rel_tuple not in rel_set:
                final_relationships.append({"source": s_id, "target": t_id, "type": r_type}); rel_set.add(rel_tuple)

    final_data = {"persons": final_persons, "relationships": final_relationships}
    with open(MERGED_JSON_PATH, 'w', encoding='utf-8') as f: json.dump(final_data, f, ensure_ascii=False, indent=2)
    print(f"✅ データ抽出・統合完了。草案データを '{MERGED_JSON_PATH}' に保存しました。")
    return True

def draw_final_tree(json_path, output_path):
    """【ステップ2】JSONデータから最終的な家系図を描画する"""
    print("--- 家系図の描画を開始 ---")
    try:
        with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError:
        print(f"エラー: '{json_path}' が見つかりません。先に 'process' コマンドを実行してください。"); return
    
    G = nx.DiGraph()
    persons = {p['id']: p for p in data.get("persons", [])}
    for p_id in persons: G.add_node(p_id, data=persons[p_id])
    for rel in data.get("relationships", []):
        if rel.get('type') in ['parent_child', 'adopted'] and G.has_node(rel.get('source')) and G.has_node(rel.get('target')):
            G.add_edge(rel.get('source'), rel.get('target'))
    try:
        pos = nx.drawing.nx_agraph.graphviz_layout(G, prog='dot')
    except Exception as e:
        print(f"レイアウト計算エラー: {e}\nGraphvizとpygraphvizのインストールを確認してください。"); return
    
    # 描画処理
    min_x, max_x = min(p[0] for p in pos.values()), max(p[0] for p in pos.values())
    min_y, max_y = min(p[1] for p in pos.values()), max(p[1] for p in pos.values())
    canvas_width, canvas_height = int(max_x - min_x + BOX_WIDTH*2), int(max_y - min_y + BOX_HEIGHT*2)
    img = Image.new('RGB', (canvas_width, canvas_height), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font, small_font = ImageFont.truetype(FONT_PATH, FONT_SIZE), ImageFont.truetype(FONT_PATH, SMALL_FONT_SIZE)
    x_offset, y_offset = -min_x + BOX_WIDTH, -min_y + BOX_HEIGHT

    for u, v in G.edges():
        ux, uy = pos[u][0] + x_offset, canvas_height - (pos[u][1] + y_offset)
        vx, vy = pos[v][0] + x_offset, canvas_height - (pos[v][1] + y_offset)
        draw.line((ux, uy + BOX_HEIGHT/2, ux, (uy+vy)/2), fill='gray', width=LINE_WIDTH)
        draw.line((ux, (uy+vy)/2, vx, (uy+vy)/2), fill='gray', width=LINE_WIDTH)
        draw.line((vx, (uy+vy)/2, vx, vy - BOX_HEIGHT/2), fill='gray', width=LINE_WIDTH)
        
    for node_id, p_data in G.nodes(data=True):
        person = p_data['data']
        px, py = pos[node_id][0] + x_offset, canvas_height - (pos[node_id][1] + y_offset)
        color = 'skyblue' if person.get('gender') == 'M' else 'lightpink' if person.get('gender') == 'F' else 'lightgray'
        draw.rectangle((px - BOX_WIDTH/2, py - BOX_HEIGHT/2, px + BOX_WIDTH/2, py + BOX_HEIGHT/2), fill=color, outline='black', width=2)
        name, birth, death = person.get('name', ''), person.get('birth_date', ''), person.get('death_date', '')
        draw.text((px, py - 18), name or '', font=font, fill='black', anchor='mm')
        draw.text((px, py), birth or '', font=small_font, fill='black', anchor='mm')
        if death: draw.text((px, py + 18), f"死亡: {death}", font=small_font, fill='black', anchor='mm')
        
    img.save(output_path)
    print(f"✅ 成功！家系図を '{output_path}' に保存しました。")

def print_usage():
    print("\n--- 戸籍解析・家系図生成ツール ---")
    print("使い方: python koseki_analyzer.py [コマンド]")
    print("\nコマンド:")
    print("  process    : AIでPDFを解析し、家系図の草案データ(JSON)を作成します。")
    print("  draw       : 生成された草案データから、家系図の画像を描画します。")

# --- メインの実行制御 ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage(); sys.exit(1)
    command = sys.argv[1]

    if command == "process":
        process_and_synthesize("input/A.pdf")
    elif command == "draw":
        draw_final_tree(MERGED_JSON_PATH, FINAL_IMAGE_PATH)
    else:
        print(f"エラー: 不明なコマンド '{command}'"); print_usage()