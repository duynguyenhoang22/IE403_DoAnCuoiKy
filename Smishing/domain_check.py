import logging
import tldextract
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from functools import lru_cache
import re
import warnings
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except (ImportError, AttributeError):
    pass # Bỏ qua nếu không import được, không ảnh hưởng logic chính

# Tắt cảnh báo SSL
warnings.filterwarnings("ignore")

try:
    from preprocessing.layer1_masking import AggressiveMasker
    from linguistic_features.layer2_normalization import TextNormalizer
    from linguistic_features.layer3_whitelist import WhitelistFilter
except ImportError:
    pass

logger = logging.getLogger(__name__)

class DomainVerifier:
    def __init__(self):
        self.ddgs = DDGS()
        self.masker = AggressiveMasker()
        self.normalizer = TextNormalizer()
        self.whitelist = WhitelistFilter()
        self.known_brands = set(self.whitelist.brand_list)
        
        # --- FIX 1: STATIC WHITELIST (Giải quyết vấn đề đa tên miền) ---
        # Nếu gặp các domain này -> Bỏ qua thuật toán bài báo -> Auto Legit
        self.whitelist_domains = {
            # Ngân hàng & Nhà mạng VN (Giữ nguyên của bạn)
            'vietcombank.com.vn', 'vcb.com.vn',
            'viettel.vn', 'vietteltelecom.vn', 'viettelpay.vn',
            'tiki.vn', 'tiki.com', 'shopee.vn', 'shopee.com',
            'momo.vn', 'zalopay.vn', 'zalo.me',
            'vnpt.com.vn', 'vinaphone.com.vn', 'mobifone.vn',
            
            # THÊM: Các ông lớn quốc tế (Để hệ thống chạy nhanh hơn)
            'google.com', 'google.com.vn', 'facebook.com', 'youtube.com',
            'gmail.com', 'apple.com', 'microsoft.com', 'instagram.com'
        }
        
        self.REQUEST_TIMEOUT = 5

    def _get_registered_domain(self, url):
        """
        FIX 2: Dùng tldextract để lấy gốc chính xác (Chống Ngrok)
        """
        try:
            # Loại bỏ dấu chấm thừa cuối câu (Lỗi Case 8)
            url = url.rstrip('.,;:')
            
            if not url.startswith(('http://', 'https://')): 
                url = 'http://' + url
            
            ext = tldextract.extract(url)
            if not ext.suffix: return ""
            # Trả về domain gốc: ngrok-free.app thay vì vietcombank.ngrok...
            return f"{ext.domain}.{ext.suffix}".lower()
        except:
            return ""

    def _smart_brand_extraction(self, text):
        masked_text, _ = self.masker.mask(text)
        norm_res = self.normalizer.normalize(masked_text)
        for token in norm_res.tokens:
            if token in self.known_brands:
                return token
        return None

    # --- ALGORITHM 2 (Cải tiến) ---
    def _level1_search_check(self, domain_d, brand_n):
        logger.info(f"--- [Level 1] Searching: '{brand_n} {domain_d} official' ---")
        query = f"{brand_n} {domain_d} official website"
        try:
            results = list(self.ddgs.text(query, max_results=5))
            for res in results:
                res_domain = self._get_registered_domain(res['href'])
                
                # Logic so sánh: 
                # 1. Khớp chính xác (Algorithm 2 gốc)
                if res_domain == domain_d:
                    return True, "Found in Search Results"
                
                # 2. Subdomain check (Mở rộng cho thực tế)
                # Ví dụ: Tin nhắn gửi link 'km.viettel.vn', search ra 'viettel.vn' -> OK
                if domain_d.endswith("." + res_domain):
                    return True, f"Subdomain of {res_domain}"
                    
            return False, "Not found in Top 5"
        except:
            return False, "Search Error"

    # --- ALGORITHM 3 (Cải tiến) ---
    def _level2_source_code_check(self, url, domain_d):
        logger.info(f"--- [Level 2] Checking Source Code of '{url}' ---")
        try:
            # FIX 3: Clean URL trước khi request
            url = url.rstrip('.,;:')
            
            response = requests.get(url, timeout=self.REQUEST_TIMEOUT, verify=False)
            if response.status_code != 200:
                return False, f"Site unreachable ({response.status_code})"

            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            internal_count = 0
            # FIX 4: Kiểm tra lỏng hơn
            # Chỉ cần có ÍT NHẤT 1 link trỏ về domain gốc hoặc domain whitelist
            for link in links:
                href = link['href']
                link_domain = self._get_registered_domain(href)
                
                if link_domain == domain_d or link_domain in self.whitelist_domains:
                    return True, "Source code contains verified internal/whitelist links"

            return False, "No verified links found in source code"

        except Exception as e:
            return False, f"Connection Failed: {e}"

    def verify(self, text):
        # 1. Lấy tất cả URL (Regex + Masker)
        regex_urls = re.findall(r'(?:https?://|www\.)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/\S*)?', text)
        regex_urls = [u.rstrip('.,:;') for u in regex_urls]
        
        _, metadata = self.masker.mask(text)
        masked_urls = metadata.get('url', []) + metadata.get('app_link', [])
        
        all_urls = list(set(regex_urls + masked_urls))
        if not all_urls:
            return "SKIP", "No URL", 0.0

        brand_n = self._smart_brand_extraction(text)
        
        has_whitelist = False
        has_phishing = False
        phishing_reason = ""
        whitelist_reason = ""

        for url in all_urls:
            clean_url = url.replace(" ", "")
            domain_d = self._get_registered_domain(clean_url)
            
            if not domain_d: continue

            # CHECK 1: STATIC WHITELIST (Ưu tiên cao nhất)
            if domain_d in self.whitelist_domains:
                has_whitelist = True
                whitelist_reason = f"Whitelisted Domain ({domain_d})"
                continue 

            # --- SỬA LỖI: KHÔNG ĐƯỢC CONTINUE KHI KHÔNG THẤY BRAND ---
            # Logic cũ: if not brand_n: continue (SAI - Khiến URL độc bị bỏ qua)
            
            # CHECK 2: ALGORITHM 2 (SEARCH)
            # Chỉ chạy được nếu có Brand Name
            search_passed = False
            if brand_n:
                is_legit, reason = self._level1_search_check(domain_d, brand_n)
                if is_legit:
                    has_whitelist = True
                    whitelist_reason = reason
                    search_passed = True # Đánh dấu đã qua ải này
            
            # Nếu đã qua Search Check thì không cần check Source Code cho tốn thời gian
            if search_passed:
                continue

            # CHECK 3: ALGORITHM 3 (SOURCE CODE)
            # Chạy cho mọi URL lạ (kể cả khi không tìm thấy Brand)
            # Đây là chốt chặn cuối cùng để bắt vcb-digibank-secure.xyz
            is_legit_l2, reason_l2 = self._level2_source_code_check(clean_url, domain_d)
            
            if is_legit_l2:
                has_whitelist = True
                whitelist_reason = reason_l2
            else:
                # Nếu không Whitelist, Không qua Search, và Source Code hỏng/độc
                # -> PHISHING
                has_phishing = True
                phishing_reason = "URL Suspicious (Failed Search/Source Check)"
                break 

        # QUYẾT ĐỊNH
        if has_phishing:
            return "PHISHING", phishing_reason, 1.0
        
        if has_whitelist:
            return "LEGIT", whitelist_reason, -1.0

        # Trường hợp URL lạ nhưng check Source code không kết luận được (vd site chết)
        # Thì vẫn nên cảnh báo nhẹ hoặc để AI quyết định
        return "SKIP", "Inconclusive", 0.0