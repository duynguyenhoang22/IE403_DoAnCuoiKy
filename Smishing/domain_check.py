import sys
import os
import re
import unicodedata
import requests
import tldextract
from bs4 import BeautifulSoup
from ddgs import DDGS # pip install ddgs
from collections import Counter
import warnings
import urllib3

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

# --- IMPORT MASKER ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from preprocessing.layer1_masking import AggressiveMasker
except ImportError:
    print("Error: Could not find 'layer1_masking.py'. Please ensure your file is named correctly and in the same folder.")
    exit()

# ==========================================
# 1. HELPER: TEXT CLEANER (For Noun Extraction)
# ==========================================
class SpamTextCleaner:
    """
    Kept from your original code. 
    Reason: We need clean text to extract Nouns (N) for the Search Engine Query.
    """
    def __init__(self):
        pass

    def normalize_unicode(self, text):
        return unicodedata.normalize('NFC', text)

    def deobfuscate_vietnamese(self, text):
        """
        Removes obfuscation characters to make text readable for search engines.
        Ex: "N'ha'n" -> "Nhan"
        """
        # Remove special chars between letters
        pattern = r'(?<=[a-zA-Z])[^a-zA-Z0-9\s](?=[a-zA-Z])'
        prev_text = ""
        while prev_text != text:
            prev_text = text
            text = re.sub(pattern, '', text)
        
        # Remove trailing distinct chars like "Qua;" -> "Qua"
        text = re.sub(r'(?<=\w)[^\w\s\.]+(?=\s|$)', '', text)
        return text

    def clean(self, text):
        if not text: return ""
        text = self.normalize_unicode(text)
        return self.deobfuscate_vietnamese(text)

# ==========================================
# 2. CORE: DOMAIN CHECKING PHASE
# ==========================================
class URLInspector:
    def __init__(self):
        # Whitelist for quick comparison (optional but recommended)
        self.whitelist_domains = {
            'vietcombank.com.vn', 'acb.com.vn', 'techcombank.com.vn', 
            'vpbank.com.vn', 'bidv.com.vn', 'zalo.me', 'momo.vn', 'vnpt.vn', 'viettel.vn'
        }
        # Shorteners that require expansion (skip Phase 1, go to Phase 2 expansion)
        self.shortener_domains = {
            'bit.ly', 'goo.gl', 'tinyurl.com', 't.co', 't.ly', 'j)t.ly', 'jit.ly', 
            'is.gd', 'buff.ly', 'adf.ly', 'bit.do', 'shorte.st', 'cutt.ly'
        }

    def refang_url(self, raw_url):
        """Standardize URL for requests"""
        clean_url = re.sub(r'\s*\.\s*', '.', raw_url) # banca . com -> banca.com
        clean_url = clean_url.replace(" ", "")
        if not clean_url.startswith(('http://', 'https://')):
            clean_url = 'http://' + clean_url
        return clean_url

    def extract_base_domain(self, url):
        """
        Extracts 'acb.com.vn' from 'https://khuyenmai.acb.com.vn'
        """
        ext = tldextract.extract(url)
        # Handle cases like 'co.uk' or 'com.vn' correctly
        if ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return ext.domain

    def extract_nouns(self, clean_sms_text):
        """
        Extract key Nouns (N) from the CLEANED SMS text.
        FIX: Sử dụng (?:...) để không tạo capturing group, giúp lấy được cả từ viết hoa.
        """
        # Regex cũ (LỖI): r'\b[A-Z][a-z0-9]+\b|\b(tài khoản|ngân hàng|...)\b'
        
        # Regex mới (ĐÃ SỬA): Thêm ?: vào đầu nhóm từ khóa
        pattern = r'\b[A-Z][a-z0-9]+\b|\b(?:tài khoản|ngân hàng|xác thực|giao dịch|mật khẩu|internet banking|website)\b'
        
        keywords = re.findall(pattern, clean_sms_text, re.IGNORECASE)
        
        # Filter out short meaningless words
        return list(set([k for k in keywords if len(k) > 2]))

    # --- PHASE 1: SEARCH ENGINE CHECK ---
    def check_domain_reputation(self, url, clean_sms_text):
        domain_d = self.extract_base_domain(url)
        
        if domain_d in self.shortener_domains:
            return False, "Shortener Detected - Force Expand"

        nouns_n = self.extract_nouns(clean_sms_text)
        
        # SỬA ĐỔI: Nếu không tìm thấy danh từ, vẫn tiếp tục search chỉ với domain
        if not nouns_n:
            query = f"{domain_d}" # Fallback query
            print(f"      [Search Query]: {query} (No nouns found)")
        else:
            # Create Query: "Vietcombank vietcombank.com.vn"
            query = f"{' '.join(nouns_n[:4])} {domain_d}" 
            print(f"      [Search Query]: {query}")

        try:
            # Using DuckDuckGo Search
            results = list(DDGS().text(query, max_results=5))
            
            for res in results:
                result_link = res['href']
                result_domain = self.extract_base_domain(result_link)
                
                # Check if the domain D matches any domain in Top 5 results
                if result_domain == domain_d:
                    return True, f"Matched trusted source: {result_domain}"
            
            return False, "Domain not found in top 5 search results"
        except Exception as e:
            return False, f"Search Error: {e}"

    # --- PHASE 2: SOURCE CODE & CONTENT ANALYSIS ---
    def check_page_content(self, url):
        print(f"      [Content Scan]: Analyzing {url}...")
        target_domain = self.extract_base_domain(url)
        
        try:
            # 1. Request with timeout and allow redirects (expands bit.ly)
            response = requests.get(url, timeout=5, verify=False, allow_redirects=True)
            
            # Check the final URL after redirection
            final_url = response.url
            final_domain = self.extract_base_domain(final_url)
            
            # If redirected to a known whitelist domain (e.g. bit.ly -> vietcombank.com.vn)
            if final_domain in self.whitelist_domains:
                return True, f"Redirects to Whitelisted Domain: {final_domain}"

            # 2. Extract Links from Source Code
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            extracted_domains = []
            for link in links:
                href = link['href']
                if href.startswith('http'):
                    d = self.extract_base_domain(href)
                    if d: extracted_domains.append(d)
            
            # 3. Analyze consistency
            if extracted_domains:
                # Find the most frequent domain referenced in the page
                most_common = Counter(extracted_domains).most_common(1)
                if most_common:
                    dominant_domain = most_common[0][0]
                    
                    # LOGIC: If the page links heavily to 'vietcombank.com.vn' 
                    # but the site is hosted on 'xyz-bank.top' -> Phishing
                    if dominant_domain in self.whitelist_domains and target_domain != dominant_domain:
                        return False, f"Phishing: Content mimics {dominant_domain} but hosted on {target_domain}"
                    
                    # If links point to itself -> Consistent
                    if dominant_domain == target_domain:
                        return True, "Consistent Content (Self-referencing)"

            return False, "Low consistency or generic content"

        except Exception as e:
            return False, f"Connection Failed: {str(e)}"

# ==========================================
# 3. SYSTEM PIPELINE (THE FLOWCHART)
# ==========================================
class SmishingDetectionPipeline:
    def __init__(self):
        self.masker = AggressiveMasker()
        self.cleaner = SpamTextCleaner()
        self.inspector = URLInspector()

    def process(self, raw_text):
        """
        Executes the flowchart logic.
        Returns: 
            status (str): 'LEGIT', 'SUSPICIOUS_URL', 'CHECK_AI', or 'CLEAN_NO_DATA'
            masked_text (str): The text after preprocessing
            details (list): Logs of what happened
        """
        # STEP 1: PRE-PROCESSING & MASKING
        masked_text, metadata = self.masker.mask(raw_text)
        urls = metadata.get('url', [])
        phones = metadata.get('phone', []) # Assuming masker returns this
        emails = metadata.get('email', []) # Assuming masker returns this
        
        details = []

        # === FLOWCHART: URL IN SMS? ===
        if urls:
            print(f"[*] URL Detected: {urls}")
            clean_text = self.cleaner.clean(raw_text)
            all_urls_legit = True
            
            for raw_url in urls:
                url = self.inspector.refang_url(raw_url)
                
                # DOMAIN CHECK 1: Search Engine
                is_legit, reason = self.inspector.check_domain_reputation(url, clean_text)
                
                if is_legit:
                    details.append(f"URL '{raw_url}': LEGIT ({reason})")
                else:
                    # DOMAIN CHECK 2: Content Analysis
                    print(f"   -> Check 1 failed ({reason}), trying Check 2...")
                    is_legit_2, reason_2 = self.inspector.check_page_content(url)
                    
                    if is_legit_2:
                        details.append(f"URL '{raw_url}': LEGIT ({reason_2})")
                    else:
                        details.append(f"URL '{raw_url}': SUSPICIOUS (Check 1: {reason}, Check 2: {reason_2})")
                        all_urls_legit = False
            
            if all_urls_legit:
                return "LEGIT", masked_text, details
            else:
                # Flowchart: If URL check fails -> Go to Feature Extraction
                return "SUSPICIOUS_URL", masked_text, details
                
        else:
            # === FLOWCHART: Phone No / Email in SMS? ===
            # We check metadata from your friend's masker
            if phones or emails:
                details.append("No URL, but Phone/Email detected.")
                return "CHECK_AI", masked_text, details
            else:
                return "CLEAN_NO_DATA", masked_text, details


# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    pipeline = SmishingDetectionPipeline()
    
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

    print(f"{'='*60}")
    print(f"{'SMISHING DETECTION SYSTEM LOG':^60}")
    print(f"{'='*60}")

    for i, sample in enumerate(samples):
        print(f"\n>>> PROCESSING SMS #{i+1}: {sample[:50]}...")
        decision, masked_output, logs = pipeline.process(sample)
        
        print(f"   [Masked Output]: {masked_output}")
        if logs:
            for log in logs:
                print(f"   [Log]: {log}")
        print(f"   [FINAL DECISION]: {decision}")