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


### 7.2 Prompt Template – Ngân hàng thật

> **TODO – Cần thiết kế chi tiết**

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

ĐẶC TRƯNG BẮT BUỘC:
  - YÊU CẦU TRỘN BRAND: Chọn NGẪU NHIÊN một ngân hàng từ danh sách trên cho mỗi dòng.
  - Prefix đúng brand: "[MB]", "[VCB]", "[BIDV]", "Techcombank:", "ACB:", ...
  - Số tài khoản PHẢI masked: dạng 123456****7890 hoặc ****7890
  - Mã OTP: 6 chữ số ngẫu nhiên thực tế (KHÔNG dùng "XXXXXX" hay "123456")
  - Số tiền: có dấu phân cách nghìn (2,345,678VND không phải 2345678VND)
  - KHÔNG có urgency đe dọa ("bị khóa", "mất toàn bộ") – chỉ thông tin thuần túy
  - KHÔNG có link (has_url = 0 với OTP và giao dịch)
  - Sender: brandname (70%) hoặc shortcode (30%)

PHONG CÁCH FORMAT:
  Level 0 (OTP và giao dịch): Template cứng – format cố định theo brand
  Level 1 (thông báo khác): Template mềm – có thể có câu hoàn chỉnh

VÍ DỤ (few-shot – pipe-delimited, KHÔNG copy nguyên, dùng làm tham chiếu style):
[PLACEHOLDER – sẽ điền sau khi có real data]

QUY TẮC FORMAT (pipe-delimited):
  content|0|has_url|has_phone_number|sender_type
  - Dùng | làm delimiter. KHÔNG dùng dấu nháy kép hay nháy đơn bao quanh content.
  - has_url = 0 (OTP và giao dịch), 0 hoặc 1 (nhắc nhở)
  - has_phone = 1 nếu có hotline trong nội dung, 0 nếu không
  - sender_type: brandname (~70%), shortcode (~30%)
  - 20–160 ký tự
  - Mã OTP và số tài khoản KHÁC NHAU mỗi dòng

QUAN TRỌNG: Đúng {size} dòng pipe-delimited. Không header. Không giải thích. Không markdown.
"""
```

### 7.3 Prompt Template – Viễn thông

> **TODO – Cần thiết kế chi tiết**

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

### 7.5 Prompt Template – Vận chuyển & Logistics

> **TODO – Cần thiết kế chi tiết**

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

### 7.6 Prompt Template – Quảng cáo hợp lệ

> **TODO – Cần thiết kế chi tiết**

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

### 7.7 Prompt Template – Dịch vụ y tế

> **TODO – Cần thiết kế chi tiết**

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

### 7.8 Prompt Template – Dịch vụ công thật

> **TODO – Cần thiết kế chi tiết**

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

### 7.9 Prompt Template – Tin nhắn cá nhân & OTP

> **TODO – Cần thiết kế chi tiết**

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

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | Sub-type                  | Formality | has_url  | has_phone | sender_type | Unique pattern              |
| --------- | ------------------------- | --------- | -------- | --------- | ----------- | --------------------------- |
| C1        | OTP, 6 chữ số, 5 phút     | 0         | 0        | 0         | brandname   | "[BRAND] Ma OTP: XXXXXX"    |
| C2        | Giao dịch, masked account | 0         | 0        | 0         | brandname   | "+/-amount, So du: balance" |
| C3        | Nhắc thẻ tín dụng / điểm  | 1         | 0 hoặc 1 | 0 hoặc 1  | brandname   | "den han", "diem thuong"    |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.3 Candidates cho Telecom Examples (Cat 2)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | Brand     | Sub-type            | Formality | has_url | has_phone | sender_type | Unique pattern                |
| --------- | --------- | ------------------- | --------- | ------- | --------- | ----------- | ----------------------------- |
| C1        | Viettel   | Đăng ký gói cước    | 0         | 0       | 0         | brandname   | Tên gói, ngày hết hạn         |
| C2        | Vinaphone | Cảnh báo số dư thấp | 0         | 0       | 0         | shortcode   | USSD code, nạp thêm           |
| C3        | MobiFone  | Khuyến mãi tháng    | 1         | 1       | 0         | brandname   | Link vinaphone.vn/mobifone.vn |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.4 Candidates cho E-commerce Examples (Cat 3)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | Platform | Sub-type             | Formality | has_url | has_phone | sender_type | Unique pattern        |
| --------- | -------- | -------------------- | --------- | ------- | --------- | ----------- | --------------------- |
| C1        | Shopee   | Xác nhận đơn hàng    | 1         | 1       | 0         | brandname   | #240327XXXXXXX format |
| C2        | Tiki     | Giao hàng thành công | 1         | 1       | 0         | brandname   | Link đánh giá tiki.vn |
| C3        | Lazada   | Hoàn trả được duyệt  | 1         | 0       | 0         | brandname   | Hoàn tiền 5–7 ngày    |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.5 Candidates cho Logistics Examples (Cat 4)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | ĐVVC         | Sub-type               | Formality | has_url | has_phone | sender_type | Unique pattern            |
| --------- | ------------ | ---------------------- | --------- | ------- | --------- | ----------- | ------------------------- |
| C1        | GHN          | Đang phân loại tại kho | 0         | 0       | 0         | brandname   | GHNRXXXXXXX tracking ID   |
| C2        | GHTK         | Giao thành công        | 0         | 0       | 0         | brandname   | GHTK tracking format      |
| C3        | Viettel Post | Giao thất bại, SĐT GV  | 1         | 0       | 1         | brandname   | has_phone=1, số giao viên |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.6 Candidates cho Legit Ads Examples (Cat 5)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | Brand   | Sub-type         | Formality | has_url | has_phone | sender_type | Unique pattern                |
| --------- | ------- | ---------------- | --------- | ------- | --------- | ----------- | ----------------------------- |
| C1        | KFC     | F&B combo deal   | 2         | 1       | 0         | shortcode   | Mã KM, link app, ngày hết hạn |
| C2        | WinMart | Siêu thị sale    | 2         | 1       | 0         | shortcode   | % giảm, ngày, domain thật     |
| C3        | MoMo    | Digital cashback | 1         | 1       | 0         | brandname   | Link deep app, momo.vn        |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.7 Candidates cho Healthcare Examples (Cat 6)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | Sub-type           | Formality | has_url | has_phone | sender_type     | Unique pattern           |
| --------- | ------------------ | --------- | ------- | --------- | --------------- | ------------------------ |
| C1        | Nhắc lịch khám BV  | 2         | 0       | 0         | brandname       | Tên BV, phòng, giờ       |
| C2        | OTP app y tế       | 0         | 0       | 0         | shortcode       | "[App] Ma OTP: XXXXXX"   |
| C3        | Nhắc nhở từ PK nhỏ | 3         | 0       | 1         | personal_number | Informal, SĐT phòng khám |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.8 Candidates cho Gov Service Legit Examples (Cat 7)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Lưu ý đặc biệt:** Category này là đối nghịch trực tiếp với Cat 6 của Label 1 (Dịch vụ công giả). Few-shot phải thể hiện rõ ràng điểm khác biệt.

**Coverage Matrix:**


| Candidate | Đơn vị        | Sub-type          | Formality | has_url | has_phone | sender_type | Unique pattern (vs Label 1 Cat 6)     |
| --------- | ------------- | ----------------- | --------- | ------- | --------- | ----------- | ------------------------------------- |
| C1        | BHXH VN       | Nhắc gia hạn BHYT | 0–1       | 0       | 0         | brandname   | Domain bhxh.gov.vn thật, không đe dọa |
| C2        | Tổng cục Thuế | Nhắc kỳ khai thuế | 1         | 1       | 0         | brandname   | thuedientu.gdt.gov.vn thật            |
| C3        | Công an tỉnh  | Nhắc gia hạn CCCD | 1         | 0       | 1         | brandname   | Địa chỉ cụ thể, không link giả        |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

### 8.9 Candidates cho Personal & OTP Examples (Cat 8)

> **TODO – Cần điền sau khi có `dataset_label_0.csv`**

**Coverage Matrix:**


| Candidate | Sub-type                 | Formality | has_url | has_phone | sender_type     | Unique pattern                     |
| --------- | ------------------------ | --------- | ------- | --------- | --------------- | ---------------------------------- |
| C1        | OTP ứng dụng phổ biến    | 0         | 0       | 0         | shortcode       | "[App] Ma OTP: 6 so"               |
| C2        | Tin nhắn cá nhân thường  | 4         | 0       | 0         | personal_number | Văn phong thân mật, không template |
| C3        | Xác nhận đặt dịch vụ nhỏ | 3         | 0       | 1         | personal_number | Đặt bàn/phòng/vé, thời gian        |


```
[PLACEHOLDER – điền candidates sau khi thu thập dataset_label_0.csv]
```

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

### 10.1 Sprint 0 – Chuẩn bị (Hiện tại)

- **[P0]** Thu thập `dataset_label_0.csv` từ thực tế (SMS hợp lệ đã gắn nhãn thủ công)
- **[P0]** Phân tích phân phối 8 category trong real data → điều chỉnh Category Mapping Table (Section 7.1)
- **[P0]** Xác định format đặc trưng của từng brand (ngân hàng, logistics, TMĐT)
- **[P0]** Thảo luận và chốt: Cấu trúc `SCENARIOS_LABEL0` dictionary cho `gen_label_0.py`
- **[P1]** Xác định mức `CATEGORY_FORMAL_RANGE` tương đương `CATEGORY_OBF_RANGE` của Label 1
- **[P1]** Thiết kế hàm `pick_formality_style()` tương đương `pick_mixed_style()` của Label 1

**Câu hỏi cần trả lời trước khi bắt đầu Sprint 1:**

1. Có bao nhiêu mẫu trong `dataset_label_0.csv`? Phân phối theo category thế nào?
2. TOTAL_SAMPLES cho Label 0 là bao nhiêu? (1500? 2000? tương đương Label 1?)
3. Có cần generate đồng thời hay tuần tự với Label 1?
4. "Quảng cáo hợp lệ" – ngưỡng phân biệt với smishing là gì? Cần thảo luận.

### 10.2 Sprint 1 – Xây dựng Few-Shot Library

**Điều kiện tiên quyết:** Đã có `dataset_label_0.csv` với đủ mẫu thực tế.

- **[P0]** Phân tích và chọn candidates cho 8 sections (8.2–8.9)
- **[P0]** Kiểm tra anonymization theo nguyên tắc Section 8.10
- **[P0]** Double-check consistency: metadata (5 cột) ↔ nội dung content
- **[P1]** Xây dựng Coverage Matrix cho từng category


| Category               | Few-shot  | Trạng thái  |
| ---------------------- | --------- | ----------- |
| 1 – Ngân hàng thật     | ❌ Chưa có | Chờ dataset |
| 2 – Viễn thông         | ❌ Chưa có | Chờ dataset |
| 3 – Thương mại điện tử | ❌ Chưa có | Chờ dataset |
| 4 – Vận chuyển         | ❌ Chưa có | Chờ dataset |
| 5 – Quảng cáo hợp lệ   | ❌ Chưa có | Chờ dataset |
| 6 – Dịch vụ y tế       | ❌ Chưa có | Chờ dataset |
| 7 – Dịch vụ công thật  | ❌ Chưa có | Chờ dataset |
| 8 – Cá nhân & OTP      | ❌ Chưa có | Chờ dataset |


### 10.3 Sprint 2 – Thiết kế Prompt Templates

- **[P0]** Thiết kế đầy đủ 8 prompt templates (Section 7.2–7.9) từ draft hiện tại
- **[P0]** Điền few-shot examples từ Sprint 1 vào templates
- **[P0]** Final cross-check: Template ↔ Few-shot (phát hiện mâu thuẫn)
- **[P0]** Triển khai `gen_label_0.py` kế thừa kiến trúc `gen_label_1.py`
- **[P1]** Thêm negative constraints cụ thể cho từng category

**Kế hoạch triển khai `gen_label_0.py`:**

```
Kế thừa từ gen_label_1.py:
  - Kiến trúc batch generation (BATCH_SIZE, extract_valid_rows)
  - Pipe-delimited parsing với "last 4 parts" approach
  - csv.writer re-serialization (RFC 4180)
  
Thay đổi:
  - label_value = 0 (thay vì 1)
  - SCENARIOS_LABEL0 (8 categories mới)
  - CATEGORY_FORMAL_RANGE (thay CATEGORY_OBF_RANGE)
  - pick_formality_style() (thay pick_mixed_style())
  - 8 prompt templates mới (Section 7.2–7.9)
  - Validation: thêm F8 (no_fake_domain) + F9 (no_placeholder)
```

### 10.4 Sprint 3 – Chạy & Đánh giá

- Chạy thử batch nhỏ (10–20 rows/category) → kiểm tra format và metadata
- **[P1]** Boundary test: dùng model phân loại đơn giản, kiểm tra xem Label 0 có bị nhầm thành Label 1 không
- Đo Fidelity: cosine similarity với `dataset_label_0.csv` real data
- Đo Diversity: inter-sample cosine similarity (Label 0 dễ bị thấp vì OTP template)
- Kết hợp Label 0 + Label 1 → train thử mô hình phân loại → đo F1 tổng thể

---

## Ghi chú thảo luận

> **Phần này dùng để ghi lại các quyết định và thảo luận trong quá trình cập nhật**

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

