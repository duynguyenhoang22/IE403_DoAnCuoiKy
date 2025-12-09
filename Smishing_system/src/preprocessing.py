import os
import re
import unicodedata 
from pyvi import ViUtils
import unicodedata
from underthesea import text_normalize, word_tokenize, pos_tag
from iocextract import extract_urls
import torch 
from transformers import AutoTokenizer, AutoModelForTokenClassification


# ==============================================================================
# CẤU HÌNH ĐƯỜNG DẪN
# ==============================================================================
# Lấy đường dẫn tuyệt đối của thư mục chứa file preprocessing.py (tức là thư mục src)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Đi ngược ra thư mục cha (Smishing_system) rồi vào data/dicts
# Logic: src/../data/dicts/selected_tags_names.txt
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
TAGS_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "dicts", "selected_tags_names.txt")

MODEL_NAME = "peterhung/vietnamese-accent-marker-xlm-roberta"

# ==============================================================================
# PHẦN KHỞI TẠO MODEL (CHẠY 1 LẦN DUY NHẤT KHI IMPORT)
# ==============================================================================
print("Đang tải model thêm dấu (Accent Restoration)... Vui lòng đợi...")

# 1. Tải Model & Tokenizer
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
try:
    print(f"   - Đang tải model {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
    model.to(device)
    model.eval()
    print("   ✅ Model đã tải xong.")
except Exception as e:
    print(f"   ❌ Lỗi tải model: {e}")
    model = None
    tokenizer = None

# 2. Tải danh sách nhãn từ file .txt
LABEL_LIST = []
try:
    if os.path.exists(TAGS_FILE_PATH):
        print(f"   - Đang đọc file tags từ: {TAGS_FILE_PATH}")
        with open(TAGS_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    LABEL_LIST.append(line)
        print(f"   ✅ Đã tải {len(LABEL_LIST)} nhãn.")
    else:
        print(f"   ⚠️ CẢNH BÁO: Không tìm thấy file {TAGS_FILE_PATH}. Chức năng thêm dấu sẽ không hoạt động.")
except Exception as e:
    print(f"   ❌ Lỗi đọc file tags: {e}")

# ==============================================================================
# CÁC HÀM XỬ LÝ CHÍNH
# ==============================================================================

# 1. Chuẩn hoá Unicode (NFC)
def normalize_unicode(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFC', text)

# 2. Bắt và loại bỏ URL 
def remove_urls(text):
    """
    Loại bỏ URL ra khỏi văn bản.
    """
    if extract_urls:
        urls = list(extract_urls(text))
        # Xóa URL dài trước để tránh lỗi chồng lấn
        urls.sort(key=len, reverse=True)
        for url in urls:
            text = text.replace(url, " ")

    # Regex bổ sung (Đã sửa lỗi \d cho IP)
    # Bắt domain phổ biến và IP address
    extra_pattern = r"((http|https)://)?(www\.)?([a-zA-Z0-9-]+\.(com|vn|net|org|xyz|info|top|club)|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})(/[a-zA-Z0-9#._-]*)?"
    text = re.sub(extra_pattern, " ", text)
    return text

# 3. Chuẩn hoá vị trí dấu câu (Đưa lên trước để tách từ dính)
def normalize_structure(text):
    """
    Tách các dấu câu bị dính. VD: "PHI.Goi" -> "PHI . Goi"
    Regex: Tìm dấu chấm (.) nằm giữa 2 ký tự chữ cái và tách ra.
    """
    # Tách dấu chấm dính liền với chữ cái phía sau (VD: .Goi -> . Goi)
    text = re.sub(r'([.])([a-zA-Z])', r'\1 \2', text)
    return text_normalize(text)

# 4. Thêm dấu câu tiếng Việt
def add_vietnamese_punctuation_transformer(text):
    """
    Hàm thêm dấu sử dụng Deep Learning + File mapping tags.
    """
    # Kiểm tra điều kiện tiên quyết
    if not model or not tokenizer or not LABEL_LIST:
        return text 

    # Lowercase input
    text_input = text.lower()

    # Tokenize sơ bộ bằng khoảng trắng để map lại sau này
    tokens_raw = text_input.split()
    if not tokens_raw: return text

    # --- SỬA LỖI TẠI ĐÂY ---
    
    # 1. Giữ nguyên object BatchEncoding gốc để dùng word_ids sau này
    tokenized_inputs = tokenizer(tokens_raw, is_split_into_words=True, return_tensors="pt", truncation=True, padding=True)
    
    # 2. Tạo một bản copy dictionary để đưa vào GPU/CPU (Model Input)
    model_inputs = {k: v.to(device) for k, v in tokenized_inputs.items()}

    # Dự đoán (Inference) dùng model_inputs
    with torch.no_grad():
        outputs = model(**model_inputs)
    
    predictions = torch.argmax(outputs.logits, dim=2)
    preds = predictions[0].cpu().numpy()
    
    # 3. Lấy word_ids từ object gốc (tokenized_inputs) thay vì dict (model_inputs)
    word_ids = tokenized_inputs.word_ids(batch_index=0)
    
    # --- KẾT THÚC SỬA LỖI ---
    
    restored_words = []
    current_word_idx = -1
    
    # Logic ghép từ và thêm dấu
    for idx, word_id in enumerate(word_ids):
        if word_id is None: continue # Bỏ qua [CLS], [SEP], [PAD]
        
        if word_id != current_word_idx:
            # Bắt đầu xử lý một từ mới trong tokens_raw
            current_word_idx = word_id
            original_word = tokens_raw[word_id] # Lấy từ gốc
            
            # Lấy nhãn dự đoán cho token đầu tiên của từ này
            pred_label_idx = preds[idx]
            
            if pred_label_idx < len(LABEL_LIST):
                tag_name = LABEL_LIST[pred_label_idx]
                
                # Logic parse tag: "a-á" nghĩa là thay 'a' bằng 'á'
                if '-' in tag_name:
                    src_char, dest_char = tag_name.split('-')
                    # Chỉ thay thế nếu từ gốc có chứa ký tự nguồn
                    if src_char in original_word:
                        original_word = original_word.replace(src_char, dest_char)
            
            restored_words.append(original_word)
            
    return " ".join(restored_words)

# 5. Pipeline làm sạch dữ liệu (Dùng cho nhánh B - Domain & Keywords)
def clean_text_pipeline(text):
    """
    Quy trình: Unicode -> Loại bỏ URL -> Chuẩn hoá -> Thêm dấu -> Tách từ
    """

    # B1. Chuẩn hoá Unicode
    text = normalize_unicode(text)

    # B2. Loại bỏ URL (Xóa rác trước khi xử lý)
    text = remove_urls(text)

    # B3. Chuẩn hoá cấu trúc (QUAN TRỌNG: Làm bước này để tách "PHI.Goi" thành "PHI . Goi")
    text = normalize_structure(text)

    # B4. Thêm dấu câu (Input lúc này đã sạch và tách bạch)
    text = add_vietnamese_punctuation_transformer(text)

    # B5. Tách từ (Word Segmentation)
    tokens = word_tokenize(text, format="text")

    return tokens

# 6. Trích xuất Danh từ (Nouns) (Dùng cho Domain Checking Phase)
def extract_nouns(clean_text):
    """
    Trích xuất danh từ và các thực thể quan trọng (Thương hiệu, Hotline).
    """
    tagged_words = pos_tag(clean_text)
    
    extracted_nouns = []
    
    # thêm WHITELIST (danh sách từ luôn đúng, không cần loại bỏ)
    whitelist = ['vpbank', 'vcb', 'otp', 'bidv', 'techcombank', 'agribank', 'zalo', 'link', 'website', 'tele', 'telegram', 'tiki', 'shopee']

    # --- CẬP NHẬT DANH SÁCH NHÃN ---
    # N, Np, Ny, Nb: Các loại danh từ chuẩn.
    # F: Foreign (Từ nước ngoài) -> QUAN TRỌNG: Bắt "vpbank", "agribank", "zalo".
    # M: Numeral (Số từ) -> Bắt số hotline "1900", số tiền "10 triệu".
    # Ni: Identification (Ký hiệu) -> Đôi khi mã giao dịch rơi vào đây.
    target_tags = ['N', 'Np', 'Ny', 'Nb', 'F', 'M', 'Ni'] 

    for word, tag in tagged_words:
            word_lower = word.lower()
            
            # Logic lấy từ:
            # A. Hoặc là nằm trong Whitelist
            # B. Hoặc là có nhãn trong target_tags
            # C. Hoặc là số (isdigit)
            is_valid_tag = tag in target_tags
            is_in_whitelist = word_lower in whitelist
            is_number = word.isdigit()
            
            if is_valid_tag or is_in_whitelist or is_number:
                # Lọc rác ký tự
                clean_word = word.replace('_', '')
                if (len(word) > 1 and clean_word.isalnum()) or is_number:
                    extracted_nouns.append(word)
        
    return " ".join(extracted_nouns)


# Test nhanh (Chỉ để debug khi chạy file này trực tiếp)
if __name__ == "__main__":
    sample = "Ngan Hang VPBANK THONG BAO. Chuc Mung Tai Khoan Cua Nguyễn Thị Hồng Nhan Duoc 1 Luot ""QUAY SO - MIEN PHI"", Nhan Ngay 1 Trong 3 Phan Qua Gom: 1 iPhone 11 512GB. 1 Tivi LG 4k 55inch. 10 Trieu Dong Vao Tai Khoan. Truy Cap Website: https://login-onlien.com.vn/ De Thuc Hien Luot QUAY SO MAY MAN MIEN PHI.Goi Vao 1900 54 54 15.Xin Cam On!"

    print("-" * 50)
    print(f"INPUT GỐC:\n{sample}")
        
    cleaned_tokens = clean_text_pipeline(sample)
    print("-" * 50)
    print(f"PIPELINE CLEANED:\n{cleaned_tokens}")
        
    nouns = extract_nouns(cleaned_tokens)
    print("-" * 50)
    print(f"DANH TỪ RÚT TRÍCH:\n{nouns}")
    print("-" * 50)