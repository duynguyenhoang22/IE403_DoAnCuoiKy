# 🚀 Smishing Detection System

Hệ thống phát hiện tin nhắn SMS lừa đảo (Smishing) cho tiếng Việt, dựa trên bài báo nghiên cứu **"DSmishSMS - A System to Detect Smishing SMS"**.

## 📋 Tổng quan

**Smishing** (SMS Phishing) là hình thức lừa đảo qua tin nhắn SMS nhằm đánh cắp thông tin cá nhân, tài khoản ngân hàng hoặc lừa người dùng chuyển tiền. Hệ thống này sử dụng Machine Learning để tự động phát hiện tin nhắn Smishing.

### 🎯 Mục tiêu
- Phát hiện tự động tin nhắn SMS lừa đảo
- Trích xuất 32 đặc trưng (features) từ mỗi tin nhắn
- Sử dụng 5 features quan trọng nhất để phân loại
- Đạt accuracy cao tương tự paper gốc (97.93%)

## 🏗️ Kiến trúc hệ thống

```
Smishing_system/
├── src/
│   ├── preprocessing.py    # Tiền xử lý văn bản tiếng Việt
│   ├── features.py         # Trích xuất features
│   └── __pycache__/
├── data/
│   ├── raw/
│   │   └── dataset.csv     # Dataset gốc (2,618 tin nhắn)
│   ├── processed/          # Dataset đã xử lý (tạo tự động)
│   │   ├── features_full.csv
│   │   └── features_top5.csv
│   └── dicts/
│       ├── selected_tags_names.txt       # Tags cho accent restoration
│       └── vietnamese-stopwords-dash.txt
├── main.ipynb              # Notebook chính - Feature extraction
├── test_features.py        # Script test features module
├── requirement.txt         # Dependencies
└── README.md              # File này

```

## 🔧 Cài đặt

### 1. Clone repository

```bash
cd Smishing_system
```

### 2. Cài đặt dependencies

```bash
pip install -r requirement.txt
```

**Các thư viện chính:**
- `pandas`, `numpy` - Xử lý dữ liệu
- `pyvi` - Thêm dấu tiếng Việt
- `underthesea` - Tách từ và POS tagging tiếng Việt
- `iocextract` - Trích xuất URL
- `transformers`, `torch` - Deep Learning cho accent restoration

### 3. Test cài đặt

```bash
python test_features.py
```

## 🚀 Sử dụng

### A. Feature Extraction (Trích xuất đặc trưng)

#### Sử dụng Jupyter Notebook (Khuyến nghị)

```bash
jupyter notebook main.ipynb
```

Chạy tuần tự các cell trong notebook để:
1. Load dataset
2. Trích xuất 32 features
3. Chọn Top 5 features
4. Lưu kết quả vào `data/processed/`

#### Sử dụng Python Script

```python
import pandas as pd
from src.features import extract_features_from_dataframe, get_selected_features_df

# Load dataset
df = pd.read_csv('data/raw/dataset.csv')

# Extract tất cả features
df_with_features = extract_features_from_dataframe(df, content_col='content', sender_col='sender_type')

# Lấy top 5 features
df_top5 = get_selected_features_df(df_with_features)

# Lưu kết quả
df_with_features.to_csv('data/processed/features_full.csv', index=False)
df_top5.to_csv('data/processed/features_top5.csv', index=False)
```

### B. Preprocessing (Tiền xử lý văn bản)

```python
from src.preprocessing import clean_text_pipeline, extract_nouns

# Làm sạch văn bản
text = "Ngan Hang VPBANK THONG BAO. Chuc Mung..."
cleaned = clean_text_pipeline(text)

# Trích xuất danh từ
nouns = extract_nouns(cleaned)
```

## 📊 Features (Đặc trưng)

Hệ thống trích xuất **32 features** từ mỗi tin nhắn, chia thành 5 nhóm:

### 1. URL Features (4 features)
- `has_url`: Có URL không?
- `num_urls`: Số lượng URL
- `has_suspicious_domain`: Domain đáng ngờ?
- `url_length_avg`: Độ dài trung bình URL

### 2. Phone Features (4 features)
- `has_phone`: Có số điện thoại không?
- `num_phones`: Số lượng SĐT
- `has_personal_phone`: Có SĐT cá nhân?
- `has_hotline`: Có hotline?

### 3. Text Features (9 features)
- `message_length`: Độ dài tin nhắn
- `num_words`: Số từ
- `num_digits`: Số chữ số
- `digit_ratio`: Tỷ lệ chữ số
- `num_special_chars`: Số ký tự đặc biệt
- `special_char_ratio`: Tỷ lệ ký tự đặc biệt
- `num_uppercase`: Số ký tự in hoa
- `uppercase_ratio`: Tỷ lệ chữ in hoa
- `has_mixed_language`: Lẫn tiếng Việt có/không dấu

### 4. Keyword Features (11 features)
- `num_financial_keywords`: Từ khóa tài chính
- `num_urgency_keywords`: Từ khóa khẩn cấp
- `num_action_keywords`: Từ khóa hành động
- `num_reward_keywords`: Từ khóa thưởng/lừa đảo
- `num_impersonation_keywords`: Từ khóa giả mạo cơ quan
- `has_*`: Binary flags (1/0) cho mỗi loại keyword
- `keyword_density`: Mật độ keyword

### 5. Sender Features (4 features)
- `is_brandname`: Gửi từ brandname?
- `is_shortcode`: Gửi từ shortcode?
- `is_personal_number`: Gửi từ SĐT cá nhân?
- `is_unknown`: Không xác định?

### 🏆 Top 5 Features (theo paper)
1. `has_url`
2. `has_phone`
3. `num_financial_keywords`
4. `num_urgency_keywords`
5. `is_personal_number`

## 📈 Dataset

- **Tổng số tin nhắn**: 2,618
- **Nguồn**: SMS thực từ điện thoại người dùng Việt Nam
- **Nhãn**: 
  - `0` - Not Smishing (Tin nhắn hợp pháp)
  - `1` - Smishing (Tin nhắn lừa đảo)
- **Các cột**:
  - `content`: Nội dung tin nhắn
  - `label`: Nhãn (0/1)
  - `has_url`: Có URL không?
  - `has_phone_number`: Có SĐT không?
  - `sender_type`: Loại người gửi (brandname/shortcode/personal_number)

## 🔬 Preprocessing Pipeline

```
Unicode Normalization 
    ↓
URL Removal
    ↓
Structure Normalization (tách dấu câu dính)
    ↓
Accent Restoration (thêm dấu bằng Deep Learning)
    ↓
Word Tokenization (tách từ)
    ↓
POS Tagging (gán nhãn từ loại)
    ↓
Noun Extraction (trích xuất danh từ)
```

### Công nghệ sử dụng

- **XLM-RoBERTa** (`peterhung/vietnamese-accent-marker-xlm-roberta`) - Thêm dấu tiếng Việt
- **Underthesea** - Tách từ và POS tagging
- **iocextract** - Trích xuất URL (hỗ trợ defanged URLs)

## 📚 Tham khảo

Paper gốc:
```
Mishra, S., & Soni, D. (2021). 
DSmishSMS - A System to Detect Smishing SMS. 
SN Computer Science, 2(5), 1-19.
```

## 🚀 Bước tiếp theo

- [ ] **Train Model**: Implement Backpropagation Algorithm và các ML classifiers
- [ ] **Domain Checking Phase**: Kiểm tra độ tin cậy của URL (WHOIS, blacklist, SSL)
- [ ] **Model Evaluation**: Đánh giá accuracy, precision, recall, F1-score
- [ ] **Deployment**: Tạo API hoặc web app để detect real-time
- [ ] **Feature Importance Analysis**: Phân tích features nào quan trọng nhất

## 📝 Ghi chú

- Preprocessing pipeline đã được tối ưu cho tiếng Việt (xử lý thiếu dấu, từ viết tắt)
- Dataset chứa các kịch bản lừa đảo phổ biến ở Việt Nam (giả mạo ngân hàng, OTP, cơ quan nhà nước)
- Feature extraction mất khoảng 0.1s/tin nhắn

## 🤝 Đóng góp

Dự án phát triển cho môn IE403 - Machine Learning. Mọi góp ý xin gửi về:
- Email: [your-email@example.com]
- GitHub Issues: [link]

## 📄 License

Educational project - IE403 Final Project

---

**Made with ❤️ for IE403 - UIT**

