import streamlit as st
import json
import google.generativeai as genai

# ページ設定
st.set_page_config(page_title="Personal Database Sync", layout="wide")

# API初期化 (Gemini)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 軽快に動くモデル "gemini-1.5-flash" を使用
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    model = None
    st.warning("⚠️ .streamlit/secrets.toml に GEMINI_API_KEY を設定してください。")

# ==========================================
# サイドバー: データ読み込み & モード選択
# ==========================================
st.sidebar.header("📂 Database Loader")

# 自分のDB
file_a = st.sidebar.file_uploader("Upload Your Database (User A)", type=["json"], key="file_a")
data_a = None
if file_a:
    data_a = json.load(file_a)
    st.sidebar.success(f"User A: {data_a.get('profile', {}).get('name', 'Loaded')}")

# 相手のDB
file_b = st.sidebar.file_uploader("Upload Partner's Database (User B)", type=["json"], key="file_b")
data_b = None
if file_b:
    data_b = json.load(file_b)
    st.sidebar.success(f"User B: {data_b.get('profile', {}).get('name', 'Loaded')}")

st.sidebar.divider()
mode = st.sidebar.radio("Select Mode", ["⚡ SYNC (共通点抽出)", "🤖 NotebookLM (AI対話)"])

st.title("🧬 Personal Database Sync")

# ==========================================
# Mode 1: SYNC (共通点の割り出し)
# ==========================================
if mode == "⚡ SYNC (共通点抽出)":
    st.header("Resonance Finder")
    st.write("二つのデータベースを照合し、共通の話題や隠れた接点を抽出します。")

    if st.button("データベースを照合 (SYNC)", type="primary"):
        if not model:
            st.error("APIキーが必要です。")
        elif not data_a or not data_b:
            st.warning("サイドバーから、自分と相手のJSONファイルを両方アップロードしてください。")
        else:
            with st.spinner("Analyzing Context with Gemini..."):
                str_a = json.dumps(data_a, ensure_ascii=False)
                str_b = json.dumps(data_b, ensure_ascii=False)

                # prompt = f"""
                # あなたは高度なマッチングアルゴリズムです。以下の2名のJSONデータを分析し、化学反応が起きるポイントを探ってください。

                # 【出力フォーマット】
                # 1. **コア・レゾナンス**: [二人の最も強い共通項を一言で]
                # 2. **話題の提案**: [具体的な会話ネタを3つ]
                # 3. **コラボレーション案**: [もし二人が何か作るとしたら？]

                # ---
                # [User A Data]
                # {str_a}

                # [User B Data]
                # {str_b}
                # """
                prompt = f"""
                以下は、ある個人の脳内を構成する「名詞のタグクラウド（brain_dump）」です。
                文脈はありませんが、これらの単語の集合体から、この人物の「美意識」「思考の癖」「隠れた興味」をプロファイリングしてください。

                その上で、相手（User B）のタグクラウドと比較し、
                「一見関係なさそうだが、深層で繋がっている概念（Core Resonance）」を発見してください。

                [User A Brain Dump]
                {json.dumps(data_a['brain_dump'], ensure_ascii=False)}

                [User B Brain Dump]
                {json.dumps(data_b['brain_dump'], ensure_ascii=False)}
                """

                try:
                    response = model.generate_content(prompt)
                    st.success("Analysis Complete.")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# Mode 2: NotebookLM (AIとの対話)
# ==========================================
elif mode == "🤖 NotebookLM (AI対話)":
    st.header("Personal AI Chat")
    
    target_option = st.radio(
        "どのデータと話しますか？", 
        ["User A (自分)", "User B (相手)", "Both (二人)"], 
        horizontal=True
    )

    target_data_str = ""
    system_role = ""

    if target_option == "User A (自分)" and data_a:
        target_data_str = json.dumps(data_a, ensure_ascii=False)
        system_role = "あなたはUser Aのデジタルツインです。一人称は『私』で、User Aのデータに基づき本人になりきって答えてください。"
    elif target_option == "User B (相手)" and data_b:
        target_data_str = json.dumps(data_b, ensure_ascii=False)
        system_role = "あなたはUser Bのデジタルツインです。一人称は『私』で、User Bのデータに基づき本人になりきって答えてください。"
    elif target_option == "Both (二人)" and (data_a and data_b):
        target_data_str = "User A:" + json.dumps(data_a, ensure_ascii=False) + "\nUser B:" + json.dumps(data_b, ensure_ascii=False)
        system_role = "あなたはUser AとUser Bの両方のデータを知る管理者です。二人の関係性やデータについて客観的に答えてください。"
    
    if not target_data_str:
        st.info("👈 左のサイドバーでJSONファイルをアップロードしてください。")
    
    # チャット履歴の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴を表示
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_query := st.chat_input("質問を入力..."):
        if not target_data_str:
            st.error("データがロードされていません。")
        elif not model:
            st.error("APIキーが必要です。")
        else:
            # ユーザー入力表示
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            # AI回答生成
            with st.chat_message("assistant"):
                # Geminiはチャット履歴をオブジェクトとして管理する必要がありますが、
                # 簡易的に毎回コンテキストを渡す方式で実装します
                
                full_prompt = f"""
                {system_role}
                
                【参照データ】
                {target_data_str}

                【これまでの会話】
                {[m['content'] for m in st.session_state.messages[-5:]]}

                【ユーザーの質問】
                {user_query}
                """
                
                try:
                    response = model.generate_content(full_prompt)
                    bot_reply = response.text
                    st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                except Exception as e:
                    st.error(f"Error: {e}")