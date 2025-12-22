# Kiến trúc phát hiện lỗi chính tả
_Exported on 12/17/2025 at 16:25:58 GMT+7 from Cursor (2.2.20)_

---

**User**

@data/dataset.csv Mục tiêu là xây dựng một cách hiệu quả và chính xác để giải quyết đặc trưng "lỗi chính tả", bạn có toàn quyền tham khảo và thiết kế đề xuất dựa trên kiến trúc này: 
Kiến trúc Phân tầng (Layered Architecture)
Hệ thống hoạt động theo mô hình cái phễu 4 tầng. Dữ liệu đi từ trên xuống, tầng trên xử lý xong mới chuyền xuống tầng dưới.

Tầng 1: Aggressive Masking (Che giấu thực thể hung hăng)
Nhiệm vụ: Tìm và thay thế các thực thể phi ngôn ngữ bằng token chung.

Công cụ: Regex (Biểu thức chính quy).

Yêu cầu đặc biệt: Phải "hung hăng" (Aggressive) để bắt cả các biến thể cố tình viết sai của Spammer.

Các token bắt buộc:

<URL>: Bắt cả http, www, bit.ly, banca . com, [ domain . com ].

<PHONE>: Bắt cả 09xxx, 84xxx, 09xx.xxx.xxx.

<CODE>: Bắt chuỗi in hoa kèm số (ST5K, OTP123, V120N).

<MONEY>: Bắt số tiền (100k, 500.000d, 1 triệu).

<DATE/TIME> (Tùy chọn): 15/05, 10h30.

Tầng 2: Tokenization & Normalization (Cắt từ & Chuẩn hóa)
Nhiệm vụ: Chia câu thành các đơn vị có nghĩa để kiểm tra.

Công cụ:

Thư viện tách từ tiếng Việt (pyvi hoặc underthesea) để giữ ngữ nghĩa từ ghép (ví dụ: ngân_hàng thay vì ngân, hàng).

Hàm chuẩn hóa Unicode (đưa về dựng sẵn NFC).

Yêu cầu: Xử lý các từ dính nhau (Glue words) nếu Regex Tầng 1 chưa bắt hết (ví dụ: ngày/đêm -> ngày / đêm).

Tầng 3: Whitelist Filtering (Bộ lọc ngoại lệ)
Nhiệm vụ: Bỏ qua các từ "đặc thù" không có trong từ điển nhưng hợp lệ trong tin nhắn.

Cấu trúc dữ liệu: Set (Hash Set) để tra cứu O(1).

3 Danh sách cần có:

Brand List: Tên thương hiệu, ngân hàng, ví điện tử (shopee, momo, vcb).

Jargon List: Thuật ngữ viễn thông/marketing (data, 4g, voucher, deal).

Slang/Abbr List: Viết tắt, teencode (lh, qc, nt, ko, dc).

Tầng 4: Dual-Lookup Validation (Tra cứu kép)
Nhiệm vụ: Kiểm tra tính hợp lệ của từ tiếng Việt, chấp nhận sự nhập nhằng có dấu/không dấu.

Cơ chế:

Check 1: Có trong Vietnamese_Full_Dict (Có dấu) không?

Check 2: Có trong Vietnamese_Shadow_Dict (Không dấu) không?

Kết quả: Nếu trượt cả 2 -> Đánh dấu là Misspell / Unknown Token.


Về mặt kiến trúc, có thể gợi ý điều chỉnh nếu cảm thấy không phù hợp hoặc không cần thiết. còn về tài nguyên yêu cầu bên trong thì không phải vấn đề. 

---

**Cursor**

Để đưa ra đề xuất phù hợp, tôi cần xem qua cấu trúc và nội dung của dataset trước.

Để hiểu rõ hơn về dữ liệu và các tài nguyên hiện có, tôi cần xem thêm một số file:

Bây giờ tôi đã hiểu rõ dữ liệu và tài nguyên hiện có. Dựa trên phân tích dataset và kiến trúc bạn đề xuất, tôi sẽ đưa ra **đánh giá chi tiết và đề xuất điều chỉnh**:

---

## 📊 Phân Tích Đặc Điểm Dữ Liệu

Từ dataset, tôi nhận diện được **5 nhóm lỗi chính tả chính** trong tin nhắn spam/smishing:

| Nhóm | Ví dụ | Tần suất |
|------|-------|----------|
| **1. Leetspeak** | `kh0ng`, `d!eu k!en`, `DU0C` | Rất cao |
| **2. Viết không dấu** | `dieu kien`, `vui long`, `tai khoan` | Rất cao |
| **3. Gibberish/Random** | `tORKiM! ay:Ma""n;N,ha7lXklq` | Trung bình |
| **4. Teencode/Viết tắt** | `lh`, `qc`, `dc`, `tt` | Trung bình |
| **5. Biến thể domain giả** | `vcbielbiok`, `vniatinbanks` | Thấp |

---

## ✅ Đánh Giá Kiến Trúc 4 Tầng Đề Xuất

### Tầng 1: Aggressive Masking ✓ **ĐỒNG Ý - CẦN THIẾT**
Đây là tầng **rất quan trọng** vì nó:
- Loại bỏ nhiễu từ các thực thể phi ngôn ngữ
- Giảm false positive (URL, số tiền không phải lỗi chính tả)

**Đề xuất bổ sung regex patterns:**

```python
# Patterns cần "hung hăng" cho smishing Việt Nam
PATTERNS = {
    '<URL>': r'(?:https?://|www\.|bit\.ly|[a-z0-9-]+\s*\.\s*(?:com|vn|top|xyz|icu|vip|cc|life|club|cfd))',
    '<PHONE>': r'(?:\+?84|0)\s*\d[\d\s\.\-]{7,12}',
    '<CODE>': r'\b[A-Z0-9]{3,}[A-Z][0-9]+|[0-9]+[A-Z]{2,}\b',  # ST5K, OTP123
    '<MONEY>': r'\d{1,3}(?:[.,]\d{3})*\s*(?:k|tr|triệu|trieu|VND|VNĐ|dong|đồng|d)\b',
    '<ZALO>': r'zalo\.me/\d+|zalo:\s*\d+',
}
```

### Tầng 2: Tokenization & Normalization ✓ **ĐỒNG Ý - CẦN THIẾT**

**Tuy nhiên**, tôi đề xuất **THÊM 1 bước trước khi tokenize**: **Leetspeak Normalization**

```
Luồng đề xuất:
Raw Text → Leet Decode → Unicode NFC → Word Tokenization
```

Lý do: Leetspeak xuất hiện **rất nhiều** trong dataset (`kh0ng`, `d!eu`, `h0 tro`). Nếu decode trước khi tokenize sẽ giúp:
- pyvi/underthesea nhận diện từ ghép tốt hơn
- Giảm số lượng "unknown tokens" ở Tầng 4

### Tầng 3: Whitelist Filtering ✓ **ĐỒNG Ý - CẦN THIẾT**

3 danh sách đề xuất hợp lý. **Bổ sung thêm**:

| Danh sách | Ví dụ cần có |
|-----------|--------------|
| **Bank/Finance** | `vcb`, `acb`, `bidv`, `vpbank`, `techcombank`, `momo`, `zalopay` |
| **Telco** | `viettel`, `vinaphone`, `mobifone`, `4g`, `5g`, `data`, `sim` |
| **E-commerce** | `shopee`, `lazada`, `tiki`, `grab`, `gojek` |
| **Common abbr** | `qc`, `lh`, `nt`, `ko`, `dc`, `ns`, `ib`, `ms`, `cskh` |

### Tầng 4: Dual-Lookup Validation ✓ **ĐỒNG Ý NHƯNG CẦN ĐIỀU CHỈNH**

Đây là điểm **cần cân nhắc kỹ nhất**:

**Vấn đề với cách tiếp cận hiện tại:**
- Từ điển `words.txt` có ~79,000 từ **có dấu** 
- SMS spam thường **không có dấu** → Hầu hết từ sẽ "trượt" Check 1
- Shadow Dict (không dấu) sẽ có **rất nhiều collision** (vd: `an` → ăn, án, àn, ản, ãn, ạn...)

---

## 🔄 ĐỀ XUẤT KIẾN TRÚC CẢI TIẾN

Tôi đề xuất **kiến trúc 5 tầng** với việc tách riêng xử lý Leetspeak:

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Raw SMS Text                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 1: AGGRESSIVE MASKING                                  │
│ ─────────────────────────────────────────────────────────── │
│ • Regex bắt URL, Phone, Money, Code, Date/Time              │
│ • Output: Text với <ENTITY> tokens                          │
│ • Bonus: Đếm số entity → Feature cho ML                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 2: LEETSPEAK DETECTION & DECODE  ← [MỚI]              │
│ ─────────────────────────────────────────────────────────── │
│ • Detect patterns: 0→o, 1→i, !→i, 3→e, @→a, $→s            │
│ • Output 1: leet_count (số ký tự bị thay)                   │
│ • Output 2: Decoded text (cho các tầng sau)                 │
│ • QUAN TRỌNG: Giữ lại bản gốc để đếm leet riêng            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 3: TOKENIZATION + NORMALIZATION                        │
│ ─────────────────────────────────────────────────────────── │
│ • Unicode NFC normalization                                 │
│ • pyvi/underthesea word segmentation                        │
│ • Xử lý từ dính: "ngày/đêm" → "ngày / đêm"                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 4: WHITELIST FILTERING                                 │
│ ─────────────────────────────────────────────────────────── │
│ • Brand names (ngân hàng, ví, telco, ecommerce)            │
│ • Technical jargon (otp, data, voucher)                     │
│ • Common abbreviations & teencode                           │
│ • Entity tokens (<URL>, <PHONE>, etc.)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 5: VIETNAMESE VALIDATION + ACCENT RESTORATION          │
│ ─────────────────────────────────────────────────────────── │
│ STRATEGY A (Fast - Rule-based):                             │
│   • Check Vietnamese_Shadow_Dict (no-accent)                │
│   • Từ "có thể có dấu" → VALID                              │
│   • Từ không match → MISSPELL                               │
│                                                             │
│ STRATEGY B (Accurate - Hybrid):                             │
│   • Dùng XLM-RoBERTa restore accent trước                   │
│   • Check Full_Dict với từ đã có dấu                        │
│   • So sánh original vs restored → Detect intentional       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT FEATURES:                                            │
│ • misspelled_count, misspelled_pct                          │
│ • leet_count, leet_pct                                      │
│ • unknown_token_count (gibberish)                           │
│ • entity_counts (url, phone, money, code)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 Giải Thích Chi Tiết Các Điều Chỉnh

### 1. Tách Leetspeak thành tầng riêng (Tầng 2)

**Lý do:**
- Leetspeak là **đặc trưng mạnh** phân biệt spam vs ham (tin thường không có)
- Cần **đếm riêng** leet_count như feature cho ML model
- Decode trước giúp các tầng sau hoạt động chính xác hơn

```python
LEET_MAP = {
    '0': 'o', '1': 'i', '!': 'i', '3': 'e', 
    '4': 'a', '@': 'a', '$': 's', '5': 's',
    '7': 't', '8': 'b', '9': 'g'
}

def decode_leet(text):
    leet_count = 0
    result = []
    for char in text:
        if char in LEET_MAP:
            result.append(LEET_MAP[char])
            leet_count += 1
        else:
            result.append(char)
    return ''.join(result), leet_count
```

### 2. Chiến lược Dual-Dict cải tiến (Tầng 5)

**Vấn đề collision của Shadow Dict:**
```
"an" (không dấu) → có thể là: ăn, án, àn, ản, ãn, ạn, an
```

**Giải pháp: "Có thể hợp lệ" thay vì "Chắc chắn hợp lệ"**

```python
def build_shadow_dict(full_dict):
    """
    Tạo shadow dict: no_accent_form → set of possible accented forms
    """
    shadow = defaultdict(set)
    for word in full_dict:
        no_accent = remove_accents(word.lower())
        shadow[no_accent].add(word)
    return shadow

def validate_word(word, full_dict, shadow_dict, whitelist):
    word_lower = word.lower()
    no_accent = remove_accents(word_lower)
    
    # Check 1: Whitelist (brands, jargon, abbr)
    if word_lower in whitelist:
        return 'VALID_WHITELIST'
    
    # Check 2: Full dict (có dấu)
    if word_lower in full_dict:
        return 'VALID_FULL'
    
    # Check 3: Shadow dict (không dấu nhưng CÓ THỂ hợp lệ)
    if no_accent in shadow_dict:
        return 'VALID_SHADOW'  # Chấp nhận - có thể là từ không dấu
    
    return 'MISSPELL'  # Không match gì cả
```

### 3. Xử lý Gibberish (Random text)

Từ dataset, tôi thấy có tin nhắn dạng:
```
"tORKiM! ay:Ma""n;N,ha7lXklq,uoacx.tech*;G^ja*nh$ap!"
```

**Đề xuất thêm Gibberish Detector:**

```python
def is_gibberish(token):
    """
    Phát hiện token gibberish dựa trên:
    1. Tỷ lệ ký tự đặc biệt cao
    2. Pattern không tự nhiên (consonant clusters bất thường)
    3. Độ dài bất thường
    """
    special_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', token)) / max(len(token), 1)
    if special_ratio > 0.3:
        return True
    
    # Vietnamese không có 3+ consonants liên tiếp
    if re.search(r'[bcdfghjklmnpqrstvwxz]{4,}', token.lower()):
        return True
    
    return False
```

---

## 📋 Tóm Tắt Đề Xuất

| Kiến trúc gốc | Đề xuất điều chỉnh |
|---------------|-------------------|
| 4 tầng | **5 tầng** (thêm Leetspeak riêng) |
| Dual-Lookup binary | **Tri-state validation** (Full/Shadow/Misspell) |
| Không có gibberish | **Thêm gibberish detector** |
| Tokenize trước | **Leet decode → Tokenize** |

**Output features đề xuất:**
- `misspelled_count` / `misspelled_pct`
- `leet_count` / `leet_pct` 
- `gibberish_count`
- `entity_counts` (dictionary với từng loại entity)

---

Bạn muốn tôi giải thích chi tiết hơn phần nào hoặc cung cấp pseudo-code/skeleton cho module cụ thể không?

```python
# Patterns cần "hung hăng" cho smishing Việt Nam
PATTERNS = {
    '<URL>': r'(?:https?://|www\.|bit\.ly|[a-z0-9-]+\s*\.\s*(?:com|vn|top|xyz|icu|vip|cc|life|club|cfd))',
    '<PHONE>': r'(?:\+?84|0)\s*\d[\d\s\.\-]{7,12}',
    '<CODE>': r'\b[A-Z0-9]{3,}[A-Z][0-9]+|[0-9]+[A-Z]{2,}\b',  # ST5K, OTP123
    '<MONEY>': r'\d{1,3}(?:[.,]\d{3})*\s*(?:k|tr|triệu|trieu|VND|VNĐ|dong|đồng|d)\b',
    '<ZALO>': r'zalo\.me/\d+|zalo:\s*\d+',
}
```

```plaintext
Luồng đề xuất:
Raw Text → Leet Decode → Unicode NFC → Word Tokenization
```

```plaintext
┌─────────────────────────────────────────────────────────────┐
│ INPUT: Raw SMS Text                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 1: AGGRESSIVE MASKING                                  │
│ ─────────────────────────────────────────────────────────── │
│ • Regex bắt URL, Phone, Money, Code, Date/Time              │
│ • Output: Text với <ENTITY> tokens                          │
│ • Bonus: Đếm số entity → Feature cho ML                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 2: LEETSPEAK DETECTION & DECODE  ← [MỚI]              │
│ ─────────────────────────────────────────────────────────── │
│ • Detect patterns: 0→o, 1→i, !→i, 3→e, @→a, $→s            │
│ • Output 1: leet_count (số ký tự bị thay)                   │
│ • Output 2: Decoded text (cho các tầng sau)                 │
│ • QUAN TRỌNG: Giữ lại bản gốc để đếm leet riêng            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 3: TOKENIZATION + NORMALIZATION                        │
│ ─────────────────────────────────────────────────────────── │
│ • Unicode NFC normalization                                 │
│ • pyvi/underthesea word segmentation                        │
│ • Xử lý từ dính: "ngày/đêm" → "ngày / đêm"                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 4: WHITELIST FILTERING                                 │
│ ─────────────────────────────────────────────────────────── │
│ • Brand names (ngân hàng, ví, telco, ecommerce)            │
│ • Technical jargon (otp, data, voucher)                     │
│ • Common abbreviations & teencode                           │
│ • Entity tokens (<URL>, <PHONE>, etc.)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ TẦNG 5: VIETNAMESE VALIDATION + ACCENT RESTORATION          │
│ ─────────────────────────────────────────────────────────── │
│ STRATEGY A (Fast - Rule-based):                             │
│   • Check Vietnamese_Shadow_Dict (no-accent)                │
│   • Từ "có thể có dấu" → VALID                              │
│   • Từ không match → MISSPELL                               │
│                                                             │
│ STRATEGY B (Accurate - Hybrid):                             │
│   • Dùng XLM-RoBERTa restore accent trước                   │
│   • Check Full_Dict với từ đã có dấu                        │
│   • So sánh original vs restored → Detect intentional       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT FEATURES:                                            │
│ • misspelled_count, misspelled_pct                          │
│ • leet_count, leet_pct                                      │
│ • unknown_token_count (gibberish)                           │
│ • entity_counts (url, phone, money, code)                   │
└─────────────────────────────────────────────────────────────┘
```

```python
LEET_MAP = {
    '0': 'o', '1': 'i', '!': 'i', '3': 'e', 
    '4': 'a', '@': 'a', '$': 's', '5': 's',
    '7': 't', '8': 'b', '9': 'g'
}

def decode_leet(text):
    leet_count = 0
    result = []
    for char in text:
        if char in LEET_MAP:
            result.append(LEET_MAP[char])
            leet_count += 1
        else:
            result.append(char)
    return ''.join(result), leet_count
```

```plaintext
"an" (không dấu) → có thể là: ăn, án, àn, ản, ãn, ạn, an
```

```python
def build_shadow_dict(full_dict):
    """
    Tạo shadow dict: no_accent_form → set of possible accented forms
    """
    shadow = defaultdict(set)
    for word in full_dict:
        no_accent = remove_accents(word.lower())
        shadow[no_accent].add(word)
    return shadow

def validate_word(word, full_dict, shadow_dict, whitelist):
    word_lower = word.lower()
    no_accent = remove_accents(word_lower)
    
    # Check 1: Whitelist (brands, jargon, abbr)
    if word_lower in whitelist:
        return 'VALID_WHITELIST'
    
    # Check 2: Full dict (có dấu)
    if word_lower in full_dict:
        return 'VALID_FULL'
    
    # Check 3: Shadow dict (không dấu nhưng CÓ THỂ hợp lệ)
    if no_accent in shadow_dict:
        return 'VALID_SHADOW'  # Chấp nhận - có thể là từ không dấu
    
    return 'MISSPELL'  # Không match gì cả
```

```plaintext
"tORKiM! ay:Ma""n;N,ha7lXklq,uoacx.tech*;G^ja*nh$ap!"
```

```python
def is_gibberish(token):
    """
    Phát hiện token gibberish dựa trên:
    1. Tỷ lệ ký tự đặc biệt cao
    2. Pattern không tự nhiên (consonant clusters bất thường)
    3. Độ dài bất thường
    """
    special_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', token)) / max(len(token), 1)
    if special_ratio > 0.3:
        return True
    
    # Vietnamese không có 3+ consonants liên tiếp
    if re.search(r'[bcdfghjklmnpqrstvwxz]{4,}', token.lower()):
        return True
    
    return False
```

---

**User**

Ở tầng 4, tôi đề xuất một quy trình kết hợp giữa cả 2 loại từ điển, kiểu đầu tiên sẽ kiểm tra qua từ điển có dấu, nếu không có thì sẽ kiểm tra từ điển không dấu. 

---

**Cursor**

Đúng vậy, quy trình **sequential check** (có dấu trước → không dấu sau) là hợp lý. Để tôi phân tích chi tiết cách tiếp cận này:

---

## 🔄 Quy Trình Dual-Lookup Đề Xuất

```
                    ┌─────────────┐
                    │   Token     │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ CHECK 1: Full Dict     │
              │ (Từ điển CÓ DẤU)       │
              └────────────┬───────────┘
                           │
                    ┌──────┴──────┐
                    │  Có trong   │
                    │  Full Dict? │
                    └──────┬──────┘
                     YES   │   NO
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        ┌───────────┐        ┌────────────────────────┐
        │  ✓ VALID  │        │ CHECK 2: Shadow Dict   │
        │  (Full)   │        │ (Từ điển KHÔNG DẤU)    │
        └───────────┘        └────────────┬───────────┘
                                          │
                                   ┌──────┴──────┐
                                   │  Có trong   │
                                   │ Shadow Dict?│
                                   └──────┬──────┘
                                    YES   │   NO
                             ┌────────────┴────────────┐
                             │                         │
                             ▼                         ▼
                       ┌───────────┐           ┌─────────────┐
                       │  ✓ VALID  │           │ ✗ MISSPELL  │
                       │ (Shadow)  │           │             │
                       └───────────┘           └─────────────┘
```

---

## 💡 Phân Tích Ưu/Nhược Điểm

### ✅ Ưu điểm

| Điểm | Giải thích |
|------|------------|
| **Chính xác với tin có dấu** | Tin nhắn chính thống (ngân hàng, telco thật) thường có dấu đầy đủ → match Full Dict ngay |
| **Linh hoạt với tin không dấu** | Tin spam viết không dấu vẫn được chấp nhận nếu là từ hợp lệ |
| **Hiệu suất tốt** | O(1) lookup cho cả 2 dict nếu dùng HashSet |
| **Logic rõ ràng** | Dễ debug, dễ maintain |

### ⚠️ Điểm cần lưu ý

**Vấn đề 1: Collision trong Shadow Dict**

```
Ví dụ: "an" (không dấu) có thể là:
├── ăn (to eat)
├── án (case/sentence)  
├── àn (?)
├── ản (?)
├── ãn (?)
├── ạn (?)
└── an (peace/safe) ← cũng hợp lệ!
```

**Giải pháp**: Với mục đích phát hiện lỗi chính tả, **collision không phải vấn đề lớn**:
- Nếu "an" map được đến BẤT KỲ từ có dấu hợp lệ nào → coi là VALID
- Mục tiêu là **loại bỏ từ hoàn toàn vô nghĩa**, không phải xác định nghĩa chính xác

---

**Vấn đề 2: Từ không dấu KHÔNG tồn tại dạng có dấu**

Một số từ vay mượn/thuật ngữ có thể chỉ tồn tại dạng không dấu:
- `wifi`, `internet`, `email`, `covid`...

**Giải pháp**: Đây là lý do cần **Whitelist (Tầng 3)** chạy trước Dual-Lookup

---

## 🛠️ Cách Xây Dựng 2 Từ Điển

### Full Dict (Có dấu)

```python
def build_full_dict(words_file_path):
    """
    Xây dựng từ điển có dấu từ file words.txt
    Format file: {"text": "từ", "source": [...]}
    """
    full_dict = set()
    
    with open(words_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                word = entry['text'].lower()
                full_dict.add(word)
                
                # Thêm cả dạng có gạch nối và không gạch nối
                # "ngân-hàng" → thêm cả "ngân hàng"
                if '-' in word:
                    full_dict.add(word.replace('-', ' '))
                    full_dict.add(word.replace('-', '_'))
                    
            except json.JSONDecodeError:
                continue
    
    return full_dict

# Kết quả: ~79,000+ từ có dấu
```

### Shadow Dict (Không dấu)

```python
import unicodedata
import re

def remove_vietnamese_accents(text):
    """
    Loại bỏ dấu tiếng Việt, giữ lại chữ cái gốc
    "ngân hàng" → "ngan hang"
    "điều kiện" → "dieu kien"
    """
    # Bảng chuyển đổi đặc biệt cho tiếng Việt
    ACCENT_MAP = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    }
    
    result = []
    for char in text.lower():
        result.append(ACCENT_MAP.get(char, char))
    
    return ''.join(result)


def build_shadow_dict(full_dict):
    """
    Tạo Shadow Dict từ Full Dict
    Mỗi dạng không dấu → set các dạng có dấu gốc (để debug nếu cần)
    """
    shadow_dict = set()
    
    for word in full_dict:
        no_accent = remove_vietnamese_accents(word)
        shadow_dict.add(no_accent)
    
    return shadow_dict

# Kết quả: ~50,000-60,000 từ không dấu (ít hơn do collision)
```

---

## 📝 Code Hoàn Chỉnh cho Dual-Lookup

```python
class DualLookupValidator:
    """
    Tầng 4: Dual-Lookup Validation
    Kiểm tra tính hợp lệ của từ tiếng Việt
    """
    
    def __init__(self, words_file_path):
        print("Loading Vietnamese dictionaries...")
        self.full_dict = self._build_full_dict(words_file_path)
        self.shadow_dict = self._build_shadow_dict(self.full_dict)
        print(f"✓ Full Dict: {len(self.full_dict):,} words")
        print(f"✓ Shadow Dict: {len(self.shadow_dict):,} words")
    
    def _build_full_dict(self, path):
        full_dict = set()
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    word = entry['text'].lower().strip()
                    if word:
                        full_dict.add(word)
                        # Xử lý biến thể
                        if '-' in word:
                            full_dict.add(word.replace('-', ' '))
                        if ' ' in word:
                            full_dict.add(word.replace(' ', '_'))
                except:
                    continue
        return full_dict
    
    def _build_shadow_dict(self, full_dict):
        shadow = set()
        for word in full_dict:
            no_accent = remove_vietnamese_accents(word)
            shadow.add(no_accent)
        return shadow
    
    def validate(self, token):
        """
        Kiểm tra token có hợp lệ không
        
        Returns:
            tuple: (is_valid: bool, match_type: str)
            match_type: 'full' | 'shadow' | 'misspell'
        """
        token_lower = token.lower().strip()
        
        # Bỏ qua token quá ngắn hoặc chỉ có số
        if len(token_lower) < 1 or token_lower.isdigit():
            return (True, 'skip')
        
        # CHECK 1: Từ điển có dấu
        if token_lower in self.full_dict:
            return (True, 'full')
        
        # CHECK 2: Từ điển không dấu
        token_no_accent = remove_vietnamese_accents(token_lower)
        if token_no_accent in self.shadow_dict:
            return (True, 'shadow')
        
        # Không match → Misspell
        return (False, 'misspell')
    
    def validate_tokens(self, tokens):
        """
        Kiểm tra danh sách tokens
        
        Returns:
            dict: {
                'misspelled_tokens': [...],
                'misspelled_count': int,
                'total_checked': int,
                'misspelled_pct': float
            }
        """
        misspelled = []
        total_checked = 0
        
        for token in tokens:
            is_valid, match_type = self.validate(token)
            
            if match_type == 'skip':
                continue
                
            total_checked += 1
            
            if not is_valid:
                misspelled.append(token)
        
        return {
            'misspelled_tokens': misspelled,
            'misspelled_count': len(misspelled),
            'total_checked': total_checked,
            'misspelled_pct': (len(misspelled) / total_checked * 100) if total_checked > 0 else 0
        }
```

---

## 🔗 Tích Hợp Với Các Tầng Khác

```python
def extract_spelling_features(text, masker, leet_decoder, tokenizer, whitelist, validator):
    """
    Pipeline hoàn chỉnh 4 tầng
    """
    # TẦNG 1: Aggressive Masking
    masked_text, entity_counts = masker.mask(text)
    
    # TẦNG 2: Leetspeak Decode (nếu tách riêng)
    decoded_text, leet_count = leet_decoder.decode(masked_text)
    
    # TẦNG 3: Tokenization
    tokens = tokenizer.tokenize(decoded_text)
    
    # TẦNG 3.5: Whitelist Filter
    tokens_to_check = [t for t in tokens if t.lower() not in whitelist]
    
    # TẦNG 4: Dual-Lookup Validation
    validation_result = validator.validate_tokens(tokens_to_check)
    
    return {
        'misspelled_count': validation_result['misspelled_count'],
        'misspelled_pct': validation_result['misspelled_pct'],
        'leet_count': leet_count,
        'leet_pct': (leet_count / len(text) * 100) if len(text) > 0 else 0,
        'total_tokens': len(tokens),
        'entity_counts': entity_counts,
        'misspelled_tokens': validation_result['misspelled_tokens']  # để debug
    }
```

---

## ✅ Kết Luận

Quy trình **Full Dict → Shadow Dict** là hợp lý và tôi **đồng ý** với đề xuất. Điểm mấu chốt:

| Bước | Mục đích |
|------|----------|
| Check Full Dict trước | Ưu tiên từ có dấu đúng (tin chính thống) |
| Check Shadow Dict sau | Chấp nhận từ không dấu nhưng có gốc hợp lệ |
| Fail cả 2 → Misspell | Từ hoàn toàn không có trong tiếng Việt |

Cách tiếp cận này **cân bằng** giữa độ chính xác và khả năng xử lý thực tế của dữ liệu SMS tiếng Việt (thường không có dấu).

```plaintext
                    ┌─────────────┐
                    │   Token     │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ CHECK 1: Full Dict     │
              │ (Từ điển CÓ DẤU)       │
              └────────────┬───────────┘
                           │
                    ┌──────┴──────┐
                    │  Có trong   │
                    │  Full Dict? │
                    └──────┬──────┘
                     YES   │   NO
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        ┌───────────┐        ┌────────────────────────┐
        │  ✓ VALID  │        │ CHECK 2: Shadow Dict   │
        │  (Full)   │        │ (Từ điển KHÔNG DẤU)    │
        └───────────┘        └────────────┬───────────┘
                                          │
                                   ┌──────┴──────┐
                                   │  Có trong   │
                                   │ Shadow Dict?│
                                   └──────┬──────┘
                                    YES   │   NO
                             ┌────────────┴────────────┐
                             │                         │
                             ▼                         ▼
                       ┌───────────┐           ┌─────────────┐
                       │  ✓ VALID  │           │ ✗ MISSPELL  │
                       │ (Shadow)  │           │             │
                       └───────────┘           └─────────────┘
```

```plaintext
Ví dụ: "an" (không dấu) có thể là:
├── ăn (to eat)
├── án (case/sentence)  
├── àn (?)
├── ản (?)
├── ãn (?)
├── ạn (?)
└── an (peace/safe) ← cũng hợp lệ!
```

```python
def build_full_dict(words_file_path):
    """
    Xây dựng từ điển có dấu từ file words.txt
    Format file: {"text": "từ", "source": [...]}
    """
    full_dict = set()
    
    with open(words_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                word = entry['text'].lower()
                full_dict.add(word)
                
                # Thêm cả dạng có gạch nối và không gạch nối
                # "ngân-hàng" → thêm cả "ngân hàng"
                if '-' in word:
                    full_dict.add(word.replace('-', ' '))
                    full_dict.add(word.replace('-', '_'))
                    
            except json.JSONDecodeError:
                continue
    
    return full_dict

# Kết quả: ~79,000+ từ có dấu
```

```python
import unicodedata
import re

def remove_vietnamese_accents(text):
    """
    Loại bỏ dấu tiếng Việt, giữ lại chữ cái gốc
    "ngân hàng" → "ngan hang"
    "điều kiện" → "dieu kien"
    """
    # Bảng chuyển đổi đặc biệt cho tiếng Việt
    ACCENT_MAP = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    }
    
    result = []
    for char in text.lower():
        result.append(ACCENT_MAP.get(char, char))
    
    return ''.join(result)


def build_shadow_dict(full_dict):
    """
    Tạo Shadow Dict từ Full Dict
    Mỗi dạng không dấu → set các dạng có dấu gốc (để debug nếu cần)
    """
    shadow_dict = set()
    
    for word in full_dict:
        no_accent = remove_vietnamese_accents(word)
        shadow_dict.add(no_accent)
    
    return shadow_dict

# Kết quả: ~50,000-60,000 từ không dấu (ít hơn do collision)
```

```python
class DualLookupValidator:
    """
    Tầng 4: Dual-Lookup Validation
    Kiểm tra tính hợp lệ của từ tiếng Việt
    """
    
    def __init__(self, words_file_path):
        print("Loading Vietnamese dictionaries...")
        self.full_dict = self._build_full_dict(words_file_path)
        self.shadow_dict = self._build_shadow_dict(self.full_dict)
        print(f"✓ Full Dict: {len(self.full_dict):,} words")
        print(f"✓ Shadow Dict: {len(self.shadow_dict):,} words")
    
    def _build_full_dict(self, path):
        full_dict = set()
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    word = entry['text'].lower().strip()
                    if word:
                        full_dict.add(word)
                        # Xử lý biến thể
                        if '-' in word:
                            full_dict.add(word.replace('-', ' '))
                        if ' ' in word:
                            full_dict.add(word.replace(' ', '_'))
                except:
                    continue
        return full_dict
    
    def _build_shadow_dict(self, full_dict):
        shadow = set()
        for word in full_dict:
            no_accent = remove_vietnamese_accents(word)
            shadow.add(no_accent)
        return shadow
    
    def validate(self, token):
        """
        Kiểm tra token có hợp lệ không
        
        Returns:
            tuple: (is_valid: bool, match_type: str)
            match_type: 'full' | 'shadow' | 'misspell'
        """
        token_lower = token.lower().strip()
        
        # Bỏ qua token quá ngắn hoặc chỉ có số
        if len(token_lower) < 1 or token_lower.isdigit():
            return (True, 'skip')
        
        # CHECK 1: Từ điển có dấu
        if token_lower in self.full_dict:
            return (True, 'full')
        
        # CHECK 2: Từ điển không dấu
        token_no_accent = remove_vietnamese_accents(token_lower)
        if token_no_accent in self.shadow_dict:
            return (True, 'shadow')
        
        # Không match → Misspell
        return (False, 'misspell')
    
    def validate_tokens(self, tokens):
        """
        Kiểm tra danh sách tokens
        
        Returns:
            dict: {
                'misspelled_tokens': [...],
                'misspelled_count': int,
                'total_checked': int,
                'misspelled_pct': float
            }
        """
        misspelled = []
        total_checked = 0
        
        for token in tokens:
            is_valid, match_type = self.validate(token)
            
            if match_type == 'skip':
                continue
                
            total_checked += 1
            
            if not is_valid:
                misspelled.append(token)
        
        return {
            'misspelled_tokens': misspelled,
            'misspelled_count': len(misspelled),
            'total_checked': total_checked,
            'misspelled_pct': (len(misspelled) / total_checked * 100) if total_checked > 0 else 0
        }
```

```python
def extract_spelling_features(text, masker, leet_decoder, tokenizer, whitelist, validator):
    """
    Pipeline hoàn chỉnh 4 tầng
    """
    # TẦNG 1: Aggressive Masking
    masked_text, entity_counts = masker.mask(text)
    
    # TẦNG 2: Leetspeak Decode (nếu tách riêng)
    decoded_text, leet_count = leet_decoder.decode(masked_text)
    
    # TẦNG 3: Tokenization
    tokens = tokenizer.tokenize(decoded_text)
    
    # TẦNG 3.5: Whitelist Filter
    tokens_to_check = [t for t in tokens if t.lower() not in whitelist]
    
    # TẦNG 4: Dual-Lookup Validation
    validation_result = validator.validate_tokens(tokens_to_check)
    
    return {
        'misspelled_count': validation_result['misspelled_count'],
        'misspelled_pct': validation_result['misspelled_pct'],
        'leet_count': leet_count,
        'leet_pct': (leet_count / len(text) * 100) if len(text) > 0 else 0,
        'total_tokens': len(tokens),
        'entity_counts': entity_counts,
        'misspelled_tokens': validation_result['misspelled_tokens']  # để debug
    }
```

---

**User**

Vậy hãy tổng kết lại từ tầng 1 cách chi tiết. Hết sức chi tiết để tôi có thể tiến hành thực hiện từng bước, không nhập nhằng giữa các phần, rành mạch rõ ràng. 

---

**Cursor**

# 📋 KIẾN TRÚC PHÂN TẦNG XỬ LÝ LỖI CHÍNH TẢ - TỔNG KẾT CHI TIẾT

---

## 🏗️ TỔNG QUAN KIẾN TRÚC

```
┌────────────────────────────────────────────────────────────────────┐
│                         RAW SMS TEXT                                │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 1: AGGRESSIVE MASKING                                        │
│  Che giấu thực thể phi ngôn ngữ bằng Regex                         │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 2: NORMALIZATION & TOKENIZATION                              │
│  Chuẩn hóa Unicode + Tách từ tiếng Việt                            │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 3: WHITELIST FILTERING                                       │
│  Lọc bỏ các từ ngoại lệ hợp lệ                                     │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 4: DUAL-LOOKUP VALIDATION                                    │
│  Kiểm tra từ điển Có dấu → Không dấu                               │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                      OUTPUT FEATURES                                │
└────────────────────────────────────────────────────────────────────┘
```

---

---

# TẦNG 1: AGGRESSIVE MASKING

---

## 1.1. Mục Tiêu

Tìm và **thay thế** các thực thể phi ngôn ngữ bằng token placeholder để:
- Không bị đếm nhầm là "lỗi chính tả"
- Chuẩn hóa dữ liệu trước khi xử lý ngôn ngữ
- Đếm số lượng từng loại thực thể (feature phụ cho ML)

---

## 1.2. Input / Output

| | Mô tả |
|---|---|
| **Input** | Chuỗi văn bản SMS gốc |
| **Output 1** | Chuỗi văn bản đã được mask (thay thực thể bằng token) |
| **Output 2** | Dictionary đếm số lượng từng loại thực thể |

**Ví dụ:**
```
Input:  "Dang nhap https://acb.vn-fake.com de nhan 500.000VND. LH: 0901234567"
Output: "Dang nhap <URL> de nhan <MONEY>. LH: <PHONE>"
Counts: {'url': 1, 'money': 1, 'phone': 1, 'code': 0, 'datetime': 0}
```

---

## 1.3. Các Loại Thực Thể Cần Mask

| Token | Mô tả | Ví dụ cần bắt |
|-------|-------|---------------|
| `<URL>` | Đường dẫn web, domain | `https://...`, `www.`, `bit.ly/xxx`, `acb.vn-fake.com`, `abc . com` |
| `<PHONE>` | Số điện thoại VN | `0901234567`, `84901234567`, `0901.234.567`, `+84 901 234 567` |
| `<MONEY>` | Số tiền | `500k`, `500.000đ`, `2.000.000VND`, `5 trieu`, `100 ngàn` |
| `<CODE>` | Mã code/OTP | `OTP123`, `ST5K`, `ABC123XYZ`, `V120N` |
| `<DATETIME>` | Ngày giờ | `15/05/2024`, `10h30`, `17:00`, `27/03` |
| `<ZALO>` | Link Zalo | `zalo.me/84xxx`, `Zalo: 0901234567` |
| `<EMAIL>` | Email | `abc@gmail.com` |

---

## 1.4. Regex Patterns Chi Tiết

```python
import re
from collections import OrderedDict

class AggressiveMasker:
    """
    Tầng 1: Aggressive Masking
    Thay thế các thực thể phi ngôn ngữ bằng token placeholder
    """
    
    def __init__(self):
        # OrderedDict để đảm bảo thứ tự xử lý (URL trước, sau đó mới đến các loại khác)
        self.patterns = OrderedDict([
            # 1. URL - Phải xử lý TRƯỚC TIÊN (aggressive)
            ('url', re.compile(
                r'('
                # Pattern 1: URL chuẩn với protocol
                r'(?:https?://)[^\s<>\"\']+'
                r'|'
                # Pattern 2: www
                r'(?:www\.)[^\s<>\"\']+'
                r'|'
                # Pattern 3: Shortener links
                r'(?:bit\.ly|tinyurl\.com|goo\.gl|t\.me|zalo\.me)/[^\s<>\"\']+'
                r'|'
                # Pattern 4: Domain có khoảng trắng cố ý (spammer trick)
                # Ví dụ: "acb . com", "vcb .vn"
                r'[a-zA-Z0-9][-a-zA-Z0-9]*\s*\.\s*(?:com|vn|net|org|top|xyz|icu|vip|cc|life|club|cfd|info|biz|site|online|tech|app|win|shop)(?:/[^\s]*)?'
                r'|'
                # Pattern 5: Domain không có protocol nhưng có path
                r'[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|vn|net|org|top|xyz|icu|vip|cc|life|club|cfd)/[^\s<>\"\']+'
                r')',
                re.IGNORECASE
            )),
            
            # 2. ZALO - Link Zalo đặc biệt
            ('zalo', re.compile(
                r'('
                r'zalo\.me/\d+'
                r'|'
                r'zalo\s*[:\-]?\s*\d{9,12}'
                r')',
                re.IGNORECASE
            )),
            
            # 3. EMAIL
            ('email', re.compile(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                re.IGNORECASE
            )),
            
            # 4. PHONE - Số điện thoại Việt Nam
            ('phone', re.compile(
                r'('
                # Pattern 1: Bắt đầu bằng +84 hoặc 84
                r'(?:\+?84)\s*\d[\d\s\.\-]{8,12}'
                r'|'
                # Pattern 2: Bắt đầu bằng 0
                r'(?<!\d)0\d{2}[\s\.\-]?\d{3}[\s\.\-]?\d{3,4}(?!\d)'
                r'|'
                # Pattern 3: Số tổng đài 1800, 1900, 9xxx
                r'(?:1800|1900|19\d{2})\s*[\d\s\.\-]{4,8}'
                r'|'
                # Pattern 4: Đầu số ngắn (brandname SMS)
                r'(?<!\d)\d{4,6}(?!\d)'
                r')'
            )),
            
            # 5. MONEY - Số tiền
            ('money', re.compile(
                r'('
                # Pattern 1: Số + đơn vị (500k, 500K, 5tr, 5TR)
                r'\d{1,3}(?:[.,]\d{3})*\s*(?:k|K|tr|TR|trieu|triệu|Trieu|Triệu)\b'
                r'|'
                # Pattern 2: Số + VND/VNĐ/đ/d/dong/đồng
                r'\d{1,3}(?:[.,]\d{3})*\s*(?:VND|VNĐ|vnđ|vnd|đồng|dong|đ|d)\b'
                r'|'
                # Pattern 3: Số lớn có dấu chấm/phẩy (500.000, 1,000,000)
                r'\d{1,3}(?:[.,]\d{3}){1,4}(?!\d)'
                r'|'
                # Pattern 4: Số + ngàn/nghìn/triệu/tỷ
                r'\d+\s*(?:ngàn|nghìn|ngan|nghin|triệu|trieu|tỷ|ty)\b'
                r')',
                re.IGNORECASE
            )),
            
            # 6. DATETIME - Ngày tháng, giờ
            ('datetime', re.compile(
                r'('
                # Pattern 1: Ngày tháng DD/MM hoặc DD/MM/YYYY
                r'\d{1,2}[/\-\.]\d{1,2}(?:[/\-\.]\d{2,4})?'
                r'|'
                # Pattern 2: Giờ phút HH:MM hoặc HHhMM hoặc HH giờ
                r'\d{1,2}\s*[hgG:]\s*\d{0,2}(?:\s*(?:phút|phut|p))?' 
                r'|'
                # Pattern 3: Giờ + AM/PM
                r'\d{1,2}\s*(?:am|pm|AM|PM)'
                r')'
            )),
            
            # 7. CODE - Mã OTP, mã giao dịch, mã khuyến mãi
            ('code', re.compile(
                r'('
                # Pattern 1: Chữ in hoa + số (OTP123, ABC123)
                r'\b[A-Z]{2,}[0-9]+[A-Z0-9]*\b'
                r'|'
                # Pattern 2: Số + chữ in hoa (123ABC, 5K50)
                r'\b[0-9]+[A-Z]{2,}[A-Z0-9]*\b'
                r'|'
                # Pattern 3: Mã có dạng XXX-XXX hoặc XXX_XXX
                r'\b[A-Z0-9]{2,}[-_][A-Z0-9]{2,}\b'
                r')'
            )),
        ])
    
    def mask(self, text):
        """
        Thực hiện masking trên văn bản
        
        Args:
            text: Chuỗi văn bản gốc
            
        Returns:
            tuple: (masked_text, entity_counts)
        """
        if not isinstance(text, str) or not text.strip():
            return text, {name: 0 for name in self.patterns.keys()}
        
        masked_text = text
        entity_counts = {name: 0 for name in self.patterns.keys()}
        
        # Áp dụng từng pattern theo thứ tự
        for entity_name, pattern in self.patterns.items():
            # Đếm số match
            matches = pattern.findall(masked_text)
            entity_counts[entity_name] = len(matches)
            
            # Thay thế bằng token
            token = f'<{entity_name.upper()}>'
            masked_text = pattern.sub(token, masked_text)
        
        return masked_text, entity_counts
    
    def mask_batch(self, texts):
        """
        Mask một batch văn bản
        
        Args:
            texts: List các chuỗi văn bản
            
        Returns:
            tuple: (list of masked_texts, list of entity_counts)
        """
        results = [self.mask(text) for text in texts]
        masked_texts = [r[0] for r in results]
        entity_counts = [r[1] for r in results]
        return masked_texts, entity_counts
```

---

## 1.5. Test Cases cho Tầng 1

```python
def test_aggressive_masker():
    masker = AggressiveMasker()
    
    test_cases = [
        # Test URL
        (
            "Dang nhap https://acb.vn-fake.com ngay",
            "Dang nhap <URL> ngay",
            {'url': 1}
        ),
        (
            "Truy cap www.vietcombank . vip de nhan",
            "Truy cap <URL> de nhan",
            {'url': 1}
        ),
        (
            "Link: bit.ly/abc123 hoac tinyurl.com/xyz",
            "Link: <URL> hoac <URL>",
            {'url': 2}
        ),
        
        # Test Phone
        (
            "LH 0901234567 hoac 84 901 234 567",
            "LH <PHONE> hoac <PHONE>",
            {'phone': 2}
        ),
        (
            "Goi 1900 1234 de duoc ho tro",
            "Goi <PHONE> de duoc ho tro",
            {'phone': 1}
        ),
        
        # Test Money
        (
            "Nhan 500k hoac 500.000 VND",
            "Nhan <MONEY> hoac <MONEY>",
            {'money': 2}
        ),
        (
            "Thanh toan 2.000.000đ truoc 5 trieu",
            "Thanh toan <MONEY> truoc <MONEY>",
            {'money': 2}
        ),
        
        # Test Code
        (
            "Ma OTP: ABC123 hoac ST5K",
            "Ma OTP: <CODE> hoac <CODE>",
            {'code': 2}
        ),
        
        # Test DateTime
        (
            "Truoc 17h30 ngay 15/05/2024",
            "Truoc <DATETIME> ngay <DATETIME>",
            {'datetime': 2}
        ),
        
        # Test Combined
        (
            "ACB: Dang nhap https://acb-fake.com de nhan 500.000VND. LH: 0901234567",
            "ACB: Dang nhap <URL> de nhan <MONEY>. LH: <PHONE>",
            {'url': 1, 'money': 1, 'phone': 1}
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 1: AGGRESSIVE MASKING")
    print("=" * 60)
    
    for i, (input_text, expected_masked, expected_counts) in enumerate(test_cases):
        masked, counts = masker.mask(input_text)
        
        # Kiểm tra từng entity count
        passed = True
        for entity, expected_count in expected_counts.items():
            if counts.get(entity, 0) != expected_count:
                passed = False
                break
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\nTest {i+1}: {status}")
        print(f"  Input:    {input_text}")
        print(f"  Output:   {masked}")
        print(f"  Counts:   {counts}")

# Chạy test
# test_aggressive_masker()
```

---

## 1.6. File Structure cho Tầng 1

```
misspelled_detection/
├── __init__.py
├── layer1_masking.py          # Code Tầng 1
├── tests/
│   └── test_layer1.py         # Test cases
```

---

## 1.7. Checklist Hoàn Thành Tầng 1

- [ ] Tạo class `AggressiveMasker`
- [ ] Implement đủ 7 loại pattern (URL, ZALO, EMAIL, PHONE, MONEY, DATETIME, CODE)
- [ ] Test với các trường hợp edge case:
  - [ ] URL có khoảng trắng cố ý (`acb . com`)
  - [ ] Phone có dấu chấm/gạch (`0901.234.567`)
  - [ ] Money nhiều format (`500k`, `500.000đ`, `5 triệu`)
  - [ ] Văn bản không có thực thể
  - [ ] Văn bản rỗng/None
- [ ] Đảm bảo thứ tự xử lý đúng (URL trước)

---

---

# TẦNG 2: NORMALIZATION & TOKENIZATION

---

## 2.1. Mục Tiêu

1. **Chuẩn hóa Unicode**: Đưa văn bản về dạng NFC chuẩn
2. **Decode Leetspeak**: Chuyển đổi ký tự thay thế về dạng gốc (`0`→`o`, `!`→`i`)
3. **Tách từ (Tokenization)**: Chia câu thành các đơn vị từ có nghĩa

---

## 2.2. Input / Output

| | Mô tả |
|---|---|
| **Input** | Chuỗi văn bản đã mask từ Tầng 1 |
| **Output 1** | Danh sách tokens (từ đã tách) |
| **Output 2** | `leet_count` - Số ký tự leetspeak đã chuyển đổi |
| **Output 3** | Văn bản đã chuẩn hóa (để debug) |

**Ví dụ:**
```
Input:  "Kh0ng pha! ban dang nhap vu! l0ng xac nhan"
Output: 
  - tokens: ["không", "phải", "bạn", "đăng", "nhập", "vui", "lòng", "xác", "nhận"]
  - leet_count: 4  (0→o: 2 lần, !→i: 2 lần)
```

---

## 2.3. Sub-module 2A: Unicode Normalization

```python
import unicodedata

def normalize_unicode(text):
    """
    Chuẩn hóa Unicode về dạng NFC (Composed)
    
    Xử lý các trường hợp:
    - Ký tự tổ hợp (combining characters)
    - Các biến thể Unicode của cùng một ký tự
    - Khoảng trắng đặc biệt
    
    Args:
        text: Chuỗi văn bản gốc
        
    Returns:
        Chuỗi đã chuẩn hóa
    """
    if not isinstance(text, str):
        return text
    
    # Bước 1: Chuẩn hóa NFC
    text = unicodedata.normalize('NFC', text)
    
    # Bước 2: Thay thế các loại khoảng trắng đặc biệt bằng space thường
    # \u00A0 = Non-breaking space
    # \u2000-\u200B = Various Unicode spaces
    text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', text)
    
    # Bước 3: Loại bỏ zero-width characters
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    
    # Bước 4: Chuẩn hóa multiple spaces thành single space
    text = re.sub(r' +', ' ', text)
    
    return text.strip()
```

---

## 2.4. Sub-module 2B: Leetspeak Decoder

```python
class LeetSpeakDecoder:
    """
    Giải mã Leetspeak - chuyển đổi ký tự thay thế về dạng gốc
    
    Phổ biến trong SMS spam tiếng Việt:
    - 0 → o (kh0ng → không)
    - 1 → i (d1ch vu → dịch vụ)  
    - ! → i (d!eu k!en → điều kiện)
    - 3 → e (tr3n → trên)
    - 4 → a (kho4n → khoản)
    - @ → a (@n → ăn)
    - $ → s ($o → số)
    """
    
    def __init__(self):
        # Bảng chuyển đổi Leetspeak → Chữ cái
        # Chỉ định nghĩa các mapping phổ biến và ít gây nhầm lẫn
        self.leet_map = {
            '0': 'o',   # kh0ng → không
            '1': 'i',   # d1ch → dịch
            '!': 'i',   # d!eu → điều
            '3': 'e',   # tr3n → trên (ít phổ biến)
            '@': 'a',   # @n → ăn (ít phổ biến)
        }
        
        # Pattern để phát hiện leetspeak trong ngữ cảnh từ
        # Chỉ decode khi ký tự nằm trong một từ (có chữ cái xung quanh)
        self.leet_pattern = re.compile(
            r'(?<=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])'
            r'([0!13@])'
            r'(?=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])',
            re.IGNORECASE
        )
    
    def decode(self, text):
        """
        Giải mã leetspeak trong văn bản
        
        Args:
            text: Chuỗi văn bản
            
        Returns:
            tuple: (decoded_text, leet_count)
        """
        if not isinstance(text, str) or not text:
            return text, 0
        
        leet_count = 0
        result = []
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Kiểm tra xem có phải leetspeak không
            if char in self.leet_map:
                # Kiểm tra ngữ cảnh: có chữ cái trước VÀ sau không?
                has_letter_before = (i > 0 and self._is_vietnamese_letter(text[i-1]))
                has_letter_after = (i < len(text)-1 and self._is_vietnamese_letter(text[i+1]))
                
                if has_letter_before and has_letter_after:
                    # Đây là leetspeak → decode
                    result.append(self.leet_map[char])
                    leet_count += 1
                else:
                    # Không phải leetspeak (ví dụ: số đứng một mình)
                    result.append(char)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result), leet_count
    
    def _is_vietnamese_letter(self, char):
        """Kiểm tra ký tự có phải chữ cái tiếng Việt không"""
        vietnamese_chars = (
            'aàáảãạăằắẳẵặâầấẩẫậbcdđeèéẻẽẹêềếểễệfghiìíỉĩịjklmno'
            'òóỏõọôồốổỗộơờớởỡợpqrstuùúủũụưừứửữựvwxyỳýỷỹỵz'
        )
        return char.lower() in vietnamese_chars
    
    def get_leet_positions(self, text):
        """
        Trả về vị trí các ký tự leetspeak (để highlight/debug)
        
        Returns:
            list of tuples: [(position, original_char, decoded_char), ...]
        """
        positions = []
        for i, char in enumerate(text):
            if char in self.leet_map:
                has_letter_before = (i > 0 and self._is_vietnamese_letter(text[i-1]))
                has_letter_after = (i < len(text)-1 and self._is_vietnamese_letter(text[i+1]))
                
                if has_letter_before and has_letter_after:
                    positions.append((i, char, self.leet_map[char]))
        
        return positions
```

---

## 2.5. Sub-module 2C: Vietnamese Tokenizer

```python
# Cần cài đặt: pip install underthesea hoặc pip install pyvi

# Option 1: Sử dụng underthesea (recommended)
from underthesea import word_tokenize

# Option 2: Sử dụng pyvi
# from pyvi import ViTokenizer

class VietnameseTokenizer:
    """
    Tách từ tiếng Việt sử dụng underthesea/pyvi
    """
    
    def __init__(self, library='underthesea'):
        """
        Args:
            library: 'underthesea' hoặc 'pyvi'
        """
        self.library = library
        
        if library == 'underthesea':
            from underthesea import word_tokenize
            self._tokenize_func = word_tokenize
        elif library == 'pyvi':
            from pyvi import ViTokenizer
            self._tokenize_func = lambda x: ViTokenizer.tokenize(x).split()
        else:
            # Fallback: simple split
            self._tokenize_func = lambda x: x.split()
    
    def tokenize(self, text):
        """
        Tách từ tiếng Việt
        
        Args:
            text: Chuỗi văn bản
            
        Returns:
            list: Danh sách tokens
        """
        if not isinstance(text, str) or not text.strip():
            return []
        
        try:
            # Tách từ
            if self.library == 'underthesea':
                # underthesea trả về list
                tokens = self._tokenize_func(text)
            else:
                tokens = self._tokenize_func(text)
            
            # Chuẩn hóa tokens
            cleaned_tokens = []
            for token in tokens:
                # Loại bỏ token rỗng
                token = token.strip()
                if token:
                    # Giữ nguyên các token đặc biệt (<URL>, <PHONE>, etc.)
                    if token.startswith('<') and token.endswith('>'):
                        cleaned_tokens.append(token)
                    else:
                        # Xử lý từ ghép có underscore (ngân_hàng → ngân_hàng)
                        cleaned_tokens.append(token)
            
            return cleaned_tokens
            
        except Exception as e:
            # Fallback nếu lỗi
            return text.split()
    
    def tokenize_with_positions(self, text):
        """
        Tách từ và giữ vị trí
        
        Returns:
            list of tuples: [(token, start_pos, end_pos), ...]
        """
        tokens = self.tokenize(text)
        result = []
        current_pos = 0
        
        for token in tokens:
            # Tìm vị trí token trong text gốc
            start = text.find(token.replace('_', ' '), current_pos)
            if start == -1:
                start = text.find(token, current_pos)
            if start == -1:
                start = current_pos
            
            end = start + len(token.replace('_', ' '))
            result.append((token, start, end))
            current_pos = end
        
        return result
```

---

## 2.6. Tích Hợp Tầng 2 Hoàn Chỉnh

```python
class NormalizationTokenizer:
    """
    Tầng 2: Normalization & Tokenization
    Kết hợp Unicode normalization + Leetspeak decode + Word tokenization
    """
    
    def __init__(self, tokenizer_library='underthesea'):
        self.leet_decoder = LeetSpeakDecoder()
        self.tokenizer = VietnameseTokenizer(library=tokenizer_library)
    
    def process(self, text):
        """
        Xử lý văn bản qua Tầng 2
        
        Args:
            text: Chuỗi văn bản (đã qua Tầng 1 masking)
            
        Returns:
            dict: {
                'tokens': list of tokens,
                'leet_count': số ký tự leetspeak,
                'normalized_text': văn bản đã chuẩn hóa (debug)
            }
        """
        if not isinstance(text, str) or not text.strip():
            return {
                'tokens': [],
                'leet_count': 0,
                'normalized_text': text
            }
        
        # Bước 1: Unicode normalization
        normalized = normalize_unicode(text)
        
        # Bước 2: Leetspeak decode
        decoded, leet_count = self.leet_decoder.decode(normalized)
        
        # Bước 3: Word tokenization
        tokens = self.tokenizer.tokenize(decoded)
        
        return {
            'tokens': tokens,
            'leet_count': leet_count,
            'normalized_text': decoded
        }
```

---

## 2.7. Test Cases cho Tầng 2

```python
def test_layer2():
    processor = NormalizationTokenizer(tokenizer_library='underthesea')
    
    test_cases = [
        # Test Leetspeak
        (
            "Kh0ng pha! ban dang nhap",
            {'expected_leet': 2}  # 0→o, !→i
        ),
        (
            "D!eu k!en nh4n t!en",
            {'expected_leet': 4}  # 4 lần !→i, 4→a
        ),
        
        # Test Unicode normalization
        (
            "Ngân  hàng   ACB",  # Multiple spaces
            {'expected_tokens_contain': ['ngân', 'hàng', 'ACB']}
        ),
        
        # Test Tokenization với từ ghép
        (
            "Tai khoan ngan hang",
            {'expected_tokens_contain': ['tài_khoản', 'ngân_hàng']}  # hoặc ['tai', 'khoan', 'ngan', 'hang'] tùy tokenizer
        ),
        
        # Test giữ nguyên entity tokens
        (
            "Dang nhap <URL> de nhan <MONEY>",
            {'expected_tokens_contain': ['<URL>', '<MONEY>']}
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 2: NORMALIZATION & TOKENIZATION")
    print("=" * 60)
    
    for i, (input_text, expected) in enumerate(test_cases):
        result = processor.process(input_text)
        
        print(f"\nTest {i+1}:")
        print(f"  Input:      {input_text}")
        print(f"  Tokens:     {result['tokens']}")
        print(f"  Leet count: {result['leet_count']}")
        
        if 'expected_leet' in expected:
            status = "✓" if result['leet_count'] == expected['expected_leet'] else "✗"
            print(f"  Leet check: {status}")

# test_layer2()
```

---

## 2.8. Dependencies cho Tầng 2

```bash
# Cài đặt thư viện tách từ tiếng Việt
pip install underthesea

# Hoặc dùng pyvi (nhẹ hơn)
pip install pyvi
```

---

## 2.9. Checklist Hoàn Thành Tầng 2

- [ ] Implement `normalize_unicode()` 
- [ ] Implement class `LeetSpeakDecoder`
  - [ ] Test với các pattern: `0`, `!`, `1`, `3`, `@`
  - [ ] Đảm bảo không decode số đứng một mình
- [ ] Implement class `VietnameseTokenizer`
  - [ ] Cài đặt underthesea hoặc pyvi
  - [ ] Test tách từ ghép tiếng Việt
- [ ] Implement class tích hợp `NormalizationTokenizer`
- [ ] Test với văn bản có entity tokens (`<URL>`, `<PHONE>`)

---

---

# TẦNG 3: WHITELIST FILTERING

---

## 3.1. Mục Tiêu

Lọc bỏ các token **đặc thù** không có trong từ điển tiếng Việt nhưng **hợp lệ** trong ngữ cảnh SMS:
- Tên thương hiệu (brand names)
- Thuật ngữ chuyên ngành (jargon)
- Viết tắt, teencode phổ biến
- Entity tokens từ Tầng 1

---

## 3.2. Input / Output

| | Mô tả |
|---|---|
| **Input** | Danh sách tokens từ Tầng 2 |
| **Output** | Danh sách tokens cần kiểm tra chính tả (đã loại whitelist) |

**Ví dụ:**
```
Input tokens:  ["vcb", "thong", "bao", "tai", "khoan", "otp", "123456", "<URL>"]
After filter:  ["thong", "bao", "tai", "khoan"]
Filtered out:  ["vcb" (brand), "otp" (jargon), "123456" (number), "<URL>" (entity)]
```

---

## 3.3. Cấu Trúc Whitelist

```python
class WhitelistFilter:
    """
    Tầng 3: Whitelist Filtering
    Lọc bỏ các token hợp lệ không cần kiểm tra chính tả
    """
    
    def __init__(self, custom_whitelist_path=None):
        # Khởi tạo các danh sách whitelist
        self.brand_list = self._build_brand_list()
        self.jargon_list = self._build_jargon_list()
        self.slang_abbr_list = self._build_slang_abbr_list()
        self.entity_tokens = self._build_entity_tokens()
        
        # Gộp tất cả thành một set để tra cứu O(1)
        self.whitelist = set()
        self.whitelist.update(self.brand_list)
        self.whitelist.update(self.jargon_list)
        self.whitelist.update(self.slang_abbr_list)
        self.whitelist.update(self.entity_tokens)
        
        # Load custom whitelist nếu có
        if custom_whitelist_path:
            self._load_custom_whitelist(custom_whitelist_path)
        
        print(f"✓ Whitelist loaded: {len(self.whitelist)} items")
    
    def _build_brand_list(self):
        """Danh sách tên thương hiệu, ngân hàng, ví điện tử, telco, ecommerce"""
        return {
            # === NGÂN HÀNG ===
            'vcb', 'vietcombank', 'acb', 'bidv', 'vietinbank', 'viettinbank',
            'techcombank', 'tcb', 'mbbank', 'mb', 'tpbank', 'vpbank',
            'sacombank', 'scb', 'shb', 'hdbank', 'ocb', 'msb',
            'seabank', 'abbank', 'vib', 'eximbank', 'namabank',
            'agribank', 'lienvietpostbank', 'pvcombank', 'bacabank',
            'vietabank', 'ncb', 'pgbank', 'baovietbank', 'cbbank',
            'gpbank', 'kienlongbank', 'vietbank', 'wooribank',
            'uob', 'hsbc', 'citibank', 'standardchartered', 'shinhan',
            'digibank', 'smartbanking', 'ebanking', 'ibanking', 'mbanking',
            
            # === VÍ ĐIỆN TỬ / FINTECH ===
            'momo', 'zalopay', 'viettelpay', 'vnpay', 'moca', 'airpay',
            'shoppeepay', 'grabpay', 'payoo', 'vtcpay', 'appotapay',
            'fecredit', 'homecredit', 'tpfinance', 'fegreenfinance',
            'mirae', 'credilo', 'tima', 'cash24', 'doctordong', 'robocash',
            
            # === VIỄN THÔNG ===
            'viettel', 'vinaphone', 'mobifone', 'vnmobile', 'gmobile',
            'vietnamobile', 'itel', 'reddi', 'wintel', 'indochina',
            
            # === THƯƠNG MẠI ĐIỆN TỬ ===
            'shopee', 'lazada', 'tiki', 'sendo', 'thegioididong', 'tgdd',
            'fptshop', 'cellphones', 'dienmayxanh', 'dmx', 'bachhoaxanh',
            'concung', 'guardian', 'watsons', 'lotte', 'aeon', 'bigc',
            'coopmart', 'vinmart', 'winmart', 'baemin', 'grabfood',
            'gojek', 'beamin', 'loship', 'ahamove', 'lalamove',
            'grab', 'be', 'gojek', 'xanh sm', 'mai linh', 'vinasun',
            
            # === MẠNG XÃ HỘI / APP ===
            'facebook', 'fb', 'zalo', 'telegram', 'viber', 'whatsapp',
            'tiktok', 'youtube', 'instagram', 'twitter', 'linkedin',
            'google', 'gmail', 'yahoo', 'outlook', 'icloud',
            
            # === THƯƠNG HIỆU KHÁC ===
            'apple', 'iphone', 'samsung', 'oppo', 'xiaomi', 'vivo',
            'huawei', 'realme', 'nokia', 'sony', 'lg', 'asus',
            'vingroup', 'vinfast', 'vinhomes', 'vincom', 'vinmec',
            'sungroup', 'novaland', 'fpt', 'vnpt', 'evn',
        }
    
    def _build_jargon_list(self):
        """Thuật ngữ chuyên ngành: viễn thông, tài chính, marketing, IT"""
        return {
            # === VIỄN THÔNG ===
            'sim', '4g', '5g', '3g', 'lte', 'data', 'wifi', 'internet',
            'roaming', 'sms', 'mms', 'ussd', 'gsm', 'cdma',
            'prepaid', 'postpaid', 'topup', 'nạp', 'goi', 'cuoc',
            
            # === TÀI CHÍNH ===
            'otp', 'pin', 'cvv', 'atm', 'pos', 'qr', 'nfc',
            'visa', 'mastercard', 'jcb', 'napas', 'swift', 'iban',
            'credit', 'debit', 'loan', 'mortgage', 'interest',
            'transfer', 'withdraw', 'deposit', 'balance',
            'transaction', 'payment', 'refund', 'cashback',
            
            # === MARKETING / KHUYẾN MÃI ===
            'voucher', 'coupon', 'deal', 'sale', 'flash', 'discount',
            'promo', 'promotion', 'km', 'khuyen', 'mai', 'freeship',
            'cod', 'ghn', 'ghtk', 'jt', 'ninja', 'best', 'viettel post',
            
            # === IT / KỸ THUẬT ===
            'app', 'web', 'link', 'url', 'click', 'download', 'update',
            'login', 'logout', 'signup', 'register', 'verify', 'confirm',
            'password', 'username', 'email', 'account', 'profile',
            'online', 'offline', 'server', 'system', 'database',
            'id', 'ip', 'api', 'sdk', 'ios', 'android', 'windows',
            
            # === ĐƠN VỊ / VIẾT TẮT ===
            'vnd', 'vnđ', 'usd', 'eur', 'btc', 'usdt', 'eth',
            'kg', 'km', 'cm', 'mm', 'm2', 'm3', 'gb', 'mb', 'kb',
            'tp', 'hcm', 'hn', 'dn', 'hp', 'ct', 'bd', 'bt',
            'bhxh', 'bhyt', 'bhtn', 'cmnd', 'cccd', 'gplx',
        }
    
    def _build_slang_abbr_list(self):
        """Viết tắt, teencode phổ biến trong SMS tiếng Việt"""
        return {
            # === VIẾT TẮT PHỔ BIẾN ===
            'lh', 'dt', 'sdt', 'đt', 'sđt',  # liên hệ, điện thoại
            'tk', 'stk',  # tài khoản, số tài khoản
            'qc', 'tb', 'tt',  # quảng cáo, thông báo, thanh toán
            'ck', 'hs', 'hd',  # chuyển khoản, hồ sơ, hợp đồng
            'kh', 'nv', 'ql',  # khách hàng, nhân viên, quản lý
            'cty', 'cong ty', 'cskh',  # công ty, chăm sóc khách hàng
            'pv', 'gd', 'kd',  # phục vụ, giao dịch, kinh doanh
            'nd', 'mgd', 'ref',  # nội dung, mã giao dịch, reference
            
            # === TEENCODE / SLANG ===
            'ko', 'k', 'khong',  # không
            'dc', 'đc', 'duoc',  # được
            'r', 'roi', 'rui',  # rồi
            'nha', 'nhe', 'nhé',  # nhé
            'a', 'e', 'em', 'anh', 'chi', 'chị',  # xưng hô
            'mk', 'mik', 'minh',  # mình
            'bn', 'bạn',  # bạn
            'ns', 'noi', 'nói',  # nói
            'nt', 'nhan', 'nhắn',  # nhắn tin
            'ib', 'inbox',  # inbox
            'ok', 'okie', 'oki', 'okê',
            'tks', 'thanks', 'thank', 'cam', 'on', 'ơn',
            'sr', 'sorry', 'xin', 'loi', 'lỗi',
            'pls', 'please', 'vui', 'long', 'lòng',
            'btw', 'fyi', 'asap', 'aka',
            
            # === CÁCH VIẾT KHÔNG DẤU PHỔ BIẾN ===
            'vui', 'long', 'vao', 'de', 'duoc', 'khong',
            'ngay', 'hom', 'nay', 'mai', 'qua',
            'tien', 'nhan', 'gui', 'chuyen',
        }
    
    def _build_entity_tokens(self):
        """Các token entity từ Tầng 1"""
        return {
            '<url>', '<phone>', '<money>', '<code>', 
            '<datetime>', '<zalo>', '<email>',
            # Thêm cả dạng viết hoa
            '<URL>', '<PHONE>', '<MONEY>', '<CODE>',
            '<DATETIME>', '<ZALO>', '<EMAIL>',
        }
    
    def _load_custom_whitelist(self, path):
        """Load whitelist tùy chỉnh từ file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().lower()
                    if word and not word.startswith('#'):
                        self.whitelist.add(word)
        except FileNotFoundError:
            print(f"Warning: Custom whitelist not found: {path}")
    
    def is_whitelisted(self, token):
        """
        Kiểm tra token có trong whitelist không
        
        Args:
            token: Một token đơn lẻ
            
        Returns:
            bool: True nếu token trong whitelist
        """
        token_lower = token.lower().strip()
        
        # Check 1: Trong whitelist set
        if token_lower in self.whitelist:
            return True
        
        # Check 2: Token là số thuần túy
        if token_lower.isdigit():
            return True
        
        # Check 3: Token là entity (bắt đầu và kết thúc bằng <>)
        if token.startswith('<') and token.endswith('>'):
            return True
        
        # Check 4: Token quá ngắn (1 ký tự) - thường là noise
        if len(token_lower) <= 1:
            return True
        
        # Check 5: Token chỉ chứa ký tự đặc biệt
        if not any(c.isalnum() for c in token):
            return True
        
        return False
    
    def filter(self, tokens):
        """
        Lọc danh sách tokens, trả về tokens cần kiểm tra chính tả
        
        Args:
            tokens: List các tokens từ Tầng 2
            
        Returns:
            dict: {
                'tokens_to_check': tokens cần kiểm tra,
                'whitelisted_tokens': tokens đã bị lọc,
                'whitelist_count': số tokens bị lọc
            }
        """
        tokens_to_check = []
        whitelisted_tokens = []
        
        for token in tokens:
            if self.is_whitelisted(token):
                whitelisted_tokens.append(token)
            else:
                tokens_to_check.append(token)
        
        return {
            'tokens_to_check': tokens_to_check,
            'whitelisted_tokens': whitelisted_tokens,
            'whitelist_count': len(whitelisted_tokens)
        }
```

---

## 3.4. File Whitelist Tùy Chỉnh (Optional)

Tạo file `custom_whitelist.txt` để thêm từ mới dễ dàng:

```text
# custom_whitelist.txt
# Thêm các từ đặc thù của dự án
# Mỗi từ một dòng, comment bắt đầu bằng #

# Tên riêng
huit
ueh
uit
hcmus

# Thuật ngữ mới
blockchain
nft
defi
metaverse

# Brand mới
cake
timo
tnex
```

---

## 3.5. Test Cases cho Tầng 3

```python
def test_whitelist_filter():
    whitelist = WhitelistFilter()
    
    test_cases = [
        # Test brand filtering
        (
            ["vcb", "thong", "bao", "tai", "khoan"],
            {"should_filter": ["vcb"], "should_keep": ["thong", "bao", "tai", "khoan"]}
        ),
        
        # Test jargon filtering
        (
            ["nhap", "otp", "de", "xac", "nhan"],
            {"should_filter": ["otp"], "should_keep": ["nhap", "de", "xac", "nhan"]}
        ),
        
        # Test entity filtering
        (
            ["dang", "nhap", "<URL>", "de", "nhan", "<MONEY>"],
            {"should_filter": ["<URL>", "<MONEY>"], "should_keep": ["dang", "nhap", "de", "nhan"]}
        ),
        
        # Test number filtering
        (
            ["ma", "123456", "het", "han", "24", "gio"],
            {"should_filter": ["123456", "24"], "should_keep": ["ma", "het", "han", "gio"]}
        ),
        
        # Test slang filtering
        (
            ["lh", "ngay", "de", "dc", "ho", "tro"],
            {"should_filter": ["lh", "dc"], "should_keep": ["ngay", "de", "ho", "tro"]}
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 3: WHITELIST FILTERING")
    print("=" * 60)
    
    for i, (tokens, expected) in enumerate(test_cases):
        result = whitelist.filter(tokens)
        
        print(f"\nTest {i+1}:")
        print(f"  Input tokens:      {tokens}")
        print(f"  Tokens to check:   {result['tokens_to_check']}")
        print(f"  Whitelisted:       {result['whitelisted_tokens']}")

# test_whitelist_filter()
```

---

## 3.6. Checklist Hoàn Thành Tầng 3

- [ ] Implement class `WhitelistFilter`
- [ ] Xây dựng `brand_list` (~100+ brands)
- [ ] Xây dựng `jargon_list` (~100+ thuật ngữ)
- [ ] Xây dựng `slang_abbr_list` (~50+ viết tắt)
- [ ] Implement logic `is_whitelisted()` với 5 checks
- [ ] Hỗ trợ custom whitelist từ file
- [ ] Test với các trường hợp edge case

---

---

# TẦNG 4: DUAL-LOOKUP VALIDATION

---

## 4.1. Mục Tiêu

Kiểm tra tính hợp lệ của từ tiếng Việt theo quy trình:
1. **Check 1**: Kiểm tra từ điển **CÓ DẤU** (Full Dict)
2. **Check 2**: Nếu không có → Kiểm tra từ điển **KHÔNG DẤU** (Shadow Dict)
3. **Kết quả**: Pass cả 2 check → `MISSPELL`

---

## 4.2. Input / Output

| | Mô tả |
|---|---|
| **Input** | Danh sách tokens đã qua Tầng 3 (cần kiểm tra) |
| **Output** | Dictionary chứa kết quả validation |

**Ví dụ:**
```
Input tokens: ["thong", "bao", "ta!", "khoan", "xyz123abc"]

Validation:
- "thong" → Shadow Dict có "thông" → VALID
- "bao"   → Shadow Dict có "báo", "bao" → VALID  
- "ta!"   → Không có trong cả 2 → MISSPELL
- "khoan" → Shadow Dict có "khoản" → VALID
- "xyz123abc" → Không có trong cả 2 → MISSPELL

Output: {
    'misspelled_tokens': ["ta!", "xyz123abc"],
    'misspelled_count': 2,
    'total_checked': 5,
    'misspelled_pct': 40.0
}
```

---

## 4.3. Xây Dựng Từ Điển

### 4.3.1. Hàm Loại Bỏ Dấu Tiếng Việt

```python
def remove_vietnamese_accents(text):
    """
    Loại bỏ dấu tiếng Việt, giữ lại chữ cái Latin gốc
    
    "ngân hàng" → "ngan hang"
    "điều kiện" → "dieu kien"
    "được"      → "duoc"
    """
    if not isinstance(text, str):
        return text
    
    # Bảng chuyển đổi đầy đủ cho tiếng Việt
    VIETNAMESE_ACCENT_MAP = {
        # a với dấu
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
        
        # đ
        'đ': 'd', 'Đ': 'D',
        
        # e với dấu
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
        
        # i với dấu
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
        
        # o với dấu
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
        
        # u với dấu
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
        
        # y với dấu
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
    }
    
    result = []
    for char in text:
        result.append(VIETNAMESE_ACCENT_MAP.get(char, char))
    
    return ''.join(result)
```

### 4.3.2. Class DualLookupValidator

```python
import json

class DualLookupValidator:
    """
    Tầng 4: Dual-Lookup Validation
    Kiểm tra từ điển Có dấu → Không dấu
    """
    
    def __init__(self, words_file_path):
        """
        Args:
            words_file_path: Đường dẫn đến file words.txt
                            Format: {"text": "từ", "source": [...]}
        """
        print("Loading Vietnamese dictionaries...")
        
        # Bước 1: Load và build Full Dict (có dấu)
        self.full_dict = self._build_full_dict(words_file_path)
        print(f"  ✓ Full Dict: {len(self.full_dict):,} words")
        
        # Bước 2: Build Shadow Dict (không dấu) từ Full Dict
        self.shadow_dict = self._build_shadow_dict()
        print(f"  ✓ Shadow Dict: {len(self.shadow_dict):,} words")
        
        print("✓ Dictionaries loaded successfully!")
    
    def _build_full_dict(self, path):
        """
        Xây dựng từ điển có dấu từ file words.txt
        """
        full_dict = set()
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON
                    entry = json.loads(line)
                    word = entry.get('text', '').strip()
                    
                    if word:
                        # Thêm dạng lowercase
                        full_dict.add(word.lower())
                        
                        # Xử lý từ ghép có gạch nối
                        # "ngân-hàng" → thêm cả "ngân hàng" và "ngân_hàng"
                        if '-' in word:
                            full_dict.add(word.lower().replace('-', ' '))
                            full_dict.add(word.lower().replace('-', '_'))
                        
                        # Xử lý từ ghép có khoảng trắng
                        # "ngân hàng" → thêm cả "ngân_hàng"
                        if ' ' in word:
                            full_dict.add(word.lower().replace(' ', '_'))
                            
                except json.JSONDecodeError:
                    # Nếu không phải JSON, thử đọc như plain text
                    word = line.strip()
                    if word:
                        full_dict.add(word.lower())
        
        return full_dict
    
    def _build_shadow_dict(self):
        """
        Xây dựng Shadow Dict (không dấu) từ Full Dict
        """
        shadow_dict = set()
        
        for word in self.full_dict:
            # Chuyển về dạng không dấu
            no_accent = remove_vietnamese_accents(word.lower())
            shadow_dict.add(no_accent)
        
        return shadow_dict
    
    def validate_token(self, token):
        """
        Kiểm tra một token
        
        Args:
            token: Một token đơn lẻ
            
        Returns:
            tuple: (is_valid, match_type)
                - is_valid: bool
                - match_type: 'full' | 'shadow' | 'misspell'
        """
        token_lower = token.lower().strip()
        
        # Bỏ qua token rỗng
        if not token_lower:
            return (True, 'skip')
        
        # CHECK 1: Từ điển có dấu (Full Dict)
        if token_lower in self.full_dict:
            return (True, 'full')
        
        # Xử lý từ ghép với underscore
        # "ngan_hang" → check cả "ngan hang"
        if '_' in token_lower:
            token_with_space = token_lower.replace('_', ' ')
            if token_with_space in self.full_dict:
                return (True, 'full')
        
        # CHECK 2: Từ điển không dấu (Shadow Dict)
        token_no_accent = remove_vietnamese_accents(token_lower)
        
        if token_no_accent in self.shadow_dict:
            return (True, 'shadow')
        
        # Xử lý từ ghép
        if '_' in token_no_accent:
            token_with_space = token_no_accent.replace('_', ' ')
            if token_with_space in self.shadow_dict:
                return (True, 'shadow')
        
        # KHÔNG match cả 2 → MISSPELL
        return (False, 'misspell')
    
    def validate_tokens(self, tokens):
        """
        Kiểm tra danh sách tokens
        
        Args:
            tokens: List các tokens cần kiểm tra
            
        Returns:
            dict: {
                'misspelled_tokens': list các từ sai chính tả,
                'misspelled_count': số từ sai,
                'valid_full_count': số từ match Full Dict,
                'valid_shadow_count': số từ match Shadow Dict,
                'total_checked': tổng số từ đã check,
                'misspelled_pct': % từ sai
            }
        """
        misspelled_tokens = []
        valid_full_count = 0
        valid_shadow_count = 0
        total_checked = 0
        
        for token in tokens:
            is_valid, match_type = self.validate_token(token)
            
            if match_type == 'skip':
                continue
            
            total_checked += 1
            
            if match_type == 'full':
                valid_full_count += 1
            elif match_type == 'shadow':
                valid_shadow_count += 1
            else:  # misspell
                misspelled_tokens.append(token)
        
        misspelled_count = len(misspelled_tokens)
        misspelled_pct = (misspelled_count / total_checked * 100) if total_checked > 0 else 0.0
        
        return {
            'misspelled_tokens': misspelled_tokens,
            'misspelled_count': misspelled_count,
            'valid_full_count': valid_full_count,
            'valid_shadow_count': valid_shadow_count,
            'total_checked': total_checked,
            'misspelled_pct': round(misspelled_pct, 2)
        }
```

---

## 4.4. Test Cases cho Tầng 4

```python
def test_dual_lookup():
    # Giả sử đã có file words.txt
    validator = DualLookupValidator('data/dicts/words.txt')
    
    test_cases = [
        # Test từ có dấu → match Full Dict
        (
            ["ngân", "hàng", "thông", "báo"],
            {'expected_full': 4, 'expected_misspell': 0}
        ),
        
        # Test từ không dấu → match Shadow Dict
        (
            ["ngan", "hang", "thong", "bao"],
            {'expected_shadow': 4, 'expected_misspell': 0}
        ),
        
        # Test từ sai chính tả
        (
            ["ngân", "hàng", "xyzabc", "abcdef"],
            {'expected_misspell': 2}
        ),
        
        # Test hỗn hợp
        (
            ["tai", "khoan", "abc123xyz", "da", "bi", "khoa"],
            {'expected_misspell': 1}  # chỉ "abc123xyz" sai
        ),
        
        # Test từ ghép
        (
            ["ngân_hàng", "tai_khoan"],
            {'expected_valid': 2}  # cả 2 đều hợp lệ
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 4: DUAL-LOOKUP VALIDATION")
    print("=" * 60)
    
    for i, (tokens, expected) in enumerate(test_cases):
        result = validator.validate_tokens(tokens)
        
        print(f"\nTest {i+1}:")
        print(f"  Input tokens:     {tokens}")
        print(f"  Misspelled:       {result['misspelled_tokens']}")
        print(f"  Full Dict match:  {result['valid_full_count']}")
        print(f"  Shadow Dict match:{result['valid_shadow_count']}")
        print(f"  Misspelled %:     {result['misspelled_pct']}%")

# test_dual_lookup()
```

---

## 4.5. Checklist Hoàn Thành Tầng 4

- [ ] Implement `remove_vietnamese_accents()` với đầy đủ bảng chuyển đổi
- [ ] Implement class `DualLookupValidator`
  - [ ] `_build_full_dict()` - load từ file words.txt
  - [ ] `_build_shadow_dict()` - tạo từ Full Dict
  - [ ] `validate_token()` - kiểm tra 1 token
  - [ ] `validate_tokens()` - kiểm tra batch
- [ ] Test với các trường hợp:
  - [ ] Từ có dấu
  - [ ] Từ không dấu  
  - [ ] Từ ghép (có `_` hoặc `-`)
  - [ ] Từ sai chính tả / gibberish
- [ ] Verify dict sizes (Full: ~79k, Shadow: ~50-60k)

---

---

# TÍCH HỢP TOÀN BỘ PIPELINE

---

## Pipeline Class Hoàn Chỉnh

```python
class MisspellingDetector:
    """
    Pipeline hoàn chỉnh phát hiện lỗi chính tả trong SMS tiếng Việt
    Kiến trúc 4 tầng:
        Tầng 1: Aggressive Masking
        Tầng 2: Normalization & Tokenization
        Tầng 3: Whitelist Filtering
        Tầng 4: Dual-Lookup Validation
    """
    
    def __init__(self, words_file_path, custom_whitelist_path=None):
        """
        Khởi tạo pipeline
        
        Args:
            words_file_path: Đường dẫn đến file từ điển tiếng Việt
            custom_whitelist_path: (Optional) Đường dẫn đến whitelist tùy chỉnh
        """
        print("=" * 60)
        print("INITIALIZING MISSPELLING DETECTOR")
        print("=" * 60)
        
        # Tầng 1
        print("\n[Layer 1] Loading Aggressive Masker...")
        self.masker = AggressiveMasker()
        
        # Tầng 2
        print("\n[Layer 2] Loading Normalizer & Tokenizer...")
        self.normalizer = NormalizationTokenizer(tokenizer_library='underthesea')
        
        # Tầng 3
        print("\n[Layer 3] Loading Whitelist Filter...")
        self.whitelist = WhitelistFilter(custom_whitelist_path)
        
        # Tầng 4
        print("\n[Layer 4] Loading Dual-Lookup Validator...")
        self.validator = DualLookupValidator(words_file_path)
        
        print("\n" + "=" * 60)
        print("✓ MISSPELLING DETECTOR READY!")
        print("=" * 60)
    
    def extract_features(self, text):
        """
        Trích xuất features lỗi chính tả từ văn bản
        
        Args:
            text: Chuỗi văn bản SMS
            
        Returns:
            dict: {
                # Từ Tầng 1
                'entity_counts': {...},
                
                # Từ Tầng 2
                'leet_count': int,
                'leet_pct': float,
                
                # Từ Tầng 4
                'misspelled_count': int,
                'misspelled_pct': float,
                'misspelled_tokens': [...],
                
                # Tổng hợp
                'total_tokens': int,
            }
        """
        if not isinstance(text, str) or not text.strip():
            return self._empty_result()
        
        # ===== TẦNG 1: AGGRESSIVE MASKING =====
        masked_text, entity_counts = self.masker.mask(text)
        
        # ===== TẦNG 2: NORMALIZATION & TOKENIZATION =====
        norm_result = self.normalizer.process(masked_text)
        tokens = norm_result['tokens']
        leet_count = norm_result['leet_count']
        
        # ===== TẦNG 3: WHITELIST FILTERING =====
        filter_result = self.whitelist.filter(tokens)
        tokens_to_check = filter_result['tokens_to_check']
        
        # ===== TẦNG 4: DUAL-LOOKUP VALIDATION =====
        validation_result = self.validator.validate_tokens(tokens_to_check)
        
        # ===== TỔNG HỢP KẾT QUẢ =====
        total_tokens = len(tokens)
        leet_pct = (leet_count / len(text) * 100) if len(text) > 0 else 0.0
        
        return {
            # Entity counts từ Tầng 1
            'entity_counts': entity_counts,
            'url_count': entity_counts.get('url', 0),
            'phone_count': entity_counts.get('phone', 0),
            'money_count': entity_counts.get('money', 0),
            'code_count': entity_counts.get('code', 0),
            
            # Leetspeak từ Tầng 2
            'leet_count': leet_count,
            'leet_pct': round(leet_pct, 2),
            
            # Whitelist từ Tầng 3
            'whitelist_count': filter_result['whitelist_count'],
            
            # Misspelling từ Tầng 4
            'misspelled_count': validation_result['misspelled_count'],
            'misspelled_pct': validation_result['misspelled_pct'],
            'misspelled_tokens': validation_result['misspelled_tokens'],
            
            # Tổng hợp
            'total_tokens': total_tokens,
            'tokens_checked': validation_result['total_checked'],
        }
    
    def _empty_result(self):
        """Trả về kết quả rỗng cho văn bản không hợp lệ"""
        return {
            'entity_counts': {},
            'url_count': 0,
            'phone_count': 0,
            'money_count': 0,
            'code_count': 0,
            'leet_count': 0,
            'leet_pct': 0.0,
            'whitelist_count': 0,
            'misspelled_count': 0,
            'misspelled_pct': 0.0,
            'misspelled_tokens': [],
            'total_tokens': 0,
            'tokens_checked': 0,
        }
    
    def process_dataframe(self, df, text_column='content'):
        """
        Xử lý toàn bộ DataFrame
        
        Args:
            df: pandas DataFrame
            text_column: Tên cột chứa văn bản
            
        Returns:
            DataFrame với các cột features mới
        """
        import pandas as pd
        from tqdm import tqdm
        
        print(f"\nProcessing {len(df)} records...")
        
        # Áp dụng cho từng dòng
        results = []
        for text in tqdm(df[text_column], desc="Extracting features"):
            results.append(self.extract_features(text))
        
        # Chuyển thành DataFrame
        features_df = pd.DataFrame(results)
        
        # Gộp với DataFrame gốc
        result_df = pd.concat([df.reset_index(drop=True), features_df], axis=1)
        
        print(f"✓ Processed {len(df)} records")
        
        return result_df
```

---

## Cách Sử Dụng

```python
# === KHỞI TẠO ===
detector = MisspellingDetector(
    words_file_path='data/dicts/words.txt',
    custom_whitelist_path='data/dicts/custom_whitelist.txt'  # optional
)

# === XỬ LÝ 1 TIN NHẮN ===
text = "Kh0ng pha! ban dang nhap https://fake-bank.com de nhan 500k. LH: 0901234567"
features = detector.extract_features(text)

print(f"Leet count: {features['leet_count']}")
print(f"Misspelled: {features['misspelled_tokens']}")
print(f"Misspelled %: {features['misspelled_pct']}%")

# === XỬ LÝ DATAFRAME ===
import pandas as pd

df = pd.read_csv('data/dataset.csv')
df_with_features = detector.process_dataframe(df, text_column='content')
df_with_features.to_csv('data/dataset_with_spelling_features.csv', index=False)
```

---

## File Structure Đề Xuất

```
misspelling_detection/
│
├── __init__.py
│
├── layer1_masking.py           # Tầng 1: AggressiveMasker
│
├── layer2_normalization.py     # Tầng 2: NormalizationTokenizer
│   ├── normalize_unicode()
│   ├── LeetSpeakDecoder
│   └── VietnameseTokenizer
│
├── layer3_whitelist.py         # Tầng 3: WhitelistFilter
│
├── layer4_validation.py        # Tầng 4: DualLookupValidator
│   ├── remove_vietnamese_accents()
│   └── DualLookupValidator
│
├── detector.py                 # Pipeline tích hợp: MisspellingDetector
│
├── utils.py                    # Các hàm tiện ích chung
│
└── tests/
    ├── test_layer1.py
    ├── test_layer2.py
    ├── test_layer3.py
    ├── test_layer4.py
    └── test_integration.py
```

---

## Checklist Tổng Thể

### Tầng 1: Aggressive Masking
- [ ] Class `AggressiveMasker`
- [ ] 7 loại patterns (URL, ZALO, EMAIL, PHONE, MONEY, DATETIME, CODE)
- [ ] Test cases

### Tầng 2: Normalization & Tokenization
- [ ] `normalize_unicode()`
- [ ] Class `LeetSpeakDecoder`
- [ ] Class `VietnameseTokenizer`
- [ ] Class tích hợp `NormalizationTokenizer`
- [ ] Test cases

### Tầng 3: Whitelist Filtering
- [ ] Class `WhitelistFilter`
- [ ] Brand list (~100+ items)
- [ ] Jargon list (~100+ items)
- [ ] Slang/Abbr list (~50+ items)
- [ ] Support custom whitelist file
- [ ] Test cases

### Tầng 4: Dual-Lookup Validation
- [ ] `remove_vietnamese_accents()`
- [ ] Class `DualLookupValidator`
- [ ] Build Full Dict từ words.txt
- [ ] Build Shadow Dict từ Full Dict
- [ ] Test cases

### Tích Hợp
- [ ] Class `MisspellingDetector`
- [ ] Method `extract_features()`
- [ ] Method `process_dataframe()`
- [ ] Integration tests

---

Đây là tài liệu chi tiết hoàn chỉnh để bạn có thể tiến hành **implement từng tầng một cách độc lập** và sau đó **tích hợp lại**. Mỗi tầng có Input/Output rõ ràng, code mẫu, test cases và checklist riêng.

```plaintext
┌────────────────────────────────────────────────────────────────────┐
│                         RAW SMS TEXT                                │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 1: AGGRESSIVE MASKING                                        │
│  Che giấu thực thể phi ngôn ngữ bằng Regex                         │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 2: NORMALIZATION & TOKENIZATION                              │
│  Chuẩn hóa Unicode + Tách từ tiếng Việt                            │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 3: WHITELIST FILTERING                                       │
│  Lọc bỏ các từ ngoại lệ hợp lệ                                     │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  TẦNG 4: DUAL-LOOKUP VALIDATION                                    │
│  Kiểm tra từ điển Có dấu → Không dấu                               │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                      OUTPUT FEATURES                                │
└────────────────────────────────────────────────────────────────────┘
```

```plaintext
Input:  "Dang nhap https://acb.vn-fake.com de nhan 500.000VND. LH: 0901234567"
Output: "Dang nhap <URL> de nhan <MONEY>. LH: <PHONE>"
Counts: {'url': 1, 'money': 1, 'phone': 1, 'code': 0, 'datetime': 0}
```

```python
import re
from collections import OrderedDict

class AggressiveMasker:
    """
    Tầng 1: Aggressive Masking
    Thay thế các thực thể phi ngôn ngữ bằng token placeholder
    """
    
    def __init__(self):
        # OrderedDict để đảm bảo thứ tự xử lý (URL trước, sau đó mới đến các loại khác)
        self.patterns = OrderedDict([
            # 1. URL - Phải xử lý TRƯỚC TIÊN (aggressive)
            ('url', re.compile(
                r'('
                # Pattern 1: URL chuẩn với protocol
                r'(?:https?://)[^\s<>\"\']+'
                r'|'
                # Pattern 2: www
                r'(?:www\.)[^\s<>\"\']+'
                r'|'
                # Pattern 3: Shortener links
                r'(?:bit\.ly|tinyurl\.com|goo\.gl|t\.me|zalo\.me)/[^\s<>\"\']+'
                r'|'
                # Pattern 4: Domain có khoảng trắng cố ý (spammer trick)
                # Ví dụ: "acb . com", "vcb .vn"
                r'[a-zA-Z0-9][-a-zA-Z0-9]*\s*\.\s*(?:com|vn|net|org|top|xyz|icu|vip|cc|life|club|cfd|info|biz|site|online|tech|app|win|shop)(?:/[^\s]*)?'
                r'|'
                # Pattern 5: Domain không có protocol nhưng có path
                r'[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|vn|net|org|top|xyz|icu|vip|cc|life|club|cfd)/[^\s<>\"\']+'
                r')',
                re.IGNORECASE
            )),
            
            # 2. ZALO - Link Zalo đặc biệt
            ('zalo', re.compile(
                r'('
                r'zalo\.me/\d+'
                r'|'
                r'zalo\s*[:\-]?\s*\d{9,12}'
                r')',
                re.IGNORECASE
            )),
            
            # 3. EMAIL
            ('email', re.compile(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                re.IGNORECASE
            )),
            
            # 4. PHONE - Số điện thoại Việt Nam
            ('phone', re.compile(
                r'('
                # Pattern 1: Bắt đầu bằng +84 hoặc 84
                r'(?:\+?84)\s*\d[\d\s\.\-]{8,12}'
                r'|'
                # Pattern 2: Bắt đầu bằng 0
                r'(?<!\d)0\d{2}[\s\.\-]?\d{3}[\s\.\-]?\d{3,4}(?!\d)'
                r'|'
                # Pattern 3: Số tổng đài 1800, 1900, 9xxx
                r'(?:1800|1900|19\d{2})\s*[\d\s\.\-]{4,8}'
                r'|'
                # Pattern 4: Đầu số ngắn (brandname SMS)
                r'(?<!\d)\d{4,6}(?!\d)'
                r')'
            )),
            
            # 5. MONEY - Số tiền
            ('money', re.compile(
                r'('
                # Pattern 1: Số + đơn vị (500k, 500K, 5tr, 5TR)
                r'\d{1,3}(?:[.,]\d{3})*\s*(?:k|K|tr|TR|trieu|triệu|Trieu|Triệu)\b'
                r'|'
                # Pattern 2: Số + VND/VNĐ/đ/d/dong/đồng
                r'\d{1,3}(?:[.,]\d{3})*\s*(?:VND|VNĐ|vnđ|vnd|đồng|dong|đ|d)\b'
                r'|'
                # Pattern 3: Số lớn có dấu chấm/phẩy (500.000, 1,000,000)
                r'\d{1,3}(?:[.,]\d{3}){1,4}(?!\d)'
                r'|'
                # Pattern 4: Số + ngàn/nghìn/triệu/tỷ
                r'\d+\s*(?:ngàn|nghìn|ngan|nghin|triệu|trieu|tỷ|ty)\b'
                r')',
                re.IGNORECASE
            )),
            
            # 6. DATETIME - Ngày tháng, giờ
            ('datetime', re.compile(
                r'('
                # Pattern 1: Ngày tháng DD/MM hoặc DD/MM/YYYY
                r'\d{1,2}[/\-\.]\d{1,2}(?:[/\-\.]\d{2,4})?'
                r'|'
                # Pattern 2: Giờ phút HH:MM hoặc HHhMM hoặc HH giờ
                r'\d{1,2}\s*[hgG:]\s*\d{0,2}(?:\s*(?:phút|phut|p))?' 
                r'|'
                # Pattern 3: Giờ + AM/PM
                r'\d{1,2}\s*(?:am|pm|AM|PM)'
                r')'
            )),
            
            # 7. CODE - Mã OTP, mã giao dịch, mã khuyến mãi
            ('code', re.compile(
                r'('
                # Pattern 1: Chữ in hoa + số (OTP123, ABC123)
                r'\b[A-Z]{2,}[0-9]+[A-Z0-9]*\b'
                r'|'
                # Pattern 2: Số + chữ in hoa (123ABC, 5K50)
                r'\b[0-9]+[A-Z]{2,}[A-Z0-9]*\b'
                r'|'
                # Pattern 3: Mã có dạng XXX-XXX hoặc XXX_XXX
                r'\b[A-Z0-9]{2,}[-_][A-Z0-9]{2,}\b'
                r')'
            )),
        ])
    
    def mask(self, text):
        """
        Thực hiện masking trên văn bản
        
        Args:
            text: Chuỗi văn bản gốc
            
        Returns:
            tuple: (masked_text, entity_counts)
        """
        if not isinstance(text, str) or not text.strip():
            return text, {name: 0 for name in self.patterns.keys()}
        
        masked_text = text
        entity_counts = {name: 0 for name in self.patterns.keys()}
        
        # Áp dụng từng pattern theo thứ tự
        for entity_name, pattern in self.patterns.items():
            # Đếm số match
            matches = pattern.findall(masked_text)
            entity_counts[entity_name] = len(matches)
            
            # Thay thế bằng token
            token = f'<{entity_name.upper()}>'
            masked_text = pattern.sub(token, masked_text)
        
        return masked_text, entity_counts
    
    def mask_batch(self, texts):
        """
        Mask một batch văn bản
        
        Args:
            texts: List các chuỗi văn bản
            
        Returns:
            tuple: (list of masked_texts, list of entity_counts)
        """
        results = [self.mask(text) for text in texts]
        masked_texts = [r[0] for r in results]
        entity_counts = [r[1] for r in results]
        return masked_texts, entity_counts
```

```python
def test_aggressive_masker():
    masker = AggressiveMasker()
    
    test_cases = [
        # Test URL
        (
            "Dang nhap https://acb.vn-fake.com ngay",
            "Dang nhap <URL> ngay",
            {'url': 1}
        ),
        (
            "Truy cap www.vietcombank . vip de nhan",
            "Truy cap <URL> de nhan",
            {'url': 1}
        ),
        (
            "Link: bit.ly/abc123 hoac tinyurl.com/xyz",
            "Link: <URL> hoac <URL>",
            {'url': 2}
        ),
        
        # Test Phone
        (
            "LH 0901234567 hoac 84 901 234 567",
            "LH <PHONE> hoac <PHONE>",
            {'phone': 2}
        ),
        (
            "Goi 1900 1234 de duoc ho tro",
            "Goi <PHONE> de duoc ho tro",
            {'phone': 1}
        ),
        
        # Test Money
        (
            "Nhan 500k hoac 500.000 VND",
            "Nhan <MONEY> hoac <MONEY>",
            {'money': 2}
        ),
        (
            "Thanh toan 2.000.000đ truoc 5 trieu",
            "Thanh toan <MONEY> truoc <MONEY>",
            {'money': 2}
        ),
        
        # Test Code
        (
            "Ma OTP: ABC123 hoac ST5K",
            "Ma OTP: <CODE> hoac <CODE>",
            {'code': 2}
        ),
        
        # Test DateTime
        (
            "Truoc 17h30 ngay 15/05/2024",
            "Truoc <DATETIME> ngay <DATETIME>",
            {'datetime': 2}
        ),
        
        # Test Combined
        (
            "ACB: Dang nhap https://acb-fake.com de nhan 500.000VND. LH: 0901234567",
            "ACB: Dang nhap <URL> de nhan <MONEY>. LH: <PHONE>",
            {'url': 1, 'money': 1, 'phone': 1}
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 1: AGGRESSIVE MASKING")
    print("=" * 60)
    
    for i, (input_text, expected_masked, expected_counts) in enumerate(test_cases):
        masked, counts = masker.mask(input_text)
        
        # Kiểm tra từng entity count
        passed = True
        for entity, expected_count in expected_counts.items():
            if counts.get(entity, 0) != expected_count:
                passed = False
                break
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\nTest {i+1}: {status}")
        print(f"  Input:    {input_text}")
        print(f"  Output:   {masked}")
        print(f"  Counts:   {counts}")

# Chạy test
# test_aggressive_masker()
```

```plaintext
misspelled_detection/
├── __init__.py
├── layer1_masking.py          # Code Tầng 1
├── tests/
│   └── test_layer1.py         # Test cases
```

```plaintext
Input:  "Kh0ng pha! ban dang nhap vu! l0ng xac nhan"
Output: 
  - tokens: ["không", "phải", "bạn", "đăng", "nhập", "vui", "lòng", "xác", "nhận"]
  - leet_count: 4  (0→o: 2 lần, !→i: 2 lần)
```

```python
import unicodedata

def normalize_unicode(text):
    """
    Chuẩn hóa Unicode về dạng NFC (Composed)
    
    Xử lý các trường hợp:
    - Ký tự tổ hợp (combining characters)
    - Các biến thể Unicode của cùng một ký tự
    - Khoảng trắng đặc biệt
    
    Args:
        text: Chuỗi văn bản gốc
        
    Returns:
        Chuỗi đã chuẩn hóa
    """
    if not isinstance(text, str):
        return text
    
    # Bước 1: Chuẩn hóa NFC
    text = unicodedata.normalize('NFC', text)
    
    # Bước 2: Thay thế các loại khoảng trắng đặc biệt bằng space thường
    # \u00A0 = Non-breaking space
    # \u2000-\u200B = Various Unicode spaces
    text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', text)
    
    # Bước 3: Loại bỏ zero-width characters
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    
    # Bước 4: Chuẩn hóa multiple spaces thành single space
    text = re.sub(r' +', ' ', text)
    
    return text.strip()
```

```python
class LeetSpeakDecoder:
    """
    Giải mã Leetspeak - chuyển đổi ký tự thay thế về dạng gốc
    
    Phổ biến trong SMS spam tiếng Việt:
    - 0 → o (kh0ng → không)
    - 1 → i (d1ch vu → dịch vụ)  
    - ! → i (d!eu k!en → điều kiện)
    - 3 → e (tr3n → trên)
    - 4 → a (kho4n → khoản)
    - @ → a (@n → ăn)
    - $ → s ($o → số)
    """
    
    def __init__(self):
        # Bảng chuyển đổi Leetspeak → Chữ cái
        # Chỉ định nghĩa các mapping phổ biến và ít gây nhầm lẫn
        self.leet_map = {
            '0': 'o',   # kh0ng → không
            '1': 'i',   # d1ch → dịch
            '!': 'i',   # d!eu → điều
            '3': 'e',   # tr3n → trên (ít phổ biến)
            '@': 'a',   # @n → ăn (ít phổ biến)
        }
        
        # Pattern để phát hiện leetspeak trong ngữ cảnh từ
        # Chỉ decode khi ký tự nằm trong một từ (có chữ cái xung quanh)
        self.leet_pattern = re.compile(
            r'(?<=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])'
            r'([0!13@])'
            r'(?=[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])',
            re.IGNORECASE
        )
    
    def decode(self, text):
        """
        Giải mã leetspeak trong văn bản
        
        Args:
            text: Chuỗi văn bản
            
        Returns:
            tuple: (decoded_text, leet_count)
        """
        if not isinstance(text, str) or not text:
            return text, 0
        
        leet_count = 0
        result = []
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Kiểm tra xem có phải leetspeak không
            if char in self.leet_map:
                # Kiểm tra ngữ cảnh: có chữ cái trước VÀ sau không?
                has_letter_before = (i > 0 and self._is_vietnamese_letter(text[i-1]))
                has_letter_after = (i < len(text)-1 and self._is_vietnamese_letter(text[i+1]))
                
                if has_letter_before and has_letter_after:
                    # Đây là leetspeak → decode
                    result.append(self.leet_map[char])
                    leet_count += 1
                else:
                    # Không phải leetspeak (ví dụ: số đứng một mình)
                    result.append(char)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result), leet_count
    
    def _is_vietnamese_letter(self, char):
        """Kiểm tra ký tự có phải chữ cái tiếng Việt không"""
        vietnamese_chars = (
            'aàáảãạăằắẳẵặâầấẩẫậbcdđeèéẻẽẹêềếểễệfghiìíỉĩịjklmno'
            'òóỏõọôồốổỗộơờớởỡợpqrstuùúủũụưừứửữựvwxyỳýỷỹỵz'
        )
        return char.lower() in vietnamese_chars
    
    def get_leet_positions(self, text):
        """
        Trả về vị trí các ký tự leetspeak (để highlight/debug)
        
        Returns:
            list of tuples: [(position, original_char, decoded_char), ...]
        """
        positions = []
        for i, char in enumerate(text):
            if char in self.leet_map:
                has_letter_before = (i > 0 and self._is_vietnamese_letter(text[i-1]))
                has_letter_after = (i < len(text)-1 and self._is_vietnamese_letter(text[i+1]))
                
                if has_letter_before and has_letter_after:
                    positions.append((i, char, self.leet_map[char]))
        
        return positions
```

```python
# Cần cài đặt: pip install underthesea hoặc pip install pyvi

# Option 1: Sử dụng underthesea (recommended)
from underthesea import word_tokenize

# Option 2: Sử dụng pyvi
# from pyvi import ViTokenizer

class VietnameseTokenizer:
    """
    Tách từ tiếng Việt sử dụng underthesea/pyvi
    """
    
    def __init__(self, library='underthesea'):
        """
        Args:
            library: 'underthesea' hoặc 'pyvi'
        """
        self.library = library
        
        if library == 'underthesea':
            from underthesea import word_tokenize
            self._tokenize_func = word_tokenize
        elif library == 'pyvi':
            from pyvi import ViTokenizer
            self._tokenize_func = lambda x: ViTokenizer.tokenize(x).split()
        else:
            # Fallback: simple split
            self._tokenize_func = lambda x: x.split()
    
    def tokenize(self, text):
        """
        Tách từ tiếng Việt
        
        Args:
            text: Chuỗi văn bản
            
        Returns:
            list: Danh sách tokens
        """
        if not isinstance(text, str) or not text.strip():
            return []
        
        try:
            # Tách từ
            if self.library == 'underthesea':
                # underthesea trả về list
                tokens = self._tokenize_func(text)
            else:
                tokens = self._tokenize_func(text)
            
            # Chuẩn hóa tokens
            cleaned_tokens = []
            for token in tokens:
                # Loại bỏ token rỗng
                token = token.strip()
                if token:
                    # Giữ nguyên các token đặc biệt (<URL>, <PHONE>, etc.)
                    if token.startswith('<') and token.endswith('>'):
                        cleaned_tokens.append(token)
                    else:
                        # Xử lý từ ghép có underscore (ngân_hàng → ngân_hàng)
                        cleaned_tokens.append(token)
            
            return cleaned_tokens
            
        except Exception as e:
            # Fallback nếu lỗi
            return text.split()
    
    def tokenize_with_positions(self, text):
        """
        Tách từ và giữ vị trí
        
        Returns:
            list of tuples: [(token, start_pos, end_pos), ...]
        """
        tokens = self.tokenize(text)
        result = []
        current_pos = 0
        
        for token in tokens:
            # Tìm vị trí token trong text gốc
            start = text.find(token.replace('_', ' '), current_pos)
            if start == -1:
                start = text.find(token, current_pos)
            if start == -1:
                start = current_pos
            
            end = start + len(token.replace('_', ' '))
            result.append((token, start, end))
            current_pos = end
        
        return result
```

```python
class NormalizationTokenizer:
    """
    Tầng 2: Normalization & Tokenization
    Kết hợp Unicode normalization + Leetspeak decode + Word tokenization
    """
    
    def __init__(self, tokenizer_library='underthesea'):
        self.leet_decoder = LeetSpeakDecoder()
        self.tokenizer = VietnameseTokenizer(library=tokenizer_library)
    
    def process(self, text):
        """
        Xử lý văn bản qua Tầng 2
        
        Args:
            text: Chuỗi văn bản (đã qua Tầng 1 masking)
            
        Returns:
            dict: {
                'tokens': list of tokens,
                'leet_count': số ký tự leetspeak,
                'normalized_text': văn bản đã chuẩn hóa (debug)
            }
        """
        if not isinstance(text, str) or not text.strip():
            return {
                'tokens': [],
                'leet_count': 0,
                'normalized_text': text
            }
        
        # Bước 1: Unicode normalization
        normalized = normalize_unicode(text)
        
        # Bước 2: Leetspeak decode
        decoded, leet_count = self.leet_decoder.decode(normalized)
        
        # Bước 3: Word tokenization
        tokens = self.tokenizer.tokenize(decoded)
        
        return {
            'tokens': tokens,
            'leet_count': leet_count,
            'normalized_text': decoded
        }
```

```python
def test_layer2():
    processor = NormalizationTokenizer(tokenizer_library='underthesea')
    
    test_cases = [
        # Test Leetspeak
        (
            "Kh0ng pha! ban dang nhap",
            {'expected_leet': 2}  # 0→o, !→i
        ),
        (
            "D!eu k!en nh4n t!en",
            {'expected_leet': 4}  # 4 lần !→i, 4→a
        ),
        
        # Test Unicode normalization
        (
            "Ngân  hàng   ACB",  # Multiple spaces
            {'expected_tokens_contain': ['ngân', 'hàng', 'ACB']}
        ),
        
        # Test Tokenization với từ ghép
        (
            "Tai khoan ngan hang",
            {'expected_tokens_contain': ['tài_khoản', 'ngân_hàng']}  # hoặc ['tai', 'khoan', 'ngan', 'hang'] tùy tokenizer
        ),
        
        # Test giữ nguyên entity tokens
        (
            "Dang nhap <URL> de nhan <MONEY>",
            {'expected_tokens_contain': ['<URL>', '<MONEY>']}
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 2: NORMALIZATION & TOKENIZATION")
    print("=" * 60)
    
    for i, (input_text, expected) in enumerate(test_cases):
        result = processor.process(input_text)
        
        print(f"\nTest {i+1}:")
        print(f"  Input:      {input_text}")
        print(f"  Tokens:     {result['tokens']}")
        print(f"  Leet count: {result['leet_count']}")
        
        if 'expected_leet' in expected:
            status = "✓" if result['leet_count'] == expected['expected_leet'] else "✗"
            print(f"  Leet check: {status}")

# test_layer2()
```

```shellscript
# Cài đặt thư viện tách từ tiếng Việt
pip install underthesea

# Hoặc dùng pyvi (nhẹ hơn)
pip install pyvi
```

```plaintext
Input tokens:  ["vcb", "thong", "bao", "tai", "khoan", "otp", "123456", "<URL>"]
After filter:  ["thong", "bao", "tai", "khoan"]
Filtered out:  ["vcb" (brand), "otp" (jargon), "123456" (number), "<URL>" (entity)]
```

```python
class WhitelistFilter:
    """
    Tầng 3: Whitelist Filtering
    Lọc bỏ các token hợp lệ không cần kiểm tra chính tả
    """
    
    def __init__(self, custom_whitelist_path=None):
        # Khởi tạo các danh sách whitelist
        self.brand_list = self._build_brand_list()
        self.jargon_list = self._build_jargon_list()
        self.slang_abbr_list = self._build_slang_abbr_list()
        self.entity_tokens = self._build_entity_tokens()
        
        # Gộp tất cả thành một set để tra cứu O(1)
        self.whitelist = set()
        self.whitelist.update(self.brand_list)
        self.whitelist.update(self.jargon_list)
        self.whitelist.update(self.slang_abbr_list)
        self.whitelist.update(self.entity_tokens)
        
        # Load custom whitelist nếu có
        if custom_whitelist_path:
            self._load_custom_whitelist(custom_whitelist_path)
        
        print(f"✓ Whitelist loaded: {len(self.whitelist)} items")
    
    def _build_brand_list(self):
        """Danh sách tên thương hiệu, ngân hàng, ví điện tử, telco, ecommerce"""
        return {
            # === NGÂN HÀNG ===
            'vcb', 'vietcombank', 'acb', 'bidv', 'vietinbank', 'viettinbank',
            'techcombank', 'tcb', 'mbbank', 'mb', 'tpbank', 'vpbank',
            'sacombank', 'scb', 'shb', 'hdbank', 'ocb', 'msb',
            'seabank', 'abbank', 'vib', 'eximbank', 'namabank',
            'agribank', 'lienvietpostbank', 'pvcombank', 'bacabank',
            'vietabank', 'ncb', 'pgbank', 'baovietbank', 'cbbank',
            'gpbank', 'kienlongbank', 'vietbank', 'wooribank',
            'uob', 'hsbc', 'citibank', 'standardchartered', 'shinhan',
            'digibank', 'smartbanking', 'ebanking', 'ibanking', 'mbanking',
            
            # === VÍ ĐIỆN TỬ / FINTECH ===
            'momo', 'zalopay', 'viettelpay', 'vnpay', 'moca', 'airpay',
            'shoppeepay', 'grabpay', 'payoo', 'vtcpay', 'appotapay',
            'fecredit', 'homecredit', 'tpfinance', 'fegreenfinance',
            'mirae', 'credilo', 'tima', 'cash24', 'doctordong', 'robocash',
            
            # === VIỄN THÔNG ===
            'viettel', 'vinaphone', 'mobifone', 'vnmobile', 'gmobile',
            'vietnamobile', 'itel', 'reddi', 'wintel', 'indochina',
            
            # === THƯƠNG MẠI ĐIỆN TỬ ===
            'shopee', 'lazada', 'tiki', 'sendo', 'thegioididong', 'tgdd',
            'fptshop', 'cellphones', 'dienmayxanh', 'dmx', 'bachhoaxanh',
            'concung', 'guardian', 'watsons', 'lotte', 'aeon', 'bigc',
            'coopmart', 'vinmart', 'winmart', 'baemin', 'grabfood',
            'gojek', 'beamin', 'loship', 'ahamove', 'lalamove',
            'grab', 'be', 'gojek', 'xanh sm', 'mai linh', 'vinasun',
            
            # === MẠNG XÃ HỘI / APP ===
            'facebook', 'fb', 'zalo', 'telegram', 'viber', 'whatsapp',
            'tiktok', 'youtube', 'instagram', 'twitter', 'linkedin',
            'google', 'gmail', 'yahoo', 'outlook', 'icloud',
            
            # === THƯƠNG HIỆU KHÁC ===
            'apple', 'iphone', 'samsung', 'oppo', 'xiaomi', 'vivo',
            'huawei', 'realme', 'nokia', 'sony', 'lg', 'asus',
            'vingroup', 'vinfast', 'vinhomes', 'vincom', 'vinmec',
            'sungroup', 'novaland', 'fpt', 'vnpt', 'evn',
        }
    
    def _build_jargon_list(self):
        """Thuật ngữ chuyên ngành: viễn thông, tài chính, marketing, IT"""
        return {
            # === VIỄN THÔNG ===
            'sim', '4g', '5g', '3g', 'lte', 'data', 'wifi', 'internet',
            'roaming', 'sms', 'mms', 'ussd', 'gsm', 'cdma',
            'prepaid', 'postpaid', 'topup', 'nạp', 'goi', 'cuoc',
            
            # === TÀI CHÍNH ===
            'otp', 'pin', 'cvv', 'atm', 'pos', 'qr', 'nfc',
            'visa', 'mastercard', 'jcb', 'napas', 'swift', 'iban',
            'credit', 'debit', 'loan', 'mortgage', 'interest',
            'transfer', 'withdraw', 'deposit', 'balance',
            'transaction', 'payment', 'refund', 'cashback',
            
            # === MARKETING / KHUYẾN MÃI ===
            'voucher', 'coupon', 'deal', 'sale', 'flash', 'discount',
            'promo', 'promotion', 'km', 'khuyen', 'mai', 'freeship',
            'cod', 'ghn', 'ghtk', 'jt', 'ninja', 'best', 'viettel post',
            
            # === IT / KỸ THUẬT ===
            'app', 'web', 'link', 'url', 'click', 'download', 'update',
            'login', 'logout', 'signup', 'register', 'verify', 'confirm',
            'password', 'username', 'email', 'account', 'profile',
            'online', 'offline', 'server', 'system', 'database',
            'id', 'ip', 'api', 'sdk', 'ios', 'android', 'windows',
            
            # === ĐƠN VỊ / VIẾT TẮT ===
            'vnd', 'vnđ', 'usd', 'eur', 'btc', 'usdt', 'eth',
            'kg', 'km', 'cm', 'mm', 'm2', 'm3', 'gb', 'mb', 'kb',
            'tp', 'hcm', 'hn', 'dn', 'hp', 'ct', 'bd', 'bt',
            'bhxh', 'bhyt', 'bhtn', 'cmnd', 'cccd', 'gplx',
        }
    
    def _build_slang_abbr_list(self):
        """Viết tắt, teencode phổ biến trong SMS tiếng Việt"""
        return {
            # === VIẾT TẮT PHỔ BIẾN ===
            'lh', 'dt', 'sdt', 'đt', 'sđt',  # liên hệ, điện thoại
            'tk', 'stk',  # tài khoản, số tài khoản
            'qc', 'tb', 'tt',  # quảng cáo, thông báo, thanh toán
            'ck', 'hs', 'hd',  # chuyển khoản, hồ sơ, hợp đồng
            'kh', 'nv', 'ql',  # khách hàng, nhân viên, quản lý
            'cty', 'cong ty', 'cskh',  # công ty, chăm sóc khách hàng
            'pv', 'gd', 'kd',  # phục vụ, giao dịch, kinh doanh
            'nd', 'mgd', 'ref',  # nội dung, mã giao dịch, reference
            
            # === TEENCODE / SLANG ===
            'ko', 'k', 'khong',  # không
            'dc', 'đc', 'duoc',  # được
            'r', 'roi', 'rui',  # rồi
            'nha', 'nhe', 'nhé',  # nhé
            'a', 'e', 'em', 'anh', 'chi', 'chị',  # xưng hô
            'mk', 'mik', 'minh',  # mình
            'bn', 'bạn',  # bạn
            'ns', 'noi', 'nói',  # nói
            'nt', 'nhan', 'nhắn',  # nhắn tin
            'ib', 'inbox',  # inbox
            'ok', 'okie', 'oki', 'okê',
            'tks', 'thanks', 'thank', 'cam', 'on', 'ơn',
            'sr', 'sorry', 'xin', 'loi', 'lỗi',
            'pls', 'please', 'vui', 'long', 'lòng',
            'btw', 'fyi', 'asap', 'aka',
            
            # === CÁCH VIẾT KHÔNG DẤU PHỔ BIẾN ===
            'vui', 'long', 'vao', 'de', 'duoc', 'khong',
            'ngay', 'hom', 'nay', 'mai', 'qua',
            'tien', 'nhan', 'gui', 'chuyen',
        }
    
    def _build_entity_tokens(self):
        """Các token entity từ Tầng 1"""
        return {
            '<url>', '<phone>', '<money>', '<code>', 
            '<datetime>', '<zalo>', '<email>',
            # Thêm cả dạng viết hoa
            '<URL>', '<PHONE>', '<MONEY>', '<CODE>',
            '<DATETIME>', '<ZALO>', '<EMAIL>',
        }
    
    def _load_custom_whitelist(self, path):
        """Load whitelist tùy chỉnh từ file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().lower()
                    if word and not word.startswith('#'):
                        self.whitelist.add(word)
        except FileNotFoundError:
            print(f"Warning: Custom whitelist not found: {path}")
    
    def is_whitelisted(self, token):
        """
        Kiểm tra token có trong whitelist không
        
        Args:
            token: Một token đơn lẻ
            
        Returns:
            bool: True nếu token trong whitelist
        """
        token_lower = token.lower().strip()
        
        # Check 1: Trong whitelist set
        if token_lower in self.whitelist:
            return True
        
        # Check 2: Token là số thuần túy
        if token_lower.isdigit():
            return True
        
        # Check 3: Token là entity (bắt đầu và kết thúc bằng <>)
        if token.startswith('<') and token.endswith('>'):
            return True
        
        # Check 4: Token quá ngắn (1 ký tự) - thường là noise
        if len(token_lower) <= 1:
            return True
        
        # Check 5: Token chỉ chứa ký tự đặc biệt
        if not any(c.isalnum() for c in token):
            return True
        
        return False
    
    def filter(self, tokens):
        """
        Lọc danh sách tokens, trả về tokens cần kiểm tra chính tả
        
        Args:
            tokens: List các tokens từ Tầng 2
            
        Returns:
            dict: {
                'tokens_to_check': tokens cần kiểm tra,
                'whitelisted_tokens': tokens đã bị lọc,
                'whitelist_count': số tokens bị lọc
            }
        """
        tokens_to_check = []
        whitelisted_tokens = []
        
        for token in tokens:
            if self.is_whitelisted(token):
                whitelisted_tokens.append(token)
            else:
                tokens_to_check.append(token)
        
        return {
            'tokens_to_check': tokens_to_check,
            'whitelisted_tokens': whitelisted_tokens,
            'whitelist_count': len(whitelisted_tokens)
        }
```

```plaintext
# custom_whitelist.txt
# Thêm các từ đặc thù của dự án
# Mỗi từ một dòng, comment bắt đầu bằng #

# Tên riêng
huit
ueh
uit
hcmus

# Thuật ngữ mới
blockchain
nft
defi
metaverse

# Brand mới
cake
timo
tnex
```

```python
def test_whitelist_filter():
    whitelist = WhitelistFilter()
    
    test_cases = [
        # Test brand filtering
        (
            ["vcb", "thong", "bao", "tai", "khoan"],
            {"should_filter": ["vcb"], "should_keep": ["thong", "bao", "tai", "khoan"]}
        ),
        
        # Test jargon filtering
        (
            ["nhap", "otp", "de", "xac", "nhan"],
            {"should_filter": ["otp"], "should_keep": ["nhap", "de", "xac", "nhan"]}
        ),
        
        # Test entity filtering
        (
            ["dang", "nhap", "<URL>", "de", "nhan", "<MONEY>"],
            {"should_filter": ["<URL>", "<MONEY>"], "should_keep": ["dang", "nhap", "de", "nhan"]}
        ),
        
        # Test number filtering
        (
            ["ma", "123456", "het", "han", "24", "gio"],
            {"should_filter": ["123456", "24"], "should_keep": ["ma", "het", "han", "gio"]}
        ),
        
        # Test slang filtering
        (
            ["lh", "ngay", "de", "dc", "ho", "tro"],
            {"should_filter": ["lh", "dc"], "should_keep": ["ngay", "de", "ho", "tro"]}
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 3: WHITELIST FILTERING")
    print("=" * 60)
    
    for i, (tokens, expected) in enumerate(test_cases):
        result = whitelist.filter(tokens)
        
        print(f"\nTest {i+1}:")
        print(f"  Input tokens:      {tokens}")
        print(f"  Tokens to check:   {result['tokens_to_check']}")
        print(f"  Whitelisted:       {result['whitelisted_tokens']}")

# test_whitelist_filter()
```

```plaintext
Input tokens: ["thong", "bao", "ta!", "khoan", "xyz123abc"]

Validation:
- "thong" → Shadow Dict có "thông" → VALID
- "bao"   → Shadow Dict có "báo", "bao" → VALID  
- "ta!"   → Không có trong cả 2 → MISSPELL
- "khoan" → Shadow Dict có "khoản" → VALID
- "xyz123abc" → Không có trong cả 2 → MISSPELL

Output: {
    'misspelled_tokens': ["ta!", "xyz123abc"],
    'misspelled_count': 2,
    'total_checked': 5,
    'misspelled_pct': 40.0
}
```

```python
def remove_vietnamese_accents(text):
    """
    Loại bỏ dấu tiếng Việt, giữ lại chữ cái Latin gốc
    
    "ngân hàng" → "ngan hang"
    "điều kiện" → "dieu kien"
    "được"      → "duoc"
    """
    if not isinstance(text, str):
        return text
    
    # Bảng chuyển đổi đầy đủ cho tiếng Việt
    VIETNAMESE_ACCENT_MAP = {
        # a với dấu
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
        'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
        'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
        
        # đ
        'đ': 'd', 'Đ': 'D',
        
        # e với dấu
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
        'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
        
        # i với dấu
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
        
        # o với dấu
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
        'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
        'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
        
        # u với dấu
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
        'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
        
        # y với dấu
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
    }
    
    result = []
    for char in text:
        result.append(VIETNAMESE_ACCENT_MAP.get(char, char))
    
    return ''.join(result)
```

```python
import json

class DualLookupValidator:
    """
    Tầng 4: Dual-Lookup Validation
    Kiểm tra từ điển Có dấu → Không dấu
    """
    
    def __init__(self, words_file_path):
        """
        Args:
            words_file_path: Đường dẫn đến file words.txt
                            Format: {"text": "từ", "source": [...]}
        """
        print("Loading Vietnamese dictionaries...")
        
        # Bước 1: Load và build Full Dict (có dấu)
        self.full_dict = self._build_full_dict(words_file_path)
        print(f"  ✓ Full Dict: {len(self.full_dict):,} words")
        
        # Bước 2: Build Shadow Dict (không dấu) từ Full Dict
        self.shadow_dict = self._build_shadow_dict()
        print(f"  ✓ Shadow Dict: {len(self.shadow_dict):,} words")
        
        print("✓ Dictionaries loaded successfully!")
    
    def _build_full_dict(self, path):
        """
        Xây dựng từ điển có dấu từ file words.txt
        """
        full_dict = set()
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON
                    entry = json.loads(line)
                    word = entry.get('text', '').strip()
                    
                    if word:
                        # Thêm dạng lowercase
                        full_dict.add(word.lower())
                        
                        # Xử lý từ ghép có gạch nối
                        # "ngân-hàng" → thêm cả "ngân hàng" và "ngân_hàng"
                        if '-' in word:
                            full_dict.add(word.lower().replace('-', ' '))
                            full_dict.add(word.lower().replace('-', '_'))
                        
                        # Xử lý từ ghép có khoảng trắng
                        # "ngân hàng" → thêm cả "ngân_hàng"
                        if ' ' in word:
                            full_dict.add(word.lower().replace(' ', '_'))
                            
                except json.JSONDecodeError:
                    # Nếu không phải JSON, thử đọc như plain text
                    word = line.strip()
                    if word:
                        full_dict.add(word.lower())
        
        return full_dict
    
    def _build_shadow_dict(self):
        """
        Xây dựng Shadow Dict (không dấu) từ Full Dict
        """
        shadow_dict = set()
        
        for word in self.full_dict:
            # Chuyển về dạng không dấu
            no_accent = remove_vietnamese_accents(word.lower())
            shadow_dict.add(no_accent)
        
        return shadow_dict
    
    def validate_token(self, token):
        """
        Kiểm tra một token
        
        Args:
            token: Một token đơn lẻ
            
        Returns:
            tuple: (is_valid, match_type)
                - is_valid: bool
                - match_type: 'full' | 'shadow' | 'misspell'
        """
        token_lower = token.lower().strip()
        
        # Bỏ qua token rỗng
        if not token_lower:
            return (True, 'skip')
        
        # CHECK 1: Từ điển có dấu (Full Dict)
        if token_lower in self.full_dict:
            return (True, 'full')
        
        # Xử lý từ ghép với underscore
        # "ngan_hang" → check cả "ngan hang"
        if '_' in token_lower:
            token_with_space = token_lower.replace('_', ' ')
            if token_with_space in self.full_dict:
                return (True, 'full')
        
        # CHECK 2: Từ điển không dấu (Shadow Dict)
        token_no_accent = remove_vietnamese_accents(token_lower)
        
        if token_no_accent in self.shadow_dict:
            return (True, 'shadow')
        
        # Xử lý từ ghép
        if '_' in token_no_accent:
            token_with_space = token_no_accent.replace('_', ' ')
            if token_with_space in self.shadow_dict:
                return (True, 'shadow')
        
        # KHÔNG match cả 2 → MISSPELL
        return (False, 'misspell')
    
    def validate_tokens(self, tokens):
        """
        Kiểm tra danh sách tokens
        
        Args:
            tokens: List các tokens cần kiểm tra
            
        Returns:
            dict: {
                'misspelled_tokens': list các từ sai chính tả,
                'misspelled_count': số từ sai,
                'valid_full_count': số từ match Full Dict,
                'valid_shadow_count': số từ match Shadow Dict,
                'total_checked': tổng số từ đã check,
                'misspelled_pct': % từ sai
            }
        """
        misspelled_tokens = []
        valid_full_count = 0
        valid_shadow_count = 0
        total_checked = 0
        
        for token in tokens:
            is_valid, match_type = self.validate_token(token)
            
            if match_type == 'skip':
                continue
            
            total_checked += 1
            
            if match_type == 'full':
                valid_full_count += 1
            elif match_type == 'shadow':
                valid_shadow_count += 1
            else:  # misspell
                misspelled_tokens.append(token)
        
        misspelled_count = len(misspelled_tokens)
        misspelled_pct = (misspelled_count / total_checked * 100) if total_checked > 0 else 0.0
        
        return {
            'misspelled_tokens': misspelled_tokens,
            'misspelled_count': misspelled_count,
            'valid_full_count': valid_full_count,
            'valid_shadow_count': valid_shadow_count,
            'total_checked': total_checked,
            'misspelled_pct': round(misspelled_pct, 2)
        }
```

```python
def test_dual_lookup():
    # Giả sử đã có file words.txt
    validator = DualLookupValidator('data/dicts/words.txt')
    
    test_cases = [
        # Test từ có dấu → match Full Dict
        (
            ["ngân", "hàng", "thông", "báo"],
            {'expected_full': 4, 'expected_misspell': 0}
        ),
        
        # Test từ không dấu → match Shadow Dict
        (
            ["ngan", "hang", "thong", "bao"],
            {'expected_shadow': 4, 'expected_misspell': 0}
        ),
        
        # Test từ sai chính tả
        (
            ["ngân", "hàng", "xyzabc", "abcdef"],
            {'expected_misspell': 2}
        ),
        
        # Test hỗn hợp
        (
            ["tai", "khoan", "abc123xyz", "da", "bi", "khoa"],
            {'expected_misspell': 1}  # chỉ "abc123xyz" sai
        ),
        
        # Test từ ghép
        (
            ["ngân_hàng", "tai_khoan"],
            {'expected_valid': 2}  # cả 2 đều hợp lệ
        ),
    ]
    
    print("=" * 60)
    print("TESTING TẦNG 4: DUAL-LOOKUP VALIDATION")
    print("=" * 60)
    
    for i, (tokens, expected) in enumerate(test_cases):
        result = validator.validate_tokens(tokens)
        
        print(f"\nTest {i+1}:")
        print(f"  Input tokens:     {tokens}")
        print(f"  Misspelled:       {result['misspelled_tokens']}")
        print(f"  Full Dict match:  {result['valid_full_count']}")
        print(f"  Shadow Dict match:{result['valid_shadow_count']}")
        print(f"  Misspelled %:     {result['misspelled_pct']}%")

# test_dual_lookup()
```

```python
class MisspellingDetector:
    """
    Pipeline hoàn chỉnh phát hiện lỗi chính tả trong SMS tiếng Việt
    Kiến trúc 4 tầng:
        Tầng 1: Aggressive Masking
        Tầng 2: Normalization & Tokenization
        Tầng 3: Whitelist Filtering
        Tầng 4: Dual-Lookup Validation
    """
    
    def __init__(self, words_file_path, custom_whitelist_path=None):
        """
        Khởi tạo pipeline
        
        Args:
            words_file_path: Đường dẫn đến file từ điển tiếng Việt
            custom_whitelist_path: (Optional) Đường dẫn đến whitelist tùy chỉnh
        """
        print("=" * 60)
        print("INITIALIZING MISSPELLING DETECTOR")
        print("=" * 60)
        
        # Tầng 1
        print("\n[Layer 1] Loading Aggressive Masker...")
        self.masker = AggressiveMasker()
        
        # Tầng 2
        print("\n[Layer 2] Loading Normalizer & Tokenizer...")
        self.normalizer = NormalizationTokenizer(tokenizer_library='underthesea')
        
        # Tầng 3
        print("\n[Layer 3] Loading Whitelist Filter...")
        self.whitelist = WhitelistFilter(custom_whitelist_path)
        
        # Tầng 4
        print("\n[Layer 4] Loading Dual-Lookup Validator...")
        self.validator = DualLookupValidator(words_file_path)
        
        print("\n" + "=" * 60)
        print("✓ MISSPELLING DETECTOR READY!")
        print("=" * 60)
    
    def extract_features(self, text):
        """
        Trích xuất features lỗi chính tả từ văn bản
        
        Args:
            text: Chuỗi văn bản SMS
            
        Returns:
            dict: {
                # Từ Tầng 1
                'entity_counts': {...},
                
                # Từ Tầng 2
                'leet_count': int,
                'leet_pct': float,
                
                # Từ Tầng 4
                'misspelled_count': int,
                'misspelled_pct': float,
                'misspelled_tokens': [...],
                
                # Tổng hợp
                'total_tokens': int,
            }
        """
        if not isinstance(text, str) or not text.strip():
            return self._empty_result()
        
        # ===== TẦNG 1: AGGRESSIVE MASKING =====
        masked_text, entity_counts = self.masker.mask(text)
        
        # ===== TẦNG 2: NORMALIZATION & TOKENIZATION =====
        norm_result = self.normalizer.process(masked_text)
        tokens = norm_result['tokens']
        leet_count = norm_result['leet_count']
        
        # ===== TẦNG 3: WHITELIST FILTERING =====
        filter_result = self.whitelist.filter(tokens)
        tokens_to_check = filter_result['tokens_to_check']
        
        # ===== TẦNG 4: DUAL-LOOKUP VALIDATION =====
        validation_result = self.validator.validate_tokens(tokens_to_check)
        
        # ===== TỔNG HỢP KẾT QUẢ =====
        total_tokens = len(tokens)
        leet_pct = (leet_count / len(text) * 100) if len(text) > 0 else 0.0
        
        return {
            # Entity counts từ Tầng 1
            'entity_counts': entity_counts,
            'url_count': entity_counts.get('url', 0),
            'phone_count': entity_counts.get('phone', 0),
            'money_count': entity_counts.get('money', 0),
            'code_count': entity_counts.get('code', 0),
            
            # Leetspeak từ Tầng 2
            'leet_count': leet_count,
            'leet_pct': round(leet_pct, 2),
            
            # Whitelist từ Tầng 3
            'whitelist_count': filter_result['whitelist_count'],
            
            # Misspelling từ Tầng 4
            'misspelled_count': validation_result['misspelled_count'],
            'misspelled_pct': validation_result['misspelled_pct'],
            'misspelled_tokens': validation_result['misspelled_tokens'],
            
            # Tổng hợp
            'total_tokens': total_tokens,
            'tokens_checked': validation_result['total_checked'],
        }
    
    def _empty_result(self):
        """Trả về kết quả rỗng cho văn bản không hợp lệ"""
        return {
            'entity_counts': {},
            'url_count': 0,
            'phone_count': 0,
            'money_count': 0,
            'code_count': 0,
            'leet_count': 0,
            'leet_pct': 0.0,
            'whitelist_count': 0,
            'misspelled_count': 0,
            'misspelled_pct': 0.0,
            'misspelled_tokens': [],
            'total_tokens': 0,
            'tokens_checked': 0,
        }
    
    def process_dataframe(self, df, text_column='content'):
        """
        Xử lý toàn bộ DataFrame
        
        Args:
            df: pandas DataFrame
            text_column: Tên cột chứa văn bản
            
        Returns:
            DataFrame với các cột features mới
        """
        import pandas as pd
        from tqdm import tqdm
        
        print(f"\nProcessing {len(df)} records...")
        
        # Áp dụng cho từng dòng
        results = []
        for text in tqdm(df[text_column], desc="Extracting features"):
            results.append(self.extract_features(text))
        
        # Chuyển thành DataFrame
        features_df = pd.DataFrame(results)
        
        # Gộp với DataFrame gốc
        result_df = pd.concat([df.reset_index(drop=True), features_df], axis=1)
        
        print(f"✓ Processed {len(df)} records")
        
        return result_df
```

```python
# === KHỞI TẠO ===
detector = MisspellingDetector(
    words_file_path='data/dicts/words.txt',
    custom_whitelist_path='data/dicts/custom_whitelist.txt'  # optional
)

# === XỬ LÝ 1 TIN NHẮN ===
text = "Kh0ng pha! ban dang nhap https://fake-bank.com de nhan 500k. LH: 0901234567"
features = detector.extract_features(text)

print(f"Leet count: {features['leet_count']}")
print(f"Misspelled: {features['misspelled_tokens']}")
print(f"Misspelled %: {features['misspelled_pct']}%")

# === XỬ LÝ DATAFRAME ===
import pandas as pd

df = pd.read_csv('data/dataset.csv')
df_with_features = detector.process_dataframe(df, text_column='content')
df_with_features.to_csv('data/dataset_with_spelling_features.csv', index=False)
```

```plaintext
misspelling_detection/
│
├── __init__.py
│
├── layer1_masking.py           # Tầng 1: AggressiveMasker
│
├── layer2_normalization.py     # Tầng 2: NormalizationTokenizer
│   ├── normalize_unicode()
│   ├── LeetSpeakDecoder
│   └── VietnameseTokenizer
│
├── layer3_whitelist.py         # Tầng 3: WhitelistFilter
│
├── layer4_validation.py        # Tầng 4: DualLookupValidator
│   ├── remove_vietnamese_accents()
│   └── DualLookupValidator
│
├── detector.py                 # Pipeline tích hợp: MisspellingDetector
│
├── utils.py                    # Các hàm tiện ích chung
│
└── tests/
    ├── test_layer1.py
    ├── test_layer2.py
    ├── test_layer3.py
    ├── test_layer4.py
    └── test_integration.py
```

