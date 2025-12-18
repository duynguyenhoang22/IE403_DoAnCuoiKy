from collections import OrderedDict, defaultdict
import re
import iocextract # pip install iocextract
import unicodedata

class AggressiveMasker:
    def __init__(self):
        # Sử dụng OrderedDict để quản lý thứ tự ưu tiên xử lý
        # Key: Tên loại thực thể
        # Value: Tuple (Token thay thế, Regex Pattern hoặc Hàm xử lý)
        self.patterns = OrderedDict([
            # 1. Nền tảng cụ thể (Zalo/Tele) cần bắt trước khi bắt URL chung
            ('zalo', ('<APP_LINK>', r'(?:https?:\/\/)?(?:www\.)?(?:zalo\.me|zalo\.vn)\/[\w\.-]+')),
            ('telegram', ('<APP_LINK>', r'(?:https?:\/\/)?(?:www\.)?(?:t\.me|telegram\.me)\/[\w_]+')),
            
            # 2. Email (Thường đi kèm trong URL, nên xử lý sau hoặc cùng lúc)
            ('email', ('<EMAIL>', r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),

            # 3. URL (Kết hợp iocextract và Aggressive Regex)
            ('url', ('<URL>', self._custom_url_masker)), 

            # 4A. HOTLINE (1800/1900) - Ưu tiên bắt trước Mobile
            # Bắt: 19001009, 1900 1009, 1900.55.55.88, 1800-1090
            ('hotline', ('<PHONE>', r'(?<!\d)(?:1800|1900)(?:[\s\.-]?\d){4,6}(?!\d)')),

            # 4B. MÁY BÀN (LANDLINE - Đầu 02x)
            # Bắt: 024.3838.3838, 028 3939 3939 (Tổng 11 số)
            ('landline', ('<PHONE>', r'(?<!\d)02\d(?:[\s\.-]?\d){8}(?!\d)')),

            # 4C. DI ĐỘNG (MOBILE - Đầu 03/05/07/08/09 hoặc +84)
            # Loại trừ trường hợp 1900 đã bắt ở trên
            ('mobile', ('<PHONE>', r'(?<!\d)(?:(?:[+]84|84)[\s\.-]?\d(?:[\s\.-]?\d){8}|0[35789](?:[\s\.-]?\d){8})(?!\d)')),
            
            # 4D. SHORTCODE (Đầu số dịch vụ ngắn 3-6 số)
            ('shortcode', ('<PHONE>', self._custom_shortcode_masker)),

            # 5. Ngày giờ (Datetime)
            # Bắt: 15/05, 10:30, 10h30, 15p, 30 ngay
            ('datetime', ('<TIME>', r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b\d{1,2}[:h]\d{2}\b|\b\d+\s?(?:phút|p|giờ|h|ngày|tháng|năm)\b')),
            
            # 6. Tiền tệ (Money)
            # Bắt: 100k, 500.000d, 1 triệu, 50 USD
            ('money', ('<MONEY>', r'(?i)\b\d+(?:[.,]\d+)*\s*(?:k|tr|triệu|trieu|tỷ|ty|nghìn|nghin|ngàn|ngan|đồng|dong|đ|d|vnd|vnđ|usd)\b')),
            
            # 7. Code & OTP (Xử lý cuối cùng để tránh ăn vào số trong URL/Date)
            ('code', ('<CODE>', self._custom_code_masker))
        ])

    def _custom_url_masker(self, text, token_tag):
        extracted = []
        
        # --- BƯỚC 1: Iocextract (Giữ nguyên) ---
        # Thư viện này bắt tốt các link chuẩn có http/https
        for url in iocextract.extract_urls(text, refang=True):
            if url in text:
                text = text.replace(url, token_tag)
                extracted.append(url)
                
        # --- BƯỚC 2: Aggressive Regex (NÂNG CẤP) ---
        
        # 1. Mở rộng danh sách TLD:
        # - Thêm nhóm shortener: ly, me, gl, to, co, cc, biz, info, mobi
        # - Thêm nhóm spam/bet: vip, pro, fun, club, win, life, xyz, top, icu
        tlds = r'com|vn|net|org|edu|gov|int|mil|biz|info|mobi|name|aero|asia|jobs|museum' \
            r'|ly|me|gl|to|co|cc|ws|tk|ga|cf|ml|at|su|bid|cfd' \
            r'|xyz|top|icu|vip|pro|club|win|life|fun|tech|site|online|store|shop'
        
        # 2. Cấu trúc Regex mới:
        # [Domain] + [Space/Dot] + [TLD] + (Optional: [Space/Slash] + [Path])
        # (?:\s*\/[\w-]+)? -> Đoạn này giúp "ăn" thêm phần /Q5YuG phía sau
        aggressive_pattern = r'(?i)\b[a-z0-9-]{1,20}\s*\.\s*(?:' + tlds + r')\b(?:\s*\/[\w-]+)?'
        
        # Dùng re.finditer để xử lý thay thế tốt hơn (tránh replace nhầm substring)
        # Lưu ý: Sắp xếp matches theo độ dài giảm dần để replace chuỗi dài trước (nếu cần)
        # Nhưng ở đây ta dùng thay thế trực tiếp
        
        matches = list(re.finditer(aggressive_pattern, text))
        
        # Lặp ngược từ cuối lên đầu để việc thay thế không làm lệch index của các match phía trước
        for m in reversed(matches):
            match_str = m.group(0)
            
            # Logic loại trừ: Tránh bắt nhầm chữ cái viết tắt (VD: "P.HCM" dính .HCM nếu có trong list)
            # Với danh sách TLD trên thì khá an toàn.
            
            # Thực hiện mask
            start, end = m.span()
            text = text[:start] + token_tag + text[end:]
            extracted.append(match_str)

        # --- BƯỚC 3: HẬU XỬ LÝ - Dọn prefix trước <URL> ---
        # Pattern: [chữ cái/số/gạch] + [space?] + . + [space?] + <URL>
        cleanup_pattern = r'(?i)[a-z0-9-]+[\s\u00A0]*\.[\s\u00A0]*(<URL>)'
        
        # Lặp để xử lý nhiều level subdomain (cdn.static.<URL>)
        prev_text = None
        while prev_text != text:
            prev_text = text
            text = re.sub(cleanup_pattern, r'\1', text)
        
        # Normalize multiple spaces
        text = re.sub(r'[\s\u00A0]+', ' ', text)
            
        return text, extracted


    def _custom_shortcode_masker(self, text, token_tag):
        extracted = []
        
        # 1. Tối ưu Whitelist: Gộp thành 1 Regex duy nhất thay vì for loop
        # Pattern: \b(191|900|...)\b
        known_shortcodes = [
            '191', '900', '999', '18001091', '106226', '5050', '9029', 
            '888', '1414', '9123', '9011'
        ]
        # Tạo regex dạng: \b(191|900|999|...)\b
        whitelist_pattern = r'\b(' + '|'.join(known_shortcodes) + r')\b'
        
        # Hàm callback để thay thế và lưu lại giá trị
        def whitelist_replacer(match):
            val = match.group(1)
            extracted.append(val)
            return token_tag # Thay thế bằng <PHONE>

        # Thực hiện thay thế an toàn
        if known_shortcodes:
            text = re.sub(whitelist_pattern, whitelist_replacer, text)

        # 2. Xử lý theo Context (Ngữ cảnh)
        # Regex: (Nhóm từ khóa) + (Khoảng trắng) + (Nhóm số Shortcode)
        # Group 1: Từ khóa (gửi, soạn...)
        # Group 2: Số điện thoại
        context_pattern = r'(?i)\b(gửi|gui|lh|liên hệ|hotline|tổng đài|cskh)\s+(\d{3,6})\b'

        def context_replacer(match):
            keyword = match.group(1) # Giữ nguyên từ khóa (ví dụ: "soạn")
            number = match.group(2)  # Số cần mask (ví dụ: "191")
            
            # Double check: Nếu số này trông giống OTP (VD: gửi 123456) -> Có thể không nên mask là Phone
            # Nhưng ở đây ta cứ mask theo logic Shortcode
            extracted.append(number)
            
            # Chỉ thay thế phần số, giữ lại phần từ khóa
            return f"{keyword} {token_tag}"

        text = re.sub(context_pattern, context_replacer, text)
                 
        return text, extracted

    def _custom_code_masker(self, text, token_tag):
        extracted = []
        
        # 1. Bắt Code dịch vụ (Chữ hoa + Số)
        # Dùng re.sub callback để thay thế an toàn
        def code_replacer(match):
            val = match.group(0)
            extracted.append(val)
            return token_tag
            
        text = re.sub(r'\b[A-Z]+[0-9]+[A-Z0-9]*\b', code_replacer, text)

        # 2. Bắt OTP (Số thuần túy 4-6 ký tự)
        # Regex update: Sử dụng Lookaround để đảm bảo không ăn vào Code đã mask (<CODE>)
        # hoặc các token khác.
        # Logic: Số đứng độc lập, không dính ký tự lạ
        otp_pattern = r'(?<![\w<])\d{4,6}(?![\w>])'
        
        def otp_replacer(match):
            val = match.group(0)
            # Loại trừ năm sinh (19xx, 20xx)
            if val.startswith(('19', '20')) and len(val) == 4:
                return val # Giữ nguyên năm
            
            extracted.append(val)
            return token_tag

        text = re.sub(otp_pattern, otp_replacer, text)
            
        return text, extracted

    def mask(self, text: str) -> tuple[str, dict]:
        """
        Logic xử lý 1 tin nhắn
        Returns: (masked_text, metadata_dict)
        """
        if not text:
            return "", {}
        
        # Chuẩn hóa Unicode trước
        text = unicodedata.normalize('NFC', text)
        
        metadata = defaultdict(list)
        processed_text = text

        for label, (token_tag, logic) in self.patterns.items():
            if callable(logic):
                # Nếu là hàm custom (URL, Code)
                processed_text, items = logic(processed_text, token_tag)
                if items:
                    metadata[label].extend(items)
            else:
                # Nếu là Regex thuần
                matches = re.findall(logic, processed_text, flags=re.IGNORECASE | re.UNICODE)
                if matches:
                    metadata[label].extend(matches)
                    # Thay thế bằng Token
                    processed_text = re.sub(logic, token_tag, processed_text, flags=re.IGNORECASE | re.UNICODE)

        return processed_text, dict(metadata)

    def _mask_batch(self, texts: list[str]) -> tuple[list[str], list[dict]]:
        """
        Logic xử lý batch
        """
        masked_texts = []
        metadatas = []
        
        for t in texts:
            m_text, meta = self.mask(t)
            masked_texts.append(m_text)
            metadatas.append(meta)
            
        return masked_texts, metadatas

    def get_entity_counts(self, metadata: dict) -> dict:
        """Chuyển metadata thành entity counts"""
        return {label: len(items) for label, items in metadata.items()}

    def mask_with_counts(self, text: str) -> tuple[str, dict]:
        masked_text, metadata = self.mask(text)
        counts = self.get_entity_counts(metadata)
        return masked_text, counts


# --- CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    masker = AggressiveMasker()
    
    samples = [
        "Truy cap ngay banca . com hoac bit.ly/test de nhan thuong",
        "Lien he zalo.me/0912345678 de duoc ho tro",
        "Ma xac thuc cua ban la 5993. Khong chia se cho ai",
        "Soan ST5K gui 9029 de nhan 1GB data",
        "Chuyen khoan 500k vao so tai khoan 0987654321",
        "Gap nhau luc 10h30 ngay 15/05 nhe",
        "Goi 1900 54 54 15 de duoc ho tro",           # Hotline có space
        "Nhan 5 trieu dong ngay",                      # Money có space
        "Truy cap acb . com . vn de xac thuc",        # URL nhiều space
        "Ma OTP cua ban: 123456. Het han sau 5 phut", # OTP + Time
        "LH zalo: 0901234567 hoac t.me/support",      # Multiple platforms
        "Bộ Y Tế xin thông báo: Bạn đã đủ điều kiện đăng ký xin trợ cấp. Vui lòng hoàn thành thủ tục đăng ký trực tuyến ngay bây giờ. Thời hạn đến 17h30 hôm nay. https://www.miniboon.vn/",
        "live:.cid.4fa739d97a500848: Thong bao KH nhan tien tu DV chuyen tien Western Union. Truy cap kiem tra thong tin nhan tien tai Website: https://yip.su/2b6L35",
        "j)t.ly/Q5YuG Um Cu,u~Th,ua8% ZJ Na.pVao- LanD:au,UuDa'j:8Tr8 PJ wz8:88.Bma Gu.i_C:OT~6OKa:H'SD;2_4H {H6MW9KD1X191> z Hoa'n,Tr'a~1,4% Ge",
        "GR N'ha'nL,jen:Qu.a;HangN,gay y H,ojV'ienM:Oj;N'apV,aoT K,La:nDa.uT,j,en:19_8_Ka'T' huon'g-H,ai'T,ram:N:ga.n fK. U,WI.Nqo6;6f7fxxzz.r-kl.com T",
    ]   
    
    print(f"{'ORIGINAL':<50} | {'MASKED'}")
    print("-" * 100)
    
    masked_batch, meta_batch = masker._mask_batch(samples)
    
    for org, msk, meta in zip(samples, masked_batch, meta_batch):
        print(f"Org: {org}")
        print(f"Msk: {msk}")
        print(f"Meta: {meta}")
        print("-" * 20)
