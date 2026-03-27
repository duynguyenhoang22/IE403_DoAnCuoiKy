# Prompt Engineering for Legitimate SMS Data Augmentation

> **Trạng thái tài liệu:** Đang cập nhật liên tục  
> **Phạm vi:** Label 0 – Tin nhắn hợp lệ (Legitimate SMS) tại Việt Nam  
> **Liên quan:** `gen_label_0.py` | `dataset_label_0.csv` | `synthetic_legitimate_sms.csv`

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
❌ Prompt yếu:  "Tạo tin nhắn SMS bình thường"
                → Model sinh ra nội dung quá generic, thiếu đặc trưng Việt Nam,
                  có thể pha trộn phong cách nước ngoài, không đúng format

✅ Prompt tốt:  [Role] + [Task] + [Context] + [Format] + [Constraints] + [Examples]
                → Model hiểu rõ mục tiêu, sinh ra đúng cấu trúc, đủ đa dạng,
                  phản ánh đúng tin nhắn hợp lệ thực tế tại Việt Nam
```

### 1.1 Các thành phần của một Prompt hoàn chỉnh


| Thành phần                  | Mục đích                                      | Ví dụ                                                 |
| --------------------------- | --------------------------------------------- | ----------------------------------------------------- |
| **Role (Vai trò)**          | Định danh model là ai → điều chỉnh "góc nhìn" | "Bạn là chuyên gia tạo dữ liệu huấn luyện..."         |
| **Task (Nhiệm vụ)**         | Chỉ định rõ việc cần làm                      | "Tạo đúng 40 dòng CSV tin nhắn ngân hàng hợp lệ"      |
| **Context (Ngữ cảnh)**      | Cung cấp thông tin nền để model hiểu domain   | "Kịch bản: Thông báo OTP từ MB Bank..."               |
| **Format (Định dạng)**      | Quy định cấu trúc output                      | "5 cột: content, label, has_url, ..."                 |
| **Constraints (Ràng buộc)** | Giới hạn những gì không được làm              | "20–160 ký tự, dùng domain .vn thật, KHÔNG obfuscate" |
| **Examples (Ví dụ)**        | Minh họa bằng mẫu cụ thể → Few-shot           | "Ví dụ 1: ..., Ví dụ 2: ..."                          |
| **Output instruction**      | Nhắc lại cách format cuối cùng                | "Chỉ xuất CSV thuần, không giải thích"                |


---

## 2. Cơ chế hoạt động khi sinh Text Data

### 2.1 LLM hoạt động theo xác suất

LLM không "nhớ" dữ liệu thật, mà **học phân phối xác suất** của ngôn ngữ. Khi bạn yêu cầu sinh tin nhắn hợp lệ, model:

1. Khởi tạo dựa trên prompt → đặt "ngữ cảnh"
2. Tại mỗi token tiếp theo, chọn từ top-k tokens có xác suất cao nhất (điều chỉnh bởi `temperature`)
3. Lặp lại cho đến khi đủ output

**Hệ quả quan trọng đặc thù với Label 0:**

- `temperature` cao → đa dạng hơn nhưng dễ "sáng tạo" nội dung không có thật (ví dụ: domain không tồn tại, tên thương hiệu sai)
- `temperature` thấp → nhất quán format nhưng dễ lặp lại template cứng → dataset thiếu diversity
- **Prompt tốt** với Label 0 = định hướng model sinh đúng đặc trưng từng loại doanh nghiệp Việt Nam (tên brand, domain, format thông báo)

### 2.2 Vì sao Few-shot hiệu quả hơn Zero-shot?

```
Zero-shot (không ví dụ):
  Model tự suy diễn "tin nhắn hợp lệ" trông như thế nào
  → Có thể sinh ra nội dung kiểu nước ngoài (Bank of America, USPS tracking)
  → THIẾU đặc trưng Việt Nam (format số dư VND, mã đơn hàng GHTK/GHN, BHXH)

Few-shot (có ví dụ thực):
  Model "calibrate" (hiệu chỉnh) output theo pattern bạn cung cấp
  → Bắt chước format, độ dài, brandname, domain đúng chuẩn Việt Nam
  → Output sát thực tế hơn rõ rệt
```

**Ví dụ minh họa** – cùng yêu cầu, khác cách prompt:

```
Zero-shot → Model sinh:
  "Your account has been credited with 500,000 VND. Balance: 2,345,678 VND."
  (Tiếng Anh, sai định dạng ngân hàng VN, không có brandname VN)

Few-shot với mẫu thực → Model sinh:
  "[MB] TK 123456****7890 +500,000VND luc 14:23 27/03/26. So du: 2,345,678VND.
   Truy van giao dich: 1800 54 54 26."
  (Đúng format ngân hàng MB, số tài khoản che, số hotline thực tế, timestamp VN)
```

---

## 3. Tại sao Prompt Engineering quan trọng với Data Augmentation?

### 3.1 Mục tiêu của Data Augmentation cho Legitimate SMS

Mô hình phát hiện smishing cần học được **boundary (ranh giới)** giữa:

- Tin nhắn ngân hàng thật (format chuẩn, domain .vn) ↔ Tin nhắn ngân hàng giả mạo (domain .vip, obfuscation)
- Tin nhắn BHXH thật (thông báo chính thống) ↔ Tin nhắn BHXH scam (NQ-116 giả, random code)
- Tin nhắn tuyển dụng thật (link .com.vn, thông tin rõ ràng) ↔ Tin nhắn tuyển dụng giả (Zalo cá nhân, lương ảo)

Synthetic data Label 0 **kém chất lượng** sẽ dạy model học **boundary sai**, dẫn đến:

- **False Positive** cao: Phân loại tin nhắn ngân hàng/BHXH thật là smishing
- **False Negative** cao: Bỏ sót smishing vì không học được pattern thật để phân biệt

### 3.2 Ba tiêu chí chất lượng của Synthetic Legitimate Data


| Tiêu chí                     | Giải thích                                                        | Hậu quả nếu thiếu                                             |
| ---------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------- |
| **Fidelity (Độ trung thực)** | Giống với tin nhắn hợp lệ thật về format, domain, tên thương hiệu | Model không học được ranh giới với smishing                   |
| **Diversity (Đa dạng)**      | Đủ các category, sub-type, loại thông báo (OTP, giao dịch, ...)   | Model overfit vào 1 template cứng, fail với biến thể thực tế  |
| **Novelty (Tính mới)**       | Không trùng lặp với data thật hoặc với nhau                       | Dataset bị inflate giả tạo, đặc biệt nguy hiểm với OTP format |


### 3.3 Thách thức đặc thù của Label 0 (so với Label 1)

Label 0 có một số thách thức **khác hoàn toàn** với Label 1:

```
Thách thức 1 – "Too clean" problem:
  Tin nhắn hợp lệ từ doanh nghiệp lớn (ngân hàng, TMĐT) rất template hóa
  → Model dễ sinh ra text quá đồng đều, "sạch bóng" không tự nhiên
  → Giải pháp: few-shot đa dạng sub-type + yêu cầu variation

Thách thức 2 – Legitimate urgency vs Smishing urgency:
  Tin nhắn OTP thật CÓ urgency ("sử dụng trong 5 phút") nhưng KHÔNG phải smishing
  → Model cần học phân biệt urgency hợp lệ vs urgency thao túng
  → Giải pháp: few-shot rõ ràng về domain thật, nội dung cụ thể không đe dọa

Thách thức 3 – Personal message ambiguity:
  Tin nhắn cá nhân (personal_number) rất ngắn, không có dấu hiệu rõ ràng
  → Khó phân biệt với smishing ngắn (Crypto/Đầu tư dạng "thả tim")
  → Giải pháp: Personal message prompt cần constraint rõ về nội dung ngữ cảnh

Thách thức 4 – Không cần Safety Framing:
  Label 0 là nội dung hoàn toàn lành mạnh → Không cần "research framing" đặc biệt
  → Prompt có thể trực tiếp hơn, đơn giản hơn về phần Role/Context
```

---

## 4. Phân tích dữ liệu thực tế (Ground Truth)

> Nguồn: `dataset_label_0.csv` – mẫu thu thập thủ công

### 4.1 Phân loại 8 Category chính

Tin nhắn hợp lệ tại Việt Nam tập trung vào 8 nhóm:


| #   | Category                   | Sub-type                                            | Đặc trưng nhận dạng                                            | Ví dụ thực                                                                                  |
| --- | -------------------------- | --------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1   | **Ngân hàng thật**         | OTP, giao dịch, nhắc nhở, số dư                     | Domain .vn thật, số tài khoản che (***), hotline chính thức    | `"[MB] TK 123****7890 +500,000VND luc 14:23. So du: 2,345,678VND. Truy van: 1800 54 54 26"` |
| 2   | **Viễn thông**             | Thông báo gói cước, hết hạn, khuyến mãi             | Brandname Viettel/Vinaphone/MobiFone, mã USSD (*098#)          | `"Viettel: Da DK goi D60 200MB/ngay, gia 60k/30 ngay. HL tu 26/03 den 25/04/2026"`          |
| 3   | **Thương mại điện tử**     | Xác nhận đơn, giao hàng, hoàn trả, đánh giá         | Mã đơn hàng (# hoặc chữ số), tên sàn (Shopee/Tiki/Lazada)      | `"Shopee: Don hang #240327XXXXX da giao thanh cong. Danh gia san pham de nhan xu uu dai!"`  |
| 4   | **Vận chuyển & Logistics** | Mã vận đơn, trạng thái, giao thất bại, lấy hàng     | Mã vận đơn (9–12 ký tự), tên ĐVVC (GHN/GHTK/VTP/Ninja Van)     | `"[GHN] Van don XXXXXXXXXXXX: Dang phan loai tai kho HCM. Du kien giao 27/03 (tu 8h-18h)"`  |
| 5   | **Quảng cáo hợp lệ**       | Khuyến mãi thực, tích điểm, ưu đãi thành viên       | Domain thật (.vn/.com.vn), code khuyến mãi cụ thể, có hạn dùng | `"KFC: Mua combo BigBox 129k tang 1 nuoc. Ma: KFCAPP26. Ap dung qua app den 31/3/2026"`     |
| 6   | **Dịch vụ y tế**           | Nhắc lịch khám, kết quả XN, tái khám, OTP app       | Tên bệnh viện/phòng khám, ngày giờ cụ thể, phòng/khoa          | `"[BV Bach Mai] Lich kham: 8h ngay 27/3 phong 301 khoa Tim mach. Vui long den dung gio"`    |
| 7   | **Dịch vụ công thật**      | BHXH/BHYT thật, thuế, VNeID, hành chính             | Domain .gov.vn, tên đơn vị chính xác, không có link giả        | `"BHXH VN: The BHYT ma so XXXXXXXXXXXX het han 31/12/2026. LH BHXH Q.Binh Thanh gia han"`   |
| 8   | **Tin nhắn cá nhân & OTP** | OTP ứng dụng, xác thực 2FA, tin nhắn phi thương mại | Mã OTP (4–8 chữ số), thời hạn ngắn, hoặc văn phong thân mật    | `"Ma OTP cua ban la: 847392. Co hieu luc trong 5 phut. KHONG chia se ma nay voi bat ky ai"` |


### 4.2 Phân phối sender_type theo Category

```
Ngân hàng thật       → brandname (~70%), shortcode (~30%) – KHÔNG dùng personal_number
Viễn thông           → brandname (~60%), shortcode (~40%)
Thương mại điện tử   → brandname (~80%), shortcode (~20%)
Vận chuyển           → brandname (~70%), shortcode (~30%)
Quảng cáo hợp lệ    → shortcode (~55%), brandname (~45%)
Dịch vụ y tế         → brandname (~60%), shortcode (~30%), personal_number (~10%)
Dịch vụ công thật    → brandname (~70%), shortcode (~30%)
Tin nhắn cá nhân/OTP → personal_number (~60%), shortcode (~30%), brandname (~10%)
```

### 4.3 Taxonomy mức độ formal hóa (thay thế obfuscation trong Label 1)

Thay vì obfuscation, Label 0 có **5 mức độ formal**, từ cứng nhắc đến thân mật:

```
LEVEL 0 – Template cứng (doanh nghiệp lớn):
  "[MB] TK 123456****7890 +500,000VND luc 14:23 27/03/26. So du: 2,345,678VND."
  → Ngân hàng, viễn thông lớn: format cố định, không biến thể

LEVEL 1 – Template mềm (có biến thể nhỏ):
  "Shopee: Don hang #240327XXXXX cua ban da duoc xac nhan. Du kien giao 28-30/3."
  → TMĐT, logistics: template nhưng có trường dữ liệu thực biến đổi

LEVEL 2 – Bán formal (doanh nghiệp vừa + nhỏ):
  "KFC Quan 1 xin thong bao: Tu 26-28/3, mua combo bat ky giam 30%. Xem menu: kfc.com.vn/menu"
  → Nhà hàng, siêu thị: ít cứng nhắc hơn, có thể có lỗi nhỏ

LEVEL 3 – Thân thiện (dịch vụ tư nhân nhỏ + lễ tân):
  "Phong kham Dr. Lan nhac ban: Lich kham ngay mai 27/3 luc 9h. Co gi thay doi lien he 0901234567 nhe."
  → Phòng khám nhỏ, cửa hàng cá nhân: nhắn như người quen

LEVEL 4 – Cá nhân hoàn toàn:
  "Chieu nay hop 3h nhe. Nho mang tai lieu du an"
  → Tin nhắn cá nhân: không có brand, không có template, ngắn gọn tự nhiên
```

### 4.4 Patterns Domain / URL hợp lệ

```python
LEGITIMATE_DOMAIN_PATTERNS = {
    "Ngân hàng":     [".com.vn", ".vn", "mbbank.com.vn", "vietcombank.com.vn",
                      "bidv.vn", "techcombank.vn", "acb.com.vn", "vpbank.com.vn"],
    "Viễn thông":    ["viettel.vn", "vinaphone.vn", "mobifone.vn"],
    "TMĐT":          ["shopee.vn", "tiki.vn", "lazada.vn", "sendo.vn"],
    "Logistics":     ["ghn.vn", "ghtk.vn", "viettelpost.vn", "ninjavan.vn"],
    "Dịch vụ công": ["bhxh.gov.vn", "gdt.gov.vn", "dichvucong.gov.vn", "vneid.gov.vn"],
    "USSD":          ["*098#", "*101#", "*111#"],  # Viễn thông
    "Shortlink thật":["zalo.me/s/", "fb.com/", "l.shopee.vn"],
}
```

**Đặc điểm phân biệt với smishing:**

```
✅ Legitimate URL:
  - TLD chuẩn: .vn, .com.vn, .gov.vn
  - Brand name ĐÚNG trong domain (mbbank.com.vn – không phải mb-bank.top)
  - HTTPS thật (nếu có link)
  - Không có homoglyph (không biến VCB thành vcbtiebink)

❌ Smishing URL:
  - TLD lạ: .vip, .top, .xyz, .cc, .icu
  - Brand giả trong domain (vcb-online.vIp)
  - URL rút gọn ẩn (t.ly/xxx, bit.ly/xxx) → che giấu đích đến
  - Homoglyph: dùng ký tự trông giống để đánh lừa
```

### 4.5 Patterns nội dung đặc trưng theo Category

```
NGÂN HÀNG THẬT – OTP:
  → "Ma OTP: XXXXXX. Su dung trong [N] phut. KHONG chia se."
  → Không có link, không có urgency đe dọa

NGÂN HÀNG THẬT – Giao dịch:
  → "[BRAND] TK [masked_account] +/-[amount] luc [time]. So du: [balance]VND."
  → Che thông tin tài khoản (*** hoặc chỉ giữ 4 số cuối)

VIỄN THÔNG – Gói cước:
  → "[BRAND]: Da DK goi [package_name] [data]/ngay gia [price]/[days] ngay.
     Hieu luc tu [start_date] den [end_date]."
  → Thông tin cụ thể, không đe dọa, có mốc thời gian rõ ràng

TMĐT – Đơn hàng:
  → "[BRAND]: Don hang #[order_id] [status]. Du kien [action] [date]."
  → Mã đơn hàng thực tế, trạng thái rõ ràng

LOGISTICS – Vận đơn:
  → "[BRAND] Van don [tracking_id]: [status]. Du kien giao [date] (tu [hour_range])."
  → Tracking ID thực tế format, giờ giao dự kiến

QUẢNG CÁO HỢP LỆ:
  → "[BRAND]: [offer_description]. [condition]. Den [expiry_date]. [link_or_more_info]"
  → Có điều kiện áp dụng rõ ràng, domain thật, ngày hết hạn cụ thể

Y TẾ – Nhắc lịch:
  → "[BRAND/Hospital] Nhac lich kham: [time] ngay [date] tai [room/department]."
  → Thông tin lịch hẹn cụ thể, không có link (hầu hết)

DỊCH VỤ CÔNG THẬT:
  → "[BRAND] thong bao: [specific_notification]. Truy cap [official_domain] de thuc hien."
  → Domain .gov.vn thật, không có urgency đe dọa kiểu scam
```

---

## 5. Khoảng cách giữa Synthetic và Real Data

### 5.1 Các nguy cơ khi sinh Label 0 bằng LLM

Khác với Label 1 (smishing có thể kiểm soát qua obfuscation pattern), Label 0 phức tạp hơn vì:


| Nguy cơ                              | Biểu hiện                                                    | Hậu quả với mô hình                                       |
| ------------------------------------ | ------------------------------------------------------------ | --------------------------------------------------------- |
| **Template monotony**                | 40 mẫu OTP giống nhau chỉ khác mã số                         | Model chỉ nhận OTP format, miss biến thể khác             |
| **Brand name hallucination**         | Sinh ra "SHB Bank" / "VPBank Online" (tên không tồn tại)     | Model học pattern sai, false positive với tên thật        |
| **Domain hallucination**             | Sinh ra "vietcombank-secure.com.vn" (domain không tồn tại)   | Boundary với smishing bị blur                             |
| **Urgency confusion**                | OTP hợp lệ có "trong 5 phút" bị mix với urgency của smishing | Model nhầm legitimate urgency là smishing                 |
| **Personal message over-generalize** | Mọi personal message đều là câu chat thân mật                | Bỏ sót: OTP từ app bên thứ ba, thông báo đặt lịch cá nhân |
| **"Quá sạch" problem**               | Text formal hoàn hảo, không có abbreviation thực tế          | Model không nhận được legitimate SMS có typo nhỏ          |


### 5.2 So sánh đặc trưng Label 0 vs Label 1


| Tiêu chí             | Label 0 (Legitimate)                        | Label 1 (Smishing)                                 |
| -------------------- | ------------------------------------------- | -------------------------------------------------- |
| **Obfuscation**      | Không có (Level 0 hoàn toàn)                | Level 0–5, chủ ý gây nhiễu                         |
| **Domain**           | .vn, .com.vn, .gov.vn – brand name đúng     | .vip, .top, .cc, .icu – brand name giả             |
| **Urgency**          | Có nhưng thực chất ("OTP trong 5 phút")     | Giả tạo, đe dọa ("mặc định đồng ý", "tài sản mất") |
| **Sender**           | Brandname/shortcode chính thống             | Giả mạo brandname hoặc personal_number scammer     |
| **CTA**              | Thông tin (domain thật, số hotline thật)    | Dẫn đến link giả, Zalo lừa đảo                     |
| **Grammar**          | Chuẩn đến semi-formal, ít lỗi               | Chủ ý lỗi (leet), nhiều ký tự đặc biệt             |
| **has_url**          | ~40% (TMĐT, logistics, quảng cáo có link)   | ~75% (link giả là vũ khí chính)                    |
| **has_phone_number** | ~20% (hotline thật, liên hệ)                | ~30% (Zalo scam, đòi nợ)                           |
| **Content length**   | 20–200 ký tự (template cố định + data động) | 40–600 ký tự (rất đa dạng)                         |


### 5.3 Nguyên nhân gốc rễ (Root Cause) của Synthetic Label 0 kém chất lượng

```
Vấn đề 1 – Thiếu brand-specific format:
  Prompt nói "tạo tin nhắn ngân hàng" nhưng mỗi ngân hàng có format riêng
  (MB dùng prefix [MB], BIDV dùng "BIDV thong bao:", VCB dùng "[VCB]")
  → Kết quả: Mix format không đúng brand, model khó học boundary

Vấn đề 2 – Không có few-shot với data động:
  OTP, số tài khoản, mã đơn hàng phải là dữ liệu giả nhưng đúng format
  → Không có few-shot: model sinh "XXXXXX" literal thay vì số thực tế "847392"

Vấn đề 3 – Thiếu diversity trong personal message:
  Prompt "tạo tin nhắn cá nhân" → model sinh toàn bộ chat thân mật
  → Bỏ sót: OTP ứng dụng bên thứ ba, thông báo nhắc lịch từ cá nhân/SME

Vấn đề 4 – Category imbalance:
  Dễ sinh quá nhiều OTP/giao dịch (template rõ ràng)
  → Thiếu: quảng cáo hợp lệ, y tế, dịch vụ công thật
```

---

## 6. Kỹ thuật Prompt Engineering hệ thống

### 6.1 Kiến trúc Prompt Layer

Prompt hiệu quả được xây dựng theo **4 lớp** từ ngoài vào trong:

```
┌─────────────────────────────────────────────┐
│  LAYER 1: PERSONA & TASK FRAMING           │
│  (Vai trò + bối cảnh data augmentation)   │
├─────────────────────────────────────────────┤
│  LAYER 2: TASK SPECIFICATION               │
│  (Nhiệm vụ cụ thể + tham số biến thiên)   │
├─────────────────────────────────────────────┤
│  LAYER 3: FEW-SHOT DEMONSTRATIONS          │
│  (Ví dụ thực → calibrate format/style)    │
├─────────────────────────────────────────────┤
│  LAYER 4: OUTPUT CONSTRAINTS               │
│  (Format + Validation + Negative examples) │
└─────────────────────────────────────────────┘
```

### 6.2 Layer 1: Persona & Task Framing

**Lưu ý quan trọng với Label 0:** Khác với Label 1 (phải dùng "safety framing" để tránh LLM từ chối), Label 0 **không cần framing đặc biệt** vì nội dung hoàn toàn lành mạnh. Tuy nhiên, vẫn cần định hướng rõ mục tiêu:

```
❌ Kém: "Tạo tin nhắn SMS bình thường"
         → LLM không biết đây là dữ liệu huấn luyện
         → Có thể sinh text quá generic hoặc không đúng format Việt Nam

✅ Tốt: "Bạn là chuyên gia tạo dữ liệu huấn luyện cho mô hình phân loại SMS
         tại Việt Nam. Nhiệm vụ là tạo dữ liệu mô phỏng tin nhắn hợp lệ (label=0)
         đại diện cho các loại SMS doanh nghiệp và cá nhân thực tế tại VN."
         → LLM hiểu đây là task tạo data, sẽ chú ý đến tính chính xác của brand/format
```

```python
SYSTEM_PROMPT_LABEL0 = """Bạn là chuyên gia tạo dữ liệu huấn luyện cho mô hình phân loại SMS 
tại Việt Nam. Nhiệm vụ là tạo dữ liệu mô phỏng tin nhắn SMS hợp lệ (label=0) – 
bao gồm thông báo từ ngân hàng, viễn thông, thương mại điện tử, 
và tin nhắn cá nhân – phản ánh đúng thực tế SMS tại Việt Nam."""
```

### 6.3 Layer 2: Task Specification – Kỹ thuật "Biến – Hằng"

Tương tự `gen_label_1.py`, thiết kế `gen_label_0.py` cần tuân theo nguyên tắc:

`brand` **→** `brands_str` **(toàn list):** Truyền toàn bộ danh sách brand của category, model tự chọn và mix ngẫu nhiên từng dòng trong batch.

`formality` **→** `(formal_lo, formal_hi), style_prompt` **từ** `pick_formality_style()`**:** Thay vì chọn 1 mức duy nhất, gộp mô tả của tất cả mức formal trong range của category thành 1 chuỗi, yêu cầu model phân bổ đều. Giống`pick_mixed_style()` của Label 1.

`batch_size` **động:** `min(BATCH_SIZE, remaining)` thay vì hằng số cố định.

`output_format` **dùng pipe** `|` **thay vì comma:** Giữ nguyên kiến trúc từ Label 1 để parser tương thích.

```python
# ─── BIẾN – thay đổi mỗi batch để đảm bảo diversity ───────────────────────
category    = random.choice(SCENARIOS_LABEL0.keys())
# Ví dụ: "Ngân hàng thật"

brands_list = SCENARIOS_LABEL0[category]
brands_str  = ", ".join(brands_list)
# Toàn bộ danh sách brand của category được truyền vào prompt
# Ví dụ: "MB Bank, Vietcombank, BIDV, Techcombank, ACB, VPBank, ..."

(formal_lo, formal_hi), style_prompt = pick_formality_style(category)
# Tra CATEGORY_FORMAL_RANGE → range mức formal của category
# Gộp MÔ TẢ + FEW-SHOT của TẤT CẢ mức trong [lo, hi] thành 1 chuỗi
# Ví dụ: "Ngân hàng thật" → (0, 1) → style chứa Level 0 + Level 1

batch_size  = min(BATCH_SIZE, TOTAL_SAMPLES - current_total)

# ─── HẰNG – giữ nguyên mọi batch ──────────────────────────────────────────
output_format  = "content|label|has_url|has_phone_number|sender_type"
label_value    = 0                          # Luôn là 0 cho legitimate
length_range   = per-category              # Khác nhau theo category
sender_options = "personal_number | brandname | shortcode"
```

### 6.4 Layer 3: Few-shot – Nguyên tắc cho Label 0

**Coverage Matrix lý tưởng** (3 examples cho Label 0):

```
Example 1: brandname + Level 0 (template cứng – OTP hoặc giao dịch ngân hàng)
Example 2: shortcode + Level 1 (template mềm – TMĐT hoặc logistics)
Example 3: personal_number + Level 3–4 (informal – personal hoặc SME)
```

**4 nguyên tắc cốt lõi** (giữ nguyên từ Label 1):

1. **Bao phủ đa dạng**: Mỗi example nên thể hiện 1 combination khác nhau của `(sender_type × content_type × formality_level)`
2. **Đủ ngắn**: 2–3 examples là tối ưu
3. **Trích từ real data**: Ưu tiên mẫu từ `dataset_label_0.csv`
4. **Luôn dùng đầy đủ 5 cột**: Pipe-delimited `content|label|has_url|has_phone_number|sender_type`

**Nguyên tắc riêng cho Label 0:**

```
5. Data động phải đúng format thực tế:
   ✅ Mã OTP: 6 chữ số ngẫu nhiên (ví dụ: 847392, không phải "XXXXXX")
   ✅ Số tài khoản: che đúng format (123456****7890 hoặc ****7890)
   ✅ Mã đơn hàng: đúng format từng sàn (Shopee: #240327XXXXXXX)
   ✅ Tracking ID: đúng format từng ĐVVC (GHN: 11 ký tự chữ hoa/số)
   ✅ Số tiền: có dấu phân cách (2,345,678VND không phải 2345678VND)

6. Brand-specific format:
   Mỗi ngân hàng, ĐVVC có format thông báo riêng – few-shot phải thể hiện đúng
   Ví dụ: MB dùng "[MB] TK ...", Vietcombank dùng "[VCB]...", BIDV dùng "BIDV:"
```

### 6.5 Layer 4: Output Constraints – Kỹ thuật "Negative Instruction"

```
✅ Negative constraints quan trọng cho Label 0:
  - "KHÔNG dùng domain giả (.vip, .top, .xyz) – chỉ dùng domain thật (.vn, .com.vn)"
  - "KHÔNG thêm urgency đe dọa ('tài khoản bị khóa vĩnh viễn', 'mất toàn bộ số dư')"
  - "KHÔNG obfuscate – viết đúng chính tả tiếng Việt (có thể bỏ dấu nhưng KHÔNG leet)"
  - "KHÔNG dùng placeholder literal ('XXXXXX', '[TÊN]', '[SỐ TIỀN]') – thay bằng data giả đúng format"
  - "KHÔNG lặp lại cùng 1 mã OTP/mã đơn hàng trong batch"
  - "KHÔNG mix format của hai brand khác nhau vào cùng 1 dòng"
```

---

## 7. Thiết kế Prompt cho từng Category

### 7.1 Category Mapping Table

> **TODO – Đây là vùng cần thảo luận chi tiết nhất trước khi thiết kế prompt**


| Category               | Sender Type ưu tiên                                         | Formality Level | has_url distribution         | Unique patterns                                          |
| ---------------------- | ----------------------------------------------------------- | --------------- | ---------------------------- | -------------------------------------------------------- |
| Ngân hàng thật         | brandname (~~70%), shortcode (~~30%)                        | 0–1             | OTP: 0%; Giao dịch: 0%; ~20% | Masked account (****), số hotline 1800xxxx, prefix brand |
| Viễn thông             | brandname (~~60%), shortcode (~~40%)                        | 0–1             | ~30%                         | Mã USSD (*098#), tên gói, ngày hết hạn                   |
| Thương mại điện tử     | brandname (~~80%), shortcode (~~20%)                        | 1               | ~70%                         | Mã đơn hàng #, link sàn thật, trạng thái đơn             |
| Vận chuyển             | brandname (~~70%), shortcode (~~30%)                        | 0–1             | ~30%                         | Tracking ID, kho phân loại, khung giờ giao               |
| Quảng cáo hợp lệ       | shortcode (~~55%), brandname (~~45%)                        | 1–2             | ~60%                         | Mã khuyến mãi, ngày hết hạn, domain thật                 |
| Dịch vụ y tế           | brandname (~~60%), shortcode (~~30%), personal_number(~10%) | 2–3             | ~20%                         | Tên bệnh viện/phòng, số phòng, tên khoa                  |
| Dịch vụ công thật      | brandname (~~70%), shortcode (~~30%)                        | 0–1             | ~40%                         | Domain .gov.vn, tên đơn vị chính xác, không đe dọa       |
| Tin nhắn cá nhân & OTP | personal_number (~~60%), shortcode (~~30%), brandname(~10%) | 3–4             | ~10%                         | OTP 4–8 chữ số, văn phong thân mật, không template       |


### 7.2 Prompt Template – Ngân hàng thật (Đã thiết kế)

**Đặc trưng bắt buộc cần capture:**

```
Sub-type A – OTP (~30% batch):
  → Prefix brand đúng: "[MB]", "[VCB]", "[BIDV]", "Techcombank:", ...
  → Mã OTP: 6 chữ số ngẫu nhiên (KHÔNG toàn 0, toàn 1)
  → Thời hạn: "trong [3/5/10] phut"
  → Câu cảnh báo: "KHONG chia se ma nay voi bat ky ai"
  → has_url = 0, has_phone = 0, sender_type = brandname hoặc shortcode

Sub-type B – Giao dịch (~40% batch):
  → "[BRAND] TK [masked_account] [+/-][amount]VND luc [HH:MM] [DD/MM/YY]. So du: [balance]VND."
  → Số tài khoản masked: 4 số cuối hoặc format ***XXXX
  → Số tiền format: dấu phân cách hàng nghìn (ví dụ: 500,000 không phải 500000)
  → has_url = 0, has_phone = 0 hoặc 1 (nếu có hotline)

Sub-type C – Nhắc nhở / thông tin (~30% batch):
  → Nhắc thanh toán thẻ tín dụng: "The tin dung XXXX den han [date]. So du: [amount]VND"
  → Thông báo điểm thưởng sắp hết hạn (THẬT, domain .vn)
  → Thông báo nâng hạng, thay đổi lãi suất
  → has_url = 0 hoặc 1 (link .vn thật), has_phone = 0 hoặc 1
```

**Draft prompt template:**

```python
BANKING_LEGIT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn ngân hàng hợp lệ (label=0).
Ngân hàng: {brands}
Loại thông báo: Mix đa dạng OTP / Giao dịch / Thông tin tài khoản
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một ngân hàng từ danh sách trên cho mỗi dòng.
  - Prefix đúng brand: "[MB]", "[VCB]", "[BIDV]", "Techcombank:", "ACB:", "VPBank:", ...
  - Số tài khoản PHẢI masked: dạng 123456****7890 hoặc ****7890 (KHÔNG để số thật)
  - Mã OTP: 6 chữ số ngẫu nhiên thực tế (KHÔNG dùng "XXXXXX", "123456", "000000")
  - Số tiền: có dấu phân cách nghìn (2,345,678VND không phải 2345678VND)
  - KHÔNG có urgency đe dọa ("bị khóa vĩnh viễn", "mất toàn bộ tài sản") – chỉ thông tin
  - has_url = 0 với OTP và giao dịch; có thể = 1 với nhắc nhở (link .vn thật)
  - Sender: brandname (~70%), shortcode (~30%) – KHÔNG dùng personal_number

SUB-TYPE (phân bổ đều trong batch):
  A – OTP (~30%): "[BRAND] Ma OTP: XXXXXX. Su dung trong [3/5/10] phut. KHONG chia se."
  B – Giao dịch (~40%): "[BRAND] TK ****XXXX +/-[amount]VND luc [HH:MM]. So du: [balance]VND."
  C – Nhắc nhở (~30%): Nhắc thanh toán thẻ tín dụng, điểm thưởng sắp hết hạn, thay đổi lãi suất

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Ma OTP la 22085377. de xac nhan giao dich (TRU TIEN) tu The cua quy khach. Vui long giu bao mat va khong chia se OTP cho bat cu ai. LH Techcombank: 1800588822|0|0|1|brandname
Ma OTP xac thuc GD la 972501, hieu luc 1 phut. Chi tiet GD:Chuyen khoan nhanh qua so TK,so tien 22,700,000 VND tren kenh Internet cua dich vu VCB Digibank.|0|0|0|brandname
Vietcombank KHONG yeu cau cung cap TEN DANG NHAP, MAT KHAU, OTP qua cac duong link gui qua SMS. Quy khach hay canh giac va TUYET DOI KHONG cung cap thong tin.|0|0|0|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (OTP và giao dịch), 0 hoặc 1 (nhắc nhở – link .vn thật nếu có)
  - has_phone = 1 nếu có hotline 1800xxxx trong nội dung, 0 nếu không
  - sender_type: brandname (~70%), shortcode (~30%)
  - 40–200 ký tự
  - Mã OTP và số tài khoản KHÁC NHAU mỗi dòng trong cùng batch
  - KHÔNG dùng domain giả (.vip, .top, .xyz) – chỉ domain .vn, .com.vn thật nếu có link
  - KHÔNG có placeholder literal như "[BRAND]", "[OTP]", "XXXXXX"

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.3 Prompt Template – Viễn thông (Đã thiết kế)

**Đặc trưng bắt buộc cần capture:**

```
Sub-type A – Thông báo gói cước (~40% batch):
  → "Da DK goi [package_name] [data_amount]/ngay gia [price]/[duration] ngay."
  → "Hieu luc tu [start_date] den [end_date]."
  → Tên gói thực: D60, MiMax99, D150, V120, Big0, ...
  → has_url = 0, has_phone = 0

Sub-type B – Số dư / Cảnh báo (~30% batch):
  → "So du tai khoan chinh: [amount]d. Nap them tai [channel]."
  → USSD code (*098# cho Viettel, *101# cho Vinaphone)
  → has_url = 0, has_phone = 0

Sub-type C – Khuyến mãi (~30% batch):
  → Ưu đãi gói data, chương trình tích điểm, quà tặng
  → Link: [brand].vn thật
  → has_url = 0 hoặc 1
```

**Draft prompt template:**

```python
TELECOM_LEGIT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn viễn thông hợp lệ (label=0).
Nhà mạng: {brands}
Loại thông báo: Mix đa dạng Gói cước / Cảnh báo / Khuyến mãi
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một nhà mạng từ danh sách trên cho mỗi dòng.
  - Prefix phổ biến: "[TB]" (thông báo), "[QC]" (quảng cáo), tên brand đầu câu
  - Tên gói thực tế: D60, MiMax99, V90B, ST7K, 5G30, WIN60, Big0, FB5K, ...
  - USSD code: Soạn [GÓI] gửi 191 (Viettel), *098# (Viettel), *101# (Vinaphone)
  - Mốc thời gian cụ thể: ngày bắt đầu, ngày hết hạn
  - CTA từ chối QC: "Tu choi QC, soan TC3 gui 199" (nếu là quảng cáo)
  - Hotline: 198 (Viettel, 0đ), 18001260 (Vinaphone), 9090 (MobiFone)

SUB-TYPE (phân bổ đều):
  A – Đăng ký gói cước thành công (~35%): thông báo sau khi khách hàng đăng ký gói data/thoại
  B – Cảnh báo hết data/số dư (~25%): thông báo đã dùng hết lưu lượng hoặc sắp hết hạn
  C – Khuyến mãi (~40%): ưu đãi tặng data, giảm giá gói, tích điểm, nạp thẻ

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
[TB] NẠP THẺ ĐỦ ĐẦY - DATA XÀI NGAY! Tặng 20% giá trị tất cả thẻ nạp vào tài khoản viễn thông trong ngày 25/11/2025. Tiền KM sử dụng truy cập Internet trong 15 ngày. Nạp thẻ online tại https://viettel.vn/naptienkm . Chi tiết gọi 197 bấm phím 19 (0đ). Trân trọng.|0|1|0|brandname
Quy khach da dung het luu luong data cua CT Viettel++ va tiep tuc truy cap theo goi Mobile Internet dang su dung (neu co). Chi tiet LH 198 (0d). Tran trong.|0|0|0|shortcode
iTel TB: Den het thang 01/2023, Quy khach dang la hoi vien Than Thiet, so diem iTel Club la 200. Diem iTel Club co gia tri su dung trong vong 12 thang. Truy cap app MyiTel tai http://onelink.to/myitel de nhan uu dai.|0|1|1|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link (viettel.vn, vinaphone.vn, mobifone.vn thật)
  - has_phone = 1 nếu có hotline trong nội dung (198, 18001260, 9090...)
  - sender_type: brandname (~80%), shortcode (~20%)
  - 50–300 ký tự (khuyến mãi thường dài hơn)
  - KHÔNG dùng domain giả – chỉ domain nhà mạng thật

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.4 Prompt Template – Thương mại điện tử

> **TODO – Cần thiết kế chi tiết**

**Đặc trưng bắt buộc cần capture:**

```
Sub-type A – Xác nhận đơn hàng (~30% batch):
  → "[BRAND]: Don hang #[order_id] da dat thanh cong. Du kien giao [date_range]."
  → Mã đơn hàng format đúng từng sàn:
      * Shopee: #240327XXXXXXX (ngày + 7 số)
      * Tiki: TKI-XXXXXXXXXX
      * Lazada: [order_number] (dạng số dài)

Sub-type B – Giao hàng thành công (~30% batch):
  → "[BRAND]: Don hang cua ban [#order_id] da [status]. [CTA review/cảm ơn]."
  → has_url = 0 hoặc 1 (link đánh giá)

Sub-type C – Cập nhật trạng thái (~40% batch):
  → Đơn đang chuẩn bị, đang giao, giao thất bại, hoàn trả
```

**Draft prompt template:** 

```python
ECOMMERCE_LEGIT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn thương mại điện tử hợp lệ (label=0).
Sàn TMĐT: {brands}
Loại thông báo: Mix đa dạng OTP xác thực / Đơn hàng / Trạng thái giao hàng
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một sàn từ danh sách trên cho mỗi dòng.
  - Format mã đơn hàng ĐÚNG từng sàn:
      * Shopee: #YYMMDDXXXXXXX (ví dụ: #240327MNKLPY)
      * Tiki: TKI-XXXXXXXXXX (dạng số)
      * Lazada: số đơn dài (ví dụ: 123456789012)
  - Mã OTP: 6 chữ số ngẫu nhiên (KHÔNG phải "XXXXXX")
  - Trạng thái đơn hàng cụ thể: "da dat thanh cong", "dang chuan bi", "da giao thanh cong"
  - Mã OTP KHÁC NHAU mỗi dòng, mã đơn hàng KHÁC NHAU mỗi dòng

SUB-TYPE (phân bổ đều):
  A – OTP/xác minh tài khoản (~40%): "KHONG chia se ma nay voi nguoi khac, ke ca nhan vien [sàn]"
  B – Xác nhận đơn hàng (~30%): thông báo sau khi đặt hàng thành công
  C – Giao hàng / hoàn trả (~30%): trạng thái vận chuyển, kết quả giao, yêu cầu đánh giá

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên mã, dùng làm tham chiếu):
SHOPEE: DE CAP NHAT MAT KHAU, ma xac minh la 131929. Co hieu luc trong 15 phut. KHONG chia se ma nay voi nguoi khac, ke ca nhan vien Shopee.|0|0|0|personal_number
Tiki: Ma xac minh dang ky tai khoan cua ban la 811962. Ma co hieu luc trong vong 15 phut. Khong chia se ma nay voi nguoi khac.|0|0|0|brandname
Shopee: Don hang #240327ABCXYZ cua ban da dat thanh cong. Du kien giao 28/03-30/03. Theo doi don tai app Shopee.|0|0|0|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (OTP và xác nhận), 1 nếu có link đánh giá/theo dõi sàn thật
  - has_phone = 0 (hầu hết TMĐT không có hotline trong SMS)
  - sender_type: brandname (~75%), personal_number (~25% – với Shopee OTP)
  - 40–180 ký tự
  - Mã OTP và mã đơn hàng KHÁC NHAU mỗi dòng

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```
### 7.5 Prompt Template – Vận chuyển & Logistics

**Đặc trưng bắt buộc cần capture:**

```
Format tracking ID theo từng ĐVVC:
  → GHN:       11 ký tự chữ hoa + số (ví dụ: GHNRXXXXXX hoặc SHNXXXXXXXX)
  → GHTK:      GHTK + 10 chữ số (ví dụ: GHTK1234567890)
  → Viettel Post: VTP + 11 ký tự
  → Ninja Van:  NVVNXXXXXXX

Trạng thái phổ biến:
  → "Dang phan loai tai kho [city]"
  → "Da giao thanh cong luc [time]"
  → "Giao khong thanh cong lan [N]. Lien he giao vien: [phone]" (has_phone=1)
  → "Kien hang se duoc hoan ve nguoi gui"
```

**Draft prompt template:**
```python
LOGISTICS_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn vận chuyển & logistics hợp lệ (label=0).
Đơn vị vận chuyển: {brands}
Loại thông báo: Mix đa dạng trạng thái vận đơn
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một ĐVVC từ danh sách trên cho mỗi dòng.
  - Format tracking ID ĐÚNG từng ĐVVC:
      * GHN:           Bắt đầu bằng GHNR hoặc SHNR + 7-8 ký tự chữ hoa/số (ví dụ: GHNR24032700001)
      * GHTK:          GHTK + 10 chữ số (ví dụ: GHTK1234567890)
      * Viettel Post:  VTP + 9-11 ký tự (ví dụ: VTP278134512)
      * Ninja Van:     NVVN + 8-9 ký tự (ví dụ: NVVN12345678)
      * J&T Express:   JT + 10-12 ký tự số (ví dụ: JT123456789012)
  - Tên kho: "kho Ha Noi", "kho TP.HCM", "kho Da Nang", "kho Binh Duong"
  - Khung giờ giao: "tu 8h-18h", "tu 8h-12h", "tu 13h-18h"
  - Số điện thoại giao viên (chỉ khi giao thất bại – 10 chữ số, format 0xxxxxxxxx)

SUB-TYPE (phân bổ đều):
  A – Đang phân loại tại kho (~30%): "Dang phan loai tai kho [city]. Du kien giao [date] (tu [giờ])."
  B – Giao thành công (~30%): "Da giao thanh cong luc [HH:MM]. Cam on da su dung dich vu."
  C – Giao thất bại / lấy lại (~25%): "Giao khong thanh cong lan [N]. Lien he giao vien: [SĐT]."
  D – Lấy hàng / hẹn giao lại (~15%): "Se den lay hang luc [time]. Vui long chuan bi kien hang."

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
[GHN] Van don GHNR24032700001: Dang phan loai tai kho TP.HCM. Du kien giao 28/03 (tu 8h-18h). Theo doi tai https://ghn.vn|0|1|0|brandname
GHTK-GHTK1234567890: Kien hang da giao thanh cong luc 14:35 ngay 27/03. Cam on ban da su dung dich vu GHTK!|0|0|0|brandname
[VTP] Ma van don: VTP278134512. Giao khong thanh cong lan 1. Lien he giao vien 0912345678 de dat lai lich giao.|0|0|1|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link theo dõi (ghn.vn, ghtk.vn, viettelpost.vn thật), 0 nếu không
  - has_phone = 1 nếu có SĐT giao viên (chỉ khi giao thất bại), 0 nếu không
  - sender_type: brandname (~80%), shortcode (~20%)
  - 60–200 ký tự
  - Tracking ID KHÁC NHAU mỗi dòng trong batch

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.6 Prompt Template – Quảng cáo hợp lệ

**Đặc trưng bắt buộc cần capture:**

```
Phân biệt Quảng cáo hợp lệ vs Smishing:
  ✅ Hợp lệ: Domain thật, mã KM cụ thể, điều kiện rõ ràng, ngày hết hạn
  ❌ Smishing: Link .vip/.top, "trúng thưởng miễn phí", không có điều kiện rõ ràng

Sub-type A – F&B (KFC, Lotteria, Jollibee, McDonald's) (~25%):
  → "Mua [combo] chi [price], tang [item] khi nhan ma [CODE]"
  → has_url = 0 hoặc 1 (link app)

Sub-type B – Siêu thị / Bán lẻ (WinMart, Co.opmart, Bách hóa xanh) (~25%):
  → "Giam [%] [category] tu [date_start] den [date_end]"
  → has_url = 0 hoặc 1 (link website thật)

Sub-type C – Dịch vụ tài chính / Ngân hàng (tín dụng, bảo hiểm) (~25%):
  → Đây là trường hợp phức tạp: marketing hợp lệ từ ngân hàng
  → PHÂN BIỆT với smishing: domain thật, không đe dọa, có opt-out

Sub-type D – App / Digital (Grab, Zalo Pay, MoMo) (~25%):
  → Thưởng voucher, cashback, đổi điểm
  → has_url = 1 (deep link app thật)
```

**Draft prompt template:** 
```python
ADS_LEGIT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn quảng cáo hợp lệ (label=0) từ thương hiệu thật.
Thương hiệu: {brands}
Mục tiêu: Quảng cáo có thật, có ưu đãi rõ ràng, KHÔNG phải scam
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một thương hiệu từ danh sách trên cho mỗi dòng.
  - Ưu đãi CỤ THỂ: % giảm, số tiền, combo, mã khuyến mãi (ví dụ: KFCAPP26, MOMO10K)
  - Điều kiện áp dụng RÕ RÀNG: thời hạn, điều kiện mua tối thiểu, kênh áp dụng
  - Domain thật: momo.vn, grab.com, kfc.com.vn, winmart.com.vn, ...
  - KHÔNG có "trúng thưởng miễn phí không điều kiện" – đây là dấu hiệu scam
  - CTA từ chối QC nếu là SMS marketing: "Soan TU CHOI gui 9999" (tùy brand)

PHÂN BIỆT hợp lệ vs scam:
  ✅ Hợp lệ: "KFC: Mua combo BigBox 129k tang 1 nuoc. Ma: KFCAPP26. Ap dung qua app den 31/3."
  ❌ Scam: "Chuc mung ban trung giai dac biet 50 trieu! Click ngay: bit.ly/xxx"

SUB-TYPE (phân bổ đều):
  A – F&B (KFC/Lotteria/Highland/The Coffee House) (~30%): combo deal, mã giảm giá app
  B – Fintech/Ví điện tử (MoMo/Grab/ZaloPay) (~35%): cashback, quà nạp tiền, tích điểm
  C – Siêu thị/Bán lẻ (WinMart/Co.opmart/Bách hóa xanh) (~20%): sale ngày lễ, mua sắm
  D – App tích điểm/thẻ thành viên (~15%): thông báo điểm sắp hết hạn, nâng hạng

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Ban co 10.000D qua Nap Dien Thoai & 140.000D qua khac trong MoMo, het han 31/10. Mo Vi > UU DAI > QUA CUA TOI dung ngay!|0|0|0|brandname
[TB] Quy khach nhan duoc voucher Giam 99.000d khi mua Bao hiem Xe may tu chuong trinh Uu dai Bao hiem het han ngay 31/07/2025. Mo app Viettel Money tai https://viettelmoney.go.link de biet them.|0|1|0|brandname
Highland Coffee: Mua 1 ca phe bat ky tang 1 banh mi trung ca phe. Ap dung thu 2-6, den 30/04/2026. Xem them: highland.coffee/uu-dai|0|1|0|shortcode

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link app/website thật, 0 nếu không
  - has_phone = 1 nếu có số hotline chăm sóc KH, 0 nếu không
  - sender_type: brandname (~55%), shortcode (~45%)
  - 60–250 ký tự
  - Ngày hết hạn ưu đãi PHẢI CỤ THỂ (ví dụ: 31/03/2026, không phải "sớm nhất")
  - KHÔNG dùng URL rút gọn ẩn danh (bit.ly, t.ly) – chỉ domain thật của brand

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.7 Prompt Template – Dịch vụ y tế

**Đặc trưng bắt buộc cần capture:**

```
Sub-type A – Nhắc lịch khám (~50% batch):
  → "[Hospital/Clinic]: Lich kham [time] ngay [date] tai [phong/khoa]."
  → Tên bệnh viện thực tế (Bach Mai, Viet Duc, Nhi TW, 108, ...)
  → Tên phòng/khoa thực tế
  → has_url = 0, has_phone = 0 hoặc 1

Sub-type B – OTP / Xác thực app y tế (~25% batch):
  → "[App] Ma xac thuc: [XXXXXX]. Co hieu luc trong [N] phut."
  → Ứng dụng: VNPT Health, eHospital, Medpro, ...

Sub-type C – Kết quả / nhắc nhở (~25% batch):
  → "Ket qua xet nghiem san sang. Xem tai ung dung [app] hoac den [dia_chi]."
  → "Nhac lich tai kham: [date]. Vui long lien he dat lai neu khong the den."
```

**Draft prompt template:**

```python
HEALTHCARE_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn dịch vụ y tế hợp lệ (label=0).
Tổ chức y tế / Ứng dụng: {brands}
Loại thông báo: Mix đa dạng nhắc lịch khám / OTP y tế / kết quả xét nghiệm
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một tổ chức từ danh sách trên cho mỗi dòng.
  - Tên bệnh viện ĐÚNG tên thật (Bệnh viện Bạch Mai, BV Việt Đức, BV Chợ Rẫy, BV 108, ...)
  - Tên phòng/khoa THỰC TẾ: Phòng 301, Khoa Tim mạch, Khoa Nhi, Khoa Xét nghiệm
  - OTP app y tế: 6 chữ số ngẫu nhiên, trong [3/5/10] phút
  - SĐT liên hệ nếu có: số hotline BV thật (02871026789, 02438253531, ...)
  - KHÔNG có urgency đe dọa – chỉ nhắc nhở lịch hẹn thân thiện

SUB-TYPE (phân bổ đều):
  A – Nhắc lịch khám (~45%): tên BV/phòng khám, giờ, ngày, phòng/khoa
  B – OTP app y tế (~25%): VNPT Health, eHospital, Medpro, BookingCare
  C – Kết quả xét nghiệm / nhắc tái khám (~30%): thông báo kết quả sẵn sàng, lịch tái khám

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot được tạo theo chuẩn thực tế – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Moi QK NGUYEN VAN ANH kham theo lich luc 8h30 ngay 28/03/2026 tai Phong 305 - Khoa Tim mach - BV Bach Mai. Vui long den dung gio va xuat trinh the BHYT.|0|0|0|brandname
VNPT Health: Ma xac thuc cua ban la: 284931. Co hieu luc trong 5 phut. KHONG chia se ma nay voi bat ky ai.|0|0|0|brandname
Phong kham Dr. Minh nhac lich kham ngay mai 28/03 luc 9h30. Co viec can doi lich vui long LH 0901234567 nhe.|0|0|1|personal_number

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (hầu hết), 1 nếu có link xem kết quả xét nghiệm trực tuyến
  - has_phone = 1 nếu có SĐT hotline BV hoặc phòng khám, 0 nếu không
  - sender_type: brandname (~60%), personal_number (~30%), shortcode (~10%)
  - 60–250 ký tự
  - Tên bệnh nhân phải là tên Việt thật (3 tiếng, họ tên đầy đủ), KHÔNG dùng "[TÊN]"

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.8 Prompt Template – Dịch vụ công thật

**Đặc trưng bắt buộc cần capture (PHÂN BIỆT với Dịch vụ công giả – Label 1 Cat 6):**

```
✅ Hợp lệ (Label 0):
  - Domain .gov.vn THẬT (bhxh.gov.vn, gdt.gov.vn, dichvucong.gov.vn)
  - KHÔNG có urgency đe dọa kiểu "thong bao cuoi cung"
  - KHÔNG có link lạ (.top, .vip) – chỉ link chính thống
  - Nội dung thông tin, không thúc ép hành động ngay

❌ Giả mạo (Label 1):
  - Domain .top/.xyz/.vip giả mạo cơ quan
  - Urgency mạnh, đe dọa xử lý hình sự
  - Link rút gọn che đích đến

Sub-type A – BHXH/BHYT (~35% batch):
  → "BHXH VN: The BHYT ma so [XXXXXXXXXXXX] het han [date]. LH BHXH [quan/huyen] gia han."
  → Không có link (has_url = 0 hầu hết)

Sub-type B – Thuế (~30% batch):
  → "Tong cuc Thue: Ky khai [ten_ky] ket thuc [date]. Dang nhap thuedientu.gdt.gov.vn."
  → Domain .gov.vn thật (has_url = 1)

Sub-type C – VNeID / Hành chính (~35% batch):
  → "Cong an [tinh/TP]: CCCD/CMND cua ban het han [date]. Den [dia_chi] de cap moi."
  → Không đe dọa, chỉ nhắc nhở lịch lịch
```

**Draft prompt template:**

```python
GOVT_LEGIT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn dịch vụ công hợp lệ (label=0).
Cơ quan / Tổ chức: {brands}
Ngữ cảnh batch này: {context}

PHÂN BIỆT hợp lệ vs giả mạo (QUAN TRỌNG):
  ✅ Hợp lệ (Label 0): domain .gov.vn THẬT, KHÔNG đe dọa, KHÔNG link lạ, thông tin thuần túy
  ❌ Giả mạo (Label 1): domain .top/.vip giả, urgency mạnh, link rút gọn che đích

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một cơ quan từ danh sách trên cho mỗi dòng.
  - KHÔNG có urgency đe dọa kiểu "thông báo cuối cùng", "sẽ bị xử lý hình sự"
  - KHÔNG có link lạ (.top, .vip, .xyz) – chỉ domain chính thống (.gov.vn, .edu.vn)
  - Nội dung thuần thông tin: nhắc nhở, thông báo, cảnh báo an toàn

SUB-TYPE (phân bổ đều):
  A – BHXH/BHYT (~25%): nhắc gia hạn thẻ, thông báo đăng ký thành công, mã số hưởng
  B – Thuế (~20%): nhắc kỳ khai thuế, hướng dẫn tra cứu thuedientu.gdt.gov.vn
  C – Bộ Công an / An ninh mạng (~25%): cảnh báo lừa đảo, nhắc gia hạn CCCD
  D – Tổ chức khác (~30%): hóa đơn điện/nước, thông báo học phí, MTTQ kêu gọi đóng góp

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
PCGV tran trong thong bao ke tu thang 07/2017 se khong thu tien tai nha, moi Quy KH thanh toan tien dien qua Ngan hang hoac cac diem thu ho. LH 1900545454|0|0|1|brandname
DHCNTT TB HOC PHI DOT 1 HK1 25-26 CUA SV Nguyen Hoang Duy (22520327) LA 18,500,000d, HAN NOP HP DOT 1 LA 28/9/2025. VUI LONG BO QUA TIN NHAN NEU DA NOP TIEN.|0|0|0|brandname
[TB] MTTQ Viet Nam keu goi chung tay ung ho dong bao bi thiet hai do bao lu gay ra. Cac tai khoan tiep nhan: 55102025 tai Vietinbank; 8639699999 tai BIDV. Chi tiet: mttqvietnam.org.vn|0|1|0|brandname

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 1 nếu có link .gov.vn hoặc .edu.vn thật, 0 nếu không
  - has_phone = 1 nếu có số hotline cơ quan (1900xxxx, 024xxxxxxx...), 0 nếu không
  - sender_type: brandname (~90%), shortcode (~10%)
  - 60–350 ký tự (thông báo cơ quan thường khá dài)
  - KHÔNG dùng domain giả – chỉ domain chính phủ/trường học thật

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.9 Prompt Template – Tin nhắn cá nhân & OTP

**Đặc trưng bắt buộc cần capture:**

```
Sub-type A – OTP ứng dụng bên thứ ba (~30% batch):
  → "[App/Service] Ma OTP: [XXXXXX]. Co hieu luc trong [N] phut."
  → Ứng dụng: Zalo, Facebook, Google, Netflix, các app Việt Nam
  → has_url = 0, sender_type = brandname hoặc shortcode

Sub-type B – Tin nhắn cá nhân thông thường (~40% batch):
  → Nội dung: nhắn nhau đi ăn, hỏi thăm, nhắc việc, thông báo
  → Văn phong tự nhiên, có thể bỏ dấu, có thể dùng từ lóng thông thường
  → has_url = 0, has_phone = 0, sender_type = personal_number

Sub-type C – OTP/thông báo từ dịch vụ nhỏ (~30% batch):
  → Đặt bàn nhà hàng, đặt phòng khách sạn, đặt vé xem phim
  → Mã xác nhận, thời gian, địa điểm
  → has_url = 0 hoặc 1, sender_type = personal_number hoặc shortcode
```

**Draft prompt template:**

```python
OTP_LEGIT_PROMPT = """
NHIỆM VỤ: Tạo đúng {size} dòng CSV tin nhắn cá nhân và OTP hợp lệ (label=0).
Ứng dụng / Ngữ cảnh: {brands}
Ngữ cảnh batch này: {context}

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU ĐA DẠNG: Trộn đều 3 sub-type bên dưới, KHÔNG để một sub-type chiếm toàn bộ batch.
  - OTP: 6 chữ số ngẫu nhiên thực tế (KHÔNG "000000", "123456", "XXXXXX")
  - Tin nhắn cá nhân: văn phong tự nhiên, có thể bỏ dấu, từ viết tắt thông thường (nha, ko, dc, thui)
  - KHÔNG có CTA đáng ngờ, KHÔNG link lạ, KHÔNG urgency thao túng

SUB-TYPE (phân bổ đều):
  A – OTP ứng dụng phổ biến (~35%): Google, Facebook, GitHub, Microsoft, Apple, Zalo, Steam, Netflix...
      Format: "[App] Ma OTP/xac thuc/dang nhap cua ban la: XXXXXX. Co hieu luc trong [N] phut."
      has_url = 0, sender_type = brandname hoặc shortcode

  B – Tin nhắn cá nhân thông thường (~40%): hỏi thăm, hẹn gặp, nhắc việc, thông báo gia đình
      Văn phong thân mật, có thể bỏ dấu hoặc dùng teencode nhẹ (ok, nha, dc, ko, thui)
      has_url = 0, has_phone = 0, sender_type = personal_number

  C – Xác nhận dịch vụ nhỏ (~25%): đặt bàn nhà hàng, đặt phòng, đặt vé, nhận hàng cá nhân
      Mã xác nhận, thời gian, địa điểm cụ thể
      has_url = 0 hoặc 1, sender_type = personal_number hoặc shortcode

PHONG CÁCH FORMAT:
{style}

VOCABULARY STYLE (áp dụng cho batch này):
{vocab_hint}

VÍ DỤ (few-shot từ data thực – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu):
Mã xác thực GitHub của bạn là: 733792|0|0|0|brandname
Use verification code 541118 for Microsoft authentication.|0|0|0|brandname
Hương đang làm gì vậy? Dạo này công việc thế nào rồi?|0|0|0|personal_number
Em Hà day. Goi lai vao so 0978123456 em co viec gap.|0|0|1|personal_number

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (hầu hết), 1 nếu có link dịch vụ thật (không rút gọn ẩn đích)
  - has_phone = 1 nếu có SĐT trong nội dung (chỉ Sub-type B/C), 0 nếu không
  - sender_type: brandname (~50%), personal_number (~45%), shortcode (~5%)
  - 5–150 ký tự (tin cá nhân rất ngắn; OTP ngắn gọn)
  - OTP KHÁC NHAU mỗi dòng
  - Sub-type B: tên người Việt tự nhiên, KHÔNG "[TÊN KHÁCH HÀNG]"

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

---

## 8. Few-Shot Examples Library

### 8.1 Nguyên tắc chọn Few-Shot cho Label 0

Examples phải được **trích từ `dataset_label_0.csv`** để đảm bảo tính thực tế.

**4 nguyên tắc cốt lõi** (kế thừa từ Label 1):

1. **Bao phủ đa dạng**: Mỗi example thể hiện 1 combination khác nhau của `(sender_type × sub-type × formality_level)`
2. **Đủ ngắn**: 2–3 examples là tối ưu
3. **Trích từ real data**: Ưu tiên mẫu từ `dataset_label_0.csv`
4. **Luôn dùng đầy đủ 5 cột**: Pipe-delimited `content|label|has_url|has_phone_number|sender_type`

**4 nguyên tắc riêng cho Label 0:**

```
5. Data động đúng format (không placeholder literal):
   ✅ OTP: "Ma OTP cua ban la: 847392"  (không phải "XXXXXX")
   ✅ Số TK: "TK 123456****7890"        (không phải "[SO_TAI_KHOAN]")
   ✅ Mã đơn: "#240327MNKLPY"           (format thực Shopee)
   ✅ Tracking: "GHNRXXX123456"         (format thực GHN)

6. Brand-specific format đúng:
   Mỗi ngân hàng có prefix riêng → few-shot phải thể hiện đúng
   MB: "[MB] TK ..." / VCB: "[VCB] ..." / BIDV: "BIDV:" / Techcombank: "Techcombank:"

7. Anonymization đặc thù Label 0:
   - Số tài khoản thật → masked (giữ 4 số cuối, che phần còn lại)
   - Tên người dùng thật → thay bằng tên Việt giả
   - Số điện thoại cá nhân → thay bằng số giả đúng format
   - Mã OTP/mã đơn hàng thật → tạo lại mã mới đúng format

8. Không được dùng domain giả:
   few-shot phải thể hiện ĐÚNG domain hợp lệ (mbbank.com.vn không phải mb-bank.top)
```

**Coverage Matrix lý tưởng** (3 examples cho Label 0):

```
  Example 1: brandname + Level 0  → OTP hoặc giao dịch ngân hàng (template cứng)
  Example 2: shortcode + Level 1  → TMĐT hoặc logistics (template mềm, data động)
  Example 3: personal_number + Level 3–4 → Personal hoặc SME (informal, tự nhiên)
```

### 8.2 Candidates cho Banking Legit Examples (Cat 1)

> **Trạng thái:** ✅ Điền từ `dataset_label_0.csv` (Sprint 0 – 27/03/2026)  
> Tổng mẫu ngân hàng thật trong dataset: **35 mẫu** (chủ yếu OTP + cảnh báo bảo mật)

**Coverage Matrix:**

| Candidate | Sub-type                 | Formality | has_url | has_phone | sender_type | Unique pattern                                        |
| --------- | ------------------------ | --------- | ------- | --------- | ----------- | ----------------------------------------------------- |
| C1        | OTP xác thực giao dịch   | 0         | 0       | 1         | brandname   | "Ma OTP la XXXXXX. de xac nhan giao dich (TRU TIEN)"  |
| C2        | OTP Digibank, hết hạn 1p | 0         | 0       | 0         | brandname   | "[VCB] Ma OTP xac thuc GD, hieu luc 1 phut"           |
| C3        | Cảnh báo bảo mật         | 0         | 0       | 0         | brandname   | "KHONG yeu cau cung cap TEN DANG NHAP, MAT KHAU, OTP" |

**Few-shot examples (trích từ `dataset_label_0.csv`):**

```
Ma OTP la 22085377. de xac nhan giao dich (TRU TIEN) tu The cua quy khach. Vui long giu bao mat va khong chia se OTP cho bat cu ai. LH Techcombank: 1800588822|0|0|1|brandname
Ma OTP xac thuc GD la 972501, hieu luc 1 phut. Chi tiet GD:Chuyen khoan nhanh qua so TK,so tien 22,700,000 VND tren kenh Internet cua dich vu VCB Digibank.|0|0|0|brandname
Vietcombank KHONG yeu cau cung cap TEN DANG NHAP, MAT KHAU, OTP qua cac duong link gui qua SMS. Quy khach hay canh giac va TUYET DOI KHONG cung cap thong tin.|0|0|0|brandname
```

**Ghi chú:** Dataset có ít mẫu giao dịch (số dư) và nhắc thẻ tín dụng → prompt cần nhấn mạnh sinh đủ Sub-type B và C.

### 8.3 Candidates cho Telecom Examples (Cat 2)

> **Trạng thái:** ✅ Điền từ `dataset_label_0.csv` (Sprint 0 – 27/03/2026)  
> Tổng mẫu viễn thông trong dataset: **966 mẫu** – category LỚN NHẤT (41.5% dataset)  
> Phân phối: brandname 81%, shortcode 19%, personal_number ~0%  
> has_url = 81% (cao nhất tất cả category), has_phone = 50%

**Coverage Matrix:**


| Candidate | Brand   | Sub-type             | Formality | has_url | has_phone | sender_type | Unique pattern                   |
| --------- | ------- | -------------------- | --------- | ------- | --------- | ----------- | -------------------------------- |
| C1        | Viettel | Khuyến mãi nạp thẻ   | 0         | 1       | 0         | brandname   | [TB] NẠP THẺ + link viettel.vn   |
| C2        | Viettel | Hết data, nhắc nạp   | 0         | 0       | 0         | shortcode   | "da dung het luu luong data"     |
| C3        | iTel    | Điểm thành viên Club | 1         | 1       | 1         | brandname   | "so diem iTel Club", link myitel |

**Few-shot examples (trích từ `dataset_label_0.csv`):**

```
[TB] NẠP THẺ ĐỦ ĐẦY - DATA XÀI NGAY! Tặng 20% giá trị tất cả thẻ nạp vào tài khoản viễn thông trong ngày 25/11/2025. Tiền KM sử dụng truy cập Internet trong 15 ngày. Nạp thẻ online tại https://viettel.vn/naptienkm . Chi tiết gọi 197 bấm phím 19 (0đ). Trân trọng.|0|1|0|brandname
Quy khach da dung het luu luong data cua CT Viettel++ va tiep tuc truy cap theo goi Mobile Internet dang su dung (neu co). Chi tiet LH 198 (0d). Tran trong.|0|0|0|shortcode
iTel TB: Den het thang 01/2023, Quy khach dang la hoi vien Than Thiet, so diem iTel Club la 200. Diem iTel Club co gia tri su dung trong vong 12 thang ke tu thang kich hoat. Truy cap app MyiTel tai http://onelink.to/myitel de nhan va su dung nhieu uu dai hap dan tu iTel Club. Chi tiet LH 0877087087 (0d cho TB iTel). Tran trong!|0|1|1|brandname
```

**Ghi chú:** Viettel chiếm đa số; cần thiết kế prompt trộn Vinaphone, MobiFone, Vietnamobile, iTel để tránh monotony.

### 8.4 Candidates cho E-commerce Examples (Cat 3)

> **Trạng thái:** ✅ Điền từ `dataset_label_0.csv` (Sprint 0 – 27/03/2026)  
> Tổng mẫu TMĐT trong dataset: **12 mẫu** – chủ yếu là OTP/xác minh tài khoản, THIẾU đơn hàng/giao hàng  
> Phân phối: brandname 75%, personal_number 25%  
> has_url = 8%, has_phone = 8% (rất thấp – đặc trưng OTP không có link)

**Coverage Matrix:**

| Candidate | Platform | Sub-type              | Formality | has_url | has_phone | sender_type     | Unique pattern              |
| --------- | -------- | --------------------- | --------- | ------- | --------- | --------------- | --------------------------- |
| C1        | Shopee   | OTP cập nhật mật khẩu | 1         | 0       | 0         | personal_number | "DE CAP NHAT MAT KHAU", 15p |
| C2        | Tiki     | OTP đăng ký tài khoản | 1         | 0       | 0         | brandname       | "dang ky tai khoan", 15p    |
| C3        | Shopee   | OTP đổi số điện thoại | 1         | 0       | 0         | brandname       | "CAP NHAT SO DIEN THOAI"    |

**Few-shot examples (trích từ `dataset_label_0.csv`):**

```
SHOPEE: DE CAP NHAT MAT KHAU, ma xac minh la 131929. Co hieu luc trong 15 phut. KHONG chia se ma nay voi nguoi khac, ke ca nhan vien Shopee.|0|0|0|personal_number
Tiki: Ma xac minh dang ky tai khoan cua ban la 811962. Ma co hieu luc trong vong 15 phut. Khong chia se ma nay voi nguoi khac.|0|0|0|brandname
SHOPEE: DE CAP NHAT SO DIEN THOAI, nhap ma xac minh 391146. Ma co hieu luc trong 15 phut. KHONG chia se ma nay voi nguoi khac, ke ca nhan vien Shopee.|0|0|0|brandname
```

**Ghi chú:** Dataset THIẾU mẫu đơn hàng, giao hàng, hoàn trả → prompt phải nhấn mạnh Sub-type B/C để bổ sung. Cần tạo synthetic cho: xác nhận đơn, trạng thái giao hàng, yêu cầu đánh giá.

### 8.5 Candidates cho Logistics Examples (Cat 4)

> **Trạng thái:** ⚠️ KHÔNG CÓ DỮ LIỆU THỰC (Sprint 0 – 27/03/2026)  
> Tổng mẫu vận chuyển trong dataset: **0 mẫu** – Category hoàn toàn vắng trong ground truth  
> → Toàn bộ few-shot phải được tạo thủ công dựa trên kiến thức thực tế về từng ĐVVC

**Coverage Matrix:**

| Candidate | ĐVVC         | Sub-type               | Formality | has_url | has_phone | sender_type | Unique pattern                  |
| --------- | ------------ | ---------------------- | --------- | ------- | --------- | ----------- | ------------------------------- |
| C1        | GHN          | Đang phân loại tại kho | 0         | 1       | 0         | brandname   | GHNR + tracking ID, link ghn.vn |
| C2        | GHTK         | Giao thành công        | 0         | 0       | 0         | brandname   | GHTK + 10 chữ số tracking       |
| C3        | Viettel Post | Giao thất bại, SĐT GV  | 1         | 0       | 1         | brandname   | VTP tracking, số giao viên      |

**Few-shot examples (SYNTHETIC – viết thủ công theo chuẩn thực tế, KHÔNG từ dataset):**

```
[GHN] Van don GHNR24032700001: Dang phan loai tai kho TP.HCM. Du kien giao 28/03 (tu 8h-18h). Theo doi tai https://ghn.vn|0|1|0|brandname
GHTK-GHTK1234567890: Kien hang da giao thanh cong luc 14:35 ngay 27/03. Cam on ban da su dung dich vu GHTK!|0|0|0|brandname
[VTP] Ma van don: VTP278134512. Giao khong thanh cong lan 1. Lien he giao vien 0912345678 de dat lai lich giao.|0|0|1|brandname
```

**Hành động cần thiết (Sprint 1):** Thu thập 10–20 mẫu vận chuyển thực tế từ điện thoại → thay thế few-shot synthetic bằng real data.

### 8.6 Candidates cho Legit Ads Examples (Cat 5)

> **Trạng thái:** ✅ Điền từ `dataset_label_0.csv` (Sprint 0 – 27/03/2026)  
> Tổng mẫu quảng cáo hợp lệ trong dataset: **169 mẫu** (7.3%)  
> Phân phối: brandname 54%, shortcode 46%, personal_number 1%  
> has_url = 54%, has_phone = 64% (cao bất thường – nhiều mẫu có hotline chăm sóc KH)

**Coverage Matrix:**

| Candidate | Brand         | Sub-type            | Formality | has_url | has_phone | sender_type     | Unique pattern                    |
| --------- | ------------- | ------------------- | --------- | ------- | --------- | --------------- | --------------------------------- |
| C1        | MoMo          | Quà nạp điện thoại  | 1         | 0       | 0         | brandname       | "Mo Vi > UU DAI > QUA CUA TOI"    |
| C2        | Viettel Money | Voucher bảo hiểm    | 1         | 1       | 0         | brandname       | Link go.link, ngày hết hạn cụ thể |
| C3        | FPT Voice     | Chúc mừng sinh nhật | 2         | 1       | 0         | personal_number | Link fpt-voice.net                |

**Few-shot examples (trích từ `dataset_label_0.csv`):**

```
Ban co 10.000D qua Nap Dien Thoai & 140.000D qua khac trong MoMo, het han 31/10. Mo Vi > UU DAI > QUA CUA TOI dung ngay!|0|0|0|brandname
[TB] Quy khach nhan duoc voucher Giam 99.000d khi mua Bao hiem Xe may tu chuong trinh Uu dai Bao hiem het han ngay 31/07/2025. Vui long mo app Viettel Money tai https://viettelmoney.go.link/kFsDU de biet them thong tin chi tiet. Tran trong!|0|1|0|brandname
CHÚC MỪNG SINH NHẬT Quý khách. Kính chúc Quý khách luôn hạnh phúc, thành công và thịnh vượng. Cảm ơn Quý khách đã luôn đồng hành cùng fpt-voice.net|0|1|0|personal_number
```

**Ghi chú:** has_phone cao (64%) vì nhiều quảng cáo có hotline tư vấn. MoMo chiếm nhiều mẫu lặp ("Ban co X.000D qua...") → prompt cần yêu cầu diversity.

### 8.7 Candidates cho Healthcare Examples (Cat 6)

> **Trạng thái:** ⚠️ RẤT ÍT DỮ LIỆU (Sprint 0 – 27/03/2026)  
> Tổng mẫu y tế trong dataset: **8 mẫu** (0.3%) – gần như vắng  
> Chỉ 1 mẫu chất lượng tốt (nhắc lịch tiêm vaccine); phần còn lại là số điện thoại đơn thuần  
> → Phần lớn few-shot phải viết thủ công

**Coverage Matrix:**

| Candidate | Sub-type               | Formality | has_url | has_phone | sender_type     | Unique pattern                        |
| --------- | ---------------------- | --------- | ------- | --------- | --------------- | ------------------------------------- |
| C1        | Nhắc lịch tiêm chủng   | 2         | 1       | 1         | brandname       | Tên BV, mã đặt lịch, xét nghiệm Covid |
| C2        | Nhắc lịch khám định kỳ | 2         | 0       | 0         | brandname       | Phòng, giờ, khoa, tên BV cụ thể       |
| C3        | OTP app y tế           | 0         | 0       | 0         | brandname       | "Ma xac thuc: XXXXXX, 5 phut"         |
| C4        | PK nhỏ – thân thiện    | 3         | 0       | 1         | personal_number | Informal, SĐT phòng khám              |

**Few-shot examples (C1 từ dataset; C2/C3/C4 synthetic theo chuẩn thực tế):**

```
Moi QK HOANG THI THUY tiem vacxin ngay 29/09/21 (BQ525).QK co mat luc 13:25 de xet nghiem Covid truoc khi vao BV. BV tu choi phuc vu neu khong xuat trinh Tin nhan hop le, giay to tuy than khong trung Thong tin da dang ky tren he thong. Vui long doc huong dan tai https://bit.ly/hdTC. LH 02871026789|0|1|1|brandname
Moi QK NGUYEN VAN ANH kham theo lich luc 8h30 ngay 28/03/2026 tai Phong 305 - Khoa Tim mach - BV Bach Mai. Vui long den dung gio va xuat trinh the BHYT.|0|0|0|brandname
VNPT Health: Ma xac thuc cua ban la: 284931. Co hieu luc trong 5 phut. KHONG chia se ma nay voi bat ky ai.|0|0|0|brandname
Phong kham Dr. Minh nhac lich kham ngay mai 28/03 luc 9h30. Co viec can doi lich vui long LH 0901234567 nhe.|0|0|1|personal_number
```

**Hành động cần thiết (Sprint 1):** Thu thập thêm mẫu nhắc lịch khám từ bệnh viện thật → bổ sung vào few-shot library.

### 8.8 Candidates cho Gov Service Legit Examples (Cat 7)

> **Trạng thái:** ✅ Điền từ `dataset_label_0.csv` (Sprint 0 – 27/03/2026)  
> Tổng mẫu dịch vụ công thật trong dataset: **67 mẫu** (2.9%)  
> Phân phối: brandname 91%, shortcode 9% – KHÔNG có personal_number  
> has_url = 18%, has_phone = 31%  
> **Ghi chú:** Dataset có BHXH, MTTQ, DHCNTT (học phí/điểm), PCGV (điện lực), Bộ Công an (cảnh báo scam)

**Lưu ý đặc biệt:** Category này là đối nghịch trực tiếp với Cat 6 của Label 1. Few-shot thể hiện rõ: KHÔNG đe dọa, KHÔNG link .top/.vip, nội dung thuần thông tin.

**Coverage Matrix:**

| Candidate | Đơn vị      | Sub-type                    | Formality | has_url | has_phone | sender_type | Unique pattern (vs Label 1 Cat 6)             |
| --------- | ----------- | --------------------------- | --------- | ------- | --------- | ----------- | --------------------------------------------- |
| C1        | PCGV (Điện) | Thay đổi quy trình thu tiền | 0         | 0       | 1         | brandname   | LH hotline 1900xxxx, không link, không đe dọa |
| C2        | MTTQ VN     | Kêu gọi hỗ trợ đồng bào     | 0         | 0       | 0         | brandname   | STK ngân hàng thật, không link lạ             |
| C3        | DHCNTT      | Thông báo học phí sinh viên | 0         | 0       | 0         | brandname   | Mã SV, số tiền, hạn nộp cụ thể                |
| C4        | Bộ Công an  | Cảnh báo lừa đảo/deepfake   | 0         | 0       | 0         | brandname   | Dài, đầy đủ thông tin, không CTA link         |

**Few-shot examples (trích từ `dataset_label_0.csv`):**

```
PCGV tran trong thong bao ke tu thang 07/2017 se khong thu tien tai nha, moi Quy KH thanh toan tien dien qua Ngan hang hoac cac diem thu ho. LH 1900545454|0|0|1|brandname
[TB] MTTQ Viet Nam keu goi chung tay ung ho dong bao bi thiet hai do bao lu gay ra. Cac tai khoan tiep nhan: 55102025 tai Vietinbank; 8639699999 tai BIDV; 1400666102025 tai Agribank; 8888881010 tai Vietcombank; 0606 tai MBbank.|0|0|0|brandname
DHCNTT TB HOC PHI DOT 1 HK1 25-26 CUA SV Nguyen Hoang Duy (22520327) LA 18,500,000d, HAN NOP HP DOT 1 LA 28/9/2025. VUI LONG BO QUA TIN NHAN NEU DA NOP TIEN.|0|0|0|brandname
```

**Hành động cần thiết (Sprint 1):** Cần bổ sung mẫu BHXH/BHYT và Tổng cục Thuế từ thực tế (hiện chưa có trong ground truth).

### 8.9 Candidates cho Personal & OTP Examples (Cat 8)

> **Trạng thái:** ✅ Điền từ `dataset_label_0.csv` (Sprint 0 – 27/03/2026)  
> Tổng mẫu cá nhân & OTP trong dataset: **252 mẫu** (10.8%)  
> Phân phối: brandname 59%, personal_number 39%, shortcode 2%  
> has_url = 5%, has_phone = 3% (rất thấp – OTP và chat cá nhân không có link/SĐT)  
> Content length: ngắn nhất (mean 101 ký tự) – đặc trưng tin nhắn cá nhân

**Coverage Matrix:**

| Candidate | Sub-type                  | Formality | has_url | has_phone | sender_type     | Unique pattern                        |
| --------- | ------------------------- | --------- | ------- | --------- | --------------- | ------------------------------------- |
| C1        | OTP GitHub (tiếng Việt)   | 0         | 0       | 0         | brandname       | "Ma xac thuc ... cua ban la: XXXXXX"  |
| C2        | OTP Microsoft (tiếng Anh) | 0         | 0       | 0         | brandname       | "Use verification code XXXXXX for..." |
| C3        | Chat hỏi thăm bạn bè      | 4         | 0       | 0         | personal_number | Văn phong thân mật, tên người Việt    |
| C4        | Chat nhắc việc có SĐT     | 4         | 0       | 1         | personal_number | Ngắn, có SĐT liên hệ, urgent nhẹ      |

**Few-shot examples (trích từ `dataset_label_0.csv`):**

```
Mã xác thực GitHub của bạn là: 733792|0|0|0|brandname
Use verification code 541118 for Microsoft authentication.|0|0|0|brandname
Hương đang làm gì vậy? Dạo này công việc thế nào rồi?|0|0|0|personal_number
Em Hà day. Goi lai vao so 0978123456 em co viec gap.|0|0|1|personal_number
```

**Ghi chú:** brandname chiếm 59% vì nhiều OTP từ Google/GitHub/Microsoft là brandname. Cần đảm bảo Sub-type B (personal chat) được sinh đủ, tránh toàn bộ batch là OTP.

### 8.10 Nguyên tắc Anonymization trong Few-Shot Examples (Label 0)

| Loại thông tin                                             | Quyết định                           | Cách xử lý đúng                                                 |
| ---------------------------------------------------------- | ------------------------------------ | --------------------------------------------------------------- |
| **Brand name thật** (MB Bank, Shopee, GHN)                 | **Giữ nguyên**                       | Calibrate format cụ thể từng brand                              |
| **Domain thật trong content** (.mbbank.com.vn, .shopee.vn) | **Giữ nguyên**                       | Đây là domain hợp lệ, cần để model học phân biệt với domain giả |
| **Số tài khoản ngân hàng thật**                            | **Masked – giữ format**              | 123456****7890 (che phần giữa, giữ 4 số cuối)                   |
| **Mã OTP thật**                                            | **Thay bằng mã giả đúng format**     | 6 chữ số ngẫu nhiên không phải "000000" hay "123456"            |
| **Mã đơn hàng thật**                                       | **Thay bằng mã giả đúng format**     | Giữ đúng format từng sàn (Shopee: #YYMMDDXXXXXXX)               |
| **Tracking ID thật**                                       | **Thay bằng ID giả đúng format**     | Giữ prefix đúng từng ĐVVC (GHN: GHNR + 8 ký tự)                 |
| **Số điện thoại cá nhân thật**                             | **Thay bằng số giả đúng format**     | Format VN: 0xxxxxxxxx (10 chữ số, không toàn 0)                 |
| **Tên người dùng thật**                                    | **Thay bằng tên Việt giả hoàn toàn** | Giữ pattern họ tên Việt 3 tiếng                                 |

**Nguyên tắc cốt lõi:**

```
❌ SAI – Dùng placeholder trừu tượng:
   "Ma OTP cua ban la: [OTP]"       → Model học in placeholder "[OTP]" vào output
   "Don hang [ORDER_ID] da giao"    → Model không học được format mã đơn hàng thực
   "TK [MASKED_ACCOUNT] +500,000"   → Model không học được format che số TK

✅ ĐÚNG – Thay bằng dữ liệu giả nhưng đúng format:
   "Ma OTP cua ban la: 847392"      → Model học: OTP = 6 chữ số
   "Don hang #240327MNKLPY da giao" → Model học: Shopee format = #YYMMDD + 6 ký tự
   "TK 123456****7890 +500,000VND"  → Model học: masked account format
```

---

## 9. Checklist đánh giá chất lượng

### 9.1 Format Validation (sau khi đã đủ data – hiện chưa kiểm tra)

```python
def validate_legit_row(row: list[str]) -> dict:
    """Kiểm tra tự động sau khi model sinh ra."""
    checks = {}
    
    # F1 – Số cột
    checks["f1_columns"] = len(row) == 5
    
    # F2 – Label đúng (phải là 0 cho legitimate)
    checks["f2_label"] = row[1].strip() == "0"
    
    # F3 – has_url hợp lệ
    checks["f3_has_url"] = row[2].strip() in ("0", "1")
    
    # F4 – has_phone_number hợp lệ
    checks["f4_has_phone"] = row[3].strip() in ("0", "1")
    
    # F5 – sender_type hợp lệ
    checks["f5_sender"] = row[4].strip() in ("personal_number", "brandname", "shortcode")
    
    # F6 – Độ dài content
    content_len = len(row[0].strip().strip('"'))
    checks["f6_length"] = 15 <= content_len <= 300
    
    # F7 – Consistency: has_url = 1 nếu có URL pattern
    import re
    has_url_pattern = bool(re.search(r'https?://|www\.|\.vn|\.com\.vn|\.gov\.vn', row[0]))
    checks["f7_url_consistency"] = not (has_url_pattern and row[2].strip() == "0")
    
    # F8 – Không có domain giả mạo (TLD lạ)
    fake_tld_pattern = bool(re.search(r'\.(vip|top|xyz|cc|icu|cfd|life|biz)\b', row[0]))
    checks["f8_no_fake_domain"] = not fake_tld_pattern
    
    # F9 – Không có placeholder literal
    placeholder_pattern = bool(re.search(r'\[OTP\]|\[BRAND\]|\[XXXXXX\]|\[ORDER_ID\]', row[0]))
    checks["f9_no_placeholder"] = not placeholder_pattern
    
    return checks
```

### 9.2 Content Quality (review thủ công)

Sau mỗi lần chạy batch mới, review ngẫu nhiên 10% mẫu theo checklist:

- Content có giống SMS hợp lệ thực tế của Việt Nam không?
- Brand name và format có đúng với nhà gửi không? (ví dụ: MB không dùng format BIDV)
- Domain/URL có phải domain hợp lệ thực tế không? (không có .vip, .top)
- Data động (OTP, số TK, tracking ID) có đúng format thực không?
- Không có placeholder literal trong content?
- Urgency (nếu có) là urgency hợp lệ, không phải thao túng tâm lý?
- sender_type có khớp với loại tổ chức gửi không?
- Nội dung không lặp lại với mẫu khác trong batch (đặc biệt OTP code)?

### 9.3 Distribution Check (sau khi thu thập đủ data – hiện chưa triển khai)

```python
import pandas as pd

def check_distribution_label0(filepath: str):
    df = pd.read_csv(filepath)
    
    print("=== DISTRIBUTION REPORT – LABEL 0 ===")
    print(f"Total: {len(df)}")
    print(f"\nlabel distribution:\n{df['label'].value_counts()}")
    print(f"\nsender_type:\n{df['sender_type'].value_counts(normalize=True)}")
    print(f"\nhas_url:\n{df['has_url'].value_counts(normalize=True)}")
    print(f"\nhas_phone_number:\n{df['has_phone_number'].value_counts(normalize=True)}")
    
    # Target phân phối Label 0:
    # sender_type: ~45% brandname, ~35% shortcode, ~20% personal_number
    # has_url: ~35% = 1 (thấp hơn Label 1 do OTP/giao dịch không có URL)
    # has_phone: ~15% = 1 (thấp hơn Label 1)
```

### 9.4 Boundary Check – Phân biệt Label 0 vs Label 1

Đây là checklist **đặc thù của Label 0** – kiểm tra xem synthetic data có thực sự phân biệt được với smishing không:

```python
BOUNDARY_INDICATORS = {
    # Chỉ xuất hiện trong Label 0 (legitimate)
    "legit_only": [
        r"\.(vn|com\.vn|gov\.vn)",           # TLD hợp lệ
        r"(bhxh|gdt|dichvucong)\.gov\.vn",   # domain dịch vụ công thật
        r"So du: \d{1,3}(,\d{3})*VND",       # format số dư chuẩn
        r"Ma OTP.*KHONG chia se",             # cảnh báo OTP đúng kiểu
        r"\*{4}\d{4}",                        # masked account number
    ],
    # KHÔNG được xuất hiện trong Label 0
    "smishing_only": [
        r"\.(vip|top|xyz|cc|icu|cfd)",        # TLD giả mạo
        r"t\.ly/|bit\.ly/|shorturl\.at/",     # URL rút gọn ẩn đích
        r"KHONG HOP TAC|bat hop tac",         # đe dọa đòi nợ
        r"NQ-116|quy B[/\-]H[/\-]T[/\-]N",  # BHXH scam pattern
        r"oZGa|hkDF|JKqc",                   # random tracking code BHXH scam
    ]
}
```

---

## 10. Roadmap cải tiến

### 10.1 Sprint 0 – Chuẩn bị ✅ HOÀN THÀNH (27/03/2026)

- **[P0] ✅** Thu thập `dataset_label_0.csv` từ thực tế (2325 SMS hợp lệ đã gắn nhãn thủ công)
- **[P0] ✅** Phân tích phân phối 8 category trong real data → cập nhật Category Mapping Table (Section 7.1)
- **[P0] ✅** Xác định format đặc trưng của từng brand (ngân hàng, logistics, TMĐT)
- **[P0] ✅** Chốt: Cấu trúc `SCENARIOS_LABEL0` dictionary trong `gen_label_0.py` (8 categories)
- **[P1] ✅** Xác định `CATEGORY_FORMAL_RANGE` tương đương `CATEGORY_OBF_RANGE` của Label 1
- **[P1] ✅** Thiết kế hàm `pick_formality_style()` tương đương `pick_mixed_style()` của Label 1
- **[P1] ✅** Viết lại `gen_label_0.py` theo kiến trúc `gen_label_1.py` (pipe-delimited, dedup, retry, 8 prompts)
- **[P1] ✅** Điền few-shot library Section 8.2–8.9 từ `dataset_label_0.csv`

**Kết quả phân tích dataset (trả lời các câu hỏi Sprint 0):**


| Câu hỏi                        | Trả lời                                                     |
| ------------------------------ | ----------------------------------------------------------- |
| Tổng mẫu `dataset_label_0.csv` | **2325 mẫu**                                                |
| Category lớn nhất              | Viễn thông (966 mẫu, 41.5%)                                 |
| Category vắng hoàn toàn        | Vận chuyển (0 mẫu)                                          |
| Category cực ít                | Y tế (8), TMĐT đơn hàng (0), Ngân hàng giao dịch (~5)       |
| sender_type dominant           | brandname (75.6%), shortcode (19.9%), personal (4.6%)       |
| has_url                        | 49% = 1 (cao hơn dự kiến)                                   |
| has_phone                      | 41% = 1 (cao hơn dự kiến)                                   |
| TOTAL_SAMPLES (synthetic)      | **3000 mẫu** (để bù category imbalance)                     |
| Generate song song Label 1?    | Có thể độc lập – không phụ thuộc                            |
| "Quảng cáo hợp lệ" vs scam     | Đã chốt: domain thật + mã KM cụ thể + ngày hết hạn = hợp lệ |


### 10.2 Sprint 1 – Xây dựng Few-Shot Library ✅ HOÀN THÀNH (27/03/2026)

- **[P0] ✅** Phân tích và chọn candidates cho 8 sections (8.2–8.9)
- **[P0] ✅** Kiểm tra anonymization theo nguyên tắc Section 8.10
- **[P0] ✅** Double-check consistency: metadata (5 cột) ↔ nội dung content
- **[P1] ✅** Xây dựng Coverage Matrix cho từng category


| Category               | Few-shot           | Trạng thái                               |
| ---------------------- | ------------------ | ---------------------------------------- |
| 1 – Ngân hàng thật     | ✅ 3 mẫu real       | ✅ Điền vào prompt – thiếu sub-type B/C   |
| 2 – Viễn thông         | ✅ 3 mẫu real       | ✅ Điền vào prompt – đủ diversity         |
| 3 – Thương mại điện tử | ✅ 3 mẫu real       | ✅ Điền vào prompt – OTP chính, thiếu GH  |
| 4 – Vận chuyển         | ⚠️ 3 mẫu synthetic | ✅ Điền vào prompt – 0 real data          |
| 5 – Quảng cáo hợp lệ   | ✅ 3 mẫu real       | ✅ Điền vào prompt – Highland Coffee mới  |
| 6 – Dịch vụ y tế       | ⚠️ 1 real + 3 syn  | ✅ Điền vào prompt – cần bổ sung Sprint 4 |
| 7 – Dịch vụ công thật  | ✅ 3 mẫu real       | ✅ Điền vào prompt – MTTQ link bỏ ra      |
| 8 – Cá nhân & OTP      | ✅ 4 mẫu real       | ✅ Điền vào prompt – đủ diversity         |


### 10.3 Sprint 2 – Thiết kế Prompt Templates ✅ HOÀN THÀNH (27/03/2026)

- **[P0] ✅** Thiết kế đầy đủ 8 prompt templates (Section 7.2–7.9)
- **[P0] ✅** Điền few-shot examples vào templates
- **[P0] ✅** Final cross-check: Template ↔ Few-shot
- **[P0] ✅** Triển khai `gen_label_0.py` kế thừa kiến trúc `gen_label_1.py`
- **[P1] ✅** Thêm negative constraints cụ thể cho từng category

**Những gì đã triển khai trong `gen_label_0.py` v2 (vượt kế hoạch):**

```
Kế thừa từ gen_label_1.py:
  ✅ Kiến trúc batch generation (BATCH_SIZE=40, extract_valid_rows)
  ✅ Pipe-delimited parsing với "last 4 parts" approach
  ✅ csv.writer re-serialization (RFC 4180)
  ✅ load_seen_contents() deduplication
  ✅ Retry + exponential backoff (MAX_RETRIES=3)

Thay đổi (kế hoạch Sprint 2):
  ✅ label_value = 0 (thay vì 1)
  ✅ SCENARIOS_LABEL0 (8 categories mới)
  ✅ CATEGORY_FORMAL_RANGE + pick_formality_style()
  ✅ 8 prompt templates (7.2–7.9) với 5 tham số mỗi template
  ✅ Validation F8 (no_fake_domain) + F9 (no_placeholder)

Bổ sung ngoài kế hoạch (Sprint 3-prep):
  ✅ [QUOTA] CATEGORY_QUOTA + build_category_queue()
  ✅ [CONTEXT] CONTEXT_VARIANTS + pick_context()
  ✅ [VOCAB] VOCAB_HINTS + pick_vocab_hint()
  ✅ [TEMP] PER_CATEGORY_TEMPERATURE per-category (0.75–0.92)
  ✅ [VALID] F7 URL-consistency check
  ✅ Cột category trong output CSV (6 cột thay vì 5)
  ✅ load_category_counts() để resume đúng quota
  ✅ Model: gemini-2.5-flash-preview-04-17
```

### 10.4 Sprint 3 – Chạy & Đánh giá ⏳ ĐANG TIẾN HÀNH

- **[P0] ⏳** Chạy `gen_label_0.py` để sinh 3000 mẫu Label 0 theo quota
- **[P0]** Chạy thử batch nhỏ (10–20 rows/category) → kiểm tra format và metadata
- **[P1]** Boundary test: dùng model phân loại đơn giản, kiểm tra xem Label 0 có bị nhầm thành Label 1 không
- Đo Fidelity: cosine similarity với `dataset_label_0.csv` real data
- Đo Diversity: inter-sample cosine similarity (Label 0 dễ bị thấp vì OTP template)
- Kết hợp Label 0 + Label 1 → train thử mô hình phân loại → đo F1 tổng thể

**Câu hỏi cần monitor trong Sprint 3 (từ Phiên 3):**

1. Tỷ lệ reject do F7 tăng bao nhiêu so với không có F7?
2. `VOCAB_HINTS` "bỏ dấu hoàn toàn" có gây false reject không?
3. Category Vận chuyển (400 samples hoàn toàn synthetic) có chất lượng đủ tốt không?
4. Personal & OTP (500 samples) có giữ được boundary với Label 1 crypto scam ngắn không?

---

## Ghi chú thảo luận

> **Phần này dùng để ghi lại các quyết định và thảo luận trong quá trình cập nhật**

### [2026-03-27] Phiên thảo luận thứ ba – Sprint 2 hoàn thành, gen_label_0.py v2

**Bối cảnh:** Sau Phiên 2 (Sprint 0 hoàn thành, few-shot library điền đầy đủ), `gen_label_0.py` đã được nâng cấp lên v2 với 5 cải tiến quan trọng, hoàn tất Sprint 1–2 và chuẩn bị sẵn sàng cho Sprint 3 (chạy sinh data).

---

#### A. Model và tham số cập nhật


| Thay đổi              | Giá trị cũ      | Giá trị mới                      |
| --------------------- | --------------- | -------------------------------- |
| Model                 | (chưa chỉ định) | `gemini-2.5-flash-preview-04-17` |
| BATCH_SIZE            | (chưa chỉ định) | 40                               |
| SLEEP_BETWEEN_BATCHES | (chưa chỉ định) | 12 giây                          |
| MAX_RETRIES           | (chưa chỉ định) | 3                                |
| Output schema         | 5 cột           | 6 cột (thêm `category`)          |


---

#### B. 5 Cải tiến chính trong gen_label_0.py v2

**[QUOTA] Category Quota Sampling**

- **Vấn đề:** `random.choice()` thuần túy không đảm bảo phân phối quota → Viễn thông (41.5% ground truth) chiếm quá nhiều batch.
- **Giải pháp:** `CATEGORY_QUOTA` dict + `build_category_queue()`. Queue proportional với remaining quota, shuffle ngẫu nhiên, resume được sau interrupt.
- **CATEGORY_QUOTA đã chốt:**


| Category                | Quota    | Lý do                                          |
| ----------------------- | -------- | ---------------------------------------------- |
| Ngân hàng thật          | 450      | Ranh giới quan trọng nhất với smishing banking |
| Viễn thông              | 300      | Template tương đối cứng, ít variation          |
| Thương mại điện tử      | 400      | Nhiều sàn, nhiều trạng thái đơn                |
| Vận chuyển              | 400      | Nhiều ĐVVC, nhiều trạng thái giao              |
| Quảng cáo hợp lệ        | 350      | Boundary tinh tế với smishing ads              |
| Dịch vụ y tế            | 300      | Formal range rộng, cần diversity               |
| Dịch vụ công thật       | 300      | Ranh giới trực tiếp với Label 1 Cat 6          |
| Tin nhắn cá nhân và OTP | 500      | Ambiguous nhất, cần nhiều examples             |
| **Tổng**                | **3000** |                                                |


**[CONTEXT] Context Variants per-category**

- **Vấn đề:** Batch khác nhau vẫn sinh nội dung tương tự → thiếu situational diversity.
- **Giải pháp:** `CONTEXT_VARIANTS` với 7–8 tình huống cụ thể per-category. `pick_context()` chọn ngẫu nhiên mỗi batch, inject qua `{context}`.
- **Kết quả:** Variation tăng từ 3 chiều → **5 chiều** `(brand × formality × sub-type × context × vocab)`.

**[VOCAB] Vocabulary Style Hints**

- **Vấn đề:** Model dùng template cố định → dataset thiếu lexical diversity.
- **Giải pháp:** `VOCAB_HINTS` list (7 hints), `pick_vocab_hint()` chọn ngẫu nhiên, inject vào Layer 4 qua `{vocab_hint}`.
- **7 hints:** viết tắt SMS (TK/GD/KM), viết đầy đủ formal, bỏ dấu hoàn toàn, có dấu đầy đủ, câu cực ngắn, câu đầy đủ tự nhiên, mix ngắn-dài.
- **Lưu ý:** Hint "bỏ dấu hoàn toàn" ≠ leet → không vi phạm F8/F9.

**[TEMP] Per-Category Temperature**

- **Vấn đề:** Temperature cố định không phù hợp với đặc thù từng category.
- **Giải pháp:** `PER_CATEGORY_TEMPERATURE` dict. Template cứng (0.75–0.78) → nhất quán format; Semi-formal (0.80–0.85); Personal/Quảng cáo (0.90–0.92) → lexical diversity.

**[VALID] F7 URL-consistency check**

- **Vấn đề:** Model đôi khi sinh has_url=0 nhưng content chứa URL → metadata sai.
- **Pattern:** `re.compile(r'https?://|www\.|\.(vn|com\.vn|gov\.vn|edu\.vn)\b', re.I)`
- **Logic:** Nếu has_url=0 mà pattern match → reject row. Tích hợp sau F1–F6 (cũ), trước F8–F9.

---

#### C. Cập nhật Output Schema

Thêm cột `category` → **6 cột** (thay vì 5):

```
content | label | has_url | has_phone_number | sender_type | category
```

Mục đích: theo dõi quota real-time, resume đúng sau interrupt, phân tích chất lượng theo category.

---

#### D. Điều chỉnh sender_type distributions so với Phiên 2


| Category               | Phiên 2 (cũ)                               | Phiên 3 (thực tế trong prompt)                        | Lý do                                |
| ---------------------- | ------------------------------------------ | ----------------------------------------------------- | ------------------------------------ |
| Viễn thông             | brandname 60%, shortcode 40%               | brandname **80%**, shortcode 20%                      | Ground truth thực tế 81% brandname   |
| Thương mại điện tử     | brandname 80%, shortcode 20%               | brandname 75%, **personal_number 25%**                | Shopee OTP hay dùng personal_number  |
| Quảng cáo hợp lệ       | shortcode 55%, brandname 45%               | **brandname 55%**, shortcode 45%                      | Điều chỉnh theo data thực            |
| Dịch vụ y tế           | brandname 60%, shortcode 30%, personal 10% | brandname 60%, **personal_number 30%**, shortcode 10% | PK nhỏ → personal_number nhiều hơn   |
| Dịch vụ công thật      | brandname 70%, shortcode 30%               | brandname **90%**, shortcode 10%                      | Ground truth 91% brandname           |
| Tin nhắn cá nhân & OTP | personal_number 60%, shortcode 30%         | **brandname 50%**, personal_number 45%, shortcode 5%  | OTP từ Google/GitHub/MS là brandname |


---

#### E. Các câu hỏi mở từ Phiên 2 đã giải quyết


| Câu hỏi (Phiên 2)                             | Giải pháp (Phiên 3)                              |
| --------------------------------------------- | ------------------------------------------------ |
| Dùng `random.choice()` hay weighted sampling? | [QUOTA] `build_category_queue()` – quota-driven  |
| Cách tăng diversity trong mỗi batch?          | [CONTEXT] + [VOCAB] – 2 chiều variation mới      |
| Temperature cố định có phù hợp không?         | [TEMP] per-category temperature (0.75–0.92)      |
| has_url inconsistency (model tự ý thêm URL)?  | [VALID] F7 URL-consistency check                 |
| Cat4 Vận chuyển 0 real data → chất lượng?     | Synthetic few-shot viết thủ công theo chuẩn ĐVVC |


---

#### F. Câu hỏi mở chuyển sang Sprint 3

1. **Tỷ lệ reject F7:** Tăng bao nhiêu % so với F1–F6 cũ? Cần monitor để đánh giá hiệu quả VOCAB hint.
2. **Hiệu quả [CONTEXT]:** Context injection có thực sự tăng inter-sample diversity không? → Đo cosine similarity giữa các batch cùng category.
3. **Vận chuyển (Cat4) quality:** 400 samples hoàn toàn synthetic → review thủ công tỷ lệ cao hơn (20% thay vì 10%).
4. **Personal & OTP (Cat8) boundary:** 500 samples, nhiều personal_number → kiểm tra boundary với Label 1 crypto scam ngắn.
5. **[VOCAB] "bỏ dấu" + brand strict:** Khi dùng hint bỏ dấu với ngân hàng, output có giữ đúng brand format không?

---

### [2026-03-27] Phiên thảo luận thứ hai – Sprint 0 hoàn thành

**Bối cảnh:** Label 1 đã hoàn thành Sprint 2 (8 prompt templates + few-shot library đầy đủ, `gen_label_1.py` hoạt động ổn định). Phiên này thực hiện toàn bộ Sprint 0 cho Label 0 từ `dataset_label_0.csv` có sẵn.

---

#### A. Phân tích `dataset_label_0.csv`

Dùng script Python phân tích thống kê và phân loại 8 category bằng keyword heuristics. Kết quả:

**Phân phối tổng thể (2325 mẫu):**


| Chỉ số                       | Giá trị   |
| ---------------------------- | --------- |
| Total rows                   | 2325      |
| sender_type: brandname       | 75.6%     |
| sender_type: shortcode       | 19.9%     |
| sender_type: personal_number | 4.6%      |
| has_url = 1                  | 49%       |
| has_phone_number = 1         | 41%       |
| Content length (mean)        | 229 ký tự |


**Phân phối category (heuristic classification):**


| Category          | Mẫu   | %      | Tình trạng                                 |
| ----------------- | ----- | ------ | ------------------------------------------ |
| Viễn thông        | 966   | 41.5%  | Dominant – Viettel chiếm đa số             |
| Cá nhân & OTP     | 252   | 10.8%  | Personal chat + OTP từ GitHub/Microsoft    |
| Quảng cáo hợp lệ  | 169   | 7.3%   | MoMo chiếm nhiều mẫu lặp                   |
| Dịch vụ công thật | 67    | 2.9%   | DHCNTT, PCGV, MTTQ, Bộ Công an             |
| Ngân hàng thật    | 35    | 1.5%   | Chủ yếu OTP + cảnh báo bảo mật             |
| TMĐT              | 12    | 0.5%   | Chỉ OTP xác minh tài khoản, thiếu đơn hàng |
| Y tế              | 8     | 0.3%   | Gần như vắng                               |
| **Vận chuyển**    | **0** | **0%** | **Hoàn toàn không có mẫu thực**            |


**Quan sát quan trọng:**

- `has_url = 49%` và `has_phone = 41%` – cao hơn nhiều so với dự đoán ban đầu trong tài liệu (ước tính 35% và 15%)
- Nguyên nhân: dataset nặng về Viễn thông (Viettel luôn kèm link nạp thẻ và hotline) và Quảng cáo (thường có hotline)
- Dataset thiếu hẳn mẫu giao dịch ngân hàng (số dư, chuyển khoản) – chỉ có OTP và cảnh báo bảo mật. 
  - Lời giải thích: Đa phần các ngân hàng hiện nay đã triển khai app riêng của họ, việc thông báo giao dịch ngân hàng hầu như đều đã chuyển sang thông báo trên app và không còn thông qua SMS nữa. Riêng các hình thức xác nhận giao dịch thì SMS OTP vẫn còn được sử dụng bên cạnh SMART OTP.

---

#### B. Quyết định kỹ thuật – `gen_label_0.py` viết lại hoàn toàn

**Vấn đề với phiên bản cũ:**

- Dùng `google.generativeai` SDK cũ (không tương thích với `gen_label_1.py`)
- 3-level (Level 1/2/3) không phản ánh đúng 8 category đặc thù của Label 0
- Toàn bộ prompt là PLACEHOLDER – chưa có nội dung thực tế
- Parser dùng comma CSV (dễ lỗi với content chứa dấu phẩy)
- Không có deduplication `load_seen_contents()`

**Các quyết định trong phiên bản mới:**


| Quyết định             | Chi tiết                                                                   |
| ---------------------- | -------------------------------------------------------------------------- |
| SDK                    | Nâng lên `google.genai` (cùng với `gen_label_1.py`)                        |
| Format                 | Pipe-delimited `                                                           |
| Dedup                  | `load_seen_contents()` – kế thừa hoàn toàn từ Label 1                      |
| TOTAL_SAMPLES          | 3000 (để bù category imbalance trong ground truth)                         |
| Safety filters         | Không tắt – Label 0 là nội dung lành mạnh                                  |
| SCENARIOS_LABEL0       | 8 categories × danh sách brand đầy đủ                                      |
| CATEGORY_FORMAL_RANGE  | Thay `CATEGORY_OBF_RANGE` – formal levels [0,4] thay vì obfuscation        |
| pick_formality_style() | Tương đương `pick_mixed_style()` của Label 1                               |
| validate_row_label0()  | Thêm 2 check mới: `no_fake_domain` (.vip/.top) + `no_placeholder` literal  |
| Few-shot               | 6 category dùng real data; Cat4 (Vận chuyển) và Cat6 (Y tế) dùng synthetic |


`**CATEGORY_FORMAL_RANGE` đã chốt:**

```python
"Ngân hàng thật":          (0, 1)   # Template cứng đến mềm
"Viễn thông":              (0, 1)   # Template cứng đến mềm
"Thương mại điện tử":      (1, 1)   # Template mềm nhất quán
"Vận chuyển":              (0, 1)   # Template cứng đến mềm
"Quảng cáo hợp lệ":       (1, 2)   # Mềm đến bán formal
"Dịch vụ y tế":            (2, 3)   # Bán formal đến thân thiện
"Dịch vụ công thật":       (0, 1)   # Template cứng đến mềm
"Tin nhắn cá nhân và OTP": (0, 4)   # Toàn spectrum: OTP cứng → personal hoàn toàn
```

---

#### C. Trả lời các câu hỏi mở từ Phiên 1


| Câu hỏi mở (Phiên 1)                                | Quyết định (Phiên 2)                                                                                                                                                      |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Quảng cáo hợp lệ" vs Smishing – ranh giới?         | **Domain thật + mã KM cụ thể + ngày hết hạn = hợp lệ.** Link rút gọn của chính brand (l.grab.com, onelink.to/myitel) vẫn là hợp lệ vì không che đích đến thương hiệu giả. |
| Personal message scope?                             | **Bao gồm cả chat hoàn toàn cá nhân** (hỏi thăm, hẹn gặp). Đây là hard negative quan trọng – model cần học phân biệt với crypto scam "thả tim" ngắn.                      |
| Overlap Label 0 vs Label 1 – cần negative examples? | **Có, đã tích hợp vào prompt**: Cat7 dịch vụ công có block "PHÂN BIỆT hợp lệ vs giả mạo" trực tiếp trong prompt, Cat5 quảng cáo có block "PHÂN BIỆT hợp lệ vs scam".      |
| Teencode cá nhân là "obfuscation"?                  | **Không – là đặc trưng tự nhiên Label 0.** Formal Level 4 cho phép bỏ dấu + từ viết tắt thông thường (nha, ko, dc) nhưng KHÔNG dùng leet (0=o, 4=a, @, #).                |


---

#### D. Few-shot Library – Trạng thái sau Phiên 2


| Category           | Nguồn few-shot | Số mẫu | Ghi chú                                     |
| ------------------ | -------------- | ------ | ------------------------------------------- |
| Cat1 Ngân hàng     | Real data      | 3      | Thiếu sub-type giao dịch (số dư)            |
| Cat2 Viễn thông    | Real data      | 3      | Đủ diversity (brandname + shortcode + iTel) |
| Cat3 TMĐT          | Real data      | 3      | Chỉ có OTP, thiếu đơn hàng/giao hàng        |
| Cat4 Vận chuyển    | **Synthetic**  | 3      | 0 mẫu thực → cần bổ sung Sprint 1           |
| Cat5 Quảng cáo     | Real data      | 3      | MoMo + Viettel Money + FPT                  |
| Cat6 Y tế          | 1 real + 3 syn | 4      | Cần bổ sung thực tế Sprint 1                |
| Cat7 Dịch vụ công  | Real data      | 3      | PCGV + MTTQ + DHCNTT                        |
| Cat8 Cá nhân & OTP | Real data      | 4      | GitHub + Microsoft + personal chat          |


---

#### E. Câu hỏi mở chuyển sang Sprint 1

1. **Category imbalance trong quá trình sinh**: Hiện tại `random.choice()` chọn đều 8 categories → Viễn thông sẽ được sinh bằng tất cả các category khác. Có nên dùng `random.choices()` với trọng số ưu tiên Cat4/Cat6/Cat1 để bù thiếu hụt trong ground truth không?
2. **Vận chuyển (Cat 4)**: 0 mẫu trong ground truth → thu thập 10–20 mẫu SMS GHN/GHTK/VTP thực tế trước Sprint 2
3. **Y tế (Cat 6)**: Chỉ 1 mẫu chất lượng tốt → thu thập thêm mẫu nhắc lịch khám BV thực tế
4. **Personal message (Cat 8)**: personal_number chỉ 4.6% trong ground truth nhưng quan trọng cho hard negative boundary – synthetic data có nên boost tỷ lệ này lên ~15–20% không?
5. **has_phone consistency**: Ground truth có has_phone = 41% (cao hơn dự đoán) → kiểm tra xem mẫu synthetic có reproduce được tỷ lệ này không sau Sprint 3

### [2026-03-26] Phiên thảo luận đầu tiên – Khởi tạo Document

**Bối cảnh:** Document này được tạo song song với khi Label 1 đã hoàn thành Sprint 2 (8 prompt templates + few-shot library đã điền đầy đủ). Label 0 bắt đầu từ Sprint 0.

**Các quyết định kiến trúc ban đầu:**

1. **Giữ nguyên 4-layer architecture** từ Label 1 → giảm learning curve, đảm bảo consistency
2. **Giữ nguyên pipe-delimited format** → parser tương thích, không cần viết lại infrastructure
3. **8 categories** phản ánh đúng thực tế SMS Việt Nam (không bắt buộc số lượng bằng Label 1)
4. **Không cần Safety Framing** – Label 0 hoàn toàn lành mạnh, không cần framing đặc biệt như Label 1

**Câu hỏi mở (cần thảo luận trong phiên tiếp theo):**

1. **"Quảng cáo hợp lệ" vs Smishing:** Ranh giới nằm ở đâu khi một brand lớn gửi SMS khuyến mãi có link rút gọn (ví dụ: Grab gửi link l.grab.com/xxx)?
2. **Personal message scope:** Có nên include tin nhắn giữa 2 cá nhân hoàn toàn không liên quan thương mại không (ví dụ: "Alo, tối nay ăn ở đâu?")? Hay chỉ tập trung vào OTP và dịch vụ?
3. **Overlap với Label 1 Categories:** Một số Category của Label 0 là đối nghịch trực tiếp với Label 1 (Gov Service thật vs Gov Service giả, Ngân hàng thật vs Ngân hàng giả). Có cần thiết kế negative examples trong prompt để model học rõ boundary không?
4. **Mức obfuscation của tin nhắn cá nhân:** Người Việt hay bỏ dấu khi nhắn tin, hay dùng teencode nhẹ (ok → oke, không → k). Có tính đây là "obfuscation" hay là đặc trưng tự nhiên của Label 0?

---

