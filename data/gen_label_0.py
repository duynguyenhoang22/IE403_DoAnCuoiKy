"""
Sinh dữ liệu SMS hợp lệ tổng hợp (Label = 0) dùng Gemini API.

Kiến trúc kế thừa từ gen_label_1.py:
  - google.genai SDK mới (cùng với gen_label_1.py)
  - Pipe-delimited format (|) cho output
  - load_seen_contents() deduplication
  - Batch generation với retry + exponential backoff
  - 8 category-specific prompt templates
  - SCENARIOS_LABEL0, CATEGORY_FORMAL_RANGE, pick_formality_style()

Cải tiến so với v1:
  [QUOTA]   Category quota sampling thay vì random.choice() thuần túy
              → đảm bảo phân phối đều, không bỏ sót category
  [CONTEXT] CONTEXT_VARIANTS per-category inject vào prompt mỗi batch
              → tăng variation không gian từ 3 chiều lên 5 chiều
  [VOCAB]   VOCAB_HINTS inject ngẫu nhiên vào Layer 4 constraints
              → lexical diversity tự nhiên, phá vỡ template cứng
  [TEMP]    PER_CATEGORY_TEMPERATURE thay vì temperature cố định
              → template-cứng dùng temp thấp, personal dùng temp cao
  [VALID]   Thêm F7 URL-consistency check
              → bắt trường hợp has_url=0 nhưng content có URL

Chạy độc lập:
    python gen_label_0.py

Biến môi trường:
    GEMINI_API_KEY – API key Gemini
"""

import csv
import os
import random
import re as _re
import time
from collections import defaultdict

from dotenv import load_dotenv
from google import genai
from google.genai import types
import pandas as pd

# =============================================================================
# 1. CẤU HÌNH HỆ THỐNG & API
# =============================================================================
load_dotenv()
API_KEY    = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-2.5-flash"

OUTPUT_FILE           = "synthetic_data/synthetic_legitimate_label0.csv"
TOTAL_SAMPLES         = 3000
BATCH_SIZE            = 40
SLEEP_BETWEEN_BATCHES = 12
MAX_RETRIES           = 3

if not API_KEY:
    raise ValueError("⚠️ GEMINI_API_KEY chưa được thiết lập!")

client = genai.Client(api_key=API_KEY)

# Label 0 là nội dung hoàn toàn lành mạnh – KHÔNG cần tắt safety filters
SYSTEM_PROMPT_LABEL0 = (
    "Bạn là chuyên gia tạo dữ liệu huấn luyện cho mô hình phân loại SMS tại Việt Nam. "
    "Nhiệm vụ là tạo dữ liệu mô phỏng tin nhắn SMS hợp lệ (label=0) – bao gồm thông báo "
    "từ ngân hàng, viễn thông, thương mại điện tử, logistics, dịch vụ công và tin nhắn cá nhân "
    "– phản ánh đúng thực tế SMS tại Việt Nam."
)

# [TEMP] Temperature khác nhau theo category:
# - Template cứng (ngân hàng, viễn thông, logistics): temp thấp → nhất quán format
# - Semi-formal (y tế, dịch vụ công): temp trung bình
# - Personal/OTP và quảng cáo: temp cao → lexical diversity tự nhiên
PER_CATEGORY_TEMPERATURE: dict[str, float] = {
    "Ngân hàng thật":             0.75,  # Format cứng, cần chính xác brand/số
    "Viễn thông":                 0.78,  # Format tương đối cứng
    "Thương mại điện tử":         0.80,  # Template mềm, mã đơn vary nhiều
    "Vận chuyển":                 0.78,  # Tracking ID vary, format cứng
    "Quảng cáo hợp lệ":          0.90,  # Cần ngôn ngữ đa dạng nhất
    "Dịch vụ y tế":               0.85,  # Formal-friendly range rộng
    "Dịch vụ công thật":          0.78,  # Văn phong hành chính tương đối cố định
    "Tin nhắn cá nhân và OTP":    0.92,  # Personal phải tự nhiên, đa dạng cao nhất
}


def _make_config(category: str) -> types.GenerateContentConfig:
    """Tạo GenerateContentConfig với temperature theo category."""
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT_LABEL0,
        temperature=PER_CATEGORY_TEMPERATURE.get(category, 0.85),
    )


# =============================================================================
# 2. KỊCH BẢN & PHONG CÁCH FORMAL HÓA
# =============================================================================
SCENARIOS_LABEL0: dict[str, list[str]] = {
    # Cat 1 – Ngân hàng thật
    "Ngân hàng thật": [
        "MB Bank", "Vietcombank", "BIDV", "Techcombank",
        "ACB", "VPBank", "TPBank", "Agribank", "Sacombank",
        "SHB", "MSB", "VIB", "HDBank", "OCB",
    ],

    # Cat 2 – Viễn thông
    "Viễn thông": [
        "Viettel", "Vinaphone", "MobiFone", "Vietnamobile",
        "Gmobile", "iTel", "Wintel",
    ],

    # Cat 3 – Thương mại điện tử
    "Thương mại điện tử": [
        "Shopee", "Tiki", "Lazada", "Sendo", "TikTok Shop",
    ],

    # Cat 4 – Vận chuyển & Logistics
    "Vận chuyển": [
        "GHN (Giao Hàng Nhanh)", "GHTK (Giao Hàng Tiết Kiệm)",
        "Viettel Post", "Ninja Van", "J&T Express", "Best Express", "SPX Express",
    ],

    # Cat 5 – Quảng cáo hợp lệ
    "Quảng cáo hợp lệ": [
        "MoMo", "Grab", "ZaloPay", "ShopeePay",
        "KFC", "Lotteria", "McDonald's", "Jollibee",
        "WinMart", "Co.opmart", "Bách hóa xanh",
        "Highland Coffee", "The Coffee House",
    ],

    # Cat 6 – Dịch vụ y tế
    "Dịch vụ y tế": [
        "Bệnh viện Bạch Mai", "Bệnh viện Việt Đức", "BV Nhi Trung Ương",
        "BV 108", "BV Đại học Y Hà Nội", "BV Chợ Rẫy", "BV Nhân Dân 115",
        "VNPT Health", "eHospital", "Medpro", "BookingCare",
        "Phòng khám đa khoa Âu Cơ",
    ],

    # Cat 7 – Dịch vụ công thật
    "Dịch vụ công thật": [
        "BHXH Việt Nam", "Tổng cục Thuế", "Bộ Công an",
        "Cục An ninh mạng", "Cục CSGT", "VNeID",
        "Điện lực (EVN)", "Cấp nước", "MTTQ Việt Nam",
        "Trường Đại học CNTT", "Đại học Quốc gia TP.HCM",
    ],

    # Cat 8 – Tin nhắn cá nhân & OTP
    "Tin nhắn cá nhân và OTP": [
        "Google", "Facebook", "GitHub", "Microsoft", "Apple",
        "Zalo", "Steam", "Netflix", "TikTok", "Instagram",
        "Grab", "Shopee", "VNeID", "Agribank E-Mobile",
        "bạn bè", "gia đình", "đồng nghiệp", "người thân",
    ],
}

# [CONTEXT] Ngữ cảnh tình huống cụ thể per-category.
# Inject vào prompt mỗi batch → tăng variation chiều thứ 4 mà không thay đổi architecture.
# Mỗi lần gọi pick_context() sẽ chọn 1 context ngẫu nhiên từ list của category.
CONTEXT_VARIANTS: dict[str, list[str]] = {
    "Ngân hàng thật": [
        "giao dịch thông thường ngày thường",
        "giao dịch cuối tháng / ngày thanh toán lương",
        "giao dịch đêm khuya hoặc cuối tuần",
        "giao dịch số tiền lớn trên 10 triệu đồng",
        "giao dịch số tiền nhỏ dưới 500 nghìn",
        "OTP đăng nhập lần đầu trên thiết bị mới",
        "nhắc nhở thẻ tín dụng sắp đến kỳ thanh toán",
        "thông báo điểm thưởng hoặc ưu đãi sắp hết hạn",
    ],
    "Viễn thông": [
        "đăng ký gói mới lần đầu",
        "gia hạn gói data hàng tháng",
        "cảnh báo đã dùng hết lưu lượng ngay giữa tháng",
        "khuyến mãi cuối tuần hoặc ngày lễ",
        "thông báo gói hết hạn sau 1–2 ngày",
        "tặng data khi nạp thẻ",
        "thông báo điểm tích lũy thành viên",
    ],
    "Thương mại điện tử": [
        "đặt hàng thành công ngày thường",
        "đặt hàng trong flash sale hoặc ngày đôi (11/11)",
        "giao hàng thành công, yêu cầu đánh giá",
        "đơn hàng bị hủy hoặc yêu cầu hoàn trả",
        "OTP xác minh tài khoản mới",
        "OTP xác nhận đổi mật khẩu",
        "nhắc nhở giỏ hàng chưa thanh toán",
    ],
    "Vận chuyển": [
        "giao hàng lần đầu thành công",
        "giao thất bại lần 1, còn cơ hội giao lại",
        "giao thất bại lần 3, chuẩn bị hoàn về người gửi",
        "hàng đang phân loại tại kho Hub lớn HCM hoặc HN",
        "hàng đã đến bưu cục địa phương, chuẩn bị giao",
        "hàng cồng kềnh hoặc nặng, cần hẹn giờ giao",
        "shipper sắp đến lấy hàng tại địa chỉ người gửi",
    ],
    "Quảng cáo hợp lệ": [
        "khuyến mãi ngày thường để kích cầu",
        "sale ngày lễ lớn (Tết, 30/4, Quốc khánh)",
        "ưu đãi sinh nhật thành viên",
        "cashback khi thanh toán qua ví điện tử",
        "combo deal cuối tuần tại cửa hàng F&B",
        "điểm tích lũy sắp hết hạn, nhắc đổi quà",
        "chương trình giới thiệu bạn bè nhận thưởng",
    ],
    "Dịch vụ y tế": [
        "nhắc lịch khám định kỳ đã đặt trước",
        "nhắc lịch tái khám sau điều trị",
        "thông báo kết quả xét nghiệm đã có",
        "OTP xác thực trên app y tế lần đầu",
        "nhắc lịch tiêm vaccine cho trẻ",
        "nhắc nhở uống thuốc theo đơn bác sĩ",
        "thông báo lịch khám bị thay đổi hoặc hủy",
    ],
    "Dịch vụ công thật": [
        "nhắc gia hạn thẻ BHYT sắp hết hạn",
        "thông báo kỳ khai thuế thu nhập cá nhân",
        "cảnh báo an ninh mạng về lừa đảo đang lan rộng",
        "nhắc gia hạn CCCD hoặc đổi sang căn cước mới",
        "thông báo hóa đơn điện tháng này đã có",
        "thông báo học phí đầu học kỳ",
        "kêu gọi ủng hộ từ thiện hoặc thiên tai",
    ],
    "Tin nhắn cá nhân và OTP": [
        "OTP đăng nhập tài khoản thông thường",
        "OTP xác nhận giao dịch quan trọng",
        "tin nhắn hỏi thăm bạn bè sau thời gian dài",
        "nhắc hẹn gặp hoặc thay đổi kế hoạch",
        "thông báo nội bộ gia đình ngắn gọn",
        "xác nhận đặt bàn hoặc đặt phòng dịch vụ nhỏ",
        "nhắc việc từ đồng nghiệp hoặc sếp",
    ],
}


def pick_context(category: str) -> str:
    """Chọn ngẫu nhiên 1 ngữ cảnh tình huống cho batch hiện tại."""
    variants = CONTEXT_VARIANTS.get(category, ["tình huống thông thường"])
    return random.choice(variants)


# [VOCAB] Vocabulary style hints — inject ngẫu nhiên vào Layer 4 của prompt.
# Phá vỡ pattern từ vựng/cấu trúc câu mà không ảnh hưởng semantic content.
VOCAB_HINTS: list[str] = [
    "Dùng viết tắt phổ biến trong SMS thực tế: TK (tài khoản), GD (giao dịch), "
    "KM (khuyến mãi), HSD (hạn sử dụng), DK (đăng ký), HD (hóa đơn), LH (liên hệ).",

    "Viết đầy đủ không viết tắt, như thông báo chính thức từ tổ chức lớn. "
    "Dùng 'Quý khách' thay vì 'bạn' hoặc 'ban'.",

    "Có thể bỏ dấu tiếng Việt hoàn toàn (không dấu) như nhiều hệ thống SMS thực tế gửi. "
    "KHÔNG dùng leet hay ký tự thay thế sai lệch.",

    "Dùng dấu tiếng Việt đầy đủ, câu hoàn chỉnh rõ ràng như SMS cao cấp của ngân hàng lớn.",

    "Câu cực ngắn gọn — mỗi thông tin một cụm, tối đa 1–2 câu, không câu dư thừa.",

    "Câu đầy đủ subject + verb + object, văn phong lịch sự nhưng tự nhiên, "
    "không quá formal kiểu hành chính.",

    "Mix ngắn và dài trong batch: một số dòng cực ngắn (<80 ký tự), "
    "một số dài hơn (~200 ký tự) với thông tin chi tiết hơn.",
]


def pick_vocab_hint() -> str:
    """Chọn ngẫu nhiên 1 vocabulary style hint cho batch hiện tại."""
    return random.choice(VOCAB_HINTS)


# Mỗi level có description + concrete examples
FORMAL_LEVEL_STYLES: dict[int, str] = {
    0: (
        "Template cứng – Format hoàn toàn cố định theo brand, như tin nhắn ngân hàng/viễn thông lớn. "
        "Không có biến thể câu, chỉ thay đổi số liệu (mã OTP, số tiền, ngày). "
        "KHÔNG bỏ dấu tiếng Việt, KHÔNG có lỗi chính tả. "
        'Ví dụ: "[MB] Ma OTP: 847392. Su dung trong 5 phut. KHONG chia se ma nay voi bat ky ai."'
    ),
    1: (
        "Template mềm – Có template cơ bản nhưng có thể có câu biến đổi nhỏ, thêm thông tin bối cảnh. "
        "Ngôn ngữ formal, lịch sự, câu hoàn chỉnh. "
        "Thường gặp ở TMĐT, logistics, viễn thông. "
        'Ví dụ: "Shopee: Don hang #240327MNKLPY cua ban da duoc xac nhan. Du kien giao 28-30/3."'
    ),
    2: (
        "Bán formal – Ngôn ngữ lịch sự nhưng ít cứng nhắc, có thể là doanh nghiệp vừa và nhỏ. "
        "Có thể có câu giới thiệu, lời chào. Có thể bỏ dấu tiếng Việt nhưng KHÔNG dùng leetcode. "
        'Ví dụ: "KFC Q.1 thong bao: Tu 26-28/3, mua combo bat ky giam 30%. Xem menu: kfc.com.vn/menu"'
    ),
    3: (
        "Thân thiện – Giống người quen nhắn, dịch vụ tư nhân nhỏ hoặc lễ tân. "
        "Có thể dùng 'bạn', 'nhe', 'nha', ngôn ngữ gần gũi. Có thể có lỗi nhỏ. "
        'Ví dụ: "Phong kham Dr. Lan nhac ban: Lich kham ngay mai 27/3 luc 9h. Co gi thay doi LH 0901234567 nhe."'
    ),
    4: (
        "Cá nhân hoàn toàn – Tin nhắn giữa hai người, không có template, ngắn gọn tự nhiên. "
        "Có thể bỏ dấu, dùng từ viết tắt thông thường (ok, nha, dc, ko, thui). "
        "Không có brand, không có thông tin thương mại. "
        'Ví dụ: "Chieu nay hop 3h nhe. Nho mang tai lieu du an"'
    ),
}

# Range formality level mong muốn cho từng category
CATEGORY_FORMAL_RANGE: dict[str, tuple[int, int]] = {
    "Ngân hàng thật":             (0, 1),
    "Viễn thông":                 (0, 1),
    "Thương mại điện tử":         (1, 1),
    "Vận chuyển":                 (0, 1),
    "Quảng cáo hợp lệ":          (1, 2),
    "Dịch vụ y tế":               (2, 3),
    "Dịch vụ công thật":          (0, 1),
    "Tin nhắn cá nhân và OTP":    (0, 4),
}


def pick_formality_style(category: str) -> tuple[tuple[int, int], str]:
    lo, hi = CATEGORY_FORMAL_RANGE.get(category, (0, 4))
    parts = []
    for lvl in range(lo, hi + 1):
        parts.append(f"- MỨC {lvl}: {FORMAL_LEVEL_STYLES[lvl]}")
    return (lo, hi), "\n".join(parts)


VALID_SENDER_TYPES = {"personal_number", "brandname", "shortcode"}

# [QUOTA] Phân phối mẫu mục tiêu per-category.
# Không dùng 375 đều nhau — phân bổ theo độ phức tạp boundary và tầm quan trọng.
# Tổng = 3000.
CATEGORY_QUOTA: dict[str, int] = {
    "Ngân hàng thật":             450,   # Ranh giới quan trọng nhất với smishing banking
    "Viễn thông":                 300,   # Template tương đối cứng, ít variation
    "Thương mại điện tử":         400,   # Nhiều sàn, nhiều trạng thái đơn
    "Vận chuyển":                 400,   # Nhiều ĐVVC, nhiều trạng thái giao
    "Quảng cáo hợp lệ":          350,   # Boundary tinh tế với smishing ads
    "Dịch vụ y tế":               300,   # Formal range rộng, cần diversity
    "Dịch vụ công thật":          300,   # Ranh giới với Label 1 Cat 6 (gov scam)
    "Tin nhắn cá nhân và OTP":    500,   # Ambiguous nhất, cần nhiều examples nhất
}

assert sum(CATEGORY_QUOTA.values()) == TOTAL_SAMPLES, (
    f"CATEGORY_QUOTA tổng = {sum(CATEGORY_QUOTA.values())}, phải = {TOTAL_SAMPLES}"
)


# =============================================================================
# 3. PROMPT ENGINEERING – 8 Category-Specific Templates
#    Thêm {context} và {vocab_hint} vào mỗi template.
# =============================================================================

def _prompt_banking(brands: str, style: str, size: int,
                    context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn ngân hàng hợp lệ (label=0).
Ngân hàng: {brands}
Loại thông báo: Mix đa dạng OTP / Giao dịch / Thông tin tài khoản
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một ngân hàng từ danh sách trên cho mỗi dòng.
  - Prefix đúng brand: "[MB]", "[VCB]", "[BIDV]", "Techcombank:", "ACB:", "VPBank:", ...
  - Số tài khoản PHẢI masked: dạng 123456****7890 hoặc ****7890 (KHÔNG để số thật)
  - Mã OTP: 6 chữ số ngẫu nhiên thực tế (KHÔNG dùng "XXXXXX", "123456", "000000")
  - Số tiền: có dấu phân cách nghìn (2,345,678VND không phải 2345678VND)
  - KHÔNG có urgency đe dọa ("bị khóa vĩnh viễn", "mất toàn bộ tài sản") – chỉ thông tin
  - has_url = 0 với OTP và giao dịch; có thể = 1 với nhắc nhở (link .vn thật)
  - Sender: brandname (~70%), shortcode (~30%) – KHÔNG dùng personal_number

SUB-TYPE (phân bổ đều trong batch):
  A – OTP (~30%): "[BRAND] Ma OTP: XXXXXX. Su dung trong [3/5/10] phut. KHONG chia se."
  B – Giao dịch (~40%): "[BRAND] TK ****XXXX +/-[amount]VND luc [HH:MM]. So du: [balance]VND."
  C – Nhắc nhở (~30%): Nhắc thanh toán thẻ tín dụng, điểm thưởng sắp hết hạn, thay đổi lãi suất

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Ma OTP la 22085377. de xac nhan giao dich (TRU TIEN) tu The cua quy khach. Vui long giu bao mat va khong chia se OTP cho bat cu ai. LH Techcombank: 1800588822|0|0|1|brandname
Ma OTP xac thuc GD la 972501, hieu luc 1 phut. Chi tiet GD:Chuyen khoan nhanh qua so TK,so tien 22,700,000 VND tren kenh Internet cua dich vu VCB Digibank.|0|0|0|brandname
Vietcombank KHONG yeu cau cung cap TEN DANG NHAP, MAT KHAU, OTP qua cac duong link gui qua SMS. Quy khach hay canh giac va TUYET DOI KHONG cung cap thong tin.|0|0|0|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (OTP và giao dịch), 0 hoặc 1 (nhắc nhở – link .vn thật nếu có)
  - has_phone = 1 nếu có hotline 1800xxxx trong nội dung, 0 nếu không
  - sender_type: brandname (~70%), shortcode (~30%)
  - 40–200 ký tự
  - Mã OTP và số tài khoản KHÁC NHAU mỗi dòng trong cùng batch
  - KHÔNG dùng domain giả (.vip, .top, .xyz) – chỉ domain .vn, .com.vn thật nếu có link
  - KHÔNG có placeholder literal như "[BRAND]", "[OTP]", "XXXXXX"

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_telecom(brands: str, style: str, size: int,
                    context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn viễn thông hợp lệ (label=0).
Nhà mạng: {brands}
Loại thông báo: Mix đa dạng Gói cước / Cảnh báo / Khuyến mãi
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một nhà mạng từ danh sách trên cho mỗi dòng.
  - Prefix phổ biến: "[TB]" (thông báo), "[QC]" (quảng cáo), tên brand đầu câu
  - Tên gói thực tế: D60, MiMax99, V90B, ST7K, 5G30, WIN60, Big0, FB5K, ...
  - USSD code: Soạn [GÓI] gửi 191 (Viettel), *098# (Viettel), *101# (Vinaphone)
  - Mốc thời gian cụ thể: ngày bắt đầu, ngày hết hạn
  - CTA từ chối QC: "Tu choi QC, soan TC3 gui 199" (nếu là quảng cáo)
  - Hotline: 198 (Viettel, 0đ), 18001260 (Vinaphone), 9090 (MobiFone)

SUB-TYPE (phân bổ đều):
  A – Đăng ký gói cước thành công (~35%): thông báo sau khi khách hàng đăng ký gói data/thoại
  B – Cảnh báo hết data/số dư (~25%): thông báo đã dùng hết lưu lượng hoặc sắp hết hạn
  C – Khuyến mãi (~40%): ưu đãi tặng data, giảm giá gói, tích điểm, nạp thẻ

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
[TB] NẠP THẺ ĐỦ ĐẦY - DATA XÀI NGAY! Tặng 20% giá trị tất cả thẻ nạp vào tài khoản viễn thông trong ngày 25/11/2025. Tiền KM sử dụng truy cập Internet trong 15 ngày. Nạp thẻ online tại https://viettel.vn/naptienkm . Chi tiết gọi 197 bấm phím 19 (0đ). Trân trọng.|0|1|0|brandname
Quy khach da dung het luu luong data cua CT Viettel++ va tiep tuc truy cap theo goi Mobile Internet dang su dung (neu co). Chi tiet LH 198 (0d). Tran trong.|0|0|0|shortcode
iTel TB: Den het thang 01/2023, Quy khach dang la hoi vien Than Thiet, so diem iTel Club la 200. Diem iTel Club co gia tri su dung trong vong 12 thang. Truy cap app MyiTel tai http://onelink.to/myitel de nhan uu dai.|0|1|1|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link (viettel.vn, vinaphone.vn, mobifone.vn thật)
  - has_phone = 1 nếu có hotline trong nội dung (198, 18001260, 9090...)
  - sender_type: brandname (~80%), shortcode (~20%)
  - 50–300 ký tự (khuyến mãi thường dài hơn)
  - KHÔNG dùng domain giả – chỉ domain nhà mạng thật

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_ecommerce(brands: str, style: str, size: int,
                      context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn thương mại điện tử hợp lệ (label=0).
Sàn TMĐT: {brands}
Loại thông báo: Mix đa dạng OTP xác thực / Đơn hàng / Trạng thái giao hàng
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một sàn từ danh sách trên cho mỗi dòng.
  - Format mã đơn hàng ĐÚNG từng sàn:
      * Shopee: #YYMMDDXXXXXXX (ví dụ: #240327MNKLPY)
      * Tiki: TKI-XXXXXXXXXX (dạng số)
      * Lazada: số đơn dài (ví dụ: 123456789012)
  - Mã OTP: 6 chữ số ngẫu nhiên (KHÔNG phải "XXXXXX")
  - Trạng thái đơn hàng cụ thể: "da dat thanh cong", "dang chuan bi", "da giao thanh cong"
  - Mã OTP KHÁC NHAU mỗi dòng, mã đơn hàng KHÁC NHAU mỗi dòng

SUB-TYPE (phân bổ đều):
  A – OTP/xác minh tài khoản (~40%): "KHONG chia se ma nay voi nguoi khac, ke ca nhan vien [sàn]"
  B – Xác nhận đơn hàng (~30%): thông báo sau khi đặt hàng thành công
  C – Giao hàng / hoàn trả (~30%): trạng thái vận chuyển, kết quả giao, yêu cầu đánh giá

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên mã, dùng làm tham chiếu):
SHOPEE: DE CAP NHAT MAT KHAU, ma xac minh la 131929. Co hieu luc trong 15 phut. KHONG chia se ma nay voi nguoi khac, ke ca nhan vien Shopee.|0|0|0|personal_number
Tiki: Ma xac minh dang ky tai khoan cua ban la 811962. Ma co hieu luc trong vong 15 phut. Khong chia se ma nay voi nguoi khac.|0|0|0|brandname
Shopee: Don hang #240327ABCXYZ cua ban da dat thanh cong. Du kien giao 28/03-30/03. Theo doi don tai app Shopee.|0|0|0|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (OTP và xác nhận), 1 nếu có link đánh giá/theo dõi sàn thật
  - has_phone = 0 (hầu hết TMĐT không có hotline trong SMS)
  - sender_type: brandname (~75%), personal_number (~25% – với Shopee OTP)
  - 40–180 ký tự
  - Mã OTP và mã đơn hàng KHÁC NHAU mỗi dòng

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_logistics(brands: str, style: str, size: int,
                      context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn vận chuyển & logistics hợp lệ (label=0).
Đơn vị vận chuyển: {brands}
Loại thông báo: Mix đa dạng trạng thái vận đơn
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một ĐVVC từ danh sách trên cho mỗi dòng.
  - Format tracking ID ĐÚNG từng ĐVVC:
      * GHN:           Bắt đầu bằng GHNR hoặc SHNR + 7-8 ký tự chữ hoa/số (ví dụ: GHNR24032700001)
      * GHTK:          GHTK + 10 chữ số (ví dụ: GHTK1234567890)
      * Viettel Post:  VTP + 9-11 ký tự (ví dụ: VTP278134512)
      * Ninja Van:     NVVN + 8-9 ký tự (ví dụ: NVVN12345678)
      * J&T Express:   JT + 10-12 ký tự số (ví dụ: JT123456789012)
  - Tên kho: "kho Ha Noi", "kho TP.HCM", "kho Da Nang", "kho Binh Duong"
  - Khung giờ giao: "tu 8h-18h", "tu 8h-12h", "tu 13h-18h"
  - Số điện thoại giao viên (chỉ khi giao thất bại – 10 chữ số, format 0xxxxxxxxx)

SUB-TYPE (phân bổ đều):
  A – Đang phân loại tại kho (~30%): "Dang phan loai tai kho [city]. Du kien giao [date] (tu [giờ])."
  B – Giao thành công (~30%): "Da giao thanh cong luc [HH:MM]. Cam on da su dung dich vu."
  C – Giao thất bại / lấy lại (~25%): "Giao khong thanh cong lan [N]. Lien he giao vien: [SĐT]."
  D – Lấy hàng / hẹn giao lại (~15%): "Se den lay hang luc [time]. Vui long chuan bi kien hang."

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
[GHN] Van don GHNR24032700001: Dang phan loai tai kho TP.HCM. Du kien giao 28/03 (tu 8h-18h). Theo doi tai https://ghn.vn|0|1|0|brandname
GHTK-GHTK1234567890: Kien hang da giao thanh cong luc 14:35 ngay 27/03. Cam on ban da su dung dich vu GHTK!|0|0|0|brandname
[VTP] Ma van don: VTP278134512. Giao khong thanh cong lan 1. Lien he giao vien 0912345678 de dat lai lich giao.|0|0|1|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link theo dõi (ghn.vn, ghtk.vn, viettelpost.vn thật), 0 nếu không
  - has_phone = 1 nếu có SĐT giao viên (chỉ khi giao thất bại), 0 nếu không
  - sender_type: brandname (~80%), shortcode (~20%)
  - 60–200 ký tự
  - Tracking ID KHÁC NHAU mỗi dòng trong batch

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_legit_ads(brands: str, style: str, size: int,
                      context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn quảng cáo hợp lệ (label=0) từ thương hiệu thật.
Thương hiệu: {brands}
Mục tiêu: Quảng cáo có thật, có ưu đãi rõ ràng, KHÔNG phải scam
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một thương hiệu từ danh sách trên cho mỗi dòng.
  - Ưu đãi CỤ THỂ: % giảm, số tiền, combo, mã khuyến mãi (ví dụ: KFCAPP26, MOMO10K)
  - Điều kiện áp dụng RÕ RÀNG: thời hạn, điều kiện mua tối thiểu, kênh áp dụng
  - Domain thật: momo.vn, grab.com, kfc.com.vn, winmart.com.vn, ...
  - KHÔNG có "trúng thưởng miễn phí không điều kiện" – đây là dấu hiệu scam
  - CTA từ chối QC nếu là SMS marketing: "Soan TU CHOI gui 9999" (tùy brand)

PHÂN BIỆT hợp lệ vs scam:
  ✅ Hợp lệ: "KFC: Mua combo BigBox 129k tang 1 nuoc. Ma: KFCAPP26. Ap dung qua app den 31/3."
  ❌ Scam: "Chuc mung ban trung giai dac biet 50 trieu! Click ngay: bit.ly/xxx"

SUB-TYPE (phân bổ đều):
  A – F&B (KFC/Lotteria/Highland/The Coffee House) (~30%): combo deal, mã giảm giá app
  B – Fintech/Ví điện tử (MoMo/Grab/ZaloPay) (~35%): cashback, quà nạp tiền, tích điểm
  C – Siêu thị/Bán lẻ (WinMart/Co.opmart/Bách hóa xanh) (~20%): sale ngày lễ, mua sắm
  D – App tích điểm/thẻ thành viên (~15%): thông báo điểm sắp hết hạn, nâng hạng

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Ban co 10.000D qua Nap Dien Thoai & 140.000D qua khac trong MoMo, het han 31/10. Mo Vi > UU DAI > QUA CUA TOI dung ngay!|0|0|0|brandname
[TB] Quy khach nhan duoc voucher Giam 99.000d khi mua Bao hiem Xe may tu chuong trinh Uu dai Bao hiem het han ngay 31/07/2025. Mo app Viettel Money tai https://viettelmoney.go.link de biet them.|0|1|0|brandname
Highland Coffee: Mua 1 ca phe bat ky tang 1 banh mi trung ca phe. Ap dung thu 2-6, den 30/04/2026. Xem them: highland.coffee/uu-dai|0|1|0|shortcode

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link app/website thật, 0 nếu không
  - has_phone = 1 nếu có số hotline chăm sóc KH, 0 nếu không
  - sender_type: brandname (~55%), shortcode (~45%)
  - 60–250 ký tự
  - Ngày hết hạn ưu đãi PHẢI CỤ THỂ (ví dụ: 31/03/2026, không phải "sớm nhất")
  - KHÔNG dùng URL rút gọn ẩn danh (bit.ly, t.ly) – chỉ domain thật của brand

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_healthcare(brands: str, style: str, size: int,
                       context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn dịch vụ y tế hợp lệ (label=0).
Tổ chức y tế / Ứng dụng: {brands}
Loại thông báo: Mix đa dạng nhắc lịch khám / OTP y tế / kết quả xét nghiệm
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một tổ chức từ danh sách trên cho mỗi dòng.
  - Tên bệnh viện ĐÚNG tên thật (Bệnh viện Bạch Mai, BV Việt Đức, BV Chợ Rẫy, BV 108, ...)
  - Tên phòng/khoa THỰC TẾ: Phòng 301, Khoa Tim mạch, Khoa Nhi, Khoa Xét nghiệm
  - OTP app y tế: 6 chữ số ngẫu nhiên, trong [3/5/10] phút
  - SĐT liên hệ nếu có: số hotline BV thật (02871026789, 02438253531, ...)
  - KHÔNG có urgency đe dọa – chỉ nhắc nhở lịch hẹn thân thiện

SUB-TYPE (phân bổ đều):
  A – Nhắc lịch khám (~45%): tên BV/phòng khám, giờ, ngày, phòng/khoa
  B – OTP app y tế (~25%): VNPT Health, eHospital, Medpro, BookingCare
  C – Kết quả xét nghiệm / nhắc tái khám (~30%): thông báo kết quả sẵn sàng, lịch tái khám

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot được tạo theo chuẩn thực tế – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Moi QK NGUYEN VAN ANH kham theo lich luc 8h30 ngay 28/03/2026 tai Phong 305 - Khoa Tim mach - BV Bach Mai. Vui long den dung gio va xuat trinh the BHYT.|0|0|0|brandname
VNPT Health: Ma xac thuc cua ban la: 284931. Co hieu luc trong 5 phut. KHONG chia se ma nay voi bat ky ai.|0|0|0|brandname
Phong kham Dr. Minh nhac lich kham ngay mai 28/03 luc 9h30. Co viec can doi lich vui long LH 0901234567 nhe.|0|0|1|personal_number

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (hầu hết), 1 nếu có link xem kết quả xét nghiệm trực tuyến
  - has_phone = 1 nếu có SĐT hotline BV hoặc phòng khám, 0 nếu không
  - sender_type: brandname (~60%), personal_number (~30%), shortcode (~10%)
  - 60–250 ký tự
  - Tên bệnh nhân phải là tên Việt thật (3 tiếng, họ tên đầy đủ), KHÔNG dùng "[TÊN]"

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_govt(brands: str, style: str, size: int,
                 context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn dịch vụ công hợp lệ (label=0).
Cơ quan / Tổ chức: {brands}
Ngữ cảnh batch này: {context}

PHÂN BIỆT hợp lệ vs giả mạo (QUAN TRỌNG):
  ✅ Hợp lệ (Label 0): domain .gov.vn THẬT, KHÔNG đe dọa, KHÔNG link lạ, thông tin thuần túy
  ❌ Giả mạo (Label 1): domain .top/.vip giả, urgency mạnh, link rút gọn che đích

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một cơ quan từ danh sách trên cho mỗi dòng.
  - KHÔNG có urgency đe dọa kiểu "thông báo cuối cùng", "sẽ bị xử lý hình sự"
  - KHÔNG có link lạ (.top, .vip, .xyz) – chỉ domain chính thống (.gov.vn, .edu.vn)
  - Nội dung thuần thông tin: nhắc nhở, thông báo, cảnh báo an toàn

SUB-TYPE (phân bổ đều):
  A – BHXH/BHYT (~25%): nhắc gia hạn thẻ, thông báo đăng ký thành công, mã số hưởng
  B – Thuế (~20%): nhắc kỳ khai thuế, hướng dẫn tra cứu thuedientu.gdt.gov.vn
  C – Bộ Công an / An ninh mạng (~25%): cảnh báo lừa đảo, nhắc gia hạn CCCD
  D – Tổ chức khác (~30%): hóa đơn điện/nước, thông báo học phí, MTTQ kêu gọi đóng góp

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
PCGV tran trong thong bao ke tu thang 07/2017 se khong thu tien tai nha, moi Quy KH thanh toan tien dien qua Ngan hang hoac cac diem thu ho. LH 1900545454|0|0|1|brandname
DHCNTT TB HOC PHI DOT 1 HK1 25-26 CUA SV Nguyen Hoang Duy (22520327) LA 18,500,000d, HAN NOP HP DOT 1 LA 28/9/2025. VUI LONG BO QUA TIN NHAN NEU DA NOP TIEN.|0|0|0|brandname
[TB] MTTQ Viet Nam keu goi chung tay ung ho dong bao bi thiet hai do bao lu gay ra. Cac tai khoan tiep nhan: 55102025 tai Vietinbank; 8639699999 tai BIDV. Chi tiet: mttqvietnam.org.vn|0|1|0|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link .gov.vn hoặc .edu.vn thật, 0 nếu không
  - has_phone = 1 nếu có số hotline cơ quan (1900xxxx, 024xxxxxxx...), 0 nếu không
  - sender_type: brandname (~90%), shortcode (~10%)
  - 60–350 ký tự (thông báo cơ quan thường khá dài)
  - KHÔNG dùng domain giả – chỉ domain chính phủ/trường học thật

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


def _prompt_personal_otp(brands: str, style: str, size: int,
                         context: str, vocab_hint: str) -> str:
    return f'''\
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn cá nhân và OTP hợp lệ (label=0).
Ứng dụng / Ngữ cảnh: {brands}
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU ĐA DẠNG: Trộn đều 3 sub-type bên dưới, KHÔNG để một sub-type chiếm toàn bộ batch.
  - OTP: 6 chữ số ngẫu nhiên thực tế (KHÔNG "000000", "123456", "XXXXXX")
  - Tin nhắn cá nhân: văn phong tự nhiên, có thể bỏ dấu, từ viết tắt thông thường (nha, ko, dc, thui)
  - KHÔNG có CTA đáng ngờ, KHÔNG link lạ, KHÔNG urgency thao túng

SUB-TYPE (phân bổ đều):
  A – OTP ứng dụng phổ biến (~35%): Google, Facebook, GitHub, Microsoft, Apple, Zalo, Steam, Netflix...
      Format: "[App] Ma OTP/xac thuc/dang nhap cua ban la: XXXXXX. Co hieu luc trong [N] phut."
      has_url = 0, sender_type = brandname hoặc shortcode

  B – Tin nhắn cá nhân thông thường (~40%): hỏi thăm, hẹn gặp, nhắc việc, thông báo gia đình
      Văn phong thân mật, có thể bỏ dấu hoặc dùng teencode nhẹ (ok, nha, dc, ko, thui)
      has_url = 0, has_phone = 0, sender_type = personal_number

  C – Xác nhận dịch vụ nhỏ (~25%): đặt bàn nhà hàng, đặt phòng, đặt vé, nhận hàng cá nhân
      Mã xác nhận, thời gian, địa điểm cụ thể
      has_url = 0 hoặc 1, sender_type = personal_number hoặc shortcode

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Mã xác thực GitHub của bạn là: 733792|0|0|0|brandname
Use verification code 541118 for Microsoft authentication.|0|0|0|brandname
Hương đang làm gì vậy? Dạo này công việc thế nào rồi?|0|0|0|personal_number
Em Hà day. Goi lai vao so 0978123456 em co viec gap.|0|0|1|personal_number

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (hầu hết), 1 nếu có link dịch vụ thật (không rút gọn ẩn đích)
  - has_phone = 1 nếu có SĐT trong nội dung (chỉ Sub-type B/C), 0 nếu không
  - sender_type: brandname (~50%), personal_number (~45%), shortcode (~5%)
  - 5–150 ký tự (tin cá nhân rất ngắn; OTP ngắn gọn)
  - OTP KHÁC NHAU mỗi dòng
  - Sub-type B: tên người Việt tự nhiên, KHÔNG "[TÊN KHÁCH HÀNG]"

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.\
'''


# Dispatch table
_PROMPT_DISPATCH = {
    "Ngân hàng thật":             _prompt_banking,
    "Viễn thông":                 _prompt_telecom,
    "Thương mại điện tử":         _prompt_ecommerce,
    "Vận chuyển":                 _prompt_logistics,
    "Quảng cáo hợp lệ":          _prompt_legit_ads,
    "Dịch vụ y tế":               _prompt_healthcare,
    "Dịch vụ công thật":          _prompt_govt,
    "Tin nhắn cá nhân và OTP":    _prompt_personal_otp,
}


def build_prompt(category: str, brands: str, style: str, size: int,
                 context: str, vocab_hint: str) -> str:
    fn = _PROMPT_DISPATCH.get(category)
    if fn is None:
        raise ValueError(f"Category không xác định: {category!r}")
    return fn(brands=brands, style=style, size=size,
              context=context, vocab_hint=vocab_hint)


# =============================================================================
# 4. VALIDATION – Label 0 specific checks
# =============================================================================
_PAT_FAKE_TLD    = _re.compile(r'\.(vip|top|xyz|cc|icu|cfd|life|biz|bet)\b', _re.I)
_PAT_PLACEHOLDER = _re.compile(r'\[OTP\]|\[BRAND\]|\[XXXXXX\]|\[ORDER_ID\]|\[TÊN\]|\[SỐ TIỀN\]', _re.I)
# [VALID] F7: URL pattern để check consistency với has_url flag
_PAT_URL         = _re.compile(r'https?://|www\.|\.(vn|com\.vn|gov\.vn|edu\.vn)\b', _re.I)


def validate_row_label0(row: list[str]) -> bool:
    """
    Validate một row Label 0. Trả về True nếu hợp lệ.
    F1–F6: checks gốc.
    F7: URL consistency (has_url=0 nhưng content có URL → reject).
    F8: No fake TLD.
    F9: No placeholder literal.
    """
    if len(row) < 5:
        return False
    label, has_url, has_phone, sender = row[1], row[2], row[3], row[4]

    if label.strip().strip("'\"") != "0":
        return False
    if sender.strip().strip("'\"") not in VALID_SENDER_TYPES:
        return False
    if has_url.strip().strip("'\"") not in ("0", "1"):
        return False
    if has_phone.strip().strip("'\"") not in ("0", "1"):
        return False

    content = row[0].strip()
    if not content or len(content) < 5:
        return False
    if _PAT_FAKE_TLD.search(content):
        return False
    if _PAT_PLACEHOLDER.search(content):
        return False

    # [VALID] F7: nếu has_url=0 nhưng content chứa URL pattern → metadata sai, reject
    if has_url.strip().strip("'\"") == "0" and _PAT_URL.search(content):
        return False

    return True


# =============================================================================
# 5. GỌI API & XỬ LÝ RESPONSE
# =============================================================================
def call_api_with_retry(prompt: str, category: str) -> str:
    config = _make_config(category)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )
            return response.text.strip()
        except Exception as exc:
            wait_secs = 20 * attempt
            print(f"  ⚠️  Lỗi API (lần {attempt}/{MAX_RETRIES}): {exc}. Nghỉ {wait_secs}s...")
            time.sleep(wait_secs)

    print("  ❌ Hết retry. Bỏ qua batch này.")
    return ""


def extract_valid_rows(raw_text: str) -> list[list[str]]:
    """
    Parse pipe-delimited output từ LLM → trả về list các row đã validated.
    Dùng | làm delimiter: luôn lấy LAST 4 parts làm metadata (robust với content chứa |).
    """
    cleaned = raw_text.replace("```csv", "").replace("```", "").strip()
    valid: list[list[str]] = []

    for line in cleaned.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("content"):
            continue

        parts = line.split("|")
        if len(parts) < 5:
            continue

        label_val = parts[-4].strip().strip("'\"")
        has_url   = parts[-3].strip().strip("'\"")
        has_phone = parts[-2].strip().strip("'\"")
        sender    = parts[-1].strip().strip("'\"")
        content   = "|".join(parts[:-4]).strip()

        row = [content, label_val, has_url, has_phone, sender]
        if validate_row_label0(row):
            valid.append(row)

    return valid


# =============================================================================
# 6. CHECKPOINT – LOAD NỘI DUNG HIỆN CÓ
# =============================================================================
def load_seen_contents(filepath: str) -> set[str]:
    if not os.path.exists(filepath):
        return set()
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        return set(df["content"].dropna().astype(str))
    except Exception:
        return set()


def load_category_counts(filepath: str) -> dict[str, int]:
    """
    Đọc file CSV hiện có và đếm số mẫu theo category (nếu có cột category).
    Nếu không có cột category, trả về dict rỗng → main() sẽ dùng quota đều.
    """
    if not os.path.exists(filepath):
        return {}
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        if "category" in df.columns:
            return df["category"].value_counts().to_dict()
    except Exception:
        pass
    return {}


# =============================================================================
# 7. [QUOTA] CATEGORY QUEUE – đảm bảo phân phối đúng quota
# =============================================================================
def build_category_queue(current_counts: dict[str, int]) -> list[str]:
    """
    Tạo danh sách category cần sinh theo quota còn thiếu.
    Trả về list đã shuffle để sampling không bị sequential.

    Logic:
      remaining[cat] = CATEGORY_QUOTA[cat] - current_counts.get(cat, 0)
      Mỗi category được thêm vào queue proportional với remaining quota của nó,
      tính theo số batch cần thiết (ceil(remaining / BATCH_SIZE)).
    """
    queue: list[str] = []
    for cat, quota in CATEGORY_QUOTA.items():
        current = current_counts.get(cat, 0)
        remaining = max(0, quota - current)
        # Số batch cần thiết cho category này
        batches_needed = (remaining + BATCH_SIZE - 1) // BATCH_SIZE
        queue.extend([cat] * batches_needed)

    random.shuffle(queue)
    return queue


# =============================================================================
# 8. TIẾN TRÌNH THỰC THI
# =============================================================================
def main() -> None:
    if not API_KEY:
        raise ValueError("API_KEY chưa được thiết lập. Dùng biến môi trường GEMINI_API_KEY.")

    # Khởi tạo file nếu chưa có
    if not os.path.exists(OUTPUT_FILE):
        output_dir = os.path.dirname(OUTPUT_FILE)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            # Thêm cột category để track phân phối và resume đúng quota
            writer.writerow(["content", "label", "has_url", "has_phone_number",
                             "sender_type", "category"])

    seen_contents: set[str] = load_seen_contents(OUTPUT_FILE)
    current_total: int = len(seen_contents)

    if current_total >= TOTAL_SAMPLES:
        print(f"✅ File đã đủ {current_total} mẫu unique. Không cần sinh thêm.")
        return

    # Load category counts để resume đúng quota sau khi interrupt
    category_counts: dict[str, int] = load_category_counts(OUTPUT_FILE)

    print(f"🚀 Bắt đầu sinh Label 0 (SMS hợp lệ). Hiện có: {current_total}/{TOTAL_SAMPLES}")
    print("📊 Quota mục tiêu:")
    for cat, quota in CATEGORY_QUOTA.items():
        current = category_counts.get(cat, 0)
        print(f"   {cat}: {current}/{quota}")

    # [QUOTA] Xây dựng queue từ quota còn thiếu
    category_queue = build_category_queue(category_counts)

    queue_idx = 0
    while current_total < TOTAL_SAMPLES:
        # Lấy category từ queue; nếu hết queue thì rebuild (trường hợp nhiều batch thất bại)
        if queue_idx >= len(category_queue):
            category_counts = load_category_counts(OUTPUT_FILE)
            category_queue = build_category_queue(category_counts)
            queue_idx = 0
            if not category_queue:
                print("✅ Tất cả categories đã đạt quota.")
                break

        category = category_queue[queue_idx]
        queue_idx += 1

        # Skip nếu category này đã đạt quota
        if category_counts.get(category, 0) >= CATEGORY_QUOTA[category]:
            continue

        remaining_for_cat = CATEGORY_QUOTA[category] - category_counts.get(category, 0)
        batch_size = min(BATCH_SIZE, remaining_for_cat, TOTAL_SAMPLES - current_total)

        brands_list            = SCENARIOS_LABEL0[category]
        brands_str             = ", ".join(brands_list)
        (lo, hi), style_prompt = pick_formality_style(category)

        # [CONTEXT] & [VOCAB] — inject axes variation thứ 4 và 5
        context    = pick_context(category)
        vocab_hint = pick_vocab_hint()

        print(f"🔄 [{current_total}/{TOTAL_SAMPLES}] {category} "
              f"[{category_counts.get(category,0)}/{CATEGORY_QUOTA[category]}] "
              f"| Ngữ cảnh: {context[:40]}...")

        prompt   = build_prompt(category, brands_str, style_prompt, batch_size,
                                context, vocab_hint)
        raw_text = call_api_with_retry(prompt, category)

        if not raw_text:
            continue

        valid_rows = extract_valid_rows(raw_text)
        if not valid_rows:
            print("  ⚠️  Không có dòng pipe-delimited hợp lệ trong response. Bỏ qua batch.")
            continue

        new_rows   = [row for row in valid_rows if row[0].strip() not in seen_contents]
        duplicates = len(valid_rows) - len(new_rows)

        if not new_rows:
            print(f"  ⚠️  Toàn bộ {len(valid_rows)} dòng đã tồn tại. Bỏ qua batch.")
            time.sleep(SLEEP_BETWEEN_BATCHES)
            continue

        # Append cột category vào mỗi row
        rows_with_cat = [row + [category] for row in new_rows]

        with open(OUTPUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(rows_with_cat)

        for row in new_rows:
            seen_contents.add(row[0].strip())

        added = len(new_rows)
        current_total += added
        category_counts[category] = category_counts.get(category, 0) + added

        dup_msg = f" ({duplicates} trùng, đã bỏ)" if duplicates else ""
        print(f"  ✅ +{added} dòng{dup_msg}. "
              f"{category}: {category_counts[category]}/{CATEGORY_QUOTA[category]}. "
              f"Tổng: {current_total}/{TOTAL_SAMPLES}")

        if current_total < TOTAL_SAMPLES:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # Hậu xử lý – giữ cột category trong file cuối
    print("🧹 Chuẩn hóa file cuối cùng...")
    df = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
    before = len(df)
    df.dropna(subset=["content"], inplace=True)
    df.drop_duplicates(subset=["content"], inplace=True)
    df["sender_type"] = df["sender_type"].str.strip().str.strip("'\"")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"🎊 Hoàn thành! {before} → {len(df)} mẫu sau lọc. File: {OUTPUT_FILE}")
    print("\n📊 Phân phối cuối cùng:")
    if "category" in df.columns:
        for cat, count in df["category"].value_counts().items():
            quota = CATEGORY_QUOTA.get(cat, "?")
            print(f"   {cat}: {count}/{quota}")


if __name__ == "__main__":
    main()