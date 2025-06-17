# find_fonts.py

import matplotlib.font_manager as fm

# システムにインストールされている全てのフォントを検索
fonts = fm.findSystemFonts()

print("--- 利用可能な日本語フォント候補 ---")
for font in fonts:
    # 日本語フォントによく含まれるキーワードで絞り込み
    if 'hiragino' in font.lower() or \
       'gothic' in font.lower() or \
       'mincho' in font.lower() or \
       'yu' in font.lower(): # Yu Gothic, Yu Minchoなど
        
        # フォントのプロパティから名前を取得
        try:
            font_name = fm.FontProperties(fname=font).get_name()
            print(f"正式名称: {font_name},  ファイルパス: {font}")
        except Exception:
            pass # 読み取れないフォントはスキップ

print("---------------------------------")
print("\n上記の中から、'Hiragino Kaku Gothic ProN' や 'Yu Gothic' のような名前をコピーしてください。")