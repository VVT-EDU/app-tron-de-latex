import streamlit as st
import os
import sys
import re
import random
import zipfile
import io
import shutil
import importlib.util
import tempfile
import traceback
import subprocess
from datetime import datetime
from PIL import Image

# Import sympy an toàn (khai báo trong requirements.txt)
try:
    import sympy
except ImportError:
    sympy = None

# ==============================================================================
# 1. KHỦY TẠO ĐƯỜNG DẪN HỆ THỐNG & TỰ ĐỘNG GIẢI NÉN FILE ZIP CÓ SẴN TRÊN REPO
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

AUTO_UNZIP_FILES = ["topics.zip", "khaibao.zip", "hotro.zip", "tieude.zip"]

for zip_filename in AUTO_UNZIP_FILES:
    zip_path = os.path.join(BASE_DIR, zip_filename)
    folder_name = zip_filename.replace(".zip", "")
    target_dir = os.path.join(BASE_DIR, folder_name)
    
    if os.path.exists(zip_path) and not os.path.exists(target_dir):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zref:
                zref.extractall(BASE_DIR)
        except Exception as e:
            st.error(f"Lỗi khi giải nén {zip_filename}: {e}")

TOPICS_DIR = os.path.join(BASE_DIR, "topics")
if os.path.exists(TOPICS_DIR):
    if TOPICS_DIR not in sys.path:
        sys.path.insert(0, TOPICS_DIR)
    for root, dirs, _ in os.walk(TOPICS_DIR):
        for d in dirs:
            sp = os.path.join(root, d)
            if sp not in sys.path:
                sys.path.insert(0, sp)

# ==============================================================================
# 2. CẤU HÌNH TRANG STREAMLIT
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trộn Đề & Tạo Đề LaTeX Pro", page_icon="📝", layout="wide")

if sympy is None:
    st.warning("⚠️ Thư viện `sympy` chưa được cài đặt trong môi trường. Hãy đảm bảo bạn đã thêm `sympy` vào file `requirements.txt` trên GitHub.")

# ==============================================================================
# 3. CÁC HÀM XỬ LÝ NỘI DUNG LATEX, MODULE PYTHON VÀ BIÊN DỊCH PDF
# ==============================================================================
ex_pattern = re.compile(r'\\begin{ex}.*?\\end{ex}', re.DOTALL)

def extract_from_tex_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    return ex_pattern.findall(content)

def generate_from_py_file(file_path):
    try:
        file_dir = os.path.dirname(file_path)
        if file_dir not in sys.path:
            sys.path.insert(0, file_dir)
            
        rel_path = os.path.relpath(file_path, BASE_DIR)
        module_name = os.path.splitext(rel_path.replace(os.sep, '.'))[0]
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'generate'):
            return str(module.generate())
        else:
            return f"% Lỗi: {os.path.basename(file_path)} thiếu hàm generate()"
    except Exception as e:
        return f"% Lỗi Python tại {os.path.basename(file_path)}:\n% {traceback.format_exc()}"

def add_folder_to_zip(zip_file, folder_name, dest_prefix):
    full_folder_path = os.path.join(BASE_DIR, folder_name)
    if os.path.exists(full_folder_path):
        for root, _, files in os.walk(full_folder_path):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, full_folder_path)
                zip_file.write(full_path, arcname=f"{dest_prefix}/{rel_path}")

def compile_tex_to_pdf(tex_content, work_dir=None):
    """Hàm biên dịch mã LaTeX trực tiếp thành file PDF bytes qua pdflatex"""
    with tempfile.TemporaryDirectory() as tmpdir:
        if work_dir and os.path.exists(work_dir):
            import shutil
            shutil.copytree(work_dir, tmpdir, dirs_exist_ok=True)

        tex_path = os.path.join(tmpdir, "document.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        for _ in range(2):
            cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "document.tex"]
            result = subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        pdf_path = os.path.join(tmpdir, "document.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                return f.read(), None
        else:
            log_path = os.path.join(tmpdir, "document.log")
            log_content = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = f.read()
            return None, log_content if log_content else result.stdout

# ==============================================================================
# 4. GIAO DIỆN CHÍNH (3 TABS)
# ==============================================================================
tab1, tab2, tab3 = st.tabs(["🚀 Trộn Đề LaTeX Direct", "🖼️ Chuyển Ảnh sang PDF", "📝 Tạo Đề Từ Data / Topics"])

# ------------------------------------------------------------------------------
# TAB 1: TRỘN ĐỀ LATEX DIRECT
# ------------------------------------------------------------------------------
with tab1:
    st.title("🚀 TRỘN ĐỀ LATEX DIRECT")
    st.info("Tính năng trộn câu hỏi từ mã LaTeX trực tiếp.")
    tex_input = st.text_area("Dán mã nguồn LaTeX cần trộn câu hỏi vào đây:", height=300, key="t1_input")
    
    col_t1_a, col_t1_b = st.columns([1, 1])
    with col_t1_a:
        num_mix = st.number_input("Số lượng đề hoán vị cần tạo:", min_value=1, max_value=20, value=2, key="t1_num")
    
    if st.button("🚀 Trộn đề ngay", type="primary", key="t1_btn"):
        if tex_input.strip():
            blocks = ex_pattern.findall(tex_input)
            if not blocks:
                st.warning("Không tìm thấy khối câu hỏi \\begin{ex}...\\end{ex} nào trong nội dung dán vào.")
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i in range(1, num_mix + 1):
                        shuffled_blocks = list(blocks)
                        random.shuffle(shuffled_blocks)
                        new_content = ex_pattern.sub(lambda m: shuffled_blocks.pop(0), tex_input)
                        zf.writestr(f"De_Tron_{i}.tex", new_content)
                st.success(f"Đã trộn thành công {num_mix} mã đề từ {len(blocks)} câu hỏi!")
                st.download_button("📦 Tải về đề đã trộn (.ZIP)", zip_buf.getvalue(), "De_Tron_LaTeX.zip", "application/zip")
        else:
            st.error("Vui lòng dán mã LaTeX trước khi trộn!")

# ------------------------------------------------------------------------------
# TAB 2: CHUYỂN ĐỔI ÁNH SANG PDF
# ------------------------------------------------------------------------------
with tab2:
    st.title("🖼️ CHUYỂN ĐỔI BỘ CÂU HỎI DẠNG ÁNH SANG PDF")
    uploaded_imgs = st.file_uploader("Chọn danh sách các file ảnh:", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="t2_uploader")
    
    if uploaded_imgs and st.button("🖼️ Chuyển đổi sang PDF", type="primary", key="t2_btn"):
        try:
            img_list = []
            for img_file in uploaded_imgs:
                image = Image.open(img_file)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                img_list.append(image)
            
            pdf_buf = io.BytesIO()
            img_list[0].save(pdf_buf, format="PDF", save_all=True, append_images=img_list[1:])
            st.success(f"Đã gộp thành công {len(img_list)} ảnh thành file PDF!")
            st.download_button("📄 Tải file PDF", pdf_buf.getvalue(), "Bo_Cau_Hoi_Anh.pdf", "application/pdf")
        except Exception as e:
            st.error(f"Có lỗi khi chuyển đổi ảnh: {e}")

# ------------------------------------------------------------------------------
# TAB 3: HỆ THỐNG TẠO ĐỀ TỰ ĐỘNG
# ------------------------------------------------------------------------------
with tab3:
    st.title("📝 HỆ THỐNG TẠO ĐỀ THI TỰ ĐỘNG")
    st.write("Hệ thống kết nối trực tiếp với thư mục `topics` trên Server hoặc tiếp nhận file ZIP nén bộ bài tập.")

    # --------------------------------------------------------------------------
    # CONTAINER VÙNG XUẤT VÀ TẢI ĐỀ THI ĐƯỢC ĐẶT LÊN ĐẦU TRANG
    # --------------------------------------------------------------------------
    export_top_container = st.container()

    col1, col2 = st.columns([1, 1])
    with col1:
        hk = st.text_input("Học kỳ:", "II", key="t3_hk")
        nam = st.text_input("Năm học:", "2025 - 2026", key="t3_nam")
        mon = st.text_input("Môn học:", "TOÁN 11", key="t3_mon")
        phut = st.text_input("Thời gian (phút):", "90", key="t3_phut")
        so_de = st.number_input("Số lượng đề cần xuất:", min_value=1, max_value=10, value=2, key="t3_sode")

    with col2:
        source_option = st.radio(
            "Nguồn dữ liệu câu hỏi:", 
            ["Dùng thư mục `topics` sẵn có trên Server", "Tải lên file ZIP/File rời mới"],
            key="t3_source_opt"
        )
        
        uploaded_files = None
        if source_option == "Tải lên file ZIP/File rời mới":
            uploaded_files = st.file_uploader("Tải lên file topics.zip hoặc danh sách file .py/.tex", type=["zip", "tex", "py"], accept_multiple_files=True, key="t3_uploader")

    scan_dir = None
    temp_dir = None

    if source_option == "Dùng thư mục `topics` sẵn có trên Server":
        default_topics = os.path.join(BASE_DIR, "topics")
        if os.path.exists(default_topics):
            scan_dir = default_topics
        else:
            st.warning("⚠️ Không tìm thấy thư mục `topics` trên Server Repo!")
    else:
        if uploaded_files:
            temp_dir = tempfile.mkdtemp()
            for u_file in uploaded_files:
                if u_file.name.endswith(".zip"):
                    with zipfile.ZipFile(u_file, 'r') as zref:
                        zref.extractall(temp_dir)
                else:
                    f_path = os.path.join(temp_dir, u_file.name)
                    with open(f_path, "wb") as f:
                        f.write(u_file.getbuffer())
            scan_dir = temp_dir

    if scan_dir:
        if scan_dir not in sys.path:
            sys.path.insert(0, scan_dir)
        for root, dirs, _ in os.walk(scan_dir):
            for d in dirs:
                sp = os.path.join(root, d)
                if sp not in sys.path:
                    sys.path.insert(0, sp)

        # Quét danh sách file bài tập .py và .tex
        q_data_list = []
        for root, _, files in os.walk(scan_dir):
            for f in sorted(files):
                if f.endswith((".py", ".tex")) and not f.startswith("__"):
                    fpath = os.path.join(root, f)
                    dtype = "ATN" if "ATN" in f.upper() else "BTF" if "BTF" in f.upper() else "CDK" if "CDK" in f.upper() else "Khác"
                    ext = f.split('.')[-1].upper()
                    rel_display = os.path.relpath(fpath, scan_dir)
                    
                    q_data_list.append({
                        "display": rel_display,
                        "filename": f,
                        "path": fpath,
                        "type": dtype,
                        "ext": ext
                    })

        # ----------------------------------------------------------------------
        # 1. BẢNG NHẬP CHỈ TIÊU SỐ CÂU CHO TỪNG ĐỀ (ATN, BTF, CDK, Khác)
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.subheader("🎯 1. Cấu hình Chỉ tiêu số câu hỏi cho từng Đề")
        st.info("Nhập số lượng câu hỏi mục tiêu bạn muốn tạo cho từng đề:")
        
        target_counts = {de_idx: {} for de_idx in range(1, so_de + 1)}
        
        cols_de = st.columns(min(so_de, 4))
        for de_idx in range(1, so_de + 1):
            with cols_de[(de_idx - 1) % 4]:
                st.markdown(f"##### 📋 **Cấu hình Đề {de_idx}**")
                n_atn = st.number_input(f"Số câu Trắc nghiệm (ATN):", min_value=0, value=12, key=f"target_atn_d{de_idx}")
                m_btf = st.number_input(f"Số câu Đúng Sai (BTF):", min_value=0, value=4, key=f"target_btf_d{de_idx}")
                k_cdk = st.number_input(f"Số câu Trả lời ngắn (CDK):", min_value=0, value=6, key=f"target_cdk_d{de_idx}")
                h_khac = st.number_input(f"Số câu Khác:", min_value=0, value=0, key=f"target_khac_d{de_idx}")
                
                target_counts[de_idx] = {
                    "ATN": n_atn,
                    "BTF": m_btf,
                    "CDK": k_cdk,
                    "Khác": h_khac
                }

        # ----------------------------------------------------------------------
        # 2. BẢNG CHỌN CÂU HỎI TỪ DANH SÁCH FILE
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.subheader("📌 2. Chọn câu hỏi từ các file bài tập")
        st.caption("Mặc định mỗi câu khi tích chọn sẽ có số lượng là 1.")

        selected_counts = {de_idx: {} for de_idx in range(1, so_de + 1)}
        sub_tabs = st.tabs(["Trắc nghiệm (ATN)", "Đúng Sai (BTF)", "Trả lời ngắn (CDK)", "Khác"])

        for i, dtype in enumerate(["ATN", "BTF", "CDK", "Khác"]):
            with sub_tabs[i]:
                items = [x for x in q_data_list if x['type'] == dtype]
                
                if not items:
                    st.info(f"Không tìm thấy file nào thuộc loại {dtype}")
                else:
                    search_kw = st.text_input(f"🔍 Tìm kiếm file trong tab {dtype}:", "", key=f"search_{dtype}")
                    filtered_items = [x for x in items if search_kw.lower() in x['display'].lower()]
                    st.caption(f"Hiển thị {len(filtered_items)}/{len(items)} file")

                    for item in filtered_items:
                        if item["ext"] == "PY":
                            max_c = 50
                            label_type = "🐍 Script Python"
                        else:
                            blks = extract_from_tex_file(item['path'])
                            max_c = max(1, len(blks))
                            label_type = f"📄 TeX tĩnh ({len(blks)} câu)"

                        with st.expander(f"📌 **{item['display']}** *({label_type})*"):
                            use_this = st.checkbox(f"Sử dụng file này cho các đề", value=False, key=f"use_{item['path']}")
                            
                            if use_this:
                                cols = st.columns(min(so_de, 4))
                                for de_idx in range(1, so_de + 1):
                                    col_target = cols[(de_idx - 1) % 4]
                                    with col_target:
                                        cnt = st.number_input(
                                            f"Đề {de_idx}:", 
                                            min_value=0, 
                                            max_value=max_c, 
                                            value=1,
                                            key=f"spin_d{de_idx}_{item['path']}"
                                        )
                                        selected_counts[de_idx][item['path']] = cnt

        # Đọc tiêu đề các phần câu hỏi
        td_defaults = {1: "", 2: "", 3: "", 4: ""}
        for j in range(1, 5):
            for path_check in [os.path.join(BASE_DIR, "tieude", f"title_{j}.tex"), os.path.join(BASE_DIR, "tieudechinh", f"title_{j}.tex")]:
                if os.path.exists(path_check):
                    with open(path_check, "r", encoding="utf-8", errors="ignore") as f:
                        raw_td = f.read().strip()
                        raw_td = raw_td.replace(r"\Closesolutionfile{ans}", "")
                        td_defaults[j] = raw_td.strip()
                    break

        st.markdown("---")

        # ----------------------------------------------------------------------
        # HÀM XUẤT PROJECT ĐỀ THI (HIỂN THỊ LÊN VÙNG TOP CONTAINER)
        # ----------------------------------------------------------------------
        def run_export():
            now = datetime.now()
            time_str = now.strftime("%d-%m-%Y_%Hh%Mm%Ss")
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for de_idx in range(1, so_de + 1):
                    folder_de = f"De_0{de_idx}_{time_str}"
                    ma_de = f"{de_idx}{random.randint(11, 99)}"
                    final_content = ""
                    counts = {"ATN": 0, "BTF": 0, "CDK": 0}

                    # Tạo thư mục 'ans/' cùng cấp với 'khaibao'
                    zip_file.writestr(f"{folder_de}/ans/atn_D{de_idx}.tex", "% File dap an ATN\n")
                    zip_file.writestr(f"{folder_de}/ans/btf_D{de_idx}.tex", "% File dap an BTF\n")
                    zip_file.writestr(f"{folder_de}/ans/cdk_D{de_idx}.tex", "% File dap an CDK\n")

                    for dtype in ["ATN", "BTF", "CDK", "Khác"]:
                        sec_txt = ""
                        items = [x for x in q_data_list if x['type'] == dtype]

                        for item in items:
                            n = selected_counts[de_idx].get(item['path'], 0)
                            if n <= 0:
                                continue

                            if item["ext"] == "PY":
                                for _ in range(n):
                                    val = generate_from_py_file(item['path'])
                                    if val:
                                        sec_txt += val + "\n"
                                if dtype in counts:
                                    counts[dtype] += n
                            else:
                                blks = extract_from_tex_file(item['path'])
                                if blks:
                                    chosen = random.sample(blks, min(n, len(blks)))
                                    sec_txt += "\n".join(chosen) + "\n"
                                    if dtype in counts:
                                        counts[dtype] += len(chosen)

                        if sec_txt:
                            idx_type = {"ATN": 1, "BTF": 2, "CDK": 3, "Khác": 4}[dtype]
                            header_title = td_defaults[idx_type]
                            if dtype in ["ATN", "BTF", "CDK"]:
                                if header_title:
                                    header_title = re.sub(r"\[ans/.*?\]", f"[ans/{dtype.lower()}_D{de_idx}]", header_title)
                                else:
                                    header_title = f"\\Opensolutionfile{{ans}}[ans/{dtype.lower()}_D{de_idx}]"
                                final_content += f"\n{header_title}\n{sec_txt}\n\\Closesolutionfile{{ans}}\n"
                            else:
                                final_content += f"\n{header_title}\n{sec_txt}\n"

                    # Ghi nội dung đề thi vào data/content.tex
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

                    # File Main_DA.tex (Đáp án)
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

                    # Đóng gói thư mục khaibao và hotro vào từng mã đề
                    add_folder_to_zip(zip_file, "khaibao", f"{folder_de}/khaibao")
                    add_folder_to_zip(zip_file, "hotro", f"{folder_de}")

            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

            # XUẤT KẾT QUẢ LÊN ĐẦU TRANG
            with export_top_container:
                st.success("🎉 Đã khởi tạo thành công Project Đề thi!")
                st.download_button("📦 Tải về bộ Project Đề Thi (.ZIP)", zip_buffer.getvalue(), f"Project_DeThi_{time_str}.zip", "application/zip")
                st.divider()

        # ----------------------------------------------------------------------
        # NÚT XUẤT ĐỀ VÀ KIỂM TRA CHỈ TIÊU SỐ CÂU
        # ----------------------------------------------------------------------
        if st.button("🚀 BẮT ĐẦU XUẤT PROJECT ĐỀ THI (.ZIP)", type="primary", key="btn_export_project"):
            errors = []
            warnings = []

            for de_idx in range(1, so_de + 1):
                actual = {"ATN": 0, "BTF": 0, "CDK": 0, "Khác": 0}
                for item in q_data_list:
                    c = selected_counts[de_idx].get(item['path'], 0)
                    actual[item['type']] += c

                for dtype in ["ATN", "BTF", "CDK", "Khác"]:
                    target = target_counts[de_idx][dtype]
                    act = actual[dtype]
                    
                    if act < target:
                        errors.append(f"❌ **Đề {de_idx} - Loại {dtype}:** Chỉ tiêu **{target}** câu nhưng bạn chỉ mới chọn **{act}** câu (Thiếu **{target - act}** câu).")
                    elif act > target:
                        warnings.append(f"⚠️ **Đề {de_idx} - Loại {dtype}:** Chỉ tiêu **{target}** câu nhưng bạn đã chọn **{act}** câu (Dư **{act - target}** câu).")

            if errors or warnings:
                with export_top_container:
                    st.subheader("⚠️ CẢNH BÁO SỐ LƯỢNG CÂU HỎI")
                    for err in errors:
                        st.error(err)
                    for warn in warnings:
                        st.warning(warn)

                    st.info("💡 Bạn có thể quay lại điều chỉnh chỉ tiêu hoặc chọn thêm/bớt câu hỏi bên dưới, hoặc bấm nút dưới đây để bỏ qua cảnh báo và tạo đề ngay.")
                    
                    if st.button("⚠️ Bỏ qua cảnh báo & Vẫn tiếp tục xuất đề", key="btn_force_export"):
                        run_export()
                    st.divider()
            else:
                run_export()
