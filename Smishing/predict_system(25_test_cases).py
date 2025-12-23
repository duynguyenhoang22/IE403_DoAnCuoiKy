import joblib
import logging
import warnings
import unicodedata
import re  # Cần import thêm re để xử lý Regex boundary

warnings.filterwarnings("ignore")
logging.getLogger('xgboost').setLevel(logging.WARNING)

try:
    from features import SmishingFeatureExtractor
    from domain_check import DomainVerifier
except ImportError as e:
    print(f"❌ LỖI IMPORT SYSTEM: {e}")
    exit()

class SmishingDetectionSystem:
    def __init__(self, model_path='smishing_xgb.pkl', encoder_path='sender_encoder.pkl', threshold=0.46):
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

    def _simple_normalize(self, text: str) -> str:
        """Chuẩn hóa nhẹ để so khớp từ khóa."""
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text.lower()

    def predict(self, text, sender_type='unknown'):
        # ---------------------------------------------------------
        # BƯỚC 1: AI SCORING (BASELINE)
        # ---------------------------------------------------------
        text_features = self.extractor.extract_features(text)
        try:
            sender_code = self.le.transform([sender_type])[0]
        except:
            sender_code = 0 
            
        full_vector = [sender_code] + text_features
        ai_prob = float(self.model.predict_proba([full_vector])[:, 1][0])

        # ---------------------------------------------------------
        # BƯỚC 2: DOMAIN VERIFICATION
        # ---------------------------------------------------------
        domain_status, domain_reason, risk_score = self.verifier.verify(text)

        # ---------------------------------------------------------
        # BƯỚC 3: CONTEXT ANALYSIS (PHÂN TÍCH NGỮ CẢNH)
        # ---------------------------------------------------------
        norm_text = self._simple_normalize(text)

        # 3.1. Conversation Guard (Bộ lọc hội thoại)
        # Dùng Regex \b để bắt chính xác từ đơn, tránh bắt nhầm (VD: 'bo' trong 'bo cong an')
        conversational_regex = [
            r'\btao\b', r'\bmay\b', r'\bba\b', r'\bme\b', r'\bbo\b', 
            r'\banh\b', r'\bem\b', r'\bchi\b', r'\bminh\b', r'\bvo\b', r'\bchong\b'
        ]
        
        # Các cụm từ dài thì dùng string matching bình thường cho nhanh
        conversational_phrases = [
            'sinh nhat', 'an com', 'di choi', 'di nhau', 'cafe', 
            'hop lop', 'lam viec', 'gui xe', 've chua', 
            'nha mang', 'qc', 'quang cao' # Chấp nhận tin quảng cáo nhà mạng là an toàn
        ]

        is_conversational = False
        # Check Regex trước
        for pattern in conversational_regex:
            if re.search(pattern, norm_text):
                is_conversational = True
                break
        
        # Nếu chưa thấy thì check tiếp phrases
        if not is_conversational:
            is_conversational = any(kw in norm_text for kw in conversational_phrases)

        # 3.2. Danger Guard (Bộ lọc rủi ro)
        # Các từ khóa này sẽ VÔ HIỆU HÓA tính năng hội thoại ở trên
        danger_kw = [
            # Nhóm tài chính (Dễ bị giả danh người thân)
            'vay', 'no xau', 'lai suat', 'giai ngan', 
            'chuyen khoan', 'stk', 'ngan hang', 'bank', 'so du',
            
            # Nhóm việc làm/Lừa đảo
            'viec nhe', 'ctv', 'hoa hong', 'chot don', 'tuyen dung',
            'trung thuong', 'qua tang', 
            
            # Nhóm giả danh cơ quan (Quan trọng)
            'cong an', 'toa an', 'lenh bat', 'dieu tra', 'trieu tap'
        ]
        has_danger = any(kw in norm_text for kw in danger_kw)

        # ---------------------------------------------------------
        # BƯỚC 4: HYBRID DECISION (QUYẾT ĐỊNH CUỐI CÙNG)
        # ---------------------------------------------------------
        
        final_score = ai_prob
        final_reason = ""
        is_smishing = False
        decision_phase = "AI Model"

        # --- LOGIC 1: DOMAIN ĐỘC HẠI (RISK = 1.0) ---
        if risk_score >= 0.8:
            final_score = 1.0
            is_smishing = True
            decision_phase = "Domain Risk"
            final_reason = f"CẢNH BÁO CAO: Phát hiện liên kết độc hại hoặc bị làm nhiễu ({domain_reason})."

        # --- LOGIC 2: WHITELIST (RISK = -1.0) ---
        elif risk_score == -1.0:
            ugc_keywords = ['google', 'drive', 'docs', 'sheet', 'form', 'dropbox', 'bit.ly', 'tinyurl', 'zalopay']
            is_ugc_platform = any(kw in domain_reason.lower() for kw in ugc_keywords)

            if is_ugc_platform:
                # Hybrid check cho Google Form/Drive
                if ai_prob > 0.65:
                    final_score = ai_prob
                    is_smishing = True
                    decision_phase = "Hybrid Warning"
                    final_reason = f"Cảnh báo: Tên miền sạch ({domain_reason}) nhưng nội dung có dấu hiệu lừa đảo."
                else:
                    final_score = 0.2
                    is_smishing = False
                    decision_phase = "Hybrid Safe"
                    final_reason = "An toàn: Tên miền dịch vụ lưu trữ/rút gọn uy tín."
            else:
                final_score = 0.0
                is_smishing = False
                decision_phase = "Authority Whitelist"
                final_reason = f"An toàn: Tên miền chính chủ đã được xác thực ({domain_reason})."

        # --- LOGIC 3: AI + SAFETY NET ---
        else:
            if ai_prob >= self.threshold:
                # AI nghi ngờ -> Kiểm tra Safety Net
                if is_conversational and not has_danger:
                    # AI cao + Hội thoại + KHÔNG nguy hiểm -> Safe
                    final_score = 0.25
                    is_smishing = False
                    decision_phase = "Conversation Guard"
                    final_reason = "Cảnh báo mức thấp: AI nghi ngờ nhưng văn phong mang tính hội thoại cá nhân."
                else:
                    # AI cao + (Không phải hội thoại HOẶC Có nguy hiểm) -> Scam
                    is_smishing = True
                    decision_phase = "AI Detection"
                    final_reason = "Cảnh báo: AI phát hiện cấu trúc văn bản thường thấy trong tin nhắn rác/lừa đảo."
            else:
                # AI thấy an toàn -> Kiểm tra sót lọt
                if has_danger and sender_type != 'brandname':
                    # AI thấp + Có từ khóa nguy hiểm -> Scam
                    final_score = 0.6
                    is_smishing = True
                    decision_phase = "Keyword Trigger"
                    final_reason = "Cảnh báo: Nội dung chứa các từ khóa rủi ro cao (Tài chính/Giả danh) cần xác minh."
                else:
                    is_smishing = False
                    final_reason = "An toàn: Không tìm thấy yếu tố rủi ro trong nội dung."

        return {
            "text": text,
            "sender": sender_type,
            "is_smishing": is_smishing,
            "confidence": float(final_score),
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
        # ==============================================================================
        # NHÓM 1: KIỂM TRA DOMAIN & URL (MỨC ĐỘ ƯU TIÊN CAO NHẤT)
        # ==============================================================================
        
        # 1. URL Chính chủ (Whitelist)
        # Kỳ vọng: SẠCH (Domain uy tín đè bẹp mọi nghi ngờ của AI).
        ("Mời bạn truy cập https://vietcombank.com.vn để xem biểu phí mới nhất năm 2025.", "brandname"),

        # 2. URL Giả mạo (Typosquatting/Phishing)
        # Kỳ vọng: LỪA ĐẢO (Domain Risk = 1.0).
        ("Tai khoan cua ban bi khoa. Vui long xac thuc ngay tai: https://vietcombank-secure-login.xyz", "brandname"),

        # 3. Subdomain Hijacking (Lừa đảo bằng Subdomain)
        # Kỳ vọng: LỪA ĐẢO (Hệ thống phải bỏ qua 'google.com' ở đầu và check domain gốc 'ngrok.io').
        ("Nhan qua tri an tu Google tai: https://google.com.vn.ngrok.io/claim-reward", "personal_number"),

        # 4. URL Obfuscation (Làm nhiễu URL bằng khoảng trắng)
        # Kỳ vọng: LỪA ĐẢO (Regex phải ghép được 'shopee . vn' lại để check).
        ("Shopee tang ban voucher 500k. Nhan tai: s h o p e e . v n / k h u y e n - m a i", "brandname"),

        # 5. URL "Sạch" nhưng nội dung lừa đảo (Ngưỡng xám)
        # Kỳ vọng: LỪA ĐẢO/CẢNH BÁO (Domain google form là sạch, nhưng nội dung tuyển dụng lừa đảo -> AI phải bắt).
        ("Tuyển dụng nhân viên chốt đơn tại nhà, lương 500k/ngày. Điền form đăng ký: https://docs.google.com/forms/d/xyz", "personal_number"),

        # ==============================================================================
        # NHÓM 2: Evasion & Teencode (CỐ TÌNH LÁCH LUẬT TEXT)
        # ==============================================================================

        # 6. Teencode nặng + Ký tự đặc biệt (Dấu chấm xen kẽ)
        # Kỳ vọng: LỪA ĐẢO (Normalization phải xóa dấu chấm để hiện ra từ khóa 'tuyen dung', 'shopee').
        ("S.H.O.P.E.E tu.ye.n du.n.g C.T.V l.a.m o.n.l.i.n.e. I.B Z.a.l.o: 098xxx", "personal_number"),

        # 7. Thay thế ký tự (Leet Speak: a->4, e->3, i->1, o->0)
        # Kỳ vọng: LỪA ĐẢO (Normalization hoặc AI phải học được pattern này).
        ("H0 tro v4y v0n nh4nh ch0ng, kh0ng can th3 ch4p. Giai ng4n tr0ng ng4y.", "personal_number"),

        # 8. Tiếng Việt không dấu + Viết tắt (Style SMS rác cũ)
        # Kỳ vọng: LỪA ĐẢO.
        ("Cty X so lo hom nay, bao dam trung 99%. Lhe ngay 09xxx de lay so.", "personal_number"),

        # 9. Mixed Chaos (Vừa có dấu, vừa không dấu, vừa Icon rác)
        # Kỳ vọng: LỪA ĐẢO.
        ("🔥HOT🔥 Việc nhe luong cao!!! ❌Ko cọc ❌Ko vốn. Thu nhập 10tr/tháng. I.b_ngay.", "personal_number"),

        # ==============================================================================
        # NHÓM 3: SOCIAL ENGINEERING (LỪA ĐẢO TÂM LÝ - KHÔNG URL)
        # ==============================================================================

        # 10. Giả mạo người thân (Nhờ chuyển khoản)
        # Kỳ vọng: LỪA ĐẢO (AI bắt cụm từ 'chuyen khoan', 'gap', sender lạ).
        ("Bo oi, may con bi hong, con dang dung so ban. Bo chuyen khoan gap cho con 5 trieu vao so 190xxx nhe.", "unknown"),

        # 11. Giả mạo cơ quan chức năng (Công an/Tòa án)
        # Kỳ vọng: LỪA ĐẢO (Keyword 'lenh bat', 'cong an', 'dieu tra').
        ("Bo Cong An thong bao: Ban co lien quan den duong day rua tien. Vui long co mat tai co quan dieu tra hoac lien he so may nay.", "personal_number"),

        # 12. Lừa đảo trúng thưởng (Scam kinh điển)
        # Kỳ vọng: LỪA ĐẢO.
        ("Chuc mung thue bao 09xxx da trung thuong 1 xe SH Mode. Soan tin NHANQUA gui 8xxx.", "personal_number"),

        # 13. Lừa đảo tình cảm (Romance Scam)
        # Kỳ vọng: LỪA ĐẢO (Hoặc Nghi ngờ cao).
        ("Em la Lan, duoc nguoi quen gioi thieu anh. Minh ket ban Zalo so nay nhe, em co chuyen muon noi.", "personal_number"),

        # ==============================================================================
        # NHÓM 4: FALSE POSITIVES (KIỂM TRA ĐỘ AN TOÀN - TRÁNH BẮT NHẦM)
        # ==============================================================================

        # 14. Tin nhắn hội thoại bình thường (Chứa từ nhạy cảm 'chuyen khoan')
        # Kỳ vọng: SẠCH (Nhờ Safety Net: Sender Personal + AI score thấp/trung bình -> Bỏ qua).
        ("Ê mày, tối qua đi ăn tao trả tiền rồi, tí mày chuyển khoản lại cho tao phần của mày nhé.", "personal_number"),

        # 15. Tin nhắn OTP chuẩn từ Brandname
        # Kỳ vọng: SẠCH.
        ("Ma xac thuc (OTP) cua ban la 123456. Ma co hieu luc trong 2 phut. Vui long khong cung cap cho bat ky ai.", "brandname"),

        # 16. Tin nhắn công việc/hẹn hò bình thường
        # Kỳ vọng: SẠCH.
        ("Chieu nay 5h hop nhe em, nho mang theo laptop de trinh chieu.", "personal_number"),

        # 17. Tin nhắn chúc mừng (Chứa từ 'tang', 'qua' nhưng ngữ cảnh sạch)
        # Kỳ vọng: SẠCH.
        ("Chuc mung sinh nhat em! Chuc em luon vui ve va hanh phuc nhe. Qua tang anh de o tren ban lam viec.", "personal_number"),

        # 18. Tin nhắn nhà mạng (Quảng cáo hợp lệ)
        # Kỳ vọng: SẠCH.
        ("[QC] Giai tri tha ga voi goi cuoc ST150K cua Viettel. Soan ST150K gui 191.", "brandname"),

        # ==============================================================================
        # NHÓM 5: EDGE CASES (CÁC TRƯỜNG HỢP HỖN LOẠN/BIÊN)
        # ==============================================================================

        # 19. Brandname giả mạo nội dung sạch (Hiếm gặp nhưng để test logic)
        # Kỳ vọng: Tùy logic (Thường là Sạch nếu nội dung quá an toàn, hoặc Cảnh báo nếu Sender không khớp).
        # Test này để xem AI phản ứng thế nào khi Sender='brandname' nhưng text như chat.
        ("Alo em a, anh la shipper day, xuong nhan hang nhe.", "brandname"), 

        # 20. Tin nhắn rất ngắn (Dưới mức tối thiểu của Feature Extractor)
        # Kỳ vọng: SẠCH (Không đủ dữ kiện để kết luận lừa đảo).
        ("Ok", "personal_number"),

        # 21. Tin nhắn rất dài chứa link độc hại ở cuối cùng (Cố tình giấu link)
        # Kỳ vọng: LỪA ĐẢO (Hệ thống phải scan hết chuỗi).
        ("Chào bạn, lâu quá không gặp... [nội dung chém gió dài 200 chữ]... xem ảnh hôm nọ ở đây nhé: http://malware.com/photo.exe", "personal_number"),
        
        # 22. Case "Việc nhẹ" nhưng viết cực kỳ trang trọng (Formal Job Scam)
        # Kỳ vọng: LỪA ĐẢO (AI phải bắt được ngữ nghĩa 'tuyển dụng' + 'telegram' dù văn phong chuẩn).
        ("Kính gửi quý khách, Công ty TNHH ABC đang tuyển cộng tác viên xử lý đơn hàng. Vui lòng liên hệ Telegram @hr_manager.", "personal_number"),

        # 23. Case "Vay tiền" nhưng viết sai chính tả be bét (Cố tình giả nghèo khổ)
        # Kỳ vọng: LỪA ĐẢO (Keyword 'vay', 'lai suat').
        ("A oi e kho qua cho e vay 5 trieu lai suat thap cung dc e can gap lam.", "unknown"),
        
        # 24. URL IP Address (Thường dùng cho trang quản trị router hoặc lừa đảo)
        # Kỳ vọng: LỪA ĐẢO/CẢNH BÁO.
        ("Vui long truy cap http://192.168.1.50/update-firmware de tranh bi ngat mang.", "brandname"),
        
        # 25. Tin nhắn chứa link Google Drive/Docs (Ranh giới mong manh)
        # Kỳ vọng: Phụ thuộc AI (Nếu nội dung dẫn dắt vào link là lừa đảo thì bắt).
        ("File danh sach luong thang nay nhe: https://docs.google.com/spreadsheets/d/123456", "personal_number") 
    ]

    print(f"{'='*80}")
    print(f"{'SENDER':<15} | {'TEXT PREVIEW':<40} | {'RESULT':<10} | {'REASON'}")
    print(f"{'='*80}")

    for text, sender in test_cases:
        res = system.predict(text, sender)
        status = "❌ LỪA ĐẢO" if res['is_smishing'] else "✅ SẠCH"
        print(f"{sender:<15} | {text[:37]:<40} | {status:<10} | {res['reason']}")