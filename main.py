# main.py (最終版)

import os
import json
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import vision
from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_path):
    print(f"PDFを画像に変換しています: {pdf_path}")
    try:
        return convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"PDFから画像への変換中にエラーが発生しました: {e}")
        return []

def ocr_image(client, image_data) -> str:
    try:
        image = vision.Image(content=image_data)
        response = client.text_detection(image=image)
        if response.error.message:
            raise Exception(response.error.message)
        return response.full_text_annotation.text
    except Exception as e:
        print(f"  - OCR処理中にエラー: {e}")
        return ""

def parse_koseki_text_for_page(text: str, page_num: int) -> str:
    print(f"  - Vertex AI (ページ {page_num}) の解析を開始...")
    if not text.strip():
        print(f"  - ページ {page_num} はテキストが空のためスキップします。")
        return None
    try:
        model = GenerativeModel("gemini-1.5-pro")
        prompt = f"""
# 命令書
あなたは日本の戸籍制度を熟知した専門家です。以下の【1ページ分のOCRテキスト】から、人物情報と血縁・婚姻関係を厳密に抽出し、JSON形式で出力してください。

# 重要ルール
- **このページから直接読み取れる事実のみ**を抽出してください。
- **最重要**: 人物の情報の中に「父 阿吹軍一」「母 ハナコ」「夫 輝男」「妻 榮子」のような記述を見つけたら、それは関係を示す決定的な証拠です。その情報をもとに、`relationships`の配列に`parent_child`または`spouse`の関係を**必ず追加**してください。
- **推論**: 「長男」「長女」という記述は、そのページの戸主または筆頭者との親子関係を示唆します。これも`parent_child`として`relationships`に追加してください。
- 氏名が不完全な場合（例：ハナコ）でも、文脈（例：阿吹軍一の妻）から氏が推測できれば補完してください（例：阿吹 ハナコ）。

# 抽出ルール
- **persons**:
    - `id`: 人物の氏名を仮のIDとしてください。（例: "阿吹 軍一"）
    - `name`: 氏名。
    - `gender`: 続柄（長男,妻,父,母など）から性別を**必ず推測し**、"M"または"F"を設定。判断不能な場合のみnull。
    - `birth_date`, `death_date`: 元号を含む日付。
    - `notes`: 婚姻、養子縁組、分家、死亡などの特記事項。
- **relationships**:
    - `type`: `spouse`(夫婦), `parent_child`(親子), `adopted`(養親子)
    - `source`: 関係の元となる人物の氏名ID（例：親、夫）
    - `target`: 関係の先となる人物の氏名ID（例：子、妻）

# OCRテキスト:
---
{text}
---

# 出力形式 (JSONのみ):
"""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"  - Vertex AIのLLM解析中(ページ {page_num})にエラー: {e}")
        return None

def process_document(pdf_path: str, output_dir: str):
    images = convert_pdf_to_images(pdf_path)
    if not images: return
    print(f"{len(images)}ページの画像に変換しました。")
    
    vision_client = vision.ImageAnnotatorClient()
    
    for i, image in enumerate(images):
        page_num = i + 1
        print(f"--- ページ {page_num} の処理を開始 ---")
        
        with BytesIO() as output:
            image.save(output, format="PNG")
            image_bytes = output.getvalue()
        
        page_text = ocr_image(vision_client, image_bytes)
        json_str = parse_koseki_text_for_page(page_text, page_num)
        
        if json_str:
            page_json_path = os.path.join(output_dir, f"page_{page_num}_data.json")
            try:
                if json_str.strip().startswith("```json"):
                    json_str = json_str.strip()[7:-3].strip()
                json_data = json.loads(json_str)
                with open(page_json_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                print(f"  - ページ {page_num} の解析結果を '{page_json_path}' に保存しました。")
            except json.JSONDecodeError:
                print(f"  - エラー: ページ {page_num} のLLM応答がJSON形式ではありません。")

if __name__ == "__main__":
    load_dotenv()
    vertexai.init(location="asia-northeast1")
    input_dir = "input"
    output_dir = "output/pages"
    pdf_filename = "A.pdf"
    pdf_path = os.path.join(input_dir, pdf_filename)
    os.makedirs(output_dir, exist_ok=True)
    process_document(pdf_path, output_dir)
    print("\n全ページの解析が完了しました。")