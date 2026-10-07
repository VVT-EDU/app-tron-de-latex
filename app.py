import streamlit as st
import os, sys, re, random, zipfile, io, shutil, importlib.util, tempfile, traceback
from datetime import datetime
from PIL import Image

# ------------------------------------------------------------------------------
# KHỞI TẠO ĐƯỜNG DẪN HỆ THỐNG (ĐẢM BẢO IMPORT MODULE NỘI BỘ KHÔNG LỖI)
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Hệ Thống Tạo Đề LaTeX Pro", page_icon="📝", layout="wide")

# ==============================================================================
# --- CÁC HÀM XỬ LÝ NỘI DUNG LATEX & PYTHON ---
# ==============================================================================
ex_pattern = re.compile(r'\\begin{ex}.*?\\end{ex}', re.DOTALL)

def extract_from_tex_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
    except:
        with open(file_path, 'r', encoding='latin-1') as f: content = f.read()
    return ex_pattern.findall(content)

def generate_from_py_file(file_path):
    """Import động module Python và gọi hàm generate()"""
    try:
        # Thêm thư mục chứa file vào sys.path để hỗ trợ import chéo
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
    """Copy thư mục cấu trúc (khaibao, hotro) vào file ZIP xuất ra"""
    full_folder_path = os.path.join(BASE_DIR, folder_name)
    if os.path.exists(full_folder_path):
        for root, _, files in os.walk(full_folder_path):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, full_folder_path)
                zip_file.write(full_path, arcname=f"{dest_prefix}/{rel_path}")

# ==============================================================================
# --- GIAO DIỆN CHÍNH ---
# ==============================================================================
tab1, tab2, tab3 = st.tabs(["🚀 Trộn Đề LaTeX Direct", "🖼️ Chuyển Ảnh sang PDF", "📝 Tạo Đề Từ Data / Topics"])

# ------------------------------------------------------------------------------
# TAB 3: HỆ THỐNG TẠO ĐỀ TỪ NGUỒN CẤU TRÚC PHỨC TẠP
# ------------------------------------------------------------------------------
with tab3:
    st.title("📝 HỆ THỐNG TẠO ĐỀ THI TỰ ĐỘNG")
    st.write("Hệ thống tự động kết nối thư mục `topics` trên Server hoặc tiếp nhận file ZIP thư mục bài tập tải lên.")

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

    # Xác định thư mục dữ liệu cần quét
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
        # Thêm tất cả thư mục con vào sys.path
        if scan_dir not in sys.path:
            sys.path.insert(0, scan_dir)
        for root, dirs, _ in os.walk(scan_dir):
            for d in dirs:
                sp = os.path.join(root, d)
                if sp not in sys.path:
                    sys.path.insert(0, sp)

        # Quét danh sách bài tập
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

        st.subheader("📌 Chọn số lượng câu hỏi sinh ra cho từng đề")
        selected_counts = {}
        sub_tabs = st.tabs(["Trắc nghiệm (ATN)", "Đúng Sai (BTF)", "Trả lời ngắn (CDK)", "Khác"])

        for i, dtype in enumerate(["ATN", "BTF", "CDK", "Khác"]):
            with sub_tabs[i]:
                items = [x for x in q_data_list if x['type'] == dtype]
                if not items:
                    st.info(f"Không có file nào thuộc loại {dtype}")
                for item in items:
                    if item["ext"] == "PY":
                        st.write(f"🐍 **{item['display']}** *(Script sinh ngẫu nhiên)*")
                        cnt = st.number_input(f"Số lượng câu sinh từ {item['display']}:", min_value=0, max_value=50, value=1, key=f"spin_{item['path']}")
                    else:
                        blks = extract_from_tex_file(item['path'])
                        st.write(f"📄 **{item['display']}** *(File tĩnh - Có {len(blks)} câu)*")
                        cnt = st.number_input(f"Số lượng câu lấy từ {item['display']}:", min_value=0, max_value=max(1, len(blks)), value=min(2, len(blks)), key=f"spin_{item['path']}")
                    selected_counts[item['path']] = cnt

        # Đọc tiêu đề phần
        td_defaults = {1: "", 2: "", 3: "", 4: ""}
        for j in range(1, 5):
            for path_check in [os.path.join(BASE_DIR, "tieude", f"title_{j}.tex"), os.path.join(BASE_DIR, "tieudechinh", f"title_{j}.tex")]:
                if os.path.exists(path_check):
                    with open(path_check, "r", encoding="utf-8", errors="ignore") as f:
                        td_defaults[j] = f.read().strip()
                    break

        if st.button("🚀 BẮT ĐẦU XUẤT PROJECT ĐỀ THI (.ZIP)", type="primary", key="btn_export_project"):
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
                        items = [x for x in q_data_list if x['type'] == dtype]

                        for item in items:
                            n = selected_counts.get(item['path'], 0)
                            if n <= 0: continue

                            if item["ext"] == "PY":
                                for _ in range(n):
                                    val = generate_from_py_file(item['path'])
                                    if val: sec_txt += val + "\n"
                                if dtype in counts: counts[dtype] += n
                            else:
                                blks = extract_from_tex_file(item['path'])
                                if blks:
                                    chosen = random.sample(blks, min(n, len(blks)))
                                    sec_txt += "\n".join(chosen) + "\n"
                                    if dtype in counts: counts[dtype] += len(chosen)

                        if sec_txt:
                            idx_type = {"ATN": 1, "BTF": 2, "CDK": 3, "Khác": 4}[dtype]
                            header_title = td_defaults[idx_type]
                            if dtype in ["ATN", "BTF", "CDK"]:
                                if header_title:
                                    header_title = re.sub(r"\[ans/.*?\]", f"[ans/{dtype.lower()}_D{de_idx}]", header_title)
                                else:
                                    header_title = f"\\Opensolutionfile{{ans}}[ans/{dtype.lower()}_D{de_idx}]"
                                final_content += f"\n{header_title}\n{sec_txt}\\Closesolutionfile{{ans}}\n"
                            else:
                                final_content += f"\n{header_title}\n{sec_txt}\n"

                    # Ghi các file xuất
                    zip_file.writestr(f"{folder_de}/data/content.tex", final_content)

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

                    # Đóng gói khai bao va hotro
                    add_folder_to_zip(zip_file, "khaibao", f"{folder_de}/khaibao")
                    add_folder_to_zip(zip_file, "hotro", f"{folder_de}")

            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

            st.success("🎉 Đã xuất thành công bộ Project đề thi!")
            st.download_button("📦 Tải về bộ Project (.ZIP)", zip_buffer.getvalue(), f"Project_DeThi_{time_str}.zip", "application/zip")
