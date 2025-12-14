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

# ===== namespace keys (멀티페이지 충돌 방지) =====
NS = "visual_"
def K(name: str) -> str:
    return NS + name

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
# 기본 지침(단일 텍스트)
# ============================
DEFAULT_TEXT_INSTRUCTION = "\n\n".join(
    [
        "너는 감성적이고 스토리텔링이 뛰어난 다큐멘터리 내레이터다.",
        "톤은 진지하고 서정적이며, 첫 문장은 강렬한 훅으로 시작한다.",
        "인트로 → 배경 → 사건/전개 → 여운이 남는 결론 순서로 전개한다.",
        "사실 기반 정보를 충분히 포함하되, 사건의 핵심 원인과 결과를 반드시 드러낸다.",
        "선정적 표현, 과도한 비유, 독자에게 말을 거는 질문형 표현은 사용하지 않는다.",
        "소제목 없이 자연스러운 내레이션만 생성하며, 문단 사이에는 한 줄 공백을 둔다.",
        "사용자가 입력한 대본을 내러티브 중심축으로 삼아, 시각화(이미지 연상)에 적합하게 정돈한다.",
    ]
)

DEFAULT_IMAGE_INSTRUCTION = ""  # 필요하면 기본값 넣어도 됨

# ============================
# Session State
# ============================
st.session_state.setdefault(K("current_input"), "")
st.session_state.setdefault(K("last_output"), "")
st.session_state.setdefault(K("model_choice"), "gpt-4o-mini")
st.session_state.setdefault(K("current_page_id"), None)

# ✅ 단일 지침 텍스트
st.session_state.setdefault(K("text_instruction"), DEFAULT_TEXT_INSTRUCTION)
st.session_state.setdefault(K("image_instruction"), DEFAULT_IMAGE_INSTRUCTION)

# ✅ 지침 set (간단 구조)
#   [{"id": "...", "name": "...", "instruction": "..."}]
st.session_state.setdefault(K("text_instruction_sets"), [])
st.session_state.setdefault(K("active_text_set_id"), None)

# ✅ 공통 이미지 지침 set (간단 구조)
#   [{"id": "...", "name": "...", "content": "..."}]
st.session_state.setdefault(K("image_instruction_sets"), [])
st.session_state.setdefault(K("active_image_set_id"), None)

# UI 상태
st.session_state.setdefault(K("show_text_set_editor"), False)
st.session_state.setdefault(K("edit_text_set_id"), None)
st.session_state.setdefault(K("text_set_delete_mode"), False)
st.session_state.setdefault(K("text_toolbar_run_id"), 0)

st.session_state.setdefault(K("show_image_set_editor"), False)
st.session_state.setdefault(K("edit_image_set_id"), None)
st.session_state.setdefault(K("image_set_delete_mode"), False)
st.session_state.setdefault(K("image_toolbar_run_id"), 0)

# reset confirm
st.session_state.setdefault(K("show_reset_confirm"), False)
st.session_state.setdefault(K("reset_input_value"), "")

# history (선택: 필요 없으면 통째로 제거 가능)
st.session_state.setdefault(K("history"), [])

# ============================
# Config I/O (호환 포함)
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
    if isinstance(data.get("text_instruction"), str) and data["text_instruction"].strip():
        st.session_state[K("text_instruction")] = data["text_instruction"]

    if isinstance(data.get("image_instruction"), str):
        st.session_state[K("image_instruction")] = data.get("image_instruction", "")

    # 2) 옛 구조(inst_role~)가 남아있으면 합쳐서 가져오기(호환)
    legacy_keys = [
        "inst_role",
        "inst_tone",
        "inst_structure",
        "inst_depth",
        "inst_forbidden",
        "inst_format",
        "inst_user_intent",
    ]
    if not (isinstance(data.get("text_instruction"), str) and data["text_instruction"].strip()):
        parts = []
        for k in legacy_keys:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
        if parts:
            st.session_state[K("text_instruction")] = "\n\n".join(parts)

    # 3) 옛 common_image_instruction 호환
    if not isinstance(data.get("image_instruction"), str):
        if isinstance(data.get("common_image_instruction"), str):
            st.session_state[K("image_instruction")] = data.get("common_image_instruction", "")

    # history
    hist = data.get("history")
    if isinstance(hist, list):
        st.session_state[K("history")] = hist[-5:]

    # 모델
    if isinstance(data.get("model_choice"), str):
        st.session_state[K("model_choice")] = data["model_choice"]

    # text sets (새 구조)
    if isinstance(data.get("text_instruction_sets"), list):
        normalized = []
        for s in data["text_instruction_sets"]:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or str(uuid4())
            name = s.get("name") or "이름 없는 set"
            instr = s.get("instruction") if isinstance(s.get("instruction"), str) else ""
            normalized.append({"id": sid, "name": name, "instruction": instr})
        st.session_state[K("text_instruction_sets")] = normalized

    # text sets (옛 instruction_sets 호환)
    elif isinstance(data.get("instruction_sets"), list):
        normalized = []
        for s in data["instruction_sets"]:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or str(uuid4())
            name = s.get("name") or "이름 없는 set"
            # legacy set이면 합치기
            if isinstance(s.get("instruction"), str):
                instr = s.get("instruction", "")
            else:
                parts = []
                for k in legacy_keys:
                    vv = s.get(k)
                    if isinstance(vv, str) and vv.strip():
                        parts.append(vv.strip())
                instr = "\n\n".join(parts) if parts else ""
            normalized.append({"id": sid, "name": name, "instruction": instr})
        st.session_state[K("text_instruction_sets")] = normalized

    # active text id (새/옛)
    if "active_text_set_id" in data:
        st.session_state[K("active_text_set_id")] = data.get("active_text_set_id")
    elif "active_instruction_set_id" in data:
        st.session_state[K("active_text_set_id")] = data.get("active_instruction_set_id")

    # image sets (새 구조)
    if isinstance(data.get("image_instruction_sets"), list):
        normalized = []
        for s in data["image_instruction_sets"]:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or str(uuid4())
            name = s.get("name") or "이름 없는 이미지 set"
            content = s.get("content") if isinstance(s.get("content"), str) else ""
            normalized.append({"id": sid, "name": name, "content": content})
        st.session_state[K("image_instruction_sets")] = normalized

    # active image id (새/옛)
    if "active_image_set_id" in data:
        st.session_state[K("active_image_set_id")] = data.get("active_image_set_id")
    elif "active_image_instruction_set_id" in data:
        st.session_state[K("active_image_set_id")] = data.get("active_image_instruction_set_id")

    # current_page_id
    if "current_page_id" in data:
        st.session_state[K("current_page_id")] = data.get("current_page_id")


def save_config():
    data = {
        "text_instruction": st.session_state[K("text_instruction")],
        "image_instruction": st.session_state[K("image_instruction")],
        "history": st.session_state[K("history")][-5:],
        "model_choice": st.session_state[K("model_choice")],
        "text_instruction_sets": st.session_state.get(K("text_instruction_sets"), []),
        "active_text_set_id": st.session_state.get(K("active_text_set_id")),
        "image_instruction_sets": st.session_state.get(K("image_instruction_sets"), []),
        "active_image_set_id": st.session_state.get(K("active_image_set_id")),
        "current_page_id": st.session_state.get(K("current_page_id")),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def reset_config():
    if os.path.exists(CONFIG_PATH):
        try:
            os.remove(CONFIG_PATH)
        except Exception:
            pass

    keys = [
        K("current_input"),
        K("last_output"),
        K("model_choice"),
        K("current_page_id"),
        K("text_instruction"),
        K("image_instruction"),
        K("text_instruction_sets"),
        K("active_text_set_id"),
        K("image_instruction_sets"),
        K("active_image_set_id"),
        K("show_text_set_editor"),
        K("edit_text_set_id"),
        K("text_set_delete_mode"),
        K("text_toolbar_run_id"),
        K("show_image_set_editor"),
        K("edit_image_set_id"),
        K("image_set_delete_mode"),
        K("image_toolbar_run_id"),
        K("show_reset_confirm"),
        K("reset_input_value"),
        K("history"),
        K("config_loaded"),
    ]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]

    st.rerun()


def apply_text_set(set_obj: dict):
    st.session_state[K("text_instruction")] = (set_obj.get("instruction") or "").strip()
    save_config()


def apply_image_set(set_obj: dict):
    st.session_state[K("image_instruction")] = (set_obj.get("content") or "").strip()
    save_config()


# ============================
# Generation
# ============================
def run_generation():
    text = st.session_state[K("current_input")].strip()
    if not text:
        return

    # history
    hist = st.session_state[K("history")]
    if text in hist:
        hist.remove(text)
    hist.append(text)
    st.session_state[K("history")] = hist[-5:]
    save_config()

    system_text_parts = []
    tinst = (st.session_state[K("text_instruction")] or "").strip()
    iinst = (st.session_state[K("image_instruction")] or "").strip()
    if tinst:
        system_text_parts.append(tinst)
    if iinst:
        system_text_parts.append(iinst)

    system_text = "\n\n".join(system_text_parts).strip()
    if not system_text:
        system_text = DEFAULT_TEXT_INSTRUCTION

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


# ============================
# Init
# ============================
if K("config_loaded") not in st.session_state:
    load_config()
    st.session_state[K("config_loaded")] = True

# 기본 text set 없으면 생성
if not st.session_state[K("text_instruction_sets")]:
    default_set = {
        "id": "default",
        "name": "기본 지침",
        "instruction": st.session_state[K("text_instruction")] or DEFAULT_TEXT_INSTRUCTION,
    }
    st.session_state[K("text_instruction_sets")] = [default_set]
    st.session_state[K("active_text_set_id")] = "default"
    st.session_state[K("current_page_id")] = "default"
    apply_text_set(default_set)
    save_config()

# active text set 적용
active_text_id = st.session_state[K("active_text_set_id")]
active_text_set = next(
    (s for s in st.session_state[K("text_instruction_sets")] if s.get("id") == active_text_id),
    None,
)
if active_text_set:
    st.session_state[K("text_instruction")] = (active_text_set.get("instruction") or "").strip()

# 기본 image set 없으면 생성
if not st.session_state[K("image_instruction_sets")]:
    img_default = {
        "id": "img_default",
        "name": "기본 이미지 지침",
        "content": st.session_state[K("image_instruction")] or DEFAULT_IMAGE_INSTRUCTION,
    }
    st.session_state[K("image_instruction_sets")] = [img_default]
    st.session_state[K("active_image_set_id")] = "img_default"
    apply_image_set(img_default)
    save_config()

# active image set 적용
active_img_id = st.session_state[K("active_image_set_id")]
active_img_set = next(
    (s for s in st.session_state[K("image_instruction_sets")] if s.get("id") == active_img_id),
    None,
)
if active_img_set:
    st.session_state[K("image_instruction")] = (active_img_set.get("content") or "").strip()


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
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================
# Header
# ============================
st.markdown(
    "<h2 style='margin-bottom:0.15rem; text-align:right; color:#374151; font-size:22px;'>visualking</h2>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ============================
# Text Instruction Set 선택/관리
# ============================
text_sets = st.session_state[K("text_instruction_sets")]
active_text_id = st.session_state[K("active_text_set_id")]
active_text_name = "선택된 set 없음"
active_text_set = None

if text_sets and active_text_id:
    for s in text_sets:
        if s.get("id") == active_text_id:
            active_text_set = s
            active_text_name = s.get("name", "이름 없는 set")
            break

st.markdown(
    f"<h3 style='text-align:center; margin:0.3rem 0 0.75rem 0;'>{active_text_name}</h3>",
    unsafe_allow_html=True,
)

names = [s.get("name", f"셋 {i+1}") for i, s in enumerate(text_sets)]
active_index = 0
for i, s in enumerate(text_sets):
    if s.get("id") == active_text_id:
        active_index = i
        break

col_a, col_b, col_c = st.columns([1, 4, 1])
with col_b:
    st.markdown(
        "<div style='font-size:0.85rem; color:#6b7280; margin-bottom:0.2rem; text-align:center;'>지침 set 선택</div>",
        unsafe_allow_html=True,
    )
    selected_index = st.radio(
        "지침 set 선택",
        options=list(range(len(text_sets))),
        format_func=lambda i: names[i],
        index=active_index,
        key=K("text_set_radio"),
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_set = text_sets[selected_index]
    if selected_set.get("id") != active_text_id:
        st.session_state[K("active_text_set_id")] = selected_set.get("id")
        st.session_state[K("current_page_id")] = selected_set.get("id")
        apply_text_set(selected_set)
        st.rerun()

with col_b:
    st.markdown(
        "<div style='font-size:0.85rem; color:#6b7280; margin-top:0.6rem; margin-bottom:0.2rem; text-align:center;'>지침 set 관리</div>",
        unsafe_allow_html=True,
    )
    toolbar_key = f"{K('text_toolbar')}_{st.session_state[K('text_toolbar_run_id')]}"
    action = st.radio(
        "",
        ["-", "추가", "편집", "삭제"],
        key=toolbar_key,
        horizontal=True,
        label_visibility="collapsed",
    )
    if action == "추가":
        st.session_state[K("show_text_set_editor")] = True
        st.session_state[K("edit_text_set_id")] = None
        st.session_state[K("text_toolbar_run_id")] += 1
        st.rerun()
    elif action == "편집":
        st.session_state[K("show_text_set_editor")] = True
        st.session_state[K("edit_text_set_id")] = st.session_state[K("active_text_set_id")]
        st.session_state[K("text_toolbar_run_id")] += 1
        st.rerun()
    elif action == "삭제":
        st.session_state[K("text_set_delete_mode")] = True
        st.session_state[K("text_toolbar_run_id")] += 1
        st.rerun()

st.markdown("---")

# ============================
# Text Set 삭제 모드
# ============================
if st.session_state.get(K("text_set_delete_mode"), False):
    st.markdown("#### 🗑 지침 set 삭제")
    if not text_sets:
        st.info("삭제할 지침 set이 없습니다.")
        st.session_state[K("text_set_delete_mode")] = False
    else:
        del_index = st.selectbox(
            "삭제할 지침 set 선택",
            options=list(range(len(text_sets))),
            format_func=lambda i: names[i],
            label_visibility="collapsed",
            key=K("text_delete_select"),
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("선택한 지침 set 삭제", use_container_width=True, key=K("btn_text_delete")):
                delete_id = text_sets[del_index].get("id")
                st.session_state[K("text_instruction_sets")] = [s for s in text_sets if s.get("id") != delete_id]

                if delete_id == st.session_state[K("active_text_set_id")]:
                    if st.session_state[K("text_instruction_sets")]:
                        new_active = st.session_state[K("text_instruction_sets")][0]
                        st.session_state[K("active_text_set_id")] = new_active.get("id")
                        st.session_state[K("current_page_id")] = new_active.get("id")
                        apply_text_set(new_active)
                    else:
                        st.session_state[K("active_text_set_id")] = None
                        st.session_state[K("current_page_id")] = None
                        st.session_state[K("text_instruction")] = DEFAULT_TEXT_INSTRUCTION

                save_config()
                st.session_state[K("text_set_delete_mode")] = False
                st.rerun()
        with c2:
            if st.button("취소", use_container_width=True, key=K("btn_text_delete_cancel")):
                st.session_state[K("text_set_delete_mode")] = False
                st.rerun()

# ============================
# Text Set 추가/편집 (✅ 이름 + 내용만)
# ============================
if st.session_state.get(K("show_text_set_editor"), False):
    edit_id = st.session_state.get(K("edit_text_set_id"))
    edit_mode = bool(edit_id)

    target = None
    if edit_mode:
        target = next((s for s in st.session_state[K("text_instruction_sets")] if s.get("id") == edit_id), None)

    if edit_mode and target:
        title = "✏️ 지침 set 편집"
        default_name = target.get("name", "")
        default_instr = target.get("instruction", "")
    else:
        title = "✨ 새 지침 set 추가"
        default_name = ""
        default_instr = ""

    st.markdown(f"## {title}")

    with st.form(K("text_set_form")):
        set_name = st.text_input("지침 set 제목", value=default_name, placeholder="예: 다큐 기본 / 경제 스릴러 등", key=K("text_set_name"))
        instr = st.text_area("지침 내용", value=default_instr, height=260, key=K("text_set_instr"))

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("💾 저장")
        with c2:
            cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state[K("show_text_set_editor")] = False
            st.session_state[K("edit_text_set_id")] = None
            st.rerun()

        if submitted:
            if not set_name.strip():
                st.error("지침 set 제목을 입력해주세요.")
            else:
                if edit_mode and target:
                    target["name"] = set_name.strip()
                    target["instruction"] = instr.strip()
                    for i, s in enumerate(st.session_state[K("text_instruction_sets")]):
                        if s.get("id") == edit_id:
                            st.session_state[K("text_instruction_sets")][i] = target
                            break
                    st.session_state[K("active_text_set_id")] = edit_id
                    st.session_state[K("current_page_id")] = edit_id
                    apply_text_set(target)
                else:
                    new_id = str(uuid4())
                    new_set = {"id": new_id, "name": set_name.strip(), "instruction": instr.strip()}
                    st.session_state[K("text_instruction_sets")].append(new_set)
                    st.session_state[K("active_text_set_id")] = new_id
                    st.session_state[K("current_page_id")] = new_id
                    apply_text_set(new_set)

                st.session_state[K("show_text_set_editor")] = False
                st.session_state[K("edit_text_set_id")] = None
                save_config()
                st.success("✅ 지침 set이 저장되었습니다.")
                st.rerun()

# ============================
# 공통 이미지 지침 set (선택/관리)
# ============================
st.markdown("### 🖼 공통 이미지 지침 set")

img_sets = st.session_state[K("image_instruction_sets")]
active_img_id = st.session_state[K("active_image_set_id")]

img_names = [s.get("name", f"이미지 셋 {i+1}") for i, s in enumerate(img_sets)]
active_img_index = 0
for i, s in enumerate(img_sets):
    if s.get("id") == active_img_id:
        active_img_index = i
        break

col_i1, col_i2, col_i3 = st.columns([1, 4, 1])
with col_i2:
    st.markdown(
        "<div style='font-size:0.85rem; color:#6b7280; margin-bottom:0.2rem; text-align:center;'>공통 이미지 지침 set 선택</div>",
        unsafe_allow_html=True,
    )
    sel_img_index = st.radio(
        "공통 이미지 지침 set 선택",
        options=list(range(len(img_sets))),
        format_func=lambda i: img_names[i],
        index=active_img_index,
        key=K("img_set_radio"),
        horizontal=True,
        label_visibility="collapsed",
    )
    chosen_img = img_sets[sel_img_index]
    if chosen_img.get("id") != active_img_id:
        st.session_state[K("active_image_set_id")] = chosen_img.get("id")
        apply_image_set(chosen_img)
        st.rerun()

with col_i2:
    st.markdown(
        "<div style='font-size:0.85rem; color:#6b7280; margin-top:0.6rem; margin-bottom:0.2rem; text-align:center;'>이미지 지침 set 관리</div>",
        unsafe_allow_html=True,
    )
    img_toolbar_key = f"{K('img_toolbar')}_{st.session_state[K('image_toolbar_run_id')]}"
    img_action = st.radio(
        "",
        ["-", "추가", "편집", "삭제"],
        key=img_toolbar_key,
        horizontal=True,
        label_visibility="collapsed",
    )
    if img_action == "추가":
        st.session_state[K("show_image_set_editor")] = True
        st.session_state[K("edit_image_set_id")] = None
        st.session_state[K("image_toolbar_run_id")] += 1
        st.rerun()
    elif img_action == "편집":
        st.session_state[K("show_image_set_editor")] = True
        st.session_state[K("edit_image_set_id")] = st.session_state[K("active_image_set_id")]
        st.session_state[K("image_toolbar_run_id")] += 1
        st.rerun()
    elif img_action == "삭제":
        st.session_state[K("image_set_delete_mode")] = True
        st.session_state[K("image_toolbar_run_id")] += 1
        st.rerun()

# 이미지 set 삭제 모드
if st.session_state.get(K("image_set_delete_mode"), False):
    st.markdown("#### 🗑 공통 이미지 지침 set 삭제")
    if not img_sets:
        st.info("삭제할 이미지 지침 set이 없습니다.")
        st.session_state[K("image_set_delete_mode")] = False
    else:
        del_index = st.selectbox(
            "삭제할 이미지 지침 set 선택",
            options=list(range(len(img_sets))),
            format_func=lambda i: img_names[i],
            label_visibility="collapsed",
            key=K("img_delete_select"),
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("선택한 이미지 지침 set 삭제", use_container_width=True, key=K("btn_img_delete")):
                delete_id = img_sets[del_index].get("id")
                st.session_state[K("image_instruction_sets")] = [s for s in img_sets if s.get("id") != delete_id]

                if delete_id == st.session_state[K("active_image_set_id")]:
                    if st.session_state[K("image_instruction_sets")]:
                        new_active = st.session_state[K("image_instruction_sets")][0]
                        st.session_state[K("active_image_set_id")] = new_active.get("id")
                        apply_image_set(new_active)
                    else:
                        st.session_state[K("active_image_set_id")] = None
                        st.session_state[K("image_instruction")] = ""

                save_config()
                st.session_state[K("image_set_delete_mode")] = False
                st.rerun()
        with c2:
            if st.button("취소", use_container_width=True, key=K("btn_img_delete_cancel")):
                st.session_state[K("image_set_delete_mode")] = False
                st.rerun()

# 이미지 set 추가/편집 (✅ 이름 + 내용만)
if st.session_state.get(K("show_image_set_editor"), False):
    edit_id = st.session_state.get(K("edit_image_set_id"))
    edit_mode = bool(edit_id)

    target = None
    if edit_mode:
        target = next((s for s in st.session_state[K("image_instruction_sets")] if s.get("id") == edit_id), None)

    if edit_mode and target:
        title = "✏️ 공통 이미지 지침 set 편집"
        default_name = target.get("name", "")
        default_content = target.get("content", "")
    else:
        title = "✨ 새 공통 이미지 지침 set 추가"
        default_name = ""
        default_content = st.session_state[K("image_instruction")] or ""

    st.markdown(f"## {title}")

    with st.form(K("img_set_form")):
        set_name = st.text_input("이미지 지침 set 제목", value=default_name, placeholder="예: 네온 사이버펑크 / 미니멀 카툰 등", key=K("img_set_name"))
        content = st.text_area("이미지 지침 내용", value=default_content, height=220, key=K("img_set_content"))

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("💾 저장")
        with c2:
            cancel = st.form_submit_button("취소")

        if cancel:
            st.session_state[K("show_image_set_editor")] = False
            st.session_state[K("edit_image_set_id")] = None
            st.rerun()

        if submitted:
            if not set_name.strip():
                st.error("이미지 지침 set 제목을 입력해주세요.")
            else:
                if edit_mode and target:
                    target["name"] = set_name.strip()
                    target["content"] = content.strip()
                    for i, s in enumerate(st.session_state[K("image_instruction_sets")]):
                        if s.get("id") == edit_id:
                            st.session_state[K("image_instruction_sets")][i] = target
                            break
                    st.session_state[K("active_image_set_id")] = edit_id
                    apply_image_set(target)
                else:
                    new_id = str(uuid4())
                    new_set = {"id": new_id, "name": set_name.strip(), "content": content.strip()}
                    st.session_state[K("image_instruction_sets")].append(new_set)
                    st.session_state[K("active_image_set_id")] = new_id
                    apply_image_set(new_set)

                st.session_state[K("show_image_set_editor")] = False
                st.session_state[K("edit_image_set_id")] = None
                save_config()
                st.success("✅ 이미지 지침 set이 저장되었습니다.")
                st.rerun()

st.markdown("---")

# ============================
# ⚙️ 설정 (사이드바 대신 메인)
# ============================
with st.expander("⚙️ 설정", expanded=False):
    st.markdown("##### GPT 모델 선택")
    model = st.selectbox(
        "",
        ["gpt-4o-mini", "gpt-4o", "gpt-4.1"],
        index=["gpt-4o-mini", "gpt-4o", "gpt-4.1"].index(st.session_state[K("model_choice")])
        if st.session_state[K("model_choice")] in ["gpt-4o-mini", "gpt-4o", "gpt-4.1"]
        else 0,
        label_visibility="collapsed",
        key=K("model_select"),
    )
    st.session_state[K("model_choice")] = model
    save_config()

    st.markdown("---")

    st.markdown("##### 🧹 설정 초기화 (visual_config.json)")
    st.caption("모든 지침, 최근 입력, visual_config.json 파일을 초기화합니다. 되돌릴 수 없습니다.")
    if not st.session_state[K("show_reset_confirm")]:
        if st.button("visual_config.json 초기화", use_container_width=True, key=K("btn_reset_open")):
            st.session_state[K("show_reset_confirm")] = True
            st.session_state[K("reset_input_value")] = ""
            st.rerun()
    else:
        st.warning("정말 초기화하시겠습니까? 아래에 '초기화'를 입력한 뒤 실행을 눌러주세요.")
        txt = st.text_input("확인용 단어 입력", key=K("reset_confirm_input"), value=st.session_state[K("reset_input_value")])
        st.session_state[K("reset_input_value")] = txt

        c1, c2 = st.columns(2)
        with c1:
            if st.button("초기화 실행", use_container_width=True, key=K("btn_reset_run")):
                if txt.strip() == "초기화":
                    reset_config()
                else:
                    st.error("입력한 내용이 '초기화'와 일치하지 않습니다.")
        with c2:
            if st.button("취소", use_container_width=True, key=K("btn_reset_cancel")):
                st.session_state[K("show_reset_confirm")] = False
                st.session_state[K("reset_input_value")] = ""
                st.rerun()

    st.markdown("---")

    st.markdown("##### 💾 visual_config.json 내보내기 / 불러오기")
    export_data = {
        "text_instruction": st.session_state[K("text_instruction")],
        "image_instruction": st.session_state[K("image_instruction")],
        "history": st.session_state[K("history")][-5:],
        "model_choice": st.session_state[K("model_choice")],
        "text_instruction_sets": st.session_state.get(K("text_instruction_sets"), []),
        "active_text_set_id": st.session_state.get(K("active_text_set_id")),
        "image_instruction_sets": st.session_state.get(K("image_instruction_sets"), []),
        "active_image_set_id": st.session_state.get(K("active_image_set_id")),
        "current_page_id": st.session_state.get(K("current_page_id")),
    }
    export_json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

    st.download_button(
        "⬇️ visual_config.json 내보내기",
        data=export_json_str.encode("utf-8"),
        file_name="visual_config.json",
        mime="application/json",
        use_container_width=True,
        key=K("download_config"),
    )

    uploaded_file = st.file_uploader(
        "visual_config.json 불러오기",
        type=["json"],
        help="이전 백업한 visual_config.json 파일을 업로드하세요.",
        key=K("upload_config"),
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
            if K("config_loaded") in st.session_state:
                del st.session_state[K("config_loaded")]
            st.success("✅ 불러오기 완료. 설정을 적용합니다.")
            st.rerun()

st.markdown("---")

# ============================
# 메인 입력/실행
# ============================
pad_left, center_col, pad_right = st.columns([1, 7, 1])

with center_col:
    st.markdown(
        "<div style='color:#4b5563; font-size:1.0rem; font-weight:500; "
        "margin-bottom:12px; text-align:center;'>대본을 시각화 해 드립니다. 대본을 넣어주세요.</div>",
        unsafe_allow_html=True,
    )

    st.text_area(
        label="대본 입력",
        key=K("current_input"),
        placeholder="여기에 대본을 붙여넣고, 아래 지침수행 버튼을 눌러주세요.",
        height=180,
        label_visibility="collapsed",
    )

    if st.button("지침 수행", use_container_width=True, key=K("btn_run")):
        run_generation()

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

# ============================
# 출력
# ============================
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
