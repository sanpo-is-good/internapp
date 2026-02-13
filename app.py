import streamlit as st
import json
import google.generativeai as genai
import os
import random
import time
import math

# ページ設定
st.set_page_config(page_title="SYNC with Kamatani", layout="wide")

# カスタムCSS: 黒背景 & テキストオンリー & SVGライン
st.markdown("""
<style>
@keyframes floatIn {
  0% { opacity: 0; transform: scale(0.5); }
  60% { opacity: 0.9; transform: scale(1.05); }
  100% { opacity: 1; transform: scale(1); }
}

@keyframes fadeInLine {
  0% { opacity: 0; }
  100% { opacity: 0.4; }
}

.stApp {
    background-color: #000000;
}

.cloud-container {
  position: relative;
  width: 100%;
  height: 80vh;
  margin: 0 auto;
  overflow: hidden;
  background: radial-gradient(circle at center, #111 0%, #000 70%);
}

.svg-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

.connection-line {
  stroke: rgba(255, 255, 255, 0.3);
  stroke-width: 1px;
  fill: none;
  opacity: 0;
  animation: fadeInLine 2s ease-out 1s forwards;
}

.word-fluffy {
  position: absolute;
  color: #fff;
  padding: 2px 4px;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  font-weight: 600;
  opacity: 0;
  animation: floatIn 1.0s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  white-space: nowrap;
  transform-origin: center center;
  transform: translate(-50%, -50%); /* 中心座標基準 */
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.5), 0 0 20px rgba(255, 255, 255, 0.3);
  z-index: 10;
}

.word-fluffy.visible {
     opacity: 1;
     transform: translate(-50%, -50%) scale(1);
}

.centered-form {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 10vh;
  text-align: center;
}

.stButton button {
    border-radius: 20px;
}
</style>
""", unsafe_allow_html=True)

# API初期化 (Gemini)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    model = None
    st.warning("⚠️ .streamlit/secrets.toml に GEMINI_API_KEY を設定してください。")

# Kamatani Data Loading
kamatani_data = None
json_path = "kamatani copy.json"
if os.path.exists(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        kamatani_data = json.load(f)
else:
    st.error(f"'{json_path}' が見つかりません。")

# サンプルデータ
SAMPLE_NAME = "友人A"
SAMPLE_DUMP = """粘菌
バイオアート
発酵
YCAM
Rhizomatiks
オートポイエーシス
南方熊楠
京都
鴨川デルタ
廃墟
工場萌え
微風ゾーン
錆
苔テラリウム
テクスチャ
Rhinoceros
Grasshopper
アルゴリズミックデザイン
3Dプリンタ
土器
縄文
岡本太郎
太陽の塔
ビオフィリア
環世界
ユクスキュル
蟲師
ナウシカの地下室
Björk
坂本龍一
Alva Noto
アンビエント
モジュラーシンセ
真空管アンプ
レコード
骨董市
喫茶ソワレ
ゼリーポンチ
薬膳カレー
クラフトビール
日本酒
菌糸レザー
スペキュラティブデザイン
長野県
山小屋
鉱物
ビスマス結晶
幾何学
フラクタル
複雑系
ライフゲーム
マッシュルーム
菌類
分解
土に還る
透明標本
ウニの骨格
民藝
柳宗悦
金継ぎ
不完全な美
wabi-sabi
A24
ミッドサマー
羊文学
カネコアヤノ
柴田聡子"""

# ==========================================
# レイアウト計算ロジック (カテゴリ別セクター配置)
# ==========================================
def calculate_layout(words, container_width=1200, container_height=900):
    """
    1. カテゴリごとに配置角度(セクター)を割り当てる。
    2. 同じカテゴリの単語はそのセクター内に配置されるようにする。
    """
    layout_items = []
    lines = []
    rects = [] 
    
    words_map = {w['text']: w for w in words}
    placed_positions = {}
    
    # カテゴリ一覧の収集 & グループ分け
    categories = set()
    roots = []
    children = []
    
    for w in words:
        cat = w.get('category', 'Others')
        categories.add(cat)
        
        parent_key = w.get('related_to')
        if not parent_key or parent_key not in words_map:
            roots.append(w)
        else:
            children.append(w)
            
    # カテゴリに角度を割り当て
    sorted_cats = sorted(list(categories))
    cat_angle_map = {}
    if sorted_cats:
        sector_size = (2 * math.pi) / len(sorted_cats)
        for i, cat in enumerate(sorted_cats):
            # ランダム性を少し持たせるため、開始位置はずらす
            base_angle = i * sector_size
            cat_angle_map[cat] = (base_angle, base_angle + sector_size)
    else:
        cat_angle_map['Others'] = (0, 2*math.pi)

    # ------ Rootの配置 (カテゴリセクター依存) ------
    roots.sort(key=lambda x: x.get('weight', 5), reverse=True)
    
    center_x = container_width / 2
    center_y = container_height / 2
    
    for i, item in enumerate(roots):
        text = item['text']
        weight = item.get('weight', 5)
        category = item.get('category', 'Others')
        
        font_size_rem = 1.5 + (weight / 10.0) * 3.0
        
        px_per_rem = 20
        est_width = (len(text) * font_size_rem * px_per_rem) + 20
        est_height = (font_size_rem * px_per_rem) + 20
        
        # カテゴリに応じた角度範囲を取得
        min_angle, max_angle = cat_angle_map.get(category, (0, 6.28))
        
        # スパイラル探索 (角度をセクター内に制限)
        # 中心からスタートしたいので、最初は範囲の中央から
        start_angle = (min_angle + max_angle) / 2
        angle = start_angle + random.uniform(-0.5, 0.5) # 少し揺らす
        radius = 0.0
        step_angle = 0.2
        step_radius = 6.0
        
        if i == 0:
             # 本当のド真ん中は1つだけ
             x, y = center_x, center_y
        else:
            found = False
            for _ in range(3000):
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                margin = 50
                if x < margin or x > container_width - margin or y < margin or y > container_height - margin:
                    radius += step_radius
                    # 角度を振り直す (セクター内)
                    angle = random.uniform(min_angle, max_angle)
                    continue

                overlap = False
                curr_w = est_width
                curr_h = est_height
                for rx, ry, rw, rh in rects:
                    if (abs(x - rx) * 2 < (curr_w + rw) * 0.9) and \
                       (abs(y - ry) * 2 < (curr_h + rh) * 0.9):
                        overlap = True
                        break
                
                if not overlap:
                    found = True
                    break
                
                # 次の探索点: 角度はセクター内で揺らす、半径は広げる
                angle += random.uniform(-0.5, 0.5) 
                # 範囲外に出ないようにクリップ (ループさせる必要はない、範囲内であればOK)
                # 簡易的に、範囲外なら戻す
                # radius += 0.5
                radius += 0.3
                
            if not found: continue

        rects.append((x, y, est_width, est_height))
        placed_positions[text] = (x, y)
        
        layout_items.append({
            "text": text,
            "x": x, "y": y,
            "style": f"top: {(y/container_height)*100}%; left: {(x/container_width)*100}%; font-size: {font_size_rem}rem; animation-delay: {random.uniform(0, 0.5)}s; z-index: {int(weight)*10};"
        })

    # ------ Childの配置 ------
    children.sort(key=lambda x: x.get('weight', 5), reverse=True)
    
    for item in children:
        text = item['text']
        weight = item.get('weight', 5)
        parent_text = item.get('related_to')
        
        px, py = placed_positions.get(parent_text, (center_x, center_y))
        
        font_size_rem = 0.8 + (weight / 10.0) * 1.5
        
        px_per_rem = 20
        est_width = (len(text) * font_size_rem * px_per_rem) + 10
        est_height = (font_size_rem * px_per_rem) + 10
        
        angle = random.uniform(0, 6.28)
        radius = est_height * 1.5
        step_angle = 0.2
        step_radius = 4.0
        
        found = False
        for _ in range(2000):
            x = px + radius * math.cos(angle)
            y = py + radius * math.sin(angle)
            
            margin = 30
            if x < margin or x > container_width - margin or y < margin or y > container_height - margin:
                radius += step_radius
                continue

            overlap = False
            curr_w = est_width
            curr_h = est_height
            for rx, ry, rw, rh in rects:
                if (abs(x - rx) * 2 < (curr_w + rw) * 0.9) and \
                   (abs(y - ry) * 2 < (curr_h + rh) * 0.9):
                    overlap = True
                    break
            
            if not overlap:
                found = True
                break
            
            angle += step_angle
            radius += 0.5
            if radius > 500: break
        
        if found:
            rects.append((x, y, est_width, est_height))
            placed_positions[text] = (x, y)
            
            if parent_text in placed_positions:
                lines.append({
                    "x1": px, "y1": py,
                    "x2": x, "y2": y
                })

            layout_items.append({
                "text": text,
                "x": x, "y": y,
                "style": f"top: {(y/container_height)*100}%; left: {(x/container_width)*100}%; font-size: {font_size_rem}rem; animation-delay: {random.uniform(0.5, 1.5)}s; z-index: {int(weight)*10};"
            })
            
    return layout_items, lines

# ==========================================
# メイン画面
# ==========================================

if "merged_result" not in st.session_state:
    st.session_state.merged_result = None

# タイトル
if st.session_state.merged_result is None:
    st.markdown("<h1 style='text-align: center; font-size: 3rem; margin-bottom: 2rem; color: #fff;'>Merge with Kamatani</h1>", unsafe_allow_html=True)

# 入力フォーム
if st.session_state.merged_result is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("Load Sample Data (友人A)"):
            st.session_state.form_name = SAMPLE_NAME
            st.session_state.form_dump = SAMPLE_DUMP
            st.rerun()
            
        with st.form("input_form"):
            default_name = st.session_state.get("form_name", "")
            default_dump = st.session_state.get("form_dump", "")
            
            user_name = st.text_input("Name", value=default_name, placeholder="Your Name")
            user_dump_text = st.text_area(
                "Brain Dump",
                value=default_dump,
                height=300,
                placeholder="好きなものや概念を入力してください..."
            )
            
            submit_col1, submit_col2, submit_col3 = st.columns([1, 1, 1])
            with submit_col2:
                submitted = st.form_submit_button("MERGE", use_container_width=True, type="primary")

        if submitted:
            if not model:
                st.error("API Error: API Key not found.")
            elif not user_dump_text.strip():
                st.warning("項目を入力してください。")
            elif not kamatani_data:
                st.error("Kamatani data not found.")
            else:
                user_items = [w.strip() for w in user_dump_text.replace("、", "\n").replace(",", "\n").split("\n") if w.strip()]
                
                with st.spinner("Merging Contexts..."):
                    prompt = f"""
                    以下は二人の「脳内タグクラウド」です。
                    
                    [User A ({user_name})]
                    {', '.join(user_items)}

                    [User B (Kamatani)]
                    {', '.join(kamatani_data.get('brain_dump', []))}
                    
                    この二人の情報をマージし、「コアとなる共通点」と「そこから派生する関連トピック」を抽出・生成してください。
                    特に「カネコアヤノ」と「柴田聡子」のような、**音楽的・意味的に近い存在**は同じカテゴリとして認識し、近くに配置できるようにしてください。
                    
                    【出力仕様】
                    1. **Json Object Array**: `[{{"text": "単語", "weight": 10, "related_to": "親単語(任意)", "category": "カテゴリ名"}}, ...]`
                    2. **Category (重要)**:
                       - 各単語に「音楽」「自然」「テクノロジー」「生活」などのカテゴリを付与してください。
                       - **似ているアーティストや概念は必ず同じカテゴリにしてください。**
                    3. **Core (親)**:
                       - 共通点や主要なテーマ (Weight 10)。
                    4. **Related (子)**:
                       - 派生語 (Weight 5-8)。
                       - `related_to` で親を指定。
                    5. **合計数**: 40〜60個程度。
                    6. **内容**:
                       - 単純なマッチングを優先。
                    
                    Example Output:
                    [
                        {{"text": "音楽", "weight": 10, "category": "Music"}},
                        {{"text": "カネコアヤノ", "weight": 8, "related_to": "音楽", "category": "Music"}},
                        {{"text": "柴田聡子", "weight": 8, "related_to": "音楽", "category": "Music"}},
                        {{"text": "自然", "weight": 10, "category": "Nature"}},
                        {{"text": "粘菌", "weight": 8, "related_to": "自然", "category": "Nature"}}
                    ]
                    
                    IMPORTANT: Output ONLY valid JSON.
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        text_resp = response.text.strip()
                        if text_resp.startswith("```json"): text_resp = text_resp[7:]
                        if text_resp.startswith("```"): text_resp = text_resp[3:]
                        if text_resp.endswith("```"): text_resp = text_resp[:-3]
                        
                        st.session_state.merged_result = json.loads(text_resp)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error: {e}")

# 結果表示
if st.session_state.merged_result:
    if st.button("↺ Reset"):
        st.session_state.merged_result = None
        st.session_state.pop("form_name", None)
        st.session_state.pop("form_dump", None)
        st.rerun()

    raw_words = st.session_state.merged_result
    
    # コンテナサイズ
    W, H = 1200, 900
    
    items, lines = calculate_layout(raw_words, container_width=W, container_height=H)
    
    # SVGライン生成
    svg_content = f'<svg class="svg-layer" viewBox="0 0 {W} {H}">'
    for line in lines:
        svg_content += f'<line class="connection-line" x1="{line["x1"]}" y1="{line["y1"]}" x2="{line["x2"]}" y2="{line["y2"]}" />'
    svg_content += '</svg>'
    
    html_content = '<div class="cloud-container">'
    html_content += svg_content
    for item in items:
        html_content += f'<div class="word-fluffy" style="{item["style"]}">{item["text"]}</div>'
    html_content += '</div>'
    
    st.markdown(html_content, unsafe_allow_html=True)


