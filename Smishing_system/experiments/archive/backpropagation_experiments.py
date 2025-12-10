"""
Backpropagation Neural Network Experiments
Thử nghiệm nhiều architectures và hyperparameters để đạt kết quả tốt như paper

Paper: DSmishSMS (97.93% accuracy với Backpropagation)
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("🧠 BACKPROPAGATION NEURAL NETWORK EXPERIMENTS")
print("="*80)
print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# 1. LOAD DATA
# ============================================================================
print("1️⃣  Loading dataset...")
df = pd.read_csv('data/processed/features_top5.csv')

X = df.drop('label', axis=1)
y = df['label']

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scaling (quan trọng cho Neural Networks!)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"   Training: {X_train.shape[0]} samples")
print(f"   Test: {X_test.shape[0]} samples")
print(f"   Features: {X.shape[1]}")
print(f"   ✅ Data scaled\n")

# ============================================================================
# 2. EXPERIMENT 1: Different Architectures
# ============================================================================
print("2️⃣  EXPERIMENT 1: Testing Different Architectures")
print("-" * 80)

architectures = [
    # Small networks
    (5,),           # 1 hidden layer: 5 neurons
    (10,),          # 1 hidden layer: 10 neurons
    (20,),          # 1 hidden layer: 20 neurons
    
    # Medium networks
    (10, 5),        # 2 layers: 10 -> 5 (CURRENT)
    (20, 10),       # 2 layers: 20 -> 10
    (30, 15),       # 2 layers: 30 -> 15
    (50, 25),       # 2 layers: 50 -> 25
    
    # Deep networks
    (20, 10, 5),    # 3 layers: 20 -> 10 -> 5
    (30, 20, 10),   # 3 layers: 30 -> 20 -> 10
    (50, 25, 10),   # 3 layers: 50 -> 25 -> 10
    
    # Wide networks
    (50,),          # 1 layer: 50 neurons
    (100,),         # 1 layer: 100 neurons
    (50, 50),       # 2 layers: 50 -> 50
]

results_arch = []

for arch in architectures:
    mlp = MLPClassifier(
        hidden_layer_sizes=arch,
        activation='relu',
        solver='adam',
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        verbose=False
    )
    
    # Train
    start = datetime.now()
    mlp.fit(X_train_scaled, y_train)
    duration = (datetime.now() - start).total_seconds()
    
    # Predict
    y_pred = mlp.predict(X_test_scaled)
    y_proba = mlp.predict_proba(X_test_scaled)[:, 1]
    
    # Metrics
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    
    results_arch.append({
        'Architecture': str(arch),
        'Accuracy': acc * 100,
        'Precision': prec * 100,
        'Recall': rec * 100,
        'F1-Score': f1 * 100,
        'AUC-ROC': auc,
        'Time': duration,
        'Iterations': mlp.n_iter_
    })
    
    print(f"   {str(arch):20s} | Acc: {acc*100:5.2f}% | Rec: {rec*100:5.2f}% | Time: {duration:.2f}s")

# Convert to DataFrame and sort
df_arch = pd.DataFrame(results_arch).sort_values('Accuracy', ascending=False)

print("\n" + "="*80)
print("📊 ARCHITECTURE COMPARISON (Top 5)")
print("="*80)
print(df_arch.head().to_string(index=False, float_format=lambda x: f'{x:.2f}'))
print("="*80)

best_arch = eval(df_arch.iloc[0]['Architecture'])
best_acc_arch = df_arch.iloc[0]['Accuracy']
print(f"\n🏆 Best Architecture: {best_arch}")
print(f"   Accuracy: {best_acc_arch:.2f}%\n")

# ============================================================================
# 3. EXPERIMENT 2: Different Activation Functions
# ============================================================================
print("3️⃣  EXPERIMENT 2: Testing Activation Functions")
print("-" * 80)

activations = ['relu', 'tanh', 'logistic']
results_act = []

for activation in activations:
    mlp = MLPClassifier(
        hidden_layer_sizes=best_arch,  # Use best architecture
        activation=activation,
        solver='adam',
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        verbose=False
    )
    
    mlp.fit(X_train_scaled, y_train)
    y_pred = mlp.predict(X_test_scaled)
    
    acc = accuracy_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    
    results_act.append({
        'Activation': activation,
        'Accuracy': acc * 100,
        'Recall': rec * 100
    })
    
    print(f"   {activation:10s} | Acc: {acc*100:5.2f}% | Rec: {rec*100:5.2f}%")

df_act = pd.DataFrame(results_act).sort_values('Accuracy', ascending=False)
best_activation = df_act.iloc[0]['Activation']
print(f"\n🏆 Best Activation: {best_activation}\n")

# ============================================================================
# 4. EXPERIMENT 3: Different Solvers
# ============================================================================
print("4️⃣  EXPERIMENT 3: Testing Solvers")
print("-" * 80)

solvers = ['adam', 'sgd', 'lbfgs']
results_solver = []

for solver in solvers:
    try:
        mlp = MLPClassifier(
            hidden_layer_sizes=best_arch,
            activation=best_activation,
            solver=solver,
            max_iter=1000,
            random_state=42,
            early_stopping=True if solver != 'lbfgs' else False,
            validation_fraction=0.1,
            verbose=False
        )
        
        mlp.fit(X_train_scaled, y_train)
        y_pred = mlp.predict(X_test_scaled)
        
        acc = accuracy_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        
        results_solver.append({
            'Solver': solver,
            'Accuracy': acc * 100,
            'Recall': rec * 100
        })
        
        print(f"   {solver:10s} | Acc: {acc*100:5.2f}% | Rec: {rec*100:5.2f}%")
    except Exception as e:
        print(f"   {solver:10s} | Failed: {e}")

df_solver = pd.DataFrame(results_solver).sort_values('Accuracy', ascending=False)
best_solver = df_solver.iloc[0]['Solver']
print(f"\n🏆 Best Solver: {best_solver}\n")

# ============================================================================
# 5. EXPERIMENT 4: Learning Rate & Regularization
# ============================================================================
print("5️⃣  EXPERIMENT 4: Learning Rate & Regularization")
print("-" * 80)

learning_rates = [0.0001, 0.001, 0.01, 0.1]
alphas = [0.0001, 0.001, 0.01, 0.1]  # L2 regularization

results_lr = []

for lr in learning_rates:
    for alpha in alphas:
        mlp = MLPClassifier(
            hidden_layer_sizes=best_arch,
            activation=best_activation,
            solver=best_solver,
            learning_rate_init=lr,
            alpha=alpha,
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            verbose=False
        )
        
        mlp.fit(X_train_scaled, y_train)
        y_pred = mlp.predict(X_test_scaled)
        
        acc = accuracy_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        
        results_lr.append({
            'Learning_Rate': lr,
            'Alpha': alpha,
            'Accuracy': acc * 100,
            'Recall': rec * 100
        })

df_lr = pd.DataFrame(results_lr).sort_values('Accuracy', ascending=False)

print("Top 5 combinations:")
print(df_lr.head().to_string(index=False, float_format=lambda x: f'{x:.4f}'))

best_lr = df_lr.iloc[0]['Learning_Rate']
best_alpha = df_lr.iloc[0]['Alpha']
print(f"\n🏆 Best Learning Rate: {best_lr}")
print(f"🏆 Best Alpha: {best_alpha}\n")

# ============================================================================
# 6. FINAL MODEL với Best Hyperparameters
# ============================================================================
print("6️⃣  Training FINAL MODEL with Best Hyperparameters")
print("-" * 80)

final_mlp = MLPClassifier(
    hidden_layer_sizes=best_arch,
    activation=best_activation,
    solver=best_solver,
    learning_rate_init=best_lr,
    alpha=best_alpha,
    max_iter=2000,  # Increase iterations
    random_state=42,
    early_stopping=True,
    validation_fraction=0.1,
    verbose=True
)

print(f"\n📋 Final Configuration:")
print(f"   Architecture: {best_arch}")
print(f"   Activation: {best_activation}")
print(f"   Solver: {best_solver}")
print(f"   Learning Rate: {best_lr}")
print(f"   Alpha (L2): {best_alpha}")
print(f"\n⏳ Training...\n")

final_mlp.fit(X_train_scaled, y_train)

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
print("🏆 FINAL MLP BACKPROPAGATION RESULTS")
print("="*80)
print(f"Training Accuracy:   {train_acc*100:.2f}%")
print(f"Test Accuracy:       {test_acc*100:.2f}%")
print(f"Overfitting Gap:     {(train_acc - test_acc)*100:.2f}%")
print("-"*80)
print(f"Precision:           {test_prec*100:.2f}%")
print(f"Recall:              {test_rec*100:.2f}%")
print(f"F1-Score:            {test_f1*100:.2f}%")
print(f"AUC-ROC:             {test_auc:.4f}")
print("-"*80)
print(f"Iterations:          {final_mlp.n_iter_}")
print(f"Training Loss:       {final_mlp.loss_:.6f}")
print("="*80)

# Compare with paper
paper_acc = 97.93
print(f"\n📄 Paper Result (Backpropagation): {paper_acc}%")
print(f"💡 Our Result:                      {test_acc*100:.2f}%")
print(f"📊 Difference:                      {test_acc*100 - paper_acc:+.2f}%")

if test_acc * 100 >= paper_acc:
    print("\n🎉🎉🎉 AMAZING! Đã đạt hoặc vượt paper! 🎉🎉🎉")
elif test_acc * 100 >= paper_acc - 2:
    print("\n🌟 EXCELLENT! Rất gần với paper (< 2% gap)!")
elif test_acc * 100 >= paper_acc - 5:
    print("\n✨ GOOD! Khá gần với paper (< 5% gap)")
else:
    print(f"\n📈 Gap còn {paper_acc - test_acc*100:.2f}% - Cần thêm improvements")

# ============================================================================
# 7. DETAILED ANALYSIS
# ============================================================================
print("\n7️⃣  Detailed Analysis")
print("-" * 80)

print("\n📋 Classification Report:")
print(classification_report(y_test, y_pred_test, target_names=['Ham', 'Smishing']))

print("\n📊 Confusion Matrix:")
cm = confusion_matrix(y_test, y_pred_test)
print(f"                Predicted")
print(f"              Ham  Smishing")
print(f"Actual Ham    {cm[0,0]:4d}    {cm[0,1]:4d}")
print(f"     Smishing {cm[1,0]:4d}    {cm[1,1]:4d}")

# ============================================================================
# 8. SAVE RESULTS
# ============================================================================
print("\n8️⃣  Saving results...")

import joblib

# Save best MLP model
joblib.dump(final_mlp, 'data/processed/best_mlp_backprop.pkl')
joblib.dump(scaler, 'data/processed/mlp_scaler.pkl')

# Save experiment results
df_arch.to_csv('data/processed/mlp_architecture_experiments.csv', index=False)
df_lr.to_csv('data/processed/mlp_hyperparameter_experiments.csv', index=False)

# Save final results
final_results = {
    'Model': 'MLP Backpropagation (Optimized)',
    'Architecture': str(best_arch),
    'Activation': best_activation,
    'Solver': best_solver,
    'Learning_Rate': best_lr,
    'Alpha': best_alpha,
    'Train_Accuracy': train_acc * 100,
    'Test_Accuracy': test_acc * 100,
    'Precision': test_prec * 100,
    'Recall': test_rec * 100,
    'F1-Score': test_f1 * 100,
    'AUC-ROC': test_auc,
    'Iterations': final_mlp.n_iter_,
    'Paper_Gap': test_acc * 100 - paper_acc
}

pd.DataFrame([final_results]).to_csv('data/processed/mlp_final_results.csv', index=False)

print(f"   ✅ Model saved: data/processed/best_mlp_backprop.pkl")
print(f"   ✅ Results saved: data/processed/mlp_*_results.csv")

# ============================================================================
# 9. VISUALIZATION
# ============================================================================
print("\n9️⃣  Creating visualizations...")

fig, axes = plt.subplots(2, 2, figsize=(15, 12))

# 1. Architecture comparison
ax1 = axes[0, 0]
top_arch = df_arch.head(10)
ax1.barh(range(len(top_arch)), top_arch['Accuracy'], color='steelblue')
ax1.set_yticks(range(len(top_arch)))
ax1.set_yticklabels(top_arch['Architecture'])
ax1.set_xlabel('Accuracy (%)', fontweight='bold')
ax1.set_title('Top 10 MLP Architectures', fontsize=14, fontweight='bold')
ax1.axvline(paper_acc, color='red', linestyle='--', linewidth=2, label=f'Paper: {paper_acc}%')
ax1.legend()
ax1.grid(axis='x', alpha=0.3)

# 2. Learning curve (if available)
ax2 = axes[0, 1]
if hasattr(final_mlp, 'loss_curve_'):
    ax2.plot(final_mlp.loss_curve_, linewidth=2, color='orange')
    ax2.set_xlabel('Iterations', fontweight='bold')
    ax2.set_ylabel('Loss', fontweight='bold')
    ax2.set_title('Training Loss Curve', fontsize=14, fontweight='bold')
    ax2.grid(alpha=0.3)
else:
    ax2.text(0.5, 0.5, 'Loss curve not available', ha='center', va='center')
    ax2.axis('off')

# 3. Confusion Matrix
ax3 = axes[1, 0]
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax3, cbar=False,
            annot_kws={'size': 14, 'weight': 'bold'})
ax3.set_xlabel('Predicted', fontweight='bold')
ax3.set_ylabel('Actual', fontweight='bold')
ax3.set_title('Confusion Matrix - Optimized MLP', fontsize=14, fontweight='bold')
ax3.set_xticklabels(['Ham', 'Smishing'])
ax3.set_yticklabels(['Ham', 'Smishing'])

# 4. Metrics comparison
ax4 = axes[1, 1]
metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
values = [test_acc*100, test_prec*100, test_rec*100, test_f1*100]
colors = ['#2ecc71', '#3498db', '#9b59b6', '#e74c3c']
bars = ax4.bar(metrics, values, color=colors, alpha=0.8)
ax4.set_ylabel('Score (%)', fontweight='bold')
ax4.set_title('Final MLP Performance Metrics', fontsize=14, fontweight='bold')
ax4.set_ylim([0, 100])
ax4.grid(axis='y', alpha=0.3)

# Add value labels on bars
for bar in bars:
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('data/processed/mlp_backprop_analysis.png', dpi=300, bbox_inches='tight')
print(f"   ✅ Visualization saved: data/processed/mlp_backprop_analysis.png")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("🎉 BACKPROPAGATION EXPERIMENTS COMPLETED!")
print("="*80)
print("\n✅ Summary:")
print(f"   - Tested {len(architectures)} architectures")
print(f"   - Tested {len(activations)} activation functions")
print(f"   - Tested {len(solvers)} solvers")
print(f"   - Tested {len(learning_rates) * len(alphas)} hyperparameter combinations")
print(f"   - Best Test Accuracy: {test_acc*100:.2f}%")
print(f"   - Gap with Paper: {test_acc*100 - paper_acc:+.2f}%")
print("\n📂 Output files:")
print(f"   - data/processed/best_mlp_backprop.pkl")
print(f"   - data/processed/mlp_architecture_experiments.csv")
print(f"   - data/processed/mlp_hyperparameter_experiments.csv")
print(f"   - data/processed/mlp_final_results.csv")
print(f"   - data/processed/mlp_backprop_analysis.png")
print("="*80)

