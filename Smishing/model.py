import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from sklearn.metrics import precision_recall_curve

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def train_smishing_model(data_path, model_output='smishing_xgb.pkl'):
    # 1. Load dữ liệu
    logger.info(f"Loading dataset from {data_path}...")
    df = pd.read_csv(data_path)
    
    # 2. Tiền xử lý (Preprocessing)
    # Loại bỏ các cột không dùng để train (ví dụ: nội dung tin nhắn gốc nếu còn)
    # Giữ lại label và các features
    if 'content' in df.columns:
        df = df.drop(columns=['content'])
    
    # Xử lý cột sender_type (Categorical -> Numeric)
    if 'sender_type' in df.columns:
        logger.info("Encoding 'sender_type' column...")
        le = LabelEncoder()
        df['sender_type'] = df['sender_type'].astype(str)
        df['sender_type'] = le.fit_transform(df['sender_type'])
        # Lưu lại encoder để dùng lúc dự đoán thực tế
        joblib.dump(le, 'sender_encoder.pkl')
    
    # Tách Feature (X) và Label (y)
    # Giả sử cột nhãn tên là 'label'
    X = df.drop(columns=['label'])
    y = df['label']
    
    logger.info(f"Dataset shape: {X.shape}")
    logger.info(f"Class distribution: \n{y.value_counts()}")

    # 3. Chia tập Train/Test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 4. Cấu hình Model XGBoost
    # scale_pos_weight: Tự động xử lý mất cân bằng dữ liệu (Sample âm / Sample dương)
    # Giúp model chú trọng vào lớp thiểu số (Smishing)
    pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        colsample_bytree=0.8,
        gamma=0.1,
        subsample=0.8,
        min_child_weight=3,
        n_estimators=200,      # Số lượng cây
        learning_rate=0.05,    # Tốc độ học
        max_depth=4,           # Độ sâu tối đa của cây
        scale_pos_weight=pos_weight, # Xử lý Imbalanced Data
        eval_metric='auc',
        random_state=42
    )

    # 5. Huấn luyện
    logger.info("Training XGBoost model...")
    model.fit(X_train, y_train)


    # 6. Đánh giá Model
    logger.info("Evaluating model...")
    y_prob = model.predict_proba(X_test)[:, 1] # Lấy xác suất lớp 1

    # Thử tăng/giảm threshold để tối ưu F1-Score
    threshold = 0.46
    y_pred = (y_prob > threshold).astype(int)

    print(f"\n=== KẾT QUẢ VỚI THRESHOLD {threshold} ===")
    print(classification_report(y_test, y_pred, target_names=['Clean', 'Smishing']))
    
    print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}")


    print("\n" + "="*30)
    print("KIỂM TRA OVERFITTING (Train vs Test)")
    print("="*30)

    # 1. Dự đoán trên tập Train (Dữ liệu model đã học)
    y_train_prob = model.predict_proba(X_train)[:, 1]
    y_train_pred = (y_train_prob >= 0.46).astype(int)

    # 2. Tính Accuracy/Recall cho tập Train
    from sklearn.metrics import accuracy_score, recall_score
    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_pred)

    train_recall = recall_score(y_train, y_train_pred)
    test_recall = recall_score(y_test, y_pred)

    print(f"Accuracy: Train={train_acc:.4f} vs Test={test_acc:.4f} | Chênh lệch: {train_acc - test_acc:.4f}")
    print(f"Recall:   Train={train_recall:.4f} vs Test={test_recall:.4f} | Chênh lệch: {train_recall - test_recall:.4f}")

    if (train_acc - test_acc) > 0.05:
        print(">> CẢNH BÁO: Có dấu hiệu Overfitting (Chênh lệch > 5%)")
    else:
        print(">> AN TOÀN: Mô hình tổng quát hóa tốt.")


    # 7. Kiểm tra Overfitting với Cross Validation
    print("\n" + "="*30)
    print("KIỂM TRA ĐỘ ỔN ĐỊNH (Cross-Validation)")
    print("="*30)
    # Chỉ dùng X, y gốc (chưa split)
    # Scoring 'roc_auc' là thước đo khách quan nhất
    scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')

    print(f"ROC-AUC qua 5 lần chạy: {scores}")
    print(f"Trung bình: {scores.mean():.4f} (+/- {scores.std():.4f})")

    # Tính toán Precision-Recall cho mọi ngưỡng
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob)

    # Tính F1-Score cho từng ngưỡng để tìm điểm tối ưu
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls)
    best_idx = np.argmax(f1_scores) # Tìm vị trí F1 cao nhất
    best_threshold = thresholds[best_idx]

    print(f"\n>> NGƯỠNG TỐI ƯU (Best Threshold): {best_threshold:.4f}")
    print(f">> F1-Score cao nhất đạt được: {f1_scores[best_idx]:.4f}")

    # Vẽ biểu đồ Precision-Recall Curve
    plt.figure(figsize=(10, 6))
    plt.plot(recalls, precisions, marker='.', label='XGBoost')
    # Đánh dấu điểm tối ưu
    plt.scatter(recalls[best_idx], precisions[best_idx], marker='o', color='red', label='Best Threshold', zorder=10)
    plt.title(f'Precision-Recall Curve (Best Threshold = {best_threshold:.2f})')
    plt.xlabel('Recall (Độ phủ)')
    plt.ylabel('Precision (Độ chính xác)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig('pr_curve.png')
    logger.info("PR Curve saved to pr_curve.png")

    # Vẽ Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Clean', 'Smishing'], yticklabels=['Clean', 'Smishing'])
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig('confusion_matrix.png')
    logger.info("Confusion matrix saved to confusion_matrix.png")

    # 7. Lưu Model
    joblib.dump(model, model_output)
    logger.info(f"Model saved to {model_output}")
    
    # 8. Feature Importance (Xem đặc trưng nào quan trọng nhất)
    # Lấy dữ liệu importance từ model
    feature_importance = model.feature_importances_
    feature_names = X.columns
    
    # Tạo DataFrame để dễ sắp xếp
    fi_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': feature_importance
    })
    
    # Sắp xếp giảm dần và lấy Top 20 quan trọng nhất
    fi_df = fi_df.sort_values(by='Importance', ascending=False).head(20)
    
    # Vẽ biểu đồ
    plt.figure(figsize=(12, 8)) # Tăng kích thước ảnh (Rộng 12, Cao 8)
    sns.barplot(
        x='Importance', 
        y='Feature', 
        hue='Feature',
        data=fi_df, 
        palette='viridis', # Màu sắc đẹp mắt (xanh -> vàng),
        legend=False
    )
    
    # Trang trí
    plt.title('Top 20 Features Importance (XGBoost)', fontsize=15, fontweight='bold')
    plt.xlabel('Importance Score', fontsize=12)
    plt.ylabel('Features', fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.7) # Thêm lưới mờ cho dễ nhìn
    
    # Lưu ảnh (Quan trọng: bbox_inches='tight' để không bị cắt chữ)
    plt.tight_layout()
    plt.savefig('feature_importance.png', bbox_inches='tight', dpi=300)
    logger.info("Feature importance saved to feature_importance.png")

if __name__ == "__main__":
    DATA_FILE = 'data/dataset_features.csv'
    train_smishing_model(DATA_FILE)