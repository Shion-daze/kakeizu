# ocr_processor.py

import os
from google.cloud import vision

def get_document_text(pdf_path: str) -> str:
    """
    指定されたPDFファイルからGoogle Cloud Vision APIを使用してテキストを抽出します。

    Args:
        pdf_path (str): 解析するPDFファイルのパス。

    Returns:
        str: 抽出された全てのテキストを結合した文字列。
             エラーが発生した場合はNone。
    """
    print(f"OCR処理を開始します: {pdf_path}")

    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("エラー: 環境変数 'GOOGLE_APPLICATION_CREDENTIALS' が設定されていません。")
        return None

    try:
        client = vision.ImageAnnotatorClient()
        
        with open(pdf_path, "rb") as f:
            content = f.read()

        mime_type = "application/pdf"
        input_config = vision.InputConfig(content=content, mime_type=mime_type)

        features = [vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)]

        request = vision.AnnotateFileRequest(
            input_config=input_config,
            features=features
        )

        # APIを呼び出し (★ここが修正点です)
        response = client.batch_annotate_files(requests=[request])

        all_text = ""
        # レスポンスの構造がbatch処理用に変わるため、ループを修正
        for image_response in response.responses[0].responses:
            all_text += image_response.full_text_annotation.text
        
        print("OCR処理が正常に完了しました。")
        return all_text

    except Exception as e:
        print(f"OCR処理中にエラーが発生しました: {e}")
        return None