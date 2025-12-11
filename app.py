import streamlit as st

# 🔽 pages 폴더 안의 파일 import
from pages import script_page, visual_page, memo_page, image_page, find_page, sub_page, bulk_page

# 페이지 이름 - 페이지 모듈 매핑
PAGES = {
    "Script Page": script_page,
    "Visual Page": visual_page,
    "Memo Page": memo_page,
    "Image Page": image_page,
    "Find Page": find_page,
    "Sub Page": sub_page,
    "Bulk Page": bulk_page,
}

def main():

    st.set_page_config(page_title="ikapp", layout="wide")

    # 메뉴 선택
    st.sidebar.title("📂 Pages")
    page_name = st.sidebar.radio("이동할 페이지 선택", list(PAGES.keys()))

    # 선택된 페이지 렌더링
    selected_page = PAGES[page_name]
    
    # 각 페이지 모듈 안에는 반드시 render() 함수가 있어야 함
    if hasattr(selected_page, "render"):
        selected_page.render()
    else:
        st.error(f"{page_name} 페이지에는 render() 함수가 없습니다!")

if __name__ == "__main__":
    main()
