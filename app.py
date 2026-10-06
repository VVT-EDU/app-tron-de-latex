import streamlit as st
import os, re, random, zipfile, io
from PIL import Image
from datetime import datetime

# --- CẤU HÌNH TRANG STREAMLIT ---
st.set_page_config(page_title="Hệ Thống Công Cụ Giáo Viên Online", page_icon="📝", layout="wide")

# --- HÀM 1: TRỘN ĐỀ LATEX ---
def parse_choices(choice_body):
    items, depth, current = [], 0, []
    for char in choice_body:
        if char == '{':
            if depth > 0: current.append(char)
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                items.append(''.join(current).strip())
                current = []
            else: current.append(char)
        else:
            if depth > 0: current.append(char)
    return items

def shuffle_ex_content(ex_content):
    match_choice = re.search(r'\\choice\s*(\{.*\})', ex_content, re.DOTALL)
    if match_choice:
        full_choice_str = match_choice.group(0)
        idx_first_brace = full_choice_str.find('{')
        choices = parse_choices(full_choice_str[idx_first_brace:])
        if len(choices) == 4:
            random.shuffle(choices)
            return ex_content.replace(full_choice_str, "\\choice\n\t{" + "}\n\t{".join(choices) + "}")

    match_choicetf = re.search(r'\\choiceTF(\[[^\]]*\])?\s*(\{.*\})', ex_content, re.DOTALL)
    if match_choicetf:
        opt_arg = match_choicetf.group(1) or ""
        full_choice_str = match_choicetf.group(0)
        idx_first_brace = full_choice_str.find('{')
        choices = parse_choices(full_choice_str[idx_first_brace:])
        if len(choices) == 4:
            random.shuffle(choices)
            return ex_content.replace(full_choice_str, f"\\choiceTF{opt_arg}\n\t{{" + "}\n\t{".join(choices) + "}")
    return ex_content

def process_section_text(section_text):
    ex_pattern = re.compile(r'(\\begin\{ex\}.*?\\end\{ex\})', re.DOTALL)
    parts = ex_pattern.split(section_text)
    non_ex_parts, ex_blocks = parts[::2], parts[1::2]
    if not ex_blocks: return section_text
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
        if section_split_pattern.match(token): new_tokens.append(token)
        else: new_tokens.append(process_section_text(token))
    return "".join(new_tokens)

# --- HÀM 2: TRÍCH XUẤT CÂU HỎI TỪ DATA ---
ex_pattern = re.compile(r'\\begin{ex}.*?\\end{ex}', re.DOTALL)
def extract_from_tex_content(content):
    return ex_pattern.findall(content)

# ================= GIAO DIỆN 3 TABS =================
tab1, tab2, tab3 = st.tabs(["🚀 Trộn Đề LaTeX", "🖼️ Chuyển Ảnh sang PDF", "📝 Tạo Đề Từ Data"])

# --- TAB 1: TRỘN ĐỀ ---
with tab1:
    st.title("📝 HỆ THỐNG TRỘN ĐỀ LATEX ONLINE")
    st.write("Tải lên các file đề gốc `.tex` để tạo ra các mã đề trộn ngẫu nhiên kèm cấu trúc chuẩn.")
    
    num_versions = st.sidebar.number_input("Số lượng mã đề cần tạo:", min_value=1, max_value=8, value=4, step=1)
    start_code = st.sidebar.number_input("Mã đề bắt đầu:", min_value=100, max_value=999, value=101, step=1)

    uploaded_tex_files = st.file_uploader("Chọn một hoặc nhiều file LaTeX (.tex)", type=["tex"], accept_multiple_files=True, key="tex_uploader")
    if uploaded_tex_files and st.button("🚀 Bắt đầu Trộn Đề", type="primary"):
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
                    zip_file.writestr(f"{base_name}_MaDe_{code}.tex", header_notice + mixed_content)
        zip_buffer.seek(0)
        st.success(f"✅ Đã trộn thành công {len(uploaded_tex_files)} file sang {num_versions} mã đề!")
        st.download_button(label="📦 Tải về tất cả mã đề (.ZIP)", data=zip_buffer, file_name="De_Thi_Da_Tron.zip", mime="application/zip")

# --- TAB 2: CHUYỂN ÁNH SANG PDF ---
with tab2:
    st.title("🖼️ CHUYỂN ĐỔI HÌNH ẢNH THÀNH FILE PDF")
    st.write("Tải lên các file ảnh (PNG, JPG, JPEG) để gộp thành 1 file PDF duy nhất.")
    uploaded_img_files = st.file_uploader("Chọn các file ảnh:", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="img_uploader")
    if uploaded_img_files:
        uploaded_img_files.sort(key=lambda x: x.name)
        st.info(f"Đã chọn **{len(uploaded_img_files)}** file ảnh.")
        if st.button("🚀 Chuyển đổi sang PDF", type="primary"):
            try:
                images = [Image.open(f).convert("RGB") for f in uploaded_img_files]
                if images:
                    pdf_bytes = io.BytesIO()
                    images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=images[1:])
                    st.success("🎉 Chuyển đổi thành công!")
                    st.download_button(label="📥 Tải file PDF về máy", data=pdf_bytes.getvalue(), file_name="output_images.pdf", mime="application/pdf")
            except Exception as e: st.error(f"Có lỗi xảy ra: {e}")

# --- TAB 3: TẠO ĐỀ TỪ DATA ---
with tab3:
    st.title("📝 HỆ THỐNG TẠO ĐỀ THI LATEX TỰ ĐỘNG TỪ DATA")
    
    col1, col2 = st.columns(2)
    with col1:
        hk = st.text_input("Học kỳ:", "II", key="t3_hk")
        nam = st.text_input("Năm học:", "2025 - 2026", key="t3_nam")
        mon = st.text_input("Môn học:", "TOÁN 11", key="t3_mon")
        phut = st.text_input("Thời gian (phút):", "90", key="t3_phut")
        so_de = st.number_input("Số lượng đề cần tạo:", min_value=1, max_value=10, value=2, key="t3_sode")
    with col2:
        uploaded_q_files = st.file_uploader("Chọn các file câu hỏi .tex:", type=["tex"], accept_multiple_files=True, key="t3_qfiles")

    if uploaded_q_files:
        st.success(f"Đã tải lên **{len(uploaded_q_files)}** file câu hỏi.")
        q_dict = {"ATN": [], "BTF": [], "CDK": [], "Khác": []}
        for f in uploaded_q_files:
            fname = f.name.upper()
            dtype = "ATN" if "ATN" in fname else "BTF" if "BTF" in fname else "CDK" if "CDK" in fname else "Khác"
            content = f.read().decode("utf-8", errors="ignore")
            blocks = extract_from_tex_content(content)
            q_dict[dtype].append({"name": f.name, "blocks": blocks})

        selected_counts = {}
        sub_tabs = st.tabs(["Trắc nghiệm (ATN)", "Đúng Sai (BTF)", "Trả lời ngắn (CDK)", "Khác"])
        for i, dtype in enumerate(["ATN", "BTF", "CDK", "Khác"]):
            with sub_tabs[i]:
                if not q_dict[dtype]: st.info(f"Không có file nào thuộc nhóm {dtype}")
                for item in q_dict[dtype]:
                    num_blocks = len(item["blocks"])
                    st.write(f"📄 **{item['name']}** (Có {num_blocks} câu hỏi)")
                    count = st.number_input(f"Số câu cần lấy từ {item['name']}:", min_value=0, max_value=num_blocks, value=min(5, num_blocks), key=f"t3_{item['name']}")
                    selected_counts[item['name']] = count

        if st.button("🚀 XUẤT PROJECT TẤT CẢ MÃ ĐỀ (.ZIP)", type="primary", key="t3_btn_export"):
            now = datetime.now()
            time_str = now.strftime("%d-%m-%Y_%Hh%Mm%Ss")
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for de_idx in range(1, so_de + 1):
                    folder_de = f"De_0{de_idx}_{time_str}"
                    ma_de = f"{de_idx}{random.randint(11, 99)}"
                    final_content = ""
                    counts = {"ATN": 0, "BTF": 0, "CDK": 0}
                    for dtype in ["ATN", "BTF", "CDK", "Khác"]:
                        sec_txt = ""
                        for item in q_dict[dtype]:
                            n = selected_counts.get(item['name'], 0)
                            if n > 0 and item['blocks']:
                                selected_blocks = random.sample(item['blocks'], min(n, len(item['blocks'])))
                                sec_txt += "\n".join(selected_blocks) + "\n"
                                if dtype in counts: counts[dtype] += len(selected_blocks)
                        if sec_txt:
                            final_content += f"\n% --- PHẦN {dtype} ---\n\\Opensolutionfile{{ans}}[ans/{dtype.lower()}_D{de_idx}]\n{sec_txt}\\Closesolutionfile{{ans}}\n"
                    
                    zip_file.writestr(f"{folder_de}/data/content.tex", final_content)
                    main_tex = f"\\documentclass[11pt,a4paper]{{extbook}}\n\\input{{khaibao/khaibao-main}}\n\\input{{khaibao/Khaibao_Standard}}\n\\input{{khaibao/trang}}\n\\usepackage{{lastpage}}\n\\begin{{document}}\n\\hideansEX{{ex}}\n\\tieudehk{{{hk}}}{{{nam}}}{{{mon}}}{{{phut}}}\n\\centerline{{\\boxed{{\\textbf{{ Mã đề: {ma_de}}}}}}}\n\\input{{data/content}}\n\\vfill\n\\input{{khaibao/thongtin-thisinh}}\n\\end{{document}}"
                    zip_file.writestr(f"{folder_de}/Main_De{de_idx}_{time_str}.tex", main_tex)
                    da_tex = f"\\documentclass[11pt,a4paper]{{extbook}}\n\\input{{khaibao/khaibao-main}}\n\\input{{khaibao/Khaibao_Standard}}\n\\input{{khaibao/trang}}\n\\usepackage{{lastpage}}\n\\begin{{document}}\n\\tieudedapanhk{{{hk}}}{{{nam}}}{{{mon}}}{{{phut}}}\n\\centerline{{\\boxed{{\\textbf{{ Mã đề: {ma_de}}}}}}}\n\\subsubsection*{{I. Trắc nghiệm}} \\inputansbox[2]{{{counts['ATN']}}}{{ans/atn_D{de_idx}}}\n\\subsubsection*{{II. Đúng Sai}} \\inputansbox[2]{{{counts['BTF']}}}{{ans/btf_D{de_idx}}}\n\\subsubsection*{{III. Trả lời ngắn}} \\inputansbox[1]{{{counts['CDK']}}}{{ans/cdk_D{de_idx}}}\n\\vspace{{0.5cm}}\\input{{khaibao/dau-bang-da}}\\input{{khaibao/da_de}}\\input{{khaibao/cuoi-bang-da}}\n\\end{{document}}"
                    zip_file.writestr(f"{folder_de}/Main_DA_De{de_idx}_{time_str}.tex", da_tex)

            st.success("🎉 Tạo bộ đề thành công!")
            st.download_button(label="📦 Tải về tất cả mã đề (.ZIP)", data=zip_buffer.getvalue(), file_name=f"Project_DeThi_{time_str}.zip", mime="application/zip", key="t3_btn_download")
