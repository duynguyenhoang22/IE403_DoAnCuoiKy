import joblib
import numpy as np
import logging
from features import SmishingFeatureExtractor

# Cấu hình logging để tắt bớt cảnh báo của XGBoost nếu cần
logging.getLogger('xgboost').setLevel(logging.WARNING)

print("Dang khoi tao he thong...")

# 1. Load Model & Resources
try:
    print("Loading model & encoder...")
    model = joblib.load('smishing_xgb.pkl')
    le = joblib.load('sender_encoder.pkl') # Load bộ mã hóa sender_type đã lưu lúc train
except FileNotFoundError as e:
    print(f"LOI: Khong tim thay file model hoac encoder. Hay chay train_model.py truoc!\nChi tiet: {e}")
    exit()

# Load Feature Extractor
extractor = SmishingFeatureExtractor() 

def check_sms(text, sender_type='unknown'):
    """
    Kiem tra tin nhan co phai Smishing khong.
    Args:
        text: Noi dung tin nhan
        sender_type: Loai nguoi gui (brandname, shortcode, personal_number, unknown...)
    """
    # B1: Trích xuất 27 đặc trưng ngôn ngữ từ text
    text_features = extractor.extract_features(text) # Trả về list 27 phần tử
    
    # B2: Mã hóa sender_type thành số (Feature thứ 28)
    try:
        # Transform trả về mảng, lấy phần tử đầu tiên
        sender_code = le.transform([sender_type])[0]
    except ValueError:
        # Nếu sender_type lạ chưa từng gặp lúc train (ví dụ nhập sai), 
        # ta có thể gán về nhóm phổ biến nhất hoặc nhóm rủi ro thấp nhất.
        # Ở đây giả sử gán về 'unknown' nếu có, hoặc 0.
        # Cách tốt nhất là in cảnh báo
        print(f"[WARN] Loai sender '{sender_type}' chua tung gap. Se gan mac dinh la 0.")
        sender_code = 0 

    # B3: Ghép thành vector 28 chiều
    # text_features là list, ta append sender_code vào cuối
    full_vector = [sender_code] + text_features
    
    # B4: Dự đoán
    # model.predict_proba nhận vào mảng 2 chiều (danh sách các mẫu)
    prob = model.predict_proba([full_vector])[:, 1][0]
    
    # Dùng ngưỡng tối ưu bạn đã chọn (ví dụ 0.46)
    THRESHOLD = 0.46 
    is_spam = prob >= THRESHOLD
    
    label = "LỪA ĐẢO (Smishing)" if is_spam else "Sạch (Clean)"
    print("-" * 60)
    print(f"SMS: '{text}'")
    print(f"Sender: {sender_type} (Code: {sender_code})")
    print(f">> KET QUA: {label}")
    print(f">> Xac suat lua dao: {prob:.4f}")
    if is_spam:
        print(">> CANH BAO: Tin nhan nay co noi dung nguy hiem!")
    print("-" * 60 + "\n")

# --- DANH SÁCH TEST THỰC TẾ ---
if __name__ == "__main__":
    print("\n--- BẮT ĐẦU BLIND TEST (VOI SENDER INFO) ---\n")

    # Case 1: Tin sạch nhưng có số (OTP) - Thường gửi từ Brandname hoặc Shortcode
    check_sms(
        text="Ma OTP cua ban la 849201. Tuyet doi khong chia se cho ai.", 
        sender_type="brandname" # Brandname uy tín
    )

    # Case 2: Lừa đảo rõ ràng (Teencode + URL) - Thường gửi từ số cá nhân rác (SIM rác)
    check_sms(
        text="Tai khoan cua ban bi khoa. Vui long dang nhap tai v.c.b-i.com de xac minh ngay.", 
        sender_type="personal_number" # Số cá nhân (09xxx) -> Rủi ro cao
    )

    # Case 3: Lừa đảo tinh vi (Giả danh Brandname) - Nội dung dọa nạt
    # Hacker dùng kỹ thuật SMS Brandname giả (Fake Base Station)
    check_sms(
        text="Bo Cong An thong bao ban lien quan den vu an hinh su. Truy cap 113.congan.vn.xyz de khai bao.", 
        sender_type="brandname" # Giả Brandname -> Để xem model có bị lừa không?
    )

    # Case 4: Tin sạch kiểu quảng cáo - Gửi từ đầu số ngắn
    check_sms(
        text="Khuyen mai 50% gia tri the nap cho thue bao tra truoc ngay hom nay. Lien he 19008198.", 
        sender_type="shortcode" # Đầu số nhà mạng
    )

    # Case 5: Tin nhắn chat bình thường - Số cá nhân
    check_sms(
        text="Em oi hom nay ve muon nhe, ko can cho com dau.", 
        sender_type="personal_number"
    )

    # Case 6: Lừa đảo nhưng cố tình dùng Brandname để đánh lừa (Test độ mạnh của Text Features)
    check_sms(
        text="Quy khach da du dieu kien vay 50 trieu voi lai suat 0%. Lien he zalo 0912345678.",
        sender_type="brandname" 
    )

    print("\n--- TEST CASE MỞ RỘNG: CÓ DẤU & KỊCH BẢN HỖN HỢP ---\n")

    # Case 7: Tin nhắn Ngân hàng chuẩn (Tiếng Việt có dấu đầy đủ)
    # Kỳ vọng: Sạch
    check_sms(
        text="Vietcombank trân trọng thông báo. Số dư tài khoản 0123xxx thay đổi -2,000,000 VND lúc 10:30. Nội dung: Chuyen tien mua hang.",
        sender_type="brandname"
    )

    # Case 8: Lừa đảo mạo danh có dấu (Kịch bản dọa khóa tài khoản)
    # Kỳ vọng: Lừa đảo (Dù viết tiếng Việt chuẩn nhưng chứa Link lạ)
    check_sms(
        text="Cảnh báo: Tài khoản E-Banking của Quý khách có dấu hiệu xâm nhập bất hợp pháp. Vui lòng xác thực ngay tại website: https://vcb-security.xyz để tránh bị khóa.",
        sender_type="brandname" # Giả danh Brandname
    )

    # Case 9: Lừa đảo "Việc nhẹ lương cao" (Hỗn hợp: Text mời chào + Zalo + Số cá nhân)
    # Kỳ vọng: Lừa đảo (Đây là dạng spam phổ biến nhất hiện nay)
    check_sms(
        text="Cty TMĐT Shopee tuyển cộng tác viên xử lý đơn hàng online. Thu nhập 500k-1tr/ngày. Công việc uy tín, không cọc. Liên hệ Zalo: 0868.123.456 để nhận việc ngay.",
        sender_type="personal_number"
    )

    # Case 10: Tin nhắn Shipper (Bình thường nhưng từ số lạ)
    # Kỳ vọng: Sạch (Hoặc xác suất lừa đảo thấp hơn Case 5)
    # Test xem model có phân biệt được Shipper với Kẻ lừa đảo không
    check_sms(
        text="Alo ban oi, minh la shipper Giao Hang Tiet Kiem. Ban co nha khong minh giao don hang Shopee nhe. Xuong nhan giup minh voi.",
        sender_type="personal_number"
    )

    # Case 11: Tin nhắn chứa URL sạch (Quảng cáo thật từ Tiki/Shopee)
    # Kỳ vọng: Sạch (Link tiki.vn uy tín)
    check_sms(
        text="Tiki Sale luong ve: Giam den 50% toan bo nganh hang thoi trang. Mua ngay tai: https://tiki.vn/khuyen-mai. So luong co han.",
        sender_type="brandname"
    )

    # Case 12: Tin nhắn vay tiền "giả danh" (Viết không dấu, cố tình lách luật)
    # Kỳ vọng: Lừa đảo (Chứa keywords nhạy cảm: vay, lai suat, ho so)
    check_sms(
        text="Ho tro vay tien mat nhanh chong, ko can tham dinh, giai ngan trong ngay. Lai suat thap. Chi can CMND. LH: 0909.888.999",
        sender_type="personal_number"
    )