import pandas as pd
import sys
from pathlib import Path

# Thêm project root vào Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from misspelled_words.misspelled import load_resources, extract_spelling_features

# Sử dụng absolute path dựa trên vị trí của script
DATA_PATH = project_root / 'data' / 'dataset.csv'
OUTPUT_PATH = project_root / 'data' / 'dataset_with_features.csv'

print(f"Loading data from: {DATA_PATH}")
df = pd.read_csv(DATA_PATH)

print(f"Dataset loaded: {len(df)} rows")

# Load resources
print("Loading spelling resources...")
vocab, max_len, stopwords = load_resources()

# Áp dụng lên DataFrame
print("Extracting features...")
results = df['content'].apply(
    lambda x: extract_spelling_features(x, vocab, max_len, stopwords)
)

# Unpack results (misspelled_count, leet_count, total_tokens, misspelled_pct, leet_pct)
df[['misspelled_count', 'leet_count', 'total_tokens', 'misspelled_pct', 'leet_pct']] = pd.DataFrame(
    results.tolist(), 
    index=df.index
)

# Lưu kết quả
print(f"Saving results to: {OUTPUT_PATH}")
df.to_csv(OUTPUT_PATH, index=False)

print("\n" + "="*60)
print("✓ FEATURE EXTRACTION COMPLETED")
print("="*60)
print(f"Processed: {len(df)} records")
print(f"Average misspelled: {df['misspelled_count'].mean():.2f} ({df['misspelled_pct'].mean():.2f}%)")
print(f"Average leet: {df['leet_count'].mean():.2f} ({df['leet_pct'].mean():.2f}%)")
print(f"Average total tokens: {df['total_tokens'].mean():.2f}")
print("="*60)