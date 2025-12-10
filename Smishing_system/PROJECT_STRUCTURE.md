# 📁 Project Structure - Smishing Detection System

## 🎯 Tổng quan

Dự án được tổ chức theo **best practices** của Machine Learning projects với cấu trúc modular, scalable và dễ maintain.

---

## 📂 Cấu trúc thư mục

```
Smishing_system/
│
├── 📁 src/                          # SOURCE CODE CHÍNH
│   ├── preprocessing.py             # Tiền xử lý văn bản tiếng Việt
│   ├── features.py                  # Trích xuất 32 features
│   └── models.py                    # 🆕 Consolidated ML models
│
├── 📁 notebooks/                    # JUPYTER NOTEBOOKS
│   └── 01_feature_extraction.ipynb  # Feature extraction workflow
│
├── 📁 experiments/                  # TRAINING EXPERIMENTS
│   ├── train_models.py              # Train 4 models comparison
│   ├── backpropagation_experiments.py  # MLP architecture testing
│   └── train_best_mlp.py            # Final MLP training
│
├── 📁 data/                         # DATA & MODELS
│   ├── raw/
│   │   └── dataset.csv              # Original dataset (2,603 SMS)
│   ├── processed/
│   │   ├── features_full.csv        # All 32 features
│   │   ├── features_top5.csv        # Top 5 features
│   │   ├── best_model_rf.pkl        # Random Forest model
│   │   ├── best_mlp_final.pkl       # MLP model (93.28%)
│   │   ├── scaler.pkl               # Feature scaler
│   │   └── *.csv, *.png             # Results & visualizations
│   └── dicts/
│       ├── selected_tags_names.txt  # Accent restoration tags
│       └── vietnamese-stopwords-dash.txt
│
├── 📁 docs/                         # DOCUMENTATION
│   ├── README.md                    # Original detailed README
│   ├── FEATURES_SUMMARY.md          # 32 features explanation
│   ├── MODEL_RESULTS.md             # Detailed model comparison
│   └── TRAINING_SUMMARY.md          # Training process summary
│
├── 📁 tests/                        # UNIT TESTS
│   └── test_features.py             # Feature extraction tests
│
├── 📁 scripts/                      # UTILITY SCRIPTS
│   └── predict.py                   # Inference script
│
├── 📁 deployment/                   # DEPLOYMENT (Ready for Phase 3)
│   ├── api/                         # REST API
│   └── docker/                      # Docker container
│
├── 📄 README.md                     # 🆕 Main project documentation
├── 📄 requirements.txt              # Python dependencies
├── 📄 .gitignore                    # 🆕 Git ignore patterns
├── 📄 reorganize.py                 # Reorganization script
└── 📄 PROJECT_STRUCTURE.md          # This file
```

---

## 🔑 Key Components

### 1. **Source Code (`src/`)**

#### `preprocessing.py` (238 lines)
- Unicode normalization
- URL removal
- Structure normalization
- **Accent restoration** (XLM-RoBERTa model)
- Word tokenization (Underthesea)
- Noun extraction

#### `features.py` (438 lines)
- **32 features extraction**:
  - URL features (4)
  - Phone features (4)
  - Text features (9)
  - Keyword features (11)
  - Sender features (4)
- **Top 5 features selection**
- **90+ keywords dictionaries**

#### `models.py` (NEW - 70 lines)
- Consolidated ML models
- `load_data()` - Load preprocessed data
- `get_best_mlp()` - Best MLP config (20,10)
- `get_best_rf()` - Best RF config
- `train_best_model()` - Training function
- `load_model()` - Load trained model

---

### 2. **Experiments (`experiments/`)**

#### `train_models.py` (364 lines)
- Train 4 models: MLP, RF, SVM, LR
- Compare performance
- **Result: RF & MLP tied at 93%+**

#### `backpropagation_experiments.py` (478 lines)
- Test 13 architectures
- Test activation functions (relu, tanh, logistic)
- Test solvers (adam, sgd, lbfgs)
- Test learning rates & regularization
- **Result: (20,10) architecture = 93.28%**

#### `train_best_mlp.py` (351 lines)
- Final MLP training
- Cross-validation
- Detailed analysis
- Visualization

---

### 3. **Data (`data/`)**

#### Raw Data:
- `dataset.csv` - 2,603 SMS (89.1% Ham, 10.9% Smishing)

#### Processed:
- **Features**: `features_full.csv` (32), `features_top5.csv` (5)
- **Models**: `best_mlp_final.pkl`, `best_model_rf.pkl`
- **Results**: Various CSV files with metrics
- **Visualizations**: PNG charts

---

### 4. **Documentation (`docs/`)**

#### `FEATURES_SUMMARY.md`
- Explanation of 32 features
- Feature importance analysis
- Keywords dictionaries

#### `MODEL_RESULTS.md`
- Detailed comparison of 4 models
- Comparison with paper (97.93%)
- Next steps for improvement

#### `TRAINING_SUMMARY.md`
- Training timeline
- Best practices
- Usage examples

---

### 5. **Scripts (`scripts/`)**

#### `predict.py`
- **Inference script** for new SMS
- Usage:
```python
from scripts.predict import predict_sms

result = predict_sms("ACB: Tai khoan bi khoa...")
print(result)  # {'label': 'Smishing', 'confidence': 86.21%}
```

---

### 6. **Tests (`tests/`)**

#### `test_features.py`
- Unit tests for feature extraction
- Test cases: Smishing & Ham samples
- **Result: ALL TESTS PASSED** ✅

---

### 7. **Deployment (`deployment/`)**

**Status**: 🚧 Ready for Phase 3

#### Planned:
- **API** (`deployment/api/app.py`):
  - Flask/FastAPI REST API
  - Endpoint: `/predict`
  - Input: SMS text
  - Output: Prediction + confidence

- **Docker** (`deployment/docker/Dockerfile`):
  - Containerized application
  - Easy deployment

---

## 📊 Project Status

### ✅ **Completed (Phase 1 & 2)**:

1. ✔️ **Feature Extraction** (32 features)
2. ✔️ **Model Training** (4 models)
3. ✔️ **Best Model**: MLP (20,10) - **93.28% accuracy**
4. ✔️ **Documentation** (Complete)
5. ✔️ **Project Structure** (Professional)

### 🚧 **In Progress (Phase 3)**:

1. ⏳ Domain Checking Phase
2. ⏳ Handle Imbalanced Data (SMOTE)
3. ⏳ Hyperparameter Tuning

### 📍 **Future (Phase 4)**:

1. 🎯 REST API Deployment
2. 🎯 Docker Container
3. 🎯 Web Interface
4. 🎯 Mobile Integration

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd Smishing_system
pip install -r requirements.txt
```

### 2. Feature Extraction

```bash
jupyter notebook notebooks/01_feature_extraction.ipynb
```

### 3. Train Model

```bash
python experiments/train_models.py
```

### 4. Make Predictions

```python
from scripts.predict import predict_sms

message = "Ngan hang ACB thong bao..."
result = predict_sms(message)
print(f"{result['label']}: {result['confidence']:.2f}%")
```

---

## 📈 Performance Metrics

| Model | Accuracy | Precision | Recall | F1-Score |
|-------|----------|-----------|--------|----------|
| **MLP (20,10)** | **93.28%** | 86.67% | 45.61% | 59.77% |
| Random Forest | 93.09% | 86.21% | 43.86% | 58.14% |
| SVM | 93.09% | 86.21% | 43.86% | 58.14% |
| Logistic Reg | 93.09% | 92.00% | 40.35% | 56.10% |

**Paper Benchmark**: 97.93% | **Gap**: -4.65%

---

## 🎯 Next Steps

1. **Implement Domain Checking**:
   - URL legitimacy checking
   - WHOIS lookup
   - Blacklist checking
   - Expected: +2-3% accuracy

2. **Handle Imbalanced Data**:
   - SMOTE or class weights
   - Expected: +5-10% recall

3. **Deploy API**:
   - Create REST API
   - Docker containerization

---

## 👥 Team

**IE403 Final Project**  
Course: Machine Learning  
University: UIT

---

## 📚 References

- Paper: DSmishSMS (Mishra & Soni, 2021)
- Accuracy: 97.93% (English dataset)
- Our result: 93.28% (Vietnamese dataset)

---

**Last Updated**: December 9, 2025  
**Status**: Phase 2 Completed ✅  
**Best Model**: MLP Backpropagation (93.28%)


