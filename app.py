import streamlit as st

st.set_page_config(
    page_title="ikapp",
    page_icon="🧩",
    layout="centered",
)

st.title("ikapp 홈")
st.write("왼쪽 사이드바에서 실행할 도구(페이지)를 선택하세요.")

st.markdown(
    """
- 📘 **script_page.py** → 대본 마스터 (scriptking)
- 🎨 **visual_page.py** → 시각화 마스터 (visualking)
- 🔍 **find_page.py** → YouTube 검색기
"""
)
