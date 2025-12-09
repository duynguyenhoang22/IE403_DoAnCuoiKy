"""
Train Final MLP Backpropagation với Best Hyperparameters
Dựa trên kết quả experiments:
- Architecture: (20, 10)
- Activation: relu
- Solver: adam
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("🧠 FINAL MLP BACKPROPAGATION MODEL")
print("="*80)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# 1. LOAD DATA
# ============================================================================
print("1️⃣  Loading dataset...")
df = pd.read_csv('data/processed/features_top5.csv')

X = df.drop('label', axis=1)
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"   Training: {X_train.shape[0]} samples")
print(f"   Test: {X_test.shape[0]} samples\n")

# ============================================================================
# 2. TRAIN FINAL MODEL với Best Hyperparameters
# ============================================================================
print("2️⃣  Training Final MLP Model...")
print("-" * 80)

final_mlp = MLPClassifier(
    hidden_layer_sizes=(20, 10),  # Best architecture
    activation='relu',             # Best activation
    solver='adam',                 # Best solver
    learning_rate_init=0.001,      # Default (works well)
    alpha=0.0001,                  # Default regularization
    max_iter=2000,                 # More iterations
    random_state=42,
    early_stopping=True,
    validation_fraction=0.15,      # Slightly more validation data
    n_iter_no_change=20,          # More patience
    verbose=True
)

print("\n📋 Model Configuration:")
print(f"   Architecture:      (20, 10)")
print(f"   Activation:        relu")
print(f"   Solver:            adam")
print(f"   Learning Rate:     0.001")
print(f"   Alpha (L2):        0.0001")
print(f"   Max Iterations:    2000")
print(f"   Early Stopping:    True")
print(f"\n⏳ Training...\n")

start_time = datetime.now()
final_mlp.fit(X_train_scaled, y_train)
training_time = (datetime.now() - start_time).total_seconds()

print(f"\n✅ Training completed in {training_time:.2f}s")
print(f"   Iterations: {final_mlp.n_iter_}")
print(f"   Final Loss: {final_mlp.loss_:.6f}\n")

# ============================================================================
# 3. EVALUATE
# ============================================================================
print("3️⃣  Evaluating Model...")
print("-" * 80)

# Predictions
y_pred_train = final_mlp.predict(X_train_scaled)
y_pred_test = final_mlp.predict(X_test_scaled)
y_proba_test = final_mlp.predict_proba(X_test_scaled)[:, 1]

# Metrics
train_acc = accuracy_score(y_train, y_pred_train)
test_acc = accuracy_score(y_test, y_pred_test)
test_prec = precision_score(y_test, y_pred_test)
test_rec = recall_score(y_test, y_pred_test)
test_f1 = f1_score(y_test, y_pred_test)
test_auc = roc_auc_score(y_test, y_proba_test)

print("\n" + "="*80)
print("📊 FINAL RESULTS")
print("="*80)
print(f"Training Accuracy:   {train_acc*100:.2f}%")
print(f"Test Accuracy:       {test_acc*100:.2f}%")
print(f"Overfitting Gap:     {(train_acc - test_acc)*100:+.2f}%")
print("-"*80)
print(f"Precision:           {test_prec*100:.2f}%")
print(f"Recall:              {test_rec*100:.2f}%")
print(f"F1-Score:            {test_f1*100:.2f}%")
print(f"AUC-ROC:             {test_auc:.4f}")
print("="*80)

# Compare with paper
paper_acc = 97.93
print(f"\n📄 Paper (Backpropagation): {paper_acc}%")
print(f"🔬 Our Result:              {test_acc*100:.2f}%")
print(f"📊 Difference:              {test_acc*100 - paper_acc:+.2f}%")

if test_acc * 100 >= paper_acc:
    print("\n🎉🎉🎉 AMAZING! Đã đạt hoặc vượt paper! 🎉🎉🎉")
elif test_acc * 100 >= paper_acc - 2:
    print("\n🌟 EXCELLENT! Rất gần với paper (< 2% gap)!")
elif test_acc * 100 >= paper_acc - 5:
    print("\n✨ GOOD! Khá gần với paper (< 5% gap)")
else:
    print(f"\n📈 Gap: {paper_acc - test_acc*100:.2f}%")

# ============================================================================
# 4. CROSS-VALIDATION
# ============================================================================
print("\n4️⃣  Cross-Validation (5-fold)...")
print("-" * 80)

cv_mlp = MLPClassifier(
    hidden_layer_sizes=(20, 10),
    activation='relu',
    solver='adam',
    max_iter=2000,
    random_state=42,
    early_stopping=True,
    verbose=False
)

cv_scores = cross_val_score(cv_mlp, X_train_scaled, y_train, cv=5, scoring='accuracy')

print(f"\nCV Scores: {cv_scores}")
print(f"Mean CV Accuracy: {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*100:.2f}%)")
print(f"Min:  {cv_scores.min()*100:.2f}%")
print(f"Max:  {cv_scores.max()*100:.2f}%")

if cv_scores.std() < 0.02:
    print("\n✅ Model is STABLE (low variance)")
else:
    print("\n⚠️  Model has some variance")

# ============================================================================
# 5. DETAILED ANALYSIS
# ============================================================================
print("\n5️⃣  Detailed Analysis")
print("-" * 80)

print("\n📋 Classification Report:")
print(classification_report(y_test, y_pred_test, target_names=['Ham', 'Smishing']))

print("\n📊 Confusion Matrix:")
cm = confusion_matrix(y_test, y_pred_test)
tn, fp, fn, tp = cm.ravel()

print(f"                Predicted")
print(f"              Ham  Smishing")
print(f"Actual Ham    {tn:4d}    {fp:4d}   (Precision: {tn/(tn+fp)*100:.1f}%)")
print(f"     Smishing {fn:4d}    {tp:4d}   (Recall: {tp/(tp+fn)*100:.1f}%)")

print(f"\n🎯 Key Metrics:")
print(f"   True Negatives:  {tn:4d} (Correct Ham)")
print(f"   False Positives: {fp:4d} (Ham → Smishing) ⚠️")
print(f"   False Negatives: {fn:4d} (Smishing → Ham) ❌ DANGEROUS")
print(f"   True Positives:  {tp:4d} (Correct Smishing)")

# ============================================================================
# 6. COMPARE WITH OTHER MODELS
# ============================================================================
print("\n6️⃣  Comparing with Other Models...")
print("-" * 80)

# Load previous results
try:
    other_results = pd.read_csv('data/processed/model_results.csv')
    
    # Add MLP result
    mlp_result = pd.DataFrame([{
        'Model': 'MLP Backpropagation (Optimized)',
        'Accuracy': test_acc * 100,
        'Precision': test_prec * 100,
        'Recall': test_rec * 100,
        'F1-Score': test_f1 * 100,
        'AUC-ROC': test_auc,
        'Time': training_time
    }])
    
    all_results = pd.concat([mlp_result, other_results], ignore_index=True)
    all_results = all_results.sort_values('Accuracy', ascending=False)
    
    print("\n📊 All Models Comparison:")
    print(all_results[['Model', 'Accuracy', 'Precision', 'Recall', 'F1-Score']].to_string(index=False, float_format=lambda x: f'{x:.2f}'))
    
    best_model = all_results.iloc[0]['Model']
    best_acc = all_results.iloc[0]['Accuracy']
    
    print(f"\n🏆 OVERALL BEST MODEL: {best_model}")
    print(f"   Accuracy: {best_acc:.2f}%")
    
except:
    print("   ℹ️  Could not load previous results for comparison")

# ============================================================================
# 7. SAVE MODEL
# ============================================================================
print("\n7️⃣  Saving Model...")
print("-" * 80)

joblib.dump(final_mlp, 'data/processed/best_mlp_final.pkl')
joblib.dump(scaler, 'data/processed/mlp_scaler.pkl')

# Save results
results = {
    'Model': 'MLP Backpropagation (Optimized)',
    'Architecture': '(20, 10)',
    'Activation': 'relu',
    'Solver': 'adam',
    'Train_Accuracy': train_acc * 100,
    'Test_Accuracy': test_acc * 100,
    'Precision': test_prec * 100,
    'Recall': test_rec * 100,
    'F1-Score': test_f1 * 100,
    'AUC-ROC': test_auc,
    'Iterations': final_mlp.n_iter_,
    'Training_Time': training_time,
    'Paper_Gap': test_acc * 100 - paper_acc,
    'CV_Mean': cv_scores.mean() * 100,
    'CV_Std': cv_scores.std() * 100
}

pd.DataFrame([results]).to_csv('data/processed/mlp_final_summary.csv', index=False)

print(f"   ✅ Model: data/processed/best_mlp_final.pkl")
print(f"   ✅ Scaler: data/processed/mlp_scaler.pkl")
print(f"   ✅ Results: data/processed/mlp_final_summary.csv")

# ============================================================================
# 8. VISUALIZATION
# ============================================================================
print("\n8️⃣  Creating Visualizations...")
print("-" * 80)

fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. Training Loss Curve
ax1 = axes[0, 0]
if hasattr(final_mlp, 'loss_curve_'):
    ax1.plot(final_mlp.loss_curve_, linewidth=2, color='#e74c3c')
    ax1.set_xlabel('Iterations', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Loss', fontweight='bold', fontsize=12)
    ax1.set_title('Training Loss Curve', fontsize=14, fontweight='bold')
    ax1.grid(alpha=0.3)
    ax1.text(0.95, 0.95, f'Final Loss: {final_mlp.loss_:.6f}', 
             transform=ax1.transAxes, ha='right', va='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# 2. Metrics Comparison
ax2 = axes[0, 1]
metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
values = [test_acc*100, test_prec*100, test_rec*100, test_f1*100]
colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
bars = ax2.bar(metrics, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax2.set_ylabel('Score (%)', fontweight='bold', fontsize=12)
ax2.set_title('MLP Performance Metrics', fontsize=14, fontweight='bold')
ax2.set_ylim([0, 100])
ax2.axhline(y=paper_acc, color='red', linestyle='--', linewidth=2, label=f'Paper: {paper_acc}%')
ax2.legend()
ax2.grid(axis='y', alpha=0.3)
for bar in bars:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{height:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)

# 3. Confusion Matrix
ax3 = axes[1, 0]
sns.heatmap(cm, annot=True, fmt='d', cmap='RdYlGn', ax=ax3, cbar=True,
            annot_kws={'size': 16, 'weight': 'bold'},
            linewidths=2, linecolor='black')
ax3.set_xlabel('Predicted Label', fontweight='bold', fontsize=12)
ax3.set_ylabel('True Label', fontweight='bold', fontsize=12)
ax3.set_title('Confusion Matrix - MLP Backpropagation', fontsize=14, fontweight='bold')
ax3.set_xticklabels(['Ham', 'Smishing'])
ax3.set_yticklabels(['Ham', 'Smishing'])

# 4. ROC Curve
ax4 = axes[1, 1]
fpr, tpr, thresholds = roc_curve(y_test, y_proba_test)
ax4.plot(fpr, tpr, linewidth=3, color='#3498db', label=f'MLP (AUC={test_auc:.3f})')
ax4.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Random')
ax4.set_xlabel('False Positive Rate', fontweight='bold', fontsize=12)
ax4.set_ylabel('True Positive Rate', fontweight='bold', fontsize=12)
ax4.set_title('ROC Curve', fontsize=14, fontweight='bold')
ax4.legend(loc='lower right', fontsize=11)
ax4.grid(alpha=0.3)
ax4.fill_between(fpr, tpr, alpha=0.2, color='#3498db')

plt.tight_layout()
plt.savefig('data/processed/mlp_final_results.png', dpi=300, bbox_inches='tight')

print(f"   ✅ Visualization: data/processed/mlp_final_results.png")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("🎉 MLP BACKPROPAGATION TRAINING COMPLETED!")
print("="*80)

print(f"\n✨ Final Results:")
print(f"   🎯 Test Accuracy:  {test_acc*100:.2f}%")
print(f"   🎯 Precision:      {test_prec*100:.2f}%")
print(f"   🎯 Recall:         {test_rec*100:.2f}%")
print(f"   🎯 F1-Score:       {test_f1*100:.2f}%")
print(f"   🎯 AUC-ROC:        {test_auc:.4f}")

print(f"\n📊 Comparison:")
print(f"   Paper:    {paper_acc:.2f}%")
print(f"   Our MLP:  {test_acc*100:.2f}%")
print(f"   Gap:      {test_acc*100 - paper_acc:+.2f}%")

print(f"\n📂 Output Files:")
print(f"   - data/processed/best_mlp_final.pkl")
print(f"   - data/processed/mlp_scaler.pkl")
print(f"   - data/processed/mlp_final_summary.csv")
print(f"   - data/processed/mlp_final_results.png")

print("\n" + "="*80)
print("✅ All experiments completed successfully!")
print("="*80)

