# Smishing_system/src/features.py

import re
import pandas as pd
from iocextract import extract_urls
from collections import Counter

# ==============================================================================
# DICTIONARY - TỪ ĐIỂN TỪ KHOÁ
# ==============================================================================

# 1. Từ khóa tài chính (Financial Keywords)
FINANCIAL_KEYWORDS = [
    'tiền', 'đồng', 'triệu', 'ngàn', 'chuyển khoản', 'thanh toán', 'nạp tiền',
    'rút tiền', 'số dư', 'tài khoản', 'stk', 'vcb', 'vietcombank', 'techcombank',
    'bidv', 'agribank', 'vpbank', 'acb', 'mb bank', 'ngân hàng', 'bank',
    'credit', 'debit', 'visa', 'mastercard', 'the atm', 'thẻ tín dụng',
    'vay', 'nợ', 'trả góp', 'lãi suất', 'phí', 'momo', 'zalopay', 'vnpay',
    'paytm', 'paypal', 'usdt', 'bitcoin'
]

# 2. Từ khóa khẩn cấp (Urgency Keywords)
URGENCY_KEYWORDS = [
    'gấp', 'ngay', 'nhanh', 'khẩn', 'lập tức', 'hôm nay', 'trước', 'hết hạn',
    'expired', 'bị khóa', 'bị chặn', 'cảnh báo', 'thông báo', 'warning',
    'canh bao', 'thong bao', 'gap', 'khan', 'truoc', 'het han'
]

# 3. Từ khóa hành động (Action Keywords - yêu cầu user làm gì đó)
ACTION_KEYWORDS = [
    'truy cập', 'click', 'nhấn', 'bấm', 'vào', 'kích', 'đăng nhập', 'xác nhận',
    'xác thực', 'cập nhật', 'nâng cấp', 'gia hạn', 'kích hoạt', 'liên hệ',
    'gọi', 'nhắn', 'reply', 'trả lời', 'download', 'tải', 'cài đặt',
    'đăng ký', 'hủy', 'nhận', 'dang nhap', 'xac nhan', 'lien he', 'cap nhat'
]

# 4. Từ khóa thưởng/lừa đảo (Reward/Scam Keywords)
REWARD_KEYWORDS = [
    'trúng', 'thưởng', 'may mắn', 'quà', 'khuyến mãi', 'miễn phí', 'free',
    'giảm giá', 'giá shock', 'voucher', 'coupon', 'hoàn tiền', 'cashback',
    'trung', 'thuong', 'qua', 'mien phi', 'khuyen mai'
]

# 5. Từ khóa giả mạo cơ quan (Impersonation Keywords)
IMPERSONATION_KEYWORDS = [
    'công an', 'police', 'viện kiểm sát', 'tòa án', 'court', 'bộ công an',
    'bộ gtvt', 'bộ y tế', 'cục', 'sở', 'phòng', 'cơ quan', 'chính quyền',
    'kho bạc', 'thuế', 'hải quan', 'customs', 'cảnh sát', 'vks', 
    'phcđgln', 'trung tâm', 'cong an', 'to an', 'co quan', 'canh sat'
]

# 6. Brandname ngân hàng/dịch vụ chính thức
LEGITIMATE_BRANDS = [
    'viettel', 'mobifone', 'vinaphone', 'vietnamobile', 'gmobile',
    'vnpt', 'fpt', 'vccorp', 'being', 'shopee', 'lazada', 'tiki', 
    'grab', 'gojek', 'facebook', 'zalo', 'google'
]


# ==============================================================================
# CÁC HÀM TRÍCH XUẤT ĐẶC TRƯNG
# ==============================================================================

def extract_url_features(text):
    """
    Feature 1: Đặc trưng liên quan đến URL
    
    Returns:
        dict: {
            'has_url': 0/1,
            'num_urls': int,
            'has_suspicious_domain': 0/1,
            'url_length_avg': float
        }
    """
    urls = list(extract_urls(text))
    
    features = {
        'has_url': 1 if urls else 0,
        'num_urls': len(urls),
        'has_suspicious_domain': 0,
        'url_length_avg': 0.0
    }
    
    if urls:
        # Độ dài trung bình của URL
        features['url_length_avg'] = sum(len(url) for url in urls) / len(urls)
        
        # Kiểm tra domain đáng ngờ
        suspicious_patterns = [
            r'\.xyz$', r'\.top$', r'\.club$', r'\.info$',  # TLD đáng ngờ
            r'\d+\.com',  # Domain có nhiều số: login123.com
            r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP address
            r'(login|verify|update|secure|account|bank).*\.(com|vn|net)',  # Từ đáng ngờ trong domain
            r'[a-z]{20,}',  # Domain quá dài không ngắt
        ]
        
        for url in urls:
            url_lower = url.lower()
            for pattern in suspicious_patterns:
                if re.search(pattern, url_lower):
                    features['has_suspicious_domain'] = 1
                    break
            if features['has_suspicious_domain']:
                break
    
    return features


def extract_phone_features(text):
    """
    Feature 2: Đặc trưng liên quan đến số điện thoại
    
    Returns:
        dict: {
            'has_phone': 0/1,
            'num_phones': int,
            'has_personal_phone': 0/1,  # SĐT cá nhân (không phải hotline/shortcode)
            'has_hotline': 0/1
        }
    """
    # Pattern bắt số điện thoại Việt Nam
    phone_patterns = [
        r'\b(0|\+84|84)[3-9]\d{8}\b',  # SĐT di động VN: 0912345678, +84912345678
        r'\b1[8-9]00\d{4,6}\b',  # Hotline: 1800xxxx, 1900xxxx
        r'\b0[2]\d{8,9}\b',  # Số cố định
    ]
    
    phones = []
    for pattern in phone_patterns:
        phones.extend(re.findall(pattern, text))
    
    # Loại bỏ các số không phải SĐT (OTP, mã gói, số tiền)
    valid_phones = []
    for phone in phones:
        # Loại bỏ nếu xung quanh có từ khóa chỉ số tiền, mã OTP
        context_pattern = rf'.{{0,20}}{re.escape(phone)}.{{0,20}}'
        context = re.search(context_pattern, text)
        if context:
            context_text = context.group().lower()
            # Skip nếu là mã OTP, số tiền
            if not re.search(r'(otp|ma xac thuc|mã xác thực|\d+đ|\d+vnd|gb)', context_text):
                valid_phones.append(phone)
    
    features = {
        'has_phone': 1 if valid_phones else 0,
        'num_phones': len(valid_phones),
        'has_personal_phone': 0,
        'has_hotline': 0
    }
    
    # Phân loại loại số điện thoại
    for phone in valid_phones:
        if re.match(r'1[8-9]00', phone):
            features['has_hotline'] = 1
        elif re.match(r'(0|\+84|84)[3-9]', phone):
            features['has_personal_phone'] = 1
    
    return features


def extract_text_features(text):
    """
    Feature 3: Đặc trưng từ nội dung văn bản
    
    Returns:
        dict: {
            'message_length': int,
            'num_words': int,
            'num_digits': int,
            'digit_ratio': float,  # Tỷ lệ chữ số / tổng ký tự
            'num_special_chars': int,
            'special_char_ratio': float,
            'num_uppercase': int,
            'uppercase_ratio': float,
            'has_mixed_language': 0/1  # Lẫn tiếng Việt không dấu + có dấu
        }
    """
    # Loại bỏ URL và SĐT để tính toán chính xác hơn
    text_clean = re.sub(r'http[s]?://\S+|www\.\S+', '', text)
    text_clean = re.sub(r'\b(0|\+84|84)[3-9]\d{8}\b', '', text_clean)
    
    features = {
        'message_length': len(text),
        'num_words': len(text.split()),
        'num_digits': len(re.findall(r'\d', text)),
        'digit_ratio': 0.0,
        'num_special_chars': len(re.findall(r'[^a-zA-Z0-9\sàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]', text)),
        'special_char_ratio': 0.0,
        'num_uppercase': len(re.findall(r'[A-Z]', text)),
        'uppercase_ratio': 0.0,
        'has_mixed_language': 0
    }
    
    if len(text) > 0:
        features['digit_ratio'] = features['num_digits'] / len(text)
        features['special_char_ratio'] = features['num_special_chars'] / len(text)
        features['uppercase_ratio'] = features['num_uppercase'] / len(text)
    
    # Kiểm tra mixed language (lẫn lộn tiếng Việt có dấu và không dấu)
    has_vietnamese_chars = bool(re.search(r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]', text.lower()))
    has_no_accent_vietnamese = bool(re.search(r'\b(ngan hang|tai khoan|chuyen khoan|thong bao|canh bao|xac nhan)\b', text.lower()))
    
    if has_vietnamese_chars and has_no_accent_vietnamese:
        features['has_mixed_language'] = 1
    
    return features


def extract_keyword_features(text):
    """
    Feature 4: Đặc trưng từ các từ khóa đặc biệt
    
    Returns:
        dict: {
            'num_financial_keywords': int,
            'num_urgency_keywords': int,
            'num_action_keywords': int,
            'num_reward_keywords': int,
            'num_impersonation_keywords': int,
            'has_financial_keywords': 0/1,
            'has_urgency_keywords': 0/1,
            'has_action_keywords': 0/1,
            'has_reward_keywords': 0/1,
            'has_impersonation_keywords': 0/1,
            'keyword_density': float  # Tổng số keyword / số từ
        }
    """
    text_lower = text.lower()
    
    # Đếm số lượng keywords
    financial_count = sum(1 for kw in FINANCIAL_KEYWORDS if kw in text_lower)
    urgency_count = sum(1 for kw in URGENCY_KEYWORDS if kw in text_lower)
    action_count = sum(1 for kw in ACTION_KEYWORDS if kw in text_lower)
    reward_count = sum(1 for kw in REWARD_KEYWORDS if kw in text_lower)
    impersonation_count = sum(1 for kw in IMPERSONATION_KEYWORDS if kw in text_lower)
    
    total_keywords = financial_count + urgency_count + action_count + reward_count + impersonation_count
    num_words = len(text.split())
    
    features = {
        'num_financial_keywords': financial_count,
        'num_urgency_keywords': urgency_count,
        'num_action_keywords': action_count,
        'num_reward_keywords': reward_count,
        'num_impersonation_keywords': impersonation_count,
        'has_financial_keywords': 1 if financial_count > 0 else 0,
        'has_urgency_keywords': 1 if urgency_count > 0 else 0,
        'has_action_keywords': 1 if action_count > 0 else 0,
        'has_reward_keywords': 1 if reward_count > 0 else 0,
        'has_impersonation_keywords': 1 if impersonation_count > 0 else 0,
        'keyword_density': total_keywords / num_words if num_words > 0 else 0.0
    }
    
    return features


def extract_sender_features(sender_type):
    """
    Feature 5: Đặc trưng từ loại người gửi
    
    Args:
        sender_type: 'brandname', 'shortcode', 'personal_number', 'unknown'
    
    Returns:
        dict: {
            'is_brandname': 0/1,
            'is_shortcode': 0/1,
            'is_personal_number': 0/1,
            'is_unknown': 0/1
        }
    """
    sender_type_lower = str(sender_type).lower()
    
    features = {
        'is_brandname': 1 if sender_type_lower == 'brandname' else 0,
        'is_shortcode': 1 if sender_type_lower == 'shortcode' else 0,
        'is_personal_number': 1 if sender_type_lower == 'personal_number' else 0,
        'is_unknown': 1 if sender_type_lower == 'unknown' else 0
    }
    
    return features


# ==============================================================================
# HÀM TỔNG HỢP - TRÍCH XUẤT TẤT CẢ CÁC ĐẶC TRƯNG
# ==============================================================================

def extract_all_features(text, sender_type='unknown'):
    """
    Trích xuất tất cả các đặc trưng từ một tin nhắn SMS
    
    Args:
        text (str): Nội dung tin nhắn
        sender_type (str): Loại người gửi
    
    Returns:
        dict: Dictionary chứa tất cả các features
    """
    all_features = {}
    
    # 1. URL features
    all_features.update(extract_url_features(text))
    
    # 2. Phone features
    all_features.update(extract_phone_features(text))
    
    # 3. Text features
    all_features.update(extract_text_features(text))
    
    # 4. Keyword features
    all_features.update(extract_keyword_features(text))
    
    # 5. Sender features
    all_features.update(extract_sender_features(sender_type))
    
    return all_features


def extract_features_from_dataframe(df, content_col='content', sender_col='sender_type'):
    """
    Trích xuất features cho toàn bộ DataFrame
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu SMS
        content_col (str): Tên cột chứa nội dung tin nhắn
        sender_col (str): Tên cột chứa loại người gửi
    
    Returns:
        pd.DataFrame: DataFrame với các cột features mới
    """
    features_list = []
    
    for idx, row in df.iterrows():
        text = str(row[content_col])
        sender_type = row[sender_col] if sender_col in df.columns else 'unknown'
        
        features = extract_all_features(text, sender_type)
        features_list.append(features)
    
    # Tạo DataFrame từ list of dicts
    features_df = pd.DataFrame(features_list)
    
    # Kết hợp với DataFrame gốc
    result_df = pd.concat([df.reset_index(drop=True), features_df], axis=1)
    
    return result_df


# ==============================================================================
# HÀM CHỌN TOP FEATURES (theo paper - 5 features hiệu quả nhất)
# ==============================================================================

def get_top_5_features():
    """
    Trả về danh sách 5 features quan trọng nhất (dựa trên paper và kinh nghiệm)
    
    Có thể điều chỉnh sau khi train model và feature importance analysis
    """
    return [
        'has_url',                      # Feature 1: Có URL không?
        'has_phone',                    # Feature 2: Có SĐT không?
        'num_financial_keywords',       # Feature 3: Số lượng từ khóa tài chính
        'num_urgency_keywords',         # Feature 4: Số lượng từ khóa khẩn cấp
        'is_personal_number',           # Feature 5: Gửi từ SĐT cá nhân?
    ]


def get_selected_features_df(df):
    """
    Lấy chỉ 5 features quan trọng nhất từ DataFrame đã extract
    
    Args:
        df (pd.DataFrame): DataFrame đã có tất cả features
    
    Returns:
        pd.DataFrame: DataFrame chỉ chứa 5 features chính + label (nếu có)
    """
    top_features = get_top_5_features()
    
    # Giữ lại label nếu có
    cols_to_keep = top_features.copy()
    if 'label' in df.columns:
        cols_to_keep.insert(0, 'label')
    
    return df[cols_to_keep]


# ==============================================================================
# TEST & DEMO
# ==============================================================================

if __name__ == "__main__":
    # Test với một số mẫu SMS
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
    
    print("=" * 80)
    print("FEATURE EXTRACTION DEMO")
    print("=" * 80)
    
    for idx, sample in enumerate(test_samples, 1):
        print(f"\n📩 SAMPLE {idx} - Expected: {sample['expected']}")
        print(f"Content: {sample['content'][:100]}...")
        print(f"Sender: {sample['sender_type']}")
        print("-" * 80)
        
        features = extract_all_features(sample['content'], sample['sender_type'])
        
        # In ra các features quan trọng
        print("🔍 EXTRACTED FEATURES:")
        for key, value in features.items():
            if value > 0 or key in get_top_5_features():  # Chỉ in features có giá trị hoặc thuộc top 5
                print(f"  {key:30s}: {value}")
        
        print("-" * 80)
        print(f"✅ TOP 5 FEATURES: {get_top_5_features()}")
        top_5_values = {k: features[k] for k in get_top_5_features()}
        print(f"   Values: {top_5_values}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)