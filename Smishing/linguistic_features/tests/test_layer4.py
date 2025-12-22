"""
Test Suite for Layer 4: Misspell Detection
==========================================
Covers:
1. OOV (Out-Of-Vocabulary) Detection
2. Dual-Lookup Logic (Full dict vs Shadow dict)
3. Broken Telex Detection (dd, aa, ee...)
4. Gibberish Detection (No vowels, Consonant clusters)
5. Repeated Character Detection (aaa, nnn)
6. Run-on Word Detection (dính từ)
7. Density Calculation
8. Integration with Layer 3 output
"""

import pytest
import sys
import pandas as pd
import ast
from pathlib import Path

# === SETUP PATH ===
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from Smishing.misspell_detection.layer4_misspell import MisspellExtractor, MisspellResult


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def mock_dicts():
    """Tạo từ điển giả lập để test logic độc lập với file words.txt"""
    # Từ điển có dấu
    full_dict = {
        'xin', 'chào', 'bạn', 'thông', 'báo', 'tài', 'khoản', 
        'ngân', 'hàng', 'vui', 'lòng', 'liên', 'hệ',
        'đường', 'phố', 'ăn', 'cơm'
    }
    # Từ điển không dấu (Shadow)
    shadow_dict = {
        'xin', 'chao', 'ban', 'thong', 'bao', 'tai', 'khoan', 
        'ngan', 'hang', 'vui', 'long', 'lien', 'he',
        'duong', 'pho', 'an', 'com'
    }
    return full_dict, shadow_dict

@pytest.fixture
def extractor(mock_dicts):
    """Fixture tạo MisspellExtractor với từ điển giả lập"""
    full, shadow = mock_dicts
    return MisspellExtractor(full_dict=full, shadow_dict=shadow)

# ============================================================
# TEST GROUP 1: BASIC OOV & DUAL LOOKUP
# ============================================================

class TestOOVDetection:
    """Tests cơ bản về phát hiện từ lạ và cơ chế tra từ điển kép"""

    def test_valid_words_full_dict(self, extractor):
        """Từ có trong full_dict không phải là OOV"""
        tokens = ['xin', 'chào', 'bạn']
        res = extractor.extract(tokens)
        assert res.oov_count == 0
        assert res.oov_density == 0.0

    def test_valid_words_shadow_dict(self, extractor):
        """Từ không dấu (có trong shadow_dict) không phải là OOV"""
        tokens = ['xin', 'chao', 'ban'] # chao, ban nằm trong shadow
        res = extractor.extract(tokens)
        assert res.oov_count == 0

    def test_oov_word(self, extractor):
        """Từ hoàn toàn lạ là OOV"""
        tokens = ['xin', 'chao', 'kaka', 'xyz']
        res = extractor.extract(tokens)
        assert res.oov_count == 2
        assert 'kaka' in res.oov_tokens
        assert 'xyz' in res.oov_tokens

    def test_case_insensitive(self, extractor):
        """Kiểm tra không phân biệt hoa thường"""
        tokens = ['XIN', 'ChàO', 'BẠN'] # Nên được normalize và tìm thấy
        res = extractor.extract(tokens)
        assert res.oov_count == 0

    def test_ignore_digits_and_short(self, extractor):
        """Bỏ qua số và từ quá ngắn (<2 chars)"""
        # '123' là số -> ignore
        # 'a' là ngắn -> ignore
        # 'xyz' là OOV
        tokens = ['123', 'a', 'xyz'] 
        res = extractor.extract(tokens)
        
        # Chỉ có 'xyz' được check và tính là OOV
        # '123' và 'a' không được tính vào checked_token_count
        assert res.oov_count == 1
        assert res.oov_density == 1.0  # 1 OOV / 1 Checked


# ============================================================
# TEST GROUP 2: ADVANCED MISSPELL FEATURES
# ============================================================

class TestAdvancedFeatures:
    """Tests các tính năng nâng cao: Telex, Gibberish, Repeated..."""

    def test_broken_telex(self, extractor):
        """Phát hiện lỗi bộ gõ Telex (aa, dd, ee...)"""
        # 'dduwowng' (đường), 'aam' (âm)
        tokens = ['dduwowng', 'aam', 'xin']
        res = extractor.extract(tokens)
        
        assert res.oov_count == 2
        assert res.broken_telex_count == 2
        assert 'dduwowng' in res.oov_tokens

    def test_gibberish(self, extractor):
        """Phát hiện từ vô nghĩa (không nguyên âm, consonant cluster)"""
        # 'xkqz' (no vowel), 'strng' (consonant cluster)
        tokens = ['xkqz', 'strng', 'bạn']
        res = extractor.extract(tokens)
        
        assert res.gibberish_count == 2
        assert res.oov_count == 2

    def test_repeated_chars(self, extractor):
        """Phát hiện lặp ký tự > 2 lần"""
        # 'hottt', 'ngannn'
        tokens = ['hottt', 'ngannn', 'vui']
        res = extractor.extract(tokens)
        
        assert res.repeated_char_count == 2
        assert res.oov_count == 2

    def test_run_on_words(self, extractor):
        """Phát hiện dính từ (Run-on)"""
        # 'xinchao' (xin + chao), 'nganhang' (ngan + hang)
        # Các từ đơn phải có trong mock_dicts
        tokens = ['xinchao', 'nganhang', 'unknowntoken']
        res = extractor.extract(tokens)
        
        assert res.run_on_word_count == 2
        assert res.oov_count == 3  # Vẫn là OOV nhưng được flag thêm là run-on


# ============================================================
# TEST GROUP 3: METRICS & EDGE CASES
# ============================================================

class TestMetrics:
    def test_density_calculation(self, extractor):
        """Tính toán mật độ lỗi chính xác"""
        # 2 từ đúng (xin, chao), 2 từ sai (kaka, hoho)
        tokens = ['xin', 'chao', 'kaka', 'hoho']
        res = extractor.extract(tokens)
        
        assert res.oov_count == 2
        # Density = 2 OOV / 4 Checked = 0.5
        assert res.oov_density == 0.5

    def test_density_with_ignored_tokens(self, extractor):
        """Tính mật độ không bao gồm token bị bỏ qua"""
        # 1 từ đúng (xin), 1 từ sai (kaka), 2 token bị bỏ qua (123, a)
        tokens = ['xin', 'kaka', '123', 'a']
        res = extractor.extract(tokens)
        
        # Checked tokens = ['xin', 'kaka'] (Total 2)
        # OOV = ['kaka'] (Total 1)
        assert res.oov_count == 1
        assert res.oov_density == 0.5

    def test_longest_oov(self, extractor):
        """Tìm độ dài từ OOV dài nhất"""
        tokens = ['abc', 'abcde', 'a'] 
        res = extractor.extract(tokens)
        
        # 'a' ignored. 'abc' (3) and 'abcde' (5) are OOV.
        assert res.longest_oov_length == 5


# ============================================================
# INTEGRATION TEST & EXPORT
# ============================================================

def export_misspell_results():
    """
    Chạy Layer 4 trên kết quả của Layer 3 và xuất CSV.
    Input: layer3_whitelist_results.csv
    Output: layer4_misspell_results.csv
    """
    input_file = Path("layer3_whitelist_results.csv")
    output_file = Path("layer4_misspell_results.csv")
    
    if not input_file.exists():
        print(f"⚠️ Input file not found: {input_file}")
        print("Skipping export test.")
        return

    print(f"\nLoading Layer 3 results from: {input_file}")
    df = pd.read_csv(input_file)
    
    # Init Extractor với từ điển thật (Tự động load words.txt)
    # Lưu ý: Class MisspellExtractor mặc định sẽ tự tìm file words.txt nếu không truyền tham số
    # hoặc bạn có thể trỏ đường dẫn cụ thể nếu cần.
    try:
        extractor = MisspellExtractor() 
        print(f"Dictionary loaded via Extractor logic.")
    except Exception as e:
        print(f"Error loading dictionary: {e}")
        return

    results = []
    
    print("Running Misspell Extraction...")
    
    for _, row in df.iterrows():
        # Convert string representation of list back to list
        # Layer 3 output column: 'tokens_to_check'
        tokens_str = row.get('tokens_to_check', '[]')
        try:
            tokens = ast.literal_eval(tokens_str) if isinstance(tokens_str, str) else []
        except:
            tokens = []
            
        res = extractor.extract(tokens)
        
        results.append({
            # Copy basic info
            'index': row.get('index'),
            'label': row.get('label'),
            'original_content': row.get('original_content'),
            
            # Layer 3 info
            'tokens_to_check': tokens,
            
            # Layer 4 Results
            'oov_count': res.oov_count,
            'oov_density': round(res.oov_density, 4),
            'broken_telex_count': res.broken_telex_count,
            'gibberish_count': res.gibberish_count,
            'repeated_char_count': res.repeated_char_count,
            'run_on_word_count': res.run_on_word_count,
            'longest_oov_len': res.longest_oov_length,
            'oov_tokens': res.oov_tokens
        })
    
    result_df = pd.DataFrame(results)
    result_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    print(f"\n✅ Results saved to: {output_file}")
    print(f"   Total rows processed: {len(result_df):,}")
    
    # Thống kê sơ bộ
    print("\n📊 SUMMARY STATISTICS (Layer 4):")
    print("-" * 40)
    print(f"   Avg OOV Density:        {result_df['oov_density'].mean():.4f}")
    print(f"   Avg Broken Telex:       {result_df['broken_telex_count'].mean():.2f}")
    print(f"   Avg Gibberish:          {result_df['gibberish_count'].mean():.2f}")
    print(f"   Avg Repeated Chars:     {result_df['repeated_char_count'].mean():.2f}")
    
    return result_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 4 Misspell Tests")
    parser.add_argument("--export", action="store_true", help="Export results to CSV")
    parser.add_argument("--test", action="store_true", help="Run pytest tests")
    
    args = parser.parse_args()
    
    if args.export:
        export_misspell_results()
    elif args.test:
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        # Default behavior: run export if no args
        print("Usage:")
        print("  python test_layer4.py --test    (Run Unit Tests)")
        print("  python test_layer4.py --export  (Run on Dataset & Save CSV)")
        print("\nRunning export by default...")
        export_misspell_results()