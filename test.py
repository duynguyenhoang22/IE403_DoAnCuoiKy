import re

test_text = "s h o p e e . v n / k h u y e n - m a i"

# Pattern mới: Tập trung vào việc chấp nhận khoảng trắng giữa các ký tự
heavily_obfuscated_pattern = (
    r'(?i)'                           # Case insensitive
    r'\b'                             # Bắt đầu từ ranh giới từ
    r'(?:[a-z0-9]\s+)+'               # Domain body: Ký tự + khoảng trắng (lặp lại): "s h o p e e "
    r'[a-z0-9]'                       # Ký tự cuối của domain body (trước dấu chấm)
    r'\s*'                            # Khoảng trắng tùy chọn
    r'(?:\.|dot|\(\.\)|\[\.\])'       # Dấu chấm (bắt cả các biến thể như " dot ", "(.)")
    r'\s*'                            # Khoảng trắng tùy chọn
    r'(?:[a-z]{1,2}\s*)+'             # TLD: Các ký tự TLD rải rác: "v n" hoặc "c o m"
    r'(?:'                            # Bắt đầu nhóm Path (tùy chọn)
        r'\s*/\s*'                    # Dấu gạch chéo có khoảng trắng bao quanh
        r'[\w\-\s]+'                  # Nội dung path: Chữ, số, gạch ngang và khoảng trắng
    r')?'                             # Kết thúc nhóm Path
)

matches = re.findall(heavily_obfuscated_pattern, test_text)

# Xử lý kết quả để in ra đẹp hơn (xóa khoảng trắng thừa để dễ đọc)
print(f"DEBUG - Raw matches: {matches}")
if matches:
    cleaned_url = matches[0].replace(' ', '')
    print(f"DEBUG - Cleaned match: {cleaned_url}")