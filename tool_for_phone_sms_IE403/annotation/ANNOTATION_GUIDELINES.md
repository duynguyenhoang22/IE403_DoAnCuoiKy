# 📋 GUIDELINES GÁN NHÃN SMS SMISHING

## 🎯 MỤC ĐÍCH

Xây dựng bộ dữ liệu huấn luyện chất lượng cao để phát hiện tin nhắn SMS độc hại (spam, lừa đảo/smishing) bằng cách gán nhãn 3 loại thông tin:

1. **label** - Phân loại tin nhắn
2. **has_url** - Có/Không có URL trong nội dung
3. **has_phone_number** - Có/Không có SĐT trong nội dung

---

## 1️⃣ GÁN NHÃN: **LABEL** (Phân loại Smishing)

### 📖 Định nghĩa

**SMISHING (SMS Phishing)** là hình thức lừa đảo qua tin nhắn SMS nhằm:

- Đánh cắp thông tin cá nhân, tài khoản ngân hàng
- Lừa người dùng chuyển tiền
- Cài đặt phần mềm độc hại
- Truy cập vào link/website giả mạo

### ✅ Giá trị nhãn

| Giá trị   | Ý nghĩa              | Mô tả                               |
| ----------- | ---------------------- | ------------------------------------- |
| **0** | **Not Smishing** | Tin nhắn hợp pháp, đáng tin cậy |
| **1** | **Smishing**     | Tin nhắn lừa đảo, đáng ngờ     |

### 🚫 **Label = 1 (SMISHING)** - Đánh dấu khi CÓ ÍT NHẤT 1 dấu hiệu sau:

#### A. Lừa đảo tài chính rõ ràng

- **Yêu cầu chuyển tiền** ngay lập tức với lý do bất thường
- **Thông báo trúng thưởng** chưa từng tham gia
- **Yêu cầu cung cấp thông tin** ngân hàng, OTP, mật khẩu
- **Đòi nợ, phạt** từ cơ quan nhà nước thông qua tin nhắn.

**Ví dụ:**

```
"Chúc mừng bạn trúng 100 triệu từ chương trình khuyến mãi. 
Vui lòng chuyển 2 triệu phí xử lý vào STK 123456789"
```

#### B. Giả mạo tổ chức/cơ quan

- Giả danh **ngân hàng** (nhưng có dấu hiệu bất thường)
- Giả danh **cơ quan nhà nước** (Công an, Viện kiểm sát, Tòa án)
- Giả danh **dịch vụ vận chuyển** yêu cầu thanh toán phí
- Giả danh **nhà mạng** yêu cầu xác thực tài khoản

**Ví dụ:**

```
"[Công An] Anh/chị bị tình nghi liên quan đến vụ án rửa tiền.
Liên hệ ngay 0912345678 để làm việc"
```

#### C. Link đáng ngờ

- Domain lạ, không chính thống (vd: `vietteI.com.vn` thay vì `viettel.com.vn`)
- Link rút gọn không rõ nguồn gốc (`bit.ly`, `tinyurl` từ nguồn không đáng tin)
- URL chứa các từ như: `xác thực`, `cập nhật tài khoản`, `đăng nhập ngay`

**Ví dụ:**

```
"Tài khoản ngân hàng của bạn sắp bị khóa. 
Cập nhật ngay tại: http://vietcomhank.com/update"
```

#### D. Ngôn ngữ tạo áp lực, khẩn cấp

- "Ngay lập tức", "Khẩn cấp", "Trong 24h"
- "Tài khoản sẽ bị khóa", "Bạn sẽ bị phạt"
- Viết SAI chính tả có chủ đích (tránh bộ lọc)

**Ví dụ:**

```
"KHẨN CẤP! Tài khoản ATM của bạn có giao dịch bất thường 50 triệu.
Xác nhận ngay tại: http://bidv-xacthuc.com hoặc gọi 0987654321"
```

#### E. Quảng cáo, spam bất hợp pháp

- Cá độ, cờ bạc trực tuyến
- Vay tiền lãi suất cắt cổ, không cần thế chấp
- Bán hàng giả, hàng nhái
- Dược phẩm không rõ nguồn gốc

**Ví dụ:**

```
"Vay tín chấp 1 tỷ chỉ cần CCCD, duyệt trong 30 phút.
Lãi suất 0% tháng đầu. Liên hệ: 0909123456"
```

### ✅ **Label = 0 (NOT SMISHING)** - Đánh dấu KHI:

#### A. Tin nhắn từ tổ chức hợp pháp

- **Nhà mạng** (Viettel, VinaPhone, Mobifone): Thông báo khuyến mãi, cước
- **Ngân hàng**: Thông báo giao dịch, số dư, tăng hạn mức
- **Dịch vụ OTP**: Mã xác thực từ Google, Facebook, Zalo...
- **Trường học**: Thông báo học phí, điểm, lịch học
- **Chính phủ/MTTQ**: Thông báo chính thống (có thông tin rõ ràng)

**Ví dụ:**

```
"[Viettel] Nạp thẻ đủ đầy - Data xài ngay! Tặng 20% giá trị 
tất cả thẻ nạp. Chi tiết gọi 198 (0đ)."
```

#### B. Dịch vụ hợp pháp

- E-commerce: Shopee, Lazada, Tiki thông báo đơn hàng
- Ví điện tử: MoMo, ZaloPay, VNPay thông báo giao dịch
- Giao thông: Thông báo phí đường bộ, ePass

**Ví dụ:**

```
"MoMo: Ban da nap tien thanh cong 100.000d vao tai khoan.
So du: 250.000d"
```

#### C. Tin nhắn cá nhân

- Tin nhắn từ bạn bè, người thân, xã giao
- Nhắc lịch hẹn, sự kiện

### ⚠️ TRƯỜNG HỢP KHÓ PHÂN BIỆT

| Tình huống                                   | Cách xử lý                                                  |
| ---------------------------------------------- | -------------------------------------------------------------- |
| **Quảng cáo hợp pháp nhưng spam**   | →**Label = 0** (không phải lừa đảo, chỉ là spam) |
| **Tin nhắn mơ hồ, thiếu ngữ cảnh** | → Căn cứ vào dấu hiệu có sẵn (URL, SĐT, ngôn ngữ)   |

---

## 2️⃣ GÁN NHÃN: **HAS_URL** (Phát hiện URL)

### 📖 Định nghĩa

Xác định xem tin nhắn có chứa đường dẫn/link hay không.

### ✅ Giá trị nhãn

| Giá trị   | Ý nghĩa      |
| ----------- | -------------- |
| **0** | Không có URL |
| **1** | Có URL        |

### 🔍 Các dạng URL cần nhận diện

#### ✅ **has_url = 1** KHI xuất hiện:

**1. URL đầy đủ với giao thức:**

```
http://viettel.vn
https://momo.vn
https://viettelmoney.go.link/abc
```

**2. URL không có giao thức:**

```
viettel.vn
www.google.com
facebook.com/page
```

**3. Link rút gọn:**

```
bit.ly/abc123
tinyurl.com/xyz
s.viettel.vn/abc
slim.link/CbB
```

**4. Đường dẫn có domain + path:**

```
shopee.vn/product/123
zalo.me/username
```

**5. IP Address:**

```
http://192.168.1.1
https://103.56.158.12/login
```

#### ❌ **has_url = 0** KHI KHÔNG có URL

**KHÔNG phải URL:**

- Số điện thoại: `0912345678`, `18008888`
- Số tài khoản: `123456789`
- Mã số: `ST15K`, `5G10`, `V90B`
- Email: `support@viettel.vn` (trừ khi là domain rõ ràng)

### 💡 Lưu ý

- **Chỉ cần có 1 URL** trong tin nhắn → `has_url = 1`
- **Nhiều URL** trong 1 tin nhắn → vẫn là `has_url = 1`
- **URL bị viết sai chính tả** → vẫn là URL (vd: `vietteI.com` với chữ I thay l)
- **URL có dấu cách** (bị ngắt dòng) → vẫn tính là URL nếu nhận diện được

---

## 3️⃣ GÁN NHÃN: **HAS_PHONE_NUMBER** (Phát hiện số điện thoại)

### 📖 Định nghĩa

Xác định xem tin nhắn có chứa số điện thoại hay không.

### ✅ Giá trị nhãn

| Giá trị   | Ý nghĩa                    |
| ----------- | ---------------------------- |
| **0** | Không có số điện thoại |
| **1** | Có số điện thoại        |

### 🔍 Các dạng số điện thoại cần nhận diện

#### ✅ **has_phone_number = 1** KHI xuất hiện:

**1. Số điện thoại di động (10-11 số):**

```
0912345678
+84912345678
84912345678
0123 456 789 (có dấu cách)
```

**2. Hotline/Tổng đài (8-10 số):**

```
18008168
1900xxxx
```

**3. Số điện thoại cố định:**

```
02812345678 (TP.HCM)
02436789012 (Hà Nội)
```

**4. Số điện thoại quốc tế:**

```
+1-234-567-8900
(+84) 912-345-678
```

#### ❌ **has_phone_number = 0** KHI KHÔNG có số điện thoại

**KHÔNG phải số điện thoại:**

**1. Shortcode/Brandname (3-6 số):**

```
191, 197, 198, 199 (đầu số dịch vụ Viettel)
9029, 8077 (dịch vụ giá trị gia tăng)
```

**2. Số tiền, số lượng:**

```
100.000đ
50 triệu
1GB, 6GB
```

**3. Mã gói cước:**

```
ST15K, V90B, 5G10
```

**4. Số tài khoản:**

```
55102025 (STK ngân hàng)
8639699999 (STK tiếp nhận)
```

**5. Mã xác thực/OTP:**

```
733792
541118
```

### 💡 Lưu ý quan trọng

- **Chỉ cần có 1 số điện thoại** → `has_phone_number = 1`
- **Nhiều số trong tin nhắn** → xem xét cẩn thận từng số
- **Số có thể gọi được** → là số điện thoại
- **Ngữ cảnh quan trọng:**
  ```
  "Liên hệ 0912345678" → has_phone_number = 1
  "Gói ST15K chỉ 15.000đ" → has_phone_number = 0
  "Chi tiết gọi 197" → has_phone_number = 0 (shortcode)
  "LH 18008168" → has_phone_number = 1 (hotline)
  ```

---

## 4️⃣ QUY TRÌNH GÁN NHÃN CHUẨN

### 📝 Các bước thực hiện

```
Bước 1: Đọc kỹ nội dung tin nhắn
   ↓
Bước 2: Xác định LABEL (smishing hay không?)
   ├─ Có dấu hiệu lừa đảo? → Label = 1
   └─ Tin nhắn hợp pháp? → Label = 0
   ↓
Bước 3: Kiểm tra HAS_URL
   ├─ Quét tìm http://, https://, www., domain
   └─ Có URL? → 1, Không? → 0
   ↓
Bước 4: Kiểm tra HAS_PHONE_NUMBER
   ├─ Tìm chuỗi số 8-11 chữ số
   ├─ Loại trừ: Mã gói, số tiền, OTP, shortcode
   └─ Có SĐT thực sự? → 1, Không? → 0
   ↓
Bước 5: Lưu kết quả
```

### ✅ CHECKLIST trước khi lưu

- [ ] Đã đọc kỹ toàn bộ tin nhắn?
- [ ] Label có phù hợp với dấu hiệu smishing?
- [ ] Đã kiểm tra hết tất cả URL trong tin nhắn?
- [ ] Đã phân biệt số điện thoại với mã dịch vụ/số tiền/shortcode?
- [ ] Nếu không chắc chắn → đã SKIP để xem lại?

---

## 5️⃣ VÍ DỤ MINH HỌA CHI TIẾT

### Ví dụ 1: Smishing rõ ràng

**Tin nhắn:**

```
"KHẨN CẤP! Tài khoản Vietcombank của bạn có giao dịch 
bất thường 50.000.000đ. Xác nhận ngay tại 
http://vietcomhank.com/xacthuc hoặc gọi 0987654321 
trong 2 giờ để tránh bị khóa tài khoản."
```

**Gán nhãn:**

- `label = 1` (Smishing - giả mạo ngân hàng, tạo áp lực, domain sai chính tả)
- `has_url = 1` (có `http://vietcomhank.com/xacthuc`)
- `has_phone_number = 1` (có `0987654321`)

---

### Ví dụ 2: Tin nhắn hợp pháp từ nhà mạng

**Tin nhắn:**

```
"[TB] NẠP THẺ ĐỦ ĐẦY - DATA XÀI NGAY! Tặng 20% giá trị 
tất cả thẻ nạp vào tài khoản viễn thông trong ngày 
25/11/2025. Nạp thẻ online tại https://viettel.vn/naptienkm . 
Chi tiết gọi 197 bấm phím 19 (0đ)."
```

**Gán nhãn:**

- `label = 0` (Không phải smishing - khuyến mãi chính thống từ Viettel)
- `has_url = 1` (có `https://viettel.vn/naptienkm`)
- `has_phone_number = 0` (197 là shortcode, không phải số điện thoại liên hệ)

---

### Ví dụ 3: OTP/Mã xác thực

**Tin nhắn:**

```
"Mã xác thực GitHub của bạn là: 733792"
```

**Gán nhãn:**

- `label = 0` (Không phải smishing - OTP hợp lệ)
- `has_url = 0` (không có URL)
- `has_phone_number = 0` (733792 là mã OTP, không phải SĐT)

---

### Ví dụ 4: Quảng cáo vay tiền đáng ngờ

**Tin nhắn:**

```
"[QC] 1 chạm giải ngân đến 35 TRIỆU đồng, chỉ cần CCCD. 
Đăng ký Vay nhanh Mcredit với Viettel Money: 
https://viettelmoney.go.link/Ngdub . Chi tiết LH 18009000 (0đ)."
```

**Gán nhãn:**

- `label = 1` (Smishing - quảng cáo vay tiền, link rút gọn đáng ngờ)
- `has_url = 1` (có `https://viettelmoney.go.link/Ngdub`)
- `has_phone_number = 1` (có `18009000` - hotline)

---

### Ví dụ 5: Thông báo học phí

**Tin nhắn:**

```
"DHCNTT TB HỌC PHÍ ĐỢT 1 HK1 25-26 CỦA SV Nguyen Hoang Duy 
(22520327) LÀ 18,500,000đ, HẠN NỘP HP ĐỢT 1 LÀ 28/9/2025. 
VUI LÒNG BỎ QUA TIN NHẮN NẾU ĐÃ NỘP TIỀN."
```

**Gán nhãn:**

- `label = 0` (Không phải smishing - thông báo học phí chính thống)
- `has_url = 0` (không có URL)
- `has_phone_number = 0` (22520327 là MSSV, 18500000 là số tiền)

---

### Ví dụ 6: Tin nhắn có hotline 1800

**Tin nhắn:**

```
"[QC] Cơ hội TRÚNG XE MÁY HONDA SH 125i khi hòa mạng Internet 
Viettel và đóng trước cước từ 6 tháng trở lên, cước thuê bao 
chỉ từ 220.000đ/tháng. LH 18008168 (0đ) để được tư vấn."
```

**Gán nhãn:**

- `label = 0` (Không phải smishing - quảng cáo chính thống từ Viettel)
- `has_url = 0` (không có URL)
- `has_phone_number = 1` (có `18008168` - hotline 8 số)

---

### Ví dụ 7: Tin nhắn lừa đảo cá độ

**Tin nhắn:**

```
"Sử dụng cược miễn phí không cần nạp S73qtEP! Cược vào 3+ 
sự kiện (tỷ lệ từ 1.4). Hiệu lực đến 23.08. Kiểm tra tại 
Cài đặt tài khoản. https://slim.link/CbB DLS"
```

**Gán nhãn:**

- `label = 1` (Smishing - cá độ bất hợp pháp, link rút gọn đáng ngờ)
- `has_url = 1` (có `https://slim.link/CbB`)
- `has_phone_number = 0` (không có số điện thoại)

---

## 6️⃣ CÁC LỖI THƯỜNG GẶP VÀ CÁCH TRÁNH

| Lỗi                                                  | Nguyên nhân                              | Cách khắc phục                                                |
| ----------------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------- |
| **Nhầm lẫn shortcode với số điện thoại** | 191, 197, 198, 199, 9029 không phải SĐT | Chỉ đánh `has_phone_number=1` với số 8-11 chữ số        |
| **Bỏ sót URL không có http://**             | Chỉ tìm URL có giao thức               | Chú ý domain:`viettel.vn`, `facebook.com`                  |
| **Gán Label=1 cho mọi quảng cáo**           | Nhầm spam với smishing                   | Phân biệt: Quảng cáo hợp pháp ≠ Lừa đảo                |
| **Nhầm mã OTP với số điện thoại**        | 733792 có 6 chữ số                      | OTP thường 4-6 số, không có tiền tố 0                     |
| **Không chắc chắn nhưng vẫn gán**         | Vội vã, không đọc kỹ                 | Sử dụng SKIP, quay lại sau                                    |
| **Nhầm hotline 1800 với shortcode**           | 18008168 có 8 chữ số                    | Hotline 1800xxxx (8 số) là SĐT, 191-199 (3 số) là shortcode |

---

## 7️⃣ NGUYÊN TẮC VÀNG

1. **Nghi ngờ = SKIP**: Không chắc chắn → đừng gán nhãn sai
2. **Đọc kỹ toàn bộ**: Đừng chỉ đọc đầu tin nhắn
3. **Ngữ cảnh quan trọng**: Cùng 1 số nhưng ngữ cảnh khác → nhãn khác
4. **Nhất quán**: Tin nhắn tương tự → gán nhãn giống nhau
5. **Hỏi khi cần**: Không rõ → thảo luận với nhóm

---

## 📊 KẾT LUẬN

Guidelines này giúp đảm bảo:

- ✅ **Tính nhất quán** trong gán nhãn
- ✅ **Chất lượng dữ liệu** cao cho mô hình AI
- ✅ **Giảm thiểu sai sót** do chủ quan

**Lưu ý:** Guidelines có thể được cập nhật khi phát hiện thêm các trường hợp đặc biệt.

---

**Phiên bản:** 1.1
**Ngày cập nhật:** 3/3/2026
**Dự án:** IE403 - Phát hiện tin nhắn SMS độc hại
