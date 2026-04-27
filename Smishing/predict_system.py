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
    def __init__(self, model_path='best_model.pkl', encoder_path='sender_encoder.pkl',
                 threshold=None, model_name='Default'):
        self.model_name = model_name
        print(f"🔄 Starting System...")
        try:
            self.model = joblib.load(model_path)
            self.le = joblib.load(encoder_path)
            self.extractor = SmishingFeatureExtractor()
            self.verifier = DomainVerifier()

            # Load metadata (feature_names & threshold) nếu có file .meta.pkl
            meta_path = model_path.replace('.pkl', '.meta.pkl')
            try:
                meta = joblib.load(meta_path)
                self.feature_names = meta.get('feature_names', None)
                saved_threshold = meta.get('threshold', None)
            except FileNotFoundError:
                self.feature_names = None
                saved_threshold = None

            # Ưu tiên: threshold truyền vào > threshold trong meta > fallback 0.46
            if threshold is not None:
                self.threshold = threshold
            elif saved_threshold is not None:
                self.threshold = saved_threshold
            else:
                self.threshold = 0.46
                warnings.warn(
                    f"Không tìm thấy {meta_path}. Dùng threshold mặc định 0.46.",
                    UserWarning
                )

            print(f"✅ SYSTEM READY! (Threshold={self.threshold:.4f})")
        except Exception as e:
            print(f"FAIL: {e}")
            exit()

    def _simple_normalize(self, text: str) -> str:
        """Chuẩn hóa nhẹ để so khớp từ khóa."""
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text.lower()

    def _build_input_vector(self, text, sender_type):
        """
        Xây dựng vector đầu vào theo đúng thứ tự feature_names đã lưu lúc train.
        Nếu không có metadata, dùng thứ tự mặc định [sender_code] + text_features.
        """
        text_features = self.extractor.extract_features(text)
        try:
            sender_code = int(self.le.transform([sender_type])[0])
        except Exception:
            warnings.warn(f"sender_type '{sender_type}' không có trong encoder. Dùng mã 0.", UserWarning)
            sender_code = 0

        if self.feature_names is not None:
            import pandas as pd
            feat_dict = {'sender_type': sender_code}
            feat_dict.update(dict(zip(self.extractor.get_feature_names(), text_features)))
            # Tái tạo vector theo đúng thứ tự feature_names đã train
            row = pd.DataFrame([[feat_dict.get(col, 0) for col in self.feature_names]],
                               columns=self.feature_names)
            return row
        else:
            return [[sender_code] + text_features]

    def predict(self, text, sender_type='unknown'):
        # ---------------------------------------------------------
        # BƯỚC 1: AI SCORING (BASELINE)
        # ---------------------------------------------------------
        input_vector = self._build_input_vector(text, sender_type)
        ai_prob = float(self.model.predict_proba(input_vector)[:, 1][0])

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
            "raw_ai_score": float(ai_prob),   # Điểm gốc AI để debug
            "domain_risk": risk_score,        # Điểm gốc Domain để debug
            "reason": final_reason,
            "phase": decision_phase
        }