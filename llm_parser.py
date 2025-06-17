# llm_parser.py (Vertex AI版)

import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part

def parse_koseki_text(text: str) -> str:
    """
    OCRで抽出した戸籍テキストをVertex AIのGeminiモデルに渡し、
    解析・構造化されたJSONを返します。
    """
    print("Vertex AIのLLMによるテキスト解析を開始します...")

    try:
        # プロジェクトIDを環境変数から取得、または直接指定
        # 通常、サービスアカウントキーから自動で推測されます。
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") 
        
        # Vertex AIを初期化
        vertexai.init(project=project_id, location="asia-northeast1") # 東京リージョン

        # 使用するモデルを指定
        model = GenerativeModel("gemini-1.5-pro")

        # AIへの指示（プロンプト） - 以前と同じ
        prompt = f"""
# 命令書
あなたは、日本の戸籍制度（改製原戸籍、除籍謄本を含む）を深く理解する戸籍専門の解析者です。以下のOCR結果から、人物とその関係性を正確に抽出し、厳格なJSON形式で出力してください。

# 前提条件
- テキストはOCRによって読み取られたもので、誤認識や不完全な部分を含む可能性があります。
- 右から左への記述、旧字体、手書き文字の文脈を考慮して解析してください。
- 複数の戸籍が混在している可能性があります。それぞれの戸籍の筆頭者（戸主）を特定し、人物間の関係性を正しく紐付けてください。

# 抽出ルール
- **persons**:
    - `id`: 人物ごとに一意の整数IDを採番してください。
    - `name`: 氏名を抽出してください。
    - `gender`: 性別を "M" (男性) または "F" (女性) で示してください。続柄（長男、妻など）から判断してください。
    - `birth_date`: 元号を含む生年月日を抽出してください。
    - `death_date`: 元号を含む死亡年月日を抽出してください。なければnullとします。
    - `relation_to_head`: その人物が属する戸籍の筆頭者から見た続柄を記載してください。
    - `notes`: 特記事項（婚姻、養子縁組、分家、死亡など）の情報を簡潔にまとめてください。不確かな情報やOCRの誤認識の可能性がある場合もここに記載してください。
- **relationships**:
    - `type`: 関係の種類を `spouse` (夫婦), `parent_child` (親子), `adopted` (養親子) のいずれかで示してください。
    - `source`: 関係の元となる人物のIDを指定してください（例：親のID）。
    - `target`: 関係の先となる人物のIDを指定してください（例：子のID）。

# OCRテキスト:
---
{text}
---

# 出力形式 (JSONのみを出力すること):
"""

        # LLMにリクエストを送信
        response = model.generate_content(prompt)
        
        print("Vertex AIによるLLM解析が正常に完了しました。")
        return response.text

    except Exception as e:
        print(f"Vertex AIのLLM解析中にエラーが発生しました: {e}")
        return None