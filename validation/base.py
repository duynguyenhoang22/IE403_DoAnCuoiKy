# ─── judges/base.py ──────────────────────────────────────────────────────────
from __future__ import annotations
import json, re, time
from abc import ABC, abstractmethod

# ── Exceptions ────────────────────────────────────────────────────────────────
class QuotaExceededException(Exception):
    """Model hết free quota — dừng model này, đánh dấu pending."""
    pass

class TransientException(Exception):
    """Lỗi tạm thời (timeout, 5xx) — retry được."""
    pass

# ── Shared taxonomy prompt text ───────────────────────────────────────────────
SMISHING_TAXONOMY = """
8 CATEGORY SMISHING (label=1):
1. Giả mạo ngân hàng    | obf 1-2 | sender: brandname/shortcode (CẤM personal_number)
   → domain giả (.vip/.top), tài khoản bị khóa, leet nhẹ
2. Đòi nợ / Đe dọa      | obf 0-1 | sender: personal_number
   → tên+CMND+SĐT Zalo, deadline giờ cụ thể, đe dọa gia đình
3. BHXH / Trợ cấp giả   | obf 2-3 | sender: personal_number
   → "NQ-116", "quy BHTN", random code 4 ký tự, domain .icu
4. Tuyển dụng giả        | obf 0-2 | sender: personal_number
   → lương 15-30tr, Zalo link, "không cần vốn"
5. Cờ bạc / Betting      | obf 2-3 | sender: personal_number/shortcode
   → "nạp X nhận Y", t.ly/bit.ly, bonus code
6. Giả mạo dịch vụ công | obf 1-2 | sender: brandname/shortcode/personal_number
   → CSGT/Thuế giả, "biên lai phạt", link .top/.xyz
7. Nội dung nhạy cảm     | obf 3-5 | sender: personal_number
   → ký tự đặc biệt nặng, Telegram/Zalo, dịch vụ tình dục/hẹn hò
8. Crypto / Đầu tư giả   | obf 1-3 | sender: personal_number
   → Telegram group, "thả tim", "nhiệm vụ", 100k-3000k/ngày

OBF LEVELS: 0=formal, 1=leet nhẹ(1-2 ký tự), 2=leet nặng+tên riêng,
3=dot/dash insertion(A-M-A-Z-O-N), 4=mixed special chars, 5=extreme noise
"""

CLEAN_TAXONOMY = """
8 CATEGORY CLEAN (label=0):
1. Ngân hàng thật          | formality 0-1 | sender: brandname/shortcode (CẤM personal_number)
   → domain .com.vn/.vn thật, số TK che (****), hotline chính thức
2. Viễn thông              | formality 0-1 | sender: brandname/shortcode
   → Viettel/Vinaphone/MobiFone, USSD (*098#), gói cước+ngày
3. Thương mại điện tử      | formality 1-2 | sender: brandname/shortcode
   → mã đơn hàng #XXXXX, Shopee/Tiki/Lazada, trạng thái giao
4. Vận chuyển & Logistics   | formality 1-2 | sender: brandname/shortcode
   → mã vận đơn 9-12 ký tự, GHN/GHTK/VTP, dự kiến giao
5. Quảng cáo hợp lệ         | formality 2-3 | sender: shortcode/brandname
   → domain thật, code khuyến mãi, hạn dùng cụ thể
6. Dịch vụ y tế             | formality 2-3 | sender: brandname/shortcode/personal_number
   → tên bệnh viện/phòng khám, ngày giờ, phòng/khoa
7. Dịch vụ công thật        | formality 0-2 | sender: brandname/shortcode
   → domain .gov.vn thật, tên đơn vị chính xác, KHÔNG urgency đe dọa
8. Tin nhắn cá nhân & OTP  | formality 3-4 | sender: personal_number/shortcode
   → OTP 4-8 chữ số + thời hạn, hoặc văn phong thân mật

FORMALITY: 0=template cứng, 1=template mềm, 2=bán formal, 3=thân thiện, 4=cá nhân
"""


def build_prompt(batch: list[dict]) -> str:
    """Xây dựng prompt chung cho cả smishing và clean trong 1 batch."""
    label = str(batch[0]["label"])
    taxonomy = SMISHING_TAXONOMY if label == "1" else CLEAN_TAXONOMY
    label_name = "SMISHING" if label == "1" else "CLEAN"
    level_field = "inferred_obf_level" if label == "1" else "inferred_formality_level"
    level_range_field = "obf_in_range" if label == "1" else "formality_in_range"
    validity_field = "is_smishing" if label == "1" else "is_legitimate"
    extra_field = '"smishing_signals": ["list tối đa 3 dấu hiệu tìm thấy"]' if label == "1" \
        else '"brand_hallucination": true/false,\n  "smishing_like_signals": ["list tối đa 3"]'

    items = "\n".join(
        f'[{i+1}] content: "{r["content"]}" | sender_type: {r["sender_type"]}'
        for i, r in enumerate(batch)
    )

    return f"""Bạn là chuyên gia phân tích SMS tại Việt Nam đang validate dataset AI.

TAXONOMY {label_name}:
{taxonomy}

Phân tích {len(batch)} tin nhắn {label_name} (label={label}) dưới đây.
Với mỗi tin, trả về JSON object:
{{
  "inferred_category": "tên category",
  "{level_field}": <số nguyên>,
  "{level_range_field}": true/false,
  "sender_type_consistent": true/false,
  "{validity_field}": true/false,
  {extra_field},
  "overall_pass": true/false,
  "fail_reason": null hoặc "string ngắn"
}}

Trả về JSON array đúng {len(batch)} object theo thứ tự [1]→[{len(batch)}].
KHÔNG giải thích, KHÔNG markdown fence, CHỈ JSON array thuần.

TIN NHẮN:
{items}"""


def parse_llm_response(raw: str, expected_count: int) -> list[dict] | None:
    """Parse JSON từ LLM response, strip markdown fence nếu có."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text).rstrip("`").strip()
    try:
        result = json.loads(text)
        if isinstance(result, list) and len(result) == expected_count:
            return result
        return None
    except json.JSONDecodeError:
        return None


# ── Abstract base ─────────────────────────────────────────────────────────────
class BaseJudge(ABC):
    name: str

    @abstractmethod
    def _call_api(self, prompt: str) -> str:
        """Gọi API, trả về raw text. Raise QuotaExceededException hoặc TransientException."""
        ...

    def judge_batch(self, batch: list[dict], retries: int = 2) -> list[dict] | None:
        """
        Judge 1 batch. Trả về list kết quả hoặc None nếu parse fail sau retry.
        Raise QuotaExceededException nếu hết quota.
        """
        prompt = build_prompt(batch)
        for attempt in range(retries + 1):
            try:
                raw = self._call_api(prompt)
                result = parse_llm_response(raw, len(batch))
                if result is not None:
                    return result
                # Parse fail → retry
                if attempt < retries:
                    time.sleep(2 ** attempt)
            except QuotaExceededException:
                raise   # propagate ngay, không retry
            except TransientException:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                else:
                    return None
            except Exception:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                else:
                    return None
        return None
