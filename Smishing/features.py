import sys
import os
import logging
import numpy as np

# Thêm đường dẫn để import module nếu chạy từ root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import các layer
from preprocessing.layer1_masking import AggressiveMasker
from linguistic_features.layer2_normalization import TextNormalizer
from linguistic_features.layer3_whitelist import WhitelistFilter
from linguistic_features.layer4_misspell import MisspellExtractor

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SmishingFeatureExtractor:
    def __init__(self, dict_path=None):
        """
        Khởi tạo pipeline và load tài nguyên (từ điển) một lần duy nhất.
        """
        logger.info("Initializing Smishing Feature Extractor...")
        
        # 1. Init Layer 1
        self.masker = AggressiveMasker()
        
        # 2. Init Layer 2 (Sẽ load từ điển ở đây)
        self.normalizer = TextNormalizer(dict_path=dict_path)
        
        # 3. Init Layer 3
        self.whitelist = WhitelistFilter()
        
        # 4. Init Layer 4 
        # TỐI ƯU: Truyền từ điển đã load từ Layer 2 sang Layer 4 để không phải load lại
        self.misspell = MisspellExtractor(
            full_dict=self.normalizer.full_dict, 
            shadow_dict=self.normalizer.shadow_dict
        )
        
        # Định nghĩa tên các đặc trưng theo thứ tự cố định để đảm bảo đồng bộ vector
        self.feature_names = [
            # --- Layer 1: Entities (12) ---
            'zalo_count', 'telegram_count', 'email_count', 'url_count', 
            'bank_acc_count', 'hotline_count', 'landline_count', 'mobile_count', 
            'shortcode_count', 'datetime_count', 'money_count', 'code_count',
            
            # --- Layer 2: Normalization & Leet (7) ---
            'leet_count', 'separator_count', 'teencode_count', 
            'visual_leet_count', 'symbol_leet_count', 
            'validated_leet_count', 'weighted_leet_score',
            
            # --- Layer 3: Whitelist (1) ---
            'whitelist_count',
            
            # --- Layer 4: Misspell & Anomalies (7) ---
            'oov_count', 'oov_density', 'broken_telex_count', 
            'longest_oov_length', 'gibberish_count', 
            'repeated_char_count', 'run_on_word_count'
        ]
        
        logger.info(f"Initialization Complete. Total features: {len(self.feature_names)}")

    def extract_features(self, text: str, return_dict: bool = False):
        """
        Chạy toàn bộ pipeline qua 4 bước và trả về vector đặc trưng.
        
        Args:
            text: Tin nhắn SMS đầu vào.
            return_dict: Nếu True trả về dict {tên_feature: giá_trị}, False trả về list giá trị.
        """
        if text is None: text = ""
        
        # ==========================================
        # BƯỚC 1: Layer 1 - Masking & Entity Extraction
        # ==========================================
        masked_text, metadata = self.masker.mask(text)
        
        # Chuyển metadata (list items) thành counts
        # Lưu ý: Cần đảm bảo thứ tự đúng như self.feature_names
        l1_features = {
            'zalo_count': len(metadata.get('zalo', [])),
            'telegram_count': len(metadata.get('telegram', [])),
            'email_count': len(metadata.get('email', [])),
            'url_count': len(metadata.get('url', [])),
            'bank_acc_count': len(metadata.get('bank_acc', [])),
            'hotline_count': len(metadata.get('hotline', [])),
            'landline_count': len(metadata.get('landline', [])),
            'mobile_count': len(metadata.get('mobile', [])),
            'shortcode_count': len(metadata.get('shortcode', [])),
            'datetime_count': len(metadata.get('datetime', [])),
            'money_count': len(metadata.get('money', [])),
            'code_count': len(metadata.get('code', []))
        }

        # ==========================================
        # BƯỚC 2: Layer 2 - Normalization & Leetspeak
        # ==========================================
        norm_res = self.normalizer.normalize(masked_text)
        
        l2_features = {
            'leet_count': norm_res.leet_count,
            'separator_count': norm_res.separator_count,
            'teencode_count': norm_res.teencode_count,
            'visual_leet_count': norm_res.visual_leet_count,
            'symbol_leet_count': norm_res.symbol_leet_count,
            'validated_leet_count': norm_res.validated_leet_count,
            'weighted_leet_score': norm_res.weighted_leet_score
        }

        # ==========================================
        # BƯỚC 3: Layer 3 - Whitelist Filtering
        # ==========================================
        # Input là tokens từ Layer 2
        whitelist_res = self.whitelist.filter(norm_res.tokens)
        
        l3_features = {
            'whitelist_count': whitelist_res.whitelist_count
        }

        # ==========================================
        # BƯỚC 4: Layer 4 - Misspell Detection
        # ==========================================
        # Input là tokens_to_check từ Layer 3 (đã lọc whitelist)
        misspell_res = self.misspell.extract(whitelist_res.tokens_to_check)
        
        l4_features = {
            'oov_count': misspell_res.oov_count,
            'oov_density': misspell_res.oov_density,
            'broken_telex_count': misspell_res.broken_telex_count,
            'longest_oov_length': misspell_res.longest_oov_length,
            'gibberish_count': misspell_res.gibberish_count,
            'repeated_char_count': misspell_res.repeated_char_count,
            'run_on_word_count': misspell_res.run_on_word_count
        }

        # ==========================================
        # TỔNG HỢP KẾT QUẢ
        # ==========================================
        # Gom tất cả feature vào 1 dict duy nhất
        all_features = {**l1_features, **l2_features, **l3_features, **l4_features}
        
        if return_dict:
            return all_features, masked_text, norm_res.normalized_text
        
        # Trả về list values theo đúng thứ tự feature_names (để đưa vào model)
        feature_vector = [all_features[name] for name in self.feature_names]
        return feature_vector

    def get_feature_names(self):
        """Trả về danh sách tên cột cho DataFrame"""
        return self.feature_names

# --- CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    # Giả lập dữ liệu
    samples = [
        "Truy cap ngay banca . com nhan thuong 500k",
        "Lien he zalo 0912345678, soan tin DK gui 9029",
        "T.h.o.n.g b.a.o: Tai khoan cua ban bi khoa. Vui long xac thuc tai vcb-i.com",
        "Chuc mung ban may man trung thuong xe may SH",
        "Dich vu tham my vien, giam gia 50% cho 100kh dau tien"
    ]
    
    extractor = SmishingFeatureExtractor()
    
    print(f"\n{'='*20} FEATURE EXTRACTION DEMO {'='*20}")
    print(f"Total features defined: {len(extractor.get_feature_names())}")
    
    for i, sms in enumerate(samples):
        print(f"\n--- SMS #{i+1} ---")
        print(f"Original: {sms}")
        
        vector = extractor.extract_features(sms, return_dict=False)
        features_dict, masked, norm = extractor.extract_features(sms, return_dict=True)
        
        print(f"Masked:   {masked}")
        print(f"Norm:     {norm}")
        print(f"Vector ({len(vector)} dims): {vector}")
        
        # In chi tiết các feature khác 0 để kiểm tra
        print("Non-zero Features:")
        for name, val in features_dict.items():
            if val > 0:
                print(f"  + {name}: {val}")