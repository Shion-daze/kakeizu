#synthesis.py (AIによる統合・名寄せ機能付き最終版)

import os
import json
import glob
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# --- 設定 ---
PAGES_INPUT_DIR = "output/pages"
MERGED_JSON_OUTPUT_PATH = "output/family_tree_merged.json"

def synthesize_with_ai(pages_dir, output_path):
    """
    AIの能力を使って、ページごとの断片的なJSONデータを
    名寄せ・統合し、最終的な単一のJSONを生成する。
    """
    print("--- AIによる統合・名寄せ処理を開始 ---")
    load_dotenv()
    try:
        vertexai.init(location="asia-northeast1")
        model = GenerativeModel("gemini-1.5-pro")
    except Exception as e:
        print(f"Google Cloudの初期化に失敗: {e}"); return

    json_files = sorted(glob.glob(os.path.join(pages_dir, "page_*_data.json")))
    if not json_files:
        print(f"エラー: '{pages_dir}' に解析済みJSONファイルが見つかりません。"); return

    # 全ページの情報を一つのテキストにまとめる
    all_pages_text = ""
    for file_path in json_files:
        page_num = os.path.basename(file_path).split('_')[1]
        all_pages_text += f"\n\n--- ページ {page_num} の抽出結果 ---\n"
        with open(file_path, 'r', encoding='utf-8') as f:
            all_pages_text += f.read()

    # AIへの最終統合を依頼するプロンプト
    prompt = f"""
# 命令書
あなたは、戸籍情報を整理するデータアナリストです。以下に、複数ページから抽出された、重複を含む人物と関係性のJSONデータ群が提示されます。あなたの仕事は、これらの断片的な情報を分析し、**同一人物を特定（名寄せ）**し、**最終的な一つのクリーンな家系データ**としてJSON形式で出力することです。

# 重要ルール
- **名寄せ**: 「妻 ハナコ」と「阿吹 ハナコ」のように、文脈（関係性や日付）から同一人物だと判断できるものは、一つの人物情報に統合してください。
- **情報統合**: 同一人物の情報が複数ある場合、それぞれの情報を補完しあって、最も完全な人物データを作成してください。（例：あるページには生年月日、別のページには死亡日が記載されている場合、両方を一つのデータにまとめる）
- **IDの再採番**: 最終的な人物リストでは、各人物に1から始まるユニークな整数IDを振り直してください。
- **関係性の再構築**: 関係性リストの`source`と`target`も、新しい整数IDを使って再構築してください。

# 入力データ（複数ページのJSONデータ群）:
---
{all_pages_text}
---

# 出力形式 (最終的な単一のJSONのみを出力すること):
{{
  "persons": [
    {{
      "id": 1,
      "name": "阿吹 利三郎",
      "gender": "M",
      "birth_date": "...",
      "death_date": "...",
      "notes": "..."
    }},
    ...
  ],
  "relationships": [
    {{
      "source": 1,
      "target": 2,
      "type": "spouse"
    }},
    ...
  ]
}}
"""

    print("AIに最終的な統合を依頼しています。これには少し時間がかかる場合があります...")
    try:
        response = model.generate_content(prompt)
        json_str = response.text
        if json_str.strip().startswith("```json"):
            json_str = json_str.strip()[7:-3].strip()
        
        # 最終的なJSONを検証して保存
        final_data = json.loads(json_str)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ AIによる統合完了！名寄せされた最終データを '{output_path}' に保存しました。")

    except Exception as e:
        print(f"AIによる最終統合処理中にエラーが発生しました: {e}")
        # エラーが発生した場合、生の応答を保存してデバッグしやすくする
        with open("output/synthesis_error_response.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("エラー応答を 'output/synthesis_error_response.txt' に保存しました。")


if __name__ == "__main__":
    synthesize_with_ai(PAGES_INPUT_DIR, MERGED_JSON_OUTPUT_PATH)