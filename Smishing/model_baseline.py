"""
Baseline Models – Spam Detection
=================================
Dataset  : dataset.csv (2 600 samples, imbalanced ~10% spam)
Features : TF-IDF trên content (5 000 unigram+bigram) +
           has_url, has_phone_number, sender_type (encoded)
Models   : Decision Tree | Random Forest | XGBoost
Metric   : Accuracy, Precision, Recall, F1, ROC-AUC
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
    classification_report,
)
from scipy.sparse import hstack, csr_matrix
import xgboost as xgb

# ──────────────────────────────────────────────
# 1. LOAD & FEATURE ENGINEERING
# ──────────────────────────────────────────────
df = pd.read_csv("data/dataset.csv")

le = LabelEncoder()
df["sender_type_enc"] = le.fit_transform(df["sender_type"])

tfidf = TfidfVectorizer(
    max_features=5_000,
    ngram_range=(1, 2),
    sublinear_tf=True,
)
X_text = tfidf.fit_transform(df["content"].fillna(""))
X_num  = df[["has_url", "has_phone_number", "sender_type_enc"]].values

X = hstack([X_text, csr_matrix(X_num)])
y = df["label"].values

# ──────────────────────────────────────────────
# 2. TRAIN / TEST SPLIT (stratified, 80/20)
# ──────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ──────────────────────────────────────────────
# 3. MODELS
# ──────────────────────────────────────────────
scale_pos = (y_train == 0).sum() / (y_train == 1).sum()   # ~8.4 → dùng cho XGB

models = {
    "Decision Tree": DecisionTreeClassifier(
        max_depth=10,
        min_samples_split=5,
        class_weight="balanced",
        random_state=42,
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        min_samples_split=5,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    ),
    "XGBoost": xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    ),
}

# ──────────────────────────────────────────────
# 4. EVALUATION
# ──────────────────────────────────────────────
print("=" * 62)
print("  BASELINE RESULTS – SPAM DETECTION")
print("=" * 62)

records = []
for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc  = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec  = recall_score(y_test, y_pred, zero_division=0)
    f1   = f1_score(y_test, y_pred, zero_division=0)
    auc  = roc_auc_score(y_test, y_prob)
    cm   = confusion_matrix(y_test, y_pred)

    # 5-fold CV F1 on train set
    cv_f1 = cross_val_score(
        model, X_train, y_train, cv=5, scoring="f1", n_jobs=-1
    ).mean()

    print(f"\n{'─' * 50}")
    print(f"  {name}")
    print(f"{'─' * 50}")
    print(f"  Accuracy       : {acc:.4f}")
    print(f"  Precision      : {prec:.4f}")
    print(f"  Recall         : {rec:.4f}")
    print(f"  F1-Score       : {f1:.4f}")
    print(f"  ROC-AUC        : {auc:.4f}")
    print(f"  CV F1 (5-fold) : {cv_f1:.4f}")
    print(f"\n  Confusion Matrix (rows=Actual, cols=Predicted):")
    print(f"              Pred Ham  Pred Spam")
    print(f"  Actual Ham    {cm[0,0]:>5}     {cm[0,1]:>5}")
    print(f"  Actual Spam   {cm[1,0]:>5}     {cm[1,1]:>5}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Ham','Spam'])}")

    records.append({
        "Model":        name,
        "Accuracy":     round(acc, 4),
        "Precision":    round(prec, 4),
        "Recall":       round(rec, 4),
        "F1":           round(f1, 4),
        "ROC-AUC":      round(auc, 4),
        "CV_F1_5fold":  round(cv_f1, 4),
    })

# ──────────────────────────────────────────────
# 5. SUMMARY TABLE
# ──────────────────────────────────────────────
print("\n" + "=" * 62)
print("  SUMMARY TABLE")
print("=" * 62)
df_res = pd.DataFrame(records).set_index("Model")
print(df_res.to_string())

df_res.to_csv("baseline_results.csv")
print("\n[Saved] baseline_results.csv")