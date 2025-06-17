# check_env.py
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# 環境変数を取得
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if cred_path:
    print("✅ 成功: .envファイルから環境変数を読み込めました。")
    print(f"   設定されているパス: {cred_path}")
else:
    print("❌ 失敗: .envファイルから環境変数を読み込めませんでした。")
    print("   ファイルの位置と内容を確認してください。")