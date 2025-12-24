import joblib
import numpy as np
import logging
from features import SmishingFeatureExtractor

# Cấu hình logging để tắt bớt cảnh báo của XGBoost nếu cần
logging.getLogger('xgboost').setLevel(logging.WARNING)

print("Dang khoi tao he thong...")

try:
    from domain_check import URLInspector, SpamTextCleaner
    from preprocessing.layer1_masking import AggressiveMasker # Dùng masker để detect entity
    from features import SmishingFeatureExtractor
except ImportError as e:
    print(f"LỖI IMPORT: {e}")
    print("Vui lòng đảm bảo các file: domain_check.py, layer1_masking.py, features.py nằm cùng thư mục.")
    exit()

# --- 2. LOAD AI MODELS (Từ predict_test.py) ---
print(">>> Đang khởi tạo hệ thống Smishing Detection...")
try:
    ai_model = joblib.load('smishing_xgb.pkl')
    sender_encoder = joblib.load('sender_encoder.pkl')
    print(" [OK] Đã load AI Model & Encoder.")
except FileNotFoundError:
    print(" [LỖI] Không tìm thấy file model (.pkl). Hãy train model trước.")
    exit()

# Khởi tạo các công cụ
masker = AggressiveMasker()
cleaner = SpamTextCleaner()
inspector = URLInspector()
extractor = SmishingFeatureExtractor()

# --- 3. HÀM DỰ ĐOÁN CỦA AI (Core Logic cũ) ---
def run_ai_prediction(text, sender_type):
    """Chạy Feature Extraction và XGBoost Model"""
    # Trích xuất 27 đặc trưng
    text_features = extractor.extract_features(text)
    
    # Mã hóa sender
    try:
        sender_code = sender_encoder.transform([sender_type])[0]
    except ValueError:
        sender_code = 0 # Fallback nếu sender lạ
        
    # Ghép vector: [sender_code, ...text_features]
    full_vector = [sender_code] + text_features
    
    # Dự đoán
    prob = ai_model.predict_proba([full_vector])[:, 1][0]
    return prob

# --- 4. PIPELINE CHÍNH (THEO FLOWCHART) ---
def hybrid_smishing_check(raw_text, sender_type='unknown'):
    print(f"\nProcessing SMS: '{raw_text[:50]}...'")
    logs = []
    
    # BƯỚC 1: PRE-PROCESSING (Tìm URL, Phone, Email)
    # Masker của bạn trả về metadata chứa danh sách url/phone/email
    masked_text, metadata = masker.mask(raw_text)
    urls = metadata.get('url', [])
    phones = metadata.get('phone', [])
    emails = metadata.get('email', [])
    
    # === NHÁNH 1: CÓ URL TRONG SMS? ===
    if urls:
        logs.append(f"-> Detected URLs: {urls}")
        clean_text = cleaner.clean(raw_text)
        all_urls_trusted = True
        
        for raw_url in urls:
            url = inspector.refang_url(raw_url)
            
            # Domain Check 1: Search Engine
            is_trust_1, reason_1 = inspector.check_domain_reputation(url, clean_text)
            
            if is_trust_1:
                logs.append(f"   + URL '{raw_url}': TRUSTED (Search: {reason_1})")
                continue # URL này ổn, check URL tiếp theo
            
            # Domain Check 2: Content Analysis (Nếu Check 1 fail)
            logs.append(f"   ! URL '{raw_url}': Check 1 failed. Running Check 2...")
            is_trust_2, reason_2 = inspector.check_page_content(url)
            
            if is_trust_2:
                logs.append(f"   + URL '{raw_url}': TRUSTED (Content: {reason_2})")
            else:
                logs.append(f"   x URL '{raw_url}': SUSPICIOUS (Reason: {reason_2})")
                all_urls_trusted = False
                break # Chỉ cần 1 URL nguy hiểm là coi như nguy hiểm
        
        # RA QUYẾT ĐỊNH SAU KHI CHECK URL
        if all_urls_trusted:
            return {
                "decision": "LEGIT",
                "reason": "All URLs are verified Trusted/Whitelisted",
                "score": 0.0,
                "logs": logs
            }
        else:
            logs.append("-> URL Check Failed. Switching to AI Model...")
            # Nếu URL check fail -> Đẩy sang AI (Theo mũi tên 'No' của sơ đồ)
            prob = run_ai_prediction(raw_text, sender_type)
            label = "SMISHING" if prob >= 0.46 else "LEGIT"
            return {
                "decision": label,
                "reason": f"URL Suspicious + AI Score {prob:.2f}",
                "score": prob,
                "logs": logs
            }

    # === NHÁNH 2: KHÔNG CÓ URL, NHƯNG CÓ PHONE/EMAIL? ===
    elif phones or emails:
        logs.append(f"-> No URL, but detected Phone/Email: {phones or emails}")
        logs.append("-> Switching to AI Model (Feature Extraction)...")
        
        prob = run_ai_prediction(raw_text, sender_type)
        label = "SMISHING" if prob >= 0.46 else "LEGIT"
        
        return {
            "decision": label,
            "reason": f"Sensitive Info detected + AI Score {prob:.2f}",
            "score": prob,
            "logs": logs
        }

    # === NHÁNH 3: KHÔNG CÓ GÌ (CLEAN) ===
    else:
        return {
            "decision": "LEGIT",
            "reason": "No URL, Phone, or Email detected. Safe content.",
            "score": 0.0,
            "logs": logs
        }

# --- 5. CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    test_cases = [
        # Case 1: URL sạch (Vietcombank) -> Nên dừng ở Phase 1
        ("Vietcombank thong bao thay doi lai suat. Chi tiet tai vietcombank.com.vn", "brandname"),
        
        # Case 2: URL bậy (Giả mạo) -> Phase 1 fail -> Phase 2 AI bắt
        ("Tai khoan bi khoa. Vui long dang nhap tai vcb-i.com de xac thuc ngay", "personal_number"),
        
        # Case 3: Không URL, chỉ chat -> Nhánh 3 (Legit ngay)
        ("Em oi ve an com khong?", "personal_number"),
        
        # Case 4: Không URL, nhưng có số lạ + nội dung lừa -> Nhánh 2 -> AI bắt
        ("Cuc thue thong bao ban no phi. Lien he 0912345678 de giai quyet gap.", "unknown"),
        
        # Case 5: Shortlink (Bit.ly) -> Phase 1 (Expand) -> Phase 1 
        ("Nhan qua ngay tai bit.ly/test (gia su link nay tro ve trang tin tuc)", "shortcode"),

        # Case 6: Nội dung có dấu + URL 
        ("CSGT Việt Nam: Hồ sơ vi phạm giao thông được lưu trữ dưới tên của bạn. Để biết thêm thông tin, vui lòng truy cập https://dichvucongs.top/vn", "brandname")
    ]

    print(f"{'='*60}")
    print(f"{'TESTING INTEGRATED PIPELINE':^60}")
    print(f"{'='*60}")

    for text, sender in test_cases:
        result = hybrid_smishing_check(text, sender)
        
        print(f"\n[INPUT]: {text}")
        print(f"[SENDER]: {sender}")
        for log in result['logs']:
            print(f"  {log}")
        print(f"STATUS: {result['decision']} ({result['reason']})")
        print("-" * 60)