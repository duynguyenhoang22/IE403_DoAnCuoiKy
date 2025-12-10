"""
Script test nhanh cho feature extraction module
Chạy file này để test xem features.py có hoạt động đúng không

Usage:
    python test_features.py
"""

import sys
sys.path.append('./src')

from features import extract_all_features, get_top_5_features

# Test samples
test_samples = [
    {
        'content': 'ACB: Tai khoan cua ban da mo dich vu tai chinh toan cau phi dich vu hang thang la 2.000.000VND se bi tru trong 2 gio .Neu khong phai ban mo dich vu vui long nhan vao https://acb-online-center.6app de huy',
        'sender_type': 'brandname',
        'expected': 'SMISHING'
    },
    {
        'content': 'Viettel thong bao: So tien tra truoc 12345 quy khach con 50.000d. Han su dung den 30/12/2025. Cam on.',
        'sender_type': 'shortcode',
        'expected': 'HAM'
    },
    {
        'content': 'Western Union TB: Vietcombank: 0071000986547. Trần Thị Lan. Ref +19.56 USD. Nhận 500.000 VND. Ngay 02/02/2025. Mgd: 1057425286. Nd: COC TIEN HANG. Quý khách nhận tiền VND vào website: https://sites.google.com/view/chuyennhantiennhanhquocte24h7',
        'sender_type': 'personal_number',
        'expected': 'SMISHING'
    }
]

def test_feature_extraction():
    """Test feature extraction cho các mẫu SMS"""
    print("=" * 80)
    print("🧪 TESTING FEATURE EXTRACTION MODULE")
    print("=" * 80)
    
    all_passed = True
    
    for idx, sample in enumerate(test_samples, 1):
        print(f"\n📩 TEST CASE {idx} - Expected: {sample['expected']}")
        print(f"Content: {sample['content'][:100]}...")
        print(f"Sender: {sample['sender_type']}")
        print("-" * 80)
        
        try:
            # Extract features
            features = extract_all_features(sample['content'], sample['sender_type'])
            
            # Kiểm tra số lượng features
            expected_feature_count = 32  # Tổng số features (4+4+9+11+4)
            actual_feature_count = len(features)
            
            if actual_feature_count != expected_feature_count:
                print(f"❌ FAILED: Expected {expected_feature_count} features, got {actual_feature_count}")
                all_passed = False
                continue
            
            print(f"✅ Extracted {actual_feature_count} features successfully!")
            
            # In ra Top 5 features
            print("\n🏆 TOP 5 FEATURES:")
            top_5 = get_top_5_features()
            for feat in top_5:
                value = features.get(feat, 'N/A')
                print(f"   • {feat:25s}: {value}")
            
            # Kiểm tra logic cơ bản
            if sample['expected'] == 'SMISHING':
                # Smishing thường có URL hoặc phone hoặc nhiều keyword
                has_indicators = (
                    features.get('has_url', 0) > 0 or 
                    features.get('has_phone', 0) > 0 or
                    features.get('num_financial_keywords', 0) > 1 or
                    features.get('num_urgency_keywords', 0) > 1
                )
                
                if has_indicators:
                    print("✅ SMISHING indicators detected correctly!")
                else:
                    print("⚠️  WARNING: Expected SMISHING but few indicators found")
            
            print("-" * 80)
            print("✅ TEST PASSED")
            
        except Exception as e:
            print(f"❌ TEST FAILED with error: {e}")
            all_passed = False
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = test_feature_extraction()
    sys.exit(0 if success else 1)

