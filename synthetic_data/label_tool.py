import streamlit as st
import pandas as pd
import os

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Smishing Labeling Tool", layout="wide")
st.title("🛡️ SMS Smishing Data Labeling Tool (Có Auto-save)")

# Tên file backup tự động
AUTOSAVE_FILE = "autosave_labeled_smishing.csv"

# Định nghĩa Categories và Levels
CATEGORIES = [
    "Giả mạo ngân hàng", "Đòi nợ / Đe dọa", "BHXH / Trợ cấp",
    "Tuyển dụng giả", "Cờ bạc / Betting", "Dịch vụ công giả",
    "Nội dung nhạy cảm", "Crypto / Đầu tư giả"
]

LEVELS = [
    "LEVEL 0 – Không obfuscation (formal)", "LEVEL 1 – Leet nhẹ (thay 1-2 ký tự)",
    "LEVEL 2 – Leet nặng + tên riêng", "LEVEL 3 – Dot/dash insertion",
    "LEVEL 4 – Mixed special chars", "LEVEL 5 – Extreme noise"
]

# Khởi tạo trạng thái phiên
if 'df' not in st.session_state:
    st.session_state.df = None
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0

# Tải file CSV
st.sidebar.header("1. Tải lên dữ liệu")
st.sidebar.markdown(f"*Mẹo: Bạn có thể tải lên file ban đầu hoặc file `{AUTOSAVE_FILE}` để làm tiếp.*")
uploaded_file = st.sidebar.file_uploader("Upload file CSV", type=['csv'])

if uploaded_file is not None and st.session_state.df is None:
    df = pd.read_csv(uploaded_file)
    if 'category' not in df.columns: df['category'] = None
    if 'level' not in df.columns: df['level'] = None
    
    st.session_state.df = df
    
    # Tự động nhảy tới dòng chưa được gán nhãn đầu tiên (để làm tiếp tục)
    unlabeled_indices = df[df['category'].isna() | df['level'].isna()].index
    if len(unlabeled_indices) > 0:
        st.session_state.current_idx = int(unlabeled_indices[0])
    else:
        st.session_state.current_idx = 0 # Đã làm xong hết
        
    st.rerun()

# Giao diện chính
if st.session_state.df is not None:
    df = st.session_state.df
    idx = st.session_state.current_idx
    total = len(df)
    labeled_count = df['category'].notna().sum()

    st.progress(labeled_count / total if total > 0 else 0)
    st.markdown(f"**Tiến độ gán nhãn:** {labeled_count} / {total} tin nhắn")
    
    if idx >= total:
        st.success("🎉 Bạn đã gán nhãn xong toàn bộ dữ liệu!")
    else:
        row = df.iloc[idx]
        
        st.markdown("---")
        st.subheader(f"Mẫu số {idx + 1}")
        st.info(f"💬 **Nội dung:**\n\n{row['content']}")
        
        col_md1, col_md2, col_md3, col_md4 = st.columns(4)
        col_md1.metric("Label", row['label'])
        col_md2.metric("Sender Type", row['sender_type'])
        col_md3.metric("Has URL", row['has_url'])
        col_md4.metric("Has Phone", row['has_phone_number'])

        st.markdown("---")
        
        col_cat, col_lev = st.columns(2)
        cat_idx = CATEGORIES.index(row['category']) if pd.notna(row['category']) and row['category'] in CATEGORIES else 0
        lev_idx = LEVELS.index(row['level']) if pd.notna(row['level']) and row['level'] in LEVELS else 0

        with col_cat:
            st.write("### Phân loại Category")
            selected_cat = st.radio("Chọn Category:", CATEGORIES, index=cat_idx)
            
        with col_lev:
            st.write("### Phân loại Cấp độ Obfuscation")
            selected_lev = st.radio("Chọn Level:", LEVELS, index=lev_idx)

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([1, 8])
        with col_btn1:
            if st.button("⬅️ Quay lại") and idx > 0:
                st.session_state.current_idx -= 1
                st.rerun()
                
        with col_btn2:
            if st.button("Lưu & Chuyển tiếp ➡️", type="primary"):
                # Cập nhật DataFrame
                st.session_state.df.at[idx, 'category'] = selected_cat
                st.session_state.df.at[idx, 'level'] = selected_lev
                
                # AUTO-SAVE: Tự động ghi đè ra file lưu nháp ngay lập tức
                st.session_state.df.to_csv(AUTOSAVE_FILE, index=False)
                
                # Chuyển tới câu tiếp theo
                st.session_state.current_idx += 1
                st.rerun()

    # Sidebar Export
    st.sidebar.markdown("---")
    st.sidebar.header("2. Xuất dữ liệu")
    if os.path.exists(AUTOSAVE_FILE):
        st.sidebar.success(f"✅ Hệ thống đang tự động lưu tại: `{AUTOSAVE_FILE}` sau mỗi lần bạn bấm Lưu.")

    csv_data = df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="📥 Tải xuống CSV bản Final",
        data=csv_data,
        file_name="final_labeled_smishing.csv",
        mime="text/csv",
    )