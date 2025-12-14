import streamlit as st
from openai import OpenAI
import os, json
from json import JSONDecodeError
from uuid import uuid4

# =================================================
# 기본 설정
# =================================================
st.set_page_config(page_title="visualking", page_icon="📝", layout="centered")

client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
CONFIG_PATH = "visual_config.json"

NS = "visual_"
def K(k): return NS + k

st.markdown(
    """
    <style>
    textarea { font-size:0.8rem !important; line-height:1.3 !important; }
    .block-container { max-width:900px; padding-top:4.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =================================================
# 기본 지침 (단일 텍스트)
# =================================================
DEFAULT_INSTRUCTION = """너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다.
톤은 진지하고 서정적이며, 첫 문장은 강렬한 훅으로 시작한다.
인트로 → 배경 → 사건/전개 → 여운이 남는 결론 순서로 전개한다.
사실 기반 정보를 충분히 포함하되, 사건의 핵심 원인과 결과를 반드시 드러낸다.
선정적 표현, 과도한 비유, 질문형 표현은 사용하지 않는다.
소제목 없이 자연스러운 내레이션만 생성한다.
사용자가 입력한 대본을 시각화에 적합하게 재정렬한다.
"""

# =================================================
# Session State
# =================================================
st.session_state.setdefault(K("input"), "")
st.session_state.setdefault(K("output"), "")
st.session_state.setdefault(K("model"), "gpt-4o-mini")

st.session_state.setdefault(K("instruction"), DEFAULT_INSTRUCTION)
st.session_state.setdefault(K("sets"), [])
st.session_state.setdefault(K("active_id"), None)

st.session_state.setdefault(K("show_editor"), False)
st.session_state.setdefault(K("edit_id"), None)
st.session_state.setdefault(K("delete_mode"), False)
st.session_state.setdefault(K("toolbar_run"), 0)

st.session_state.setdefault(K("reset_confirm"), False)
st.session_state.setdefault(K("reset_text"), "")

# =================================================
# Config I/O
# =================================================
def load_config():
    if not os.path.exists(CONFIG_PATH): return
    try:
        data = json.load(open(CONFIG_PATH, "r", encoding="utf-8"))
    except JSONDecodeError:
        return

    if isinstance(data.get("instruction"), str):
        st.session_state[K("instruction")] = data["instruction"]

    if isinstance(data.get("sets"), list):
        st.session_state[K("sets")] = data["sets"]

    if data.get("active_id"):
        st.session_state[K("active_id")] = data["active_id"]

    if data.get("model"):
        st.session_state[K("model")] = data["model"]

def save_config():
    json.dump(
        {
            "instruction": st.session_state[K("instruction")],
            "sets": st.session_state[K("sets")],
            "active_id": st.session_state[K("active_id")],
            "model": st.session_state[K("model")],
        },
        open(CONFIG_PATH, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=2,
    )

def reset_config():
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    for k in list(st.session_state.keys()):
        if k.startswith(NS):
            del st.session_state[k]
    st.rerun()

# =================================================
# 초기화
# =================================================
if K("loaded") not in st.session_state:
    load_config()
    st.session_state[K("loaded")] = True

if not st.session_state[K("sets")]:
    default = {
        "id": "default",
        "name": "기본 지침",
        "instruction": st.session_state[K("instruction")],
    }
    st.session_state[K("sets")] = [default]
    st.session_state[K("active_id")] = "default"
    save_config()

active_set = next(
    (s for s in st.session_state[K("sets")] if s["id"] == st.session_state[K("active_id")]),
    None,
)
if active_set:
    st.session_state[K("instruction")] = active_set["instruction"]

# =================================================
# 헤더
# =================================================
st.markdown(
    "<h2 style='text-align:right;color:#374151;'>visualking</h2>",
    unsafe_allow_html=True,
)
st.markdown("---")

# =================================================
# 지침 set 선택 / 관리 (단 1회)
# =================================================
sets = st.session_state[K("sets")]
names = [s["name"] for s in sets]
active_index = next(i for i, s in enumerate(sets) if s["id"] == st.session_state[K("active_id")])

st.radio(
    "지침 set 선택",
    range(len(sets)),
    format_func=lambda i: names[i],
    index=active_index,
    horizontal=True,
    label_visibility="collapsed",
    key=K("set_select"),
    on_change=lambda: (
        st.session_state.__setitem__(K("active_id"), sets[st.session_state[K("set_select")]]["id"]),
        st.session_state.__setitem__(K("instruction"), sets[st.session_state[K("set_select")]]["instruction"]),
        save_config(),
    ),
)

toolbar_key = f"{K('toolbar')}_{st.session_state[K('toolbar_run')]}"
action = st.radio(
    "",
    ["-", "추가", "편집", "삭제"],
    horizontal=True,
    label_visibility="collapsed",
    key=toolbar_key,
)

if action == "추가":
    st.session_state[K("show_editor")] = True
    st.session_state[K("edit_id")] = None
    st.session_state[K("toolbar_run")] += 1
    st.rerun()

if action == "편집":
    st.session_state[K("show_editor")] = True
    st.session_state[K("edit_id")] = st.session_state[K("active_id")]
    st.session_state[K("toolbar_run")] += 1
    st.rerun()

if action == "삭제":
    st.session_state[K("delete_mode")] = True
    st.session_state[K("toolbar_run")] += 1
    st.rerun()

st.markdown("---")

# =================================================
# 지침 set 삭제
# =================================================
if st.session_state[K("delete_mode")]:
    idx = st.selectbox("삭제할 지침 선택", range(len(sets)), format_func=lambda i: names[i])
    c1, c2 = st.columns(2)
    if c1.button("삭제", use_container_width=True):
        del_id = sets[idx]["id"]
        st.session_state[K("sets")] = [s for s in sets if s["id"] != del_id]
        st.session_state[K("active_id")] = st.session_state[K("sets")][0]["id"]
        save_config()
        st.session_state[K("delete_mode")] = False
        st.rerun()
    if c2.button("취소", use_container_width=True):
        st.session_state[K("delete_mode")] = False
        st.rerun()

# =================================================
# 지침 set 추가 / 편집 (제목 + 내용만)
# =================================================
if st.session_state[K("show_editor")]:
    edit_id = st.session_state[K("edit_id")]
    target = next((s for s in sets if s["id"] == edit_id), None)

    with st.form("editor"):
        name = st.text_input("지침 set 제목", value=target["name"] if target else "")
        instr = st.text_area("지침 내용", value=target["instruction"] if target else "", height=260)
        ok = st.form_submit_button("저장")
        cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state[K("show_editor")] = False
            st.rerun()

        if ok:
            if target:
                target["name"] = name.strip()
                target["instruction"] = instr.strip()
            else:
                new_id = str(uuid4())
                st.session_state[K("sets")].append(
                    {"id": new_id, "name": name.strip(), "instruction": instr.strip()}
                )
                st.session_state[K("active_id")] = new_id
            save_config()
            st.session_state[K("show_editor")] = False
            st.rerun()

# =================================================
# 메인 입력 / 실행
# =================================================
st.text_area(
    "대본 입력",
    key=K("input"),
    height=180,
    label_visibility="collapsed",
    placeholder="대본을 붙여넣고 지침 수행을 누르세요.",
)

if st.button("지침 수행", use_container_width=True):
    with st.spinner("변환 중..."):
        res = client.chat.completions.create(
            model=st.session_state[K("model")],
            messages=[
                {"role": "system", "content": st.session_state[K("instruction")]},
                {"role": "user", "content": st.session_state[K("input")]},
            ],
            max_tokens=800,
        )
    st.session_state[K("output")] = res.choices[0].message.content

# =================================================
# 출력
# =================================================
if st.session_state[K("output")]:
    st.text_area(
        "결과",
        value=st.session_state[K("output")],
        height=400,
        label_visibility="collapsed",
    )

# =================================================
# 설정
# =================================================
with st.expander("⚙️ 설정"):
    st.selectbox(
        "GPT 모델",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state[K("model")]),
        key=K("model"),
    )
    if st.button("visual_config.json 초기화", use_container_width=True):
        reset_config()
