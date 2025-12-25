import joblib
import logging
import warnings
import re
import unicodedata

warnings.filterwarnings("ignore")
logging.getLogger('xgboost').setLevel(logging.WARNING)

try:
    from features import SmishingFeatureExtractor
    from domain_check import DomainVerifier
except ImportError as e:
    print(f"❌ LỖI IMPORT SYSTEM: {e}")
    exit()

class SmishingDetectionSystem:
    def __init__(self, model_path='phishing_xgb.pkl', encoder_path='sender_encoder.pkl', threshold=0.46):
        self.threshold = threshold
        print(f"🔄 Starting System (Threshold={self.threshold})...")
        try:
            self.model = joblib.load(model_path)
            self.le = joblib.load(encoder_path)
            self.extractor = SmishingFeatureExtractor()
            self.verifier = DomainVerifier()
            print("✅ SYSTEM READY!")
        except Exception as e:
            print(f"FAIL: {e}")
            exit()

    def _normalize_for_keywords(self, text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)

        return re.sub(r"\s+", " ", text).strip()

    def predict(self, text, sender_type='unknown'):
        # ---------------------------------------------------------
        # BƯỚC 1: LẤY ĐIỂM SỐ TỪ CẢ 2 NGUỒN (AI & DOMAIN)
        # ---------------------------------------------------------
        
        # 1.1 AI Prediction (Luôn chạy để lấy baseline)
        text_features = self.extractor.extract_features(text)
        try:
            sender_code = self.le.transform([sender_type])[0]
        except:
            sender_code = 0
        full_vector = [sender_code] + text_features
        ai_prob = float(self.model.predict_proba([full_vector])[:, 1][0])

        # 1.2 Domain Verification
        domain_status, domain_reason, risk_score = self.verifier.verify(text)

        # ---------------------------------------------------------
        # BƯỚC 2: HỢP NHẤT ĐIỂM SỐ (SCORE FUSION LOGIC)
        # ---------------------------------------------------------
        
        final_score = ai_prob
        final_reason = ""
        is_smishing = False
        decision_phase = "AI Model"

        # LOGIC QUYẾT ĐỊNH:
        
        # TRƯỜNG HỢP 1: PHÁT HIỆN URL ĐỘC HẠI (RISK = 1.0)
        # -> Ưu tiên cao nhất, bất kể AI nói gì.
        if risk_score == 1.0:
            final_score = 1.0
            is_smishing = True
            final_reason = f"PHÁT HIỆN TÊN MIỀN ĐỘC HẠI: {domain_reason}"
            decision_phase = "Domain Check (Phishing Detected)"

        # TRƯỜNG HỢP 2: TÊN MIỀN CHÍNH CHỦ/WHITELIST (RISK = -1.0)
        # -> Giảm điểm AI xuống mức an toàn, nhưng không về 0 tuyệt đối 
        # (đề phòng trường hợp URL sạch nhưng nội dung lừa đảo kiểu 'chuyen khoan').
        elif risk_score == -1.0:
            # Nếu AI nghi ngờ rất cao (>0.9) thì vẫn giữ lại cảnh báo nhẹ, 
            # còn bình thường thì gán về 0.
            if ai_prob > 0.95:
                final_score = 0.45 # Mấp mé ngưỡng cảnh báo
                is_smishing = False
                final_reason = f"Domain an toàn ({domain_reason}), nhưng nội dung đáng ngờ."
            else:
                final_score = 0.0
                is_smishing = False
                final_reason = f"Tên miền chính chủ/Whitelist: {domain_reason}"
            decision_phase = "Domain Check (Verified Safe)"

        # TRƯỜNG HỢP 3: KHÔNG CÓ URL HOẶC KHÔNG XÁC ĐỊNH (RISK = 0.0)
        # -> Dựa hoàn toàn vào AI + Safety Net
        else:
            # Dùng ngưỡng Threshold của AI
            if ai_prob >= self.threshold:
                is_smishing = True
                final_reason = "AI phát hiện nội dung/hành vi đáng ngờ"
                text = self._normalize_for_keywords(text)
                # --- BƯỚC 3: SAFETY NET (LƯỚI AN TOÀN CHO CHAT) ---
                # Chỉ kích hoạt khi: AI nghi ngờ + Sender cá nhân + Không có URL
                if sender_type == 'personal_number' and ai_prob < 0.80:
                    # Kiểm tra từ khóa nguy hiểm (Cả có dấu và không dấu)
                    danger_keywords = [
                        # Nhóm nguy hiểm cao (Có dấu)
                        'otp', 'mã', 'cskh', 'bank', 'thưởng', 'tặng', 'phí', 'lệnh', 
                        'công an', 'tòa án', 'click', 'truy cập', 'chuyển khoản', 
                        'vui lòng', 'xác thực', 'trúng', 'vay', 'nợ', 'lãi',
                        
                        # Nhóm nguy hiểm cao (Không dấu - Teencode)
                        'thuong', 'lenh', 'cong an', 'toa an', 
                        'chuyen khoan', 'xac thuc', 'trung',
                        
                        # Cụm từ thay vì từ đơn (Tránh bắt nhầm "hôm qua", "nhân viên")
                        'nhan qua', 'nhan tien', 'qua tang', 'nhan thuong', # Thay vì 'qua', 'nhan'
                        'gui tang', 'trung thuong', 'tuyen dung', 'ctv', 'viec lam', 'thu nhap', 'chot don', 'luong cao'

                        
                    ]
                    has_danger = any(kw in text.lower() for kw in danger_keywords)
                    
                    # Nếu không có từ khóa nguy hiểm -> Hủy án
                    if not has_danger:
                        is_smishing = False
                        final_reason = "Tin nhắn hội thoại thông thường (Conversation)"
                        decision_phase = "Safety Net (AI Override)"
                        # Giảm score xuống dưới ngưỡng để không báo động
                        final_score = min(ai_prob, 0.3) 

            else:
                is_smishing = False
                final_reason = "Nội dung an toàn"

        # ---------------------------------------------------------
        # BƯỚC 4: ĐÓNG GÓI KẾT QUẢ
        # ---------------------------------------------------------
        return {
            "text": text,
            "sender": sender_type,
            "is_smishing": is_smishing,
            "confidence": float(final_score), # Điểm số cuối cùng đã qua xử lý
            "raw_ai_score": float(ai_prob),   # Điểm gốc của AI (để debug)
            "domain_risk": risk_score,        # Điểm gốc của Domain
            "reason": final_reason,
            "phase": decision_phase
        }

# ==========================================
# MAIN EXECUTION (DEMO)
# ==========================================
if __name__ == "__main__":
    # Khởi tạo hệ thống
    system = SmishingDetectionSystem(threshold=0.46)

    test_cases = [
        # --- NHÓM 1: KIỂM TRA ĐỘ CHÍNH XÁC CỦA DOMAIN CHECKER ---
        
        # Case 1: Lừa đảo "Treo đầu dê bán thịt chó" (Brand Mismatch)
        # Mục tiêu: Test khả năng nhận diện Brand (Layer 2) và so sánh Domain (Layer 3).
        # Kỳ vọng: LỪA ĐẢO (Dù sender là Brandname giả, nhưng Domain Check phải bắt được link sai).
        ("Quy khach V.C.B vui long xac thuc kyc tai vcb-digibank-secure.xyz de tranh bi khoa tai khoan.", "brandname"),

        # Case 2: Lừa đảo Subdomain tinh vi (Subdomain Hijacking)
        # Mục tiêu: Test logic phân tích TLD. Hacker để domain thật ở đầu để lừa mắt nhìn.
        # Kỳ vọng: LỪA ĐẢO (Domain gốc là 'ngrok-free.app', không phải 'vietcombank.com.vn').
        ("Vietcombank thong bao: So du bien dong -2.000.000. Chi tiet: https://vietcombank.com.vn.ngrok-free.app/login", "personal_number"),

        # --- NHÓM 2: KIỂM TRA KHẢ NĂNG "GIẢI MÃ" CỦA AI (NORMALIZATION) ---

        # Case 3: Kỹ thuật Leetspeak/Teencode nặng (Evasion)
        # Mục tiêu: Test Layer 2 (TextNormalizer). Hệ thống phải hiểu "h0.tro", "t.i.k.i", "v4y".
        # Kỳ vọng: LỪA ĐẢO (AI phải phát hiện được pattern đáng ngờ sau khi chuẩn hóa).
        ("T.i.k.i tu.yen d.ung C.T.V l.a.m o.n.l.i.n.e. Th.u nh.ap 500k/ngay. I.B Z.a.l.o: 09xx.xxx.xxx", "personal_number"),

        # Case 4: Lừa đảo URL bị làm nhiễu (URL Obfuscation)
        # Mục tiêu: Test Layer 1 (AggressiveMasker). Phải bắt được URL dù có dấu cách.
        # Kỳ vọng: LỪA ĐẢO (Masker phải ghép được 'bit . ly' thành URL để Domain Check hoạt động).
        ("Nhan qua tri an khach hang tai bi t . ly / qua-tang-bi-mat", "personal_number"),

        # --- NHÓM 3: LỪA ĐẢO KHÔNG CÓ URL (DỰA HOÀN TOÀN VÀO AI) ---

        # Case 5: Lừa đảo "Việc nhẹ lương cao" (Job Scam)
        # Mục tiêu: Test bộ từ khóa của AI (tuyen dung, ctv, khong coc, ib zalo).
        # Kỳ vọng: LỪA ĐẢO (Confidence cao do chứa nhiều keyword rác).
        ("Shopee tuyển nhân viên chốt đơn, không cần cọc, lương nhận trong ngày. Liên hệ telegram @hr_shopee để nhận việc.", "personal_number"),

        # Case 6: Lừa đảo chuyển tiền/mượn tiền (Social Engineering)
        # Mục tiêu: Test khả năng phân biệt ngữ cảnh.
        # Kỳ vọng: LỪA ĐẢO (AI phát hiện hành vi hối thúc + số lạ).
        ("Anh oi em dang can tien gap, chuyen khoan cho em 5 trieu vao so 1903xxx nay nhe, toi ve em tra.", "unknown"),

        # --- NHÓM 4: KIỂM TRA "OAN SAI" (FALSE POSITIVE TEST) ---
        
        # Case 7: Tin nhắn OTP chuẩn (Legit OTP)
        # Mục tiêu: Đảm bảo không chặn tin nhắn quan trọng của người dùng.
        # Kỳ vọng: SẠCH (Chứa từ khóa nhạy cảm 'ma', 'otp' nhưng cấu trúc chuẩn, sender uy tín).
        ("Ma xac thuc OTP cua ban la 840293. Hieu luc trong 5 phut. Tuyet doi khong chia se cho ai.", "brandname"),

        # Case 8: Tin nhắn quảng cáo sạch (Legit Ads)
        # Mục tiêu: Phân biệt Spam rác và Quảng cáo nhà mạng.
        # Kỳ vọng: SẠCH (Link về trang chủ chính thức viettel.vn).
        ("VIETTEL TB: Tang 20% gia tri the nap cho thue bao tra truoc. Chi tiet tai https://viettel.vn/khuyen-mai.", "brandname"),

        # Case 9: Tin nhắn giao tiếp đời thường (Conversational)
        # Mục tiêu: Test xem AI có bị "nhạy cảm" quá với số lạ không.
        # Kỳ vọng: SẠCH (Không chứa keyword nguy hiểm, không URL, không Zalo/Tele).
        ("Alo ban oi, ti nua qua don minh di an com nhe, minh doi o cong cty.", "personal_number"),

        # --- NHÓM 5: EDGE CASE (CA KHÓ) ---

        # Case 10: Lừa đảo giả danh Shipper (Shipper Scam)
        # Mục tiêu: Đây là dạng lừa đảo mới (gửi link thu phí ship).
        # Kỳ vọng: LỪA ĐẢO (AI hoặc Domain Check phải bắt được link lạ ghtk-vn.top).
        ("Giao Hang Tiet Kiem: Don hang cua ban thieu 10k phi ship. Vui long thanh toan tai ghtk-vn.top de duoc giao hang.", "personal_number")
    ]

    print(f"{'='*80}")
    print(f"{'SENDER':<15} | {'TEXT PREVIEW':<40} | {'RESULT':<10} | {'REASON'}")
    print(f"{'='*80}")

    for text, sender in test_cases:
        res = system.predict(text, sender)
        status = "❌ LỪA ĐẢO" if res['is_smishing'] else "✅ SẠCH"
        print(f"{sender:<15} | {text[:37]:<40} | {status:<10} | {res['reason']}")