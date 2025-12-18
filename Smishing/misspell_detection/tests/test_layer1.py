"""
test_layer1.py
==============
Unit tests và Integration tests cho Layer 1: Aggressive Masking

Chạy tests:
    pytest tests/test_layer1.py -v
    pytest tests/test_layer1.py -v -k "test_url"  # Chỉ chạy test URL
"""

import pytest
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# === SETUP PATH ===
# Thêm path để import được các module
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent  # IE403_DoAnCuoiKy/
sys.path.insert(0, str(ROOT_DIR))

from Smishing.misspell_detection.layer1_masking import AggressiveMasker
from Smishing.data_loader import load_dataset, DataLoader


# === FIXTURES ===
@pytest.fixture
def masker():
    """Tạo instance của AggressiveMasker cho mỗi test"""
    return AggressiveMasker()


@pytest.fixture
def sample_dataset():
    """Load dataset thực để test integration"""
    data_path = ROOT_DIR / "data" / "dataset.csv"
    if data_path.exists():
        return load_dataset(data_path)
    return None


# ============================================================
# UNIT TESTS - Test từng loại entity riêng biệt
# ============================================================

class TestURLMasking:
    """Tests cho URL masking"""
    
    def test_standard_url_with_https(self, masker):
        text = "Truy cap https://example.com de xem"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
        assert "url" in meta
    
    def test_standard_url_with_www(self, masker):
        text = "Truy cap www.example.com de xem"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
    
    def test_url_shortener_bitly(self, masker):
        text = "Click bit.ly/abc123 ngay"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
    
    def test_aggressive_url_with_spaces(self, masker):
        """URL có khoảng trắng cố ý - QUAN TRỌNG cho spam detection"""
        text = "Truy cap banca . com de nhan thuong"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
        assert "banca . com" not in masked
    
    def test_spam_tld_icu(self, masker):
        text = "Vao ngay www.scam.icu de nhan"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
    
    def test_spam_tld_vip(self, masker):
        text = "Link: abc.vip de trung thuong"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
    
    def test_multiple_urls(self, masker):
        text = "Vao https://a.com hoac https://b.com"
        masked, meta = masker.mask(text)
        assert masked.count("<URL>") == 2


class TestZaloTelegramMasking:
    """Tests cho Zalo/Telegram link masking"""
    
    def test_zalo_link(self, masker):
        text = "Lien he zalo.me/0912345678"
        masked, meta = masker.mask(text)
        assert "<APP_LINK>" in masked
        assert "zalo" in meta
    
    def test_telegram_link(self, masker):
        text = "Join t.me/groupname"
        masked, meta = masker.mask(text)
        assert "<APP_LINK>" in masked
        assert "telegram" in meta


class TestPhoneMasking:
    """Tests cho Phone number masking"""
    
    def test_mobile_standard(self, masker):
        text = "Goi 0901234567 ngay"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked
        assert "mobile" in meta
    
    def test_mobile_with_country_code(self, masker):
        text = "Goi +84901234567 de duoc ho tro"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked
    
    def test_mobile_with_dots(self, masker):
        text = "SDT: 0901.234.567"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked
    
    def test_hotline_1900(self, masker):
        text = "Goi hotline 19001009 de duoc ho tro"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked
        assert "hotline" in meta
    
    def test_hotline_with_spaces(self, masker):
        text = "Goi 1900 54 54 15 de duoc tu van"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked
    
    def test_landline(self, masker):
        text = "Van phong: 02438383838"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked
        assert "landline" in meta
    
    def test_shortcode(self, masker):
        text = "Soan TIN gui 9029"
        masked, meta = masker.mask(text)
        assert "<PHONE>" in masked


class TestMoneyMasking:
    """Tests cho Money masking"""
    
    def test_money_with_k(self, masker):
        text = "Nhan ngay 500k"
        masked, meta = masker.mask(text)
        assert "<MONEY>" in masked
        assert "money" in meta
    
    def test_money_with_trieu(self, masker):
        text = "Giai thuong 5 triệu dong"
        masked, meta = masker.mask(text)
        assert "<MONEY>" in masked
    
    def test_money_with_vnd(self, masker):
        text = "Thanh toan 500.000VND"
        masked, meta = masker.mask(text)
        assert "<MONEY>" in masked
    
    def test_money_with_dong(self, masker):
        text = "Chi phi 100.000 đồng"
        masked, meta = masker.mask(text)
        assert "<MONEY>" in masked
    
    def test_multiple_money(self, masker):
        text = "Tu 500k den 1 triệu"
        masked, meta = masker.mask(text)
        assert masked.count("<MONEY>") == 2


class TestCodeOTPMasking:
    """Tests cho Code/OTP masking"""
    
    def test_otp_6_digits(self, masker):
        text = "Ma OTP cua ban la 123456"
        masked, meta = masker.mask(text)
        assert "<CODE>" in masked
        assert "code" in meta
    
    def test_otp_4_digits(self, masker):
        text = "Ma xac thuc: 5993"
        masked, meta = masker.mask(text)
        assert "<CODE>" in masked
    
    def test_service_code(self, masker):
        text = "Soan ST5K gui 9029"
        masked, meta = masker.mask(text)
        assert "<CODE>" in masked
    
    def test_exclude_year(self, masker):
        """Năm sinh không nên bị mask"""
        text = "Sinh nam 1990 tai Ha Noi"
        masked, meta = masker.mask(text)
        assert "1990" in masked  # Năm phải được giữ lại
    
    def test_exclude_year_2000s(self, masker):
        text = "Sinh nam 2024"
        masked, meta = masker.mask(text)
        assert "2024" in masked


class TestDateTimeMasking:
    """Tests cho DateTime masking"""
    
    def test_date_dd_mm(self, masker):
        text = "Gap nhau ngay 15/05 nhe"
        masked, meta = masker.mask(text)
        assert "<TIME>" in masked
        assert "datetime" in meta
    
    def test_time_hh_mm(self, masker):
        text = "Hen luc 10h30"
        masked, meta = masker.mask(text)
        assert "<TIME>" in masked
    
    def test_duration_minutes(self, masker):
        text = "Het han sau 5 phút"
        masked, meta = masker.mask(text)
        assert "<TIME>" in masked


class TestEmailMasking:
    """Tests cho Email masking"""
    
    def test_standard_email(self, masker):
        text = "Lien he email@example.com"
        masked, meta = masker.mask(text)
        assert "<EMAIL>" in masked
        assert "email" in meta


# ============================================================
# INTEGRATION TESTS - Test với dữ liệu thực
# ============================================================

class TestIntegrationWithDataset:
    """Tests tích hợp với dataset thực"""
    
    def test_load_dataset(self, sample_dataset):
        """Test load dataset thành công"""
        if sample_dataset is None:
            pytest.skip("Dataset không tồn tại")
        
        assert len(sample_dataset) > 0
        assert "content" in sample_dataset.columns
    
    def test_mask_real_samples(self, masker, sample_dataset):
        """Test mask trên một số mẫu thực"""
        if sample_dataset is None:
            pytest.skip("Dataset không tồn tại")
        
        # Lấy 10 mẫu đầu tiên
        for idx, row in sample_dataset.head(10).iterrows():
            content = row["content"]
            masked, meta = masker.mask(content)
            
            # Đảm bảo không crash
            assert isinstance(masked, str)
            assert isinstance(meta, dict)
    
    def test_mask_batch_performance(self, masker, sample_dataset):
        """Test hiệu suất mask batch"""
        if sample_dataset is None:
            pytest.skip("Dataset không tồn tại")
        
        texts = sample_dataset["content"].head(100).tolist()
        masked_texts, metas = masker._mask_batch(texts)
        
        assert len(masked_texts) == len(texts)
        assert len(metas) == len(texts)
    
    def test_entity_counts(self, masker, sample_dataset):
        """Test đếm entity"""
        if sample_dataset is None:
            pytest.skip("Dataset không tồn tại")
        
        text = sample_dataset["content"].iloc[0]
        masked, meta = masker.mask(text)
        counts = masker.get_entity_counts(meta)
        
        assert isinstance(counts, dict)
        for key, val in counts.items():
            assert isinstance(val, int)
            assert val >= 0


# ============================================================
# EDGE CASES & REGRESSION TESTS
# ============================================================

class TestEdgeCases:
    """Tests cho các trường hợp đặc biệt"""
    
    def test_empty_string(self, masker):
        masked, meta = masker.mask("")
        assert masked == ""
        assert meta == {}
    
    def test_none_handling(self, masker):
        """Test xử lý None - có thể cần thêm logic"""
        # Hiện tại code sẽ crash nếu input là None
        # Có thể skip hoặc expect exception
        pass
    
    def test_unicode_vietnamese(self, masker):
        """Test với text tiếng Việt có dấu"""
        text = "Xin chào, mời bạn truy cập https://example.vn"
        masked, meta = masker.mask(text)
        assert "<URL>" in masked
        assert "Xin chào" in masked  # Phần text tiếng Việt được giữ nguyên
    
    def test_gibberish_text(self, masker):
        """Test với text rác/gibberish từ spam"""
        text = "j)t.ly/Q5YuG Um Cu,u~Th,ua8% ZJ Na.pVao"
        masked, meta = masker.mask(text)
        # Đảm bảo không crash
        assert isinstance(masked, str)
    
    def test_combined_entities(self, masker):
        """Test tin nhắn có nhiều loại entity"""
        text = "ACB: Dang nhap https://acb.vn de nhan 500k. LH: 0901234567"
        masked, meta = masker.mask(text)
        
        assert "<URL>" in masked
        assert "<MONEY>" in masked
        assert "<PHONE>" in masked


# ============================================================
# EXPORT RESULTS - Xuất kết quả ra file để kiểm tra
# ============================================================

import pandas as pd
from datetime import datetime

def export_masking_results():
    """
    Chạy masking trên toàn bộ dataset và xuất ra file CSV để đối chiếu.
    
    Output: tests/layer1_masking_results.csv
    """
    print("=" * 60)
    print("EXPORT LAYER 1 MASKING RESULTS")
    print("=" * 60)
    
    # Setup paths
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
    DATA_PATH = ROOT_DIR / "data" / "dataset.csv"
    OUTPUT_DIR = Path(__file__).resolve().parent  # Thư mục tests/
    OUTPUT_FILE = OUTPUT_DIR / "layer1_masking_results.csv"
    
    # Load dataset
    print(f"\n📂 Loading dataset from: {DATA_PATH}")
    try:
        df = load_dataset(DATA_PATH)
        print(f"✅ Loaded {len(df):,} rows")
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        return
    
    # Initialize masker
    masker = AggressiveMasker()
    
    # Process each row
    print(f"\n🔄 Processing {len(df):,} rows...")
    
    results = []
    for idx, row in df.iterrows():
        content = row.get("content", "")
        label = row.get("label", "")
        
        # Mask the content
        try:
            masked_text, metadata = masker.mask(str(content))
            counts = masker.get_entity_counts(metadata)
        except Exception as e:
            masked_text = f"ERROR: {e}"
            metadata = {}
            counts = {}
        
        # Build result row
        result = {
            "index": idx,
            "label": label,
            "original_content": content,
            "masked_content": masked_text,
            # Entity counts
            "url_count": counts.get("url", 0) + counts.get("zalo", 0) + counts.get("telegram", 0),
            "phone_count": counts.get("hotline", 0) + counts.get("landline", 0) + 
                          counts.get("mobile", 0) + counts.get("shortcode", 0),
            "money_count": counts.get("money", 0),
            "code_count": counts.get("code", 0),
            "email_count": counts.get("email", 0),
            "datetime_count": counts.get("datetime", 0),
            # Raw metadata (for debugging)
            "raw_metadata": str(metadata),
        }
        results.append(result)
        
        # Progress indicator
        if (idx + 1) % 500 == 0:
            print(f"   Processed {idx + 1:,} / {len(df):,} rows...")
    
    # Create DataFrame and save
    result_df = pd.DataFrame(results)
    
    # Save to CSV
    result_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ Results saved to: {OUTPUT_FILE}")
    print(f"   Total rows: {len(result_df):,}")
    
    # Print summary statistics
    print("\n📊 SUMMARY STATISTICS:")
    print("-" * 40)
    print(f"   URLs detected:      {result_df['url_count'].sum():,}")
    print(f"   Phones detected:    {result_df['phone_count'].sum():,}")
    print(f"   Money detected:     {result_df['money_count'].sum():,}")
    print(f"   Codes detected:     {result_df['code_count'].sum():,}")
    print(f"   Emails detected:    {result_df['email_count'].sum():,}")
    print(f"   DateTimes detected: {result_df['datetime_count'].sum():,}")
    
    # Show sample rows
    print("\n📋 SAMPLE RESULTS (first 5 rows):")
    print("-" * 40)
    for _, row in result_df.head(5).iterrows():
        print(f"\n[{row['index']}] Label: {row['label']}")
        print(f"   Original: {row['original_content'][:80]}...")
        print(f"   Masked:   {row['masked_content'][:80]}...")
    
    return result_df


def export_comparison_view():
    """
    Xuất ra file dễ đọc hơn: chỉ có original vs masked để so sánh nhanh.
    
    Output: tests/layer1_comparison.csv
    """
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
    DATA_PATH = ROOT_DIR / "data" / "dataset.csv"
    OUTPUT_DIR = Path(__file__).resolve().parent
    OUTPUT_FILE = OUTPUT_DIR / "layer1_comparison.csv"
    
    print("\n" + "=" * 60)
    print("EXPORT COMPARISON VIEW")
    print("=" * 60)
    
    df = load_dataset(DATA_PATH)
    masker = AggressiveMasker()
    
    # Chỉ lấy các cột cần thiết
    comparison = []
    for idx, row in df.iterrows():
        content = str(row.get("content", ""))
        masked, meta = masker.mask(content)
        
        # Kiểm tra có thay đổi không
        has_changes = masked != content
        
        comparison.append({
            "index": idx,
            "label": row.get("label", ""),
            "has_changes": has_changes,
            "original": content,
            "masked": masked,
        })
    
    result_df = pd.DataFrame(comparison)
    result_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    
    # Thống kê
    changed_count = result_df["has_changes"].sum()
    print(f"\n✅ Comparison saved to: {OUTPUT_FILE}")
    print(f"   Rows with changes: {changed_count:,} / {len(result_df):,} ({changed_count/len(result_df)*100:.1f}%)")
    
    return result_df


# ============================================================
# RUN TESTS DIRECTLY (optional)
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1 Masking Tests")
    parser.add_argument("--export", action="store_true", help="Export masking results to CSV")
    parser.add_argument("--compare", action="store_true", help="Export comparison view to CSV")
    parser.add_argument("--test", action="store_true", help="Run pytest tests")
    
    args = parser.parse_args()
    
    if args.export:
        export_masking_results()
    elif args.compare:
        export_comparison_view()
    elif args.test:
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        # Mặc định: chạy export
        print("Usage:")
        print("  python test_layer1.py --export   # Xuất full results")
        print("  python test_layer1.py --compare  # Xuất comparison view")
        print("  python test_layer1.py --test     # Chạy pytest")
        print("\nRunning default: --export")
        export_masking_results()