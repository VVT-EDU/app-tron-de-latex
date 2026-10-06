import streamlit as st
import os
import re
import random
import zipfile
import io
from PIL import Image

# --- CẤU HÌNH TRANG STREAMLIT ---
st.set_page_config(page_title="Hệ Thống Công Cụ Giáo Viên Online", page_icon="📝", layout="centered")

# --- 1. CÁC HÀM XỬ LÝ TRỘN ĐỀ LATEX ---
def parse_choices(choice_body):
    items = []
    depth = 0
    current = []
    for char in choice_body:
        if char == '{':
            if depth > 0:
                current.append(char)
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                items.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        else:
            if depth > 0:
                current.append(char)
    return items

def shuffle_ex_content(ex_content):
    # Trộn \choice{...}
    match_choice = re.search(r'\\choice\s*(\{.*\})', ex_content, re.DOTALL)
    if match_choice:
        full_choice_str = match_choice.group(0)
        idx_first_brace = full_choice_str.find('{')
        body_all = full_choice_str[idx_first_brace:]
        choices = parse_choices(body_all)
        if len(choices) == 4:
            random.shuffle(choices)
            new_choice_str = "\\choice\n\t{" + "}\n\t{".join(choices) + "}"
            ex_content = ex_content.replace(full_choice_str, new_choice_str)
            return ex_content

    # Trộn \choiceTF{...}
    match_choicetf = re.search(r'\\choiceTF(\[[^\]]*\])?\s*(\{.*\})', ex_content, re.DOTALL)
    if match_choicetf:
        opt_arg = match_choicetf.group(1) or ""
        full_choice_str = match_choicetf.group(0)
        idx_first_brace = full_choice_str.find('{')
        body_all = full_choice_str[idx_first_brace:]
        choices = parse_choices(body_all)
        if len(choices) == 4:
            random.shuffle(choices)
            new_choice_str = f"\\choiceTF{opt_arg}\n\t{{" + "}\n\t{".join(choices) + "}"
            ex_content = ex_content.replace(full_choice_str, new_choice_str)
            return ex_content

    return ex_content

def process_section_text(section_text):
    ex_pattern = re.compile(r'(\\begin\{ex\}.*?\\end\{ex\})', re.DOTALL)
    parts = ex_pattern.split(section_text)
    non_ex_parts = parts[::2]
    ex_blocks = parts[1::2]
    
    if not ex_blocks:
        return section_text
    
    processed_ex_blocks = [shuffle_ex_content(ex) for ex in ex_blocks]
    random.shuffle(processed_ex_blocks)
    
    result = []
    for i in range(len(processed_ex_blocks)):
        result.append(non_ex_parts[i])
        result.append(processed_ex_blocks[i])
    result.append(non_ex_parts[-1])
    return "".join(result)

def mix_latex_file(content, seed_val):
    random.seed(seed_val)
    section_split_pattern = re.compile(r'(%+\s*PHAN\s+[0-9IVX]+|\\subsubsection\*\{[^}]*PHẦN\s+[0-9IVX]+[^}]*\})', re.IGNORECASE)
    tokens = section_split_pattern.split(content)
    
    new_tokens = []
    for token in tokens:
        if section_split_pattern.match(token):
            new_tokens.append(token)
        else:
            new_tokens.append(process_section_text(token))
            
    return "".join(new_tokens)

# --- 2. GIAO DIỆN TABS STREAMLIT ---
tab1, tab2 = st.tabs(["🚀 Trộn Đề LaTeX", "🖼️ Chuyển Ảnh sang PDF"])

# ================= TAB 1: TRỘN ĐỀ LATEX =================
with tab1:
    st.title("📝 HỆ THỐNG TRỘN ĐỀ LATEX ONLINE")
    st.write("Tải lên các file đề gốc `.tex` để tạo ra các mã đề trộn ngẫu nhiên kèm cấu trúc chuẩn.")

    # Thanh cấu hình Sidebar
    st.sidebar.header("Cấu hình trộn đề")
    num_versions = st.sidebar.number_input("Số lượng mã đề cần tạo:", min_value=1, max_value=8, value=4, step=1)
    start_code = st.sidebar.number_input("Mã đề bắt đầu:", min_value=100, max_value=999, value=101, step=1)

    # Tải file .tex lên
    uploaded_tex_files = st.file_uploader(
        "Chọn một hoặc nhiều file LaTeX (.tex)", 
        type=["tex"], 
        accept_multiple_files=True,
        key="tex_uploader"
    )

    if uploaded_tex_files:
        if st.button("🚀 Bắt đầu Trộn Đề", type="primary"):
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for uploaded_file in uploaded_tex_files:
                    filename = uploaded_file.name
                    base_name = os.path.splitext(filename)[0]
                    content = uploaded_file.read().decode("utf-8")
                    
                    for i in range(num_versions):
                        code = start_code + i
                        mixed_content = mix_latex_file(content, seed_val=code + hash(filename))
                        
                        header_notice = f"% ==========================================\n% MÃ ĐỀ: {code}\n% ==========================================\n\n"
                        final_content = header_notice + mixed_content
                        
                        out_filename = f"{base_name}_MaDe_{code}.tex"
                        zip_file.writestr(out_filename, final_content)

            zip_buffer.seek(0)
            st.success(f"✅ Đã trộn thành công {len(uploaded_tex_files)} file sang {num_versions} mã đề!")
            
            # Nút tải file ZIP
            st.download_button(
                label="📦 Tải về tất cả mã đề (.ZIP)",
                data=zip_buffer,
                file_name="De_Thi_Da_Tron.zip",
                mime="application/zip"
            )

# ================= TAB 2: CHUYỂN ÁNH SANG PDF =================
with tab2:
    st.title("🖼️ CHUYỂN ĐỔI HÌNH ẢNH THÀNH FILE PDF")
    st.write("Tải lên các file ảnh (PNG, JPG, JPEG) để gộp thành 1 file PDF duy nhất.")
    
    uploaded_img_files = st.file_uploader(
        "Chọn các file ảnh:",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="img_uploader"
    )
    
    if uploaded_img_files:
        # Sắp xếp ảnh theo tên file
        uploaded_img_files.sort(key=lambda x: x.name)
        st.info(f"Đã chọn **{len(uploaded_img_files)}** file ảnh.")
        
        if st.button("🚀 Chuyển đổi sang PDF", type="primary"):
            try:
                images = [Image.open(f).convert("RGB") for f in uploaded_img_files]
                if images:
                    pdf_bytes = io.BytesIO()
                    images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=images[1:])
                    
                    st.success("🎉 Chuyển đổi thành công!")
                    st.download_button(
                        label="📥 Tải file PDF về máy",
                        data=pdf_bytes.getvalue(),
                        file_name="output_images.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Có lỗi xảy ra: {e}")
