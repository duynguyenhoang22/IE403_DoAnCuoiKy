import streamlit as st
import pandas as pd
import time

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Smishing Detector AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS TÙY CHỈNH ---
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stAlert { padding: 1rem; border-radius: 0.5rem; }
    .metric-card { background-color: white; padding: 1rem; border-radius: 0.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- IMPORT HỆ THỐNG ---
try:
    from predict_system import SmishingDetectionSystem
except ImportError:
    st.error("❌ Không tìm thấy file 'predict_system.py'. Hãy chắc chắn bạn đã đổi tên file 'predict_system(25_test_cases).py' thành 'predict_system.py' và để cùng thư mục.")
    st.stop()

# --- LOAD MODEL (CACHE) ---
@st.cache_resource
def load_system():
    # Khởi tạo hệ thống (Threshold 0.46)
    return SmishingDetectionSystem(threshold=0.46)

try:
    system = load_system()
except Exception as e:
    st.error(f"Lỗi khởi động hệ thống: {e}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Smishing Guard")
    st.markdown("---")
    
    menu = st.radio(
        "🔍 Chọn Chế Độ:",
        ["Kiểm Tra Thủ Công", "Chạy Test Cases Tự Động"]
    )
    
    st.markdown("---")
    st.subheader("⚙️ Cấu Hình")
    
    new_threshold = st.slider("Ngưỡng chặn (Threshold)", 0.0, 1.0, 0.46, 0.01)
    if new_threshold != system.threshold:
        system.threshold = new_threshold
        st.toast(f"Đã cập nhật Threshold: {new_threshold}", icon="✅")

    st.info(
        """
        **Các loại người gửi:**
        * **Unknown:** Số lạ / Không xác định
        * **Personal:** Số cá nhân (09xx, +84...)
        * **Brandname:** Tên thương hiệu
        """
    )

# --- TRANG 1: KIỂM TRA THỦ CÔNG ---
if menu == "Kiểm Tra Thủ Công":
    st.header("📝 Kiểm Tra Tin Nhắn Đáng Ngờ")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        sms_text = st.text_area(
            "Nhập nội dung tin nhắn:", 
            height=150,
            placeholder="Ví dụ: Vietcombank thong bao tai khoan cua ban bi khoa..."
        )
        
    with col2:
        sender_label = st.selectbox(
            "Loại người gửi:", 
            ["Số lạ (Unknown)", "Số cá nhân (Personal)", "Thương hiệu (Brandname)"]
        )
        
        sender_map = {
            "Số lạ (Unknown)": "unknown",
            "Số cá nhân (Personal)": "personal_number",
            "Thương hiệu (Brandname)": "brandname"
        }
        sender_code = sender_map[sender_label]
        
        check_btn = st.button("🛡️ QUÉT NGAY", use_container_width=True, type="primary")

    if check_btn and sms_text:
        with st.spinner("Đang phân tích..."):
            time.sleep(0.3) 
            result = system.predict(sms_text, sender_code)
            
        st.markdown("---")
        
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.subheader("Kết Quả")
            if result['is_smishing']:
                st.error("🚫 LỪA ĐẢO / RỦI RO")
            else:
                st.success("✅ AN TOÀN")
            
            st.metric("Mức độ tin cậy", f"{result['confidence']*100:.1f}%")
            st.progress(result['confidence'], text="Chỉ số rủi ro")

        with res_col2:
            st.subheader("Chi Tiết Phân Tích")
            st.info(f"📍 **Giai đoạn:** {result['phase']}")
            st.warning(f"💡 **Lý do:** {result['reason']}")
            
            with st.expander("Xem thông số kỹ thuật"):
                st.json({
                    "AI Raw Score": result['raw_ai_score'],
                    "Domain Risk": result.get('domain_risk', 'N/A'),
                    "Sender Type": result['sender']
                })

# --- TRANG 2: CHẠY TEST CASES ---
elif menu == "Chạy Test Cases Tự Động":
    st.header("🧪 Bộ Kiểm Thử Tự Động")
    
    if st.button("🚀 CHẠY TẤT CẢ TEST CASES", type="primary"):
        test_cases = [
            ("Mời bạn truy cập https://vietcombank.com.vn để xem biểu phí.", "brandname"),
            ("Tai khoan cua ban bi khoa. Vui long xac thuc ngay tai: https://vietcombank-secure-login.xyz", "brandname"),
            ("Nhan qua tri an tu Google tai: https://google.com.vn.ngrok.io/claim-reward", "personal_number"),
            ("Shopee tang ban voucher 500k. Nhan tai: s h o p e e . v n / k h u y e n - m a i", "brandname"),
            ("Tuyển dụng nhân viên chốt đơn tại nhà, lương 500k/ngày. Điền form đăng ký: https://docs.google.com/forms/d/xyz", "personal_number"),
            ("S.H.O.P.E.E tu.ye.n du.n.g C.T.V l.a.m o.n.l.i.n.e. I.B Z.a.l.o: 098xxx", "personal_number"),
            ("H0 tro v4y v0n nh4nh ch0ng, kh0ng can th3 ch4p. Giai ng4n tr0ng ng4y.", "personal_number"),
            ("Cty X so lo hom nay, bao dam trung 99%. Lhe ngay 09xxx de lay so.", "personal_number"),
            ("🔥HOT🔥 Việc nhe luong cao!!! ❌Ko cọc ❌Ko vốn. Thu nhập 10tr/tháng. I.b_ngay.", "personal_number"),
            ("Bo oi, may con bi hong, con dang dung so ban. Bo chuyen khoan gap cho con 5 trieu vao so 190xxx nhe.", "unknown"),
            ("Bo Cong An thong bao: Ban co lien quan den duong day rua tien. Vui long co mat tai co quan dieu tra hoac lien he so may nay.", "personal_number"),
            ("Chuc mung thue bao 09xxx da trung thuong 1 xe SH Mode. Soan tin NHANQUA gui 8xxx.", "personal_number"),
            ("Em la Lan, duoc nguoi quen gioi thieu anh. Minh ket ban Zalo so nay nhe, em co chuyen muon noi.", "personal_number"),
            ("Ê mày, tối qua đi ăn tao trả tiền rồi, tí mày chuyển khoản lại cho tao phần của mày nhé.", "personal_number"),
            ("Ma xac thuc (OTP) cua ban la 123456. Ma co hieu luc trong 2 phut. Vui long khong cung cap cho bat ky ai.", "brandname"),
            ("Chieu nay 5h hop nhe em, nho mang theo laptop de trinh chieu.", "personal_number"),
            ("Chuc mung sinh nhat em! Chuc em luon vui ve va hanh phuc nhe. Qua tang anh de o tren ban lam viec.", "personal_number"),
            ("[QC] Giai tri tha ga voi goi cuoc ST150K cua Viettel. Soan ST150K gui 191.", "brandname"),
            ("Alo em a, anh la shipper day, xuong nhan hang nhe.", "brandname"), 
            ("Ok", "personal_number"),
            ("Chào bạn, lâu quá không gặp... [nội dung chém gió dài 200 chữ]... xem ảnh hôm nọ ở đây nhé: http://malware.com/photo.exe", "personal_number"),
            ("Kính gửi quý khách, Công ty TNHH ABC đang tuyển cộng tác viên xử lý đơn hàng. Vui lòng liên hệ Telegram @hr_manager.", "personal_number"),
            ("A oi e kho qua cho e vay 5 trieu lai suat thap cung dc e can gap lam.", "unknown"),
            ("Vui long truy cap http://192.168.1.50/update-firmware de tranh bi ngat mang.", "brandname"),
            ("File danh sach luong thang nay nhe: https://docs.google.com/spreadsheets/d/123456", "personal_number")
        ]
        
        results = []
        progress_bar = st.progress(0, text="Đang chạy test cases...")
        
        for i, (text, sender) in enumerate(test_cases):
            progress_bar.progress((i + 1) / len(test_cases), text=f"Đang xử lý case {i+1}/{len(test_cases)}")
            res = system.predict(text, sender)
            
            results.append({
                "STT": i + 1,
                "Sender": sender,
                "Text Preview": text[:50] + "..." if len(text) > 50 else text,
                "Result": "❌ SCAM" if res['is_smishing'] else "✅ SAFE",
                "Reason": res['reason'],
                "Phase": res['phase'],
                "is_smishing": res['is_smishing']
            })
            
        progress_bar.empty()
        st.success("✅ Đã hoàn thành kiểm thử!")
        
        # Hiển thị bảng kết quả
        df = pd.DataFrame(results)
        
        def highlight_scam(row):
            # Hàm tô màu: Đỏ nhạt nếu Scam, Xanh nhạt nếu Safe
            if row['is_smishing']:
                color = '#ffebee'
            else:
                color = '#e8f5e9'
            return [f'background-color: {color}; color: black'] * len(row)

        st.dataframe(
            df.style.apply(highlight_scam, axis=1),
            column_config={
                "is_smishing": None, 
                "Result": st.column_config.TextColumn("Kết quả", help="Scam hay Safe?"),
            },
            use_container_width=True,
            height=600
        )