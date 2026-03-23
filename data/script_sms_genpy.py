# %%
import pandas as pd

# Đọc dataset gốc
df = pd.read_csv('../data/dataset.csv')

# Tạo dataset cho label 0 (không phải smishing)
df_label_0 = df[df['label'] == 0]
df_label_0.to_csv('../data/dataset_label_0.csv', index=False)

# Tạo dataset cho label 1 (smishing)
df_label_1 = df[df['label'] == 1]
df_label_1.to_csv('../data/dataset_label_1.csv', index=False)

print("Đã tạo 2 file dataset:")
print("- dataset_label_0.csv: {} mẫu".format(len(df_label_0)))
print("- dataset_label_1.csv: {} mẫu".format(len(df_label_1)))


# %%
import google.generativeai as genai
import pandas as pd
import time
import random
import os

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
API_KEY = ""
#API_KEY = "AIzaSyDCIKmwtqoZ6psCEUvSPMh0f1gYD-EMt3U"  # Thay API Key của bạn vào đây
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

OUTPUT_FILE = "synthetic_2000_smishing_v2.csv"
TOTAL_SAMPLES = 2000
BATCH_SIZE = 40  # Số mẫu mỗi lần gọi API (tối ưu cho chất lượng)

# ==========================================
# 2. ĐỊNH NGHĨA KỊCH BẢN & TEENCODE (Bám sát Guideline)
# ==========================================
scenarios = {
    "Dịch vụ công": ["VNeID", "Tổng cục Thuế", "Cục Viễn thông", "Bộ Công an", "BHXH"],
    "Tuyển dụng & TMĐT": ["TikTok Shop", "Shopee Mall", "Tiki", "Amazon Job", "Lazada"],
    "Tài chính & Quà tặng": ["Mcredit", "FE Credit", "Vietcombank", "Lì xì Tết 2026", "SHB Digibank"],
    "Giải trí & Nhạy cảm": ["Telegram Hẹn hò", "789Bet", "Kwin668", "Gái xinh Zalo", "Cá độ bóng đá"]
}

teencode_styles = [
    "Thay e=3, a=4, o=0, i=1 và chèn dấu chấm/gạch ngang xen kẽ (ví dụ: T.u.y.3.n, S-h-0-p-e-e)",
    "Dùng j thay gi, f thay ph, w thay qu, z thay d (ví dụ: th0ng b4o vj fhat, jao luu za.lo)",
    "Chèn ký tự đặc biệt @, #, !, *, ^ liên tục vào các từ khóa nhạy cảm để lách bộ lọc",
    "Viết sai chính tả vùng miền kết hợp không dấu (ví dụ: li3n h3^ x3m hjnh_anh n0ng)",
    "Sử dụng Homoglyph: dùng chữ 'l' thay 'I', dùng số '0' thay 'O' trong các link giả mạo"
]

# ==========================================
# 3. HÀM GỌI API SINH DỮ LIỆU
# ==========================================
def generate_smishing_batch(size):
    # Chọn ngẫu nhiên ngữ cảnh để đảm bảo độ đa dạng
    category = random.choice(list(scenarios.keys()))
    brand = random.choice(scenarios[category])
    style = random.choice(teencode_styles)
    
    prompt = f"""
    Bạn là một chuyên gia về dữ liệu tin nhắn lừa đảo (Smishing) tại Việt Nam.
    Hãy tạo {size} mẫu tin nhắn lừa đảo (Label 1) cho kịch bản: {category} (Thương hiệu: {brand}).
    
    YÊU CẦU KỸ THUẬT:
    1. Áp dụng phong cách nhiễu/teencode: {style}.
    2. Tuân thủ cấu trúc CSV: content,label,has_url,has_phone_number,sender_type.
    3. sender_type chỉ chọn 1 trong: 'personal_number', 'brandname', 'shortcode'.
    4. has_url=1 nếu có link (kể cả link rác/giả), has_phone_number=1 nếu có SĐT thực tế.
    5. Nội dung: Đánh vào tâm lý cấp bách, sợ hãi hoặc lòng tham (theo đúng Rationale-Aware).
    
    TRẢ VỀ: Chỉ trả về các dòng dữ liệu CSV, không có dòng tiêu đề, không giải thích.
    """
    
    try:
        response = model.generate_content(
            prompt, 
            generation_config={"temperature": 0.95} # Tăng sáng tạo để tránh trùng lặp
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Lỗi API: {e}")
        return ""

# ==========================================
# 4. TIẾN TRÌNH THỰC THI
# ==========================================
def main():
    # Khởi tạo file và ghi Header
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            f.write("content,label,has_url,has_phone_number,sender_type\n")
    
    current_total = 0
    print(f"🚀 Bắt đầu sinh {TOTAL_SAMPLES} mẫu dữ liệu...")

    while current_total < TOTAL_SAMPLES:
        print(f"🔄 Đang xử lý đợt: {current_total} -> {current_total + BATCH_SIZE}...")
        
        batch_csv = generate_smishing_batch(BATCH_SIZE)
        
        if batch_csv:
            with open(OUTPUT_FILE, "a", encoding="utf-8-sig") as f:
                f.write(batch_csv + "\n")
            current_total += BATCH_SIZE
            print(f"✅ Đã lưu thêm {BATCH_SIZE} mẫu.")
        
        # Nghỉ để tránh Rate Limit (Điều chỉnh tùy theo loại tài khoản API)
        time.sleep(12) 

    # Hậu xử lý: Loại bỏ dòng trống hoặc dòng lỗi định dạng
    print("🧹 Đang chuẩn hóa dữ liệu...")
    df = pd.read_csv(OUTPUT_FILE)
    df.dropna(subset=['content'], inplace=True)
    df.drop_duplicates(subset=['content'], inplace=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    
    print(f"🎊 HOÀN THÀNH! Tổng số mẫu thực tế sau khi lọc trùng: {len(df)}")

if __name__ == "__main__":
    main()

# %%
import google.generativeai as genai
import pandas as pd
import time
import random
import os

# ==========================================
# 1. CẤU HÌNH API
# ==========================================
API_KEY = ""
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

OUTPUT_FILE = "synthetic_2000_label_0_generalized.csv"
TOTAL_SAMPLES = 2000
BATCH_SIZE = 40 

# ==========================================
# 2. PROMPT 3 CẤP ĐỘ ĐÃ TỔNG QUÁT HÓA
# ==========================================
def get_generalized_prompt(level, size):
    if level == 1: # Cấp độ 1: Đời thường & Công việc chung
        return f"""
        Đóng vai người dùng di động tại VN, tạo {size} SMS nhãn 0 (tin sạch).
        Chủ đề: Hỏi thăm bạn bè, hẹn cà phê/ăn uống, nhắc lịch họp công ty, thông báo gia đình, nhắc lịch học/thi chung chung.
        Yêu cầu: Ngôn ngữ tự nhiên, gần gũi (dùng: nhé, nha, rồi ạ, ok).
        Định dạng CSV: content,0,0,0,personal_number
        """
    
    elif level == 2: # Cấp độ 2: Few-shot & Teencode đời thường (Tối ưu)
        return f"""
        Tạo {size} SMS nhãn 0 dựa trên phong cách chat của người Việt:
        'Ok b nha', 'Mai di som nhe', 'Toi nay qua nha t choi ko?', 'Co j bao t sau'.
        Yêu cầu: Sử dụng teencode nhẹ phổ biến (ko, dc, oke, rùi, bít, thui, j, m, t). 
        Kết hợp linh hoạt có dấu và không dấu để mô phỏng tin nhắn cá nhân thực tế.
        Định dạng CSV: content,0,0,0,personal_number
        """
    
    elif level == 3: # Cấp độ 3: Hard Negative (Phòng thủ - Chứa từ khóa nhạy cảm)
        return f"""
        Tạo {size} SMS nhãn 0 (TIN SẠCH) nhưng chứa các từ khóa dễ nhầm lẫn: 'ngân hàng', 'OTP', 'xác nhận', 'giao dịch', 'link'.
        Yêu cầu nghiêm ngặt dựa trên Guidelines:
        - Nội dung là giao dịch thật: Biến động số dư (VCB, ACB...), OTP từ Google/Apple/Facebook, thông báo giao hàng Shopee/Lazada.
        - has_url=1 nếu link dẫn về domain chính thống (.vn, .com, .edu.vn).
        - has_phone_number=0 nếu là mã OTP 6 số.
        - sender_type: 'brandname' hoặc 'shortcode'.
        Định dạng CSV: content,0,has_url,has_phone_number,sender_type
        """

# ==========================================
# 3. LUỒNG SINH DỮ LIỆU TỰ ĐỘNG
# ==========================================
def main():
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", encoding="utf-8-sig") as f:
            f.write("content,label,has_url,has_phone_number,sender_type\n")
    
    current = 0
    while current < TOTAL_SAMPLES:
        # Chia tỷ lệ: 30% Level 1, 40% Level 2 (Teencode), 30% Level 3 (Hard Negative)
        level = random.choices([1, 2, 3], weights=[30, 40, 30])[0]
        print(f"🔄 Đang sinh {BATCH_SIZE} mẫu (Level {level})... Tổng: {current}/{TOTAL_SAMPLES}")
        
        prompt = get_generalized_prompt(level, BATCH_SIZE)
        
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.9} # Giữ độ đa dạng cao
            )
            # Làm sạch Markdown nếu có
            batch_data = response.text.strip().replace("```csv", "").replace("```", "")
            
            with open(OUTPUT_FILE, "a", encoding="utf-8-sig") as f:
                f.write(batch_data + "\n")
            
            current += BATCH_SIZE
            time.sleep(12) # Tránh lỗi 429 Rate Limit
        except Exception as e:
            print(f"❌ Lỗi: {e}. Đang nghỉ 20s...")
            time.sleep(20)

    # Hậu xử lý: Lọc trùng nội dung
    df = pd.read_csv(OUTPUT_FILE)
    df.drop_duplicates(subset=['content'], inplace=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"🎉 Hoàn thành! File lưu tại: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()


