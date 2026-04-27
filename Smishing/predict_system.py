import joblib
import logging
import warnings

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
        # BƯỚC 3: HYBRID DECISION (QUYẾT ĐỊNH CUỐI CÙNG)
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

        # --- LOGIC 3: AI DECISION ---
        else:
            if ai_prob >= self.threshold:
                is_smishing = True
                decision_phase = "AI Detection"
                final_reason = "Cảnh báo: AI phát hiện cấu trúc văn bản thường thấy trong tin nhắn rác/lừa đảo."
            else:
                is_smishing = False
                decision_phase = "AI Model"
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