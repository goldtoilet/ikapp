import streamlit as st
import json
import os

# =========================
# secrets 인증 정보
# =========================
AUTH_ID = st.secrets["auth"]["id"]
AUTH_PW = st.secrets["auth"]["password"]

# =========================
# 자동 로그인 상태 저장 파일
# =========================
AUTH_STATE_PATH = ".ikapp_auth.json"


def load_auth_state():
    if not os.path.exists(AUTH_STATE_PATH):
        return {"remember": False}
    try:
        with open(AUTH_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"remember": False}


def save_auth_state(state):
    with open(AUTH_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


# =========================
# 로그인 UI
# =========================
def login_view():
    st.markdown("## 🔐 ikapp 로그인")

    user_id = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")
    remember = st.checkbox("자동 로그인")

    if st.button("로그인", use_container_width=True):
        if user_id == AUTH_ID and password == AUTH_PW:
            st.session_state.logged_in = True
            save_auth_state({"remember": remember})
            st.success("로그인 성공")
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 틀렸습니다.")


# =========================
# 비밀번호 변경 안내
# =========================
def password_change_view():
    st.markdown("---")
    st.markdown("### 🔑 비밀번호 변경")

    st.info(
        "보안을 위해 비밀번호는 앱 내부에서 직접 변경하지 않습니다.\n\n"
        "📌 변경 방법:\n"
        "1. `.streamlit/secrets.toml` 파일 열기\n"
        "2. `[auth] password` 값 수정\n"
        "3. 앱 재시작"
    )


# =========================
# 헤더
# =========================
def header_bar():
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 🧩 ikapp")
    with col2:
        if st.button("로그아웃"):
            st.session_state.logged_in = False
            save_auth_state({"remember": False})
            st.rerun()


# =========================
# 홈 화면 (기존 내용)
# =========================
def main_home():
    st.title("ikapp 홈")
    st.write("왼쪽 사이드바에서 실행할 도구(페이지)를 선택하세요.")
    st.markdown(
        """
- 📘 **script_page.py** → 대본 마스터 (scriptking)
- 🎨 **visual_page.py** → 시각화 마스터 (visualking)
- 🔍 **find_page.py** → YouTube 검색기
"""
    )


# =========================
# 앱 시작
# =========================
st.set_page_config(
    page_title="ikapp",
    page_icon="🧩",
    layout="centered",
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 자동 로그인
auth_state = load_auth_state()
if auth_state.get("remember") and not st.session_state.logged_in:
    st.session_state.logged_in = True

# =========================
# 렌더링
# =========================
if not st.session_state.logged_in:
    login_view()
else:
    header_bar()
    st.markdown("---")
    main_home()
    password_change_view()

