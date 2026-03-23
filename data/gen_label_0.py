"""
Sinh dữ liệu SMS sạch tổng hợp (Label = 0) dùng Gemini API.

Chiến lược 3 cấp độ:
  Level 1 (30%) – Đời thường & Công việc  : Hỏi thăm, hẹn gặp, nhắc lịch gia đình/công ty
  Level 2 (40%) – Teencode đời thường     : Phỏng theo phong cách chat thực tế người Việt
  Level 3 (30%) – Hard Negative           : Có từ khóa nhạy cảm nhưng là giao dịch/thông báo thật

Chạy độc lập:
    python gen_label_0.py

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

OUTPUT_FILE           = "synthetic_clean_label0.csv"
TOTAL_SAMPLES         = 2000
BATCH_SIZE            = 40
SLEEP_BETWEEN_BATCHES = 12    # giây – điều chỉnh theo rate-limit tài khoản
MAX_RETRIES           = 3

# Phân phối 3 cấp độ (tổng = 100)
LEVEL_WEIGHTS = [30, 40, 30]

VALID_SENDER_TYPES = {"personal_number", "brandname", "shortcode"}

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# =============================================================================
# 2. PROMPT ENGINEERING – 3 CẤP ĐỘ
# =============================================================================
def build_prompt(level: int, size: int) -> str:
    """
    Xây dựng prompt sinh SMS sạch (Label 0) theo 3 cấp độ.

    ┌─────────────────────────────────────────────────────────────┐
    │  TODO – PROMPT ENGINEERING ZONE (thảo luận chi tiết sau)   │
    │                                                             │
    │  Level 1: Few-shot phong phú hơn (đa dạng chủ đề)         │
    │  Level 2: Mở rộng & kiểm chứng danh sách teencode         │
    │  Level 3: Ràng buộc chặt tránh sinh hard negative          │
    │           ambiguous (dễ bị nhãn sai khi annotation)        │
    │           – has_url logic rõ ràng: = 1 khi CÓ URL bất kể  │
    │             chính thống hay không; OTP ≠ SĐT               │
    └─────────────────────────────────────────────────────────────┘
    """
    if level == 1:
        return _build_prompt_level1(size)
    if level == 2:
        return _build_prompt_level2(size)
    if level == 3:
        return _build_prompt_level3(size)
    raise ValueError(f"Level không hợp lệ: {level}. Chỉ chấp nhận 1, 2, 3.")


def _build_prompt_level1(size: int) -> str:
    """
    Level 1 – Đời thường & Công việc.
    Tin nhắn cá nhân hoàn toàn vô hại: hỏi thăm, hẹn gặp,
    nhắc lịch, thông báo gia đình.
    """
    # ------------------------------------------------------------------
    # PLACEHOLDER: Few-shot examples Level 1
    # Mục tiêu: 3–4 ví dụ bao phủ đa dạng ngữ cảnh
    #   (bạn bè / gia đình / đồng nghiệp / học sinh)
    # Lưu ý khi thiết kế: tránh đặt câu quá formal, cần gần gũi
    # ------------------------------------------------------------------
    few_shot_block = """\
[PLACEHOLDER – FEW-SHOT LEVEL 1]
Ví dụ 1 (bạn bè):      "Tối nay rảnh không, làm ly cafe?",0,0,0,personal_number
Ví dụ 2 (gia đình):    ...
Ví dụ 3 (công việc):   ...
Ví dụ 4 (học sinh):    ...\
"""

    return f"""\
Đóng vai người dùng di động tại Việt Nam.
Tạo đúng {size} tin nhắn SMS thuộc nhãn 0 (tin sạch, không có yếu tố lừa đảo).

CHỦ ĐỀ GỢI Ý (đa dạng, không lặp):
  - Hỏi thăm / hẹn cà phê / ăn uống với bạn bè
  - Nhắc lịch họp / gửi tài liệu nội bộ công ty
  - Thông báo sinh hoạt gia đình (đón con, mua đồ, về muộn)
  - Nhắc lịch học / thi / nộp bài của sinh viên

QUY TẮC FORMAT CSV (bắt buộc):
  - Mỗi dòng: content,0,0,0,personal_number
  - Không chứa URL, không chứa SĐT
  - Ngôn ngữ tự nhiên, gần gũi (nhé, nha, rồi ạ, oke, thôi)
  - Độ dài content: 20–120 ký tự

[PLACEHOLDER – CONSTRAINTS & NEGATIVE EXAMPLES CHI TIẾT LEVEL 1]
(Ví dụ: Không được chứa từ khóa "trúng thưởng", "xác nhận", "OTP", v.v.)

VÍ DỤ THAM KHẢO:
{few_shot_block}

QUAN TRỌNG: Chỉ xuất đúng {size} dòng CSV thuần.
Không dòng tiêu đề, không giải thích, không markdown fence.\
"""


def _build_prompt_level2(size: int) -> str:
    """
    Level 2 – Teencode đời thường.
    Phỏng theo phong cách chat thực tế: kết hợp linh hoạt
    có dấu / không dấu, viết tắt phổ biến.
    """
    # ------------------------------------------------------------------
    # PLACEHOLDER: Few-shot examples Level 2
    # Mục tiêu: ví dụ thể hiện rõ 3–4 kiểu teencode khác nhau
    # Lưu ý: tránh teencode quá "hacker style" gây nhầm smishing
    # ------------------------------------------------------------------
    few_shot_block = """\
[PLACEHOLDER – FEW-SHOT LEVEL 2]
Ví dụ 1 (viết tắt cơ bản): "ok b nha, tí qua",0,0,0,personal_number
Ví dụ 2 (không dấu):       ...
Ví dụ 3 (hỗn hợp):         ...
Ví dụ 4 (emoji + viết tắt):...\
"""

    # Danh sách teencode đời thường – cần mở rộng và kiểm chứng thực tế
    teencode_vocab = (
        "ko, dc, oke, rùi, bít, thui, j (gì), m (mày), t (tao), mk (mình), "
        "bh (bây giờ), ntn (như thế nào), vs (với), bn (bạn/bây nhiêu), "
        "trc (trước), cx (cũng), ck (chồng), vk (vợ), đc (được), ns (nói), "
        "kb (không biết), hmu (hit me up), ib (inbox)"
    )

    return f"""\
Tạo đúng {size} SMS nhãn 0 phỏng theo phong cách chat thực tế của người Việt.

PHONG CÁCH:
  - Teencode phổ biến: {teencode_vocab}
  - Kết hợp linh hoạt có dấu và không dấu trong cùng một tin
  - Tránh teencode kiểu "hacker" hoặc ký tự obfuscate (@ # ^ !)
    vì dễ bị nhầm với smishing

QUY TẮC FORMAT CSV (bắt buộc):
  - Mỗi dòng: content,0,0,0,personal_number
  - Không chứa URL, không chứa SĐT
  - Độ dài content: 10–90 ký tự (tin nhắn ngắn kiểu chat)

[PLACEHOLDER – CONSTRAINTS & NEGATIVE EXAMPLES CHI TIẾT LEVEL 2]

VÍ DỤ THAM KHẢO:
{few_shot_block}

QUAN TRỌNG: Chỉ xuất đúng {size} dòng CSV thuần.
Không dòng tiêu đề, không giải thích, không markdown fence.\
"""


def _build_prompt_level3(size: int) -> str:
    """
    Level 3 – Hard Negative.
    Tin sạch có chứa từ khóa dễ nhầm với smishing (OTP, link,
    ngân hàng, giao dịch). Dùng để phòng thủ mô hình.
    """
    # ------------------------------------------------------------------
    # PLACEHOLDER: Few-shot examples Level 3
    # Mục tiêu: ít nhất 3 ví dụ bao phủ sub-type:
    #   (a) OTP thật từ dịch vụ lớn (Google, Apple, ngân hàng)
    #   (b) Biến động số dư ngân hàng
    #   (c) Thông báo giao hàng có link domain chính thống
    # Chú ý: has_url phải = 1 nếu có bất kỳ URL nào
    # ------------------------------------------------------------------
    few_shot_block = """\
[PLACEHOLDER – FEW-SHOT LEVEL 3]
Ví dụ 1 (OTP thật):
  "[VCB] Ma OTP: 482910. Hieu luc 2 phut. Khong cung cap cho bat ky ai.",0,0,0,brandname
Ví dụ 2 (biến động số dư):
  "[ACB] TK 12345678 +2500000 VND luc 14:32. SD: 8700000 VND.",0,0,0,brandname
Ví dụ 3 (thông báo giao hàng có link chính thống):
  ...\
"""

    return f"""\
Tạo đúng {size} SMS nhãn 0 (TIN SẠCH) chứa các từ khóa dễ nhầm lẫn với smishing.
Mục tiêu: Hard Negative giúp mô hình phân biệt giao dịch thật với lừa đảo.

CÁC SUB-TYPE (phân phối đều):
  (a) OTP thật: mã OTP 6 số từ dịch vụ lớn (Google, Apple, VCB, Agribank, v.v.)
  (b) Biến động số dư ngân hàng: cú pháp chuẩn ngân hàng VN
  (c) Thông báo giao hàng Shopee/Lazada/GHTK có link chính thống

QUY TẮC FORMAT CSV (bắt buộc):
  - 5 cột: content,label,has_url,has_phone_number,sender_type
  - label            : luôn = 0
  - has_url          : 1 khi tin nhắn chứa BẤT KỲ URL nào (kể cả link chính thống); 0 nếu không
  - has_phone_number : 0 (mã OTP 6 số KHÔNG phải SĐT – đây là quy tắc cứng)
  - sender_type      : brandname hoặc shortcode (KHÔNG dùng personal_number cho loại này)
  - Nội dung phải thực tế, không mơ hồ, không thể nhầm thành smishing

[PLACEHOLDER – CONSTRAINTS & NEGATIVE EXAMPLES CHI TIẾT LEVEL 3]
(Ví dụ: Không được có cụm "nhấn vào link sau để xác nhận danh tính"
         vì ambiguous – cần thay bằng ngữ cảnh rõ ràng hơn)

VÍ DỤ THAM KHẢO:
{few_shot_block}

QUAN TRỌNG: Chỉ xuất đúng {size} dòng CSV thuần.
Không dòng tiêu đề, không giải thích, không markdown fence.\
"""


# =============================================================================
# 3. GỌI API & XỬ LÝ RESPONSE
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


def extract_valid_rows(raw_text: str) -> list[str]:
    """
    Lọc các dòng CSV hợp lệ từ response thô của model.

    Loại bỏ:
      - Markdown code fence (```csv ... ```)
      - Dòng tiêu đề lặp lại
      - Dòng giải thích bằng ngôn ngữ tự nhiên
      - Dòng có label != 0 hoặc sender_type không hợp lệ
      - Dòng có cấu trúc CSV sai (thiếu cột)

    Dùng csv.reader để xử lý đúng content chứa dấu phẩy (quoted fields).
    """
    cleaned = raw_text.replace("```csv", "").replace("```", "")
    valid: list[str] = []

    for line in cleaned.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("content,"):
            continue

        try:
            row = next(csv.reader(io.StringIO(line)))
        except csv.Error:
            continue

        if len(row) < 5:
            continue

        label_col  = row[1].strip().strip("'\"")
        sender_col = row[4].strip().strip("'\"")

        if label_col != "0":
            continue
        if sender_col not in VALID_SENDER_TYPES:
            continue

        valid.append(line)

    return valid


# =============================================================================
# 4. CHECKPOINT – ĐẾM MẪU HIỆN CÓ
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
# 5. TIẾN TRÌNH THỰC THI
# =============================================================================
def main() -> None:
    if not API_KEY:
        raise ValueError("API_KEY chưa được thiết lập. Dùng biến môi trường GEMINI_API_KEY.")

    # Khởi tạo file nếu chưa có
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            f.write("content,label,has_url,has_phone_number,sender_type\n")

    # Checkpoint: tiếp tục từ điểm dừng nếu file đã có dữ liệu
    current_total = count_existing_samples(OUTPUT_FILE)
    if current_total >= TOTAL_SAMPLES:
        print(f"✅ File đã đủ {current_total} mẫu. Không cần sinh thêm.")
        return

    print(f"🚀 Bắt đầu sinh SMS sạch. Hiện có: {current_total}/{TOTAL_SAMPLES} mẫu.")

    while current_total < TOTAL_SAMPLES:
        batch_size = min(BATCH_SIZE, TOTAL_SAMPLES - current_total)
        level      = random.choices([1, 2, 3], weights=LEVEL_WEIGHTS)[0]

        print(f"🔄 [{current_total}/{TOTAL_SAMPLES}] Level {level} – {batch_size} mẫu")

        prompt    = build_prompt(level, batch_size)
        raw_text  = call_api_with_retry(prompt)

        if not raw_text:
            continue

        valid_rows = extract_valid_rows(raw_text)

        if not valid_rows:
            print("  ⚠️  Không có dòng CSV hợp lệ trong response. Bỏ qua batch.")
            continue

        with open(OUTPUT_FILE, "a", encoding="utf-8-sig") as f:
            f.write("\n".join(valid_rows) + "\n")

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

    print(f"🎉 Hoàn thành! {before} → {len(df)} mẫu sau lọc. File: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
