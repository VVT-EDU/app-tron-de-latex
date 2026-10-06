import streamlit as st
import os, re, random, io, zipfile
from datetime import datetime

st.set_page_config(page_title="Tạo Đề Thi LaTeX từ Data", page_icon="📝", layout="wide")

st.title("📝 Hệ Thống Tạo Đề Thi LaTeX Tự Động")

# --- HÀM TRÍCH XUẤT CÂU HỎI ---
ex_pattern = re.compile(r'\\begin{ex}.*?\\end{ex}', re.DOTALL)

def extract_from_tex_content(content):
    return ex_pattern.findall(content)

# --- GIAO DIỆN CẤU HÌNH ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Cấu hình thông tin đề thi")
    hk = st.text_input("Học kỳ:", "II")
    nam = st.text_input("Năm học:", "2025 - 2026")
    mon = st.text_input("Môn học:", "TOÁN 11")
    phut = st.text_input("Thời gian (phút):", "90")
    so_de = st.number_input("Số lượng đề cần tạo:", min_value=1, max_value=10, value=2)

with col2:
    st.subheader("2. Tải lên danh sách file câu hỏi (.tex)")
    uploaded_q_files = st.file_uploader(
        "Chọn các file câu hỏi .tex:",
        type=["tex"],
        accept_multiple_files=True
    )

if uploaded_q_files:
    st.success(f"Đã tải lên **{len(uploaded_q_files)}** file câu hỏi.")
    
    # Phân loại câu hỏi theo tên file (ATN, BTF, CDK, Khác)
    q_dict = {"ATN": [], "BTF": [], "CDK": [], "Khác": []}
    for f in uploaded_q_files:
        fname = f.name.upper()
        dtype = "ATN" if "ATN" in fname else "BTF" if "BTF" in fname else "CDK" if "CDK" in fname else "Khác"
        
        content = f.read().decode("utf-8", errors="ignore")
        blocks = extract_from_tex_content(content)
        q_dict[dtype].append({"name": f.name, "blocks": blocks})

    st.subheader("3. Chọn số lượng câu hỏi cho mỗi đề")
    
    selected_counts = {}
    tabs = st.tabs(["Trắc nghiệm (ATN)", "Đúng Sai (BTF)", "Trả lời ngắn (CDK)", "Khác"])
    
    for i, dtype in enumerate(["ATN", "BTF", "CDK", "Khác"]):
        with tabs[i]:
            if not q_dict[dtype]:
                st.info(f"Không có file nào thuộc nhóm {dtype}")
            for item in q_dict[dtype]:
                num_blocks = len(item["blocks"])
                st.write(f"📄 **{item['name']}** (Có {num_blocks} câu hỏi)")
                count = st.number_input(
                    f"Số câu cần lấy từ {item['name']}:",
                    min_value=0,
                    max_value=num_blocks,
                    value=min(5, num_blocks),
                    key=item['name']
                )
                selected_counts[item['name']] = count

    # --- NÚT XUẤT ĐỀ THI ---
    if st.button("🚀 XUẤT PROJECT TẤT CẢ MÃ ĐỀ (.ZIP)", type="primary"):
        now = datetime.now()
        time_str = now.strftime("%d-%m-%Y_%Hh%Mm%Ss")
        
        # Tạo file ZIP trong RAM
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for de_idx in range(1, so_de + 1):
                folder_de = f"De_0{de_idx}_{time_str}"
                ma_de = f"{de_idx}{random.randint(11, 99)}"
                
                # Trích xuất ngẫu nhiên câu hỏi
                final_content = ""
                counts = {"ATN": 0, "BTF": 0, "CDK": 0}
                
                for dtype in ["ATN", "BTF", "CDK", "Khác"]:
                    sec_txt = ""
                    for item in q_dict[dtype]:
                        n = selected_counts.get(item['name'], 0)
                        if n > 0 and item['blocks']:
                            selected_blocks = random.sample(item['blocks'], min(n, len(item['blocks'])))
                            sec_txt += "\n".join(selected_blocks) + "\n"
                            if dtype in counts:
                                counts[dtype] += len(selected_blocks)
                    
                    if sec_txt:
                        final_content += f"\n% --- PHẦN {dtype} ---\n\\Opensolutionfile{{ans}}[ans/{dtype.lower()}_D{de_idx}]\n{sec_txt}\\Closesolutionfile{{ans}}\n"
                
                # File content.tex
                zip_file.writestr(f"{folder_de}/data/content.tex", final_content)
                
                # File Main_De.tex
                main_tex = f"""\\documentclass[11pt,a4paper]{{extbook}}
\\input{{khaibao/khaibao-main}}
\\input{{khaibao/Khaibao_Standard}}
\\input{{khaibao/trang}}
\\usepackage{{lastpage}}
\\begin{{document}}
\\hideansEX{{ex}}
\\tieudehk{{{hk}}}{{{nam}}}{{{mon}}}{{{phut}}}
\\centerline{{\\boxed{{\\textbf{{ Mã đề: {ma_de}}}}}}}
\\input{{data/content}}
\\vfill
\\input{{khaibao/thongtin-thisinh}}
\\end{{document}}"""
                zip_file.writestr(f"{folder_de}/Main_De{de_idx}_{time_str}.tex", main_tex)

                # File Main_DA.tex
                da_tex = f"""\\documentclass[11pt,a4paper]{{extbook}}
\\input{{khaibao/khaibao-main}}
\\input{{khaibao/Khaibao_Standard}}
\\input{{khaibao/trang}}
\\usepackage{{lastpage}}
\\begin{{document}}
\\tieudedapanhk{{{hk}}}{{{nam}}}{{{mon}}}{{{phut}}}
\\centerline{{\\boxed{{\\textbf{{ Mã đề: {ma_de}}}}}}}
\\subsubsection*{{I. Trắc nghiệm}} \\inputansbox[2]{{{counts['ATN']}}}{{ans/atn_D{de_idx}}}
\\subsubsection*{{II. Đúng Sai}} \\inputansbox[2]{{{counts['BTF']}}}{{ans/btf_D{de_idx}}}
\\subsubsection*{{III. Trả lời ngắn}} \\inputansbox[1]{{{counts['CDK']}}}{{ans/cdk_D{de_idx}}}
\\vspace{{0.5cm}}\\input{{khaibao/dau-bang-da}}\\input{{khaibao/da_de}}\\input{{khaibao/cuoi-bang-da}}
\\end{{document}}"""
                zip_file.writestr(f"{folder_de}/Main_DA_De{de_idx}_{time_str}.tex", da_tex)

        st.success("🎉 Tạo bộ đề thành công!")
        
        # Nút Tải ZIP
        st.download_button(
            label="📦 Tải về tất cả mã đề (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"Project_DeThi_{time_str}.zip",
            mime="application/zip"
        )
