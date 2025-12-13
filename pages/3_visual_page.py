import streamlit as st
from openai import OpenAI
import os
import json
from json import JSONDecodeError
from uuid import uuid4

st.set_page_config(page_title="visualking", page_icon="📝", layout="centered")

api_key = os.getenv("GPT_API_KEY")
client = OpenAI(api_key=api_key)

CONFIG_PATH = "visual_config.json"

NS = "visual_"
def K(name: str) -> str:
    return NS + name

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


st.session_state.setdefault(K("inst_role"), "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다.")
st.session_state.setdefault(K("inst_tone"), "톤은 진지하고 서정적이며, 첫 문장은 강렬한 훅으로 시작한다.")
st.session_state.setdefault(K("inst_structure"), "인트로 → 배경 → 사건/전개 → 여운이 남는 결론 순서로 전개한다.")
st.session_state.setdefault(K("inst_depth"), "사실 기반 정보를 충분히 포함하되, 사건의 핵심 원인과 결과를 반드시 드러낸다.")
st.session_state.setdefault(K("inst_forbidden"), "선정적 표현, 과도한 비유, 독자에게 말을 거는 질문형 표현은 사용하지 않는다.")
st.session_state.setdefault(K("inst_format"), "전체 분량은 500자 이상으로 하고, 소제목 없이 자연스러운 내레이션만 생성하며, 문단 사이에는 한 줄 공백을 둔다.")
st.session_state.setdefault(K("inst_user_intent"), "사용자가 입력한 주제를 내러티브의 중심축으로 삼고, 배경 정보를 자연스럽게 녹여 스토리화한다.")

st.session_state.setdefault(K("current_input"), "")
st.session_state.setdefault(K("last_output"), "")
st.session_state.setdefault(K("model_choice"), "gpt-4o-mini")

st.session_state.setdefault(K("current_page_id"), None)

st.session_state.setdefault(K("instruction_sets"), [])
st.session_state.setdefault(K("active_instruction_set_id"), None)
st.session_state.setdefault(K("show_instruction_set_editor"), False)
st.session_state.setdefault(K("edit_instruction_set_id"), None)
st.session_state.setdefault(K("instset_toolbar_run_id"), 0)
st.session_state.setdefault(K("instset_delete_mode"), False)

st.session_state.setdefault(K("image_instruction_sets"), [])
st.session_state.setdefault(K("active_image_instruction_set_id"), None)
st.session_state.setdefault(K("show_image_instruction_set_editor"), False)
st.session_state.setdefault(K("edit_image_instruction_set_id"), None)
st.session_state.setdefault(K("image_instset_toolbar_run_id"), 0)
st.session_state.setdefault(K("image_instset_delete_mode"), False)
st.session_state.setdefault(K("common_image_instruction"), "")

st.session_state.setdefault(K("show_reset_confirm"), False)
st.session_state.setdefault(K("reset_input_value"), "")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except JSONDecodeError:
        return

    if isinstance(data.get("inst_role"), str):
        st.session_state[K("inst_role")] = data["inst_role"]
    elif isinstance(data.get("role_instruction"), str):
        st.session_state[K("inst_role")] = data["role_instruction"]

    for key in ["inst_tone", "inst_structure", "inst_depth", "inst_forbidden", "inst_format", "inst_user_intent"]:
        if isinstance(data.get(key), str):
            st.session_state[K(key)] = data[key]

    hist = data.get("history")
    if isinstance(hist, list):
        st.session_state[K("history")] = hist[-5:]

    if isinstance(data.get("instruction_sets"), list):
        st.session_state[K("instruction_sets")] = data["instruction_sets"]
    if "active_instruction_set_id" in data:
        st.session_state[K("active_instruction_set_id")] = data["active_instruction_set_id"]

    if isinstance(data.get("image_instruction_sets"), list):
        st.session_state[K("image_instruction_sets")] = data["image_instruction_sets"]
    if "active_image_instruction_set_id" in data:
        st.session_state[K("active_image_instruction_set_id")] = data["active_image_instruction_set_id"]
    if isinstance(data.get("common_image_instruction"), str):
        st.session_state[K("common_image_instruction")] = data["common_image_instruction"]

    if "current_page_id" in data:
        st.session_state[K("current_page_id")] = data.get("current_page_id")

def save_config():
    data = {
        "inst_role": st.session_state[K("inst_role")],
        "inst_tone": st.session_state[K("inst_tone")],
        "inst_structure": st.session_state[K("inst_structure")],
        "inst_depth": st.session_state[K("inst_depth")],
        "inst_forbidden": st.session_state[K("inst_forbidden")],
        "inst_format": st.session_state[K("inst_format")],
        "inst_user_intent": st.session_state[K("inst_user_intent")],
        "history": st.session_state[K("history")][-5:],
        "instruction_sets": st.session_state.get(K("instruction_sets"), []),
        "active_instruction_set_id": st.session_state.get(K("active_instruction_set_id")),
        "image_instruction_sets": st.session_state.get(K("image_instruction_sets"), []),
        "active_image_instruction_set_id": st.session_state.get(K("active_image_instruction_set_id")),
        "common_image_instruction": st.session_state.get(K("common_image_instruction"), ""),
        "current_page_id": st.session_state.get(K("current_page_id")),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def reset_config():
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)

    for key in [
        K("inst_role"),
        K("inst_tone"),
        K("inst_structure"),
        K("inst_depth"),
        K("inst_forbidden"),
        K("inst_format"),
        K("inst_user_intent"),
        K("history"),
        K("current_input"),
        K("last_output"),
        K("model_choice"),
        K("current_page_id"),
        K("instruction_sets"),
        K("active_instruction_set_id"),
        K("show_instruction_set_editor"),
        K("edit_instruction_set_id"),
        K("instset_toolbar_run_id"),
        K("instset_delete_mode"),
        K("image_instruction_sets"),
        K("active_image_instruction_set_id"),
        K("show_image_instruction_set_editor"),
        K("edit_image_instruction_set_id"),
        K("image_instset_toolbar_run_id"),
        K("image_instset_delete_mode"),
        K("common_image_instruction"),
        K("show_reset_confirm"),
        K("reset_input_value"),
        K("config_loaded"),
    ]:
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()

def apply_instruction_set(set_obj: dict):
    for key in ["inst_role", "inst_tone", "inst_structure", "inst_depth", "inst_forbidden", "inst_format", "inst_user_intent"]:
        if key in set_obj:
            st.session_state[K(key)] = set_obj.get(key, "")
    save_config()

def apply_image_instruction_set(set_obj: dict):
    st.session_state[K("common_image_instruction")] = set_obj.get("content", "")
    save_config()

def sync_active_set_field(field_name: str, value: str):
    active_id = st.session_state.get(K("active_instruction_set_id"))
    sets = st.session_state.get(K("instruction_sets"), [])
    if not active_id or not sets:
        return
    for s in sets:
        if s.get("id") == active_id:
            s[field_name] = value
            break
    st.session_state[K("instruction_sets")] = sets
    save_config()

def ensure_active_set_applied():
    sets = st.session_state.get(K("instruction_sets"), [])
    active_id = st.session_state.get(K("active_instruction_set_id"))
    if not sets or not active_id:
        return
    active_set = next((s for s in sets if s.get("id") == active_id), None)
    if active_set:
        for key in ["inst_role", "inst_tone", "inst_structure", "inst_depth", "inst_forbidden", "inst_format", "inst_user_intent"]:
            if key in active_set:
                st.session_state[K(key)] = active_set.get(key, "")

def ensure_active_image_set_applied():
    sets = st.session_state.get(K("image_instruction_sets"), [])
    active_id = st.session_state.get(K("active_image_instruction_set_id"))
    if not sets or not active_id:
        return
    active_set = next((s for s in sets if s.get("id") == active_id), None)
    if active_set:
        st.session_state[K("common_image_instruction")] = active_set.get("content", "")

def run_generation():
    text = st.session_state[K("current_input")].strip()
    if not text:
        return

    system_parts = [
        st.session_state[K("inst_role")],
        st.session_state[K("inst_tone")],
        st.session_state[K("inst_structure")],
        st.session_state[K("inst_depth")],
        st.session_state[K("inst_forbidden")],
        st.session_state[K("inst_format")],
        st.session_state[K("inst_user_intent")],
        st.session_state[K("common_image_instruction")],
    ]
    system_text = "\n\n".join(part.strip() for part in system_parts if isinstance(part, str) and part.strip())

    user_text = (
        "다음에 제공하는 대본(텍스트)을 위의 지침에 맞게 정돈하고, "
        "시각화를 위한 내레이션/이미지 연상에 적합한 형태로 다시 작성해줘.\n\n"
        f"대본:\n{text}"
    )

    with st.spinner("🎬 지침에 따라 대본을 변환하는 중입니다..."):
        res = client.chat.completions.create(
            model=st.session_state[K("model_choice")],
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            max_tokens=800,
        )

    st.session_state[K("last_output")] = res.choices[0].message.content

if K("config_loaded") not in st.session_state:
    load_config()
    st.session_state[K("config_loaded")] = True

if not st.session_state[K("instruction_sets")]:
    default_set = {
        "id": "default",
        "name": "기본 지침",
        "inst_role": st.session_state[K("inst_role")],
        "inst_tone": st.session_state[K("inst_tone")],
        "inst_structure": st.session_state[K("inst_structure")],
        "inst_depth": st.session_state[K("inst_depth")],
        "inst_forbidden": st.session_state[K("inst_forbidden")],
        "inst_format": st.session_state[K("inst_format")],
        "inst_user_intent": st.session_state[K("inst_user_intent")],
    }
    st.session_state[K("instruction_sets")] = [default_set]
    st.session_state[K("active_instruction_set_id")] = "default"
    st.session_state[K("current_page_id")] = "default"
    save_config()
else:
    ensure_active_set_applied()
    if st.session_state.get(K("current_page_id")) is None and st.session_state.get(K("active_instruction_set_id")):
        st.session_state[K("current_page_id")] = st.session_state[K("active_instruction_set_id")]
        save_config()

if not st.session_state[K("image_instruction_sets")]:
    img_default_set = {
        "id": "img_default",
        "name": "기본 이미지 지침",
        "content": st.session_state[K("common_image_instruction")] or "",
    }
    st.session_state[K("image_instruction_sets")] = [img_default_set]
    st.session_state[K("active_image_instruction_set_id")] = "img_default"
    save_config()
else:
    ensure_active_image_set_applied()

st.markdown(
    """
    <style>
    .block-container {
        max-width: 900px;
        padding-top: 4.5rem;
    }
    .stVerticalBlock {
        gap: 0.25rem !important;
    }
    hr {
        margin-top: 0.35rem !important;
        margin-bottom: 0.35rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    .sidebar-top {
        flex-grow: 1;
    }
    .sidebar-bottom {
        margin-top: auto;
        padding-top: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("<div class='sidebar-top'>", unsafe_allow_html=True)
    st.markdown("### 📘 지침")

    with st.expander("1. 역할 지침 (Role Instructions)", expanded=False):
        st.caption("ChatGPT가 어떤 캐릭터 / 전문가 / 화자인지 정의합니다.")
        st.markdown(
            "- 예: `당신은 다큐멘터리 전문 내레이터이다.`\n"
            "- 예: `당신은 사건의 흐름을 촘촘히 짜주는 스토리텔링 편집자다.`\n"
            "- 예: `당신은 유튜브 쇼츠용 대본을 압축해주는 전문가다.`"
        )
        inst_role_edit = st.text_area(
            "역할 지침",
            st.session_state[K("inst_role")],
            height=125,
            key=K("inst_role_edit"),
        )
        if st.button("역할 지침 저장", key=K("save_role")):
            if inst_role_edit.strip():
                st.session_state[K("inst_role")] = inst_role_edit.strip()
                sync_active_set_field("inst_role", st.session_state[K("inst_role")])
            st.success("역할 지침이 저장되었습니다.")

    with st.expander("2. 톤 & 스타일 지침", expanded=False):
        st.caption("어떤 분위기/문체/리듬으로 말할지 정의합니다.")
        st.markdown(
            "- 예: `톤은 진지하고 저널리즘 스타일을 유지한다.`\n"
            "- 예: `첫 문장은 100% 강렬한 훅으로 시작한다.`\n"
            "- 예: `문장은 짧고 간결하며 리듬감 있게 구성한다.`"
        )
        inst_tone_edit = st.text_area(
            "톤 & 스타일 지침",
            st.session_state[K("inst_tone")],
            height=125,
            key=K("inst_tone_edit"),
        )
        if st.button("톤 & 스타일 지침 저장", key=K("save_tone")):
            if inst_tone_edit.strip():
                st.session_state[K("inst_tone")] = inst_tone_edit.strip()
                sync_active_set_field("inst_tone", st.session_state[K("inst_tone")])
            st.success("톤 & 스타일 지침이 저장되었습니다.")

    with st.expander("3. 콘텐츠 구성 지침", expanded=False):
        st.caption("초반–중반–후반 또는 장면 흐름을 어떻게 짤지 정의합니다.")
        st.markdown(
            "- 예: `인트로 → 배경 → 사건 → 인물 → 결론 단계로 전개하라.`\n"
            "- 예: `각 문단은 3~4문장으로 제한한다.`\n"
            "- 예: `스토리 전개는 시간순으로 배열한다.`"
        )
        inst_structure_edit = st.text_area(
            "콘텐츠 구성 지침",
            st.session_state[K("inst_structure")],
            height=125,
            key=K("inst_structure_edit"),
        )
        if st.button("콘텐츠 구성 지침 저장", key=K("save_structure")):
            if inst_structure_edit.strip():
                st.session_state[K("inst_structure")] = inst_structure_edit.strip()
                sync_active_set_field("inst_structure", st.session_state[K("inst_structure")])
            st.success("콘텐츠 구성 지침이 저장되었습니다.")

    with st.expander("4. 정보 밀도 & 조사 심도 지침", expanded=False):
        st.caption("얼마나 깊게, 얼마나 촘촘하게 설명할지 정의합니다.")
        st.markdown(
            "- 예: `사실 기반의 정보 비율을 50% 이상 유지.`\n"
            "- 예: `불필요한 수식어는 최소화.`\n"
            "- 예: `사건의 핵심 원인·결과를 반드시 포함.`"
        )
        inst_depth_edit = st.text_area(
            "정보 밀도 & 조사 심도 지침",
            st.session_state[K("inst_depth")],
            height=125,
            key=K("inst_depth_edit"),
        )
        if st.button("정보 밀도 지침 저장", key=K("save_depth")):
            if inst_depth_edit.strip():
                st.session_state[K("inst_depth")] = inst_depth_edit.strip()
                sync_active_set_field("inst_depth", st.session_state[K("inst_depth")])
            st.success("정보 밀도 지침이 저장되었습니다.")

    with st.expander("5. 금지 지침 (Forbidden Rules)", expanded=False):
        st.caption("절대 쓰지 말아야 할 표현/스타일/토픽을 정의합니다.")
        st.markdown(
            "- 예: `예시나 비유를 남발하지 마라.`\n"
            "- 예: `독자에게 질문 형태로 말 걸지 말라.`\n"
            "- 예: `선정적 표현은 제외.`"
        )
        inst_forbidden_edit = st.text_area(
            "금지 지침",
            st.session_state[K("inst_forbidden")],
            height=125,
            key=K("inst_forbidden_edit"),
        )
        if st.button("금지 지침 저장", key=K("save_forbidden")):
            if inst_forbidden_edit.strip():
                st.session_state[K("inst_forbidden")] = inst_forbidden_edit.strip()
                sync_active_set_field("inst_forbidden", st.session_state[K("inst_forbidden")])
            st.success("금지 지침이 저장되었습니다.")

    with st.expander("6. 출력 형식 지침 (Output Format)", expanded=False):
        st.caption("길이, 단락, 제목, 마크다운 형식 등을 정의합니다.")
        st.markdown(
            "- 예: `전체 500자 이상.`\n"
            "- 예: `소제목 없이 자연스러운 내레이션만 생성.`\n"
            "- 예: `문단 간 공백 1줄 유지.`"
        )
        inst_format_edit = st.text_area(
            "출력 형식 지침",
            st.session_state[K("inst_format")],
            height=125,
            key=K("inst_format_edit"),
        )
        if st.button("출력 형식 지침 저장", key=K("save_format")):
            if inst_format_edit.strip():
                st.session_state[K("inst_format")] = inst_format_edit.strip()
                sync_active_set_field("inst_format", st.session_state[K("inst_format")])
            st.success("출력 형식 지침이 저장되었습니다.")

    with st.expander("7. 사용자 요청 반영 지침", expanded=False):
        st.caption("사용자가 준 주제/키워드를 어떻게 스토리 안에 녹일지 정의합니다.")
        st.markdown(
            "- 예: `사용자가 입력한 키워드를 내러티브 중심축으로 사용한다.`\n"
            "- 예: `주제의 배경 정보를 먼저 파악한 뒤 스토리화한다.`"
        )
        inst_user_intent_edit = st.text_area(
            "사용자 요청 반영 지침",
            st.session_state[K("inst_user_intent")],
            height=125,
            key=K("inst_user_intent_edit"),
        )
        if st.button("사용자 요청 지침 저장", key=K("save_user_intent")):
            if inst_user_intent_edit.strip():
                st.session_state[K("inst_user_intent")] = inst_user_intent_edit.strip()
                sync_active_set_field("inst_user_intent", st.session_state[K("inst_user_intent")])
            st.success("사용자 요청 반영 지침이 저장되었습니다.")

    st.markdown("---")
    st.markdown("### 🖼 공통 이미지 지침 set")

    img_sets = st.session_state[K("image_instruction_sets")]
    active_img_id = st.session_state[K("active_image_instruction_set_id")]

    if img_sets:
        img_names = [s.get("name", f"이미지 셋 {i+1}") for i, s in enumerate(img_sets)]
        active_img_index = 0
        for i, s in enumerate(img_sets):
            if s.get("id") == active_img_id:
                active_img_index = i
                break

        selected_img_index = st.radio(
            "공통 이미지 지침 set 선택",
            options=list(range(len(img_sets))),
            format_func=lambda i: img_names[i],
            index=active_img_index,
            label_visibility="collapsed",
            key=K("image_instset_selector"),
        )

        selected_img_set = img_sets[selected_img_index]
        if selected_img_set.get("id") != active_img_id:
            st.session_state[K("active_image_instruction_set_id")] = selected_img_set.get("id")
            apply_image_instruction_set(selected_img_set)
            st.rerun()

    img_toolbar_key = f"{K('image_instset_toolbar')}_{st.session_state[K('image_instset_toolbar_run_id')]}"
    img_action = st.radio(
        "",
        ["-", "추가", "편집", "삭제"],
        key=img_toolbar_key,
        horizontal=True,
        label_visibility="collapsed",
    )

    if img_action == "추가":
        st.session_state[K("show_image_instruction_set_editor")] = True
        st.session_state[K("edit_image_instruction_set_id")] = None
        st.session_state[K("image_instset_toolbar_run_id")] += 1
        st.rerun()
    elif img_action == "편집":
        st.session_state[K("show_image_instruction_set_editor")] = True
        st.session_state[K("edit_image_instruction_set_id")] = st.session_state[K("active_image_instruction_set_id")]
        st.session_state[K("image_instset_toolbar_run_id")] += 1
        st.rerun()
    elif img_action == "삭제":
        st.session_state[K("image_instset_delete_mode")] = True
        st.session_state[K("image_instset_toolbar_run_id")] += 1
        st.rerun()

    if st.session_state[K("image_instset_delete_mode")]:
        sets = st.session_state[K("image_instruction_sets")]
        if not sets:
            st.info("삭제할 공통 이미지 지침 set이 없습니다.")
        else:
            names = [s.get("name", f"이미지 셋 {i+1}") for i, s in enumerate(sets)]
            del_index = st.selectbox(
                "삭제할 공통 이미지 지침 set 선택",
                options=list(range(len(sets))),
                format_func=lambda i: names[i],
                label_visibility="collapsed",
                key=K("delete_image_instruction_set_select"),
            )
            col_img_del1, col_img_del2 = st.columns(2)
            with col_img_del1:
                if st.button("선택한 이미지 지침 set 삭제", use_container_width=True, key=K("btn_delete_img_set")):
                    delete_id = sets[del_index].get("id")
                    st.session_state[K("image_instruction_sets")] = [s for s in sets if s.get("id") != delete_id]
                    if delete_id == st.session_state[K("active_image_instruction_set_id")]:
                        if st.session_state[K("image_instruction_sets")]:
                            st.session_state[K("active_image_instruction_set_id")] = st.session_state[K("image_instruction_sets")][0].get("id")
                            ensure_active_image_set_applied()
                        else:
                            st.session_state[K("active_image_instruction_set_id")] = None
                            st.session_state[K("common_image_instruction")] = ""
                    save_config()
                    st.session_state[K("image_instset_delete_mode")] = False
                    st.rerun()
            with col_img_del2:
                if st.button("취소", use_container_width=True, key=K("btn_cancel_delete_img_set")):
                    st.session_state[K("image_instset_delete_mode")] = False
                    st.rerun()

    st.markdown("</div><div class='sidebar-bottom'>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### ⚙️ 설정")

    with st.expander("GPT 모델 선택", expanded=False):
        model = st.selectbox(
            "",
            ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
            index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state[K("model_choice")]),
            label_visibility="collapsed",
            key=K("model_selectbox"),
        )
        st.session_state[K("model_choice")] = model

    with st.expander("🧹 설정 초기화 (visual_config.json)", expanded=False):
        st.caption("모든 지침, 최근 입력, visual_config.json 파일을 초기화합니다. 되돌릴 수 없습니다.")
        if not st.session_state[K("show_reset_confirm")]:
            if st.button("visual_config.json 초기화", use_container_width=True, key=K("btn_reset_open")):
                st.session_state[K("show_reset_confirm")] = True
                st.session_state[K("reset_input_value")] = ""
                st.rerun()
        else:
            st.warning("정말 visual_config.json을 초기화하시겠습니까? 아래에 '초기화'를 입력한 뒤 실행을 눌러주세요.")
            txt = st.text_input(
                "확인용 단어 입력",
                key=K("reset_confirm_input"),
                value=st.session_state[K("reset_input_value")],
            )
            st.session_state[K("reset_input_value")] = txt
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("초기화 실행", use_container_width=True, key=K("btn_reset_run")):
                    if txt.strip() == "초기화":
                        reset_config()
                    else:
                        st.error("입력한 내용이 '초기화'와 일치하지 않습니다.")
            with col_r2:
                if st.button("취소", use_container_width=True, key=K("btn_reset_cancel")):
                    st.session_state[K("show_reset_confirm")] = False
                    st.session_state[K("reset_input_value")] = ""
                    st.rerun()

    with st.expander("💾 visual_config.json 내보내기 / 불러오기", expanded=False):
        st.caption("현재 설정을 파일로 저장하거나, 기존 visual_config.json 파일을 불러올 수 있습니다.")

        export_data = {
            "inst_role": st.session_state[K("inst_role")],
            "inst_tone": st.session_state[K("inst_tone")],
            "inst_structure": st.session_state[K("inst_structure")],
            "inst_depth": st.session_state[K("inst_depth")],
            "inst_forbidden": st.session_state[K("inst_forbidden")],
            "inst_format": st.session_state[K("inst_format")],
            "inst_user_intent": st.session_state[K("inst_user_intent")],
            "history": st.session_state[K("history")][-5:],
            "instruction_sets": st.session_state.get(K("instruction_sets"), []),
            "active_instruction_set_id": st.session_state.get(K("active_instruction_set_id")),
            "image_instruction_sets": st.session_state.get(K("image_instruction_sets"), []),
            "active_image_instruction_set_id": st.session_state.get(K("active_image_instruction_set_id")),
            "common_image_instruction": st.session_state.get(K("common_image_instruction"), ""),
            "current_page_id": st.session_state.get(K("current_page_id")),
        }
        export_json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ visual_config.json 내보내기",
            data=export_json_str.encode("utf-8"),
            file_name="visual_config.json",
            mime="application/json",
            use_container_width=True,
            key=K("download_visual_config"),
        )

        st.markdown("---")

        uploaded_file = st.file_uploader(
            "visual_config.json 불러오기",
            type=["json"],
            help="이전 백업한 visual_config.json 파일을 업로드하세요.",
            key=K("upload_visual_config"),
        )

        if uploaded_file is not None:
            try:
                raw = uploaded_file.read().decode("utf-8")
                _ = json.loads(raw)
            except Exception:
                st.error("❌ JSON 파일을 읽는 중 오류가 발생했습니다. 올바른 visual_config.json인지 확인해주세요.")
            else:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    f.write(raw)

                if K("config_loaded") in st.session_state:
                    del st.session_state[K("config_loaded")]

                load_config()
                ensure_active_set_applied()
                ensure_active_image_set_applied()

                if not st.session_state[K("instruction_sets")]:
                    default_set = {
                        "id": "default",
                        "name": "기본 지침",
                        "inst_role": st.session_state[K("inst_role")],
                        "inst_tone": st.session_state[K("inst_tone")],
                        "inst_structure": st.session_state[K("inst_structure")],
                        "inst_depth": st.session_state[K("inst_depth")],
                        "inst_forbidden": st.session_state[K("inst_forbidden")],
                        "inst_format": st.session_state[K("inst_format")],
                        "inst_user_intent": st.session_state[K("inst_user_intent")],
                    }
                    st.session_state[K("instruction_sets")] = [default_set]
                    st.session_state[K("active_instruction_set_id")] = "default"

                if not st.session_state[K("image_instruction_sets")]:
                    img_default_set = {
                        "id": "img_default",
                        "name": "기본 이미지 지침",
                        "content": st.session_state[K("common_image_instruction")] or "",
                    }
                    st.session_state[K("image_instruction_sets")] = [img_default_set]
                    st.session_state[K("active_image_instruction_set_id")] = "img_default"

                if st.session_state.get(K("current_page_id")) is None and st.session_state.get(K("active_instruction_set_id")):
                    st.session_state[K("current_page_id")] = st.session_state[K("active_instruction_set_id")]

                save_config()
                st.success("✅ visual_config.json이 성공적으로 불러와졌습니다. 설정이 적용됩니다.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

inst_sets_main = st.session_state[K("instruction_sets")]
active_id_main = st.session_state[K("active_instruction_set_id")]
active_set_main = None
active_name_main = "선택된 set 없음"

if inst_sets_main and active_id_main:
    for s in inst_sets_main:
        if s.get("id") == active_id_main:
            active_set_main = s
            active_name_main = s.get("name", "이름 없는 set")
            break

if active_set_main is None:
    active_set_main = {
        "inst_role": st.session_state[K("inst_role")],
        "inst_tone": st.session_state[K("inst_tone")],
        "inst_structure": st.session_state[K("inst_structure")],
        "inst_depth": st.session_state[K("inst_depth")],
        "inst_forbidden": st.session_state[K("inst_forbidden")],
        "inst_format": st.session_state[K("inst_format")],
        "inst_user_intent": st.session_state[K("inst_user_intent")],
    }

st.markdown(
    "<h2 style='margin-bottom:0.15rem; text-align:right; color:#374151; font-size:22px;'>visualking</h2>",
    unsafe_allow_html=True,
)

if inst_sets_main:
    names_main = [s.get("name", f"셋 {i+1}") for i, s in enumerate(inst_sets_main)]
    active_index_main = 0
    for i, s in enumerate(inst_sets_main):
        if s.get("id") == active_id_main:
            active_index_main = i
            break

    col_l1, col_c1, col_r1 = st.columns([1, 4, 1])
    with col_c1:
        st.markdown(
            "<div style='font-size:0.85rem; color:#6b7280; margin-bottom:0.2rem; text-align:center;'>지침 set 선택</div>",
            unsafe_allow_html=True,
        )
        selected_index_main = st.radio(
            "지침 set 선택",
            options=list(range(len(inst_sets_main))),
            format_func=lambda i: names_main[i],
            index=active_index_main,
            key=K("instset_main_radio"),
            horizontal=True,
            label_visibility="collapsed",
        )
        selected_set_main = inst_sets_main[selected_index_main]
        if selected_set_main.get("id") != active_id_main:
            st.session_state[K("active_instruction_set_id")] = selected_set_main.get("id")
            st.session_state[K("current_page_id")] = selected_set_main.get("id")
            apply_instruction_set(selected_set_main)
            save_config()
            st.rerun()

    col_l2, col_c2, col_r2 = st.columns([1, 4, 1])
    with col_c2:
        st.markdown(
            "<div style='font-size:0.85rem; color:#6b7280; margin-top:0.6rem; margin-bottom:0.2rem; text-align:center;'>지침 set 관리</div>",
            unsafe_allow_html=True,
        )
        toolbar_key = f"{K('instset_toolbar_main')}_{st.session_state[K('instset_toolbar_run_id')]}"
        action_main = st.radio(
            "",
            ["-", "추가", "편집", "삭제"],
            key=toolbar_key,
            horizontal=True,
            label_visibility="collapsed",
        )

        if action_main == "추가":
            st.session_state[K("show_instruction_set_editor")] = True
            st.session_state[K("edit_instruction_set_id")] = None
            st.session_state[K("instset_toolbar_run_id")] += 1
            st.rerun()
        elif action_main == "편집":
            st.session_state[K("show_instruction_set_editor")] = True
            st.session_state[K("edit_instruction_set_id")] = st.session_state[K("active_instruction_set_id")]
            st.session_state[K("instset_toolbar_run_id")] += 1
            st.rerun()
        elif action_main == "삭제":
            st.session_state[K("instset_delete_mode")] = True
            st.session_state[K("instset_toolbar_run_id")] += 1
            st.rerun()

st.markdown("---")

st.markdown(
    f"<h3 style='text-align:center; margin:0.5rem 0 0.75rem 0;'>{active_name_main}</h3>",
    unsafe_allow_html=True,
)
st.markdown("---")

if st.session_state.get(K("instset_delete_mode"), False):
    sets = st.session_state[K("instruction_sets")]
    st.markdown("#### 🗑 지침 set 삭제")

    if not sets:
        st.info("삭제할 지침 set이 없습니다.")
        st.session_state[K("instset_delete_mode")] = False
    else:
        names_del = [s.get("name", f"셋 {i+1}") for i, s in enumerate(sets)]
        del_index = st.selectbox(
            "삭제할 지침 set 선택",
            options=list(range(len(sets))),
            format_func=lambda i: names_del[i],
            label_visibility="collapsed",
            key=K("delete_instruction_set_select_main"),
        )
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            if st.button("선택한 지침 set 삭제", use_container_width=True, key=K("btn_delete_text_set")):
                delete_id = sets[del_index].get("id")
                st.session_state[K("instruction_sets")] = [s for s in sets if s.get("id") != delete_id]
                if delete_id == st.session_state[K("active_instruction_set_id")]:
                    if st.session_state[K("instruction_sets")]:
                        st.session_state[K("active_instruction_set_id")] = st.session_state[K("instruction_sets")][0].get("id")
                        st.session_state[K("current_page_id")] = st.session_state[K("active_instruction_set_id")]
                        ensure_active_set_applied()
                    else:
                        st.session_state[K("active_instruction_set_id")] = None
                        st.session_state[K("current_page_id")] = None
                save_config()
                st.session_state[K("instset_delete_mode")] = False
                st.rerun()
        with col_del2:
            if st.button("취소", use_container_width=True, key=K("btn_cancel_delete_text_set")):
                st.session_state[K("instset_delete_mode")] = False
                st.rerun()

if st.session_state.get(K("show_instruction_set_editor"), False):
    edit_id = st.session_state.get(K("edit_instruction_set_id"))
    edit_mode = bool(edit_id)

    target_set = None
    if edit_mode:
        for s in st.session_state[K("instruction_sets")]:
            if s.get("id") == edit_id:
                target_set = s
                break

    if edit_mode and target_set:
        title_text = "✏️ 지침 set 편집"
        default_name = target_set.get("name", "")
        role_txt_default = target_set.get("inst_role", "")
        tone_txt_default = target_set.get("inst_tone", "")
        struct_txt_default = target_set.get("inst_structure", "")
        depth_txt_default = target_set.get("inst_depth", "")
        forbid_txt_default = target_set.get("inst_forbidden", "")
        format_txt_default = target_set.get("inst_format", "")
        intent_txt_default = target_set.get("inst_user_intent", "")
    else:
        title_text = "✨ 새 지침 set 추가"
        default_name = ""
        role_txt_default = ""
        tone_txt_default = ""
        struct_txt_default = ""
        depth_txt_default = ""
        forbid_txt_default = ""
        format_txt_default = ""
        intent_txt_default = ""

    st.markdown(f"## {title_text}")

    with st.form(K("instruction_set_editor_form")):
        set_name = st.text_input("지침 set 이름", value=default_name, placeholder="예: 다큐 기본셋 / 연애의 경제학 셋 등", key=K("set_name_input"))

        role_txt = st.text_area("1. 역할 지침", role_txt_default, height=80, key=K("role_txt"))
        tone_txt = st.text_area("2. 톤 & 스타일 지침", tone_txt_default, height=80, key=K("tone_txt"))
        struct_txt = st.text_area("3. 콘텐츠 구성 지침", struct_txt_default, height=80, key=K("struct_txt"))
        depth_txt = st.text_area("4. 정보 밀도 & 조사 심도 지침", depth_txt_default, height=80, key=K("depth_txt"))
        forbid_txt = st.text_area("5. 금지 지침", forbid_txt_default, height=80, key=K("forbid_txt"))
        format_txt = st.text_area("6. 출력 형식 지침", format_txt_default, height=80, key=K("format_txt"))
        intent_txt = st.text_area("7. 사용자 요청 반영 지침", intent_txt_default, height=80, key=K("intent_txt"))

        col_a, col_b = st.columns(2)
        with col_a:
            submit_label = "💾 수정 내용 저장" if edit_mode else "💾 지침 set 저장"
            submitted = st.form_submit_button(submit_label)
        with col_b:
            cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state[K("show_instruction_set_editor")] = False
            st.session_state[K("edit_instruction_set_id")] = None
            st.rerun()

        if submitted:
            if not set_name.strip():
                st.error("지침 set 이름을 입력해주세요.")
            else:
                if edit_mode and target_set:
                    target_set["name"] = set_name.strip()
                    target_set["inst_role"] = role_txt.strip()
                    target_set["inst_tone"] = tone_txt.strip()
                    target_set["inst_structure"] = struct_txt.strip()
                    target_set["inst_depth"] = depth_txt.strip()
                    target_set["inst_forbidden"] = forbid_txt.strip()
                    target_set["inst_format"] = format_txt.strip()
                    target_set["inst_user_intent"] = intent_txt.strip()
                    for i, s in enumerate(st.session_state[K("instruction_sets")]):
                        if s.get("id") == edit_id:
                            st.session_state[K("instruction_sets")][i] = target_set
                            break
                    st.session_state[K("active_instruction_set_id")] = edit_id
                    st.session_state[K("current_page_id")] = edit_id
                else:
                    new_id = str(uuid4())
                    new_set = {
                        "id": new_id,
                        "name": set_name.strip(),
                        "inst_role": role_txt.strip(),
                        "inst_tone": tone_txt.strip(),
                        "inst_structure": struct_txt.strip(),
                        "inst_depth": depth_txt.strip(),
                        "inst_forbidden": forbid_txt.strip(),
                        "inst_format": format_txt.strip(),
                        "inst_user_intent": intent_txt.strip(),
                    }
                    st.session_state[K("instruction_sets")].append(new_set)
                    st.session_state[K("active_instruction_set_id")] = new_id
                    st.session_state[K("current_page_id")] = new_id

                ensure_active_set_applied()
                st.session_state[K("show_instruction_set_editor")] = False
                st.session_state[K("edit_instruction_set_id")] = None
                save_config()
                st.success("✅ 지침 set이 저장되었습니다.")
                st.rerun()

if st.session_state.get(K("show_image_instruction_set_editor"), False):
    edit_id = st.session_state.get(K("edit_image_instruction_set_id"))
    edit_mode = bool(edit_id)

    target_set = None
    if edit_mode:
        for s in st.session_state[K("image_instruction_sets")]:
            if s.get("id") == edit_id:
                target_set = s
                break

    if edit_mode and target_set:
        title_text = "✏️ 공통 이미지 지침 set 편집"
        default_name = target_set.get("name", "")
        content_default = target_set.get("content", "")
    else:
        title_text = "✨ 새 공통 이미지 지침 set 추가"
        default_name = ""
        content_default = st.session_state[K("common_image_instruction")] or ""

    st.markdown(f"## {title_text}")

    with st.form(K("image_instruction_set_editor_form")):
        set_name = st.text_input(
            "공통 이미지 지침 set 이름",
            value=default_name,
            placeholder="예: 다큐 기본 이미지 스타일 / 감성 쇼츠 스타일 등",
            key=K("img_set_name"),
        )

        content_txt = st.text_area(
            "공통 이미지 지침 내용",
            content_default,
            height=200,
            key=K("img_content_txt"),
            help="예: 카메라 구도, 조명 스타일, 색감, 해상도, 렌즈, 화풍 등 통합 프롬프트",
        )

        col_a, col_b = st.columns(2)
        with col_a:
            submit_label = "💾 수정 내용 저장" if edit_mode else "💾 공통 이미지 지침 set 저장"
            submitted = st.form_submit_button(submit_label)
        with col_b:
            cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state[K("show_image_instruction_set_editor")] = False
            st.session_state[K("edit_image_instruction_set_id")] = None
            st.rerun()

        if submitted:
            if not set_name.strip():
                st.error("공통 이미지 지침 set 이름을 입력해주세요.")
            else:
                if edit_mode and target_set:
                    target_set["name"] = set_name.strip()
                    target_set["content"] = content_txt.strip()
                    for i, s in enumerate(st.session_state[K("image_instruction_sets")]):
                        if s.get("id") == edit_id:
                            st.session_state[K("image_instruction_sets")][i] = target_set
                            break
                    st.session_state[K("active_image_instruction_set_id")] = edit_id
                else:
                    new_id = str(uuid4())
                    new_set = {"id": new_id, "name": set_name.strip(), "content": content_txt.strip()}
                    st.session_state[K("image_instruction_sets")].append(new_set)
                    st.session_state[K("active_image_instruction_set_id")] = new_id

                st.session_state[K("common_image_instruction")] = content_txt.strip()
                ensure_active_image_set_applied()
                st.session_state[K("show_image_instruction_set_editor")] = False
                st.session_state[K("edit_image_instruction_set_id")] = None
                save_config()
                st.success("✅ 공통 이미지 지침 set이 저장되었습니다.")
                st.rerun()

pad_left, center_col, pad_right = st.columns([1, 7, 1])

with center_col:
    st.markdown(
        "<div style='color:#4b5563; font-size:1.0rem; font-weight:500; margin-bottom:12px; text-align:center;'>대본을 시각화 해 드립니다. 대본을 넣어주세요.</div>",
        unsafe_allow_html=True,
    )

    _ = st.text_area(
        label="주제 입력",
        key=K("current_input"),
        placeholder="여기에 대본을 붙여넣고, 아래 지침수행 버튼을 눌러주세요.",
        height=180,
        label_visibility="collapsed",
    )

    if st.button("지침 수행", use_container_width=True, key=K("btn_run")):
        run_generation()

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

if st.session_state[K("last_output")]:
    st.markdown(
        "<h3 style='text-align:center; margin-bottom:0.6rem;'>📄 변환된 결과</h3>",
        unsafe_allow_html=True,
    )
    output_text = st.text_area(
        "",
        value=st.session_state[K("last_output")],
        height=400,
        key=K("output_editor"),
        label_visibility="collapsed",
    )
    st.session_state[K("last_output")] = output_text
