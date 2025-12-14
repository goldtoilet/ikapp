import streamlit as st
from openai import OpenAI
import os
import json
from json import JSONDecodeError
from uuid import uuid4

st.set_page_config(page_title="scriptking", page_icon="📝", layout="centered")

api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

# ✅ script 페이지 전용 config 파일
CONFIG_PATH = "script_config.json"

# textarea 기본 스타일
st.markdown(
    """
    <style>
    textarea {
        font-size: 0.8rem !important;
        line-height: 1.3 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================
# 기본값(단일 지침 텍스트)
# ============================
DEFAULT_INSTRUCTION_TEXT = "\n\n".join(
    [
        "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다.",
        "톤은 진지하고 서정적이며, 첫 문장은 강렬한 훅으로 시작한다.",
        "인트로 → 배경 → 사건/전개 → 여운이 남는 결론 순서로 전개한다.",
        "사실 기반 정보를 충분히 포함하되, 사건의 핵심 원인과 결과를 반드시 드러낸다.",
        "선정적 표현, 과도한 비유, 독자에게 말을 거는 질문형 표현은 사용하지 않는다.",
        "전체 분량은 500자 이상으로 하고, 소제목 없이 자연스러운 내레이션만 생성하며, 문단 사이에는 한 줄 공백을 둔다.",
        "사용자가 입력한 주제를 내러티브의 중심축으로 삼고, 배경 정보를 자연스럽게 녹여 스토리화한다.",
    ]
)

# ============================
# Session State
# ============================
st.session_state.setdefault("history", [])
st.session_state.setdefault("current_input", "")
st.session_state.setdefault("last_output", "")
st.session_state.setdefault("model_choice", "gpt-4o-mini")

# ✅ 단일 지침 텍스트
st.session_state.setdefault("instruction_text", DEFAULT_INSTRUCTION_TEXT)

# ✅ 지침 set(간단 구조)
#   [{"id": "...", "name": "...", "instruction": "..."}]
st.session_state.setdefault("instruction_sets", [])
st.session_state.setdefault("active_instruction_set_id", None)

# UI 상태
st.session_state.setdefault("show_instruction_set_editor", False)
st.session_state.setdefault("edit_instruction_set_id", None)
st.session_state.setdefault("instset_delete_mode", False)
st.session_state.setdefault("instset_toolbar_run_id", 0)

# reset confirm
st.session_state.setdefault("show_reset_confirm", False)
st.session_state.setdefault("reset_input_value", "")

# 멀티페이지 공통 current_page_id (유지)
st.session_state.setdefault("current_page_id", None)


# ============================
# Config I/O
# ============================
def load_config():
    if not os.path.exists(CONFIG_PATH):
        return
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except JSONDecodeError:
        return
    except Exception:
        return

    # 1) 새 구조 우선 로드
    if isinstance(data.get("instruction_text"), str) and data["instruction_text"].strip():
        st.session_state.instruction_text = data["instruction_text"]

    # 2) 예전 7분할 구조가 남아있으면 합쳐서 가져오기(호환)
    legacy_keys = [
        "inst_role",
        "inst_tone",
        "inst_structure",
        "inst_depth",
        "inst_forbidden",
        "inst_format",
        "inst_user_intent",
    ]
    if not (isinstance(data.get("instruction_text"), str) and data["instruction_text"].strip()):
        legacy_parts = []
        for k in legacy_keys:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                legacy_parts.append(v.strip())
        if legacy_parts:
            st.session_state.instruction_text = "\n\n".join(legacy_parts)

    hist = data.get("history")
    if isinstance(hist, list):
        st.session_state.history = hist[-5:]

    if isinstance(data.get("instruction_sets"), list):
        # 호환: 예전 set에 inst_role 등이 있으면 instruction으로 합쳐 저장
        normalized = []
        for s in data["instruction_sets"]:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or str(uuid4())
            name = s.get("name") or "이름 없는 set"
            if isinstance(s.get("instruction"), str):
                instr = s.get("instruction", "")
            else:
                # legacy set 구조라면 합치기
                parts = []
                for k in legacy_keys:
                    vv = s.get(k)
                    if isinstance(vv, str) and vv.strip():
                        parts.append(vv.strip())
                instr = "\n\n".join(parts) if parts else ""
            normalized.append({"id": sid, "name": name, "instruction": instr})
        st.session_state.instruction_sets = normalized

    if "active_instruction_set_id" in data:
        st.session_state.active_instruction_set_id = data.get("active_instruction_set_id")

    if "current_page_id" in data:
        st.session_state.current_page_id = data.get("current_page_id")

    if isinstance(data.get("model_choice"), str):
        st.session_state.model_choice = data["model_choice"]


def save_config():
    data = {
        "instruction_text": st.session_state.instruction_text,
        "history": st.session_state.history[-5:],
        "instruction_sets": st.session_state.get("instruction_sets", []),
        "active_instruction_set_id": st.session_state.get("active_instruction_set_id"),
        "current_page_id": st.session_state.get("current_page_id"),
        "model_choice": st.session_state.model_choice,
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def reset_config():
    if os.path.exists(CONFIG_PATH):
        try:
            os.remove(CONFIG_PATH)
        except Exception:
            pass

    for key in [
        "history",
        "current_input",
        "last_output",
        "model_choice",
        "instruction_text",
        "instruction_sets",
        "active_instruction_set_id",
        "show_instruction_set_editor",
        "edit_instruction_set_id",
        "instset_delete_mode",
        "instset_toolbar_run_id",
        "show_reset_confirm",
        "reset_input_value",
        "current_page_id",
        "config_loaded",
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


def apply_instruction_set(set_obj: dict):
    st.session_state.instruction_text = (set_obj.get("instruction") or "").strip()
    save_config()


# ============================
# Generation
# ============================
def run_generation():
    topic = st.session_state.current_input.strip()
    if not topic:
        return

    hist = st.session_state.history
    if topic in hist:
        hist.remove(topic)
    hist.append(topic)
    st.session_state.history = hist[-5:]
    save_config()

    system_text = (st.session_state.instruction_text or "").strip()
    if not system_text:
        system_text = DEFAULT_INSTRUCTION_TEXT

    user_text = f"다음 주제에 맞는 다큐멘터리 내레이션을 작성해줘.\n\n주제: {topic}"

    with st.spinner("🎬 대본을 작성하는 중입니다..."):
        res = client.chat.completions.create(
            model=st.session_state.model_choice,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            max_tokens=600,
        )

    st.session_state.last_output = res.choices[0].message.content


# ============================
# Init
# ============================
if "config_loaded" not in st.session_state:
    load_config()
    st.session_state.config_loaded = True

# 기본 set 없으면 생성
if not st.session_state.instruction_sets:
    default_set = {
        "id": "default",
        "name": "기본 지침",
        "instruction": st.session_state.instruction_text or DEFAULT_INSTRUCTION_TEXT,
    }
    st.session_state.instruction_sets = [default_set]
    st.session_state.active_instruction_set_id = "default"
    st.session_state.current_page_id = "default"
    apply_instruction_set(default_set)
    save_config()

# active set 적용
active_id = st.session_state.active_instruction_set_id
active_set = next((s for s in st.session_state.instruction_sets if s.get("id") == active_id), None)
if active_set:
    st.session_state.instruction_text = (active_set.get("instruction") or "").strip()


# ============================
# Layout / CSS
# ============================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 4.5rem;
    }
    .stVerticalBlock { gap: 0.25rem !important; }
    hr { margin-top: 0.35rem !important; margin-bottom: 0.35rem !important; }

    div[data-testid="stTextInput"] input[aria-label="주제 입력"] {
        background-color: white !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 8px !important;
        padding: 14px 14px !important;
        font-size: 1.0rem !important;
        font-weight: 400 !important;
        box-shadow: none !important;
        width: 100% !important;
    }
    div[data-testid="stTextInput"] input[aria-label="주제 입력"]::placeholder {
        color: #9ca3af !important;
        font-size: 0.95rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================
# Header
# ============================
st.markdown(
    "<h2 style='margin-bottom:0.15rem; text-align:right; "
    "color:#9ca3af; font-size:22px;'>scriptking</h2>",
    unsafe_allow_html=True,
)
st.markdown("---")
st.markdown("<div style='margin-top:0.4rem;'></div>", unsafe_allow_html=True)

# ============================
# 지침 set 선택 & 관리 (메인에만)
# ============================
sets = st.session_state.instruction_sets
active_id = st.session_state.active_instruction_set_id
active_name = "선택된 set 없음"

if sets and active_id:
    for s in sets:
        if s.get("id") == active_id:
            active_name = s.get("name", "이름 없는 set")
            break

names = [s.get("name", f"셋 {i+1}") for i, s in enumerate(sets)]
active_index = 0
for i, s in enumerate(sets):
    if s.get("id") == active_id:
        active_index = i
        break

col_l1, col_c1, col_r1 = st.columns([1, 6, 1])
with col_c1:
    st.markdown(
        "<div style='font-size:1.05rem; font-weight:600; color:#4b5563; "
        "margin-bottom:0.15rem; text-align:left;'>지침 set 선택</div>",
        unsafe_allow_html=True,
    )
    selected_index = st.radio(
        "지침 set 선택",
        options=list(range(len(sets))),
        format_func=lambda i: names[i],
        index=active_index,
        key="instset_main_radio",
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_set = sets[selected_index]
    if selected_set.get("id") != active_id:
        st.session_state.active_instruction_set_id = selected_set.get("id")
        st.session_state.current_page_id = selected_set.get("id")
        apply_instruction_set(selected_set)
        st.rerun()

col_l2, col_c2, col_r2 = st.columns([1, 6, 1])
with col_c2:
    st.markdown(
        "<div style='font-size:1.05rem; font-weight:600; color:#4b5563; "
        "margin-top:0.4rem; margin-bottom:0.15rem; text-align:left;'>지침 set 관리</div>",
        unsafe_allow_html=True,
    )
    toolbar_key = f"instset_toolbar_main_{st.session_state['instset_toolbar_run_id']}"
    action = st.radio(
        "",
        ["-", "추가", "편집", "삭제"],
        key=toolbar_key,
        horizontal=True,
        label_visibility="collapsed",
    )

    if action == "추가":
        st.session_state.show_instruction_set_editor = True
        st.session_state.edit_instruction_set_id = None
        st.session_state.instset_toolbar_run_id += 1
        st.rerun()
    elif action == "편집":
        st.session_state.show_instruction_set_editor = True
        st.session_state.edit_instruction_set_id = st.session_state.active_instruction_set_id
        st.session_state.instset_toolbar_run_id += 1
        st.rerun()
    elif action == "삭제":
        st.session_state.instset_delete_mode = True
        st.session_state.instset_toolbar_run_id += 1
        st.rerun()

st.markdown("---")

st.markdown(
    f"<h2 style='text-align:center; margin:0.6rem 0 1.2rem 0; "
    f"font-size:26px; color:#111827;'>{active_name}</h2>",
    unsafe_allow_html=True,
)

# ============================
# 삭제 모드
# ============================
if st.session_state.get("instset_delete_mode", False):
    st.markdown("#### 🗑 지침 set 삭제")
    if not sets:
        st.info("삭제할 지침 set이 없습니다.")
        st.session_state.instset_delete_mode = False
    else:
        del_index = st.selectbox(
            "삭제할 지침 set 선택",
            options=list(range(len(sets))),
            format_func=lambda i: names[i],
            label_visibility="collapsed",
            key="delete_instruction_set_select_main",
        )
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            if st.button("선택한 지침 set 삭제", use_container_width=True):
                delete_id = sets[del_index].get("id")
                st.session_state.instruction_sets = [s for s in sets if s.get("id") != delete_id]

                # active가 삭제되면 첫 set로 이동
                if delete_id == st.session_state.active_instruction_set_id:
                    if st.session_state.instruction_sets:
                        new_active = st.session_state.instruction_sets[0]
                        st.session_state.active_instruction_set_id = new_active.get("id")
                        st.session_state.current_page_id = new_active.get("id")
                        apply_instruction_set(new_active)
                    else:
                        st.session_state.active_instruction_set_id = None
                        st.session_state.current_page_id = None
                        st.session_state.instruction_text = DEFAULT_INSTRUCTION_TEXT

                save_config()
                st.session_state.instset_delete_mode = False
                st.rerun()
        with col_del2:
            if st.button("취소", use_container_width=True):
                st.session_state.instset_delete_mode = False
                st.rerun()

# ============================
# 추가/편집 에디터 (✅ 이름 + 지침내용만)
# ============================
if st.session_state.get("show_instruction_set_editor", False):
    edit_id = st.session_state.get("edit_instruction_set_id")
    edit_mode = bool(edit_id)

    target_set = None
    if edit_mode:
        target_set = next((s for s in st.session_state.instruction_sets if s.get("id") == edit_id), None)

    if edit_mode and target_set:
        title_text = "✏️ 지침 set 편집"
        default_name = target_set.get("name", "")
        default_instruction = target_set.get("instruction", "")
    else:
        title_text = "✨ 새 지침 set 추가"
        default_name = ""
        default_instruction = ""

    st.markdown(f"## {title_text}")

    with st.form("instruction_set_editor_form"):
        set_name = st.text_input(
            "지침 set 이름",
            value=default_name,
            placeholder="예: 다큐 기본셋 / 경제 스릴러 셋 등",
        )
        instruction_txt = st.text_area(
            "지침 내용",
            value=default_instruction,
            height=260,
            placeholder="여기에 시스템 지침(프롬프트)을 한 덩어리로 넣으세요.",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            submitted = st.form_submit_button("💾 저장")
        with col_b:
            cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state.show_instruction_set_editor = False
            st.session_state.edit_instruction_set_id = None
            st.rerun()

        if submitted:
            if not set_name.strip():
                st.error("지침 set 이름을 입력해주세요.")
            else:
                if edit_mode and target_set:
                    target_set["name"] = set_name.strip()
                    target_set["instruction"] = instruction_txt.strip()
                    for i, s in enumerate(st.session_state.instruction_sets):
                        if s.get("id") == edit_id:
                            st.session_state.instruction_sets[i] = target_set
                            break
                    st.session_state.active_instruction_set_id = edit_id
                    st.session_state.current_page_id = edit_id
                    apply_instruction_set(target_set)
                else:
                    new_id = str(uuid4())
                    new_set = {
                        "id": new_id,
                        "name": set_name.strip(),
                        "instruction": instruction_txt.strip(),
                    }
                    st.session_state.instruction_sets.append(new_set)
                    st.session_state.active_instruction_set_id = new_id
                    st.session_state.current_page_id = new_id
                    apply_instruction_set(new_set)

                st.session_state.show_instruction_set_editor = False
                st.session_state.edit_instruction_set_id = None
                save_config()
                st.success("✅ 지침 set이 저장되었습니다.")
                st.rerun()

# ============================
# 설정(모델/초기화/내보내기/불러오기) - 사이드바 대신 메인으로 이동
# ============================
with st.expander("⚙️ 설정", expanded=False):
    st.markdown("##### GPT 모델 선택")
    model = st.selectbox(
        "",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state.model_choice)
        if st.session_state.model_choice in ["gpt-4o-mini", "gpt-4o", "gpt-4.1"]
        else 0,
        label_visibility="collapsed",
    )
    st.session_state.model_choice = model
    save_config()

    st.markdown("---")

    st.markdown("##### 🧹 설정 초기화 (script_config.json)")
    st.caption("모든 지침, 최근 입력, script_config.json 파일을 초기화합니다. 되돌릴 수 없습니다.")
    if not st.session_state.show_reset_confirm:
        if st.button("script_config.json 초기화", use_container_width=True):
            st.session_state.show_reset_confirm = True
            st.session_state.reset_input_value = ""
            st.rerun()
    else:
        st.warning("정말 초기화하시겠습니까? 아래에 '초기화'를 입력한 뒤 실행을 눌러주세요.")
        txt = st.text_input(
            "확인용 단어 입력",
            key="reset_confirm_input",
            value=st.session_state.reset_input_value,
        )
        st.session_state.reset_input_value = txt
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("초기화 실행", use_container_width=True):
                if txt.strip() == "초기화":
                    reset_config()
                else:
                    st.error("입력한 내용이 '초기화'와 일치하지 않습니다.")
        with col_r2:
            if st.button("취소", use_container_width=True):
                st.session_state.show_reset_confirm = False
                st.session_state.reset_input_value = ""
                st.rerun()

    st.markdown("---")

    st.markdown("##### 💾 script_config.json 내보내기 / 불러오기")
    export_data = {
        "instruction_text": st.session_state.instruction_text,
        "history": st.session_state.history[-5:],
        "instruction_sets": st.session_state.get("instruction_sets", []),
        "active_instruction_set_id": st.session_state.get("active_instruction_set_id"),
        "current_page_id": st.session_state.get("current_page_id"),
        "model_choice": st.session_state.model_choice,
    }
    export_json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    st.download_button(
        "⬇️ script_config.json 내보내기",
        data=export_json_str.encode("utf-8"),
        file_name="script_config.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded_file = st.file_uploader(
        "script_config.json 불러오기",
        type=["json"],
        help="이전 백업한 script_config.json 파일을 업로드하세요.",
    )
    if uploaded_file is not None:
        try:
            raw = uploaded_file.read().decode("utf-8")
            _ = json.loads(raw)
        except Exception:
            st.error("❌ JSON 파일을 읽는 중 오류가 발생했습니다. 올바른 파일인지 확인해주세요.")
        else:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(raw)
            if "config_loaded" in st.session_state:
                del st.session_state["config_loaded"]
            st.success("✅ 불러오기 완료. 설정을 적용합니다.")
            st.rerun()

st.markdown("---")

# ============================
# 최근 히스토리 및 입력
# ============================
if st.session_state.history:
    items = st.session_state.history[-5:]
    html_items = ""
    for h in items:
        html_items += f"""
<div style="
    font-size:0.85rem;
    color:#797979;
    margin-bottom:4px;
">{h}</div>
"""
    st.markdown(
        f"""<div style="max-width:460px; margin:40px auto 40px auto;">
  <div style="margin-left:100px; text-align:left;">
    <div style="font-size:0.8rem; color:#9ca3af; margin-bottom:10px;">최근</div>
    {html_items}
  </div>
</div>""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """<div style="max-width:460px; margin:40px auto 40px auto;">
  <div style="margin-left:100px; font-size:0.8rem; color:#d1d5db; text-align:left;">
    최근 입력이 없습니다.
  </div>
</div>""",
        unsafe_allow_html=True,
    )

pad_left, center_col, pad_right = st.columns([1, 7, 1])

with center_col:
    st.markdown(
        "<div style='color:#4b5563; font-size:1.0rem; font-weight:500; "
        "margin-bottom:12px; text-align:center;'>키워드에 맞추어 대본을 만들어드립니다.</div>",
        unsafe_allow_html=True,
    )

    st.text_input(
        label="주제 입력",
        key="current_input",
        placeholder="gpt에게 물어보기",
        label_visibility="collapsed",
        on_change=run_generation,
    )

st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("<div style='margin-top:0.6rem;'></div>", unsafe_allow_html=True)

# ============================
# 생성 결과
# ============================
if st.session_state.last_output:
    st.markdown(
        "<h3 style='text-align:center; margin-bottom:0.75rem;'>📄 생성된 내레이션</h3>",
        unsafe_allow_html=True,
    )
    output_text = st.text_area(
        "",
        value=st.session_state.last_output,
        height=400,
        key="output_editor",
        label_visibility="collapsed",
    )
    st.session_state.last_output = output_text
