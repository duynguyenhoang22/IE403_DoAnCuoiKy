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


| Thành phần                  | Mục đích                                      | Ví dụ                                         |
| --------------------------- | --------------------------------------------- | --------------------------------------------- |
| **Role (Vai trò)**          | Định danh model là ai → điều chỉnh "góc nhìn" | "Bạn là chuyên gia tạo dữ liệu huấn luyện..." |
| **Task (Nhiệm vụ)**         | Chỉ định rõ việc cần làm                      | "Tạo đúng 40 dòng CSV tin nhắn lừa đảo"       |
| **Context (Ngữ cảnh)**      | Cung cấp thông tin nền để model hiểu domain   | "Kịch bản: Giả mạo ngân hàng VCB..."          |
| **Format (Định dạng)**      | Quy định cấu trúc output                      | "5 cột: content, label, has_url, ..."         |
| **Constraints (Ràng buộc)** | Giới hạn những gì không được làm              | "40–160 ký tự, KHÔNG có dấu nháy đơn..."      |
| **Examples (Ví dụ)**        | Minh họa bằng mẫu cụ thể → Few-shot           | "Ví dụ 1: ..., Ví dụ 2: ..."                  |
| **Output instruction**      | Nhắc lại cách format cuối cùng                | "Chỉ xuất CSV thuần, không giải thích"        |


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


| Tiêu chí                     | Giải thích                                             | Hậu quả nếu thiếu                        |
| ---------------------------- | ------------------------------------------------------ | ---------------------------------------- |
| **Fidelity (Độ trung thực)** | Giống với smishing thật về style, pattern, obfuscation | Model không học được dấu hiệu thật       |
| **Diversity (Đa dạng)**      | Đủ các category, sub-type, kỹ thuật obfuscation        | Model overfit vào một số pattern cố định |
| **Novelty (Tính mới)**       | Không trùng lặp với data thật hoặc với nhau            | Dataset bị inflate giả tạo               |


---

## 4. Phân tích dữ liệu thực tế (Ground Truth)

> Nguồn: `dataset_label_1.csv` – 280 mẫu thu thập thủ công

### 4.1 Phân loại 8 Category chính

Phân tích `dataset_label_1.csv` cho thấy smishing Việt Nam tập trung vào 8 nhóm:


| #   | Category                 | Sub-type                                | Đặc trưng nhận dạng                                     | Ví dụ thực                                                                                  |
| --- | ------------------------ | --------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1   | **Giả mạo ngân hàng**    | Account lock, OTP steal, point expiry   | Domain giả (.vip, .top, .cc), brandname sender          | `"VCB Digibank tran trong thong bao...tai khoan...bi khoa. Dang nhap www.vcbtiebink.com"`   |
| 2   | **Đòi nợ / Đe dọa**      | Threatening, debt collection            | Tên người + CMND + số tiền + deadline + đe dọa gia đình | `"CANH BAO LAN CUOI!!! Trong 24H nua Ong/Ba...phai lien he...thanh toan KHOAN VAY"`         |
| 3   | **BHXH / Trợ cấp giả**   | BHTN support, COVID support, tax refund | Quy BHTN, NQ-116, deadline "QUA HAN", random code cuối  | `"Theo NQ-116, Ong(Ba) da du d!eu k!en NHAN TIEN ho tro tu quy B/H/T/N"`                    |
| 4   | **Tuyển dụng giả**       | Fake job (TikTok, Amazon, eBay, Tiki)   | Lương cao (15-30tr/tháng), Zalo contact, không cần vốn  | `"Amazon can tuyen nhan vien lam viec tai nha...thu nhap 10tr-50tr/thang...zalo.me/..."`    |
| 5   | **Cờ bạc / Betting**     | Casino, game bài, xổ số                 | Bonus code, link ngắn (t.ly, bit.ly), hoa hồng          | `"Dang ky + 558k! Nap 50k nhan 108k...No Hu, Ban Ca. DK: t.ly/..."`                         |
| 6   | **Giả mạo dịch vụ công** | CSGT, Bộ GTVT, Bộ Y Tế, Thuế            | Biên lai phạt, "thông báo cuối cùng", link .top/.xyz    | `"Cảnh sát Giao thông Việt Nam: Hồ sơ vi phạm...vui lòng truy cập https://dichvucongs.top"` |
| 7   | **Nội dung nhạy cảm**    | Dịch vụ tình dục, hẹn hò                | Obfuscation nặng ký tự đặc biệt, Telegram/Zalo link     | `"Hen h0 tinh m0t dem cung nhung em g@! xinh dep...Telegram;https://sourl.cn/..."`          |
| 8   | **Crypto / Đầu tư gỉa**  | "Kiếm tiền online", thả tim, đặt đơn    | Telegram group, task farming, "100k/ngày"               | `"Chi can 20 phut moi ngay giao vien chuyen nghiep co the huong dan ban kiem 500k-3000k"`   |


### 4.2 Phân phối sender_type theo Category

```
Giả mạo ngân hàng → brandname (~60%), shortcode (~40%) – KHÔNG dùng personal_number (giả mạo SMS Brandname)
Đòi nợ / Đe dọa   → 95% personal_number (vì dùng SĐT thực để liên hệ)
BHXH / Trợ cấp    → 90% personal_number (cố tình giả cá nhân gửi)
Tuyển dụng giả    → 85% personal_number (Zalo cá nhân)
Cờ bạc / Betting  → 70% personal_number, 20% shortcode
Dịch vụ công      → 50% brandname, 30% personal_number, 20% shortcode
Nội dung nhạy cảm → 95% personal_number
Crypto / Đầu tư   → 100% personal_number
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


| Tiêu chí               | `dataset_label_1.csv` (Real)    | `synthetic_2000_smishing_v2.csv` (Synthetic cũ)         |
| ---------------------- | ------------------------------- | ------------------------------------------------------- |
| **Category diversity** | 8 category đan xen tự nhiên     | Monotone: toàn bộ 1 batch = 1 brand (40/40 mẫu 789BET)  |
| **Obfuscation level**  | Level 0–5, phân phối tự nhiên   | Hầu hết Level 2–3, thiếu Level 4–5                      |
| **sender_type format** | `brandname` (không nháy)        | `'brandname'` (có nháy đơn – parse error)               |
| **Độ dài content**     | 30–600+ ký tự (rất đa dạng)     | 60–150 ký tự (đồng đều nhân tạo)                        |
| **Đòi nợ / Đe dọa**    | Có (20%+ mẫu)                   | Gần như không có                                        |
| **BHXH giả**           | Có (nhiều biến thể random code) | Không có                                                |
| **Nội dung nhạy cảm**  | Có (explicit content)           | Không có                                                |
| **Domain pattern**     | Đa dạng, sáng tạo               | Lặp lại pattern giống nhau (`789bet.vIp`, `789bet.c0m`) |
| **Grammar/Typo**       | Tự nhiên, không đồng đều        | Quá đồng đều, "cleaner" hơn thực tế                     |


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

```python
SYSTEM_PROMPT = """Bạn là chuyên gia an ninh mạng đang xây dựng dataset huấn luyện mô hình phát hiện smishing 
cho dự án bảo vệ người dùng di động tại Việt Nam (phối hợp với Bộ TT&TT). Đây là dữ liệu giả lập phục vụ nghiên cứu bảo mật hợp pháp."""
```

### 6.3 Layer 2: Task Specification – Kỹ thuật "Biến – Hằng"

Những điểm khác biệt chính so với phiên bản ban đầu:

`brand` **→** `brands_str` **(toàn list):** Không chọn 1 brand rồi truyền vào — mà truyền toàn bộ danh sách, để model tự mix brand từng dòng trong batch. Đảm bảo diversity tốt hơn mà không cần sample lại mỗi dòng.

`style` **→** `(obf_lo, obf_hi), style_prompt` **từ** `pick_mixed_style()`**:** Thay vì chọn 1 level duy nhất, hàm này gộp mô tả của tất cả level trong range của category thành 1 chuỗi, yêu cầu model phân bổ đều. `obf_lo/hi` được giữ lại riêng cho bước `extract_valid_rows()` để soft-check sau khi sinh.

`batch_size` **động:** `min(BATCH_SIZE, remaining)` thay vì hằng số cố định — batch cuối không bao giờ overshoot.

`output_format` **dùng pipe** `|` **thay vì comma:** Parser dùng chiến lược "lấy 4 phần tử cuối làm metadata" để xử lý trường hợp content chứa ký tự `|`.

```python
# ─── BIẾN – thay đổi mỗi batch để đảm bảo diversity ───────────────────────
category   = random.choice(SCENARIOS.keys())
# Ví dụ: "Giả mạo ngân hàng"

brands_list = SCENARIOS[category]
brands_str  = ", ".join(brands_list)
# Toàn bộ danh sách brand của category được truyền vào prompt,
# model tự chọn ngẫu nhiên 1 brand cho từng dòng (mix trong batch)
# Ví dụ: "Vietcombank, VCB Digibank, BIDV, Techcombank, ..."

(obf_lo, obf_hi), style_prompt = pick_mixed_style(category)
# Tra CATEGORY_OBF_RANGE → range (lo, hi) của category
# Gộp MÔ TẢ + FEW-SHOT của TẤT CẢ level trong [lo, hi] thành 1 chuỗi
# Model tự phân bổ đều các dòng across mức obfuscation trong range
# Ví dụ: "Giả mạo ngân hàng" → (1, 2) → style chứa Level 1 + Level 2

batch_size = min(BATCH_SIZE, TOTAL_SAMPLES - current_total)
# Batch cuối có thể nhỏ hơn BATCH_SIZE

# ─── HẰNG – giữ nguyên mọi batch ──────────────────────────────────────────

output_format  = "content|label|has_url|has_phone_number|sender_type"
# Dùng pipe (|) làm delimiter thay vì comma — tránh escape khi content chứa dấu phẩy
# Parser lấy 4 cột CUỐI làm metadata, phần còn lại ghép lại thành content

label_value    = 1
length_range   = per-category          # 40–160 / 80–300 / 80–250 / ... (khác nhau theo cat)
sender_options = "personal_number | brandname | shortcode"
# Tỉ lệ sender cụ thể theo category (ví dụ: banking → brandname 60% / shortcode 40%)
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


| Category          | Sender Type ưu tiên                                     | Psychology chính | Obfuscation Level | Unique patterns                                   |
| ----------------- | ------------------------------------------------------- | ---------------- | ----------------- | ------------------------------------------------- |
| Giả mạo ngân hàng | brandname (60%), shortcode (40%)                        | fear + urgency   | 1–2               | Domain có subdomain dạng `bank.vn-xx.top`         |
| Đòi nợ / Đe dọa   | personal_number                                         | fear + authority | 0–1               | Tên + CMND + SĐT Zalo, deadline giờ cụ thể        |
| BHXH / Trợ cấp    | personal_number                                         | greed + urgency  | 2–3               | "NQ-116", random code cuối (4 ký tự), domain .icu |
| Tuyển dụng giả    | personal_number                                         | greed            | 0–2               | Zalo link, "bán thời gian", lương 15-30tr         |
| Cờ bạc / Betting  | personal_number, shortcode                              | greed            | 2–3               | Link t.ly/bit.ly, "nạp X nhận Y", bonus code      |
| Dịch vụ công      | brandname (50%), shortcode (30%), personal_number (20%) | fear + authority | 1–2               | "biên lai phạt", "thông báo cuối cùng", link .top |
| Nội dung nhạy cảm | personal_number                                         | greed (nhu cầu)  | 3–5               | Telegram, Zalo, mix tiếng Anh, ký tự đặc biệt     |
| Crypto / Đầu tư   | personal_number                                         | greed            | 1–3               | Telegram group, "nhiệm vụ", "thả tim", "đặt đơn"  |


### 7.2 Prompt Template – Giả mạo ngân hàng (Đã thiết kế)

```python
BANKING_FRAUD_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo ngân hàng (label=1).
Ngân hàng bị giả mạo: {brands}
Chiến lược tâm lý: FEAR (sợ mất tài sản/bị khóa) + URGENCY (deadline giờ cụ thể)
 
ĐẶC TRƯNG CỦA LOẠI NÀY (bắt buộc áp dụng):
  - YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một ngân hàng từ danh sách trên cho mỗi dòng. KHÔNG ĐƯỢC lặp lại liên tục một ngân hàng.
  - Domain giả tương ứng với brand: dạng {brand_lower}.vn-xx.top / {brand_lower}-online.vip / {brand_lower}.cc
  - Sender type: brandname hoặc shortcode (ít khi personal_number)
  - Cú pháp chuẩn ngân hàng giả: "[{brands.upper()}] Tài khoản..." hoặc "{brands} trân trọng..."
  - Phải có CTA (call-to-action): "Nhấn vào / Đăng nhập / Xác thực tại [link]"

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu style):
VCB Digibank tran trong thong bao.tai khoan cua quy khach hien tai da bi khoa.Dang nhap www.vcbtiebink.com de xac thuc ngay hom nay|1|1|0|brandname
Vietcombank lưu ý: Bạn có 18699 điểm thưởng sẽ hết hạn sau 24 giờ, vui lòng truy cập: https://vietcombankd.cfd/vn để đổi quà.|1|1|0|brandname
UNG DUNG VCB DIGIBANK cua ban duoc PHAT HIEN KICH HOAT tren thiet bi la. Neu KHONG PHA BAN KICH HOAT vui long bam vao https://vietcombank.vn-ms.top de doi thiet bi hoac huy de tranh mat tai san|1|1|0|brandname
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 (luôn có link)
  - has_phone = 0 (ngân hàng giả không để SĐT liên hệ trực tiếp)
  - sender_type: brandname (~60%), shortcode (~40%) – KHÔNG dùng personal_number
    (KHÔNG dấu nháy đơn)
  - 40–160 ký tự
  - Domain giả KHÁC NHAU mỗi dòng (hạn chế lặp lại full domain, chỉ dùng cùng TLD pattern)
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.3 Prompt Template – Đòi nợ/ Đe doạ (Đã thiết kế)

```python
DEBT_THREAT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn đòi nợ / đe dọa (label=1).
Tổ chức đòi nợ giả mạo (chỉ dùng cho Sub-type A): {brands}
Chiến lược tâm lý: FEAR (mất uy tín, bị điều tra hình sự) + AUTHORITY (cơ quan pháp lý giả)

ĐẶC TRƯNG BẮT BUỘC:
  - Mở đầu bằng 1 trong: "CANH BAO LAN CUOI!!!" / "[CANH CAO LAN CUOI]:" / "TB KHAN:"
  - KHÔNG có URL/link (has_url luôn = 0)
  - sender: personal_number (luôn luôn)

  SUB-TYPE A – Công ty tài chính / đòi nợ tư nhân (~70% batch):
    → YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một tổ chức từ danh sách trên cho mỗi dòng.
    → BẮT BUỘC: tên người Việt 3 tiếng ngẫu nhiên (KHÔNG lặp lại giữa các dòng)
    → BẮT BUỘC: số CMND/CCCD giả (9 hoặc 12 chữ số, KHÔNG toàn 0 hoặc toàn 1)
    → BẮT BUỘC: số tiền KHÔNG tròn: ví dụ 3,947,000VND / 48,554,336VND / 1,285,000VND
    → Deadline cụ thể: "truoc 16H Ngay DD/MM" / "Trong 24H nua" / "truoc 17g hom nay"
    → Đe dọa: "Cong Khai HINH ANH va THONG TIN", "thong bao nguoi than gia dinh noi lam viec",
      "ghi no xau CIC"
    → CTA: số điện thoại local (0xxxxxxxxx) hoặc ZALO để liên hệ (has_phone = 1 nếu có local SĐT)

  SUB-TYPE B – Giả mạo cơ quan điều tra (~30% batch):
    → Dùng "Ong/Ba" hoặc "O/B" generic, KHÔNG cần tên/CMND cụ thể
    → Nhấn mạnh "trach nhiem hinh su", "Phong AN NINH DIEU TRA", "dieu tra toan bo thong tin"
    → CTA: SĐT dạng quốc tế (84xxxxxxxxx) hoặc không có SĐT (has_phone = 0)
    → Deadline: "truoc 17g hom nay" hoặc "trong vong 24H"

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}

VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên tên/CMND/số tiền, dùng làm tham chiếu style):
CANH BAO LAN CUOI!!! Trong 24H nua Ong/Ba Nguyen Thi Lan CMND: 046079231845 phai lien he gap SDT/ZALO: 0352891743 gap Tran Van Duc de THOA THUAN-GIAM NO. Neu KHONG HOP TAC thanh toan KHOAN VAY 3,947,000VND se Cong Khai HINH ANH va THONG TIN len XA HOI, DIA PHUONG va thong bao nguoi than.|1|0|1|personal_number
Trung Tam Tin Dung F&TB den Ong/Ba: So CMND: 024091768345. Chung toi nghi ngo Ong/Ba lam dung tin nhiem chiem doat tai san voi so tien: 48,554,336VND (tien goc). Canh bao lan cuoi truoc 16H Ngay 25/03 thanh toan toi thieu: 3,725,583VND. Tiep tuc bat hop tac, moi rui ro ve Uy tin Danh du Tai san Ong/Ba tu chiu.|1|0|0|personal_number
[CANH CAO LAN CUOI]: Chung toi da nhac nho nhieu lan nhung O/B van bat hop tac. Truoc 17g hom nay chua thanh toan, Phong AN NINH DIEU TRA se vao cuoc dieu tra toan bo thong tin hinh anh cua O/B va nhung nguoi lien quan se phai chiu trach nhiem hinh su. LH khi san sang: 84912654378.|1|0|0|personal_number

QUY TẮC FORMAT (pipe-delimited):
  content|1|0|has_phone_number|personal_number
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (KHÔNG BAO GIỜ có link)
  - has_phone = 1 nếu content chứa SĐT local 10 số (0xxxxxxxxx), 0 nếu không
  - sender_type = personal_number (luôn luôn)
  - 80–300 ký tự (dài hơn các loại smishing khác – đặc trưng đòi nợ)
  - KHÔNG lặp tên người, CMND, số tiền giữa các dòng trong cùng batch

QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.4 Prompt Template – BHXH/ Trợ cấp (Đã thiết kế)

```python
# Pattern BHXH có tính hệ thống cao – cần capture đúng
BHXH_SCAM_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo BHXH/BHTN (label=1).
Tổ chức / chương trình bị giả mạo: {brands}
Chiến lược tâm lý: GREED (nhận tiền miễn phí) + URGENCY (quá hạn không nhận được)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một tổ chức/chương trình từ danh sách trên cho mỗi dòng.
  - Viện dẫn: "theo NQ-116", "Quyết định BHXH", "quỹ BHTN"
  - Điều kiện: "Ban da du d!eu k!en" hoặc "da du dieu kien"
  - CTA: "Bam vao / Nhan tai [domain.icu hoặc .com]"
  - Cảnh báo deadline: "QUA HAN SE KH0NG DUOC CHAP NHAN"
  - Kết thúc bằng 4 ký tự random (ví dụ: hkDF, oZGa, SP0s – làm tracking ID giả)
  - Domain pattern: www.[5-6 ký tự ngẫu nhiên].icu hoặc mo.[random].com
  - Sender type: luôn là personal_number

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên domain/code, dùng làm tham chiếu style):
[T.B] BHXH: Ong (Ba) da du d!eu k!en NHAN T1EN h0 tro tu quy BH-TN. Bam vao www.mvndc.icu de lay. QUA HAN SE KH0NG_DUOC CHAP NHAN! oZGa|1|1|0|personal_number
Theo _NQ_116, Ong (Ba) da du d!eu k!en NHAN TIEN ho tro tu quy BHTN. Bam vao www.pwmgh.icu de lay. QUA HAN SE KHONG_DUOC CHAP NHAN! hkDF|1|1|0|personal_number
Ong/(Ba) da du d!eu'k!en NHAN'TIEN ho tro tu quy-BHTN. Bam'vao www.opaxa.icu de_'lay. QUA-HAN' SE KH0ng DUOC CHAP_NAHN! JKqc|1|1|0|personal_number
BHXH VN: Ong(Ba) DU DIEU KIEN nhan tien ho tro BHTN dot 3. Nhan tai: mo.cvxqa.com truoc khi QUA HAN. tPkm|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link domain.icu / mo.[random].com, 0 nếu không
  - sender_type = personal_number (luôn luôn)
  - 60–180 ký tự
  - Domain random chars phải KHÁC NHAU mỗi dòng (không lặp lại mvndc, pwmgh, opaxa, cvxqa từ ví dụ)
  - Mã xác nhận cuối (4 ký tự) KHÁC NHAU mỗi dòng, không dùng lại oZGa/hkDF/JKqc/tPkm từ ví dụ
  - Đa dạng TLD: ~70% .icu, ~30% .com (dạng mo.[random].com) trong cùng một batch
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.5 Prompt Template – Tuyển dụng giả (Đã thiết kế)

```python
JOB_SCAM_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn tuyển dụng giả mạo (label=1).
Nền tảng / Công ty bị giả mạo: {brands}
Chiến lược tâm lý: GREED (lương hấp dẫn, làm tại nhà) + URGENCY (tuyển gấp, số lượng hạn chế)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một công ty/nền tảng từ danh sách trên cho mỗi dòng. ĐẢM BẢO sự xen kẽ giữa các công ty.
  - Tên công ty/platform ở đầu câu: "{brands} cần tuyển..." hoặc "tôi là trưởng phòng {brands}..."
  - Thu nhập hàng ngày (KHÔNG dùng lương tháng đơn độc): "500k~3000k/ngày", "800.000đ/ngày",
    "350–999k/ngay"
  - Điều kiện dễ: "thao tác đơn giản", "không cần kinh nghiệm", "làm tại nhà"
  - Độ tuổi: "22–60 tuổi" hoặc "23–65 tuổi" (không quá 18, không dưới 65)
  - CTA Zalo: "Liên hệ Zalo: zalo.me/84xxxxxxxxx" hoặc số trực tiếp "Zalo: 84xxxxxxxxx"
  - Sender: personal_number (luôn luôn)
  - Sub-type tùy platform:
      * Amazon / eBay: "xử lý đơn đặt hàng TMĐT", Zalo link + số riêng (has_url=1, has_phone=1)
      * TikTok: "xử lý đơn hàng trên nền tảng TikTok", "nhận tiền sau 13–25 phút" (has_url=1, has_phone=1)
      * Shopee / Lazada: "xử lý đơn + đánh giá sản phẩm", chỉ Zalo link (has_url=1, has_phone=0)
      * Tiki: "đặt hàng để nâng thứ hạng cửa hàng", số Zalo trực tiếp (has_url=0, has_phone=1)
      * Cty generic (HVS, EMIME): "tuyển nhân viên bán thời gian", Zalo link + số riêng

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên số Zalo/SĐT, dùng làm tham chiếu style):
Amazon cần tuyển nhân viên làm việc tại nhà!!! Yêu cầu 23-60 tuổi. Lương 10tr-50tr/tháng. Ít nhất 500k~3000k/ngày, thao tác đơn giản. Liên hệ Zalo: zalo.me/84938271045 Zalo: 84938271045|1|1|1|personal_number
Xin chào, tôi là trưởng phòng nhân sự của Cty HVS, tuyển nhân viên bán thời gian. Thu nhập 15-30tr/tháng (500k-1tr/ngày). Làm tại nhà, mọi lúc mọi nơi. Tuổi 22-65. Zalo: zalo.me/84962183074 hoặc 84962183074|1|1|1|personal_number
Xin chào, mình là giám đốc marketing của Tiki. Cửa hàng Tiki đang tuyển số lượng lớn nhân viên chuyên đặt hàng để nâng cao số lượng giao dịch và thứ hạng cửa hàng. Chỉ cần có kinh nghiệm mua sắm trực tuyến, mỗi ngày bạn có thể dễ dàng kiếm 800.000đ bằng điện thoại di động. Lương quyết toán ngay trong ngày. Zalo: 84769231508|1|0|1|personal_number
Tiktok dang tuyen nhan vien lam viec tai nha!!! Mo ta cong viec: Xu ly don hang tren nen tang Tiktok. Thu nhap 350-999k/ngay. Thao tac don gian, nhan tien sau 13-25 phut. Lien he ngay: zalo.me/84937512094 zalo:84937512094|1|1|1|personal_number
Shopee tuyen gap nhan vien xu ly don hang va danh gia san pham tai nha!!! Yeu cau 22-55 tuoi. Thu nhap 500k-1.5tr/ngay. Nhan tien trong ngay sau moi nhiem vu hoan thanh. Khong can kinh nghiem, co nguoi huong dan cu the. Dang ky: zalo.me/84918273645|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url: 1 nếu có zalo.me/xxx link, 0 nếu chỉ có SĐT
  - has_phone: 1 nếu số điện thoại được liệt kê riêng trong text (không chỉ trong URL)
  - sender_type = personal_number (luôn luôn)
  - 80–250 ký tự
  - Phân biệt sub-type rõ ràng: KHÔNG toàn bộ cùng platform trong một batch
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.6 Prompt Template – Cờ bạc/ Betting (Đã thiết kế)

```python
GAMBLING_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn mời gọi cờ bạc/betting (label=1).
Nhà cái / Platform: {brands}
Chiến lược tâm lý: GREED (bonus khủng, rút tiền ngay) + FOMO (khuyến mãi có hạn)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một nhà cái từ danh sách trên cho mỗi dòng. 
  - Luôn có URL (has_url = 1 trong hầu hết trường hợp).
  - Sub-type (xen kẽ trong batch):
      * "nạp X nhận Y": "Nap Xk nhan Yk", "1 vong cuoc la rut MAXX X.XXXk",
        "No Hu", "Ban Ca", "BCR", tracking code 4–5 ký tự cuối, URL t.ly/[code]
      * Platform promo: "tai app", "x3 nap dau", list game bị dot-insert
        (TLMN, X.oc-D.ia, N.ohu), URL .cc/.tech domain
      * Casino formal: "Baccarat trực tiếp", "chọi gà", "xổ số", "CSKH 24/24",
        "gửi và rút trong X phút", short domain (5–6 ký tự .com)
      * Đại lý/hoa hồng: "tuyển đại lý", "hoa hồng X%", Zalo có số, URL .vip/.bet,
        sender = shortcode (đặc trưng duy nhất dùng shortcode)
  - Domain pattern: t.ly/[code] / .cc / .tech / .vip / .bet / [5–6char].com
  - Sender: personal_number (hầu hết), shortcode (chỉ với sub-type đại lý)

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên tracking code/domain/URL, dùng làm tham chiếu style):
Dang ky + 558k! (Nap 50k nhan 108k) 1 vong cuoc la rut MAXX 8.888k. No Hu. Ban Ca. BCR... DK: t.ly/DJyj1 ZnReS|1|1|0|personal_number
G.em moi Awin tag ban 299k khi tai app, x3 nap dau, rut ngay ko can nap, choi TLMN, X.oc-D.ia, N.ohu...dinhcao. click: https://athd.cc/5TyUoM|1|1|0|personal_number
Để chào mừng năm mới, Kim Long tặng ngay 68-888K khi đăng ký tại: d82yy.com, hãy liên hệ CSKH để nhận. Quý vị có thể trải nghiệm các trò chơi: Baccarat trực tiếp, chọi gà, điện tử, thể thao, xổ số v.v. Gửi và rút tiền trong vòng 3 phút, CSKH 24/24|1|1|0|personal_number
V7 top 3 nha cai VN, tuyen dai ly voi muc hoa hong len den 50%, tra hoa hong nhieu hinh thuc, lien he zalo Van: 0932187456 Link: https://v7bet.vip|1|1|1|shortcode
D/Ki + 558k. ( N-ap 5Ok nhän 1O8k ) 1 vong cuöc la rut MAXX 8.888k. Htra tuc thi 3%. N/ö h/ü - B/än C/ä. BCR... DK: ibvif.cc/LbFzDg ~noyc|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 (luôn luôn – đặc trưng của gambling scam)
  - has_phone: 1 chỉ với sub-type đại lý (có Zalo + SĐT), 0 còn lại
  - sender_type: personal_number hoặc shortcode (shortcode chỉ cho đại lý)
  - 40–180 ký tự
  - Tracking code cuối KHÁC NHAU mỗi dòng (KHÔNG copy từ few-shot)
  - Domain string KHÁC NHAU mỗi dòng (chỉ dùng TLD pattern, KHÔNG lặp full domain)
  - KHÔNG dùng brand name thật trong domain (ví dụ: 789bet.com → sai, dùng domain giả)
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.7 Prompt Template – Dịch vụ công (Đã thiết kế)

```python
GOVT_FAKE_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn giả mạo cơ quan nhà nước (label=1).
Cơ quan bị giả mạo: {brands}
Chiến lược tâm lý: FEAR (vi phạm pháp luật, bị xử phạt) + AUTHORITY (danh nghĩa nhà nước)
 
ĐẶC TRƯNG BẮT BUỘC:
  YÊU CẦU TRỘN BRAND: BẮT BUỘC chọn NGẪU NHIÊN một cơ quan từ danh sách trên cho mỗi dòng.
  - Mở đầu bằng tên cơ quan: "{brands}: ..." hoặc "[{brands.upper()}]" hoặc "Bộ ... xin thông báo"
  - Nội dung tùy sub-type:
      * CSGT / Bộ GTVT: "hồ sơ vi phạm giao thông", "biên lai chưa nộp phạt",
        "thông báo cuối cùng", CTA link hoặc SĐT
      * Tổng cục Thuế / Hoàn thuế: "đủ điều kiện hoàn thuế TNCN", link .vip/.top
      * VNeID / Bộ Công an: "cập nhật thông tin định danh", "xác thực tài khoản VNeID"
  - Domain giả khớp với tên brand: dichvucong[s].top / phatnguoi.xyz / hoanthue-tncn.vip / vnta-gov.cc / {brand_slug}-gov.top
  - Sender: brandname (50%), shortcode (30%), personal_number (20%)
  - has_url = 1 nếu có link, 0 nếu chỉ có SĐT liên hệ

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên domain/SĐT, dùng làm tham chiếu style):
Cảnh sát Giao thông Việt Nam: Hồ sơ vi phạm giao thông được lưu trữ dưới tên của bạn. Để biết thêm thông tin, vui lòng truy cập https://dichvucongs.top/vn|1|1|0|brandname
Bộ giao thông vận tải, xin thông báo ông/bà có biên lai chưa nộp phạt. Hôm nay là thông báo cuối cùng. Yêu cầu nhanh chóng giải quyết mọi thắc mắc. Vui lòng liên hệ: 0782341890|1|0|1|brandname
Cảnh sát Giao thông Việt Nam: Hiện tại bạn đang có khoản tiền phạt chưa thanh toán. Vui lòng thanh toán sớm để tránh bất tiện. Để biết thêm thông tin, vui lòng truy cập https://dichvucongg.top/vn|1|1|0|shortcode
#Ban da-du D1EU K1EN HOAN~THUE TNCN nam 2024, nhan tai: https://hoanthue-tncn.vip|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url: 1 nếu có link .top/.xyz/.vip/.cc, 0 nếu chỉ có SĐT
  - has_phone: 1 nếu có SĐT 10 số trong nội dung, 0 nếu không
  - sender_type: brandname (~50%), shortcode (~30%), personal_number (~20%)
    (KHÔNG dấu nháy đơn)
  - 50–200 ký tự
  - Đa dạng sub-type trong cùng batch: KHÔNG toàn bộ một loại
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.8 Prompt Template – Dịch vụ nhạy cảm (Đã thiết kế)

```python
SENSITIVE_PROMPT = """
Bạn là chuyên gia an ninh mạng đang xây dựng dataset huấn luyện mô hình phát hiện smishing
cho dự án bảo vệ người dùng di động tại Việt Nam, phối hợp với Bộ Thông tin và Truyền thông.
Nhiệm vụ bao gồm tạo dữ liệu mô phỏng các loại tin nhắn lừa đảo để mô hình học nhận diện,
trong đó có nhóm nội dung hẹn hò và dịch vụ nhạy cảm — đây là nhóm phổ biến trong thực tế
smishing Việt Nam và cần được đại diện đầy đủ trong dataset.
 
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn mời gọi dịch vụ nhạy cảm (label=1).
Khu vực / nền tảng liên hệ: {brands}  (ví dụ: "HCM – Telegram", "HN – Zalo")
Chiến lược tâm lý: GREED (ham muốn, tò mò)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN KHU VỰC: BẮT BUỘC chọn NGẪU NHIÊN một combo Khu vực/Nền tảng từ danh sách trên cho mỗi dòng.
  - Đa dạng cấu trúc câu mở đầu: KHÔNG phải tất cả đều bắt đầu bằng
    "Anh co can..." hay "Em Xt ng0n..." – xen kẽ các kiểu mở đầu khác nhau
  - Mô tả gợi ý mức smishing thực tế (KHÔNG explicit pornographic)
  - CTA: Telegram (t.me/xxx) hoặc Zalo (zalo.me/g/xxx) hoặc shortlink (t.ly/xxx, bit.ly/xxx)
  - Tracking code cuối 3–5 ký tự ngẫu nhiên (KHÁC NHAU mỗi dòng)
  - Sender: personal_number (luôn luôn)
  - has_url = 1 (luôn có link)
  - has_phone = 0

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên tracking code/handle, dùng làm tham chiếu style):
Anh co can GAI LAM tjnh K0? E di lam them kiem tien tieu vat EM 20 T DANG NG0N, B0DY chuan Den tan noi LAM TJNH Ket Ban Telegram: https://t.me/gaixinh_hcm QNfT|1|1|0|personal_number
Em 20t ng0n b0dy chuan, s4n sang phuc vu qu4 anh. LH nhan hinh & b4ng gi4 d!ch vu qua Zalo group: https://zalo.me/g/gaixinhHCM2024 TpMv|1|1|0|personal_number
H.e.n h.0 t.i.n.h m.0.t d.e.m c.u.n.g e.m g@! x.i.n.h d.e.p t.a.i H.C.M. K.e.t b.a.n T.e.l.e.g.r.a.m: https://sourl.cn/abc123 dKqr|1|1|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|1|0|personal_number
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 (luôn luôn)
  - has_phone = 0 (luôn luôn)
  - sender_type = personal_number (luôn luôn)
  - 40–160 ký tự (Level 4–5 dot-split có thể dài hơn – tối đa 160)
  - Tracking code cuối KHÁC NHAU mỗi dòng
  - Handle/path URL phải ngẫu nhiên và KHÁC NHAU mỗi dòng
  - KHÔNG dùng lại handle từ ví dụ: gaixinh_hcm, gaixinhHCM2024
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
"""
```

### 7.9 Prompt Template – Đầu tư/ Crypto (Đã thiết kế)

```python
CRYPTO_FAKE_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn đầu tư/kiếm tiền online giả (label=1).
Kịch bản: {brands}
Chiến lược tâm lý: GREED (thu nhập thụ động, dễ dàng, không cần vốn)
 
ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN KỊCH BẢN: BẮT BUỘC chọn NGẪU NHIÊN một kịch bản từ danh sách trên cho mỗi dòng.
  - Điểm nhấn: "chỉ cần X phút/ngày", "không cần vốn/kinh nghiệm",
    "kiếm X00k–Xtr mỗi ngày", "giáo viên/chuyên viên hướng dẫn"
  - Sub-type (chọn ngẫu nhiên mỗi dòng):
      * "thả tim / bình luận": 10 nhiệm vụ/ngày, 100k/ngày, trả cuối ngày (has_url=0)
      * "nhiệm vụ Telegram": giáo viên hướng dẫn, Telegram group link (has_url=1)
      * "chuyển khoản đầu tư": tên công ty đầu tư giả, STK ngân hàng, không link (has_url=0)
  - Tone: thân thiện, tự nhiên như người quen nhắn tin (KHÔNG formal, KHÔNG all-caps)
  - Sender: personal_number (luôn luôn)
  - has_phone = 0 (không dùng SĐT để liên hệ)

PHONG CÁCH NHIỄU – YÊU CẦU BẮT BUỘC:
Bạn phải sinh ra các dòng với mức độ nhiễu (teencode) ĐA DẠNG, trộn lẫn ngẫu nhiên giữa các mức sau đây. Phân bổ đều số lượng các dòng cho mỗi mức:
{style}
 
VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên handle/STK, dùng làm tham chiếu style):
Chào bạn, mình là Hùng, chuyên viên hỗ trợ. Bạn đang muốn làm công việc thả tim video kiếm tiền bên mình đúng không? Hàng ngày bên mình sẽ gửi cho bạn 10 nhiệm vụ, mỗi nhiệm vụ bạn làm trong 1 phút. Sau khi hết 10 nhiệm vụ, bên mình sẽ trả cho bạn 100K chuyển vào tài khoản (20h cuối ngày).|1|0|0|personal_number
Chi cän 2O phut möi ngäy giäo vien chuyen nghiep cö the huong dän ban kiem 500k-3000k, Them Telegram: t.me/huongnghieptainha01|1|1|0|personal_number
Anh/chi hay chuyen so tien can nap vao tai khoan sau, sau do chup man hinh em se lam lenh nap vao tai khoan dau tu CSI ngay. NH MSB STK: 04001023847291 TK: CONG TY TNHH DAU TU BDS SSG|1|0|0|personal_number
 
QUY TẮC FORMAT (pipe-delimited):
  content|1|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url: 1 nếu có Telegram link (t.me/xxx), 0 nếu không có link
  - has_phone = 0 (luôn luôn)
  - sender_type = personal_number (luôn luôn)
  - 40–220 ký tự
  - Đa dạng sub-type trong cùng batch: KHÔNG toàn bộ một loại
 
QUAN TRỌNG: Đúng {size} dòng pipe-delimited (dùng | làm delimiter). Không header. Không giải thích. Không markdown.
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
4. **Luôn dùng đầy đủ 5 cột**: Few-shot example phải là dòng pipe-delimited hoàn chỉnh `content|label|has_url|has_phone_number|sender_type`, **không chỉ riêng content** – model cần thấy ground truth của tất cả cột để học cách điền đúng metadata

```
Lý do cần đủ 5 cột:
  ❌ Chỉ cung cấp content:
     VCB Digibank tran trong...www.vcbtiebink.com...
     → Model không có cơ sở để điền has_url, sender_type
     → Có thể sinh: ...|1|0|0|personal_number  (sai has_url, sai sender_type)

  ✅ Cung cấp đầy đủ dòng pipe-delimited:
     VCB Digibank tran trong...www.vcbtiebink.com|1|1|0|brandname
     → Model học: URL present → has_url=1; bank impersonation → brandname
     → Sinh đúng nhất quán cho toàn batch

Lý do dùng pipe | thay vì CSV dấu phẩy:
  ❌ CSV với dấu phẩy: "Nhấp vào ""link"" này",1,1,0,brandname
     → LLM thường không escape đúng RFC 4180 → parse error
     → Content chứa dấu phẩy cần wrap quotes → LLM hay bỏ sót

  ✅ Pipe-delimited: Nhấp vào "link" này|1|1|0|brandname
     → Không cần escape, không cần wrap quotes
     → gen_label_1.py parse bằng split("|") → re-serialize bằng csv.writer → RFC 4180
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
  Input row: VCB Digibank tran trong thong bao.tai khoan cua quy khach hien tai da bi khoa.Dang nhap www.vcbtiebink.com de xac thuc ngay hom nay|1|1|0|brandname

✅ Candidate 2 (brandname + greed + Level 1):
  Input row: Vietcombank lưu ý: Bạn có 18699 điểm thưởng sẽ hết hạn sau 24 giờ, vui lòng truy cập: https://vietcombankd.cfd/vn để đổi quà.|1|1|0|brandname

✅ Candidate 3 (brandname + fear + Level 2):
  Input row: UNG DUNG VCB DIGIBANK cua ban duoc PHAT HIEN KICH HOAT tren thiet bi la. Neu KHONG PHA BAN KICH HOAT vui long bam vao https://vietcombank.vn-ms.top de doi thiet bi hoac huy de tranh mat tai san|1|1|0|brandname

✅ Quyết định: Dùng cả 3 candidates trên làm few-shot cho Banking Fraud prompt.
   - Brand name (VCB, Vietcombank) giữ nguyên trong few-shot → calibrate style cụ thể từng bank
   - Dùng biến {brand} ở phần Task Specification để generalize sang bank khác
   - Domain giả trong content (.vcbtiebink.com, .cfd, .vn-ms.top) giữ nguyên → đây là fake domain, không phải thông tin cá nhân thật
```

### 8.3 Candidates cho BHXH Scam Examples

```
✅ Candidate 1 (Level 2, random code, TLD .icu):
  [T.B] BHXH: Ong (Ba) da du d!eu k!en NHAN T1EN h0 tro tu quy BH-TN. Bam vao www.mvndc.icu de lay. QUA HAN SE KH0NG_DUOC CHAP NHAN! oZGa|1|1|0|personal_number

✅ Candidate 2 (Level 3, NQ-116, TLD .icu):
  Theo _NQ_116, Ong (Ba) da du d!eu k!en NHAN TIEN ho tro tu quy BHTN. Bam vao www.pwmgh.icu de lay. QUA HAN SE KHONG_DUOC CHAP NHAN! hkDF|1|1|0|personal_number

✅ Candidate 3 (Level 1, với dấu, TLD .icu):
  Ong/(Ba) da du d!eu'k!en NHAN'TIEN ho tro tu quy-BHTN. Bam'vao www.opaxa.icu de_'lay. QUA-HAN' SE KH0ng DUOC CHAP_NAHN! JKqc|1|1|0|personal_number

✅ Candidate 4 (Level 2, TLD .com – biến thể mo.[random].com):
  BHXH VN: Ong(Ba) DU DIEU KIEN nhan tien ho tro BHTN dot 3. Nhan tai: mo.cvxqa.com truoc khi QUA HAN. tPkm|1|1|0|personal_number
```

> **Phân tích domain overlap:** Cả 4 candidates đều dùng domain pattern ngẫu nhiên – đây là **Level A overlap** (pattern trùng, string khác) và là chủ ý đúng đắn, phản ánh thực tế scammer dùng random subdomain. Điều quan trọng hơn là **string domain không được trùng nhau** (Level B) trong cùng một batch sinh ra.
>
> **Hai loại overlap cần phân biệt:**
>
> - `Level A` – Nhiều messages cùng dùng TLD `.icu` với random chars khác nhau → **Chấp nhận được**, thậm chí đúng thực tế. Dạy model: `.icu` + random chars = đặc trưng smishing
> - `Level B` – Cùng string `www.mvndc.icu` xuất hiện nhiều lần trong batch → **Gây hại**: với TF-IDF, string đó trở thành high-weight feature; model học chuỗi cụ thể thay vì học pattern tổng quát
>
> **Rủi ro thực sự lớn hơn domain overlap:**
>
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


| Candidate | Platform            | Kiểu lừa đảo                     | sender_type     | has_url | has_phone | Level |
| --------- | ------------------- | -------------------------------- | --------------- | ------- | --------- | ----- |
| C1        | Amazon              | xử lý đơn TMĐT + Zalo link       | personal_number | 1       | 1         | 0     |
| C2        | Cty HVS (generic)   | tuyển bán thời gian, formal      | personal_number | 1       | 1         | 0     |
| C3        | **Tiki**            | đặt đơn nâng rank cửa hàng       | personal_number | 0       | 1         | 0     |
| C4        | **TikTok**          | xử lý đơn + nhận tiền 13–25 phút | personal_number | 1       | 1         | 1     |
| C5        | **Shopee / Lazada** | xử lý đơn + đánh giá sản phẩm    | personal_number | 1       | 0         | 0     |


```
✅ Candidate 1 (Amazon, Zalo link + greed, Level 0, has_url=1, has_phone=1):
  Amazon cần tuyển nhân viên làm việc tại nhà!!! Yêu cầu 23-60 tuổi. Lương 10tr-50tr/tháng. Ít nhất 500k~3000k/ngày, thao tác đơn giản. Liên hệ Zalo: zalo.me/84938271045 Zalo: 84938271045|1|1|1|personal_number

✅ Candidate 2 (Cty HVS generic, formal style, Level 0, has_url=1, has_phone=1):
  Xin chào, tôi là trưởng phòng nhân sự của Cty HVS, tuyển nhân viên bán thời gian. Thu nhập 15-30tr/tháng (500k-1tr/ngày). Làm tại nhà, mọi lúc mọi nơi. Tuổi 22-65. Zalo: zalo.me/84962183074 hoặc 84962183074|1|1|1|personal_number

✅ Candidate 3 (Tiki "đặt đơn nâng rank", Level 0, has_url=0, has_phone=1):
  Xin chào, mình là giám đốc marketing của Tiki. Cửa hàng Tiki đang tuyển số lượng lớn nhân viên chuyên đặt hàng để nâng cao số lượng giao dịch và thứ hạng cửa hàng. Chỉ cần có kinh nghiệm mua sắm trực tuyến, mỗi ngày bạn có thể dễ dàng kiếm 800.000đ bằng điện thoại di động. Lương quyết toán ngay trong ngày. Zalo: 84769231508|1|0|1|personal_number

✅ Candidate 4 (TikTok "xử lý đơn hàng", Level 1 – bỏ dấu, has_url=1, has_phone=1):
  Tiktok dang tuyen nhan vien lam viec tai nha!!! Mo ta cong viec: Xu ly don hang tren nen tang Tiktok. Thu nhap 350-999k/ngay. Thao tac don gian, nhan tien sau 13-25 phut. Lien he ngay: zalo.me/84937512094 zalo:84937512094|1|1|1|personal_number

✅ Candidate 5 (Shopee / Lazada "xử lý đơn + đánh giá SP", Level 0, has_url=1, has_phone=0):
  Shopee tuyen gap nhan vien xu ly don hang va danh gia san pham tai nha!!! Yeu cau 22-55 tuoi. Thu nhap 500k-1.5tr/ngay. Nhan tien trong ngay sau moi nhiem vu hoan thanh. Khong can kinh nghiem, co nguoi huong dan cu the. Dang ky: zalo.me/84918273645|1|1|0|personal_number
```

> **Phân tích đặc trưng từng platform (trích từ `dataset_label_1.csv`):**
>
>
> | Platform          | Từ khoá đặc trưng                                                                            | Lương           | Contact pattern                     |
> | ----------------- | -------------------------------------------------------------------------------------------- | --------------- | ----------------------------------- |
> | **Amazon**        | "xử lý đơn đặt hàng từ nền tảng thương mại điện tử", "thao tác đơn giản và hướng dẫn đi kèm" | 500k~3000k/ngày | Zalo link + số riêng                |
> | **Tiki**          | "đặt hàng để nâng cao số lượng giao dịch và thứ hạng", "kinh nghiệm mua sắm trực tuyến"      | 800.000đ/ngày   | Số Zalo trực tiếp (không Zalo link) |
> | **TikTok**        | "Xử lý đơn hàng từ nền tảng ứng dụng", "nhận tiền sau 13–25 phút"                            | 350–999k/ngày   | Zalo link + số riêng                |
> | **Shopee/Lazada** | "xử lý đơn + đánh giá sản phẩm", "nâng thứ hạng cửa hàng"                                    | 500k–1.5tr/ngày | Zalo link (số không liệt kê riêng)  |
>
>
> **Lưu ý `has_phone` vs `has_url`:** Khi số điện thoại chỉ nằm trong path của Zalo URL (`zalo.me/84xxx`) và không được liệt kê lại riêng trong văn bản → `has_phone=0`, `has_url=1`. Khi số được liệt kê lại sau link hoặc trực tiếp trong text → `has_phone=1`.

> ⚠️ **Anonymization note**: Tất cả số điện thoại đã được thay bằng số giả đúng format (84 + 9 chữ số). Xem nguyên tắc tại **Section 8.6**.
>
> **Candidates KHÔNG đưa vào few-shot** (quá gần với candidates khác):
>
> - eBay "xử lý đơn": cùng pattern với Amazon, chỉ khác brand → dùng `{brand}` variable thay thế
> - TikTok "bình luận/thả tim": pattern đặc biệt (has_url=0, has_phone=1, ngắn) → phù hợp cho Crypto/Đầu tư category hơn

### 8.5 Candidates cho Gambling Scam Examples

**Coverage Matrix:**


| Candidate | Style                          | Obf Level | URL type                 | sender_type     | Unique pattern                          |
| --------- | ------------------------------ | --------- | ------------------------ | --------------- | --------------------------------------- |
| C1        | "nạp X nhận Y", No Hũ / Bắn Cá | 1         | t.ly                     | personal_number | Tracking code cuối (ZnReS)              |
| C2        | App promo, platform list       | 2         | .cc domain (athd.cc)     | personal_number | Dot-inserted text, "G.em moi Awin"      |
| C3        | Casino formal, CSKH 24/24      | 0         | short domain (d82yy.com) | personal_number | Baccarat/chọi gà/xổ số, full Vietnamese |
| C4        | Đại lý / hoa hồng recruit      | 1         | .vip domain              | **shortcode**   | "tuyển đại lý", hoa hồng 50%, Zalo      |
| C5        | Slash-dash obfuscation nặng    | 3         | .cc domain (ibvif.cc)    | personal_number | D/Ki, N-ap, N/ö h/ü, B/än C/ä pattern   |


```
✅ Candidate 1 (Level 1, t.ly, tracking code, personal_number):
  Dang ky + 558k! (Nap 50k nhan 108k) 1 vong cuoc la rut MAXX 8.888k. No Hu. Ban Ca. BCR... DK: t.ly/DJyj1 ZnReS|1|1|0|personal_number

✅ Candidate 2 (Level 2, .cc domain, dotted-platform list, personal_number):
  G.em moi Awin tag ban 299k khi tai app, x3 nap dau, rut ngay ko can nap, choi TLMN, X.oc-D.ia, N.ohu...dinhcao. click: https://athd.cc/5TyUoM|1|1|0|personal_number

✅ Candidate 3 (Level 0, casino formal, short domain, personal_number):
  Để chào mừng năm mới, Kim Long tặng ngay 68-888K khi đăng ký tại: d82yy.com, hãy liên hệ CSKH để nhận. Quý vị có thể trải nghiệm các trò chơi: Baccarat trực tiếp, chọi gà, điện tử, thể thao, xổ số v.v. Gửi và rút tiền trong vòng 3 phút, CSKH 24/24|1|1|0|personal_number

✅ Candidate 4 (Level 1, .vip domain, đại lý/hoa hồng recruit, shortcode):
  V7 top 3 nha cai VN, tuyen dai ly voi muc hoa hong len den 50%, tra hoa hong nhieu hinh thuc, lien he zalo Van: 0932187456 Link: https://v7bet.vip|1|1|1|shortcode

✅ Candidate 5 (Level 3, slash-dash obfuscation, .cc domain, personal_number):
  D/Ki + 558k. ( N-ap 5Ok nhän 1O8k ) 1 vong cuöc la rut MAXX 8.888k. Htra tuc thi 3%. N/ö h/ü - B/än C/ä. BCR... DK: ibvif.cc/LbFzDg ~noyc|1|1|0|personal_number
```

> **Phân tích đặc trưng từng sub-type (trích từ `dataset_label_1.csv`):**
>
>
> | Sub-type                | Từ khoá đặc trưng                                                 | URL pattern               | sender_type     |
> | ----------------------- | ----------------------------------------------------------------- | ------------------------- | --------------- |
> | **"nạp X nhận Y"**      | "nap Xk nhan Yk", "No Hu", "Ban Ca", "1 vong cuoc la rut MAXX"    | t.ly/[code]               | personal_number |
> | **Platform promo**      | "tai app", "x3 nap dau", "TLMN, Xoc Dia, Nohu"                    | .cc / .tech domain        | personal_number |
> | **Casino formal**       | "Baccarat trực tiếp", "CSKH 24/24", "gửi/rút trong 3 phút"        | short domain (d82yy, k98) | personal_number |
> | **Đại lý/hoa hồng**     | "tuyển đại lý", "hoa hồng X%", "trả hoa hồng nhiều hình thức"     | .vip / .bet domain        | **shortcode**   |
> | **Extreme obfuscation** | D/Ki, N-ap, slash/dash split trên mọi từ, ký tự diacritic lẫn lộn | .cc / ibvif.cc            | personal_number |
>
>
> **Lưu ý chọn few-shot cho một batch cụ thể:**
>
> - Nếu prompt target "nổ hũ / bắn cá": dùng C1 + C5 (cùng "558k" pattern nhưng khác obfuscation level)
> - Nếu prompt target "casino đa dạng game": dùng C3 + C2
> - Nếu prompt target "đại lý/affiliate": dùng C4 là đủ (pattern rất khác biệt so với các loại khác)

> ⚠️ **Anonymization note**: Số điện thoại C4 (`0935123456` trong real data) đã được thay bằng `0932187456`. Domain và tracking code giữ nguyên – đây là thông tin giả/hết hiệu lực của scammer.

### 8.6 Nguyên tắc Anonymization trong Few-Shot Examples

Few-shot examples được trích từ data thực nên có thể chứa thông tin cá nhân. Quy tắc xử lý:


| Loại thông tin                                             | Quyết định                           | Cách xử lý đúng                                            |
| ---------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------- |
| **Brand name thật** (VCB, Vietcombank, BIDV)               | **Giữ nguyên**                       | Không thay đổi – dùng để calibrate style cụ thể từng brand |
| **Domain giả trong content** (.vcbtiebink.com, .vn-ms.top) | **Giữ nguyên**                       | Đây là fake domain bịa đặt, không phải thông tin cá nhân   |
| **Số điện thoại scammer** (trong Zalo link, nội dung)      | **Thay bằng số giả đúng format**     | Format VN: `84` + 9 chữ số (ví dụ: `84938271045`)          |
| **Tên người thật** (trong debt scam, job scam)             | **Thay bằng tên Việt giả hoàn toàn** | Ví dụ: Nguyễn Văn A → Trần Minh Khoa                       |
| **CMND/CCCD thật**                                         | **Thay bằng số giả đúng format**     | 9 hoặc 12 chữ số ngẫu nhiên                                |


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

### 8.7 Candidates cho Debt/Threat Examples (Cat 2)

**Coverage Matrix:**


| Candidate | Style                                            | Obf Level | has_url | has_phone | sender_type     | Unique pattern                  |
| --------- | ------------------------------------------------ | --------- | ------- | --------- | --------------- | ------------------------------- |
| C1        | CANH BAO LAN CUOI, tên + CMND + SĐT Zalo         | 0         | 0       | 1         | personal_number | Đe dọa công khai MXH + gia đình |
| C2        | Trung tâm tín dụng formal, số tiền + % tối thiểu | 0         | 0       | 0         | personal_number | Hai mức tiền: gốc + tối thiểu   |
| C3        | Phòng AN NINH ĐIỀU TRA, deadline giờ cụ thể      | 1         | 0       | 0         | personal_number | "chiu trach nhiem hinh su"      |


```
✅ Candidate 1 (CANH BAO LAN CUOI, tên + CMND + SĐT, Level 0, has_url=0, has_phone=1):
  CANH BAO LAN CUOI!!! Trong 24H nua Ong/Ba Nguyen Thi Lan CMND: 046079231845 phai lien he gap SDT/ZALO: 0352891743 gap Tran Van Duc de THOA THUAN-GIAM NO. Neu KHONG HOP TAC thanh toan KHOAN VAY 3,947,000VND se Cong Khai HINH ANH va THONG TIN len XA HOI, DIA PHUONG va thong bao nguoi than.|1|0|1|personal_number

✅ Candidate 2 (Trung tâm tín dụng formal, 2 mức tiền, Level 0, has_url=0, has_phone=0):
  Trung Tam Tin Dung F&TB den Ong/Ba: So CMND: 024091768345. Chung toi nghi ngo Ong/Ba lam dung tin nhiem chiem doat tai san voi so tien: 48,554,336VND (tien goc). Canh bao lan cuoi truoc 16H Ngay 25/03 thanh toan toi thieu: 3,725,583VND. Tiep tuc bat hop tac, moi rui ro ve Uy tin Danh du Tai san Ong/Ba tu chiu.|1|0|0|personal_number

✅ Candidate 3 (Phòng AN NINH ĐIỀU TRA, deadline giờ, Level 1, has_url=0, has_phone=0):
  [CANH CAO LAN CUOI]: Chung toi da nhac nho nhieu lan nhung O/B van bat hop tac. Truoc 17g hom nay chua thanh toan, Phong AN NINH DIEU TRA se vao cuoc dieu tra toan bo thong tin hinh anh cua O/B va nhung nguoi lien quan se phai chiu trach nhiem hinh su. LH khi san sang: 84912654378.|1|0|0|personal_number
```

> **Phân tích đặc trưng (trích từ `dataset_label_1.csv` rows 6, 41, 155, 156):**
>
>
> | Pattern                  | Từ khoá đặc trưng                                                         | has_url | has_phone                |
> | ------------------------ | ------------------------------------------------------------------------- | ------- | ------------------------ |
> | **Công ty tài chính**    | "CANH BAO LAN CUOI", tên người + CMND, số tiền không tròn, deadline giờ   | 0       | 1 (SĐT Zalo local 10 số) |
> | **Trung tâm tín dụng**   | "Trung Tam Tin Dung", 2 mức tiền (gốc + tối thiểu), "tu chiu trach nhiem" | 0       | 0                        |
> | **Cơ quan điều tra giả** | "Phong AN NINH DIEU TRA", "chiu trach nhiem hinh su", deadline giờ        | 0       | 0                        |
>
>
> **Lưu ý `has_phone`:** SĐT local 10 số (0xxxxxxxxx) trong nội dung → `has_phone=1`. SĐT dạng quốc tế (84xxxxxxxxx) → `has_phone=0` theo convention của `dataset_label_1.csv`.

> ⚠️ **Anonymization note**: Tên người (Lê Hoàng Nam → Nguyen Thi Lan, Nguyen Van Tai → Tran Van Duc), CMND (079095012345 → 046079231845), SĐT (0901234567 → 0352891743) đã được thay hoàn toàn. SĐT trong C3 dùng format quốc tế `84xxxxxxxxx` theo đúng row 6 gốc.

---

### 8.8 Candidates cho Government Fake Examples (Cat 6)

**Coverage Matrix:**


| Candidate | Cơ quan       | Sub-type                               | sender_type     | has_url | has_phone | Level |
| --------- | ------------- | -------------------------------------- | --------------- | ------- | --------- | ----- |
| C1        | CSGT          | Hồ sơ vi phạm + link .top              | brandname       | 1       | 0         | 0     |
| C2        | Bộ GTVT       | Biên lai phạt + SĐT                    | brandname       | 0       | 1         | 0     |
| C3        | CSGT          | Tiền phạt chưa thanh toán + link .top  | shortcode       | 1       | 0         | 0     |
| C4        | Tổng cục Thuế | Hoàn thuế TNCN + link .vip, obfuscated | personal_number | 1       | 0         | 2     |


```
✅ Candidate 1 (CSGT + link .top, Level 0, has_url=1, has_phone=0, brandname):
  Cảnh sát Giao thông Việt Nam: Hồ sơ vi phạm giao thông được lưu trữ dưới tên của bạn. Để biết thêm thông tin, vui lòng truy cập https://dichvucongs.top/vn|1|1|0|brandname

✅ Candidate 2 (Bộ GTVT + biên lai + SĐT, Level 0, has_url=0, has_phone=1, brandname):
  Bộ giao thông vận tải, xin thông báo ông/bà có biên lai chưa nộp phạt. Hôm nay là thông báo cuối cùng. Yêu cầu nhanh chóng giải quyết mọi thắc mắc. Vui lòng liên hệ: 0782341890|1|0|1|brandname

✅ Candidate 3 (CSGT + tiền phạt + link .top, Level 0, has_url=1, has_phone=0, shortcode):
  Cảnh sát Giao thông Việt Nam: Hiện tại bạn đang có khoản tiền phạt chưa thanh toán. Vui lòng thanh toán sớm để tránh bất tiện. Để biết thêm thông tin, vui lòng truy cập https://dichvucongg.top/vn|1|1|0|shortcode

✅ Candidate 4 (Hoàn thuế TNCN + link .vip, Level 2 obfuscated, has_url=1, has_phone=0, personal_number):
  #Ban da-du D1EU K1EN HOAN~THUE TNCN nam 2024, nhan tai: https://hoanthue-tncn.vip|1|1|0|personal_number
```

> **Phân tích đặc trưng (trích từ `dataset_label_1.csv` rows 14, 60, 63, 113, 87, 119):**
>
>
> | Sub-type             | Từ khoá đặc trưng                                             | Domain pattern      | sender               |
> | -------------------- | ------------------------------------------------------------- | ------------------- | -------------------- |
> | **CSGT**             | "hồ sơ vi phạm giao thông", "khoản tiền phạt chưa thanh toán" | dichvucong[s/g].top | brandname, shortcode |
> | **Bộ GTVT**          | "biên lai chưa nộp phạt", "thông báo cuối cùng", SĐT liên hệ  | (không có link)     | brandname            |
> | **Thuế / Hoàn thuế** | "đủ điều kiện hoàn thuế TNCN", obfuscation Level 2+           | hoanthue-tncn.vip   | personal_number      |
>

> ⚠️ **Anonymization note**: C2 phone `0782320830` (real data row 14) đã được thay bằng `0782341890`. C1, C3, C4 không có thông tin cá nhân – dùng nguyên từ real data.

---

### 8.9 Candidates cho Sensitive Content Examples (Cat 7)

**Coverage Matrix:**


| Candidate | Sub-type                     | Obf Level | Platform            | sender_type     | Unique pattern          |
| --------- | ---------------------------- | --------- | ------------------- | --------------- | ----------------------- |
| C1        | Hẹn hò / dịch vụ, leet nặng  | 3         | Telegram            | personal_number | tjnh, K0, NG0N, B0DY    |
| C2        | Hẹn hò / dịch vụ, vowel-leet | 3         | Zalo group          | personal_number | s4n sang, hi4nh, gi4    |
| C3        | Dot-split extreme            | 4         | Telegram (sourl.cn) | personal_number | h.e.n h.0 tách từng chữ |


```
✅ Candidate 1 (Level 3, Telegram t.me, leet substitution, personal_number):
  Anh co can GAI LAM tjnh K0? E di lam them kiem tien tieu vat EM 20 T DANG NG0N, B0DY chuan Den tan noi LAM TJNH Ket Ban Telegram: https://t.me/gaixinh_hcm QNfT|1|1|0|personal_number

✅ Candidate 2 (Level 3, Zalo group link, vowel-leet style, personal_number):
  Em 20t ng0n b0dy chuan, s4n sang phuc vu qu4 anh. LH nhan hinh & b4ng gi4 d!ch vu qua Zalo group: https://zalo.me/g/gaixinhHCM2024 TpMv|1|1|0|personal_number

✅ Candidate 3 (Level 4, dot-split obfuscation, shortlink, personal_number):
  H.e.n h.0 t.i.n.h m.0.t d.e.m c.u.n.g e.m g@! x.i.n.h d.e.p t.a.i H.C.M. K.e.t b.a.n T.e.l.e.g.r.a.m: https://sourl.cn/abc123 dKqr|1|1|0|personal_number
```

> **Phân tích đặc trưng (trích từ `dataset_label_1.csv` row 52 + Section 4.1):**
>
>
> | Pattern           | Obf technique                     | Platform           | Tracking code       |
> | ----------------- | --------------------------------- | ------------------ | ------------------- |
> | Leet substitution | j=t, K0=không, NG0N, B0DY         | Telegram (t.me)    | Có (3–5 ký tự cuối) |
> | Vowel-number      | 4=a, i4nh, gi4                    | Zalo group         | Có                  |
> | Dot-split         | mỗi ký tự cách nhau bằng dấu chấm | Telegram/shortlink | Có                  |
>
>
> **Lưu ý an toàn:** Candidates ở Level 3–4 đủ đặc trưng để model nhận dạng pattern nhưng không chứa nội dung explicit. Phù hợp với safety framing của prompt (nghiên cứu bảo mật).

> ⚠️ **Anonymization note**: C1 dùng nguyên từ real data row 52 (Telegram handle là thông tin giả/hết hiệu lực). C2, C3 được tổng hợp từ pattern thực tế vì real data không có đủ đa dạng sub-type.

---

### 8.10 Candidates cho Crypto/Investment Examples (Cat 8)

**Coverage Matrix:**


| Candidate | Sub-type                            | Obf Level | has_url | has_phone | sender_type     | Unique pattern                     |
| --------- | ----------------------------------- | --------- | ------- | --------- | --------------- | ---------------------------------- |
| C1        | Thả tim / 10 nhiệm vụ/ngày          | 0         | 0       | 0         | personal_number | Tone thân thiện, trả 20h cuối ngày |
| C2        | Giáo viên hướng dẫn + Telegram      | 2         | 1       | 0         | personal_number | "20 phút/ngày", 500k–3000k         |
| C3        | Chuyển khoản đầu tư + STK ngân hàng | 0         | 0       | 0         | personal_number | Tên công ty giả + số tài khoản     |


```
✅ Candidate 1 (thả tim / nhiệm vụ, Level 0, has_url=0, has_phone=0, personal_number):
  Chào bạn, mình là Hùng, chuyên viên hỗ trợ. Bạn đang muốn làm công việc thả tim video kiếm tiền bên mình đúng không? Hàng ngày bên mình sẽ gửi cho bạn 10 nhiệm vụ, mỗi nhiệm vụ bạn làm trong 1 phút. Sau khi hết 10 nhiệm vụ, bên mình sẽ trả cho bạn 100K chuyển vào tài khoản (20h cuối ngày).|1|0|0|personal_number

✅ Candidate 2 (giáo viên + Telegram, Level 2 – vowel substitution, has_url=1, has_phone=0, personal_number):
  Chi cän 2O phut möi ngäy giäo vien chuyen nghiep cö the huong dän ban kiem 500k-3000k, Them Telegram: t.me/huongnghieptainha01|1|1|0|personal_number

✅ Candidate 3 (chuyển khoản đầu tư giả, Level 0, has_url=0, has_phone=0, personal_number):
  Anh/chi hay chuyen so tien can nap vao tai khoan sau, sau do chup man hinh em se lam lenh nap vao tai khoan dau tu CSI ngay. NH MSB STK: 04001023847291 TK: CONG TY TNHH DAU TU BDS SSG|1|0|0|personal_number
```

> **Phân tích đặc trưng (trích từ `dataset_label_1.csv` rows 120, 135, 190, 191):**
>
>
> | Sub-type                 | Từ khoá đặc trưng                                             | has_url | Tone                           |
> | ------------------------ | ------------------------------------------------------------- | ------- | ------------------------------ |
> | **Thả tim / nhiệm vụ**   | "10 nhiệm vụ", "1 phút/nhiệm vụ", "100K", "trả 20h cuối ngày" | 0       | Thân thiện, như bạn bè         |
> | **Giáo viên + Telegram** | "20 phút/ngày", "giáo viên chuyên nghiệp", "500k–3000k"       | 1       | Nhẹ obfuscation                |
> | **Chuyển khoản đầu tư**  | Tên công ty + STK ngân hàng, "lệnh nạp vào tài khoản"         | 0       | Formal, hướng dẫn step-by-step |
>
>
> **Phân biệt với Job Scam (Cat 4):** Crypto/Đầu tư KHÔNG đề cập nền tảng TMĐT (Shopee, TikTok Shop), KHÔNG có Zalo phone contact, thu nhập được frame là "đầu tư / nhiệm vụ" thay vì "lương tháng".

> ⚠️ **Anonymization note**: C1 và C3 dùng nguyên từ real data (rows 135, 120). C2 Telegram handle được thay từ handle thật (`t.me/Nguyenthingocthuy00`) bằng handle giả (`t.me/huongnghieptainha01`). STK ngân hàng C3 giữ nguyên – đây là tài khoản của scammer, không phải nạn nhân.

---

## 9. Checklist đánh giá chất lượng

### 9.1 Format Validation (sau khi đã đủ data - hiện chưua kiểm tra)

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

- Content có giống smishing thực tế không? (không quá "polished")
- Obfuscation style đúng với level yêu cầu không?
- Domain URL trông như domain giả mạo không?
- Chiến lược tâm lý (fear/greed/urgency) được thể hiện rõ không?
- sender_type có khớp với loại smishing không?
- Nội dung không lặp lại với mẫu khác trong batch?

### 9.3 Distribution Check (sau khi thu thập đủ data - hiện chưa triển khai)

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

### 10.1 Sprint 1 – Xây dựng nền tảng (Đã hoàn thành)

- **[P0]** Chọn và xây dựng few-shot library cho tất cả 8 categories (Sections 8.2–8.5, 8.7–8.10)
- **[P0]** Thiết kế BHXH prompt draft (Section 7.3)
- **[P0]** Thiết kế Debt/Threat prompt draft (Section 7.4)
- **[P0]** Thiết kế Dịch vụ công prompt draft (Section 7.5)
- **[P0]** Thiết kế Nội dung nhạy cảm prompt draft (Section 7.6)
- **[P0]** Thiết kế Crypto/Đầu tư prompt draft (Section 7.7)
- **[P0]** Map đầy đủ 8 Category trong `gen_label_1.py` (`SCENARIOS` dictionary)
- **[P0]** Phân tích anonymization rules (Section 8.6)

**Trạng thái sau Sprint 1 → Sprint 2 (Hoàn thành):**


| Category              | Few-shot              | Prompt Template    | Trạng thái   |
| --------------------- | --------------------- | ------------------ | ------------ |
| 1 – Giả mạo ngân hàng | ✅ 8.2 (3 candidates)  | ✅ 7.2 (hoàn chỉnh) | ✅ Hoàn thành |
| 2 – Đòi nợ / Đe dọa   | ✅ 8.7 (3 candidates)  | ✅ 7.4 (hoàn chỉnh) | ✅ Hoàn thành |
| 3 – BHXH / Trợ cấp    | ✅ 8.3 (4 candidates)  | ✅ 7.3 (hoàn chỉnh) | ✅ Hoàn thành |
| 4 – Tuyển dụng giả    | ✅ 8.4 (5 candidates)  | ✅ 7.8 (hoàn chỉnh) | ✅ Hoàn thành |
| 5 – Cờ bạc / Betting  | ✅ 8.5 (5 candidates)  | ✅ 7.9 (hoàn chỉnh) | ✅ Hoàn thành |
| 6 – Dịch vụ công      | ✅ 8.8 (4 candidates)  | ✅ 7.5 (hoàn chỉnh) | ✅ Hoàn thành |
| 7 – Nội dung nhạy cảm | ✅ 8.9 (3 candidates)  | ✅ 7.6 (hoàn chỉnh) | ✅ Hoàn thành |
| 8 – Crypto / Đầu tư   | ✅ 8.10 (3 candidates) | ✅ 7.7 (hoàn chỉnh) | ✅ Hoàn thành |


### 10.2 Sprint 2 – Hoàn thiện Prompt Templates (Hiện tại)

- **[P0]** Thiết kế prompt template cho **Job Scam** (Cat 4) – Section 7.8
- **[P0]** Thiết kế prompt template cho **Gambling** (Cat 5) – Section 7.9
- **[P0]** Final review & cross-check toàn bộ templates ↔ few-shot (phiên thứ tám)
- **[P0]** Áp dụng 4 sửa đổi: A1 (HVS daily rate), A2 (STK Crypto), A3 (Debt sub-type), B1 (egeR prefix)
- **[P0]** Giải quyết vấn đề Quote Escaping trong CSV → đổi sang pipe-delimited (phiên thứ chín)
- **[P0]** Cập nhật toàn bộ QUY TẮC FORMAT (8 templates) và 30 few-shot candidates sang pipe-delimited
- **[P0]** Điền few-shot examples vào `[PLACEHOLDER]` trong tất cả 8 prompt templates (phiên thứ mười)
- **[P1]** Thêm "Negative examples" vào prompt (chỉ rõ output KHÔNG mong muốn)
- **[P1]** Thử nghiệm few-shot với 2 vs 3 examples → so sánh diversity

### 10.3 Sprint 3 – Chạy & Đánh giá

- Chạy thử batch nhỏ (10–20 rows/category) → kiểm tra format CSV và metadata
- **[P1]** Tạo category-specific `temperature`: Level 4–5 obfuscation cần temperature cao hơn
- Chạy KNN similarity giữa synthetic và real data → đo Fidelity
- Đo inter-sample cosine similarity → đo Diversity
- Chạy thử mô hình với old vs new synthetic data → đo impact thực tế

---

## Ghi chú thảo luận

> **Phần này dùng để ghi lại các quyết định và thảo luận trong quá trình cập nhật**

### [2026-03-23] Phiên thảo luận đầu tiên

**Quan sát từ data thực:**

- `dataset_label_1.csv` có mật độ BHXH scam cao (~15% tổng mẫu) nhưng `synthetic_2000_smishing_v2.csv` gần như không có → Cần ưu tiên bổ sung
- Obfuscation Level 4–5 (extreme noise) chiếm ~10% real data nhưng 0% synthetic → Cần thêm category "Extreme Obfuscation" riêng
- Debt collection scam dùng **tên người thật + CMND giả** – pattern này rất đặc trưng, cần few-shot cụ thể

**Quyết định pending:**

- Có nên tách "Extreme Obfuscation" thành 1 category riêng trong `SCENARIOS` không?
- Few-shot nên là 2 hay 3 examples? (trade-off: 3 examples → tốn token nhưng calibrate tốt hơn)
- Nội dung nhạy cảm (sexual) – có đưa vào không? Nếu có thì xử lý safety filter như thế nào?

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

- Có nên tách "Extreme Obfuscation" thành 1 category riêng trong `SCENARIOS` không?
- Nội dung nhạy cảm (sexual) – có đưa vào không? Nếu có thì xử lý safety filter như thế nào?

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

- Áp dụng phân tích tương tự cho 8.5 (Gambling) – kiểm tra xem có rủi ro Level B không?

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

- Xây dựng prompt template cho Job Scam (Section 7 chưa có) với `{brand}` variable bao phủ Amazon/Tiki/TikTok/Shopee/Lazada/eBay

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

- Double-check toàn bộ Section 8 (8.1–8.5) trước khi thiết kế prompt – xem phiên thảo luận tiếp theo

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


| Category              | Few-shot             | Prompt template     | Trạng thái             |
| --------------------- | -------------------- | ------------------- | ---------------------- |
| 1 – Giả mạo ngân hàng | ✅ 8.2 (3 candidates) | 🔨 7.2 (draft)      | Sẵn sàng thiết kế      |
| 2 – Đòi nợ / Đe dọa   | ❌ Chưa có            | ❌ 7.4 (placeholder) | Cần làm trước khi chạy |
| 3 – BHXH / Trợ cấp    | ✅ 8.3 (4 candidates) | 🔨 7.3 (draft)      | Sẵn sàng thiết kế      |
| 4 – Tuyển dụng giả    | ✅ 8.4 (5 candidates) | ❌ Chưa có           | Sẵn sàng thiết kế      |
| 5 – Cờ bạc / Betting  | ✅ 8.5 (5 candidates) | ❌ Chưa có           | Sẵn sàng thiết kế      |
| 6 – Dịch vụ công      | ❌ Chưa có            | ❌ Chưa có           | Cần làm                |
| 7 – Nội dung nhạy cảm | ❌ Chưa có            | ❌ Chưa có           | Defer – safety filter  |
| 8 – Crypto / Đầu tư   | ❌ Chưa có            | ❌ Chưa có           | Cần làm                |


**Bước tiếp theo:** ~~Thiết kế prompt template cho 4 category đã có few-shot (Cat 1, 3, 4, 5)~~ → **Đã điều chỉnh trong phiên thứ bảy**: ưu tiên xây dựng few-shot + draft template cho 4 category còn thiếu hoàn toàn (Cat 2, 6, 7, 8) trước để đưa toàn bộ 8 categories về trạng thái "có nền tảng". Xem phiên thảo luận thứ bảy và thứ tám bên dưới.

---

### [2026-03-23] Phiên thảo luận thứ bảy – Hoàn thiện toàn bộ Prompt Templates (Section 7) & Few-Shot Library (Section 8)

**Chủ đề thảo luận:** Xây dựng đồng thời nội dung cho 4 category chưa có template/few-shot (Cat 2, 6, 7, 8) **và** thiết kế template cho 2 category còn thiếu (Cat 4, 5) – đưa toàn bộ 8 prompt templates về trạng thái "draft hoàn chỉnh".

**Lý do điều chỉnh ưu tiên so với kế hoạch phiên 6:**

- Phiên 6 dự kiến thiết kế template cho 4 category *đã có* few-shot (Cat 1, 3, 4, 5)
- Quyết định: ưu tiên bổ sung 4 category *chưa có gì* (Cat 2, 6, 7, 8) trước để đưa cả 8 categories về cùng baseline; sau đó ngay trong phiên này thiết kế nốt 2 template còn thiếu (Cat 4, 5)

**Nội dung đã thực hiện:**

*Section 7 – Prompt Templates (6 templates được thêm/cập nhật):*

- **7.4 (Đòi nợ / Đe dọa)**: Thay placeholder bằng draft đầy đủ. CANH BAO LAN CUOI + tên/CMND giả + số tiền không tròn + deadline giờ + đe dọa leo thang. Constraint cứng: `has_url=0` luôn luôn.
- **7.5 (Dịch vụ công giả)**: Template mới. 3 sub-type: CSGT (link .top), Bộ GTVT (SĐT), Thuế/Hoàn thuế (link .vip). Sender đa dạng: brandname/shortcode/personal_number.
- **7.6 (Nội dung nhạy cảm)**: Template mới. Bắt buộc Level 3–5 obfuscation, Telegram/Zalo link, tracking code cuối mỗi dòng. Safety framing nghiên cứu bảo mật.
- **7.7 (Crypto / Đầu tư giả)**: Template mới. 3 sub-type: thả tim (has_url=0), Telegram nhiệm vụ (has_url=1), chuyển khoản STK (has_url=0). Tone thân thiện – phân biệt với Job Scam.
- **7.8 (Tuyển dụng giả)**: Template mới. Platform-specific sub-type: Amazon/eBay/TikTok (Zalo link + số), Shopee/Lazada (Zalo link only), Tiki (số trực tiếp, has_url=0). Thu nhập/ngày thay lương/tháng.
- **7.9 (Cờ bạc / Betting)**: Template mới. 4 sub-type: nạp X nhận Y + tracking code / platform promo dot-insert / casino formal / đại lý hoa hồng (shortcode). `has_url=1` luôn luôn. Constraint: tracking code và domain khác nhau mỗi dòng.

*Section 8 – Few-Shot Candidates (4 sections được thêm mới):*

- **8.7 (Debt/Threat, 3 candidates)**: C1 từ row 41 (CANH BAO + tên+CMND+SĐT Zalo), C2 từ row 155 (Trung tâm tín dụng formal, 2 mức tiền), C3 từ row 6 (Phòng AN NINH ĐIỀU TRA). `has_url=0` trong cả 3.
- **8.8 (Government Fake, 4 candidates)**: C1 row 60 (CSGT brandname + link .top), C2 row 14 (Bộ GTVT+SĐT), C3 row 63 (CSGT shortcode + link .top), C4 row 113 (Hoàn thuế obf Level 2).
- **8.9 (Sensitive Content, 3 candidates)**: C1 row 52 (real data, leet Level 3), C2–C3 tổng hợp từ pattern (vowel-leet + dot-split Level 4).
- **8.10 (Crypto/Investment, 3 candidates)**: C1 row 135 (thả tim, has_url=0), C2 row 190 (giáo viên+Telegram, Level 2), C3 row 120 (chuyển khoản STK ngân hàng).

**Trạng thái sau phiên thứ bảy – tất cả 8 categories:**


| Category              | Few-shot              | Prompt Template | Trạng thái                     |
| --------------------- | --------------------- | --------------- | ------------------------------ |
| 1 – Giả mạo ngân hàng | ✅ 8.2 (3 candidates)  | 🔨 7.2 (draft)  | Chờ điền few-shot vào template |
| 2 – Đòi nợ / Đe dọa   | ✅ 8.7 (3 candidates)  | 🔨 7.4 (draft)  | Chờ điền few-shot vào template |
| 3 – BHXH / Trợ cấp    | ✅ 8.3 (4 candidates)  | 🔨 7.3 (draft)  | Chờ điền few-shot vào template |
| 4 – Tuyển dụng giả    | ✅ 8.4 (5 candidates)  | 🔨 7.8 (draft)  | Chờ điền few-shot vào template |
| 5 – Cờ bạc / Betting  | ✅ 8.5 (5 candidates)  | 🔨 7.9 (draft)  | Chờ điền few-shot vào template |
| 6 – Dịch vụ công      | ✅ 8.8 (4 candidates)  | 🔨 7.5 (draft)  | Chờ điền few-shot vào template |
| 7 – Nội dung nhạy cảm | ✅ 8.9 (3 candidates)  | 🔨 7.6 (draft)  | Chờ điền few-shot vào template |
| 8 – Crypto / Đầu tư   | ✅ 8.10 (3 candidates) | 🔨 7.7 (draft)  | Chờ điền few-shot vào template |


**Điểm cần thảo luận sâu (chưa chốt):**

1. **8.7 C3 (Đòi nợ)**: SĐT dạng quốc tế `84912654378` → `has_phone=0` theo convention. Có cần chuyển sang local `0xxxxxxxxx` để `has_phone=1` không?
2. **8.8 (Dịch vụ công)**: Hiện bao phủ CSGT + Bộ GTVT + Thuế. Có cần thêm sub-type VNeID / Bộ Công an không?
3. **8.9 C2, C3**: Tổng hợp từ pattern (không có trong real data) – cần xác nhận mức obfuscation đủ realistic không?
4. **8.10 C3**: STK ngân hàng `04001012266596` giữ nguyên từ real data (tài khoản scammer). Có cần thay bằng STK giả không?

**Quyết định pending:**

- Thảo luận và chốt 4 điểm trên → xem phiên thảo luận thứ tám bên dưới
- Điền few-shot vào `[PLACEHOLDER]` trong tất cả 8 prompt templates (Sprint 2 còn lại)

---

### [2026-03-23] Phiên thảo luận thứ tám – Final Review & Áp dụng sửa đổi

**Chủ đề thảo luận:** Kiểm tra kỹ lưỡng lần cuối toàn bộ document trước khi điền few-shot vào templates; chốt các pending decisions từ phiên 7; áp dụng 4 sửa đổi phát hiện trong quá trình cross-check.

**Phương pháp review:**
Cross-check từng cặp (Template 7.x ↔ Few-shot 8.x) theo 4 tiêu chí: metadata 5 cột, sender_type coverage, psychology/obfuscation coverage, constraint consistency.

**Issues phát hiện và đã xử lý:**

1. **A1 – 8.4 C2 (HVS) vi phạm constraint "hàng ngày"** ✅ Đã sửa
  - Template 7.8 quy định `"Thu nhập hàng ngày (KHÔNG dùng lương tháng đơn độc)"` nhưng C2 chỉ có `"15-30tr/tháng"` → thêm `"(500k-1tr/ngày)"` vào content
2. **A2 – 8.10 C3 STK ngân hàng từ real data** ✅ Đã sửa
  - `04001012266596` (tài khoản scammer thật) → thay bằng `04001023847291` (giả đúng format MSB 14 chữ số)
  - Áp dụng nguyên tắc anonymization Section 8.6: thay thông tin thực bằng giả đúng format
3. **A3 – Template 7.4 thiếu phân biệt 2 sub-type Đòi nợ** ✅ Đã sửa
  - C3 (8.7) là sub-type "cơ quan điều tra" không có tên/CMND, mâu thuẫn với constraint "BẮT BUỘC" tên+CMND
  - Bổ sung vào ĐẶC TRƯNG BẮT BUỘC: Sub-type A (~~70%) → tên+CMND+số tiền bắt buộc; Sub-type B (~~30%) → "O/B" generic + hình sự hóa, không cần tên/CMND
4. **B1 – 8.8 C4 prefix "egeR" gây nhiễu** ✅ Đã sửa
  - `"egeR #Ban da-du..."` → `"#Ban da-du D1EU K1EN HOAN~THUE TNCN nam 2024..."` 
  - Bỏ tracking noise vô nghĩa, thêm năm `2024` giữ "token lạ" mở đầu có nghĩa

**Pending decisions từ phiên 7 đã chốt:**


| #   | Quyết định                                   | Kết luận                                                         |
| --- | -------------------------------------------- | ---------------------------------------------------------------- |
| 1   | 8.7 C3 – `has_phone=0` cho `84912654378`     | ✅ **Giữ nguyên** – đúng convention quốc tế vs local              |
| 2   | 8.8 – Có cần thêm VNeID/Bộ Công an few-shot? | ✅ **Không thêm** – template instruction đủ, model tự generalize  |
| 3   | 8.9 C2, C3 synthesized – có đủ realistic?    | ✅ **Chấp nhận** – phản ánh đúng taxonomy obfuscation Section 4.3 |
| 4   | 8.10 C3 – STK ngân hàng có cần thay không?   | ✅ **Đã thay** (A2 ở trên)                                        |


**Issues được xác nhận KHÔNG cần sửa:**

- Banking fraud (8.2): Thiếu few-shot shortcode → Chấp nhận, banking scam thực tế ~90% brandname/personal_number
- Gov fake VNeID (8.8): Thiếu few-shot candidate → Chấp nhận, instruction text đủ để model generalize
- Sensitive content (8.9) C2, C3 synthesized → Chấp nhận

**Trạng thái sau phiên thứ tám – sẵn sàng điền few-shot:**


| Category              | Few-shot                         | Template          | Trạng thái        |
| --------------------- | -------------------------------- | ----------------- | ----------------- |
| 1 – Giả mạo ngân hàng | ✅ 8.2 (3 candidates)             | ✅ 7.2 (sạch)      | **Sẵn sàng điền** |
| 2 – Đòi nợ / Đe dọa   | ✅ 8.7 (3 candidates)             | ✅ 7.4 (đã sửa A3) | **Sẵn sàng điền** |
| 3 – BHXH / Trợ cấp    | ✅ 8.3 (4 candidates)             | ✅ 7.3 (sạch)      | **Sẵn sàng điền** |
| 4 – Tuyển dụng giả    | ✅ 8.4 (5 candidates, đã sửa A1)  | ✅ 7.8 (sạch)      | **Sẵn sàng điền** |
| 5 – Cờ bạc / Betting  | ✅ 8.5 (5 candidates)             | ✅ 7.9 (sạch)      | **Sẵn sàng điền** |
| 6 – Dịch vụ công      | ✅ 8.8 (4 candidates, đã sửa B1)  | ✅ 7.5 (sạch)      | **Sẵn sàng điền** |
| 7 – Nội dung nhạy cảm | ✅ 8.9 (3 candidates)             | ✅ 7.6 (sạch)      | **Sẵn sàng điền** |
| 8 – Crypto / Đầu tư   | ✅ 8.10 (3 candidates, đã sửa A2) | ✅ 7.7 (sạch)      | **Sẵn sàng điền** |


**Thứ tự ưu tiên điền `[PLACEHOLDER]` (Sprint 2):**

1. Cat 3 (BHXH) → Cat 1 (Banking) → Cat 5 (Gambling) → Cat 7 (Sensitive) – 4 category không issue
2. Cat 2 (Debt) → Cat 4 (Job) → Cat 6 (Gov) → Cat 8 (Crypto) – 4 category đã có sửa đổi

**Quyết định pending:**

- Điền few-shot vào `[PLACEHOLDER]` trong tất cả 8 prompt templates theo thứ tự trên

---

### [2026-03-23] Phiên thảo luận thứ chín – Quote Escaping & Pipe-Delimited Architecture

**Chủ đề thảo luận:** Xử lý toàn diện vấn đề dấu nháy kép trong CSV output của LLM; thay đổi kiến trúc output format.

**Vấn đề được phát hiện:**

Root cause chain:

1. LLM sinh ra CSV với dấu nháy kép không đúng RFC 4180 (ví dụ: `"Nhấp vào "link" này"` – internal quotes không được escape)
2. `csv.reader` trong `extract_valid_rows()` (phiên bản cũ) có thể misparse hoặc reject dòng đó
3. Dù có validate, script vẫn ghi **raw string từ LLM** (`f.write("\n".join(valid_rows))`) thay vì re-serialized string → malformed quotes đi thẳng vào file
4. `pd.read_csv()` ở bước hậu xử lý gặp malformed CSV → parse sai hoặc crash

**Nguyên tắc cốt lõi:** Không thể yêu cầu LLM không sinh ra dấu nháy trong nội dung tin nhắn – phải xử lý ở tầng kiến trúc.

**Giải pháp đã áp dụng – hai lớp:**

*Lớp 1 – Thay delimiter trong prompt: từ dấu phẩy (CSV) → dấu `|` (pipe)*

- Ký tự `|` hầu như không xuất hiện trong SMS Việt Nam
- LLM không cần quote, không cần escape gì cả
- Output format: `content|label|has_url|has_phone_number|sender_type`

*Lớp 2 – Parse-and-reserialize trong `gen_label_1.py` (người dùng tự sửa)*


| Hàm/đoạn                           | Trước                            | Sau                                                  |
| ---------------------------------- | -------------------------------- | ---------------------------------------------------- |
| `extract_valid_rows()` return type | `list[str]` (raw lines)          | `list[list[str]]` (parsed rows)                      |
| `extract_valid_rows()` logic       | `csv.reader` trên từng line      | `split("                                             |
| Header write                       | `f.write("content,label,...")`   | `csv.writer(f).writerow([...])`                      |
| Data write                         | `f.write("\n".join(valid_rows))` | `csv.writer(f, QUOTE_MINIMAL).writerows(valid_rows)` |
| File open                          | `open(..., "w")`                 | `open(..., "w", newline="")`                         |


*Lý do "last 4 parts" approach:*

```
line.split("|") → parts
content  = "|".join(parts[:-4])   # nếu content có |, ghép lại đúng
metadata = parts[-4:]              # label, has_url, has_phone, sender luôn ở cuối
```

Robust ngay cả khi content tình cờ chứa ký tự `|`.

*Flow hoàn chỉnh sau thay đổi:*

```
LLM output (pipe, no quoting):
  Nhấp vào "link" này để xac thuc|1|1|0|brandname

extract_valid_rows():
  → content = 'Nhấp vào "link" này để xac thuc'  (Python string bình thường)

csv.writer ghi ra file (RFC 4180, tự động escape):
  "Nhấp vào ""link"" này để xac thuc",1,1,0,brandname

pd.read_csv(): parse hoàn toàn đúng ✅
```

**Thay đổi trong document (do assistant thực hiện):**

1. Tất cả 8 `QUY TẮC FORMAT` trong Section 7 → đổi sang `QUY TẮC FORMAT (pipe-delimited)`
2. Tất cả 30 few-shot candidates trong Section 8 → đổi sang pipe format (xóa `"..."` wrap, thay `,1,` → `|1|`, etc.)
3. Section 8.1 → cập nhật nguyên tắc 4 (CSV → pipe-delimited) + giải thích lý do
4. Roadmap 10.2 → thêm 2 dòng completed

**Lưu ý còn lại:** `build_prompt()` trong `gen_label_1.py` (placeholder function) vẫn còn instruction CSV cũ – sẽ được thay thế hoàn toàn khi điền few-shot vào templates (Sprint 2 tiếp theo).  -> Đã hoàn thành ✅

**Quyết định pending:**

- Điền few-shot vào `[PLACEHOLDER]` trong tất cả 8 prompt templates → xem phiên thứ mười bên dưới

---

### [2026-03-23] Phiên thảo luận thứ mười – Hoàn thành Sprint 2: Điền few-shot vào 8 Templates

**Chủ đề thảo luận:** Điền few-shot examples từ Section 8 vào tất cả 8 `[PLACEHOLDER]` trong Section 7, hoàn tất Sprint 2.

**Nội dung đã thực hiện:**

Theo thứ tự ưu tiên chốt ở phiên thứ tám (4 category không issue trước, 4 category đã sửa đổi sau):


| Template                | Few-shot điền vào      | Số examples | Ghi chú                                                                  |
| ----------------------- | ---------------------- | ----------- | ------------------------------------------------------------------------ |
| 7.2 – Giả mạo ngân hàng | 8.2 C1, C2, C3         | 3           | Bao phủ: fear+lock / greed+points / fear+device-activation               |
| 7.3 – BHXH / Trợ cấp    | 8.3 C1, C2, C3, C4     | 4           | Bao phủ: Level 2 .icu / Level 3 NQ-116 / Level 1 dấu / .com variant      |
| 7.9 – Cờ bạc / Betting  | 8.5 C1, C2, C3, C4, C5 | 5           | Bao phủ: t.ly / .cc / casino formal / đại lý shortcode / slash-dash obf  |
| 7.6 – Nội dung nhạy cảm | 8.9 C1, C2, C3         | 3           | Bao phủ: leet Level 3 / vowel-leet Zalo / dot-split Level 4              |
| 7.4 – Đòi nợ / Đe dọa   | 8.7 C1, C2, C3         | 3           | Bao phủ: Sub-A tên+CMND+Zalo / Sub-A 2 mức tiền / Sub-B cơ quan điều tra |
| 7.8 – Tuyển dụng giả    | 8.4 C1–C5              | 5           | Bao phủ: Amazon / HVS / Tiki / TikTok / Shopee                           |
| 7.5 – Dịch vụ công      | 8.8 C1, C2, C3, C4     | 4           | Bao phủ: CSGT brandname / GTVT SĐT / CSGT shortcode / Hoàn thuế obf      |
| 7.7 – Crypto / Đầu tư   | 8.10 C1, C2, C3        | 3           | Bao phủ: thả tim / giáo viên+Telegram / chuyển khoản STK                 |


**Quy tắc đặt few-shot trong template:**

- Tiêu đề: `VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên [loại thông tin], dùng làm tham chiếu style):`
- Format: mỗi dòng = một pipe-delimited row đầy đủ 5 cột
- Không có header, không có giải thích kèm theo từng dòng
- Instruction "KHÔNG copy nguyên" nhắc LLM tham khảo style, không sao chép string cụ thể

**Trạng thái Sprint 2 sau phiên thứ mười:**


| Task                                 | Trạng thái   |
| ------------------------------------ | ------------ |
| Thiết kế 8 prompt template           | ✅ Hoàn thành |
| Xây dựng few-shot library 8 sections | ✅ Hoàn thành |
| Điền few-shot vào 8 `[PLACEHOLDER]`  | ✅ Hoàn thành |
| Chuyển đổi sang pipe-delimited       | ✅ Hoàn thành |
| Final cross-check & 4 sửa đổi        | ✅ Hoàn thành |


**Sprint 2 – HOÀN THÀNH. Sẵn sàng chuyển sang Sprint 3.**

**Bước tiếp theo (Sprint 3):**

- Cập nhật `build_prompt()` trong `gen_label_1.py` để sử dụng 8 template mới ✅ (đã hoàn thành trong code)
- Chạy thử batch nhỏ (10–20 rows/category) → kiểm tra format và metadata
- Đo chất lượng: KNN similarity vs real data (Fidelity), inter-sample cosine similarity (Diversity)

---

### [2026-03-26] Phiên thảo luận thứ mười một – Cross-Check Document ↔ Code & Cập nhật Đồng bộ

**Chủ đề thảo luận:** Kiểm tra kỹ lưỡng toàn bộ mâu thuẫn giữa `gen_label_1.py` (code thực thi) và document này; áp dụng các sửa đổi cần thiết để đồng bộ hóa.

**Phương pháp review:**
So sánh từng cặp (Section document ↔ đoạn code tương ứng) theo 5 tiêu chí: tên file, phân phối sender_type, kiến trúc sinh batch, constraint TLD, trạng thái implement.

---

**Các mâu thuẫn đã phát hiện và xử lý:**

| ID | Vị trí | Mâu thuẫn | Hành động |
|----|--------|-----------|-----------|
| M1 | Section 4.2 | Bảng phân phối sender_type ghi banking: "30% personal_number" trong khi code prompt cấm hẳn personal_number; thiếu dòng Crypto/Đầu tư | ✅ Đã cập nhật: banking → `brandname (~60%), shortcode (~40%) – KHÔNG dùng personal_number`; thêm dòng `Crypto / Đầu tư → 100% personal_number` |
| M2 | Section 7.1 & 7.5 | Section 7.1 và QUY TẮC FORMAT của 7.5 không liệt kê `personal_number` cho Dịch vụ công, mâu thuẫn với Section 4.2 và code `_prompt_govt_fake()` | ✅ Đã cập nhật Section 7.1 và 7.5 để thêm `personal_number (~20%)` |
| M3 | Section 6.3 | Pseudocode mô tả kiến trúc cũ: `brand = random.choice()` (1 brand), `OBFUSCATION_LEVELS`, `CATEGORY_PSYCHOLOGY` – các biến này không tồn tại trong code | ✅ Đã viết lại pseudocode phản ánh đúng: `brands_str`, `pick_mixed_style()`, `CATEGORY_OBF_RANGE` |
| M4 | Section 10.2 / Phiên thứ chín | Note "build_prompt() vẫn còn instruction CSV cũ" đã lỗi thời – code đã dùng pipe-delimited hoàn chỉnh | ✅ Đã thêm "→ Đã hoàn thành ✅" vào note |
| M5 | Section 7.5 QUY TẮC FORMAT | `has_url` constraint liệt kê TLD `.top/.xyz/.vip` nhưng thiếu `.cc` – trong khi code và few-shot C4 đều dùng `.cc` | ✅ Đã bổ sung `.cc` vào danh sách TLD |
| M6 | Section 4.2 | Bảng phân phối sender_type thiếu category Crypto/Đầu tư | ✅ Đã thêm dòng (xử lý cùng M2) |
| M7 | Phiên thứ bảy | Ghi "đưa toàn bộ **9** prompt templates" trong khi chỉ có 8 categories | ✅ Đã sửa thành "8 prompt templates" |
| M8 | Section 7.4 QUY TẮC FORMAT | Dòng `has_phone` kết thúc bằng dấu nháy đơn thừa `'` | ✅ Đã xóa |
| M9 | Section 9.1 & 9.3 | `validate_smishing_row()` và `check_distribution()` được trình bày như đã implement nhưng không có trong code | ✅ Đã thêm ghi chú "(sau khi đã đủ data - hiện chưa kiểm tra)" / "(hiện chưa triển khai)" vào heading |

---

**Các mâu thuẫn xác nhận KHÔNG cần sửa:**

- **Model name:** Code dùng `"gemini-3-flash-preview"` – document không đề cập model cụ thể → chấp nhận, model có thể thay đổi theo thời gian.
- **Temperature = 0.9:** Code dùng temperature cao cố định. Section 10.3 Sprint 3 đã liệt kê "category-specific temperature" là task tương lai → không mâu thuẫn, đây là cải tiến chứ không phải lỗi.
- **TOTAL_SAMPLES = 3000 vs `synthetic_2000_smishing_v2.csv`:** File cũ là dataset 2000 mẫu (so sánh trong Section 5.1), file mới target 3000 → không mâu thuẫn.
- **Hàm `validate_smishing_row()` (Section 9.1):** Đây là pseudocode kế hoạch cho Sprint 3 – đã ghi chú rõ trong heading. Logic validation thực tế được tích hợp trực tiếp trong `extract_valid_rows()`.

---

**Trạng thái đồng bộ sau phiên thứ mười một:**

| Tiêu chí | Trước phiên này | Sau phiên này |
|---|---|---|
| Phân phối sender_type (banking) | ❌ Không khớp code | ✅ Khớp code |
| Phân phối sender_type (Dịch vụ công) | ❌ Thiếu personal_number | ✅ Đầy đủ |
| Phân phối sender_type (Crypto) | ❌ Thiếu dòng | ✅ Đã bổ sung |
| Pseudocode Section 6.3 | ❌ Biến sai tên, logic cũ | ✅ Phản ánh đúng kiến trúc |
| TLD list Section 7.5 | ❌ Thiếu `.cc` | ✅ Đầy đủ |
| Số prompt templates (phiên thứ bảy) | ❌ "9 templates" | ✅ "8 templates" |
| Trạng thái implement Section 9 | ❌ Không rõ là pseudocode | ✅ Ghi chú rõ ràng |

**Bước tiếp theo (Sprint 3 – không thay đổi):**
- Chạy `gen_label_1.py` batch nhỏ (10–20 rows/category) để kiểm tra format và metadata
- Đo Fidelity (KNN similarity vs real data) và Diversity (inter-sample cosine similarity)

