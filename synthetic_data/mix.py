import pandas as pd

# ─── CẤU HÌNH ─────────────────────────────────────────────────────────────────
FILE_LABEL_1 = "synthetic_data\synthetic_smishing_label1.csv"      # ← file chứa label 1
FILE_LABEL_0 = "synthetic_data\\synthetic_legitimate_label0.csv"           # ← file chứa label 0
OUTPUT_FILE  = "synthetic_data\dataset_mixed.csv"
RANDOM_SEED  = 42
# ──────────────────────────────────────────────────────────────────────────────

df1 = pd.read_csv(FILE_LABEL_1)
df0 = pd.read_csv(FILE_LABEL_0)

print(f"Label 1: {len(df1)} mẫu")
print(f"Label 0: {len(df0)} mẫu")

df_mixed = pd.concat([df1, df0], ignore_index=True).sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

df_mixed.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"\n✅ Đã mix xong: {len(df_mixed)} mẫu → {OUTPUT_FILE}")
print(df_mixed["label"].value_counts().to_string())