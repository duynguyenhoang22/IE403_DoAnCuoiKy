"""
Script train các mô hình ML để phát hiện Smishing SMS
Sử dụng Top 5 Features từ DSmishSMS paper

Models:
1. MLP Neural Network (Backpropagation)
2. Random Forest
3. SVM
4. Logistic Regression
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Machine Learning
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)

# Models
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
import joblib

print("="*80)
print("🤖 SMISHING DETECTION - MODEL TRAINING")
print("="*80)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# 1. LOAD DATASET
# ============================================================================
print("1️⃣  Loading dataset...")
df = pd.read_csv('data/processed/features_top5.csv')

print(f"   📊 Shape: {df.shape}")
print(f"   📋 Features: {[col for col in df.columns if col != 'label']}")
print(f"   📈 Label distribution:")
print(f"      - Ham (0): {len(df[df['label']==0])} ({len(df[df['label']==0])/len(df)*100:.1f}%)")
print(f"      - Smishing (1): {len(df[df['label']==1])} ({len(df[df['label']==1])/len(df)*100:.1f}%)")

# ============================================================================
# 2. DATA PREPARATION
# ============================================================================
print("\n2️⃣  Preparing data...")
X = df.drop('label', axis=1)
y = df['label']

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"   Training set: {X_train.shape[0]} samples")
print(f"   Test set: {X_test.shape[0]} samples")

# Feature scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"   ✅ Features scaled (StandardScaler)")

# ============================================================================
# 3. TRAIN MODELS
# ============================================================================
print("\n3️⃣  Training models...")
print("-" * 80)

models = {}
results = []

# 3.1. MLP Neural Network (Backpropagation)
print("\n🧠 MLP Neural Network (Backpropagation)...")
mlp = MLPClassifier(
    hidden_layer_sizes=(10, 5),
    activation='relu',
    solver='adam',
    max_iter=1000,
    random_state=42,
    early_stopping=True,
    validation_fraction=0.1
)
start = datetime.now()
mlp.fit(X_train_scaled, y_train)
duration = (datetime.now() - start).total_seconds()

y_pred_mlp = mlp.predict(X_test_scaled)
y_proba_mlp = mlp.predict_proba(X_test_scaled)[:, 1]

models['MLP'] = mlp
results.append({
    'Model': 'MLP (Backpropagation)',
    'Accuracy': accuracy_score(y_test, y_pred_mlp),
    'Precision': precision_score(y_test, y_pred_mlp),
    'Recall': recall_score(y_test, y_pred_mlp),
    'F1-Score': f1_score(y_test, y_pred_mlp),
    'AUC-ROC': roc_auc_score(y_test, y_proba_mlp),
    'Time': duration
})
print(f"   ✅ Trained in {duration:.2f}s | Accuracy: {results[-1]['Accuracy']*100:.2f}%")

# 3.2. Random Forest
print("\n🌲 Random Forest...")
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
start = datetime.now()
rf.fit(X_train, y_train)
duration = (datetime.now() - start).total_seconds()

y_pred_rf = rf.predict(X_test)
y_proba_rf = rf.predict_proba(X_test)[:, 1]

models['RF'] = rf
results.append({
    'Model': 'Random Forest',
    'Accuracy': accuracy_score(y_test, y_pred_rf),
    'Precision': precision_score(y_test, y_pred_rf),
    'Recall': recall_score(y_test, y_pred_rf),
    'F1-Score': f1_score(y_test, y_pred_rf),
    'AUC-ROC': roc_auc_score(y_test, y_proba_rf),
    'Time': duration
})
print(f"   ✅ Trained in {duration:.2f}s | Accuracy: {results[-1]['Accuracy']*100:.2f}%")

# 3.3. SVM
print("\n⚡ Support Vector Machine...")
svm = SVC(
    kernel='rbf',
    C=1.0,
    gamma='scale',
    probability=True,
    random_state=42
)
start = datetime.now()
svm.fit(X_train_scaled, y_train)
duration = (datetime.now() - start).total_seconds()

y_pred_svm = svm.predict(X_test_scaled)
y_proba_svm = svm.predict_proba(X_test_scaled)[:, 1]

models['SVM'] = svm
results.append({
    'Model': 'SVM',
    'Accuracy': accuracy_score(y_test, y_pred_svm),
    'Precision': precision_score(y_test, y_pred_svm),
    'Recall': recall_score(y_test, y_pred_svm),
    'F1-Score': f1_score(y_test, y_pred_svm),
    'AUC-ROC': roc_auc_score(y_test, y_proba_svm),
    'Time': duration
})
print(f"   ✅ Trained in {duration:.2f}s | Accuracy: {results[-1]['Accuracy']*100:.2f}%")

# 3.4. Logistic Regression
print("\n📊 Logistic Regression...")
lr = LogisticRegression(
    max_iter=1000,
    random_state=42,
    n_jobs=-1
)
start = datetime.now()
lr.fit(X_train_scaled, y_train)
duration = (datetime.now() - start).total_seconds()

y_pred_lr = lr.predict(X_test_scaled)
y_proba_lr = lr.predict_proba(X_test_scaled)[:, 1]

models['LR'] = lr
results.append({
    'Model': 'Logistic Regression',
    'Accuracy': accuracy_score(y_test, y_pred_lr),
    'Precision': precision_score(y_test, y_pred_lr),
    'Recall': recall_score(y_test, y_pred_lr),
    'F1-Score': f1_score(y_test, y_pred_lr),
    'AUC-ROC': roc_auc_score(y_test, y_proba_lr),
    'Time': duration
})
print(f"   ✅ Trained in {duration:.2f}s | Accuracy: {results[-1]['Accuracy']*100:.2f}%")

print("-" * 80)

# ============================================================================
# 4. RESULTS COMPARISON
# ============================================================================
print("\n4️⃣  Comparing results...")
results_df = pd.DataFrame(results)

# Format percentages
for col in ['Accuracy', 'Precision', 'Recall', 'F1-Score']:
    results_df[col] = results_df[col] * 100

# Sort by Accuracy
results_df = results_df.sort_values('Accuracy', ascending=False).reset_index(drop=True)

print("\n" + "="*80)
print("📊 MODEL COMPARISON RESULTS")
print("="*80)
print(results_df.to_string(index=False, float_format=lambda x: f'{x:.2f}'))
print("="*80)

# Best model
best_model_name = results_df.iloc[0]['Model']
best_acc = results_df.iloc[0]['Accuracy']
paper_acc = 97.93

print(f"\n🏆 BEST MODEL: {best_model_name}")
print(f"   Accuracy: {best_acc:.2f}%")
print(f"   Precision: {results_df.iloc[0]['Precision']:.2f}%")
print(f"   Recall: {results_df.iloc[0]['Recall']:.2f}%")
print(f"   F1-Score: {results_df.iloc[0]['F1-Score']:.2f}%")
print(f"   AUC-ROC: {results_df.iloc[0]['AUC-ROC']:.4f}")

print(f"\n📄 PAPER RESULT (DSmishSMS): {paper_acc}%")
print(f"   Difference: {best_acc - paper_acc:+.2f}%")

if best_acc >= paper_acc:
    print(f"\n🎉 EXCELLENT! Đã đạt hoặc vượt kết quả trong paper!")
else:
    gap = paper_acc - best_acc
    print(f"\n📈 Good result! Khoảng cách: {gap:.2f}%")

# ============================================================================
# 5. FEATURE IMPORTANCE (Random Forest)
# ============================================================================
print("\n5️⃣  Feature Importance (Random Forest)...")
feature_imp = pd.DataFrame({
    'Feature': X.columns,
    'Importance': rf.feature_importances_
}).sort_values('Importance', ascending=False)

print("\n📊 Feature Importance Ranking:")
for idx, row in feature_imp.iterrows():
    print(f"   {row['Feature']:30s}: {row['Importance']:.4f}")

# ============================================================================
# 6. SAVE MODELS
# ============================================================================
print("\n6️⃣  Saving models...")

# Save best model
best_key = 'MLP' if 'MLP' in best_model_name else 'RF' if 'Forest' in best_model_name else 'SVM' if 'SVM' in best_model_name else 'LR'
best_model = models[best_key]

joblib.dump(best_model, f'data/processed/best_model_{best_key.lower()}.pkl')
joblib.dump(scaler, 'data/processed/scaler.pkl')
results_df.to_csv('data/processed/model_results.csv', index=False)

print(f"   ✅ Best model saved: data/processed/best_model_{best_key.lower()}.pkl")
print(f"   ✅ Scaler saved: data/processed/scaler.pkl")
print(f"   ✅ Results saved: data/processed/model_results.csv")

# ============================================================================
# 7. VISUALIZATION
# ============================================================================
print("\n7️⃣  Creating visualizations...")

plt.style.use('seaborn-v0_8-darkgrid')
fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 7.1. Accuracy Bar Chart
ax1 = axes[0, 0]
colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
bars = ax1.barh(results_df['Model'], results_df['Accuracy'], color=colors[:len(results_df)])
ax1.set_xlabel('Accuracy (%)', fontsize=12, fontweight='bold')
ax1.set_title('Model Accuracy Comparison', fontsize=14, fontweight='bold')
ax1.axvline(paper_acc, color='red', linestyle='--', linewidth=2, label=f'Paper: {paper_acc}%')
ax1.legend()
ax1.grid(axis='x', alpha=0.3)
for bar in bars:
    width = bar.get_width()
    ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:.2f}%',
             ha='left', va='center', fontsize=10, fontweight='bold')

# 7.2. All Metrics
ax2 = axes[0, 1]
x = np.arange(len(results_df))
width = 0.2
metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
colors_metrics = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
for i, metric in enumerate(metrics):
    ax2.bar(x + (i-1.5)*width, results_df[metric], width, label=metric, color=colors_metrics[i])
ax2.set_ylabel('Score (%)', fontsize=12, fontweight='bold')
ax2.set_title('All Metrics Comparison', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(results_df['Model'], rotation=15, ha='right')
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# 7.3. ROC Curves
ax3 = axes[1, 0]
fpr_mlp, tpr_mlp, _ = roc_curve(y_test, y_proba_mlp)
fpr_rf, tpr_rf, _ = roc_curve(y_test, y_proba_rf)
fpr_svm, tpr_svm, _ = roc_curve(y_test, y_proba_svm)
fpr_lr, tpr_lr, _ = roc_curve(y_test, y_proba_lr)

ax3.plot(fpr_mlp, tpr_mlp, label=f'MLP (AUC={results_df[results_df["Model"]=="MLP (Backpropagation)"]["AUC-ROC"].values[0]:.3f})', linewidth=2)
ax3.plot(fpr_rf, tpr_rf, label=f'RF (AUC={results_df[results_df["Model"]=="Random Forest"]["AUC-ROC"].values[0]:.3f})', linewidth=2)
ax3.plot(fpr_svm, tpr_svm, label=f'SVM (AUC={results_df[results_df["Model"]=="SVM"]["AUC-ROC"].values[0]:.3f})', linewidth=2)
ax3.plot(fpr_lr, tpr_lr, label=f'LR (AUC={results_df[results_df["Model"]=="Logistic Regression"]["AUC-ROC"].values[0]:.3f})', linewidth=2)
ax3.plot([0, 1], [0, 1], 'k--', label='Random', linewidth=1)
ax3.set_xlabel('False Positive Rate', fontsize=12, fontweight='bold')
ax3.set_ylabel('True Positive Rate', fontsize=12, fontweight='bold')
ax3.set_title('ROC Curves', fontsize=14, fontweight='bold')
ax3.legend(loc='lower right')
ax3.grid(alpha=0.3)

# 7.4. Confusion Matrix (Best Model)
ax4 = axes[1, 1]
y_pred_best = y_pred_mlp if 'MLP' in best_model_name else y_pred_rf if 'Forest' in best_model_name else y_pred_svm if 'SVM' in best_model_name else y_pred_lr
cm = confusion_matrix(y_test, y_pred_best)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax4, cbar=False, 
            annot_kws={'size': 14, 'weight': 'bold'})
ax4.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
ax4.set_ylabel('True Label', fontsize=12, fontweight='bold')
ax4.set_title(f'Confusion Matrix - {best_model_name}', fontsize=14, fontweight='bold')
ax4.set_xticklabels(['Ham', 'Smishing'])
ax4.set_yticklabels(['Ham', 'Smishing'])

plt.tight_layout()
plt.savefig('data/processed/model_comparison.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Visualization saved: data/processed/model_comparison.png")

# ============================================================================
# 8. CLASSIFICATION REPORT
# ============================================================================
print("\n8️⃣  Detailed Classification Report (Best Model)...")
print("\n" + "="*80)
print(f"📋 CLASSIFICATION REPORT - {best_model_name}")
print("="*80)
print(classification_report(y_test, y_pred_best, target_names=['Ham (0)', 'Smishing (1)']))
print("="*80)

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("🎉 MODEL TRAINING COMPLETED!")
print("="*80)
print("✅ Achievements:")
print(f"   - Trained 4 models successfully")
print(f"   - Best model: {best_model_name} ({best_acc:.2f}%)")
print(f"   - Paper comparison: {best_acc - paper_acc:+.2f}%")
print(f"\n📂 Output files:")
print(f"   - data/processed/best_model_{best_key.lower()}.pkl")
print(f"   - data/processed/scaler.pkl")
print(f"   - data/processed/model_results.csv")
print(f"   - data/processed/model_comparison.png")
print("="*80)

