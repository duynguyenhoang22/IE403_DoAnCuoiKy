from dataclasses import dataclass

@dataclass
class WhitelistResult:
    """Kết quả filter whitelist - tương tự NormalizationResult của Layer 2"""
    tokens_to_check: list[str]      # Tokens cần kiểm tra chính tả
    whitelisted_tokens: list[str]   # Tokens đã bị lọc (không cần check)
    whitelist_count: int = 0        # Feature: số tokens trong whitelist
    original_tokens: list[str] = None  # Tokens gốc từ input


class WhitelistFilter:
    """
    Tầng 3: Whitelist Filtering
    Lọc bỏ các token hợp lệ không cần kiểm tra chính tả
    """
    
    def __init__(self, custom_whitelist_path=None):
        # Khởi tạo các danh sách whitelist theo category
        self.brand_list = self._build_brand_list()
        self.jargon_list = self._build_jargon_list()
        self.slang_abbr_list = self._build_slang_abbr_list()
        self.entity_tokens = self._build_entity_tokens()
        
        # Gộp tất cả thành một set để tra cứu O(1)
        self.whitelist = set()
        self.whitelist.update(self.brand_list)
        self.whitelist.update(self.jargon_list)
        self.whitelist.update(self.slang_abbr_list)
        self.whitelist.update(self.entity_tokens)
        
        # Load custom whitelist nếu có
        if custom_whitelist_path:
            self._load_custom_whitelist(custom_whitelist_path)

    # ... các method _build_*() và filter()
    def is_whitelisted(self, token: str) -> bool:
        token_lower = token.lower().strip()
        
        # Check 1: Có trong whitelist set không? (O(1) lookup)
        # VD: "vcb", "otp", "sim" → True
        if token_lower in self.whitelist:
            return True
        
        # Check 2: Là số thuần túy không?
        # VD: "123456", "2024" → True
        # Lý do: Số đã được Layer 1 xử lý (OTP, năm...), còn lại là noise
        if token_lower.isdigit():
            return True
        
        # Check 3: Là entity tag <...> không?
        # VD: "<URL>", "<PHONE>" → True
        if token.startswith('<') and token.endswith('>'):
            return True
        
        # Check 4: Token quá ngắn (≤1 ký tự)?
        # VD: "a", "b", "1" → True
        # Lý do: Noise, không có ý nghĩa chính tả
        if len(token_lower) <= 1:
            return True
        
        # Check 5: Không chứa chữ/số nào?
        # VD: "---", "..." → True
        if not any(c.isalnum() for c in token):
            return True
        
        return False

    def _build_brand_list(self):
        """
        Suy luận: Tên thương hiệu xuất hiện trong SMS nhưng KHÔNG có trong từ điển TV
        """
        return {
            # === NGÂN HÀNG (Xuất hiện nhiều trong smishing) ===
            'vcb', 'vietcombank', 'acb', 'bidv', 'vietinbank', 'techcombank', 
            'tcb', 'mbbank', 'mb', 'tpbank', 'vpbank', 'sacombank', 'shb',
            'hdbank', 'ocb', 'msb', 'agribank', 'pvcombank',
            
            # === VÍ ĐIỆN TỬ / FINTECH ===
            'momo', 'zalopay', 'viettelpay', 'vnpay', 'shoppeepay',
            'fecredit', 'homecredit',  # Hay xuất hiện trong SMS đòi nợ
            
            # === VIỄN THÔNG ===
            'viettel', 'vinaphone', 'mobifone', 'vietnamobile',
            
            # === E-COMMERCE / APPS ===
            'shopee', 'lazada', 'tiki', 'grab', 'gojek', 'be',
            'tiktok', 'facebook', 'fb', 'zalo', 'telegram',
            
            # === THƯƠNG HIỆU KHÁC ===
            'apple', 'iphone', 'samsung', 'vingroup', 'vinfast', 'viettel', 'money',
            'vnpt', 'vina', 'vinaphone' 'mobi', 'mobiphone','fpt', 'post', 'myvt', 
            'myvnpt', 'myviettel', 'vietteltt', 'tv360', 'fptplay', 'steam', 'riot',
            'vneid', 'evnhcmc',
            'google', 'netflix', 'instagram'
        }

    
    def _build_jargon_list(self):
        """
        Suy luận: Thuật ngữ chuyên ngành mà người dùng SMS hiểu nhưng không có trong từ điển
        """
        return {
            # === VIỄN THÔNG (Xuất hiện trong SMS nhà mạng) ===
            'sim', '3g', '4g', '5g', 'lte', 'data', 'wifi', 'roaming',
            
            # === TÀI CHÍNH (Xuất hiện trong SMS ngân hàng) ===
            'otp', 'pin', 'atm', 'pos', 'qr', 'visa', 'mastercard',
            'digibank', 'smartbanking', 'ebanking', 'ibanking',
            
            # === CRYPTO (SMS lừa đảo crypto) ===
            'usdt', 'btc', 'eth', 'crypto', 'blockchain',
            
            # === IT / APP ===
            'app', 'web', 'link', 'url', 'online', 'offline',
            'download', 'update', 'login', 'logout',

            'sms', 'voucher', 'data', 
            'gb', 'mb', 'otp', 'link', 
            'app', 'web', 'page', 'https'
        }

    def _build_slang_abbr_list(self):
        """
        Suy luận: Viết tắt phổ biến trong SMS tiếng Việt + một số từ tiếng Anh khác
        Nguồn: Quan sát từ dữ liệu thực tế
        """
        return {
            # === VIẾT TẮT PHỔ BIẾN (Xuất hiện nhiều trong data) ===
            'tb', 'qc', 'tkc'  # Thông báo, quảng cáo, tài khoản chính - xuất hiện nhiều trong các tin nhắn từ nhà mạng
            'lh',    # Liên hệ
            'tc', 'tc1', 'tc2', 'tc3', # Cú pháp từ chối 
            'sdt', 'đt', 'dt', 'sđt', # Số điện thoại
            'tk', 'stk',  # Tài khoản
            'tt',    # Thanh toán / Thông tin
            'cskh',  # Chăm sóc khách hàng
            'bhtn', 'bhxh', 'bhyt',  # Bảo hiểm
            'cmnd', 'cccd',  # Chứng minh/Căn cước
            'nd', 'mgd', 'ref',  # Nội dung, mã giao dịch
            'cty',   # Công ty
            'yc', # yêu cầu
            'tp', # thành phố
            'hcm', #hồ chí minh
            'bhxh', 'bhyt', 'bhtn', # bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp
            'cmnd', 'cccd', # chứng minh nhân dân, căn cước công dân
            'gplx', # giấy phép lái xe
            'cntt', 'dh'

            # === TEENCODE PHỔ BIẾN ===
            'ko', 'k',    # Không
            'dc', 'đc',   # Được  
            'r',          # Rồi
            'bn',         # Bạn
            'ok', 'okie', 'oke', 'okay', 'dk', 'hsd', 
            'qk', 'gd', 'dv', 'dh', 'kh', 'nv', 'lh',
            'hs', 'thpt', 'thcs'

            # === TIẾNG ANH ===
            'ref', 'sms', 'verify', 'code', 'bank', 'transfer', 'verification', 'send', 'transaction',
            'mobile', 'phone', 'number', 'tel', 'call', 'contact', 'covid', 'website', 
            
            
            'big', 'airtime' # Quan sát từ bộ dữ liệu thì bigXX thường là cú pháp của 1 gói dịch vụ, airtime là một dịch vụ ứng tiền thường xuyên gửi tn cho ng dùng. 
            
            }

    def _build_entity_tokens(self):
        """
        Các token entity từ Layer 1 - LUÔN whitelist
        """
        return {
            '<url>', '<phone>', '<money>', '<code>', '<time>',
            '<email>', '<app_link>',
            # Cả dạng viết hoa (để an toàn)
            '<URL>', '<PHONE>', '<MONEY>', '<CODE>', '<TIME>',
            '<EMAIL>', '<APP_LINK>',
        }
        
    def _load_custom_whitelist(self, path: str):
        """Load whitelist tùy chỉnh từ file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().lower()
                    # Bỏ qua dòng trống và comment
                    if word and not word.startswith('#'):
                        self.whitelist.add(word)
            print(f"✓ Custom whitelist loaded from: {path}")
        except FileNotFoundError:
            print(f"⚠ Warning: Custom whitelist not found: {path}")

    def filter(self, tokens: list[str]) -> WhitelistResult:
        """
        Lọc danh sách tokens, trả về tokens cần kiểm tra chính tả
        
        Args:
            tokens: List các tokens từ Layer 2
            
        Returns:
            WhitelistResult với tokens_to_check và whitelisted_tokens
        """
        if not tokens:
            return WhitelistResult(
                tokens_to_check=[],
                whitelisted_tokens=[],
                whitelist_count=0,
                original_tokens=[]
            )
        
        tokens_to_check = []
        whitelisted_tokens = []
        
        for token in tokens:
            if self.is_whitelisted(token):
                whitelisted_tokens.append(token)
            else:
                tokens_to_check.append(token)
        
        return WhitelistResult(
            tokens_to_check=tokens_to_check,
            whitelisted_tokens=whitelisted_tokens,
            whitelist_count=len(whitelisted_tokens),
            original_tokens=list(tokens)  # Copy để tránh mutation
        )

# --- TEST ---
if __name__ == "__main__":
    whitelist_filter = WhitelistFilter()
    
    print(f"✓ Whitelist loaded: {len(whitelist_filter.whitelist)} items")
    print(f"  - Brands: {len(whitelist_filter.brand_list)}")
    print(f"  - Jargon: {len(whitelist_filter.jargon_list)}")
    print(f"  - Slang/Abbr: {len(whitelist_filter.slang_abbr_list)}")
    print(f"  - Entity tokens: {len(whitelist_filter.entity_tokens)}")
    
    # Test cases từ dữ liệu thực
    test_cases = [
        # Case 1: SMS ngân hàng
        ['vcb', 'thong', 'bao', 'tai', 'khoan', 'cua', 'ban', '<URL>'],
        
        # Case 2: SMS với OTP
        ['ma', 'otp', 'cua', 'ban', 'la', '123456', 'het', 'han', 'sau', '5', 'phut'],
        
        # Case 3: SMS viết tắt
        ['lh', 'ngay', 'sdt', '<PHONE>', 'de', 'duoc', 'ho', 'tro'],
        
        # Case 4: SMS smishing leet
        ['ong', 'ba', 'da', 'du', 'dieu', 'kien', 'nhan', 'tien', 'bhtn', '<URL>'],
        
        # Case 5: SMS bình thường
        ['chao', 'ban', 'dao', 'nay', 'khoe', 'khong'],
    ]
    
    print("\n" + "=" * 60)
    print("TESTING TẦNG 3: WHITELIST FILTERING")
    print("=" * 60)
    
    for i, tokens in enumerate(test_cases, 1):
        result = whitelist_filter.filter(tokens)
        
        print(f"\nTest {i}:")
        print(f"  Input:          {tokens}")
        print(f"  To check:       {result.tokens_to_check}")
        print(f"  Whitelisted:    {result.whitelisted_tokens}")
        print(f"  Whitelist count: {result.whitelist_count}")