import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    precision_recall_curve, accuracy_score, recall_score,
    f1_score, precision_score
)
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Load & Preprocess (dùng chung cho cả 2 hàm train)
# =============================================================================

def _load_and_preprocess(data_path, encoder_path='sender_encoder.pkl'):
    """
    Load CSV, drop 'content', encode 'sender_type', tách X/y.
    Trả về (X, y, feature_names).
    """
    logger.info(f"Loading dataset from {data_path}...")
    df = pd.read_csv(data_path)

    if 'content' in df.columns:
        df = df.drop(columns=['content'])

    if 'sender_type' in df.columns:
        logger.info("Encoding 'sender_type' column...")
        le = LabelEncoder()
        df['sender_type'] = le.fit_transform(df['sender_type'].astype(str))
        joblib.dump(le, encoder_path)
        logger.info(f"Sender encoder saved to {encoder_path}")

    X = df.drop(columns=['label'])
    y = df['label']

    logger.info(f"Dataset shape: {X.shape}")
    logger.info(f"Class distribution:\n{y.value_counts()}")
    return X, y


def _find_best_threshold(y_true, y_prob):
    """
    Tìm threshold tối ưu theo F1-Score từ Precision-Recall curve.
    Trả về (best_threshold, best_f1, precisions, recalls, thresholds).
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    denom = precisions + recalls
    f1_scores = np.where(denom > 0, 2 * (precisions * recalls) / denom, 0.0)
    best_idx = int(np.argmax(f1_scores))
    # thresholds có len = len(precisions) - 1; clamp index an toàn
    best_idx = min(best_idx, len(thresholds) - 1)
    return thresholds[best_idx], f1_scores[best_idx], precisions, recalls, thresholds


def _save_model_artifacts(model, feature_names, threshold, model_output):
    """
    Lưu model (.pkl) và metadata (.meta.pkl) gồm feature_names & threshold.
    predict_system.py sẽ load cả hai để đảm bảo khớp feature order và ngưỡng.
    """
    joblib.dump(model, model_output)
    meta_path = model_output.replace('.pkl', '.meta.pkl')
    joblib.dump({'feature_names': list(feature_names), 'threshold': threshold}, meta_path)
    logger.info(f"Model saved to {model_output}")
    logger.info(f"Metadata (feature_names, threshold={threshold:.4f}) saved to {meta_path}")


# =============================================================================
# HÀM 1: Train XGBoost đơn lẻ + đánh giá chi tiết
# =============================================================================

def train_smishing_model(data_path, model_output='smishing_xgb.pkl',
                         encoder_path='sender_encoder.pkl'):
    # 1. Load & Preprocess
    X, y = _load_and_preprocess(data_path, encoder_path)

    # 2. Chia tập Train/Test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 3. Cấu hình XGBoost
    pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    model = xgb.XGBClassifier(
        objective='binary:logistic',
        colsample_bytree=0.8,
        gamma=0.1,
        subsample=0.8,
        min_child_weight=3,
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        scale_pos_weight=pos_weight,
        eval_metric='auc',
        random_state=42
    )

    # 4. Huấn luyện
    logger.info("Training XGBoost model...")
    model.fit(X_train, y_train)

    # 5. Tính xác suất dự đoán
    y_prob = model.predict_proba(X_test)[:, 1]

    # 6. Tìm threshold tối ưu (thay vì hard-code 0.46)
    best_threshold, best_f1, precisions, recalls, thresholds = _find_best_threshold(y_test, y_prob)
    logger.info(f"Best Threshold: {best_threshold:.4f}  |  Best F1: {best_f1:.4f}")

    y_pred = (y_prob >= best_threshold).astype(int)

    # 7. Đánh giá trên Test set
    print(f"\n=== KẾT QUẢ VỚI THRESHOLD TỐI ƯU = {best_threshold:.4f} ===")
    print(classification_report(y_test, y_pred, target_names=['Clean', 'Smishing']))
    print(f"ROC-AUC Score: {roc_auc_score(y_test, y_prob):.4f}")

    # 8. Kiểm tra Overfitting (Train vs Test)
    print("\n" + "="*40)
    print("KIỂM TRA OVERFITTING (Train vs Test)")
    print("="*40)

    y_train_prob = model.predict_proba(X_train)[:, 1]
    y_train_pred = (y_train_prob >= best_threshold).astype(int)

    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc  = accuracy_score(y_test, y_pred)
    train_recall = recall_score(y_train, y_train_pred)
    test_recall  = recall_score(y_test, y_pred)

    print(f"Accuracy: Train={train_acc:.4f} vs Test={test_acc:.4f} | Δ={train_acc - test_acc:.4f}")
    print(f"Recall:   Train={train_recall:.4f} vs Test={test_recall:.4f} | Δ={train_recall - test_recall:.4f}")

    if (train_acc - test_acc) > 0.05:
        print(">> CẢNH BÁO: Có dấu hiệu Overfitting (Chênh lệch > 5%)")
    else:
        print(">> AN TOÀN: Mô hình tổng quát hóa tốt.")

    # 9. Cross-Validation (trên toàn X để đo độ ổn định)
    print("\n" + "="*40)
    print("KIỂM TRA ĐỘ ỔN ĐỊNH (Cross-Validation 5-fold)")
    print("="*40)
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
    print(f"ROC-AUC qua 5 fold: {cv_scores}")
    print(f"Trung bình: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # 10. Vẽ Precision-Recall Curve
    best_idx = int(np.argmin(np.abs(thresholds - best_threshold)))
    plt.figure(figsize=(10, 6))
    plt.plot(recalls, precisions, marker='.', label='XGBoost')
    plt.scatter(recalls[best_idx], precisions[best_idx],
                marker='o', color='red', zorder=10,
                label=f'Best Threshold={best_threshold:.2f}')
    plt.title(f'Precision-Recall Curve (Best Threshold = {best_threshold:.2f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig('pr_curve.png', bbox_inches='tight', dpi=150)
    plt.close()
    logger.info("PR Curve saved to pr_curve.png")

    # 11. Vẽ Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Clean', 'Smishing'],
                yticklabels=['Clean', 'Smishing'])
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig('confusion_matrix.png', bbox_inches='tight', dpi=150)
    plt.close()
    logger.info("Confusion matrix saved to confusion_matrix.png")

    # 12. Vẽ Feature Importance
    fi_df = pd.DataFrame({
        'Feature': X.columns,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False).head(20)

    plt.figure(figsize=(12, 8))
    sns.barplot(x='Importance', y='Feature', hue='Feature',
                data=fi_df, palette='viridis', legend=False)
    plt.title('Top 20 Feature Importance (XGBoost)', fontsize=15, fontweight='bold')
    plt.xlabel('Importance Score', fontsize=12)
    plt.ylabel('Features', fontsize=12)
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('feature_importance.png', bbox_inches='tight', dpi=300)
    plt.close()
    logger.info("Feature importance saved to feature_importance.png")

    # 13. Lưu Model + Metadata
    _save_model_artifacts(model, X.columns, best_threshold, model_output)

    results = {
        'model': model,
        'best_threshold': best_threshold,
        'feature_names': list(X.columns),
        'auc': roc_auc_score(y_test, y_prob),
        'f1': best_f1,
        'accuracy': test_acc,
        'recall': test_recall,
    }
    return results


# =============================================================================
# HÀM 2: So sánh nhiều models, lưu model tốt nhất
# =============================================================================

def train_and_compare_models(data_path, model_output='best_model.pkl',
                             encoder_path='sender_encoder.pkl'):
    """Train và so sánh Decision Tree, Random Forest, XGBoost."""
    # 1. Load & Preprocess (dùng chung helper)
    X, y = _load_and_preprocess(data_path, encoder_path)

    # 2. Chia tập Train/Test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 3. Định nghĩa các models
    pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    models = {
        'Decision Tree': DecisionTreeClassifier(
            max_depth=10, min_samples_split=10, min_samples_leaf=5,
            random_state=42, class_weight='balanced'
        ),
        'Random Forest': RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_split=10,
            min_samples_leaf=5, random_state=42,
            class_weight='balanced', n_jobs=-1
        ),
        'XGBoost': xgb.XGBClassifier(
            objective='binary:logistic',
            colsample_bytree=0.8, gamma=0.1, subsample=0.8,
            min_child_weight=3, n_estimators=200, learning_rate=0.05,
            max_depth=4, scale_pos_weight=pos_weight,
            eval_metric='auc', random_state=42
        )
    }

    # 4. Train & đánh giá từng model với threshold tối ưu riêng
    results = {}

    for name, model in models.items():
        logger.info(f"Training {name}...")
        model.fit(X_train, y_train)

        y_prob = model.predict_proba(X_test)[:, 1]

        # Tìm threshold tối ưu theo F1 thay vì dùng hằng số cứng
        best_thr, _, _, _, _ = _find_best_threshold(y_test, y_prob)
        y_pred = (y_prob >= best_thr).astype(int)

        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec  = recall_score(y_test, y_pred, zero_division=0)
        f1   = f1_score(y_test, y_pred, zero_division=0)
        auc  = roc_auc_score(y_test, y_prob)

        results[name] = {
            'model': model,
            'best_threshold': best_thr,
            'accuracy': acc,
            'precision': prec,
            'recall': rec,
            'f1': f1,
            'auc': auc,
            'y_pred': y_pred,
            'y_prob': y_prob,
        }

        print(f"\n=== {name.upper()} (threshold={best_thr:.4f}) ===")
        print(classification_report(y_test, y_pred, target_names=['Clean', 'Smishing']))
        print(f"ROC-AUC Score: {auc:.4f}")

    # 5. Bảng so sánh
    print("\n" + "="*70)
    print("MODEL COMPARISON SUMMARY")
    print("="*70)
    print(f"{'Model':<15} {'Threshold':<10} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1':<10} {'AUC':<10}")
    print("-"*75)
    for name, m in results.items():
        print(f"{name:<15} {m['best_threshold']:<10.4f} {m['accuracy']:<10.4f} "
              f"{m['precision']:<10.4f} {m['recall']:<10.4f} {m['f1']:<10.4f} {m['auc']:<10.4f}")

    # 6. Lưu model tốt nhất theo F1
    best_name = max(results, key=lambda n: results[n]['f1'])
    best_model = results[best_name]['model']
    best_thr   = results[best_name]['best_threshold']
    print(f"\n>> Best model (F1-Score): {best_name}  threshold={best_thr:.4f}")

    _save_model_artifacts(best_model, X.columns, best_thr, model_output)

    # 7. Vẽ Precision-Recall curves so sánh
    plt.figure(figsize=(12, 8))
    for name, m in results.items():
        precs, recs, _ = precision_recall_curve(y_test, m['y_prob'])
        plt.plot(recs, precs, marker='.', label=f'{name} (AUC={m["auc"]:.3f})')
    plt.title('Precision-Recall Curves Comparison')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.savefig('pr_curves_comparison.png', bbox_inches='tight', dpi=300)
    plt.close()
    logger.info("PR curves comparison saved to pr_curves_comparison.png")

    # 8. Feature Importance cho model tốt nhất
    if hasattr(best_model, 'feature_importances_'):
        fi_df = pd.DataFrame({
            'Feature': X.columns,
            'Importance': best_model.feature_importances_
        }).sort_values('Importance', ascending=False).head(20)

        plt.figure(figsize=(12, 8))
        sns.barplot(x='Importance', y='Feature', hue='Feature',
                    data=fi_df, palette='viridis', legend=False)
        plt.title(f'Top 20 Feature Importance ({best_name})', fontsize=15, fontweight='bold')
        plt.xlabel('Importance Score', fontsize=12)
        plt.ylabel('Features', fontsize=12)
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('feature_importance_best_model.png', bbox_inches='tight', dpi=300)
        plt.close()
        logger.info("Feature importance saved to feature_importance_best_model.png")

    return results


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    DATA_FILE = 'data/dataset_features.csv'
    train_smishing_model(DATA_FILE)
    train_and_compare_models(DATA_FILE)
