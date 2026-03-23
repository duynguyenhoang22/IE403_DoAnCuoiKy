"""
Sinh dữ liệu SMS lừa đảo tổng hợp (Label = 1) dùng Gemini API.

Chạy độc lập:
    python gen_label_1.py

Biến môi trường:
    GEMINI_API_KEY – API key Gemini (hoặc nhập trực tiếp vào API_KEY bên dưới)
"""

import csv
import io
import os
import random
import time

import google.generativeai as genai
import pandas as pd

# =============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# =============================================================================
API_KEY   = os.getenv("GEMINI_API_KEY", "")   # Ưu tiên dùng biến môi trường
MODEL_NAME = "gemini-2.0-flash"               # TODO: Cập nhật tên model phù hợp

OUTPUT_FILE            = "synthetic_smishing_label1.csv"
TOTAL_SAMPLES          = 3000
BATCH_SIZE             = 40
SLEEP_BETWEEN_BATCHES  = 12   # giây – điều chỉnh theo rate-limit tài khoản
MAX_RETRIES            = 3

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

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
        "Trung tâm Thu hồi Nợ", "Phòng An ninh Điều tra",
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
    "Nội dung nhạy cảm": [
        "Telegram Hẹn hò", "Zalo Gái xinh", "Dịch vụ người lớn",
        "Hẹn hò tình một đêm", "Nhóm kín Telegram",
    ],

    # Cat 8 – Crypto / Đầu tư giả
    # Psychology: greed | sender: personal_number | Obf: Level 1–3
    "Crypto / Đầu tư giả": [
        "TikTok nhiệm vụ", "Thả tim kiếm tiền", "Đặt đơn hàng online",
        "Sàn đầu tư XYZ", "Copy trade Forex", "Nhóm Telegram đầu tư",
    ],
}

TEENCODE_STYLES: list[str] = [
    "Thay e=3, a=4, o=0, i=1 và chèn dấu chấm/gạch ngang xen kẽ (ví dụ: T.u.y.3.n, S-h-0-p-e-e)",
    "Dùng j thay gi, f thay ph, w thay qu, z thay d (ví dụ: th0ng b4o vj fhat, jao luu za.lo)",
    "Chèn ký tự đặc biệt @, #, !, *, ^ liên tục vào từ khóa nhạy cảm để lách bộ lọc",
    "Viết sai chính tả vùng miền kết hợp không dấu (ví dụ: li3n h3^ x3m hjnh_anh n0ng)",
    "Homoglyph: dùng chữ 'l' thay 'I', số '0' thay 'O' trong link giả mạo",
]

VALID_SENDER_TYPES = {"personal_number", "brandname", "shortcode"}

# =============================================================================
# 3. PROMPT ENGINEERING
# =============================================================================
def build_prompt(category: str, brand: str, style: str, size: int) -> str:
    """
    Xây dựng prompt sinh dữ liệu smishing (Label 1).

    ┌─────────────────────────────────────────────────────────────┐
    │  TODO – PROMPT ENGINEERING ZONE (thảo luận chi tiết sau)   │
    │                                                             │
    │  Các điểm cần đào sâu:                                     │
    │  • Few-shot examples (2–3 mẫu đa dạng category/style)     │
    │  • Chiến lược tâm lý cụ thể: urgency / fear / greed       │
    │  • Ràng buộc nội dung tránh trùng lặp giữa các batch      │
    │  • Cân bằng tỷ lệ has_url / has_phone_number trong batch   │
    └─────────────────────────────────────────────────────────────┘
    """

    # ------------------------------------------------------------------
    # PLACEHOLDER: Few-shot examples
    # Mục tiêu: 2–3 ví dụ bao phủ đa dạng category, sender_type, style
    # ------------------------------------------------------------------
    few_shot_block = """\
[PLACEHOLDER – FEW-SHOT EXAMPLES]
Ví dụ 1 (brandname, có URL, kiểu urgency): ...
Ví dụ 2 (shortcode, có SĐT, kiểu fear):   ...
Ví dụ 3 (personal_number, có URL, kiểu greed): ...\
"""

    # ------------------------------------------------------------------
    # PLACEHOLDER: Chiến lược tâm lý
    # Mục tiêu: mapping cụ thể category → chiến lược tâm lý ưu tiên
    # Ví dụ: "Dịch vụ công" → fear (khóa tài khoản, phạt tiền)
    #         "Tài chính"   → greed (nhận thưởng, hoàn tiền)
    # ------------------------------------------------------------------
    psychology_block = """\
[PLACEHOLDER – CHIẾN LƯỢC TÂM LÝ THEO KỊCH BẢN]
Đánh vào: cấp bách / sợ hãi / lòng tham (tùy chỉnh chi tiết theo {category})\
""".format(category=category)

    return f"""\
Bạn là chuyên gia tạo dữ liệu huấn luyện mô hình phát hiện Smishing tại Việt Nam.

NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn lừa đảo.
  - Kịch bản : {category}
  - Thương hiệu giả mạo: {brand}
  - Phong cách nhiễu/teencode: {style}

QUY TẮC FORMAT CSV (bắt buộc tuân thủ):
  - 5 cột theo thứ tự: content,label,has_url,has_phone_number,sender_type
  - label       : luôn = 1
  - has_url     : 1 nếu có BẤT KỲ URL/link nào (kể cả link rác/obfuscated), 0 nếu không
  - has_phone_number: 1 nếu có SĐT 10 số thực tế, 0 nếu không
  - sender_type : một trong personal_number | brandname | shortcode (KHÔNG dấu nháy đơn)
  - content     : wrap trong dấu nháy kép nếu nội dung chứa dấu phẩy hoặc ký tự đặc biệt
  - Độ dài content: 40–160 ký tự (giống SMS thực tế)

{psychology_block}

VÍ DỤ FORMAT THAM KHẢO:
{few_shot_block}

QUAN TRỌNG: Chỉ xuất đúng {size} dòng CSV thuần.
Không có dòng tiêu đề, không giải thích, không markdown fence.\
"""


# =============================================================================
# 4. GỌI API & XỬ LÝ RESPONSE
# =============================================================================
def call_api_with_retry(prompt: str) -> str:
    """Gọi Gemini API với cơ chế retry + exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.9},
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
    Parse pipe-delimited output từ LLM → trả về list các row đã parsed.
    Dùng | làm delimiter: LLM không cần quote, không cần escape.
    Để tránh lỗi khi content tình cờ chứa |, luôn lấy LAST 4 parts làm metadata.
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

        # Lấy 4 cột cuối làm metadata (robust kể cả khi content chứa |)
        label_val  = parts[-4].strip().strip("'\"")
        has_url    = parts[-3].strip().strip("'\"")
        has_phone  = parts[-2].strip().strip("'\"")
        sender     = parts[-1].strip().strip("'\"")
        # Tất cả phần còn lại (trước 4 cột cuối) ghép lại thành content
        content    = "|".join(parts[:-4]).strip()

        if label_val != "1":
            continue
        if sender not in VALID_SENDER_TYPES:
            continue
        if has_url not in ("0", "1") or has_phone not in ("0", "1"):
            continue
        if not content:
            continue

        valid.append([content, label_val, has_url, has_phone, sender])

    return valid


# =============================================================================
# 5. CHECKPOINT – ĐẾM MẪU HIỆN CÓ
# =============================================================================
def count_existing_samples(filepath: str) -> int:
    """Đếm số dòng dữ liệu hợp lệ trong file (không tính header)."""
    if not os.path.exists(filepath):
        return 0
    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        return len(df)
    except Exception:
        return 0


# =============================================================================
# 6. TIẾN TRÌNH THỰC THI
# =============================================================================
def main() -> None:
    if not API_KEY:
        raise ValueError("API_KEY chưa được thiết lập. Dùng biến môi trường GEMINI_API_KEY.")

    # Khởi tạo file nếu chưa có
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["content", "label", "has_url", "has_phone_number", "sender_type"])

    # Checkpoint: tiếp tục từ điểm dừng nếu file đã có dữ liệu
    current_total = count_existing_samples(OUTPUT_FILE)
    if current_total >= TOTAL_SAMPLES:
        print(f"✅ File đã đủ {current_total} mẫu. Không cần sinh thêm.")
        return

    print(f"🚀 Bắt đầu sinh smishing. Hiện có: {current_total}/{TOTAL_SAMPLES} mẫu.")

    while current_total < TOTAL_SAMPLES:
        batch_size = min(BATCH_SIZE, TOTAL_SAMPLES - current_total)

        category = random.choice(list(SCENARIOS.keys()))
        brand    = random.choice(SCENARIOS[category])
        style    = random.choice(TEENCODE_STYLES)

        print(f"🔄 [{current_total}/{TOTAL_SAMPLES}] {category} – {brand}")

        prompt    = build_prompt(category, brand, style, batch_size)
        raw_text  = call_api_with_retry(prompt)

        if not raw_text:
            # API thất bại hoàn toàn sau retry – thử lại vòng tiếp theo
            continue

        valid_rows = extract_valid_rows(raw_text)

        if not valid_rows:
            print("  ⚠️  Không có dòng CSV hợp lệ trong response. Bỏ qua batch.")
            continue

        with open(OUTPUT_FILE, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(valid_rows)

        added          = len(valid_rows)
        current_total += added
        print(f"  ✅ Thêm {added} dòng hợp lệ. Tổng: {current_total}/{TOTAL_SAMPLES}")

        if current_total < TOTAL_SAMPLES:
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # -------------------------------------------------------------------------
    # Hậu xử lý
    # -------------------------------------------------------------------------
    print("🧹 Chuẩn hóa & loại bỏ trùng lặp...")
    df = pd.read_csv(OUTPUT_FILE, encoding="utf-8-sig")
    before = len(df)
    df.dropna(subset=["content"], inplace=True)
    df.drop_duplicates(subset=["content"], inplace=True)
    # Chuẩn hóa sender_type: bỏ dấu nháy thừa nếu model vẫn sinh ra
    df["sender_type"] = df["sender_type"].str.strip().str.strip("'\"")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"🎊 Hoàn thành! {before} → {len(df)} mẫu sau lọc. File: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
