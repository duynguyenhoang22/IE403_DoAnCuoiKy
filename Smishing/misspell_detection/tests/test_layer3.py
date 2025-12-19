"""
Test Suite for Layer 3: Whitelist Filtering
============================================
Covers:
1. Brand name filtering
2. Jargon/Technical term filtering
3. Slang/Abbreviation filtering
4. Entity token filtering
5. is_whitelisted() checks
6. filter() method
7. WhitelistResult dataclass
8. Edge cases
9. Integration with Layer 2 output
"""

import pytest
import sys
from pathlib import Path
import pandas as pd

# Setup path
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from Smishing.misspell_detection.layer3_whitelist import WhitelistFilter, WhitelistResult


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def whitelist_filter():
    """Fixture tạo WhitelistFilter instance"""
    return WhitelistFilter()


# ============================================================
# TEST GROUP 1: BRAND FILTERING
# ============================================================

class TestBrandFiltering:
    """Tests cho Brand name filtering"""
    
    def test_bank_brand_vcb(self, whitelist_filter):
        """VCB (Vietcombank) được whitelist"""
        assert whitelist_filter.is_whitelisted("vcb") == True
        assert whitelist_filter.is_whitelisted("VCB") == True  # Case insensitive
    
    def test_bank_brand_bidv(self, whitelist_filter):
        """BIDV được whitelist"""
        assert whitelist_filter.is_whitelisted("bidv") == True
    
    def test_bank_brand_vietinbank(self, whitelist_filter):
        """Vietinbank được whitelist"""
        assert whitelist_filter.is_whitelisted("vietinbank") == True
    
    def test_ewallet_brand_momo(self, whitelist_filter):
        """MoMo được whitelist"""
        assert whitelist_filter.is_whitelisted("momo") == True
    
    def test_telco_brand_viettel(self, whitelist_filter):
        """Viettel được whitelist"""
        assert whitelist_filter.is_whitelisted("viettel") == True
    
    def test_app_brand_tiktok(self, whitelist_filter):
        """TikTok được whitelist"""
        assert whitelist_filter.is_whitelisted("tiktok") == True


# ============================================================
# TEST GROUP 2: JARGON FILTERING
# ============================================================

class TestJargonFiltering:
    """Tests cho Jargon/Technical term filtering"""
    
    def test_jargon_otp(self, whitelist_filter):
        """OTP (One-Time Password) được whitelist"""
        assert whitelist_filter.is_whitelisted("otp") == True
    
    def test_jargon_sim(self, whitelist_filter):
        """SIM card được whitelist"""
        assert whitelist_filter.is_whitelisted("sim") == True
    
    def test_jargon_4g(self, whitelist_filter):
        """4G network được whitelist"""
        assert whitelist_filter.is_whitelisted("4g") == True
    
    def test_jargon_digibank(self, whitelist_filter):
        """Digibank được whitelist"""
        assert whitelist_filter.is_whitelisted("digibank") == True
    
    def test_jargon_usdt(self, whitelist_filter):
        """USDT (crypto) được whitelist"""
        assert whitelist_filter.is_whitelisted("usdt") == True


# ============================================================
# TEST GROUP 3: SLANG/ABBREVIATION FILTERING
# ============================================================

class TestSlangAbbreviationFiltering:
    """Tests cho Slang/Abbreviation filtering"""
    
    def test_abbr_lh(self, whitelist_filter):
        """LH (Liên hệ) được whitelist"""
        assert whitelist_filter.is_whitelisted("lh") == True
    
    def test_abbr_tk(self, whitelist_filter):
        """TK (Tài khoản) được whitelist"""
        assert whitelist_filter.is_whitelisted("tk") == True
    
    def test_abbr_cskh(self, whitelist_filter):
        """CSKH (Chăm sóc khách hàng) được whitelist"""
        assert whitelist_filter.is_whitelisted("cskh") == True
    
    def test_abbr_bhtn(self, whitelist_filter):
        """BHTN (Bảo hiểm thất nghiệp) được whitelist"""
        assert whitelist_filter.is_whitelisted("bhtn") == True
    
    def test_teencode_ko(self, whitelist_filter):
        """KO (Không) được whitelist"""
        assert whitelist_filter.is_whitelisted("ko") == True


# ============================================================
# TEST GROUP 4: ENTITY TOKEN FILTERING
# ============================================================

class TestEntityTokenFiltering:
    """Tests cho Entity token filtering từ Layer 1"""
    
    def test_entity_url_uppercase(self, whitelist_filter):
        """<URL> uppercase được whitelist"""
        assert whitelist_filter.is_whitelisted("<URL>") == True
    
    def test_entity_phone_uppercase(self, whitelist_filter):
        """<PHONE> uppercase được whitelist"""
        assert whitelist_filter.is_whitelisted("<PHONE>") == True
    
    def test_entity_money_lowercase(self, whitelist_filter):
        """<money> lowercase được whitelist"""
        assert whitelist_filter.is_whitelisted("<money>") == True
    
    def test_entity_app_link(self, whitelist_filter):
        """<APP_LINK> với underscore được whitelist"""
        assert whitelist_filter.is_whitelisted("<APP_LINK>") == True


# ============================================================
# TEST GROUP 5: IS_WHITELISTED CHECKS
# ============================================================

class TestIsWhitelistedChecks:
    """Tests cho 5 checks trong is_whitelisted()"""
    
    def test_check1_in_whitelist_set(self, whitelist_filter):
        """Check 1: Token có trong whitelist set"""
        assert whitelist_filter.is_whitelisted("vcb") == True
        assert whitelist_filter.is_whitelisted("xyzabc") == False  # Không có trong set
    
    def test_check2_pure_digit(self, whitelist_filter):
        """Check 2: Số thuần túy được whitelist"""
        assert whitelist_filter.is_whitelisted("123456") == True
        assert whitelist_filter.is_whitelisted("2024") == True
        assert whitelist_filter.is_whitelisted("0") == True
    
    def test_check3_entity_tag(self, whitelist_filter):
        """Check 3: Entity tag <...> được whitelist"""
        assert whitelist_filter.is_whitelisted("<CUSTOM_TAG>") == True
        assert whitelist_filter.is_whitelisted("<anything>") == True
    
    def test_check4_short_token(self, whitelist_filter):
        """Check 4: Token ≤1 ký tự được whitelist"""
        assert whitelist_filter.is_whitelisted("a") == True
        assert whitelist_filter.is_whitelisted("1") == True
        assert whitelist_filter.is_whitelisted("") == True
    
    def test_check5_special_chars_only(self, whitelist_filter):
        """Check 5: Token chỉ có ký tự đặc biệt được whitelist"""
        assert whitelist_filter.is_whitelisted("---") == True
        assert whitelist_filter.is_whitelisted("...") == True
        assert whitelist_filter.is_whitelisted("***") == True
    
    def test_vietnamese_word_not_whitelisted(self, whitelist_filter):
        """Từ tiếng Việt bình thường KHÔNG được whitelist"""
        assert whitelist_filter.is_whitelisted("thong") == False
        assert whitelist_filter.is_whitelisted("bao") == False
        assert whitelist_filter.is_whitelisted("khoan") == False
        assert whitelist_filter.is_whitelisted("tai") == False


# ============================================================
# TEST GROUP 6: FILTER METHOD
# ============================================================

class TestFilterMethod:
    """Tests cho filter() method"""
    
    def test_filter_mixed_tokens(self, whitelist_filter):
        """Filter tokens hỗn hợp"""
        tokens = ['vcb', 'thong', 'bao', 'tai', 'khoan', '<URL>']
        result = whitelist_filter.filter(tokens)
        
        assert 'vcb' in result.whitelisted_tokens
        assert '<URL>' in result.whitelisted_tokens
        assert 'thong' in result.tokens_to_check
        assert 'bao' in result.tokens_to_check
    
    def test_filter_all_whitelisted(self, whitelist_filter):
        """Tất cả tokens đều whitelist"""
        tokens = ['vcb', 'otp', '<PHONE>', '123456']
        result = whitelist_filter.filter(tokens)
        
        assert len(result.tokens_to_check) == 0
        assert len(result.whitelisted_tokens) == 4
    
    def test_filter_none_whitelisted(self, whitelist_filter):
        """Không có token nào whitelist"""
        tokens = ['chao', 'ban', 'khoe', 'khong']
        result = whitelist_filter.filter(tokens)
        
        assert len(result.tokens_to_check) == 4
        assert len(result.whitelisted_tokens) == 0
    
    def test_filter_whitelist_count(self, whitelist_filter):
        """whitelist_count đúng"""
        tokens = ['vcb', 'thong', 'bao', 'otp', '<URL>']
        result = whitelist_filter.filter(tokens)
        
        # vcb, otp, <URL> = 3 whitelisted
        assert result.whitelist_count == 3
    
    def test_filter_original_tokens_preserved(self, whitelist_filter):
        """original_tokens được giữ nguyên"""
        tokens = ['vcb', 'thong', 'bao']
        result = whitelist_filter.filter(tokens)
        
        assert result.original_tokens == tokens


# ============================================================
# TEST GROUP 7: WHITELIST RESULT
# ============================================================

class TestWhitelistResult:
    """Tests cho WhitelistResult dataclass"""
    
    def test_result_has_all_fields(self, whitelist_filter):
        """Result có đủ các fields"""
        tokens = ['test']
        result = whitelist_filter.filter(tokens)
        
        assert hasattr(result, 'tokens_to_check')
        assert hasattr(result, 'whitelisted_tokens')
        assert hasattr(result, 'whitelist_count')
        assert hasattr(result, 'original_tokens')
    
    def test_result_types(self, whitelist_filter):
        """Kiểm tra types của các fields"""
        tokens = ['vcb', 'test']
        result = whitelist_filter.filter(tokens)
        
        assert isinstance(result.tokens_to_check, list)
        assert isinstance(result.whitelisted_tokens, list)
        assert isinstance(result.whitelist_count, int)
        assert isinstance(result.original_tokens, list)
    
    def test_result_empty_input(self, whitelist_filter):
        """Result với empty input"""
        result = whitelist_filter.filter([])
        
        assert result.tokens_to_check == []
        assert result.whitelisted_tokens == []
        assert result.whitelist_count == 0
        assert result.original_tokens == []
    
    def test_result_is_dataclass(self, whitelist_filter):
        """Result là dataclass instance"""
        tokens = ['test']
        result = whitelist_filter.filter(tokens)
        
        assert isinstance(result, WhitelistResult)


# ============================================================
# TEST GROUP 8: EDGE CASES
# ============================================================

class TestEdgeCases:
    """Tests cho các edge cases"""
    
    def test_empty_list(self, whitelist_filter):
        """Empty token list"""
        result = whitelist_filter.filter([])
        assert result.tokens_to_check == []
        assert result.whitelist_count == 0
    
    def test_whitespace_token(self, whitelist_filter):
        """Token có whitespace"""
        assert whitelist_filter.is_whitelisted("  vcb  ") == True  # strip() xử lý
    
    def test_case_insensitive(self, whitelist_filter):
        """Case insensitive lookup"""
        assert whitelist_filter.is_whitelisted("VCB") == True
        assert whitelist_filter.is_whitelisted("vcb") == True
        assert whitelist_filter.is_whitelisted("Vcb") == True
    
    def test_mixed_alphanumeric(self, whitelist_filter):
        """Token có cả chữ và số (không thuần số)"""
        # Những token như "abc123" không phải số thuần, cũng không trong whitelist
        assert whitelist_filter.is_whitelisted("abc123") == False
        assert whitelist_filter.is_whitelisted("4g") == True  # Trong jargon list
    
    def test_unicode_vietnamese(self, whitelist_filter):
        """Token tiếng Việt có dấu"""
        # Từ có dấu không trong whitelist -> cần check chính tả
        assert whitelist_filter.is_whitelisted("tài") == False
        assert whitelist_filter.is_whitelisted("khoản") == False


# ============================================================
# TEST GROUP 9: INTEGRATION WITH LAYER 2
# ============================================================

class TestIntegrationWithLayer2:
    """Tests với output thực từ Layer 2"""
    
    def test_real_smishing_tokens_1(self, whitelist_filter):
        """Tokens từ SMS smishing ngân hàng"""
        # Simulated output from Layer 2
        tokens = ['vcb', 'thong', 'bao', 'tai', 'khoan', 'cua', 'ban', '<URL>']
        result = whitelist_filter.filter(tokens)
        
        # vcb và <URL> được whitelist
        assert 'vcb' in result.whitelisted_tokens
        assert '<URL>' in result.whitelisted_tokens
        # Các từ tiếng Việt cần check
        assert 'thong' in result.tokens_to_check
        assert 'bao' in result.tokens_to_check
    
    def test_real_smishing_tokens_2(self, whitelist_filter):
        """Tokens từ SMS smishing với OTP"""
        tokens = ['ma', 'otp', 'cua', 'ban', 'la', '123456', 'het', 'han']
        result = whitelist_filter.filter(tokens)
        
        # otp và 123456 được whitelist
        assert 'otp' in result.whitelisted_tokens
        assert '123456' in result.whitelisted_tokens
        # Các từ khác cần check
        assert 'ma' in result.tokens_to_check
        assert 'het' in result.tokens_to_check
    
    def test_real_smishing_tokens_3(self, whitelist_filter):
        """Tokens từ SMS smishing BHTN"""
        tokens = ['ong', 'ba', 'da', 'du', 'dieu', 'kien', 'bhtn', '<URL>']
        result = whitelist_filter.filter(tokens)
        
        # bhtn và <URL> được whitelist
        assert 'bhtn' in result.whitelisted_tokens
        assert '<URL>' in result.whitelisted_tokens
        assert result.whitelist_count == 2
    
    def test_real_ham_tokens(self, whitelist_filter):
        """Tokens từ SMS bình thường (ham)"""
        tokens = ['chao', 'ban', 'dao', 'nay', 'khoe', 'khong']
        result = whitelist_filter.filter(tokens)
        
        # Không có token nào đặc biệt -> tất cả cần check
        assert result.whitelist_count == 0
        assert len(result.tokens_to_check) == 6


# ============================================================
# EXPORT RESULTS
# ============================================================

def export_whitelist_results():
    """
    Chạy whitelist filtering trên dataset đã qua Layer 2 và xuất ra CSV.
    """
    print("=" * 60)
    print("EXPORT LAYER 3 WHITELIST FILTERING RESULTS")
    print("=" * 60)
    
    # Setup paths
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
    LAYER2_RESULTS = Path(__file__).resolve().parent / "layer2_normalization_results.csv"
    OUTPUT_FILE = Path(__file__).resolve().parent / "layer3_whitelist_results.csv"
    
    # Check if Layer 2 results exist
    if not LAYER2_RESULTS.exists():
        print(f"❌ Layer 2 results not found: {LAYER2_RESULTS}")
        print("   Please run Layer 2 export first.")
        return
    
    # Load Layer 2 results
    print(f"\n📂 Loading Layer 2 results from: {LAYER2_RESULTS}")
    df = pd.read_csv(LAYER2_RESULTS)
    print(f"✅ Loaded {len(df):,} rows")
    
    # Initialize filter
    whitelist_filter = WhitelistFilter()
    print(f"✓ Whitelist loaded: {len(whitelist_filter.whitelist)} items")
    
    # Process each row
    print(f"\n🔄 Processing {len(df):,} rows...")
    
    results = []
    for idx, row in df.iterrows():
        # Parse tokens from Layer 2 (stored as string representation of list)
        try:
            tokens_str = row.get("layer2_tokens", "[]")
            tokens = eval(tokens_str) if isinstance(tokens_str, str) else []
        except:
            tokens = []
        
        # Apply whitelist filter
        result = whitelist_filter.filter(tokens)
        
        # Build result row
        result_row = {
            "index": row.get("index", idx),
            "label": row.get("label", ""),
            "original_content": row.get("original_content", ""),
            "layer2_tokens": tokens_str,
            "tokens_to_check": str(result.tokens_to_check),
            "whitelisted_tokens": str(result.whitelisted_tokens),
            "whitelist_count": result.whitelist_count,
            "tokens_to_check_count": len(result.tokens_to_check),
        }
        results.append(result_row)
        
        if (idx + 1) % 500 == 0:
            print(f"   Processed {idx + 1:,} / {len(df):,} rows...")
    
    # Save results
    result_df = pd.DataFrame(results)
    result_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    
    print(f"\n✅ Results saved to: {OUTPUT_FILE}")
    print(f"   Total rows: {len(result_df):,}")
    
    # Statistics
    print("\n📊 SUMMARY STATISTICS:")
    print("-" * 40)
    print(f"   Total whitelist count:    {result_df['whitelist_count'].sum():,}")
    print(f"   Total tokens to check:    {result_df['tokens_to_check_count'].sum():,}")
    print(f"   Avg whitelist per msg:    {result_df['whitelist_count'].mean():.2f}")
    print(f"   Avg tokens to check:      {result_df['tokens_to_check_count'].mean():.2f}")
    
    return result_df


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 3 Whitelist Tests")
    parser.add_argument("--export", action="store_true", help="Export results to CSV")
    parser.add_argument("--test", action="store_true", help="Run pytest tests")
    
    args = parser.parse_args()
    
    if args.export:
        export_whitelist_results()
    elif args.test:
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("Usage:")
        print("  python test_layer3.py --test     # Chạy pytest")
        print("  python test_layer3.py --export   # Xuất results CSV")
        print("\nRunning default: --test")
        pytest.main([__file__, "-v", "--tb=short"])