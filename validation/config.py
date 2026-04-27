# ─── config.py ──────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()

# ── Model endpoints & names (free tier) ──────────────────────────────────────
MODEL_CONFIG = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model":    "gemini-2.0-flash",          # free tier Google AI Studio
        "type":     "self",                       # self-validation
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "model":    "grok-3-mini",               # free tier xAI
        "type":     "cross",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model":    "qwen-turbo",                # free quota DashScope
        "type":     "cross",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model":    "deepseek-chat",             # free tier DeepSeek
        "type":     "cross",
    },
}

ALL_JUDGES = list(MODEL_CONFIG.keys())  # ["gemini", "grok", "qwen", "deepseek"]

# ── Voting thresholds ─────────────────────────────────────────────────────────
MAJORITY_THRESHOLD = 3   # cần >= 3/4 pass để kết luận pass
TIE_THRESHOLD      = 2   # 2-2 → manual review

# ── Batch size cho LLM calls ─────────────────────────────────────────────────
LLM_BATCH_SIZE = 10
LLM_MAX_RETRIES = 2      # retry cho transient error (timeout, 5xx)

# ── Taxonomy: SMISHING ────────────────────────────────────────────────────────
SMISHING_CATEGORIES = [
    "Giả mạo ngân hàng",
    "Đòi nợ / Đe dọa",
    "BHXH / Trợ cấp giả",
    "Tuyển dụng giả",
    "Cờ bạc / Betting",
    "Giả mạo dịch vụ công",
    "Nội dung nhạy cảm",
    "Crypto / Đầu tư giả",
]
SMISHING_OBF_RANGE = {
    "Giả mạo ngân hàng":   (1, 2),
    "Đòi nợ / Đe dọa":     (0, 1),
    "BHXH / Trợ cấp giả":  (2, 3),
    "Tuyển dụng giả":       (0, 2),
    "Cờ bạc / Betting":     (2, 3),
    "Giả mạo dịch vụ công": (1, 2),
    "Nội dung nhạy cảm":    (3, 5),
    "Crypto / Đầu tư giả":  (1, 3),
}
SMISHING_SENDER_FORBIDDEN = {
    "Giả mạo ngân hàng": {"personal_number"},
}

# ── Taxonomy: CLEAN ───────────────────────────────────────────────────────────
CLEAN_CATEGORIES = [
    "Ngân hàng thật",
    "Viễn thông",
    "Thương mại điện tử",
    "Vận chuyển & Logistics",
    "Quảng cáo hợp lệ",
    "Dịch vụ y tế",
    "Dịch vụ công thật",
    "Tin nhắn cá nhân & OTP",
]
CLEAN_FORMALITY_RANGE = {
    "Ngân hàng thật":         (0, 1),
    "Viễn thông":             (0, 1),
    "Thương mại điện tử":     (1, 2),
    "Vận chuyển & Logistics":  (1, 2),
    "Quảng cáo hợp lệ":       (2, 3),
    "Dịch vụ y tế":           (2, 3),
    "Dịch vụ công thật":      (0, 2),
    "Tin nhắn cá nhân & OTP": (3, 4),
}
CLEAN_SENDER_FORBIDDEN = {
    "Ngân hàng thật":         {"personal_number"},
    "Viễn thông":             {"personal_number"},
    "Thương mại điện tử":     {"personal_number"},
    "Vận chuyển & Logistics":  {"personal_number"},
    "Quảng cáo hợp lệ":       {"personal_number"},
    "Dịch vụ công thật":      {"personal_number"},
}

# ── URL/domain patterns ───────────────────────────────────────────────────────
FAKE_TLDS        = {".vip",".top",".xyz",".cc",".icu",".cfd",".life",".biz",".me",".info"}
SHORTENED_HOSTS  = {"t.ly","bit.ly","tinyurl.com","shorturl.at","sourl.cn"}
LEGIT_TLDS       = {".vn",".com.vn",".gov.vn",".edu.vn",".org.vn"}

MIN_LEN = {"smishing": 40, "clean": 20}
MAX_LEN = {"smishing": 600, "clean": 300}
