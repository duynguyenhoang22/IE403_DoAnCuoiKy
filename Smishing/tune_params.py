import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def tune_xgboost_hyperparameters(data_path):
    # 1. Load và Chuẩn bị dữ liệu (như cũ)
    logger.info("Loading data...")
    df = pd.read_csv(data_path)
    
    if 'text' in df.columns: df = df.drop(columns=['text'])
    
    if 'sender_type' in df.columns:
        le = LabelEncoder()
        df['sender_type'] = df['sender_type'].astype(str)
        df['sender_type'] = le.fit_transform(df['sender_type'])

    X = df.drop(columns=['label'])
    y = df['label']

    # 2. Tính toán tỷ lệ mẫu (Scale Pos Weight)
    # Đây là tham số bắt buộc phải giữ cố định để xử lý mất cân bằng
    pos_weight = (y == 0).sum() / (y == 1).sum()
    logger.info(f"Calculated scale_pos_weight: {pos_weight:.2f}")

    # 3. Định nghĩa mô hình cơ sở
    xgb_model = xgb.XGBClassifier(
        objective='binary:logistic',
        learning_rate=0.05,       # Giữ Learning rate thấp để model học kỹ
        n_estimators=200,         # Số lượng cây vừa phải
        scale_pos_weight=pos_weight,
        eval_metric='auc',
        random_state=42
    )

    # 4. THIẾT LẬP LƯỚI THAM SỐ (GRID)
    # Tập trung vào các tham số giúp giảm Overfitting
    param_grid = {
        # Độ sâu của cây: Sâu quá thì học vẹt (Overfit), nông quá thì học kém (Underfit)
        # Giá trị thử nghiệm: 3 (nông), 4, 5, 6 (sâu vừa)
        'max_depth': [3, 4, 5, 6],

        # Trọng số tối thiểu của node con: Giá trị càng cao càng khó tạo nhánh mới -> Chống Overfit tốt nhất
        # Giá trị thử nghiệm: 1 (mặc định), 3 (khắt khe), 5 (rất khắt khe)
        'min_child_weight': [1, 3, 5],

        # Gamma: Điểm phạt khi tạo nhánh mới. > 0 giúp model "thận trọng" hơn
        # Giá trị thử nghiệm: 0, 0.1, 0.2
        'gamma': [0, 0.1, 0.2],
        
        # Subsample: Mỗi cây chỉ được nhìn thấy bao nhiêu % dữ liệu?
        # < 1.0 giúp model tổng quát hóa tốt hơn
        'subsample': [0.8, 1.0],
        
        # Colsample_bytree: Mỗi cây được dùng bao nhiêu % đặc trưng?
        'colsample_bytree': [0.8, 1.0]
    }

    # 5. Cấu hình Grid Search
    # StratifiedKFold đảm bảo mỗi fold đều có đủ tỷ lệ tin nhắn lừa đảo
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    grid_search = GridSearchCV(
        estimator=xgb_model,
        param_grid=param_grid,
        scoring='roc_auc',  # Tối ưu hóa chỉ số ROC-AUC
        n_jobs=-1,          # Dùng tất cả nhân CPU chạy cho nhanh
        cv=cv,
        verbose=1           # Hiện tiến trình
    )

    logger.info("Starting Grid Search... (This may take a while)")
    grid_search.fit(X, y)

    # 6. Kết quả
    print("\n" + "="*40)
    print("KẾT QUẢ TỐI ƯU HÓA THAM SỐ")
    print("="*40)
    print(f"Best ROC-AUC Score: {grid_search.best_score_:.4f}")
    print("Best Hyperparameters:")
    for param, val in grid_search.best_params_.items():
        print(f"  - {param}: {val}")

    return grid_search.best_params_

if __name__ == "__main__":
    DATA_FILE = 'data/dataset_features.csv'
    best_params = tune_xgboost_hyperparameters(DATA_FILE)