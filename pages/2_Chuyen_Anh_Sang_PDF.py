import streamlit as st
from PIL import Image
import io

st.set_page_config(page_title="Chuyển Ảnh sang PDF", page_icon="🖼️", layout="wide")

st.title("🖼 Chuyển Đổi Hình Ảnh Thành File PDF")
st.write("Tải lên các file ảnh (PNG, JPG, JPEG) để gộp thành 1 file PDF duy nhất.")

# Cho phép người dùng tải lên nhiều ảnh
uploaded_files = st.file_uploader(
    "Chọn các file ảnh (có thể chọn nhiều file cùng lúc):",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"Đã chọn **{len(uploaded_files)}** ảnh.")
    
    # Sắp xếp ảnh theo tên file
    uploaded_files.sort(key=lambda x: x.name)
    
    output_pdf_name = st.text_input("Tên file PDF xuất ra:", "output.pdf")
    if not output_pdf_name.endswith(".pdf"):
        output_pdf_name += ".pdf"

    if st.button("🚀 Chuyển đổi sang PDF", type="primary"):
        try:
            images = []
            for file in uploaded_files:
                img = Image.open(file).convert("RGB")
                images.append(img)
            
            if images:
                first_image = images[0]
                other_images = images[1:]
                
                # Lưu vào bộ nhớ tạm (BytesIO)
                pdf_bytes = io.BytesIO()
                first_image.save(pdf_bytes, format="PDF", save_all=True, append_images=other_images)
                pdf_data = pdf_bytes.getvalue()
                
                st.success("🎉 Chuyển đổi thành công!")
                
                # Nút tải về file PDF
                st.download_button(
                    label="📥 Tải file PDF về máy",
                    data=pdf_data,
                    file_name=output_pdf_name,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Có lỗi xảy ra: {e}")
