"""
Sinh dữ liệu SMS lừa đảo tổng hợp (Label = 1) dùng Gemini API.

Chạy độc lập:
    python gen_label_1.py

Biến môi trường:
    GEMINI_API_KEY – API key Gemini (hoặc nhập trực tiếp vào API_KEY bên dưới)
"""

import csv
import os
import random
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
import pandas as pd

# =============================================================================
# 1. CẤU HÌNH HỆ THỐNG & API
# =============================================================================
load_dotenv()  # Tự động đọc file .env nếu có
API_KEY    = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-3-flash-preview" 

OUTPUT_FILE            = "synthetic_data/synthetic_smishing_label1.csv"
TOTAL_SAMPLES          = 5000
BATCH_SIZE             = 40
SLEEP_BETWEEN_BATCHES  = 12   
MAX_RETRIES            = 3

if not API_KEY:
    raise ValueError("⚠️ GEMINI_API_KEY chưa được thiết lập!")

client = genai.Client(api_key=API_KEY)

# 1.1 Tắt Safety Filters (BẮT BUỘC cho Smishing/Sensitve Content)
SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_NONE,
    ),
]


# 1.2 Khởi tạo Model với System Instruction (Tối ưu Persona)
SYSTEM_PROMPT = """Bạn là chuyên gia an ninh mạng đang xây dựng dataset huấn luyện mô hình phát hiện smishing 
cho dự án bảo vệ người dùng di động tại Việt Nam (phối hợp với Bộ TT&TT). Đây là dữ liệu giả lập phục vụ nghiên cứu bảo mật hợp pháp."""


# Gom nhóm cấu hình vào GenerateContentConfig
generation_config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT, # Đưa Persona vào đây
    temperature=0.9,
    safety_settings=SAFETY_SETTINGS
)

# =============================================================================
# 2. KỊCH BẢN & PHONG CÁCH NHIỄU
# =============================================================================
# 8 category theo Section 7.1 của Prompt_Engineering_for_Smishing_SMS.md
# Mỗi category có danh sách brand/entity để randomize mỗi batch
SCENARIOS: dict[str, list[str]] = {
    # Cat 1 – Giả mạo ngân hàng
    # Psychology: fear + urgency | sender: brandname (60%) | Obf: Level 1–2
    "Giả mạo ngân hàng": [
        "Vietcombank", "VCB Digibank", "BIDV", "Techcombank",
        "ACB", "MB Bank", "TPBank", "SHB Digibank", "MSB", "Sacombank",
    ],

    # Cat 2 – Đòi nợ / Đe dọa
    # Psychology: fear + authority | sender: personal_number | Obf: Level 0–1
    # Không có brand cố định – dùng tên tổ chức đòi nợ giả
    "Đòi nợ / Đe dọa": [
        "Trung tâm Thu hồi Nợ", "Phòng An ninh Điều tra", "PC02",
        "Công ty Tài chính FE", "Mcredit", "Home Credit",
        "HD Saison", "Mirae Asset",
    ],

    # Cat 3 – BHXH / Trợ cấp giả
    # Psychology: greed + urgency | sender: personal_number | Obf: Level 2–3
    "BHXH / Trợ cấp giả": [
        "BHXH Việt Nam", "Quỹ BHTN", "Bộ LĐ-TB-XH",
        "Hỗ trợ COVID-19", "Hoàn thuế TNCN", "Trợ cấp NQ-116",
    ],

    # Cat 4 – Tuyển dụng giả
    # Psychology: greed | sender: personal_number | Obf: Level 0–2
    "Tuyển dụng giả": [
        "Amazon", "TikTok", "Shopee", "Lazada", "Tiki",
        "eBay", "Cty HVS", "EMIME Company",
    ],

    # Cat 5 – Cờ bạc / Betting
    # Psychology: greed | sender: personal_number, shortcode | Obf: Level 2–3
    "Cờ bạc / Betting": [
        "789Bet", "Kwin668", "V7Bet", "Kim Long Casino",
        "8DAY", "JILI", "Awin", "Giải trí 2Q",
    ],

    # Cat 6 – Dịch vụ công giả
    # Psychology: fear + authority | sender: brandname, shortcode | Obf: Level 1–2
    "Dịch vụ công giả": [
        "Cảnh sát Giao thông", "Bộ GTVT", "Tổng cục Thuế",
        "VNeID", "Bộ Công an", "Bộ Y Tế", "Cục Viễn thông",
    ],

    # Cat 7 – Nội dung nhạy cảm
    # Psychology: greed (nhu cầu) | sender: personal_number | Obf: Level 3–5
    # Giá trị là location_platform (khu vực + nền tảng liên hệ) thay vì brand
    "Nội dung nhạy cảm": [
        "HCM – Telegram", "HCM – Zalo",
        "HN – Telegram", "HN – Zalo",
        "ĐN – Telegram",
    ],

    # Cat 8 – Crypto / Đầu tư giả
    # Psychology: greed | sender: personal_number | Obf: Level 1–3
    "Crypto / Đầu tư giả": [
        "TikTok nhiệm vụ", "Thả tim kiếm tiền", "Đặt đơn hàng online",
        "Sàn đầu tư XYZ", "Copy trade Forex", "Nhóm Telegram đầu tư",
    ],
}

# Mỗi level có 1 description ngắn gọn (cho prompt) + 1–2 concrete examples
# để model "thấy" output trông như thế nào — giảm phụ thuộc vào prior của model.
OBF_LEVEL_STYLES: dict[int, str] = {
    0: (
        "Không obfuscation — viết bình thường, đầy đủ dấu tiếng Việt, "
        "formal như tin nhắn ngân hàng/cơ quan thật. "
        "KHÔNG dùng leet, KHÔNG viết tắt, KHÔNG ký tự đặc biệt. "
        'Ví dụ output: "Tài khoản của bạn đã bị khóa. Vui lòng đăng nhập để xác thực."'
    ),
    1: (
        "Leet nhẹ — bỏ dấu tiếng Việt, thay một số nguyên âm bằng số "
        "(o→0, i→1, e→3, a→4) và chèn dấu chấm/gạch ngang xen kẽ vài từ. "
        'Ví dụ output: "T4i kh04n cua b4n d4 b1 kh04. Dang nh4p t41 vcb.vn-0nl1n3.top."'
    ),
    2: (
        "Leet nặng — bỏ dấu hoàn toàn, dùng j=gi, f=ph, w=qu, z=d, "
        "0=o, 4=a, 1=i/l, 3=e, kết hợp không đồng đều giữa các từ. "
        'Ví dụ output: "Ong (Ba) da du d!eu k!en NHAN T1EN h0 tro. Bam vao www.xkqpz.icu."'
    ),
    3: (
        "Mixed special chars — chèn @, #, !, *, ~, ^ vào giữa hoặc cuối các từ nhạy cảm, "
        "mix tiếng Anh/Việt vô trật tự, thay khoảng trắng bằng _ hoặc - ở vài chỗ. "
        'Ví dụ output: "B4N_da-du D!EU K!EN nh4n T1EN h0~tro tu quy BH#TN. Nhan t41: mo.vqxpk.com."'
    ),
    4: (
        "Dot/dash split — tách TỪng KÝ tự hoặc từng âm tiết bằng dấu chấm hay gạch ngang. "
        "Áp dụng cho ít nhất 30% từ trong tin nhắn. "
        'Ví dụ output: "A-M-A-Z-O-N c-a-n t-u-y-e-n n-h-a-n v-i-e-n. T-h-u n-h-a-p 5-0-0-k/n-g-a-y."'
    ),
    5: (
        "Extreme noise — chèn ký tự ASCII lạ (;, :, \", `, ,) xen kẽ từng âm tiết, "
        "homoglyph (l↔I↔1, 0↔O), mix chữ hoa/thường ngẫu nhiên, "
        "Unicode trông giống Latin (ä, ö, ü, ë). "
        'Ví dụ output: "tORK;iM! ay:Ma\\\"n;N,nh4n:thu\\\"0g tU quy B,H;T,N. N4p:vao K3t:b4n jNG4Y."'
    ),
}

# Range obfuscation level mong muốn cho từng category.
# Tuple (min_level, max_level) — pick_style() sẽ sample đều trong range này.
CATEGORY_OBF_RANGE: dict[str, tuple[int, int]] = {
    "Giả mạo ngân hàng":  (1, 2),   # Formal giả ngân hàng — không quá nhiễu
    "Đòi nợ / Đe dọa":    (0, 1),   # Đe dọa đọc được — Level 0/1
    "BHXH / Trợ cấp giả": (2, 3),   # BHXH hay dùng leet nặng + special chars
    "Tuyển dụng giả":      (0, 2),   # Job scam thường khá readable
    "Cờ bạc / Betting":    (2, 3),   # Gambling dùng nhiễu vừa phải
    "Dịch vụ công giả":    (1, 2),   # Giả cơ quan nhà nước — cần đọc được
    "Nội dung nhạy cảm":   (3, 5),   # Sensitive phải lách filter — nhiễu nặng
    "Crypto / Đầu tư giả": (1, 3),   # Crypto mix từ thân thiện đến leet
}


def pick_mixed_style(category: str) -> tuple[tuple[int, int], str]:
    """
    Trả về range (lo, hi) và chuỗi mô tả gộp của tất cả các level trong range đó.
    """
    lo, hi = CATEGORY_OBF_RANGE.get(category, (0, 5))
    
    mixed_style_desc = []
    for lvl in range(lo, hi + 1):
        mixed_style_desc.append(f"- MỨC {lvl}: {OBF_LEVEL_STYLES[lvl]}")
        
    combined_style = "\n".join(mixed_style_desc)
    return (lo, hi), combined_style

VALID_SENDER_TYPES = {"personal_number", "brandname", "shortcode"}


# ---------------------------------------------------------------------------
# Obfuscation level checker — heuristic nhanh, không cần ML
# ---------------------------------------------------------------------------
import re as _re

# Pre-compile patterns
_PAT_LEET_LIGHT  = _re.compile(r'[0134]')
_PAT_LEET_HEAVY  = _re.compile(r'\bj[aeiou]|[fwz][aeiou]|d!|k!|h0\b|t1en|nhan\b.*\b[0-9]')
_PAT_SPECIAL     = _re.compile(r'[@#!*~^]')
_PAT_DOT_SPLIT   = _re.compile(r'(?:[a-zA-Z0-9]-){2}[a-zA-Z0-9]|[a-zA-Z]\.[a-zA-Z]\.[a-zA-Z]')
_PAT_NOISE       = _re.compile(r'[;:"`]{2,}|[A-Z]{2}[a-z][A-Z]')


def obf_level_of(text: str) -> int:
    """
    Ước lượng obfuscation level của một chuỗi content.
    Trả về int 0–5 (best-effort, không hoàn hảo).
    Dùng để filter/warn sau khi model sinh output.
    """
    t = str(text)
    if _PAT_DOT_SPLIT.search(t):
        return 5 if _PAT_NOISE.search(t) else 4
    n_special = len(_PAT_SPECIAL.findall(t))
    if n_special >= 4 or _PAT_NOISE.search(t):
        return 5 if n_special >= 8 else 3
    if _PAT_LEET_HEAVY.search(t):
        return 2
    n_leet = len(_PAT_LEET_LIGHT.findall(t))
    if n_leet >= 4:
        return 1
    return 0


def obf_in_range(text: str, lo: int, hi: int) -> bool:
    """True nếu level của text nằm trong [lo, hi]."""
    return lo <= obf_level_of(text) <= hi


# =============================================================================
# 3. PROMPT ENGINEERING – 8 Category-Specific Templates
# =============================================================================

def _prompt_banking(brands: str, style: str, size: int) -> str:
    """Cat 1 – Giả mạo ngân hàng: fear + urgency, brandname/shortcode, Level 1–2."""
    brand_lower = brands.lower().replace(" ", "")
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo ngân hàng (label=1).
Ngân hàng bị giả mạo: {brands}
Chiến lược tâm lý: FEAR (sợ mất tài sản/bị khóa) + URGENCY (deadline giờ cụ thể)
 
ĐẶC TRƯNG CỦA LOẠI NÀY (bắt buộc áp dụng):
  - YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một ngân hàng từ danh sách trên cho mỗi dòng. KHÔNG ĐƯỢC lặp lại liên tục một ngân hàng.
  - Domain giả tương ứng với brand: dạng {brand_lower}.vn-xx.top / {brand_lower}-online.vip / {brand_lower}.cc
  - Sender type: brandname hoặc shortcode (ít khi personal_number)
  - Cú pháp chuẩn ngân hàng giả: "[{brands.upper()}] Tài khoản..." hoặc "{brands} trân trọng..."
  - Phải có CTA (call-to-action): "Nhấn vào / Đăng nhập / Xác thực tại [link]"

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu style):
VCB Digibank tran trong thong bao.tai khoan cua quy khach hien tai da bi khoa.Dang nhap www.vcbtiebink.com de xac thuc ngay hom nay|1|1|0|brandname
Vietcombank lưu ý: Bạn có 18699 điểm thưởng sẽ hết hạn sau 24 giờ, vui lòng truy cập: https://vietcombankd.cfd/vn để đổi quà.|1|1|0|brandname
UNG DUNG VCB DIGIBANK cua ban duoc PHAT HIEN KICH HOAT tren thiet bi la. Neu KHONG PHA BAN KICH HOAT vui long bam vao https://vietcombank.vn-ms.top de doi thiet bi hoac huy de tranh mat tai san|1|1|0|brandname
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 (luôn có link)
  - has_phone = 0 (ngân hàng giả không để SĐT liên hệ trực tiếp)
  - sender_type: brandname (~60%), shortcode (~40%) – KHÔNG dùng personal_number
    (KHÔNG dấu nháy đơn)
  - 40–160 ký tự
  - Domain giả KHÁC NHAU mỗi dòng (hạn chế lặp lại full domain, chỉ dùng cùng TLD pattern)
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''


def _prompt_debt_threat(brands: str, style: str, size: int, obf_level: int = 0) -> str:
    """Cat 2 – Đòi nợ / Đe dọa: fear + authority, personal_number, Level 0–1."""
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn đòi nợ / đe dọa (label=1).
Tổ chức đòi nợ giả mạo (chỉ dùng cho Sub-type A): {brands}
Chiến lược tâm lý: FEAR (mất uy tín, bị điều tra hình sự) + AUTHORITY (cơ quan pháp lý giả)

ĐẶC TRƯNG BẮT BUỘC:
  - Mở đầu bằng 1 trong: "CANH BAO LAN CUOI!!!" / "[CANH CAO LAN CUOI]:" / "TB KHAN:"
  - KHÔNG có URL/link (has_url luôn = 0)
  - sender: personal_number (luôn luôn)

  SUB-TYPE A – Công ty tài chính / đòi nợ tư nhân (~70% batch):
    → YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một tổ chức từ danh sách trên cho mỗi dòng.
    → BẮT BUỘC: tên người Việt 3 tiếng ngẫu nhiên (KHÔNG lặp lại giữa các dòng)
    → BẮT BUỘC: số CMND/CCCD giả (9 hoặc 12 chữ số, KHÔNG toàn 0 hoặc toàn 1)
    → BẮT BUỘC: số tiền KHÔNG tròn: ví dụ 3,947,000VND / 48,554,336VND / 1,285,000VND
    → Deadline cụ thể: "truoc 16H Ngay DD/MM" / "Trong 24H nua" / "truoc 17g hom nay"
    → Đe dọa: "Cong Khai HINH ANH va THONG TIN", "thong bao nguoi than gia dinh noi lam viec",
      "ghi no xau CIC"
    → CTA: số điện thoại local (0xxxxxxxxx) hoặc ZALO để liên hệ (has_phone = 1 nếu có local SĐT)

  SUB-TYPE B – Giả mạo cơ quan điều tra (~30% batch):
    → Dùng "Ong/Ba" hoặc "O/B" generic, KHÔNG cần tên/CMND cụ thể
    → Nhấn mạnh "trach nhiem hinh su", "Phong AN NINH DIEU TRA", "dieu tra toan bo thong tin"
    → CTA: SĐT dạng quốc tế (84xxxxxxxxx) hoặc không có SĐT (has_phone = 0)
    → Deadline: "truoc 17g hom nay" hoặc "trong vong 24H"

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}

VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên tên/CMND/số tiền, dùng làm tham chiếu style):
CANH BAO LAN CUOI!!! Trong 24H nua Ong/Ba Nguyen Thi Lan CMND: 046079231845 phai lien he gap SDT/ZALO: 0352891743 gap Tran Van Duc de THOA THUAN-GIAM NO. Neu KHONG HOP TAC thanh toan KHOAN VAY 3,947,000VND se Cong Khai HINH ANH va THONG TIN len XA HOI, DIA PHUONG va thong bao nguoi than.|1|0|1|personal_number
Trung Tam Tin Dung F&TB den Ong/Ba: So CMND: 024091768345. Chung toi nghi ngo Ong/Ba lam dung tin nhiem chiem doat tai san voi so tien: 48,554,336VND (tien goc). Canh bao lan cuoi truoc 16H Ngay 25/03 thanh toan toi thieu: 3,725,583VND. Tiep tuc bat hop tac, moi rui ro ve Uy tin Danh du Tai san Ong/Ba tu chiu.|1|0|0|personal_number
[CANH CAO LAN CUOI]: Chung toi da nhac nho nhieu lan nhung O/B van bat hop tac. Truoc 17g hom nay chua thanh toan, Phong AN NINH DIEU TRA se vao cuoc dieu tra toan bo thong tin hinh anh cua O/B va nhung nguoi lien quan se phai chiu trach nhiem hinh su. LH khi san sang: 84912654378.|1|0|0|personal_number

QUY TẮC FORMAT (pipe-delimited):
  content|1|0|has_phone_number|personal_number
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (KHÔNG BAO GIỜ có link)
  - has_phone = 1 nếu content chứa SĐT local 10 số (0xxxxxxxxx), 0 nếu không
  - sender_type = personal_number (luôn luôn)
  - 80–300 ký tự (dài hơn các loại smishing khác – đặc trưng đòi nợ)
  - KHÔNG lặp tên người, CMND, số tiền giữa các dòng trong cùng batch

QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''


def _prompt_bhxh(brands: str, style: str, size: int, obf_level: int = 2) -> str:
    """Cat 3 – BHXH / Trợ cấp giả: greed + urgency, personal_number, Level 2–3."""
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo BHXH/BHTN (label=1).
Tổ chức / chương trình bị giả mạo: {brands}
Chiến lược tâm lý: GREED (nhận tiền miễn phí) + URGENCY (quá hạn không nhận được)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một tổ chức/chương trình từ danh sách trên cho mỗi dòng.
  - Viện dẫn: "theo NQ-116", "Quyết định BHXH", "quỹ BHTN"
  - Điều kiện: "Ban da du d!eu k!en" hoặc "da du dieu kien"
  - CTA: "Bam vao / Nhan tai [domain.icu hoặc .com]"
  - Cảnh báo deadline: "QUA HAN SE KH0NG DUOC CHAP NHAN"
  - Kết thúc bằng 4 ký tự random (ví dụ: hkDF, oZGa, SP0s – làm tracking ID giả)
  - Domain pattern: www.[5-6 ký tự ngẫu nhiên].icu hoặc mo.[random].com
  - Sender type: luôn là personal_number

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên domain/code, dùng làm tham chiếu style):
[T.B] BHXH: Ong (Ba) da du d!eu k!en NHAN T1EN h0 tro tu quy BH-TN. Bam vao www.mvndc.icu de lay. QUA HAN SE KH0NG_DUOC CHAP NHAN! oZGa|1|1|0|personal_number
Theo _NQ_116, Ong (Ba) da du d!eu k!en NHAN TIEN ho tro tu quy BHTN. Bam vao www.pwmgh.icu de lay. QUA HAN SE KHONG_DUOC CHAP NHAN! hkDF|1|1|0|personal_number
Ong/(Ba) da du d!eu'k!en NHAN'TIEN ho tro tu quy-BHTN. Bam'vao www.opaxa.icu de_'lay. QUA-HAN' SE KH0ng DUOC CHAP_NAHN! JKqc|1|1|0|personal_number
BHXH VN: Ong(Ba) DU DIEU KIEN nhan tien ho tro BHTN dot 3. Nhan tai: mo.cvxqa.com truoc khi QUA HAN. tPkm|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link domain.icu / mo.[random].com, 0 nếu không
  - sender_type = personal_number (luôn luôn)
  - 60–180 ký tự
  - Domain random chars phải KHÁC NHAU mỗi dòng (không lặp lại mvndc, pwmgh, opaxa, cvxqa từ ví dụ)
  - Mã xác nhận cuối (4 ký tự) KHÁC NHAU mỗi dòng, không dùng lại oZGa/hkDF/JKqc/tPkm từ ví dụ
  - Đa dạng TLD: ~70% .icu, ~30% .com (dạng mo.[random].com) trong cùng một batch
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''


def _prompt_job_scam(brands: str, style: str, size: int) -> str:
    """Cat 4 – Tuyển dụng giả: greed + urgency, personal_number, Level 0–2."""
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn tuyển dụng giả mạo (label=1).
Nền tảng / Công ty bị giả mạo: {brands}
Chiến lược tâm lý: GREED (lương hấp dẫn, làm tại nhà) + URGENCY (tuyển gấp, số lượng hạn chế)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một công ty/nền tảng từ danh sách trên cho mỗi dòng. ĐẢM BẢO sự xen kẽ giữa các công ty.
  - Tên công ty/platform ở đầu câu: "{brands} cần tuyển..." hoặc "tôi là trưởng phòng {brands}..."
  - Thu nhập hàng ngày (KHÔNG dùng lương tháng đơn độc): "500k~3000k/ngày", "800.000đ/ngày",
    "350–999k/ngay"
  - Điều kiện dễ: "thao tác đơn giản", "không cần kinh nghiệm", "làm tại nhà"
  - Độ tuổi: "22–60 tuổi" hoặc "23–65 tuổi" (không quá 18, không dưới 65)
  - CTA Zalo: "Liên hệ Zalo: zalo.me/84xxxxxxxxx" hoặc số trực tiếp "Zalo: 84xxxxxxxxx"
  - Sender: personal_number (luôn luôn)
  - Sub-type tùy platform:
      * Amazon / eBay: "xử lý đơn đặt hàng TMĐT", Zalo link + số riêng (has_url=1, has_phone=1)
      * TikTok: "xử lý đơn hàng trên nền tảng TikTok", "nhận tiền sau 13–25 phút" (has_url=1, has_phone=1)
      * Shopee / Lazada: "xử lý đơn + đánh giá sản phẩm", chỉ Zalo link (has_url=1, has_phone=0)
      * Tiki: "đặt hàng để nâng thứ hạng cửa hàng", số Zalo trực tiếp (has_url=0, has_phone=1)
      * Cty generic (HVS, EMIME): "tuyển nhân viên bán thời gian", Zalo link + số riêng

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên số Zalo/SĐT, dùng làm tham chiếu style):
Amazon cần tuyển nhân viên làm việc tại nhà!!! Yêu cầu 23-60 tuổi. Lương 10tr-50tr/tháng. Ít nhất 500k~3000k/ngày, thao tác đơn giản. Liên hệ Zalo: zalo.me/84938271045 Zalo: 84938271045|1|1|1|personal_number
Xin chào, tôi là trưởng phòng nhân sự của Cty HVS, tuyển nhân viên bán thời gian. Thu nhập 15-30tr/tháng (500k-1tr/ngày). Làm tại nhà, mọi lúc mọi nơi. Tuổi 22-65. Zalo: zalo.me/84962183074 hoặc 84962183074|1|1|1|personal_number
Xin chào, mình là giám đốc marketing của Tiki. Cửa hàng Tiki đang tuyển số lượng lớn nhân viên chuyên đặt hàng để nâng cao số lượng giao dịch và thứ hạng cửa hàng. Chỉ cần có kinh nghiệm mua sắm trực tuyến, mỗi ngày bạn có thể dễ dàng kiếm 800.000đ bằng điện thoại di động. Lương quyết toán ngay trong ngày. Zalo: 84769231508|1|0|1|personal_number
Tiktok dang tuyen nhan vien lam viec tai nha!!! Mo ta cong viec: Xu ly don hang tren nen tang Tiktok. Thu nhap 350-999k/ngay. Thao tac don gian, nhan tien sau 13-25 phut. Lien he ngay: zalo.me/84937512094 zalo:84937512094|1|1|1|personal_number
Shopee tuyen gap nhan vien xu ly don hang va danh gia san pham tai nha!!! Yeu cau 22-55 tuoi. Thu nhap 500k-1.5tr/ngay. Nhan tien trong ngay sau moi nhiem vu hoan thanh. Khong can kinh nghiem, co nguoi huong dan cu the. Dang ky: zalo.me/84918273645|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url: 1 nếu có zalo.me/xxx link, 0 nếu chỉ có SĐT
  - has_phone: 1 nếu số điện thoại được liệt kê riêng trong text (không chỉ trong URL)
  - sender_type = personal_number (luôn luôn)
  - 80–250 ký tự
  - Phân biệt sub-type rõ ràng: KHÔNG toàn bộ cùng platform trong một batch
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''


def _prompt_gambling(brands: str, style: str, size: int, obf_level: int = 2) -> str:
    """Cat 5 – Cờ bạc / Betting: greed + FOMO, personal_number/shortcode, Level 2–3."""
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn mời gọi cờ bạc/betting (label=1).
Nhà cái / Platform: {brands}
Chiến lược tâm lý: GREED (bonus khủng, rút tiền ngay) + FOMO (khuyến mãi có hạn)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một nhà cái từ danh sách trên cho mỗi dòng. 
  - Luôn có URL (has_url = 1 trong hầu hết trường hợp).
  - Sub-type (xen kẽ trong batch):
      * "nạp X nhận Y": "Nap Xk nhan Yk", "1 vong cuoc la rut MAXX X.XXXk",
        "No Hu", "Ban Ca", "BCR", tracking code 4–5 ký tự cuối, URL t.ly/[code]
      * Platform promo: "tai app", "x3 nap dau", list game bị dot-insert
        (TLMN, X.oc-D.ia, N.ohu), URL .cc/.tech domain
      * Casino formal: "Baccarat trực tiếp", "chọi gà", "xổ số", "CSKH 24/24",
        "gửi và rút trong X phút", short domain (5–6 ký tự .com)
      * Đại lý/hoa hồng: "tuyển đại lý", "hoa hồng X%", Zalo có số, URL .vip/.bet,
        sender = shortcode (đặc trưng duy nhất dùng shortcode)
  - Domain pattern: t.ly/[code] / .cc / .tech / .vip / .bet / [5–6char].com
  - Sender: personal_number (hầu hết), shortcode (chỉ với sub-type đại lý)

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên tracking code/domain/URL, dùng làm tham chiếu style):
Dang ky + 558k! (Nap 50k nhan 108k) 1 vong cuoc la rut MAXX 8.888k. No Hu. Ban Ca. BCR... DK: t.ly/DJyj1 ZnReS|1|1|0|personal_number
G.em moi Awin tag ban 299k khi tai app, x3 nap dau, rut ngay ko can nap, choi TLMN, X.oc-D.ia, N.ohu...dinhcao. click: https://athd.cc/5TyUoM|1|1|0|personal_number
Để chào mừng năm mới, Kim Long tặng ngay 68-888K khi đăng ký tại: d82yy.com, hãy liên hệ CSKH để nhận. Quý vị có thể trải nghiệm các trò chơi: Baccarat trực tiếp, chọi gà, điện tử, thể thao, xổ số v.v. Gửi và rút tiền trong vòng 3 phút, CSKH 24/24|1|1|0|personal_number
V7 top 3 nha cai VN, tuyen dai ly voi muc hoa hong len den 50%, tra hoa hong nhieu hinh thuc, lien he zalo Van: 0932187456 Link: https://v7bet.vip|1|1|1|shortcode
D/Ki + 558k. ( N-ap 5Ok nhän 1O8k ) 1 vong cuöc la rut MAXX 8.888k. Htra tuc thi 3%. N/ö h/ü - B/än C/ä. BCR... DK: ibvif.cc/LbFzDg ~noyc|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 (luôn luôn – đặc trưng của gambling scam)
  - has_phone: 1 chỉ với sub-type đại lý (có Zalo + SĐT), 0 còn lại
  - sender_type: personal_number hoặc shortcode (shortcode chỉ cho đại lý)
  - 40–180 ký tự
  - Tracking code cuối KHÁC NHAU mỗi dòng (KHÔNG copy từ few-shot)
  - Domain string KHÁC NHAU mỗi dòng (chỉ dùng TLD pattern, KHÔNG lặp full domain)
  - KHÔNG dùng brand name thật trong domain (ví dụ: 789bet.com → sai, dùng domain giả)
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''

def _prompt_govt_fake(brands: str, style: str, size: int) -> str:
    """Cat 6 – Dịch vụ công giả: fear + authority, brandname/shortcode, Level 1–2."""
    brand_slug = brands.lower().replace(" ", "-")
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo cơ quan nhà nước (label=1).
Cơ quan bị giả mạo: {brands}
Chiến lược tâm lý: FEAR (vi phạm pháp luật, bị xử phạt) + AUTHORITY (danh nghĩa nhà nước)
 
ĐẶC TRƯNG BẮT BUỘC:
  YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một cơ quan từ danh sách trên cho mỗi dòng.
  - Mở đầu bằng tên cơ quan: "{brands}: ..." hoặc "[{brands.upper()}]" hoặc "Bộ ... xin thông báo"
  - Nội dung tùy sub-type:
      * CSGT / Bộ GTVT: "hồ sơ vi phạm giao thông", "biên lai chưa nộp phạt",
        "thông báo cuối cùng", CTA link hoặc SĐT
      * Tổng cục Thuế / Hoàn thuế: "đủ điều kiện hoàn thuế TNCN", link .vip/.top
      * VNeID / Bộ Công an: "cập nhật thông tin định danh", "xác thực tài khoản VNeID"
  - Domain giả khớp với tên brand: dichvucong[s].top / phatnguoi.xyz / hoanthue-tncn.vip / vnta-gov.cc / {brand_slug}-gov.top
  - Sender: brandname (50%), shortcode (30%), personal_number (20%)
  - has_url = 1 nếu có link, 0 nếu chỉ có SĐT liên hệ

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên domain/SĐT, dùng làm tham chiếu style):
Cảnh sát Giao thông Việt Nam: Hồ sơ vi phạm giao thông được lưu trữ dưới tên của bạn. Để biết thêm thông tin, vui lòng truy cập https://dichvucongs.top/vn|1|1|0|brandname
Bộ giao thông vận tải, xin thông báo ông/bà có biên lai chưa nộp phạt. Hôm nay là thông báo cuối cùng. Yêu cầu nhanh chóng giải quyết mọi thắc mắc. Vui lòng liên hệ: 0782341890|1|0|1|brandname
Cảnh sát Giao thông Việt Nam: Hiện tại bạn đang có khoản tiền phạt chưa thanh toán. Vui lòng thanh toán sớm để tránh bất tiện. Để biết thêm thông tin, vui lòng truy cập https://dichvucongg.top/vn|1|1|0|shortcode
#Ban da-du D1EU K1EN HOAN~THUE TNCN nam 2024, nhan tai: https://hoanthue-tncn.vip|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url: 1 nếu có link .top/.xyz/.vip/.cc, 0 nếu chỉ có SĐT
  - has_phone: 1 nếu có SĐT 10 số trong nội dung, 0 nếu không
  - sender_type: brandname (~50%), shortcode (~30%), personal_number (~20%)
    (KHÔNG dấu nháy đơn)
  - 50–200 ký tự
  - Đa dạng sub-type trong cùng batch: KHÔNG toàn bộ một loại
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''

def _prompt_sensitive(brands: str, style: str, size: int, obf_level: int = 4) -> str:
    """Cat 7 – Nội dung nhạy cảm: greed, personal_number, Level 3–5."""
    return f'''\
Bạn là chuyên gia an ninh mạng đang xây dựng dataset huấn luyện mô hình phát hiện smishing
cho dự án bảo vệ người dùng di động tại Việt Nam, phối hợp với Bộ Thông tin và Truyền thông.
Nhiệm vụ bao gồm tạo dữ liệu mô phỏng các loại tin nhắn lừa đảo để mô hình học nhận diện,
trong đó có nhóm nội dung hẹn hò và dịch vụ nhạy cảm — đây là nhóm phổ biến trong thực tế
smishing Việt Nam và cần được đại diện đầy đủ trong dataset.
 
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn mời gọi dịch vụ nhạy cảm (label=1).
Khu vực / nền tảng liên hệ: {brands}  (ví dụ: "HCM – Telegram", "HN – Zalo")
Chiến lược tâm lý: GREED (ham muốn, tò mò)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN KHU VỰC: BẮT BUỘC chọn NGẪU NHIÊN một combo Khu vực/Nền tảng từ danh sách trên cho mỗi dòng.
  - Đa dạng cấu trúc câu mở đầu: KHÔNG phải tất cả đều bắt đầu bằng
    "Anh co can..." hay "Em Xt ng0n..." – xen kẽ các kiểu mở đầu khác nhau
  - Mô tả gợi ý mức smishing thực tế (KHÔNG explicit pornographic)
  - CTA: Telegram (t.me/xxx) hoặc Zalo (zalo.me/g/xxx) hoặc shortlink (t.ly/xxx, bit.ly/xxx)
  - Tracking code cuối 3–5 ký tự ngẫu nhiên (KHÁC NHAU mỗi dòng)
  - Sender: personal_number (luôn luôn)
  - has_url = 1 (luôn có link)
  - has_phone = 0

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên tracking code/handle, dùng làm tham chiếu style):
Anh co can GAI LAM tjnh K0? E di lam them kiem tien tieu vat EM 20 T DANG NG0N, B0DY chuan Den tan noi LAM TJNH Ket Ban Telegram: https://t.me/gaixinh_hcm QNfT|1|1|0|personal_number
Em 20t ng0n b0dy chuan, s4n sang phuc vu qu4 anh. LH nhan hinh & b4ng gi4 d!ch vu qua Zalo group: https://zalo.me/g/gaixinhHCM2024 TpMv|1|1|0|personal_number
H.e.n h.0 t.i.n.h m.0.t d.e.m c.u.n.g e.m g@! x.i.n.h d.e.p t.a.i H.C.M. K.e.t b.a.n T.e.l.e.g.r.a.m: https://sourl.cn/abc123 dKqr|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|1|0|personal_number
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 (luôn luôn)
  - has_phone = 0 (luôn luôn)
  - sender_type = personal_number (luôn luôn)
  - 40–160 ký tự (Level 4–5 dot-split có thể dài hơn – tối đa 160)
  - Tracking code cuối KHÁC NHAU mỗi dòng
  - Handle/path URL phải ngẫu nhiên và KHÁC NHAU mỗi dòng
  - KHÔNG dùng lại handle từ ví dụ: gaixinh_hcm, gaixinhHCM2024
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''

def _prompt_crypto(brands: str, style: str, size: int, obf_level: int = 2) -> str:
    """Cat 8 – Crypto / Đầu tư giả: greed, personal_number, Level 1–3."""
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn đầu tư/kiếm tiền online giả (label=1).
Kịch bản: {brands}
Chiến lược tâm lý: GREED (thu nhập thụ động, dễ dàng, không cần vốn)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN KỊCH BẢN: BẮT BUỘC chọn NGẪU NHIÊN một kịch bản từ danh sách trên cho mỗi dòng.
  - Điểm nhấn: "chỉ cần X phút/ngày", "không cần vốn/kinh nghiệm",
    "kiếm X00k–Xtr mỗi ngày", "giáo viên/chuyên viên hướng dẫn"
  - Sub-type (chọn ngẫu nhiên mỗi dòng):
      * "thả tim / bình luận": 10 nhiệm vụ/ngày, 100k/ngày, trả cuối ngày (has_url=0)
      * "nhiệm vụ Telegram": giáo viên hướng dẫn, Telegram group link (has_url=1)
      * "chuyển khoản đầu tư": tên công ty đầu tư giả, STK ngân hàng, không link (has_url=0)
  - Tone: thân thiện, tự nhiên như người quen nhắn tin (KHÔNG formal, KHÔNG all-caps)
  - Sender: personal_number (luôn luôn)
  - has_phone = 0 (không dùng SĐT để liên hệ)

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên handle/STK, dùng làm tham chiếu style):
Chào bạn, mình là Hùng, chuyên viên hỗ trợ. Bạn đang muốn làm công việc thả tim video kiếm tiền bên mình đúng không? Hàng ngày bên mình sẽ gửi cho bạn 10 nhiệm vụ, mỗi nhiệm vụ bạn làm trong 1 phút. Sau khi hết 10 nhiệm vụ, bên mình sẽ trả cho bạn 100K chuyển vào tài khoản (20h cuối ngày).|1|0|0|personal_number
Chi cän 2O phut möi ngäy giäo vien chuyen nghiep cö the huong dän ban kiem 500k-3000k, Them Telegram: t.me/huongnghieptainha01|1|1|0|personal_number
Anh/chi hay chuyen so tien can nap vao tai khoan sau, sau do chup man hinh em se lam lenh nap vao tai khoan dau tu CSI ngay. NH MSB STK: 04001023847291 TK: CONG TY TNHH DAU TU BDS SSG|1|0|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url: 1 nếu có Telegram link (t.me/xxx), 0 nếu không có link
  - has_phone = 0 (luôn luôn)
  - sender_type = personal_number (luôn luôn)
  - 40–220 ký tự
  - Đa dạng sub-type trong cùng batch: KHÔNG toàn bộ một loại
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.\
'''

# Dispatch table: category name → template function
_PROMPT_DISPATCH: dict[str, object] = {
    "Giả mạo ngân hàng":  _prompt_banking,
    "Đòi nợ / Đe dọa":    _prompt_debt_threat,
    "BHXH / Trợ cấp giả": _prompt_bhxh,
    "Tuyển dụng giả":      _prompt_job_scam,
    "Cờ bạc / Betting":    _prompt_gambling,
    "Dịch vụ công giả":    _prompt_govt_fake,
    "Nội dung nhạy cảm":   _prompt_sensitive,
    "Crypto / Đầu tư giả": _prompt_crypto,
}


def build_prompt(category: str, brands: str, style: str, size: int) -> str:
    """Gọi tới category-specific template với chuỗi brands và chuỗi style đã mix."""
    fn = _PROMPT_DISPATCH.get(category)
    if fn is None:
        raise ValueError(f"Category không xác định: {category!r}")
    
    # Gọi hàm template với các tham số mới
    return fn(brands=brands, style=style, size=size)


# =============================================================================
# 4. GỌI API & XỬ LÝ RESPONSE
# =============================================================================
def call_api_with_retry(prompt: str) -> str:
    """Gọi Gemini API với cơ chế retry + exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=prompt,
                            config=generation_config
                        )
            return response.text.strip()
        except Exception as exc:
            wait_secs = 20 * attempt
            print(f"  ⚠️  Lỗi API (lần {attempt}/{MAX_RETRIES}): {exc}. Nghỉ {wait_secs}s...")
            time.sleep(wait_secs)

    print("  ❌ Hết retry. Bỏ qua batch này.")
    return ""


def extract_valid_rows(
    raw_text: str,
    expected_obf_lo: int = 0,
    expected_obf_hi: int = 5,
) -> list[list[str]]:
    """
    Parse pipe-delimited output từ LLM → trả về list các row đã parsed.
    Dùng | làm delimiter: LLM không cần quote, không cần escape.
    Để tránh lỗi khi content tình cờ chứa |, luôn lấy LAST 4 parts làm metadata.

    obf_check (soft): rows lệch level bị đánh dấu warn nhưng KHÔNG bị reject —
    tránh drop quá nhiều mẫu hợp lệ do heuristic không hoàn hảo.
    """
    cleaned = raw_text.replace("```csv", "").replace("```", "").strip()
    valid: list[list[str]] = []
    obf_warn = 0

    for line in cleaned.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("content"):
            continue

        parts = line.split("|")
        if len(parts) < 5:
            continue

        # Lấy 4 cột cuối làm metadata (robust kể cả khi content chứa |)
        label_val  = parts[-4].strip().strip("'\"")
        has_url    = parts[-3].strip().strip("'\"")
        has_phone  = parts[-2].strip().strip("'\"")
        sender     = parts[-1].strip().strip("'\"")
        content    = "|".join(parts[:-4]).strip()

        if label_val != "1":
            continue
        if sender not in VALID_SENDER_TYPES:
            continue
        if has_url not in ("0", "1") or has_phone not in ("0", "1"):
            continue
        if not content:
            continue

        # Soft obf_check: warn nếu level lệch khỏi expected range
        if not obf_in_range(content, expected_obf_lo, expected_obf_hi):
            obf_warn += 1

        valid.append([content, label_val, has_url, has_phone, sender])

    if obf_warn > 0:
        warn_pct = obf_warn / max(len(valid), 1) * 100
        if warn_pct >= 30:
            print(f"  ⚠️  obf_check: {obf_warn}/{len(valid)} dòng ({warn_pct:.0f}%) "
                  f"lệch khỏi Level {expected_obf_lo}–{expected_obf_hi}. "
                  f"Kiểm tra style hoặc few-shot có lấn át prompt không.")

    return valid


# =============================================================================
# 5. CHECKPOINT – LOAD NỘI DUNG HIỆN CÓ VÀO BỘ NHỚ
# =============================================================================
def load_seen_contents(filepath: str) -> set[str]:
    """
    Đọc file output hiện có và trả về set các chuỗi content đã tồn tại.

    Dùng set để:
      - Đếm unique samples chính xác (bỏ qua duplicate từ session cũ)
      - O(1) lookup khi lọc trùng từng batch trong session mới
    """
    if not os.path.exists(filepath):
        return set()
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        return set(df["content"].dropna().astype(str))
    except Exception:
        return set()


# =============================================================================
# 6. TIẾN TRÌNH THỰC THI
# =============================================================================
def main() -> None:
    if not API_KEY:
        raise ValueError("API_KEY chưa được thiết lập. Dùng biến môi trường GEMINI_API_KEY.")

    # -------------------------------------------------------------------------
    # Khởi tạo file nếu chưa có
    # -------------------------------------------------------------------------
    if not os.path.exists(OUTPUT_FILE):
            # Lấy đường dẫn thư mục cha từ OUTPUT_FILE
            output_dir = os.path.dirname(OUTPUT_FILE)
            
            # Nếu đường dẫn thư mục cha tồn tại và chưa được tạo, thì tạo nó
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["content", "label", "has_url", "has_phone_number", "sender_type"])

    # -------------------------------------------------------------------------
    # Load toàn bộ content đã sinh vào set – dùng xuyên suốt session này.
    # len(seen_contents) = số mẫu UNIQUE thực sự (khác với raw row count).
    # -------------------------------------------------------------------------
    seen_contents: set[str] = load_seen_contents(OUTPUT_FILE)
    current_total: int = len(seen_contents)

    if current_total >= TOTAL_SAMPLES:
        print(f"✅ File đã đủ {current_total} mẫu unique. Không cần sinh thêm.")
        return

    print(f"🚀 Bắt đầu sinh smishing. Hiện có: {current_total}/{TOTAL_SAMPLES} mẫu unique.")

    # -------------------------------------------------------------------------
    # Vòng sinh dữ liệu
    # -------------------------------------------------------------------------
    while current_total < TOTAL_SAMPLES:
        batch_size = min(BATCH_SIZE, TOTAL_SAMPLES - current_total)

        category           = random.choice(list(SCENARIOS.keys()))
        brands_list        = SCENARIOS[category]
        brands_str         = ", ".join(brands_list)
        (lo, hi), style_prompt = pick_mixed_style(category)
        print(f"🔄 [{current_total}/{TOTAL_SAMPLES}] Category: {category} "
              f"[Mix Brands: {len(brands_list)} brands] [Mix Obf Level: {lo}–{hi}]")

        prompt   = build_prompt(category, brands_str, style_prompt, batch_size)
        raw_text = call_api_with_retry(prompt)

        if not raw_text:
            # API thất bại hoàn toàn sau retry – thử lại vòng tiếp theo
            continue

        valid_rows = extract_valid_rows(raw_text, expected_obf_lo=lo, expected_obf_hi=hi)
        if not valid_rows:
            print("  ⚠️  Không có dòng pipe-delimited hợp lệ trong response. Bỏ qua batch.")
            continue

        # Lọc trùng: chỉ giữ các dòng có content CHƯA tồn tại trong seen_contents.
        # Điều này bảo vệ cả trùng lặp trong session hiện tại lẫn giữa các ngày chạy.
        new_rows   = [row for row in valid_rows if row[0].strip() not in seen_contents]
        duplicates = len(valid_rows) - len(new_rows)

        if not new_rows:
            print(f"  ⚠️  Toàn bộ {len(valid_rows)} dòng đã tồn tại. Bỏ qua batch.")
            time.sleep(SLEEP_BETWEEN_BATCHES)
            continue

        # Ghi các dòng mới vào file (append – không ghi đè)
        with open(OUTPUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(new_rows)

        # Cập nhật seen_contents ngay lập tức để các batch tiếp theo trong cùng session
        # cũng được kiểm tra đúng (tránh trùng trong 1 lần chạy dài).
        for row in new_rows:
            seen_contents.add(row[0].strip())

        added          = len(new_rows)
        current_total += added
        dup_msg = f" ({duplicates} trùng, đã bỏ)" if duplicates else ""
        print(f"  ✅ Thêm {added} dòng mới{dup_msg}. Unique tổng: {current_total}/{TOTAL_SAMPLES}")

        if current_total < TOTAL_SAMPLES:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # -------------------------------------------------------------------------
    # Hậu xử lý cuối: chuẩn hóa sender_type + dedup an toàn lần cuối
    # (seen_contents đã lọc trong quá trình chạy, bước này chỉ là safety net)
    # -------------------------------------------------------------------------
    print("🧹 Chuẩn hóa file cuối cùng...")
    df = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
    before = len(df)
    df.dropna(subset=["content"], inplace=True)
    df.drop_duplicates(subset=["content"], inplace=True)
    df["sender_type"] = df["sender_type"].str.strip().str.strip("'\"")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"🎊 Hoàn thành! {before} → {len(df)} mẫu sau lọc. File: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
