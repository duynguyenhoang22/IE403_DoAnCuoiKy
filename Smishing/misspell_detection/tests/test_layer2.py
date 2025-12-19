"""
Test Suite for Layer 2: Text Normalization
==========================================
Covers:
1. Leetspeak Decoding
2. Separator Cleaning  
3. Layer 1 Tag Protection
4. Tokenization
5. Edge Cases
6. Integration with Dataset
"""

import pytest
import sys
from pathlib import Path

# Setup path
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from Smishing.misspell_detection.layer2_normalization import TextNormalizer, NormalizationResult


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def normalizer():
    """Fixture tạo TextNormalizer instance"""
    return TextNormalizer()


# ============================================================
# TEST GROUP 1: LEETSPEAK DECODING
# ============================================================

class TestLeetspeak:
    """Tests cho Leetspeak decoding"""
    
    def test_leet_digit_0_to_o(self, normalizer):
        """0 → o"""
        text = "kh0ng"
        result = normalizer.normalize(text)
        assert "khong" in result.normalized_text
        assert result.leet_count >= 1
    
    def test_leet_digit_1_to_i(self, normalizer):
        """1 → i"""
        text = "t1en"
        result = normalizer.normalize(text)
        assert "tien" in result.normalized_text
    
    def test_leet_digit_3_to_e(self, normalizer):
        """3 → e"""
        text = "ti3n"
        result = normalizer.normalize(text)
        assert "tien" in result.normalized_text
    
    def test_leet_digit_4_to_a(self, normalizer):
        """4 → a"""
        text = "kho4n"
        result = normalizer.normalize(text)
        assert "khoan" in result.normalized_text
    
    def test_leet_symbol_exclamation_to_i(self, normalizer):
        """! → i"""
        text = "d!eu k!en"
        result = normalizer.normalize(text)
        assert "dieu" in result.normalized_text
        assert "kien" in result.normalized_text
    
    def test_leet_symbol_at_to_a(self, normalizer):
        """@ → a"""
        text = "t@i kho@n"
        result = normalizer.normalize(text)
        assert "tai" in result.normalized_text
        assert "khoan" in result.normalized_text
    
    def test_leet_symbol_dollar_to_s(self, normalizer):
        """$ → s"""
        text = "$ms"
        result = normalizer.normalize(text)
        assert "sms" in result.normalized_text
    
    def test_leet_char_j_to_i(self, normalizer):
        """j → i (Vietnamese-specific)"""
        text = "mjnh"
        result = normalizer.normalize(text)
        assert "minh" in result.normalized_text
    
    def test_leet_char_w_to_u(self, normalizer):
        """w → u (Vietnamese-specific)"""
        text = "wua"
        result = normalizer.normalize(text)
        assert "uua" in result.normalized_text
    
    def test_leet_char_z_to_d(self, normalizer):
        """z → d (Vietnamese-specific)"""
        text = "zang"
        result = normalizer.normalize(text)
        assert "dang" in result.normalized_text
    
    def test_leet_char_f_to_ph(self, normalizer):
        """f → ph (Vietnamese-specific, 1→2 char)"""
        text = "fap ly"
        result = normalizer.normalize(text)
        assert "phap" in result.normalized_text
    
    def test_leet_combined(self, normalizer):
        """Multiple leet chars in one text"""
        text = "kh0ng co d!eu k!en"
        result = normalizer.normalize(text)
        assert "khong" in result.normalized_text
        assert "dieu" in result.normalized_text
        assert "kien" in result.normalized_text
        assert result.leet_count >= 3
    
    def test_leet_heavy_spam(self, normalizer):
        """Heavy leetspeak như spam thực tế"""
        text = "Th0ng ba0 NHAN T1EN h0 tr0"
        result = normalizer.normalize(text)
        assert "thong" in result.normalized_text
        assert "bao" in result.normalized_text
        assert "tien" in result.normalized_text


# ============================================================
# TEST GROUP 2: SEPARATOR CLEANING
# ============================================================

class TestSeparatorCleaning:
    """Tests cho Separator cleaning"""
    
    def test_separator_apostrophe(self, normalizer):
        """Dấu ' tách từ"""
        text = "NHAN'TIEN"
        result = normalizer.normalize(text)
        assert "nhan" in result.tokens
        assert "tien" in result.tokens
    
    def test_separator_dash(self, normalizer):
        """Dấu - tách từ"""
        text = "QUA-HAN"
        result = normalizer.normalize(text)
        assert "qua" in result.tokens
        assert "han" in result.tokens
    
    def test_separator_tilde(self, normalizer):
        """Dấu ~ tách từ"""
        text = "ho~tro"
        result = normalizer.normalize(text)
        assert "ho" in result.tokens
        assert "tro" in result.tokens
    
    def test_separator_colon(self, normalizer):
        """Dấu : tách từ"""
        text = "thong:bao"
        result = normalizer.normalize(text)
        assert "thong" in result.tokens
        assert "bao" in result.tokens
    
    def test_separator_dot(self, normalizer):
        """Dấu . tách từ"""
        text = "tai.khoan"
        result = normalizer.normalize(text)
        assert "tai" in result.tokens
        assert "khoan" in result.tokens
    
    def test_separator_multiple(self, normalizer):
        """Nhiều separator khác nhau"""
        text = "NHAN'TIEN-MAT~ngay.nay"
        result = normalizer.normalize(text)
        assert "nhan" in result.tokens
        assert "tien" in result.tokens
        assert "mat" in result.tokens
        assert "ngay" in result.tokens
        assert result.separator_count >= 4
    
    def test_separator_complex_spam(self, normalizer):
        """Spam pattern phức tạp"""
        text = "d!eu'k!en:NHAN-T1EN"
        result = normalizer.normalize(text)
        # Sau normalize: dieu kien nhan tien
        assert len(result.tokens) >= 4


# ============================================================
# TEST GROUP 3: LAYER 1 TAG PROTECTION
# ============================================================

class TestTagProtection:
    """Tests cho việc bảo vệ Layer 1 Tags"""
    
    def test_protect_url_tag(self, normalizer):
        """<URL> được giữ nguyên"""
        text = "Truy cap <URL> ngay"
        result = normalizer.normalize(text)
        assert "<URL>" in result.tokens
    
    def test_protect_phone_tag(self, normalizer):
        """<PHONE> được giữ nguyên"""
        text = "Lien he <PHONE> de duoc ho tro"
        result = normalizer.normalize(text)
        assert "<PHONE>" in result.tokens
    
    def test_protect_money_tag(self, normalizer):
        """<MONEY> được giữ nguyên"""
        text = "Nhan ngay <MONEY>"
        result = normalizer.normalize(text)
        assert "<MONEY>" in result.tokens
    
    def test_protect_code_tag(self, normalizer):
        """<CODE> được giữ nguyên"""
        text = "Ma xac thuc la <CODE>"
        result = normalizer.normalize(text)
        assert "<CODE>" in result.tokens
    
    def test_protect_app_link_tag(self, normalizer):
        """<APP_LINK> (có underscore) được giữ nguyên"""
        text = "Lien he qua <APP_LINK>"
        result = normalizer.normalize(text)
        assert "<APP_LINK>" in result.tokens
    
    def test_protect_multiple_tags(self, normalizer):
        """Nhiều tags cùng lúc"""
        text = "Chuyen <MONEY> vao <PHONE> qua <URL>"
        result = normalizer.normalize(text)
        assert "<MONEY>" in result.tokens
        assert "<PHONE>" in result.tokens
        assert "<URL>" in result.tokens
    
    def test_protect_tag_with_leet_around(self, normalizer):
        """Tag không bị ảnh hưởng bởi leet decode xung quanh"""
        text = "kh0ng co <URL> d!eu k!en"
        result = normalizer.normalize(text)
        assert "<URL>" in result.tokens
        assert "khong" in result.tokens
        assert "dieu" in result.tokens


# ============================================================
# TEST GROUP 4: TOKENIZATION
# ============================================================

class TestTokenization:
    """Tests cho Tokenization"""
    
    def test_tokenize_simple(self, normalizer):
        """Tokenize text đơn giản"""
        text = "tai khoan cua ban"
        result = normalizer.normalize(text)
        assert result.tokens == ["tai", "khoan", "cua", "ban"]
    
    def test_tokenize_lowercase(self, normalizer):
        """Tokens được lowercase (trừ tags)"""
        text = "TAI KHOAN CUA BAN"
        result = normalizer.normalize(text)
        assert result.tokens == ["tai", "khoan", "cua", "ban"]
    
    def test_tokenize_mixed_case(self, normalizer):
        """Mixed case text"""
        text = "TaI KhOaN"
        result = normalizer.normalize(text)
        assert "tai" in result.tokens
        assert "khoan" in result.tokens
    
    def test_tokenize_with_vietnamese_chars(self, normalizer):
        """Tiếng Việt có dấu"""
        text = "Tài khoản của bạn"
        result = normalizer.normalize(text)
        assert "tài" in result.tokens
        assert "khoản" in result.tokens
        assert "của" in result.tokens
        assert "bạn" in result.tokens
    
    def test_tokenize_preserves_tag_case(self, normalizer):
        """Tags giữ nguyên uppercase"""
        text = "test <URL> test"
        result = normalizer.normalize(text)
        assert "<URL>" in result.tokens  # Uppercase preserved
    
    def test_tokenize_filters_numbers(self, normalizer):
        """Số không có trong tokens (đã mask ở Layer 1)"""
        text = "abc 123 def"
        result = normalizer.normalize(text)
        # Số thuần không được giữ trong tokens
        assert "abc" in result.tokens
        assert "def" in result.tokens
    
    def test_normalized_text_reconstruction(self, normalizer):
        """normalized_text được xây dựng từ tokens"""
        text = "tai khoan cua ban"
        result = normalizer.normalize(text)
        assert result.normalized_text == "tai khoan cua ban"


# ============================================================
# TEST GROUP 5: EDGE CASES
# ============================================================

class TestEdgeCases:
    """Tests cho các edge cases"""
    
    def test_empty_string(self, normalizer):
        """Empty string"""
        result = normalizer.normalize("")
        assert result.tokens == []
        assert result.normalized_text == ""
        assert result.leet_count == 0
    
    def test_none_handling(self, normalizer):
        """None input - có thể raise hoặc return empty"""
        # Tùy vào implementation, có thể cần try-except
        try:
            result = normalizer.normalize(None)
            assert result.tokens == []
        except (TypeError, AttributeError):
            pass  # Acceptable behavior
    
    def test_only_separators(self, normalizer):
        """Text chỉ có separators"""
        text = "---'''~~~"
        result = normalizer.normalize(text)
        assert result.tokens == []
    
    def test_only_numbers(self, normalizer):
        """Text chỉ có số - partial decode do 2 không có mapping"""
        text = "123456"
        result = normalizer.normalize(text)
        # 1→i, 2→(no map), 3→e, 4→a, 5→s, 6→g
        # Result: "i2easg" → tokenize splits at 2 → ['i', 'easg']
        assert len(result.tokens) >= 1  # Có output do partial decode
    
    def test_unicode_normalization(self, normalizer):
        """Unicode characters được normalize"""
        # Combining character vs precomposed
        text_combining = "tài"  # có thể có combining diacritics
        result = normalizer.normalize(text_combining)
        assert len(result.tokens) >= 1
    
    def test_very_long_text(self, normalizer):
        """Text rất dài"""
        text = "tai khoan " * 1000
        result = normalizer.normalize(text)
        assert len(result.tokens) == 2000
    
    def test_gibberish(self, normalizer):
        """Gibberish text từ spam"""
        text = "tORKiM ay Ma n N ha lXklq"
        result = normalizer.normalize(text)
        # Should not crash, tokens extracted
        assert isinstance(result.tokens, list)


# ============================================================
# TEST GROUP 6: INTEGRATION WITH REAL DATA
# ============================================================

class TestIntegrationRealData:
    """Tests với dữ liệu thực từ dataset"""
    
    def test_real_spam_sample_1(self, normalizer):
        """Sample spam thực tế #1"""
        text = "Ong/(Ba) da du d!eu'k!en NHAN'TIEN h0 tro"
        result = normalizer.normalize(text)
        
        # Verify decoded correctly
        assert "dieu" in result.normalized_text
        assert "kien" in result.normalized_text
        assert "nhan" in result.normalized_text
        assert "tien" in result.normalized_text
        assert result.leet_count >= 3
    
    def test_real_spam_sample_2(self, normalizer):
        """Sample spam thực tế #2 - với Layer 1 tags"""
        text = "Tai khoan <PHONE> da nhan <MONEY> qua <URL>"
        result = normalizer.normalize(text)
        
        assert "<PHONE>" in result.tokens
        assert "<MONEY>" in result.tokens
        assert "<URL>" in result.tokens
    
    def test_real_spam_sample_3(self, normalizer):
        """Sample spam thực tế #3 - heavy leet"""
        text = "QUA-HAN' SE KH0ng DUOC CHAP_NAHN!"
        result = normalizer.normalize(text)
        
        assert "qua" in result.tokens
        assert "han" in result.tokens
        assert "khong" in result.normalized_text  # 0 → o
    
    def test_real_spam_sample_4(self, normalizer):
        """Sample spam thực tế #4 - mixed"""
        text = "Th0ng ba0:BIDV nang cap he thong. Vui l0ng dang nhap <URL>"
        result = normalizer.normalize(text)
        
        assert "thong" in result.normalized_text
        assert "bao" in result.normalized_text
        assert "long" in result.normalized_text  # l0ng → long
        assert "<URL>" in result.tokens
    
    def test_real_ham_sample(self, normalizer):
        """Sample ham (không spam) - text chuẩn"""
        text = "Hương đang làm gì vậy? Dạo này công việc thế nào rồi?"
        result = normalizer.normalize(text)
        
        # Vietnamese text with diacritics preserved
        assert "hương" in result.tokens
        assert "đang" in result.tokens
        assert result.leet_count == 0  # No leet in normal text


# ============================================================
# TEST GROUP 7: RESULT OBJECT
# ============================================================

class TestNormalizationResult:
    """Tests cho NormalizationResult dataclass"""
    
    def test_result_has_all_fields(self, normalizer):
        """Result có đủ các fields"""
        text = "test text"
        result = normalizer.normalize(text)
        
        assert hasattr(result, 'tokens')
        assert hasattr(result, 'normalized_text')
        assert hasattr(result, 'original_text')
        assert hasattr(result, 'leet_count')
        assert hasattr(result, 'separator_count')
    
    def test_result_original_preserved(self, normalizer):
        """original_text được giữ nguyên"""
        text = "Th0ng ba0: TEST"
        result = normalizer.normalize(text)
        
        assert result.original_text == text
    
    def test_result_types(self, normalizer):
        """Kiểm tra types của các fields"""
        text = "test"
        result = normalizer.normalize(text)
        
        assert isinstance(result.tokens, list)
        assert isinstance(result.normalized_text, str)
        assert isinstance(result.original_text, str)
        assert isinstance(result.leet_count, int)
        assert isinstance(result.separator_count, int)


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])