# run_tests_csv.py
import pandas as pd
from predict_system import SmishingDetectionSystem

# ─── CẤU HÌNH ── Chỉ cần sửa phần này ────────────────────────────────────────
DATASET_PATH = "synthetic_data\\dataset_mixed.csv"   # ← tên file CSV của bạn
TEXT_COL     = "content"            # ← cột nội dung SMS
LABEL_COL    = "label"              # ← cột nhãn: 0 = ham, 1 = smishing
SENDER_COL   = "sender_type"        # ← cột sender
# Các cột phụ (không dùng để predict nhưng giữ lại trong output để phân tích)
IS_URL_COL   = "has_url"
IS_PHONE_COL = "has_phone_number"
N_SAMPLES    = 100
RANDOM_SEED  = 42
OUTPUT_PATH  = "Smishing\\error_analysis_results.csv"
# ──────────────────────────────────────────────────────────────────────────────

class Color:
    RED    = '\033[91m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    BLUE   = '\033[94m'
    RESET  = '\033[0m'


def classify_error(row):
    """Phân loại tự động lỗi FP/FN theo đặc điểm tin nhắn."""
    text  = str(row[TEXT_COL]).lower()
    true  = int(row[LABEL_COL])
    pred  = int(row["pred_label"])
    phase = str(row["phase"])

    if true == pred:
        return "CORRECT"

    # FALSE POSITIVE: Ham bị gán là Smishing
    if true == 0 and pred == 1:
        if any(kw in text for kw in ["otp", "ma xac thuc", "ma giao dich"]):
            return "FP_OTP"
        if any(kw in text for kw in ["khuyen mai", "nha mang", "viettel",
                                      "mobifone", "vinaphone", "qc", "quang cao"]):
            return "FP_carrier_ad"
        if (any(kw in text for kw in ["chuyen khoan", "tien", "muon"]) and
                any(kw in text for kw in ["anh", "em", "ban", "tao", "may"])):
            return "FP_personal_financial"
        if phase == "AI Detection":
            return "FP_ai_false_alarm"
        return "FP_other"

    # FALSE NEGATIVE: Smishing bị bỏ sót
    if true == 1 and pred == 0:
        has_url = any(kw in text for kw in
                      ["http", "www", ".com", ".vn", ".xyz", "bit.ly"])
        if not has_url:
            return "FN_no_url"
        if not any(kw in text for kw in ["!", "@", "0", "4", "3", "1"]):
            return "FN_clean_text"
        if any(kw in text for kw in ["anh", "em", "ban", "toi"]):
            return "FN_impersonation_personal"
        if phase == "Conversation Guard":
            return "FN_blocked_by_conv_guard"
        return "FN_other"

    return "UNKNOWN"


def main():
    # ── 1. Load CSV ──────────────────────────────────────────────────────────
    print(f"\n📂 Đang load: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"   Tổng mẫu: {len(df)}")
    print(f"   Phân bố nhãn:\n{df[LABEL_COL].value_counts().to_string()}")

    # ── 2. Lấy N_SAMPLES mẫu ngẫu nhiên (stratified) ────────────────────────
    sample = (
        df.groupby(LABEL_COL, group_keys=False)
          .apply(lambda x: x.sample(
              min(len(x), max(1, int(N_SAMPLES * len(x) / len(df)))),
              random_state=RANDOM_SEED
          ))
    )
    if len(sample) < N_SAMPLES:
        extra = df.drop(sample.index).sample(
            N_SAMPLES - len(sample), random_state=RANDOM_SEED
        )
        sample = pd.concat([sample, extra])
    sample = sample.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    print(f"\n✅ Đã chọn {len(sample)} mẫu (stratified)")
    print(f"   Phân bố mẫu:\n{sample[LABEL_COL].value_counts().to_string()}\n")

    # ── 3. Load model ────────────────────────────────────────────────────────
    system = SmishingDetectionSystem(threshold=0.46)

    # ── 4. Predict và hiển thị từng mẫu (giống script gốc) ──────────────────
    print(f"\n{'='*130}")
    print(f"{'#':<4} | {'LABEL':<7} | {'SENDER':<15} | {'TEXT PREVIEW':<52} | {'RESULT':<19} | PHASE / REASON")
    print(f"{'='*130}")

    results = []
    for idx, row in sample.iterrows():
        text       = str(row[TEXT_COL])
        true_label = int(row[LABEL_COL])
        sender     = str(row[SENDER_COL]) if SENDER_COL and SENDER_COL in row else "unknown"
        is_url     = row.get(IS_URL_COL, None)
        is_phone   = row.get(IS_PHONE_COL, None)

        try:
            res = system.predict(text, sender_type=sender)
        except Exception as e:
            res = {
                "is_smishing": False, "confidence": 0.0,
                "raw_ai_score": 0.0, "domain_risk": 0.0,
                "reason": f"ERROR: {e}", "phase": "ERROR"
            }

        pred_label = int(res["is_smishing"])
        correct    = (true_label == pred_label)

        # Màu sắc
        if res["is_smishing"]:
            status = f"{Color.RED}❌ LỪA ĐẢO{Color.RESET}"
        else:
            status = f"{Color.GREEN}✅ SẠCH   {Color.RESET}"

        # Đánh dấu mẫu sai
        true_str = f"{Color.YELLOW}[SMISHING]{Color.RESET}" if true_label == 1 else "[HAM]    "
        marker   = "" if correct else f"{Color.YELLOW}◄ SAI{Color.RESET}"

        display_text = (text[:49] + "…") if len(text) > 49 else text
        print(
            f"{idx:<4} | {true_str:<7} | {sender:<15} | {display_text:<52} | "
            f"{status:<19} | [{res['phase']}] {res['reason'][:60]} {marker}"
        )

        results.append({
            TEXT_COL:        text,
            LABEL_COL:       true_label,
            "sender":        sender,
            "is_url":        is_url,
            "is_phone":      is_phone,
            "pred_label":    pred_label,
            "correct":       correct,
            "confidence":    round(res["confidence"], 4),
            "raw_ai_score":  round(res["raw_ai_score"], 4),
            "domain_risk":   res["domain_risk"],
            "phase":         res["phase"],
            "reason":        res["reason"],
        })

    # ── 5. Phân loại lỗi ────────────────────────────────────────────────────
    df_result = pd.DataFrame(results)
    df_result["error_type"] = df_result.apply(classify_error, axis=1)

    errors  = df_result[df_result["correct"] == False]
    fp      = errors[errors[LABEL_COL] == 0]
    fn      = errors[errors[LABEL_COL] == 1]
    correct_count = df_result["correct"].sum()

    # ── 6. Tóm tắt kết quả ──────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  TÓM TẮT TRÊN {N_SAMPLES} MẪU")
    print(f"{'='*60}")
    print(f"  Đúng  : {correct_count}/{N_SAMPLES}  ({100*correct_count/N_SAMPLES:.1f}%)")
    print(f"  Sai   : {len(errors)}/{N_SAMPLES}  ({100*len(errors)/N_SAMPLES:.1f}%)")
    print(f"  ├─ False Positive (Ham → Smishing) : {len(fp)}")
    print(f"  └─ False Negative (Smishing → Ham) : {len(fn)}")

    print(f"\n{'─'*40}")
    print("  Phân loại lỗi:")
    print(errors["error_type"].value_counts().to_string())

    print(f"\n{'─'*40}")
    print("  Decision phase của các lỗi:")
    print(errors["phase"].value_counts().to_string())

    # ── 7. Ví dụ cụ thể ─────────────────────────────────────────────────────
    if len(fp) > 0:
        print(f"\n{Color.YELLOW}─── Ví dụ False Positive (Ham bị gán Smishing) ───{Color.RESET}")
        for _, r in fp.head(3).iterrows():
            print(f"  [{r['error_type']}] Score={r['confidence']:.2f} | Phase={r['phase']}")
            print(f"  Text: {r[TEXT_COL][:120]}\n")

    if len(fn) > 0:
        print(f"\n{Color.RED}─── Ví dụ False Negative (Smishing bị bỏ sót) ────{Color.RESET}")
        for _, r in fn.head(3).iterrows():
            print(f"  [{r['error_type']}] Score={r['confidence']:.2f} | Phase={r['phase']}")
            print(f"  Text: {r[TEXT_COL][:120]}\n")

    # ── 8. Lưu file ─────────────────────────────────────────────────────────
    df_result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n✅ Đã lưu kết quả vào: {OUTPUT_PATH}")
    print("   (Mở file này để xem chi tiết và chỉnh error_type thủ công nếu cần)\n")


if __name__ == "__main__":
    main()
