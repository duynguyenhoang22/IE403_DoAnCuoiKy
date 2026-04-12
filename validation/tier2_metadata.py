# ─── tier2_metadata.py ───────────────────────────────────────────────────────
import re
from urllib.parse import urlparse
from config import FAKE_TLDS, SHORTENED_HOSTS, LEGIT_TLDS

_URL_EXTRACT = re.compile(
    r"https?://[^\s|]+"
    r"|www\.[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}"
    r"|[a-zA-Z0-9\-]+\.(vip|top|xyz|cc|icu|cfd|life|vn|com\.vn|gov\.vn)"
    r"|t\.ly/\S+|bit\.ly/\S+|tinyurl\.com/\S+|sourl\.cn/\S+",
    re.I,
)
_URGENCY = re.compile(
    r"khan.?cap|ngay.?lap.?tuc|trong\s*\d+\s*[hH]|het.?han|bi.?khoa|"
    r"mat.?toan.?bo|canh.?bao|dang.?nhap.?ngay|xac.?thuc.?ngay|nhan.?tien|"
    r"trung.?thuong|bhtn|nq.?116|quy.?bh", re.I
)
_LEET   = re.compile(r"[0-9][a-zA-Z]|[a-zA-Z][0-9]|[!@#$%^&*]{2,}")
_FAKETLD= re.compile(r"\.(vip|top|xyz|cc|icu|cfd|t\.ly|bit\.ly)", re.I)


def _extract_urls(text: str) -> list[str]:
    """Dùng finditer để tránh bug capturing group của findall."""
    return [m.group(0) for m in _URL_EXTRACT.finditer(text)]


def _classify_url(url: str) -> str:
    u = url.lower()
    for h in SHORTENED_HOSTS:
        if h in u: return "shortened"
    try:
        host = urlparse(u if u.startswith("http") else "http://"+u).hostname or u
    except Exception:
        host = u
    for tld in FAKE_TLDS:
        if host.endswith(tld): return "fake"
    for tld in LEGIT_TLDS:
        if host.endswith(tld): return "legit"
    return "unknown"


def validate_tier2(row: dict) -> dict:
    errors = []
    c  = str(row["content"]).strip()
    lb = str(row["label"]).strip()
    hu = str(row["has_url"]).strip()
    st = str(row["sender_type"]).strip().lower()

    urls = _extract_urls(c)

    # Smishing + URL → phải là fake/shortened
    if lb=="1" and hu=="1":
        legit = [u for u in urls if _classify_url(u)=="legit"]
        if legit:
            errors.append(f"smishing_has_legit_domain:{legit[0]!r}")

    # Clean + URL → phải là legit
    if lb=="0" and hu=="1":
        fake = [u for u in urls if _classify_url(u) in ("fake","shortened")]
        if fake:
            errors.append(f"clean_has_fake_domain:{fake[0]!r}")

    # Smishing không có dấu hiệu nào → nghi ngờ nhãn sai
    if lb=="1":
        has_signal = bool(_URGENCY.search(c) or _LEET.search(c) or _FAKETLD.search(c) or
                         (hu=="1" and any(_classify_url(u)!="legit" for u in urls)))
        if not has_signal:
            errors.append("smishing_no_signals:không tìm thấy obfuscation/urgency/fake_url")

    if errors:
        return {"pass": False, "fail_code": "T2-meta", "fail_reason": "; ".join(errors)}
    return {"pass": True, "fail_code": None, "fail_reason": None}
