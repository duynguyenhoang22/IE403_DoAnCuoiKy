# ─── tier1_rules.py ──────────────────────────────────────────────────────────
import re
from config import FAKE_TLDS, SHORTENED_HOSTS, LEGIT_TLDS, MIN_LEN, MAX_LEN

VALID_SENDER = {"brandname", "shortcode", "personal_number"}

_URL_RE = re.compile(
    r"https?://[^\s|]+"
    r"|www\.[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}"
    r"|[a-zA-Z0-9\-]+\.(vip|top|xyz|cc|icu|cfd|life|vn|com\.vn|gov\.vn)"
    r"|t\.ly/\S+|bit\.ly/\S+|tinyurl\.com/\S+|sourl\.cn/\S+",
    re.I,
)
_PHONE_RE = re.compile(
    r"(?<!\d)(0[3-9]\d[\s\-]?\d{3}[\s\-]?\d{4}|\+84[\s\-]?[3-9]\d[\s\-]?\d{3}[\s\-]?\d{4})(?!\d)"
)


def validate_tier1(row: dict) -> dict:
    errors = []
    for col in ("content","label","has_url","has_phone_number","sender_type"):
        if not str(row.get(col,"")).strip():
            errors.append(f"missing:{col}")
    if errors:
        return {"pass": False, "fail_code": "T1-format", "fail_reason": "; ".join(errors)}

    c  = str(row["content"]).strip()
    lb = str(row["label"]).strip()
    hu = str(row["has_url"]).strip()
    hp = str(row["has_phone_number"]).strip()
    st = str(row["sender_type"]).strip().lower()

    if lb not in ("0","1"):           errors.append(f"invalid_label:{lb!r}")
    if hu not in ("0","1"):           errors.append(f"invalid_has_url:{hu!r}")
    if hp not in ("0","1"):           errors.append(f"invalid_has_phone:{hp!r}")
    if st not in VALID_SENDER:        errors.append(f"invalid_sender_type:{st!r}")
    if errors:
        return {"pass": False, "fail_code": "T1-format", "fail_reason": "; ".join(errors)}

    key = "smishing" if lb=="1" else "clean"
    if len(c) < MIN_LEN[key]: errors.append(f"too_short:{len(c)}<{MIN_LEN[key]}")
    if len(c) > MAX_LEN[key]: errors.append(f"too_long:{len(c)}>{MAX_LEN[key]}")

    url_in_text   = bool(_URL_RE.search(c))
    phone_in_text = bool(_PHONE_RE.search(c))

    if hu=="1" and not url_in_text:   errors.append("has_url=1_no_url_in_content")
    if hu=="0" and url_in_text:       errors.append("has_url=0_url_found_in_content")
    if hp=="1" and not phone_in_text: errors.append("has_phone=1_no_phone_in_content")
    if hp=="0" and phone_in_text:     errors.append("has_phone=0_phone_found_in_content")

    if errors:
        return {"pass": False, "fail_code": "T1-format", "fail_reason": "; ".join(errors)}
    return {"pass": True, "fail_code": None, "fail_reason": None}
