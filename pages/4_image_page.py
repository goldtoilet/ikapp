import os
import json
import base64
import urllib.request
import urllib.error

import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="imageking", page_icon="🎬", layout="wide")

st.markdown(
    """
    <style>
    textarea {
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
    }
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        font-size: 0.95rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def get_env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v is not None else default

def safe_index(options, value, default=0):
    try:
        return options.index(value)
    except ValueError:
        return default

GPT_API_KEY = get_env("GPT_API_KEY", "")
if not GPT_API_KEY:
    st.error("❌ GPT_API_KEY 가 설정되어 있지 않습니다. .env 또는 환경변수를 확인해주세요.")
    st.stop()

client = OpenAI(api_key=GPT_API_KEY)

IMAGE_MODELS = {"OpenAI gpt-image-1": "gpt-image-1"}
VIDEO_MODELS = {"OpenAI gpt-video-1": "gpt-video-1"}

st.session_state.setdefault("prompt_text", "")
st.session_state.setdefault("image_b64", None)
st.session_state.setdefault("image_model_label", "OpenAI gpt-image-1")
st.session_state.setdefault("image_orientation", "정사각형 1:1 (1024x1024)")
st.session_state.setdefault("image_quality", "low")

st.session_state.setdefault("video_bytes", None)
st.session_state.setdefault("video_error_msg", None)
st.session_state.setdefault("video_model_label", "OpenAI gpt-video-1")
st.session_state.setdefault("video_size", "9:16 (1080x1920)")
st.session_state.setdefault("video_duration", 5)
st.session_state.setdefault("video_fps", 24)

def b64_to_bytes(b64_str: str) -> bytes:
    return base64.b64decode(b64_str)

def get_image_params():
    orientation = st.session_state.get("image_orientation", "정사각형 1:1 (1024x1024)")
    quality = st.session_state.get("image_quality", "low")
    if orientation.startswith("정사각형"):
        size = "1024x1024"
    elif orientation.startswith("가로형"):
        size = "1536x1024"
    else:
        size = "1024x1536"
    return size, quality

def get_video_params():
    size_label = st.session_state.get("video_size", "9:16 (1080x1920)")
    duration = int(st.session_state.get("video_duration", 5))
    fps = int(st.session_state.get("video_fps", 24))

    if size_label.startswith("9:16"):
        size = "1080x1920"
    elif size_label.startswith("16:9"):
        size = "1920x1080"
    else:
        size = "1024x1024"

    duration = max(1, min(duration, 20))
    fps = max(12, min(fps, 60))
    return size, duration, fps

def generate_image(prompt: str):
    if not prompt:
        return None
    size, quality = get_image_params()
    label = st.session_state.get("image_model_label", list(IMAGE_MODELS.keys())[0])
    model = IMAGE_MODELS.get(label, "gpt-image-1")
    resp = client.images.generate(model=model, prompt=prompt, size=size, quality=quality, n=1)
    return resp.data[0].b64_json

def generate_video_from_prompt_rest(prompt: str):
    if not prompt:
        return None, "EMPTY_PROMPT"

    label = st.session_state.get("video_model_label", list(VIDEO_MODELS.keys())[0])
    model = VIDEO_MODELS.get(label, "gpt-video-1")
    size, duration, fps = get_video_params()

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "duration": duration,
        "fps": fps,
        "response_format": "b64_json",
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/videos/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {GPT_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode("utf-8")
        data = json.loads(raw)
        b64 = None
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list) and data["data"]:
                b64 = data["data"][0].get("b64_json")
            if not b64 and "b64_json" in data:
                b64 = data["b64_json"]
        if not b64:
            return None, f"VIDEO_B64_NOT_FOUND: {str(data)[:300]}"
        return base64.b64decode(b64), None
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="ignore")
        except Exception:
            detail = str(e)
        return None, f"HTTPError {e.code}: {detail[:500]}"
    except Exception as e:
        return None, str(e)

with st.sidebar:
    with st.expander("🖼 이미지 옵션", expanded=True):
        image_labels = list(IMAGE_MODELS.keys())
        current_image_label = st.session_state.get("image_model_label", image_labels[0])
        st.session_state["image_model_label"] = st.selectbox(
            "이미지 생성 모델",
            image_labels,
            index=safe_index(image_labels, current_image_label, 0),
        )

        ratios = ["정사각형 1:1 (1024x1024)", "가로형 3:2 (1536x1024)", "세로형 2:3 (1024x1536)"]
        current_ratio = st.session_state.get("image_orientation", ratios[0])
        st.session_state["image_orientation"] = st.radio(
            "비율 선택",
            ratios,
            index=safe_index(ratios, current_ratio, 0),
        )

        qualities = ["low", "high"]
        current_q = st.session_state.get("image_quality", "low")
        st.session_state["image_quality"] = st.radio(
            "품질",
            qualities,
            index=safe_index(qualities, current_q, 0),
            horizontal=True,
        )

    st.markdown("")

    with st.expander("🎬 동영상 생성 (모델/옵션)", expanded=True):
        video_labels = list(VIDEO_MODELS.keys())
        current_video_label = st.session_state.get("video_model_label", video_labels[0])
        st.session_state["video_model_label"] = st.selectbox(
            "동영상 생성 모델",
            video_labels,
            index=safe_index(video_labels, current_video_label, 0),
        )

        v_sizes = ["9:16 (1080x1920)", "16:9 (1920x1080)", "1:1 (1024x1024)"]
        current_vs = st.session_state.get("video_size", v_sizes[0])
        st.session_state["video_size"] = st.radio(
            "영상 비율/해상도",
            v_sizes,
            index=safe_index(v_sizes, current_vs, 0),
        )

        st.session_state["video_duration"] = st.slider(
            "길이(초)",
            min_value=1,
            max_value=20,
            value=int(st.session_state.get("video_duration", 5)),
            step=1,
        )

        st.session_state["video_fps"] = st.slider(
            "FPS",
            min_value=12,
            max_value=60,
            value=int(st.session_state.get("video_fps", 24)),
            step=1,
        )

st.markdown(
    """
    <div>
        <div class="main-title">imageking</div>
        <div class="main-subtitle">
            하나의 프롬프트를 계속 변형해 보면서,<br>
            원하는 스타일을 찾는 실험용 이미지·영상 생성기입니다.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("🧪 이미지 / 영상 생성", expanded=False):
    prompt_text = st.text_area(
        "프롬프트",
        height=220,
        value=st.session_state.get("prompt_text", ""),
        placeholder=(
            "예시:\n"
            "A Korean woman in her 20s with short hair,\n"
            "standing in a neon-lit street at night.\n"
            "50mm lens, medium shot, eye-level angle, cinematic framing.\n"
            "Cinematic realism, soft skin texture, subtle freckles.\n"
            "Rim lighting with pink and blue neon reflections.\n"
            "Moody and emotional atmosphere.\n"
            "Ultra-detailed, sharp focus, 8K resolution."
        ),
    )
    st.session_state["prompt_text"] = prompt_text

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        clicked_image = st.button("🖼 이미지 생성", type="primary", use_container_width=True)
    with col_btn2:
        clicked_video = st.button("🎬 영상 생성", type="secondary", use_container_width=True)

    if clicked_image:
        if not prompt_text.strip():
            st.warning("프롬프트를 먼저 입력해주세요.")
        else:
            with st.spinner("이미지를 생성하는 중입니다..."):
                new_b64 = generate_image(prompt_text.strip())
            if new_b64:
                st.session_state["image_b64"] = new_b64
                st.session_state["video_bytes"] = None
                st.session_state["video_error_msg"] = None
                st.success("✅ 이미지가 생성되었습니다.")
            else:
                st.error("이미지 생성에 실패했습니다.")

    if clicked_video:
        if not prompt_text.strip():
            st.warning("프롬프트를 먼저 입력해주세요.")
        else:
            with st.spinner("영상을 생성하는 중입니다..."):
                video_bytes, err = generate_video_from_prompt_rest(prompt_text.strip())
            if video_bytes:
                st.session_state["video_bytes"] = video_bytes
                st.session_state["video_error_msg"] = None
                st.success("🎬 영상이 생성되었습니다.")
            else:
                st.session_state["video_bytes"] = None
                st.session_state["video_error_msg"] = f"영상 생성 실패: {err}"

    if st.session_state.get("image_b64"):
        st.markdown("---")
        st.markdown("#### 🖼 생성된 이미지")
        img_bytes = b64_to_bytes(st.session_state["image_b64"])
        st.image(img_bytes, use_container_width=True)

        if st.button("🔁 이 프롬프트로 다시 이미지 생성"):
            if not st.session_state.get("prompt_text", "").strip():
                st.warning("프롬프트가 비어 있습니다.")
            else:
                with st.spinner("이미지를 다시 생성하는 중입니다..."):
                    new_b64 = generate_image(st.session_state["prompt_text"].strip())
                if new_b64:
                    st.session_state["image_b64"] = new_b64
                    st.session_state["video_bytes"] = None
                    st.session_state["video_error_msg"] = None
                    st.success("✅ 이미지가 재생성되었습니다.")
                else:
                    st.error("이미지 재생성에 실패했습니다.")
            st.rerun()

    if st.session_state.get("video_bytes"):
        st.markdown("---")
        st.markdown("#### 🎬 생성된 영상 미리보기")
        st.video(st.session_state["video_bytes"])
        st.download_button(
            label="📥 영상 다운로드 (MP4)",
            data=st.session_state["video_bytes"],
            file_name="imageking_output.mp4",
            mime="video/mp4",
        )
    elif st.session_state.get("video_error_msg"):
        st.markdown("---")
        st.markdown("#### ⚠️ 영상 생성 오류")
        st.error(st.session_state["video_error_msg"])
