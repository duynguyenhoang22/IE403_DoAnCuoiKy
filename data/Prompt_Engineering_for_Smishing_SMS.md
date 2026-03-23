# Prompt Engineering for Smishing SMS Data Augmentation

> **Trạng thái tài liệu:** Đang cập nhật liên tục  
> **Phạm vi:** Label 1 – Tin nhắn lừa đảo (Smishing) tại Việt Nam  
> **Liên quan:** `gen_label_1.py` | `dataset_label_1.csv` | `synthetic_2000_smishing_v2.csv`

---

## Mục lục

1. [Prompt Engineering là gì?](#1-prompt-engineering-là-gì)
2. [Cơ chế hoạt động khi sinh Text Data](#2-cơ-chế-hoạt-động-khi-sinh-text-data)
3. [Tại sao Prompt Engineering quan trọng với Data Augmentation?](#3-tại-sao-prompt-engineering-quan-trọng-với-data-augmentation)
4. [Phân tích dữ liệu thực tế (Ground Truth)](#4-phân-tích-dữ-liệu-thực-tế-ground-truth)
5. [Khoảng cách giữa Synthetic và Real Data](#5-khoảng-cách-giữa-synthetic-và-real-data)
6. [Kỹ thuật Prompt Engineering hệ thống](#6-kỹ-thuật-prompt-engineering-hệ-thống)
7. [Thiết kế Prompt cho từng Category](#7-thiết-kế-prompt-cho-từng-category)
8. [Few-Shot Examples Library](#8-few-shot-examples-library)
9. [Checklist đánh giá chất lượng](#9-checklist-đánh-giá-chất-lượng)
10. [Roadmap cải tiến](#10-roadmap-cải-tiến)

---

## 1. Prompt Engineering là gì?

**Prompt Engineering** là quá trình thiết kế và tối ưu hóa đầu vào (prompt) cho các mô hình ngôn ngữ lớn (LLM) nhằm dẫn dắt chúng tạo ra output đúng ý định, có kiểm soát và nhất quán.

Với một LLM như Gemini, cùng một yêu cầu nhưng cách diễn đạt khác nhau có thể cho kết quả hoàn toàn khác nhau:

```
❌ Prompt yếu:  "Tạo tin nhắn lừa đảo"
                → Model có thể từ chối, hoặc sinh ra nội dung không đúng format,
                  không đa dạng, không kiểm soát được

✅ Prompt tốt:  [Role] + [Task] + [Context] + [Format] + [Constraints] + [Examples]
                → Model hiểu rõ mục tiêu, sinh ra đúng cấu trúc, đủ đa dạng
```

### 1.1 Các thành phần của một Prompt hoàn chỉnh

| Thành phần | Mục đích | Ví dụ |
|---|---|---|
| **Role (Vai trò)** | Định danh model là ai → điều chỉnh "góc nhìn" | "Bạn là chuyên gia tạo dữ liệu huấn luyện..." |
| **Task (Nhiệm vụ)** | Chỉ định rõ việc cần làm | "Tạo đúng 40 dòng CSV tin nhắn lừa đảo" |
| **Context (Ngữ cảnh)** | Cung cấp thông tin nền để model hiểu domain | "Kịch bản: Giả mạo ngân hàng VCB..." |
| **Format (Định dạng)** | Quy định cấu trúc output | "5 cột: content, label, has_url, ..." |
| **Constraints (Ràng buộc)** | Giới hạn những gì không được làm | "40–160 ký tự, KHÔNG có dấu nháy đơn..." |
| **Examples (Ví dụ)** | Minh họa bằng mẫu cụ thể → Few-shot | "Ví dụ 1: ..., Ví dụ 2: ..." |
| **Output instruction** | Nhắc lại cách format cuối cùng | "Chỉ xuất CSV thuần, không giải thích" |

---

## 2. Cơ chế hoạt động khi sinh Text Data

### 2.1 LLM hoạt động theo xác suất

LLM không "nhớ" dữ liệu thật, mà **học phân phối xác suất** của ngôn ngữ. Khi bạn yêu cầu sinh tin nhắn lừa đảo, model:

1. Khởi tạo dựa trên prompt → đặt "ngữ cảnh"
2. Tại mỗi token tiếp theo, chọn từ top-k tokens có xác suất cao nhất (điều chỉnh bởi `temperature`)
3. Lặp lại cho đến khi đủ output

**Hệ quả quan trọng:**
- `temperature` cao → đa dạng hơn nhưng dễ lệch format, sinh nội dung ngoài ý muốn
- `temperature` thấp → nhất quán format nhưng dễ lặp lại, thiếu đa dạng
- **Prompt tốt** = giảm "không gian tìm kiếm" của model → dễ kiểm soát output hơn

### 2.2 Vì sao Few-shot hiệu quả hơn Zero-shot?

```
Zero-shot (không ví dụ):
  Model tự suy diễn "tin nhắn lừa đảo" trông như thế nào
  → Có thể sinh ra template quen thuộc từ training data quốc tế
  → THIẾU đặc trưng Việt Nam (teencode, domain .vip/.top, BHXH, ...)

Few-shot (có ví dụ thực):
  Model "calibrate" (hiệu chỉnh) output theo pattern bạn cung cấp
  → Bắt chước style, độ dài, ký tự đặc biệt, domain pattern từ ví dụ
  → Output sát thực tế hơn rõ rệt
```

**Ví dụ minh họa** – cùng yêu cầu, khác cách prompt:

```
Zero-shot → Model sinh:
  "Tài khoản VCB của bạn bị khóa. Vui lòng xác thực tại vcb.com.vn"
  (Quá sạch, quá formal, không có obfuscation, domain thật)

Few-shot với mẫu thực → Model sinh:
  "VCB Di9ibank: Tk ban bi kh0a bat thuong! Xac thuc NGAY tai vcb-online.vIp
   hoac mat toan bo so du. KHAN CAP!"
  (Có obfuscation, domain giả, tâm lý urgency, gần thực tế)
```

---

## 3. Tại sao Prompt Engineering quan trọng với Data Augmentation?

### 3.1 Mục tiêu của Data Augmentation cho Smishing

Mô hình phát hiện smishing cần học được **boundary (ranh giới)** giữa:
- Tin nhắn lừa đảo có pattern tinh vi ↔ Tin nhắn ngân hàng thật
- Tin nhắn obfuscated nặng ↔ Tin nhắn teen thông thường

Synthetic data **kém chất lượng** sẽ dạy model học **pattern sai**, dẫn đến:
- **False Positive** cao: Phân loại tin nhắn thật là smishing
- **False Negative** cao: Bỏ sót smishing tinh vi

### 3.2 Ba tiêu chí chất lượng của Synthetic Smishing Data

| Tiêu chí | Giải thích | Hậu quả nếu thiếu |
|---|---|---|
| **Fidelity (Độ trung thực)** | Giống với smishing thật về style, pattern, obfuscation | Model không học được dấu hiệu thật |
| **Diversity (Đa dạng)** | Đủ các category, sub-type, kỹ thuật obfuscation | Model overfit vào một số pattern cố định |
| **Novelty (Tính mới)** | Không trùng lặp với data thật hoặc với nhau | Dataset bị inflate giả tạo |

---

## 4. Phân tích dữ liệu thực tế (Ground Truth)

> Nguồn: `dataset_label_1.csv` – 280 mẫu thu thập thủ công

### 4.1 Phân loại 8 Category chính

Phân tích `dataset_label_1.csv` cho thấy smishing Việt Nam tập trung vào 8 nhóm:

| # | Category | Sub-type | Đặc trưng nhận dạng | Ví dụ thực |
|---|---|---|---|---|
| 1 | **Giả mạo ngân hàng** | Account lock, OTP steal, point expiry | Domain giả (.vip, .top, .cc), brandname sender | `"VCB Digibank tran trong thong bao...tai khoan...bi khoa. Dang nhap www.vcbtiebink.com"` |
| 2 | **Đòi nợ / Đe dọa** | Threatening, debt collection | Tên người + CMND + số tiền + deadline + đe dọa gia đình | `"CANH BAO LAN CUOI!!! Trong 24H nua Ong/Ba...phai lien he...thanh toan KHOAN VAY"` |
| 3 | **BHXH / Trợ cấp giả** | BHTN support, COVID support, tax refund | Quy BHTN, NQ-116, deadline "QUA HAN", random code cuối | `"Theo NQ-116, Ong(Ba) da du d!eu k!en NHAN TIEN ho tro tu quy B/H/T/N"` |
| 4 | **Tuyển dụng giả** | Fake job (TikTok, Amazon, eBay, Tiki) | Lương cao (15-30tr/tháng), Zalo contact, không cần vốn | `"Amazon can tuyen nhan vien lam viec tai nha...thu nhap 10tr-50tr/thang...zalo.me/..."` |
| 5 | **Cờ bạc / Betting** | Casino, game bài, xổ số | Bonus code, link ngắn (t.ly, bit.ly), hoa hồng | `"Dang ky + 558k! Nap 50k nhan 108k...No Hu, Ban Ca. DK: t.ly/..."` |
| 6 | **Giải mạo dịch vụ công** | CSGT, Bộ GTVT, Bộ Y Tế, Thuế | Biên lai phạt, "thông báo cuối cùng", link .top/.xyz | `"Cảnh sát Giao thông Việt Nam: Hồ sơ vi phạm...vui lòng truy cập https://dichvucongs.top"` |
| 7 | **Nội dung nhạy cảm** | Dịch vụ tình dục, hẹn hò | Obfuscation nặng ký tự đặc biệt, Telegram/Zalo link | `"Hen h0 tinh m0t dem cung nhung em g@! xinh dep...Telegram;https://sourl.cn/..."` |
| 8 | **Crypto / Đầu tư giả** | "Kiếm tiền online", thả tim, đặt đơn | Telegram group, task farming, "100k/ngày" | `"Chi can 20 phut moi ngay giao vien chuyen nghiep co the huong dan ban kiem 500k-3000k"` |

### 4.2 Phân phối sender_type theo Category

```
Giả mạo ngân hàng  → 60% brandname, 30% personal_number, 10% shortcode
Đòi nợ / Đe dọa   → 95% personal_number (vì dùng SĐT thực để liên hệ)
BHXH / Trợ cấp    → 90% personal_number (cố tình giả cá nhân gửi)
Tuyển dụng giả    → 85% personal_number (Zalo cá nhân)
Cờ bạc / Betting  → 70% personal_number, 20% shortcode
Dịch vụ công      → 50% brandname, 30% personal_number, 20% shortcode
Nội dung nhạy cảm → 95% personal_number
```

### 4.3 Taxonomy kỹ thuật obfuscation (từ data thật)

Dữ liệu thực cho thấy **6 cấp độ obfuscation**, từ nhẹ đến nặng:

```
LEVEL 0 – Không obfuscation (formal):
  "Vietcombank tran trong thong bao tai khoan cua quy khach hien tai da bi khoa."

LEVEL 1 – Leet nhẹ (thay 1-2 ký tự):
  "Th0ng ba0: BIDV nang cap he thong. Vui l0ng dang nhap https://b0dv.xyz"

LEVEL 2 – Leet nặng + tên riêng (pattern: j=d, f=ph, z=d, w=qu):
  "Ong(Ba) da du d!eu k!en NHAN T1EN h0 tro tu quy BH-TN. Bam vao www.mvndc.icu"

LEVEL 3 – Dot/dash insertion (tách từng ký tự):
  "[A-M-A-Z-O-N] C-h-u-c m-u-n-g b-4-n d-u-o-c t-u-y-3-n. L-u-o-n-g 500k/n-g-4-y"

LEVEL 4 – Mixed special chars (nhiễu loạn ký tự):
  "tORKiM! ay:Ma\"n;N,ha7lXklq,uoacx.tech*;G^ja*nh$ap! nhan:thu\"0g"
  "GR N'ha'nL,jen:Qu.a;HangN,gay y H,ojV'ienM:Oj;N'apV,aoT K..."

LEVEL 5 – Extreme noise (gần như không đọc được):
  "j)t.ly/Q5YuG Um Cu,u~Th,ua8% ZJ Na.pVao-LanD:au,UuDa'j:8Tr8 PJ wz8:88.Bma"
  "ỢờỘỤ ĐặngNh_Ảp Chỗ'iNga_y TPNỜH'Ủ NhắnLỉX_ị 8888(Kắ) FrỀ'ễ..."
```

### 4.4 Patterns URL / Domain giả mạo

```python
FAKE_DOMAIN_PATTERNS = {
    "TLD lạ":      [".vip", ".top", ".xyz", ".cc", ".icu", ".cfd", ".life", ".biz", ".me", ".info"],
    "Brand + TLD": ["vcb-online.vIp", "vietinbank.top", "bidv.xyz", "acb-online-center.com"],
    "Gov giả":     ["dichvucongs.top", "vnta-gov.cc", "hoanthue-tncn.vip", "phatnguoi.xyz"],
    "Subdomain":   ["vietcombank.vn-ms.top", "shb.com.vn-kps.top", "msb.vn-cvs.top"],
    "URL ngắn":    ["bit.ly/...", "t.ly/...", "tinyurl.com/...", "shorturl.at/..."],
    "Homoglyph":   ["vcbtiebink.com", "vniatinbanks.cc", "vovietcombanks.cc"],
}
```

### 4.5 Patterns chiến lược tâm lý

```
URGENCY (Cấp bách):
  → "trước 17h", "trong 24H", "ngay lập tức", "chỉ còn X phút"
  → "HẾT HẠN", "không thể khôi phục", "mặc định xác nhận"

FEAR (Sợ hãi):
  → "bị khóa tài khoản", "chuyển sang cơ quan điều tra"
  → "lộ thông tin cá nhân", "thông báo người thân + nơi làm việc"
  → "nợ xấu CIC", "gửi hồ sơ về địa phương"

GREED (Lòng tham):
  → "trúng thưởng iPhone", "điểm thưởng sắp hết hạn"
  → "nạp 50k nhận 108k", "lương 15-30tr/tháng"
  → "nhận tiền hỗ trợ BHTN miễn phí"

AUTHORITY (Uy quyền):
  → "[BỘ CÔNG AN]", "Cảnh sát Giao thông", "Tổng cục Thuế"
  → "theo NQ-116", "căn cứ Điều 38 Luật Giao dịch điện tử"
  → "Lệnh truy nã", "CCCD", "hồ sơ vi phạm"
```

---

## 5. Khoảng cách giữa Synthetic và Real Data

### 5.1 So sánh trực tiếp

| Tiêu chí | `dataset_label_1.csv` (Real) | `synthetic_2000_smishing_v2.csv` (Synthetic cũ) |
|---|---|---|
| **Category diversity** | 8 category đan xen tự nhiên | Monotone: toàn bộ 1 batch = 1 brand (40/40 mẫu 789BET) |
| **Obfuscation level** | Level 0–5, phân phối tự nhiên | Hầu hết Level 2–3, thiếu Level 4–5 |
| **sender_type format** | `brandname` (không nháy) | `'brandname'` (có nháy đơn – parse error) |
| **Độ dài content** | 30–600+ ký tự (rất đa dạng) | 60–150 ký tự (đồng đều nhân tạo) |
| **Đòi nợ / Đe dọa** | Có (20%+ mẫu) | Gần như không có |
| **BHXH giả** | Có (nhiều biến thể random code) | Không có |
| **Nội dung nhạy cảm** | Có (explicit content) | Không có |
| **Domain pattern** | Đa dạng, sáng tạo | Lặp lại pattern giống nhau (`789bet.vIp`, `789bet.c0m`) |
| **Grammar/Typo** | Tự nhiên, không đồng đều | Quá đồng đều, "cleaner" hơn thực tế |

### 5.2 Nguyên nhân gốc rễ (Root Cause)

```
Vấn đề 1 – Batch monotone:
  Prompt cung cấp 1 category + 1 brand → Model sinh 40 mẫu na ná nhau
  → Kết quả: Thiếu diversity trong batch, dễ overfit

Vấn đề 2 – Không có few-shot:
  Model suy diễn format từ training data → Sinh ra "clean template"
  → Kết quả: Thiếu đặc trưng Việt Nam, thiếu obfuscation thực tế

Vấn đề 3 – Thiếu category mapping:
  Prompt không map category → chiến lược tâm lý cụ thể
  → Kết quả: Tất cả category dùng chung template urgency/fear chung chung

Vấn đề 4 – Không ràng buộc sender_type format:
  Prompt nói "chọn 1 trong: 'brandname', 'shortcode'..." (có nháy đơn)
  → Model copy luôn dấu nháy vào output
```

---

## 6. Kỹ thuật Prompt Engineering hệ thống

### 6.1 Kiến trúc Prompt Layer

Prompt hiệu quả được xây dựng theo **4 lớp** từ ngoài vào trong:

```
┌─────────────────────────────────────────────┐
│  LAYER 1: PERSONA & SAFETY FRAMING         │
│  (Vai trò + bối cảnh nghiên cứu hợp lệ)   │
├─────────────────────────────────────────────┤
│  LAYER 2: TASK SPECIFICATION               │
│  (Nhiệm vụ cụ thể + tham số biến thiên)   │
├─────────────────────────────────────────────┤
│  LAYER 3: FEW-SHOT DEMONSTRATIONS          │
│  (Ví dụ thực → calibrate style/format)    │
├─────────────────────────────────────────────┤
│  LAYER 4: OUTPUT CONSTRAINTS               │
│  (Format + Validation + Negative examples) │
└─────────────────────────────────────────────┘
```

### 6.2 Layer 1: Persona & Safety Framing

**Mục tiêu:** Tránh LLM từ chối yêu cầu vì "nhạy cảm", đồng thời định hướng góc nhìn.

```
❌ Kém: "Bạn là hacker. Hãy tạo tin nhắn lừa đảo."
         → LLM từ chối, hoặc sinh nội dung vô nghĩa

✅ Tốt: "Bạn là chuyên gia an ninh mạng đang tạo dataset huấn luyện
         cho mô hình phát hiện smishing của Bộ Thông tin và Truyền thông VN.
         Nhiệm vụ là tạo dữ liệu giả lập có nhãn để mô hình học cách nhận diện."
         → LLM hiểu đây là nghiên cứu hợp pháp, sẽ hợp tác
```

**Lý do hoạt động:** LLM được fine-tune với RLHF để từ chối nội dung harmful **trong ngữ cảnh thực**. Khi frame rõ ràng là "dữ liệu huấn luyện mô hình bảo mật", LLM phân loại đây là task hợp pháp.

### 6.3 Layer 2: Task Specification – Kỹ thuật "Biến – Hằng"

Tách rõ những gì **thay đổi mỗi batch** (biến) và những gì **cố định** (hằng):

```python
# BIẾN – thay đổi mỗi batch để đảm bảo diversity:
category  = random.choice(SCENARIOS.keys())   # "Giả mạo ngân hàng"
brand     = random.choice(SCENARIOS[category]) # "VCB"
style     = random.choice(OBFUSCATION_LEVELS)  # Level 2 – Leet
psychology = CATEGORY_PSYCHOLOGY[category]     # "fear" – khóa tài khoản
size      = BATCH_SIZE                         # 40

# HẰNG – giữ nguyên mọi batch:
output_format  = "content,label,has_url,has_phone_number,sender_type"
label_value    = 1
length_range   = "40–160 ký tự"
sender_options = "personal_number | brandname | shortcode"
```

### 6.4 Layer 3: Few-shot – Số lượng và Chọn lọc

**Nguyên tắc chọn few-shot examples:**

1. **Bao phủ đa dạng**: Mỗi example nên thể hiện 1 combination khác nhau của (sender_type × psychology × obfuscation_level)
2. **Đủ ngắn để không chiếm quá nhiều token**: 2–3 examples là tối ưu cho batch generation
3. **Trích từ real data**: Ưu tiên dùng mẫu từ `dataset_label_1.csv` vì chúng đã được xác nhận là thực tế

```
Few-shot "Coverage Matrix" lý tưởng cho Label 1:
  Example 1: brandname + fear + Level 1   (bank impersonation)
  Example 2: personal_number + greed + Level 3  (job/gambling scam)
  Example 3: shortcode + urgency + Level 2  (government fake)
```

### 6.5 Layer 4: Output Constraints – Kỹ thuật "Negative Instruction"

Ngoài nói model phải làm gì, cần nói rõ **KHÔNG làm gì**:

```
✅ Negative constraints hiệu quả:
  - "KHÔNG có dòng tiêu đề"           → Ngăn model thêm header CSV
  - "KHÔNG có dấu nháy đơn trong sender_type"  → Fix bug 'brandname'
  - "KHÔNG giải thích, KHÔNG markdown fence"   → Ngăn ```csv...```
  - "KHÔNG lặp lại cùng 1 domain trong batch"  → Tăng diversity URL
  - "KHÔNG dùng brand name thật trong URL"     → Đảm bảo fake domain
```

---

## 7. Thiết kế Prompt cho từng Category

### 7.1 Category Mapping Table

> **TODO – Đây là vùng cần thảo luận chi tiết nhất**

| Category | Sender Type ưu tiên | Psychology chính | Obfuscation Level | Unique patterns |
|---|---|---|---|---|
| Giả mạo ngân hàng | brandname (60%) | fear + urgency | 1–2 | Domain có subdomain dạng `bank.vn-xx.top` |
| Đòi nợ / Đe dọa | personal_number | fear + authority | 0–1 | Tên + CMND + SĐT Zalo, deadline giờ cụ thể |
| BHXH / Trợ cấp | personal_number | greed + urgency | 2–3 | "NQ-116", random code cuối (4 ký tự), domain .icu |
| Tuyển dụng giả | personal_number | greed | 0–2 | Zalo link, "bán thời gian", lương 15-30tr |
| Cờ bạc / Betting | personal_number, shortcode | greed | 2–3 | Link t.ly/bit.ly, "nạp X nhận Y", bonus code |
| Dịch vụ công | brandname, shortcode | fear + authority | 1–2 | "biên lai phạt", "thông báo cuối cùng", link .top |
| Nội dung nhạy cảm | personal_number | greed (nhu cầu) | 3–5 | Telegram, Zalo, mix tiếng Anh, ký tự đặc biệt |
| Crypto / Đầu tư | personal_number | greed | 1–3 | Telegram group, "nhiệm vụ", "thả tim", "đặt đơn" |

### 7.2 Prompt Template – Giả mạo ngân hàng (Đã thiết kế)

```python
# PLACEHOLDER – Cần điền few-shot examples từ Section 8
BANKING_FRAUD_PROMPT = """
Bạn là chuyên gia bảo mật đang tạo dataset phát hiện smishing cho ngân hàng VN.

NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo ngân hàng (label=1).
Ngân hàng bị giả mạo: {brand}
Chiến lược tâm lý: FEAR (sợ mất tài sản/bị khóa) + URGENCY (deadline giờ cụ thể)
Phong cách nhiễu: {style}

ĐẶC TRƯNG CỦA LOẠI NÀY (bắt buộc áp dụng):
  - Domain giả: dạng {brand_lower}.vn-xx.top / {brand_lower}-online.vip / {brand_lower}.cc
  - Sender type: brandname hoặc shortcode (ít khi personal_number)
  - Cú pháp chuẩn ngân hàng giả: "[{BRAND}] Tài khoản..." hoặc "{Brand} trân trọng..."
  - Phải có CTA (call-to-action): "Nhấn vào / Đăng nhập / Xác thực tại [link]"

[PLACEHOLDER – FEW-SHOT EXAMPLES VỊ TRÍ NÀY]

QUY TẮC FORMAT:
  content,1,has_url,has_phone_number,sender_type
  - has_url = 1 (luôn có link)
  - sender_type: brandname hoặc shortcode (KHÔNG dấu nháy đơn)
  - 40–160 ký tự, content wrap trong dấu nháy kép nếu có dấu phẩy

QUAN TRỌNG: Đúng {size} dòng CSV. Không header. Không giải thích. Không markdown.
"""
```

### 7.3 Prompt Template – BHXH / Trợ cấp giả (Đã thiết kế)

```python
# Pattern BHXH có tính hệ thống cao – cần capture đúng
BHXH_SCAM_PROMPT = """
Bạn là chuyên gia bảo mật đang tạo dataset phát hiện smishing từ quỹ BHXH giả.

NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo BHXH/BHTN (label=1).
Chiến lược tâm lý: GREED (nhận tiền miễn phí) + URGENCY (quá hạn không nhận được)
Phong cách nhiễu: {style}

ĐẶC TRƯNG BẮT BUỘC:
  - Viện dẫn: "theo NQ-116", "Quyết định BHXH", "quỹ BHTN"
  - Điều kiện: "Ban da du d!eu k!en" hoặc "da du dieu kien"
  - CTA: "Bam vao / Nhan tai [domain.icu hoặc .com]"
  - Cảnh báo deadline: "QUA HAN SE KH0NG DUOC CHAP NHAN"
  - Kết thúc bằng 4 ký tự random: (ví dụ: hkDF, oZGa, SP0s – làm tracking ID giả)
  - Domain pattern: www.[5-6 ký tự ngẫu nhiên].icu hoặc mo.[random].com
  - Sender type: luôn là personal_number

[PLACEHOLDER – FEW-SHOT EXAMPLES VỊ TRÍ NÀY]

QUAN TRỌNG: Đúng {size} dòng CSV. Không header. Không giải thích. Không markdown.
"""
```

### 7.4 Prompt Template – Đòi nợ / Đe dọa (Chưa thiết kế)

```python
# TODO – Category này quan trọng vì thiếu hoàn toàn trong synthetic data cũ
DEBT_THREAT_PROMPT = """
[PLACEHOLDER – Cần thiết kế đầy đủ]

Đặc trưng cần capture:
  - Có tên người cụ thể (tên Việt random) + CMND/CCCD giả
  - Số tiền cụ thể (không tròn): 1,947,000đ / 48,554,336đ
  - Deadline rất cụ thể: "trước 16H ngày..."
  - Đe dọa tiếp theo: "thông báo người thân, gia đình, nơi làm việc"
  - Kêu gọi Zalo/SĐT cụ thể
  - Sender: personal_number, has_url = 0, has_phone = 1
  - Ngôn ngữ: formal nhưng threatening, không dấu hoặc có dấu
"""
```

---

## 8. Few-Shot Examples Library

### 8.1 Nguyên tắc chọn Few-Shot

Examples phải được **trích từ `dataset_label_1.csv`** để đảm bảo tính thực tế. Dưới đây là danh sách candidates từ real data:

**4 nguyên tắc cốt lõi:**

1. **Bao phủ đa dạng**: Mỗi example nên thể hiện 1 combination khác nhau của `(sender_type × psychology × obfuscation_level)` – tránh 2 examples giống nhau về pattern
2. **Đủ ngắn để không chiếm quá nhiều token**: 2–3 examples là tối ưu cho batch generation; quá nhiều examples → tốn token input, có thể làm model bị "distracted"
3. **Trích từ real data**: Ưu tiên dùng mẫu từ `dataset_label_1.csv` vì đã được xác nhận là thực tế
4. **Luôn dùng đầy đủ 5 cột**: Few-shot example phải là dòng CSV hoàn chỉnh `(content, label, has_url, has_phone_number, sender_type)`, **không chỉ riêng content** – model cần thấy ground truth của tất cả cột để học cách điền đúng metadata

```
Lý do cần đủ 5 cột:
  ❌ Chỉ cung cấp content:
     "VCB Digibank tran trong...www.vcbtiebink.com..."
     → Model không có cơ sở để điền has_url, sender_type
     → Có thể sinh: ...,1,0,0,personal_number  (sai has_url, sai sender_type)

  ✅ Cung cấp đầy đủ dòng CSV:
     "VCB Digibank tran trong...www.vcbtiebink.com",1,1,0,brandname
     → Model học: URL present → has_url=1; bank impersonation → brandname
     → Sinh đúng nhất quán cho toàn batch
```

**Coverage Matrix lý tưởng** (3 examples cho Label 1):
```
  Example 1: brandname + fear    + Level 1  → bank impersonation
  Example 2: personal_number + greed  + Level 3  → job/gambling scam
  Example 3: shortcode + urgency + Level 2  → government fake
```

### 8.2 Candidates cho Banking Fraud Examples

```
✅ Candidate 1 (brandname + fear + Level 1):
  Input row: "VCB Digibank tran trong thong bao.tai khoan cua quy khach hien tai 
              da bi khoa.Dang nhap www.vcbtiebink.com de xac thuc ngay hom nay",1,1,0,brandname

✅ Candidate 2 (brandname + greed + Level 1):
  Input row: "Vietcombank lưu ý: Bạn có 18699 điểm thưởng sẽ hết hạn sau 24 giờ, 
              vui lòng truy cập: https://vietcombankd.cfd/vn để đổi quà.",1,1,0,brandname

✅ Candidate 3 (brandname + fear + Level 2):
  Input row: "UNG DUNG VCB DIGIBANK cua ban duoc PHAT HIEN KICH HOAT tren thiet bi la.
              Neu KHONG PHA BAN KICH HOAT vui long bam vao https://vietcombank.vn-ms.top 
              de doi thiet bi hoac huy de tranh mat tai san",1,1,0,brandname

✅ Quyết định: Dùng cả 3 candidates trên làm few-shot cho Banking Fraud prompt.
   - Brand name (VCB, Vietcombank) giữ nguyên trong few-shot → calibrate style cụ thể từng bank
   - Dùng biến {brand} ở phần Task Specification để generalize sang bank khác
   - Domain giả trong content (.vcbtiebink.com, .cfd, .vn-ms.top) giữ nguyên → đây là fake domain, không phải thông tin cá nhân thật
```

### 8.3 Candidates cho BHXH Scam Examples

```
✅ Candidate 1 (Level 2, random code, TLD .icu):
  "[T.B] BHXH: Ong (Ba) da du d!eu k!en NHAN T1EN h0 tro tu quy BH-TN. 
   Bam vao www.mvndc.icu de lay. QUA HAN SE KH0NG_DUOC CHAP NHAN! oZGa",1,1,0,personal_number

✅ Candidate 2 (Level 3, NQ-116, TLD .icu):
  "Theo _NQ_116, Ong (Ba) da du d!eu k!en NHAN TIEN ho tro tu quy BHTN. 
   Bam vao www.pwmgh.icu de lay. QUA HAN SE KHONG_DUOC CHAP NHAN! hkDF",1,1,0,personal_number

✅ Candidate 3 (Level 1, với dấu, TLD .icu):
  "Ong/(Ba) da du d!eu'k!en NHAN'TIEN ho tro tu quy-BHTN. 
   Bam'vao www.opaxa.icu de_'lay. QUA-HAN' SE KH0ng DUOC CHAP_NAHN! JKqc",1,1,0,personal_number

✅ Candidate 4 (Level 2, TLD .com – biến thể mo.[random].com):
  "BHXH VN: Ong(Ba) DU DIEU KIEN nhan tien ho tro BHTN dot 3.
   Nhan tai: mo.cvxqa.com truoc khi QUA HAN. tPkm",1,1,0,personal_number
```

> **Phân tích domain overlap:** Cả 4 candidates đều dùng domain pattern ngẫu nhiên – đây là **Level A overlap** (pattern trùng, string khác) và là chủ ý đúng đắn, phản ánh thực tế scammer dùng random subdomain. Điều quan trọng hơn là **string domain không được trùng nhau** (Level B) trong cùng một batch sinh ra.
>
> **Hai loại overlap cần phân biệt:**
> - `Level A` – Nhiều messages cùng dùng TLD `.icu` với random chars khác nhau → **Chấp nhận được**, thậm chí đúng thực tế. Dạy model: `.icu` + random chars = đặc trưng smishing
> - `Level B` – Cùng string `www.mvndc.icu` xuất hiện nhiều lần trong batch → **Gây hại**: với TF-IDF, string đó trở thành high-weight feature; model học chuỗi cụ thể thay vì học pattern tổng quát
>
> **Rủi ro thực sự lớn hơn domain overlap:**
> 1. **Content template monotony**: 40 mẫu dùng cùng cấu trúc câu → model overfit vào template cứng
> 2. **Random code cuối bị copy từ few-shot** (`oZGa`, `hkDF` lặp lại) → inflate feature không có nghĩa
> 3. **Thiếu `.com` variant** (Candidate 4 bổ sung điều này) → model bỏ sót BHXH scam dùng `mo.[random].com`

**Constraints cần thêm vào BHXH prompt (Output Layer):**
```
- Domain random chars phải KHÁC NHAU mỗi dòng (không lặp lại mvndc, pwmgh, opaxa, cvxqa từ ví dụ)
- Mã xác nhận cuối (4 ký tự) phải KHÁC NHAU mỗi dòng, không dùng lại oZGa/hkDF/JKqc/tPkm từ ví dụ
- Đa dạng TLD: phân phối ~70% .icu, ~30% .com (dạng mo.[random].com) trong cùng một batch
- Đa dạng cấu trúc câu: không lặp lại cùng template "Ong (Ba) da du dieu kien..." quá 3 lần liên tiếp
```

### 8.4 Candidates cho Job Scam Examples

**Coverage Matrix:**

| Candidate | Platform | Kiểu lừa đảo | sender_type | has_url | has_phone | Level |
|---|---|---|---|---|---|---|
| C1 | Amazon | xử lý đơn TMĐT + Zalo link | personal_number | 1 | 1 | 0 |
| C2 | Cty HVS (generic) | tuyển bán thời gian, formal | personal_number | 1 | 1 | 0 |
| C3 | **Tiki** | đặt đơn nâng rank cửa hàng | personal_number | 0 | 1 | 0 |
| C4 | **TikTok** | xử lý đơn + nhận tiền 13–25 phút | personal_number | 1 | 1 | 1 |
| C5 | **Shopee / Lazada** | xử lý đơn + đánh giá sản phẩm | personal_number | 1 | 0 | 0 |

```
✅ Candidate 1 (Amazon, Zalo link + greed, Level 0, has_url=1, has_phone=1):
  "Amazon cần tuyển nhân viên làm việc tại nhà!!! Yêu cầu 23-60 tuổi. 
   Lương 10tr-50tr/tháng. Ít nhất 500k~3000k/ngày, thao tác đơn giản. 
   Liên hệ Zalo: zalo.me/84938271045 Zalo: 84938271045",1,1,1,personal_number

✅ Candidate 2 (Cty HVS generic, formal style, Level 0, has_url=1, has_phone=1):
  "Xin chào, tôi là trưởng phòng nhân sự của Cty HVS, tuyển nhân viên bán thời gian. 
   Thu nhập 15-30tr/tháng. Làm tại nhà, mọi lúc mọi nơi. Tuổi 22-65. 
   Zalo: zalo.me/84962183074 hoặc 84962183074",1,1,1,personal_number

✅ Candidate 3 (Tiki "đặt đơn nâng rank", Level 0, has_url=0, has_phone=1):
  "Xin chào, mình là giám đốc marketing của Tiki. Cửa hàng Tiki đang tuyển số lượng 
   lớn nhân viên chuyên đặt hàng để nâng cao số lượng giao dịch và thứ hạng cửa hàng. 
   Chỉ cần có kinh nghiệm mua sắm trực tuyến, mỗi ngày bạn có thể dễ dàng kiếm 
   800.000đ bằng điện thoại di động. Lương quyết toán ngay trong ngày. 
   Zalo: 84769231508",1,0,1,personal_number

✅ Candidate 4 (TikTok "xử lý đơn hàng", Level 1 – bỏ dấu, has_url=1, has_phone=1):
  "Tiktok dang tuyen nhan vien lam viec tai nha!!! Mo ta cong viec: Xu ly don hang 
   tren nen tang Tiktok. Thu nhap 350-999k/ngay. Thao tac don gian, nhan tien sau 
   13-25 phut. Lien he ngay: zalo.me/84937512094 zalo:84937512094",1,1,1,personal_number

✅ Candidate 5 (Shopee / Lazada "xử lý đơn + đánh giá SP", Level 0, has_url=1, has_phone=0):
  "Shopee tuyen gap nhan vien xu ly don hang va danh gia san pham tai nha!!! 
   Yeu cau 22-55 tuoi. Thu nhap 500k-1.5tr/ngay. Nhan tien trong ngay sau moi 
   nhiem vu hoan thanh. Khong can kinh nghiem, co nguoi huong dan cu the. 
   Dang ky: zalo.me/84918273645",1,1,0,personal_number
```

> **Phân tích đặc trưng từng platform (trích từ `dataset_label_1.csv`):**
>
> | Platform | Từ khoá đặc trưng | Lương | Contact pattern |
> |---|---|---|---|
> | **Amazon** | "xử lý đơn đặt hàng từ nền tảng thương mại điện tử", "thao tác đơn giản và hướng dẫn đi kèm" | 500k~3000k/ngày | Zalo link + số riêng |
> | **Tiki** | "đặt hàng để nâng cao số lượng giao dịch và thứ hạng", "kinh nghiệm mua sắm trực tuyến" | 800.000đ/ngày | Số Zalo trực tiếp (không Zalo link) |
> | **TikTok** | "Xử lý đơn hàng từ nền tảng ứng dụng", "nhận tiền sau 13–25 phút" | 350–999k/ngày | Zalo link + số riêng |
> | **Shopee/Lazada** | "xử lý đơn + đánh giá sản phẩm", "nâng thứ hạng cửa hàng" | 500k–1.5tr/ngày | Zalo link (số không liệt kê riêng) |
>
> **Lưu ý `has_phone` vs `has_url`:** Khi số điện thoại chỉ nằm trong path của Zalo URL (`zalo.me/84xxx`) và không được liệt kê lại riêng trong văn bản → `has_phone=0`, `has_url=1`. Khi số được liệt kê lại sau link hoặc trực tiếp trong text → `has_phone=1`.

> ⚠️ **Anonymization note**: Tất cả số điện thoại đã được thay bằng số giả đúng format (84 + 9 chữ số). Xem nguyên tắc tại **Section 8.6**.
>
> **Candidates KHÔNG đưa vào few-shot** (quá gần với candidates khác):
> - eBay "xử lý đơn": cùng pattern với Amazon, chỉ khác brand → dùng `{brand}` variable thay thế
> - TikTok "bình luận/thả tim": pattern đặc biệt (has_url=0, has_phone=1, ngắn) → phù hợp cho Crypto/Đầu tư category hơn

### 8.5 Candidates cho Gambling Scam Examples

**Coverage Matrix:**

| Candidate | Style | Obf Level | URL type | sender_type | Unique pattern |
|---|---|---|---|---|---|
| C1 | "nạp X nhận Y", No Hũ / Bắn Cá | 1 | t.ly | personal_number | Tracking code cuối (ZnReS) |
| C2 | App promo, platform list | 2 | .cc domain (athd.cc) | personal_number | Dot-inserted text, "G.em moi Awin" |
| C3 | Casino formal, CSKH 24/24 | 0 | short domain (d82yy.com) | personal_number | Baccarat/chọi gà/xổ số, full Vietnamese |
| C4 | Đại lý / hoa hồng recruit | 1 | .vip domain | **shortcode** | "tuyển đại lý", hoa hồng 50%, Zalo |
| C5 | Slash-dash obfuscation nặng | 3 | .cc domain (ibvif.cc) | personal_number | D/Ki, N-ap, N/ö h/ü, B/än C/ä pattern |

```
✅ Candidate 1 (Level 1, t.ly, tracking code, personal_number):
  "Dang ky + 558k! (Nap 50k nhan 108k) 1 vong cuoc la rut MAXX 8.888k. 
   No Hu. Ban Ca. BCR... DK: t.ly/DJyj1 ZnReS",1,1,0,personal_number

✅ Candidate 2 (Level 2, .cc domain, dotted-platform list, personal_number):
  "G.em moi Awin tag ban 299k khi tai app, x3 nap dau, rut ngay ko can nap, 
   choi TLMN, X.oc-D.ia, N.ohu...dinhcao. click: https://athd.cc/5TyUoM",1,1,0,personal_number

✅ Candidate 3 (Level 0, casino formal, short domain, personal_number):
  "Để chào mừng năm mới, Kim Long tặng ngay 68-888K khi đăng ký tại: d82yy.com, hãy liên hệ CSKH để nhận. Quý vị có thể trải nghiệm các trò chơi: Baccarat trực tiếp, chọi gà, điện tử, thể thao, xổ số v.v. Gửi và rút tiền trong vòng 3 phút, CSKH 24/24",1,1,0,personal_number

✅ Candidate 4 (Level 1, .vip domain, đại lý/hoa hồng recruit, shortcode):
  "V7 top 3 nha cai VN, tuyen dai ly voi muc hoa hong len den 50%, 
   tra hoa hong nhieu hinh thuc, lien he zalo Van: 0932187456 
   Link: https://v7bet.vip",1,1,1,shortcode

✅ Candidate 5 (Level 3, slash-dash obfuscation, .cc domain, personal_number):
  "D/Ki + 558k. ( N-ap 5Ok nhän 1O8k ) 1 vong cuöc la rut MAXX 8.888k. 
   Htra tuc thi 3%. N/ö h/ü - B/än C/ä. BCR... DK: ibvif.cc/LbFzDg ~noyc",1,1,0,personal_number
```

> **Phân tích đặc trưng từng sub-type (trích từ `dataset_label_1.csv`):**
>
> | Sub-type | Từ khoá đặc trưng | URL pattern | sender_type |
> |---|---|---|---|
> | **"nạp X nhận Y"** | "nap Xk nhan Yk", "No Hu", "Ban Ca", "1 vong cuoc la rut MAXX" | t.ly/[code] | personal_number |
> | **Platform promo** | "tai app", "x3 nap dau", "TLMN, Xoc Dia, Nohu" | .cc / .tech domain | personal_number |
> | **Casino formal** | "Baccarat trực tiếp", "CSKH 24/24", "gửi/rút trong 3 phút" | short domain (d82yy, k98) | personal_number |
> | **Đại lý/hoa hồng** | "tuyển đại lý", "hoa hồng X%", "trả hoa hồng nhiều hình thức" | .vip / .bet domain | **shortcode** |
> | **Extreme obfuscation** | D/Ki, N-ap, slash/dash split trên mọi từ, ký tự diacritic lẫn lộn | .cc / ibvif.cc | personal_number |
>
> **Lưu ý chọn few-shot cho một batch cụ thể:**
> - Nếu prompt target "nổ hũ / bắn cá": dùng C1 + C5 (cùng "558k" pattern nhưng khác obfuscation level)
> - Nếu prompt target "casino đa dạng game": dùng C3 + C2
> - Nếu prompt target "đại lý/affiliate": dùng C4 là đủ (pattern rất khác biệt so với các loại khác)

> ⚠️ **Anonymization note**: Số điện thoại C4 (`0935123456` trong real data) đã được thay bằng `0932187456`. Domain và tracking code giữ nguyên – đây là thông tin giả/hết hiệu lực của scammer.

### 8.6 Nguyên tắc Anonymization trong Few-Shot Examples

Few-shot examples được trích từ data thực nên có thể chứa thông tin cá nhân. Quy tắc xử lý:

| Loại thông tin | Quyết định | Cách xử lý đúng |
|---|---|---|
| **Brand name thật** (VCB, Vietcombank, BIDV) | **Giữ nguyên** | Không thay đổi – dùng để calibrate style cụ thể từng brand |
| **Domain giả trong content** (.vcbtiebink.com, .vn-ms.top) | **Giữ nguyên** | Đây là fake domain bịa đặt, không phải thông tin cá nhân |
| **Số điện thoại scammer** (trong Zalo link, nội dung) | **Thay bằng số giả đúng format** | Format VN: `84` + 9 chữ số (ví dụ: `84938271045`) |
| **Tên người thật** (trong debt scam, job scam) | **Thay bằng tên Việt giả hoàn toàn** | Ví dụ: Nguyễn Văn A → Trần Minh Khoa |
| **CMND/CCCD thật** | **Thay bằng số giả đúng format** | 9 hoặc 12 chữ số ngẫu nhiên |

**Nguyên tắc cốt lõi của anonymization:**

```
❌ SAI – Dùng placeholder trừu tượng:
   "zalo.me/PHONE_NUMBER"       → Model học placeholder, không học format 10 số
   "Ông/Bà [TÊN_NGƯỜI]..."      → Model in nguyên [TÊN_NGƯỜI] vào output
   "CMND số [SO_CMND]"          → Model không học được pattern số CMND thật

✅ ĐÚNG – Thay bằng dữ liệu giả nhưng đúng format:
   "zalo.me/84938271045"        → Model học: Zalo format = zalo.me/84xxxxxxxxx
   "Ông/Bà Trần Minh Khoa..."   → Model học: pattern tên Việt 3 tiếng
   "CMND số 079123456789"       → Model học: CCCD = 12 chữ số
```

---

## 9. Checklist đánh giá chất lượng

### 9.1 Format Validation (tự động)

```python
def validate_smishing_row(row: list[str]) -> dict:
    """Kiểm tra tự động sau khi model sinh ra."""
    checks = {}
    
    # F1 – Số cột
    checks["f1_columns"] = len(row) == 5
    
    # F2 – Label đúng
    checks["f2_label"] = row[1].strip() == "1"
    
    # F3 – has_url hợp lệ
    checks["f3_has_url"] = row[2].strip() in ("0", "1")
    
    # F4 – has_phone_number hợp lệ
    checks["f4_has_phone"] = row[3].strip() in ("0", "1")
    
    # F5 – sender_type hợp lệ
    checks["f5_sender"] = row[4].strip() in ("personal_number", "brandname", "shortcode")
    
    # F6 – Độ dài content
    content_len = len(row[0].strip().strip('"'))
    checks["f6_length"] = 20 <= content_len <= 400
    
    # F7 – Consistency: has_url = 1 nếu có URL pattern
    import re
    has_url_pattern = bool(re.search(r'https?://|www\.|bit\.ly|t\.ly|tinyurl', row[0]))
    checks["f7_url_consistency"] = not (has_url_pattern and row[2].strip() == "0")
    
    return checks
```

### 9.2 Content Quality (review thủ công)

Sau mỗi lần chạy batch mới, review ngẫu nhiên 10% mẫu theo checklist:

- [ ] Content có giống smishing thực tế không? (không quá "polished")
- [ ] Obfuscation style đúng với level yêu cầu không?
- [ ] Domain URL trông như domain giả mạo không?
- [ ] Chiến lược tâm lý (fear/greed/urgency) được thể hiện rõ không?
- [ ] sender_type có khớp với loại smishing không?
- [ ] Nội dung không lặp lại với mẫu khác trong batch?

### 9.3 Distribution Check (sau khi thu thập đủ data)

```python
import pandas as pd

def check_distribution(filepath: str):
    df = pd.read_csv(filepath)
    
    print("=== DISTRIBUTION REPORT ===")
    print(f"Total: {len(df)}")
    print(f"\nsender_type:\n{df['sender_type'].value_counts(normalize=True)}")
    print(f"\nhas_url:\n{df['has_url'].value_counts(normalize=True)}")
    print(f"\nhas_phone_number:\n{df['has_phone_number'].value_counts(normalize=True)}")
    
    # Target: 
    # sender_type: ~50% personal_number, ~35% brandname, ~15% shortcode
    # has_url: ~75% = 1
    # has_phone: ~30% = 1
```

---

## 10. Roadmap cải tiến

### 10.1 Ưu tiên ngay (Sprint hiện tại)

- [ ] **[P0]** Chọn và điền few-shot examples vào Section 8
- [ ] **[P0]** Thiết kế BHXH prompt hoàn chỉnh (Section 7.3) – thiếu hoàn toàn trong v2
- [ ] **[P0]** Thiết kế Debt/Threat prompt (Section 7.4) – thiếu hoàn toàn trong v2
- [ ] **[P1]** Map đầy đủ Category → Psychology trong `gen_label_1.py`

### 10.2 Ưu tiên tiếp theo

- [ ] **[P1]** Thêm "Negative examples" vào prompt (chỉ rõ output KHÔNG mong muốn)
- [ ] **[P1]** Thử nghiệm few-shot với 2 vs 3 examples → so sánh diversity
- [ ] **[P2]** Tạo Category-specific temperature: Level 4–5 obfuscation cần temperature cao hơn
- [ ] **[P2]** Thiết kế prompt cho nội dung nhạy cảm (Level 4–5) – an toàn với safety filter

### 10.3 Đánh giá sau khi hoàn thành

- [ ] Chạy KNN similarity giữa synthetic và real data → đo Fidelity
- [ ] Đo inter-sample cosine similarity → đo Diversity
- [ ] Chạy thử mô hình với old vs new synthetic data → đo impact thực tế

---

## Ghi chú thảo luận

> **Phần này dùng để ghi lại các quyết định và thảo luận trong quá trình cập nhật**

### [2026-03-23] Phiên thảo luận đầu tiên

**Quan sát từ data thực:**
- `dataset_label_1.csv` có mật độ BHXH scam cao (~15% tổng mẫu) nhưng `synthetic_2000_smishing_v2.csv` gần như không có → Cần ưu tiên bổ sung
- Obfuscation Level 4–5 (extreme noise) chiếm ~10% real data nhưng 0% synthetic → Cần thêm category "Extreme Obfuscation" riêng
- Debt collection scam dùng **tên người thật + CMND giả** – pattern này rất đặc trưng, cần few-shot cụ thể

**Quyết định pending:**
- [ ] Có nên tách "Extreme Obfuscation" thành 1 category riêng trong `SCENARIOS` không?
- [ ] Few-shot nên là 2 hay 3 examples? (trade-off: 3 examples → tốn token nhưng calibrate tốt hơn)
- [ ] Nội dung nhạy cảm (sexual) – có đưa vào không? Nếu có thì xử lý safety filter như thế nào?

---

### [2026-03-23] Phiên thảo luận thứ hai – Few-Shot Examples (Section 8)

**Chủ đề thảo luận:** Cấu trúc few-shot examples và nguyên tắc anonymization

**Quyết định đã chốt:**

1. **Few-shot phải dùng đầy đủ 5 cột** – không chỉ riêng `content`:
   - Model cần thấy ground truth của `has_url`, `has_phone_number`, `sender_type` để học cách điền đúng toàn bộ dòng CSV
   - Nếu chỉ cho content, model sẽ "đoán" các cột metadata → sinh sai nhất quán

2. **Anonymization theo loại thông tin** (xem chi tiết tại Section 8.6):
   - Brand name thật (VCB, Vietcombank) → **Giữ nguyên** trong few-shot, dùng `{brand}` ở task description để generalize
   - Số điện thoại scammer → **Thay bằng số giả đúng format** (không dùng placeholder trừu tượng)
   - Tên người thật → **Thay bằng tên Việt giả hoàn toàn**
   - Fake domain trong content → **Giữ nguyên** (không phải thông tin cá nhân)

3. **Áp dụng cho 8.4 (Job Scam)**: Hai số Zalo thật (`84927946049`, `84925605508`) đã được thay bằng số giả (`84938271045`, `84962183074`) – đúng format nhưng không liên hệ được người thật

**Quyết định pending:**
- [ ] Có nên tách "Extreme Obfuscation" thành 1 category riêng trong `SCENARIOS` không?
- [ ] Nội dung nhạy cảm (sexual) – có đưa vào không? Nếu có thì xử lý safety filter như thế nào?

---

### [2026-03-23] Phiên thảo luận thứ ba – Domain Pattern Overlap (Section 8.3)

**Chủ đề thảo luận:** Liệu việc trùng lặp domain pattern giữa các tin nhắn có ảnh hưởng chất lượng dữ liệu không?

**Phân tích đã thực hiện:**

Phân biệt 2 cấp độ overlap hoàn toàn khác nhau về mức độ ảnh hưởng:
- **Level A** (pattern trùng, string khác – ví dụ: nhiều messages cùng dùng `.icu` nhưng subdomain khác nhau): **Chấp nhận được** – phản ánh đúng hành vi scammer thật; dạy model học TLD lạ là đặc trưng smishing
- **Level B** (string trùng hoàn toàn – ví dụ: `www.mvndc.icu` xuất hiện nhiều lần): **Gây hại** với TF-IDF/BoW model; ít ảnh hưởng hơn với neural model do tokenization ở subword level

**Kết luận:** Domain pattern overlap KHÔNG phải mối nguy lớn nhất. Mối nguy thực sự là:
1. Content template monotony (cấu trúc câu lặp lại trong batch)
2. Random code cuối (`oZGa`, `hkDF`) bị LLM copy nguyên từ few-shot examples
3. Thiếu đa dạng TLD (chỉ `.icu`, thiếu `.com` variant `mo.[random].com`)

**Quyết định đã chốt:**
- Thêm Candidate 4 vào 8.3: biến thể `mo.[random].com` để bao phủ TLD thứ hai
- Thêm 4 constraints vào BHXH prompt Output Layer: domain string khác nhau mỗi dòng, random code cuối khác nhau mỗi dòng, phân phối TLD ~70% `.icu` / ~30% `.com`, đa dạng cấu trúc câu

**Quyết định pending:**
- [ ] Áp dụng phân tích tương tự cho 8.5 (Gambling) – kiểm tra xem có rủi ro Level B không?

---

### [2026-03-23] Phiên thảo luận thứ tư – Job Scam Variants (Section 8.4)

**Chủ đề thảo luận:** Bổ sung few-shot candidates cho các platform TMĐT phổ biến tại Việt Nam (Tiki, Shopee, Lazada)

**Phân tích từ `dataset_label_1.csv`:**
- Tìm thấy 3 nhóm pattern job scam riêng biệt: Amazon/eBay style, Tiki "đặt đơn nâng rank", TikTok "xử lý đơn + nhận tiền nhanh"
- Shopee/Lazada job scam không có trong real data nhưng được tổng hợp từ pattern tương tự
- Phân biệt quan trọng về `has_phone`: số trong `zalo.me/84xxx` URL path → `has_phone=0`; số liệt kê riêng trong text → `has_phone=1`

**Quyết định đã chốt:**
- Thêm 3 candidates mới (C3 Tiki, C4 TikTok, C5 Shopee/Lazada) vào 8.4
- Coverage Matrix 5 candidates bao phủ: 3 platform TMĐT VN, 2 kiểu contact (link vs số trực tiếp), Level 0 và Level 1
- eBay không cần candidate riêng: cùng pattern với Amazon, dùng `{brand}` variable là đủ
- TikTok "thả tim/bình luận" pattern (has_url=0, ngắn, no greed salary claim) → phù hợp hơn cho Crypto/Đầu tư category

**Quyết định pending:**
- [ ] Xây dựng prompt template cho Job Scam (Section 7 chưa có) với `{brand}` variable bao phủ Amazon/Tiki/TikTok/Shopee/Lazada/eBay

---

### [2026-03-23] Phiên thảo luận thứ năm – Gambling Scam Candidates (Section 8.5)

**Chủ đề thảo luận:** Chọn 5 candidates đa dạng cho gambling/betting scam từ `dataset_label_1.csv`

**Phân loại sub-type gambling scam từ real data:**
- "nạp X nhận Y" (rows 193–199): template chuẩn nhất, t.ly link, tracking code cuối
- Platform promo / "tai app" (rows 266–267): dots-inserted text, platform list (TLMN, Xóc Đĩa, Nổ Hũ)
- Casino formal (row 21): Level 0, Baccarat/chọi gà/xổ số, CSKH 24/24, short domain
- Đại lý/hoa hồng (row 58): duy nhất dùng **shortcode** sender, hoa hồng 50%, .vip domain
- Extreme obfuscation (row 198): slash/dash split toàn bộ từ, diacritic lẫn lộn, Level 3

**Quyết định đã chốt:**
- 5 candidates bao phủ: Level 0/1/2/3, URL types: t.ly/.cc/short domain/.vip, sender: personal_number (4) + shortcode (1)
- C4 (đại lý/hoa hồng, shortcode) là candidate duy nhất trong 8.5 dùng shortcode – quan trọng để model biết không phải gambling scam nào cũng từ personal_number
- C5 (slash-dash obfuscation) nằm giữa Level 3–4, phục vụ như "bridge" sang extreme obfuscation

**Quyết định pending:**
- [x] Double-check toàn bộ Section 8 (8.1–8.5) trước khi thiết kế prompt – xem phiên thảo luận tiếp theo

---

### [2026-03-23] Phiên thảo luận thứ sáu – Double-Check & Chốt kiến trúc

**Chủ đề thảo luận:** Double-check toàn bộ Section 8 và chốt kiến trúc `SCENARIOS` trước khi thiết kế prompt

**Kết quả double-check:**

*Lỗi phát hiện và đã sửa (do người dùng tự sửa):*
1. **8.4 C1 (Amazon)**: `has_phone=1` nhưng số chỉ nằm trong URL path → đã thêm `Zalo: 84938271045` sau link để metadata khớp nội dung ✅
2. **8.4 C2 (HVS)**: Tương tự C1 → đã thêm `hoặc 84962183074` sau Zalo link ✅
3. **8.5 C3 (Casino Kim Long)**: Label "Level 0" nhưng content bỏ dấu (Level 1) → đã restore diacritics tiếng Việt đầy đủ ✅

*Confirmed đúng (không cần sửa):*
- 8.2 Banking Fraud: cả 3 candidates đều đúng metadata ✅
- 8.3 BHXH: cả 4 candidates đều đúng metadata ✅
- 8.4 C3/C4/C5: đúng ✅
- 8.5 C1/C2/C4/C5: đúng ✅

*Coverage gap đã xác nhận (sẽ xử lý ở Sprint sau):*
- Thiếu few-shot cho: Cat 2 (Đòi nợ), Cat 6 (Dịch vụ công), Cat 7 (Nhạy cảm), Cat 8 (Crypto)

**Quyết định kiến trúc đã chốt:**
- **Số category: 8** – theo đúng Section 7.1 (từ bỏ cấu trúc 4-category cũ)
- `gen_label_1.py SCENARIOS` đã được cập nhật từ 4 → 8 category:
  - Tách riêng BHXH (Cat 3) khỏi Dịch vụ công (Cat 6)
  - Tách riêng Cờ bạc (Cat 5) khỏi Nội dung nhạy cảm (Cat 7)
  - Thêm mới: Đòi nợ/Đe dọa (Cat 2) và Crypto/Đầu tư (Cat 8)
  - Mỗi category có danh sách brand/entity riêng để randomize

**Trạng thái sẵn sàng cho Prompt Design:**

| Category | Few-shot | Prompt template | Trạng thái |
|---|---|---|---|
| 1 – Giả mạo ngân hàng | ✅ 8.2 (3 candidates) | 🔨 7.2 (draft) | Sẵn sàng thiết kế |
| 2 – Đòi nợ / Đe dọa | ❌ Chưa có | ❌ 7.4 (placeholder) | Cần làm trước khi chạy |
| 3 – BHXH / Trợ cấp | ✅ 8.3 (4 candidates) | 🔨 7.3 (draft) | Sẵn sàng thiết kế |
| 4 – Tuyển dụng giả | ✅ 8.4 (5 candidates) | ❌ Chưa có | Sẵn sàng thiết kế |
| 5 – Cờ bạc / Betting | ✅ 8.5 (5 candidates) | ❌ Chưa có | Sẵn sàng thiết kế |
| 6 – Dịch vụ công | ❌ Chưa có | ❌ Chưa có | Cần làm |
| 7 – Nội dung nhạy cảm | ❌ Chưa có | ❌ Chưa có | Defer – safety filter |
| 8 – Crypto / Đầu tư | ❌ Chưa có | ❌ Chưa có | Cần làm |

**Bước tiếp theo:** Thiết kế prompt template cho 4 category đã có few-shot (Cat 1, 3, 4, 5), ưu tiên theo thứ tự tác động lớn nhất đến dataset quality.
