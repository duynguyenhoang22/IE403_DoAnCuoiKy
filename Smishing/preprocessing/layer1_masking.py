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

            # 4. BANK ACCOUNT (bắt stk)
            ('bank_acc', ('<BANK_ACC>', self._custom_bank_masker)),

            # 5A. HOTLINE (1800/1900) - Ưu tiên bắt trước Mobile
            # Bắt: 19001009, 1900 1009, 1900.55.55.88, 1800-1090
            ('hotline', ('<PHONE>', r'(?<!\d)(?:1800|1900)(?:[\s\.-]?\d){4,6}(?!\d)')),

            # 5B. MÁY BÀN (LANDLINE - Đầu 02x)
            # Bắt: 024.3838.3838, 028 3939 3939 (Tổng 11 số)
            ('landline', ('<PHONE>', r'(?<!\d)02\d(?:[\s\.-]?\d){8}(?!\d)')),

            # 5C. DI ĐỘNG (MOBILE - Đầu 03/05/07/08/09 hoặc +84)
            # Loại trừ trường hợp 1900 đã bắt ở trên
            ('mobile', ('<PHONE>', r'(?<!\d)(?:(?:[+]84|84)[\s\.-]?\d(?:[\s\.-]?\d){8}|0[35789](?:[\s\.-]?\d){8})(?!\d)')),
            
            # 5D. SHORTCODE (Đầu số dịch vụ ngắn 3-6 số)
            ('shortcode', ('<PHONE>', self._custom_shortcode_masker)),

            # 6. Ngày giờ (Datetime)
            # Bắt: 15/05, 10:30, 10h30, 15p, 30 ngay
            ('datetime', ('<TIME>', r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|\b\d{1,2}[:h]\d{2}\b|\b\d+\s?(?:phút|p|giờ|h|ngày|tháng|năm)\b')),
            
            # 7. Tiền tệ (Money)
            # Bắt: 100k, 500.000d, 1 triệu, 50 USD
            ('money', ('<MONEY>', r'(?i)\b(?:\d+(?:[.,]\d+)*\s*(?:triệu|trieu|tr|tỷ|ty|nghìn|nghin|ngàn|ngan|đồng|dong|vnd|vnđ|usd|k|đ|d)\b|[1-9]\d{0,2}(?:[.,]\d{3})+)(?!\d)')),
            
            # 8. Code & OTP (Xử lý cuối cùng để tránh ăn vào số trong URL/Date)
            ('code', ('<CODE>', self._custom_code_masker))
        ])

    def _custom_url_masker(self, text, token_tag):
        extracted = []
        
        # 1. CẬP NHẬT TLDs
        # Thêm app, io, dev, cloud... (các TLD hiện đại hacker hay dùng)
        safe_tlds = r'vn|com|net|org|edu|gov|int|mil|biz|info|mobi|aero|asia|jobs|museum|app|io|dev|cloud'
        
        risky_tlds = (
            r'name|ly|me|gl|to|co|cc|ws|tk|ga|cf|ml|at|su|bid|cfd|'
            r'xyz|top|icu|vip|pro|club|win|life|fun|tech|site|online|store|shop|live|website'
        )

        # 2. XỬ LÝ ĐẶC BIỆT: BROKEN SHORTENERS
        # Bắt riêng bit.ly, t.ly, tinyurl bị chèn khoảng trắng: "bi t . ly", "bit .ly"
        # Logic: (b i t) + (khoảng trắng/dấu chấm lộn xộn) + (l y)
        broken_shortener_pattern = (
            r'(?i)\b(?:b\s*i\s*t|t|tinyurl)\s*[\.\,]\s*l\s*y\b'  # Bắt phần domain
            r'(?:[\/\s]+[\w\-\.\?\=\&\%]+)?'                     # Bắt phần path phía sau
        )

        # 3. CHIẾN LƯỢC: PROTOCOL-BASED
        # Nếu đã có http/https, ta chấp nhận TẤT CẢ các đuôi từ 2 ký tự trở lên.
        # Không cần check whitelist TLD ở đây vì http là tín hiệu quá mạnh.
        protocol_agnostic_pattern = (
            r'(?i)\b(?:https?:\/\/|www\.)'        # Protocol
            r'(?:[\w\-\.]+(?:\s+[\w\-\.]+)*)'     # Subdomains (cho phép space nhẹ)
            r'\.[a-z]{2,10}\b'                    # TLD bất kỳ (2-10 ký tự) -> Bắt được .app, .ngrok
            r'(?:[\/][\w\-\.\?\=\&\%]*)?'         # Path
        )

        # 4. SCHEMELESS (Giữ nguyên logic cũ để an toàn)
        # Safe TLDs (Fuzzy - cho phép khoảng trắng)
        schemeless_safe_pattern = (
            r'(?i)\b(?:[\w\-]+)(?:\s*\.\s*[\w\-]+)*\s*\.\s*(?:' + safe_tlds + r')\b(?:[\/][\w\-\.\?\=\&\%]*)?'
        )
        # Risky TLDs (Strict - bắt buộc dính liền)
        schemeless_risky_pattern = (
            r'(?i)\b(?:[\w\-]+)(?:\.[\w\-]+)*\.(?:' + risky_tlds + r')\b(?:[\/][\w\-\.\?\=\&\%]*)?'
        )

        # --- THỰC THI REPLACEMENT ---
        def replace_and_extract(match):
            url = match.group(0)
            # Clean URL: Xóa hết khoảng trắng thừa để Domain Check hoạt động được
            # VD: "bi t . ly" -> "bit.ly"
            clean_url = re.sub(r'\s+', '', url)
            
            # Xử lý riêng cho trường hợp dấu chấm bị tách: "bit . ly" -> "bit.ly"
            # Nhưng cẩn thận không nối "com . vn" thành "com.vn" nếu logic trên chưa xử lý
            # Ở đây đơn giản là xóa space là đủ cho hầu hết case.
            
            extracted.append(clean_url) 
            return token_tag

        # Thứ tự ưu tiên (Pattern cụ thể chạy trước)
        
        # B1: Bắt Broken Shorteners (Case 3)
        text = re.sub(broken_shortener_pattern, replace_and_extract, text)

        # B2: Bắt Protocol mạnh (Case 1)
        text = re.sub(protocol_agnostic_pattern, replace_and_extract, text)

        # B3: Bắt Schemeless Safe
        text = re.sub(schemeless_safe_pattern, replace_and_extract, text)
        
        # B4: Bắt Schemeless Risky
        text = re.sub(schemeless_risky_pattern, replace_and_extract, text)

        # Cleanup
        text = re.sub(rf'{token_tag}[\w\.\-\/]+', token_tag, text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text, extracted

    def _custom_bank_masker(self, text, token_tag):
        extracted = []
        
        # Danh sách từ khóa nhận diện STK (Ngân hàng & Từ chỉ định)
        keywords = (
            r'stk|số tk|so tk|số tài khoản|so tai khoan|tài khoản|tai khoan|tk|account|acc|'
            r'ngân hàng|ngan hang|bank|banking|'
            r'vietcombank|vcb|techcombank|tcb|mbbank|mb|bidv|vietinbank|vtb|'
            r'agribank|vpbank|acb|sacombank|tpbank|hdbank|vib|ocb|shb|eximbank|msb'
        )
        
        # Regex giải thích:
        # 1. (?i)\b(?:...): Bắt đầu bằng một trong các từ khóa trên (case-insensitive)
        # 2. (?:[\s:\.\-]*?): Cho phép các ký tự ngăn cách (dấu hai chấm, khoảng trắng, dấu chấm...)
        # 3. (\d{8,19}): Bắt dãy số chính (STK thường từ 8 đến 19 số)
        # 4. (?!\d): Đảm bảo kết thúc dãy số (không cắt giữa chừng)
        # 5. Lookbehind/Context check: Đảm bảo số này gắn liền với keyword
        
        pattern = rf'(?i)\b({keywords})(?:[\s:\.\-\|]*?)(\d{8,19})(?!\d)'
        
        def replacer(match):
            keyword = match.group(1) # Giữ lại từ khóa (vd: "Vietcombank")
            number = match.group(2)  # Số tài khoản
            
            # Logic loại trừ xung đột:
            # Nếu số bắt được chính xác là 10 số và bắt đầu bằng 0 -> Có thể là SĐT?
            # NHƯNG vì nó đứng sau từ khóa "STK" hoặc "Bank", ta ưu tiên nó là BANK_ACC.
            # Trừ trường hợp keyword là "LH" hay "Liên hệ" (đã xử lý ở logic khác hoặc không nằm trong list keywords trên)
            
            extracted.append(number)
            # Trả về: "Vietcombank <BANK_ACC>" thay vì chỉ "<BANK_ACC>" 
            # để giữ ngữ cảnh cho model hiểu đây là thông tin thanh toán.
            return f"{keyword} {token_tag}"

        # Thực hiện replace
        text = re.sub(pattern, replacer, text)
        
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
        
        # --- DANH SÁCH TIỀN TỐ GÓI CƯỚC HỢP LỆ ---
        # Bộ lọc quan trọng nhất để phân biệt Code vs Leet Speak
        # Code nhà mạng luôn bắt đầu bằng các cụm từ này
        VALID_PREFIXES = {
            'V', 'ST', 'D', 'C', 'M', 'MI', 'SD', 'HD', 'VD', 'MAX', 'BIG', 'KC', # Viettel/Vina/Mobi prefixes
            'DK', 'HUY', 'Y', 'KT', 'T', # Cú pháp tin nhắn
            'NAP', 'TK', 'MK', # Viết tắt chức năng
            'UMAX', 'TRE', 'SV', 'ECO' # Các gói đặc thù
        }

        # 1. Bắt Code dịch vụ (Chữ hoa + Số)
        def code_replacer(match):
            val = match.group(0)
            
            # --- LOGIC PHÂN LOẠI ---
            
            # Rule 1: Độ dài. Code gói cước thường ngắn (3-8 ký tự).
            # Leet speak spam thường dài (ví dụ: KHUYENMA1 -> 9 ký tự)
            if len(val) > 8: 
                return val # Trả về nguyên gốc để xử lý như Leet word

            # Rule 2: Kiểm tra Prefix
            match_prefix = re.match(r'^[A-Z]+', val)
            if match_prefix:
                prefix = match_prefix.group(0)
                
                # === THÊM RULE MỚI: Phân biệt Leetspeak ===
                # Leetspeak: Chỉ có 1 số (0 hoặc 1) xen giữa các chữ
                # Code: Thường có nhiều số liên tiếp hoặc số > 1
                
                digits = re.findall(r'\d', val)
                
                # Nếu chỉ có 1 số VÀ số đó là 0 hoặc 1 → Có thể là Leetspeak
                if len(digits) == 1 and digits[0] in '01':
                    # Kiểm tra thêm: Có chữ SAU số không? (pattern Leet: C0NG, T1EN)
                    if re.match(r'^[A-Z]+[01][A-Z]+$', val):
                        return val  # Leetspeak → Không mask
                
                # Nếu prefix hợp lệ VÀ không phải Leetspeak → Mask
                if prefix in VALID_PREFIXES:
                    extracted.append(val)
                    return token_tag
            
            return val

        # Regex bắt chuỗi: Bắt đầu bằng Chữ, chứa Số
        text = re.sub(r'\b[A-Z]+[0-9]+[A-Z0-9]*\b', code_replacer, text)

        # 2. Bắt OTP (Số thuần túy 4-6 ký tự) - GIỮ NGUYÊN
        otp_pattern = r'(?<![\w<])\d{4,6}(?![\w>])'
        
        def otp_replacer(match):
            val = match.group(0)
            if val.startswith(('19', '20')) and len(val) == 4:
                return val 
            extracted.append(val)
            return "<CODE>"

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
        "Vietcombank thong bao: So du bien dong -2.000.000. Chi tiet: https://vietcombank.com.vn.ngrok-free.app/login",
        "Quy khach V.C.B vui long xac thuc kyc tai vcb-digibank-secure.xyz de tranh bi khoa tai khoan.",
        "Nhan qua tri an khach hang tai bi t . ly / qua-tang-bi-mat",
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
