"""
Script sửa lỗi duplicate columns trong features_top5.csv
"""

import pandas as pd

# Đọc file
df = pd.read_csv('data/processed/features_top5.csv')

print("Các cột hiện tại:", df.columns.tolist())
print("Shape:", df.shape)

# Xóa cột trùng (cột has_url.1)
if 'has_url.1' in df.columns:
    print("\n⚠️ Phát hiện cột trùng 'has_url.1'")
    df = df.drop(columns=['has_url.1'])
    print("✅ Đã xóa cột has_url.1")

print("\nCác cột sau khi sửa:", df.columns.tolist())
print("Shape mới:", df.shape)

# Lưu lại
df.to_csv('data/processed/features_top5.csv', index=False, encoding='utf-8-sig')
print("\n✅ Đã lưu file đã sửa: data/processed/features_top5.csv")

