# Smishing/main_preprocessing.py

import pandas as pd
import numpy as np
from tqdm import tqdm  # pip install tqdm (thanh tiến trình)
import logging

# Import các module của bạn
from data_loader import DataLoader
from features import SmishingFeatureExtractor

# Cấu hình log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def process_dataset(input_csv, output_csv):
    # 1. Load dữ liệu (Xử lý các lỗi dấu nháy/phẩy)
    logger.info(f"Loading data from {input_csv}...")
    loader = DataLoader()
    # Giả sử file csv của bạn có 4 cột cuối là label, has_url...
    df = loader.load_csv(input_csv, fixed_tail_cols=4, try_standard_first=False)
    
    # Kiểm tra cột chứa nội dung tin nhắn (thường là cột đầu tiên hoặc tên là 'text'/'content')
    # Ở đây giả định cột nội dung nằm ở cột đầu tiên sau khi load (index 0)
    text_col = df.columns[0] 
    logger.info(f"Text column detected: '{text_col}'")

    # 2. Khởi tạo Feature Extractor
    logger.info("Initializing Feature Extractor...")
    extractor = SmishingFeatureExtractor()
    feature_names = extractor.get_feature_names()

    # 3. Trích xuất đặc trưng (Chạy vòng lặp)
    logger.info("Extracting features...")
    
    # Tạo list để chứa các vector
    feature_vectors = []
    
    # Dùng tqdm để hiện thanh tiến trình
    texts = df[text_col].astype(str).tolist()
    for text in tqdm(texts):
        # Trích xuất vector 27 chiều
        vec = extractor.extract_features(text, return_dict=False)
        feature_vectors.append(vec)

    # 4. Tạo DataFrame mới chứa Features
    X_features = pd.DataFrame(feature_vectors, columns=feature_names)
    
    # 5. Ghép Features với Label gốc
    # Giữ lại các cột label quan trọng từ df gốc
    cols_to_keep = ['label', 'sender_type'] # Tùy chỉnh theo file của bạn
    final_df = pd.concat([df[cols_to_keep], X_features], axis=1)
    
    # 6. Lưu file kết quả
    logger.info(f"Saving processed data to {output_csv}...")
    final_df.to_csv(output_csv, index=False)
    logger.info("Done!")
    
    # Preview
    print("\nSample Data:")
    print(final_df.head())

if __name__ == "__main__":
    # Đường dẫn file input (file lỗi) và output (file sạch để train)
    INPUT_FILE = 'data/dataset.csv'  
    OUTPUT_FILE = 'data/dataset_features.csv'
    
    # Tạo file mẫu nếu chưa có để test
    # (Bạn thay thế bằng file thật của bạn)
    import os
    if not os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("text,label,has_url,has_phone,sender_type\n")
            f.write('"Chuc mung "ban" da trung thuong",1,0,0,unknown\n')
            f.write('Tai khoan VCB cua ban bi khoa,1,1,0,brandname\n')

    process_dataset(INPUT_FILE, OUTPUT_FILE)