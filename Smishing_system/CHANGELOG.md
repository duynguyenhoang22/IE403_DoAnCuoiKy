# 📝 Changelog

All notable changes to Smishing Detection System.

---

## [Unreleased] - Phase 3

### Planned
- Domain Checking Phase implementation
- SMOTE for imbalanced data handling
- REST API deployment
- Docker containerization
- Web interface

---

## [1.0.0] - 2025-12-09 - MAJOR REORGANIZATION ✨

### 🎯 Major Changes

#### **Project Restructure**
- ✅ Reorganized entire project with professional structure
- ✅ Separated concerns: `src/`, `docs/`, `experiments/`, `scripts/`
- ✅ Created deployment-ready structure

#### **New Files**
- ✅ `src/models.py` - Consolidated ML models module
- ✅ `scripts/predict.py` - Inference script
- ✅ `README.md` - New main documentation
- ✅ `.gitignore` - Git ignore patterns
- ✅ `PROJECT_STRUCTURE.md` - Project structure guide
- ✅ `docs/API_USAGE.md` - API documentation
- ✅ `CHANGELOG.md` - This file

#### **Moved Files**
- ✅ `main.ipynb` → `notebooks/01_feature_extraction.ipynb`
- ✅ All `.md` files → `docs/`
- ✅ Training scripts → `experiments/`
- ✅ `test_features.py` → `tests/`

#### **Deleted Files**
- ❌ `fix_features.py` - Temporary utility
- ❌ `__pycache__/` - Python cache

---

## [0.9.0] - 2025-12-09 - MLP OPTIMIZATION 🧠

### Added
- ✅ **Backpropagation experiments** script
  - Tested 13 architectures
  - Tested 3 activation functions
  - Tested 3 solvers
  - Tested 16 learning rate & regularization combinations

### Results
- 🏆 **Best Architecture Found**: (20, 10)
- 🏆 **Best Activation**: relu
- 🏆 **Best Solver**: adam
- 🏆 **Best Accuracy**: **93.28%** (vs paper 97.93%)

### Improved
- MLP model: 88.68% → **93.28%** (+4.6% improvement!)
- Now **BEST MODEL OVERALL** (beats RF, SVM, LR)

---

## [0.8.0] - 2025-12-09 - MODEL TRAINING 🤖

### Added
- ✅ **4 ML Models trained**:
  1. MLP (Backpropagation)
  2. Random Forest
  3. SVM
  4. Logistic Regression

### Results
- Random Forest: 93.09% accuracy
- SVM: 93.09% accuracy
- Logistic Regression: 93.09% accuracy
- MLP (baseline): 88.68% accuracy

### Analysis
- Feature importance analysis (Random Forest)
- **Top feature**: `is_personal_number` (63.44%)
- Comparison with paper (97.93%)
- Gap: -4.84%

### Files Created
- `train_models.py` - Training script
- `model_results.csv` - Results table
- `model_comparison.png` - Visualizations
- `MODEL_RESULTS.md` - Detailed analysis
- `TRAINING_SUMMARY.md` - Summary

---

## [0.7.0] - 2025-12-09 - FEATURE EXTRACTION ⚙️

### Added
- ✅ **32 features extracted** from SMS:
  - URL features (4)
  - Phone features (4)
  - Text features (9)
  - Keyword features (11)
  - Sender features (4)

- ✅ **Top 5 features selected**:
  1. `has_url`
  2. `has_phone`
  3. `num_financial_keywords`
  4. `num_urgency_keywords`
  5. `is_personal_number`

### Implementation
- `src/features.py` (438 lines)
- **90+ keywords** in 5 categories:
  - Financial (20)
  - Urgency (15)
  - Action (20)
  - Reward (15)
  - Impersonation (20)

### Files Created
- `main.ipynb` - Feature extraction notebook
- `features_full.csv` - All 32 features
- `features_top5.csv` - Top 5 features
- `FEATURES_SUMMARY.md` - Documentation

---

## [0.6.0] - 2025-12-09 - PREPROCESSING 🔧

### Added
- ✅ **Vietnamese text preprocessing**:
  - Unicode normalization (NFC)
  - URL removal (iocextract + regex)
  - Structure normalization
  - **Accent restoration** (XLM-RoBERTa)
  - Word tokenization (Underthesea)
  - POS tagging
  - Noun extraction

### Implementation
- `src/preprocessing.py` (238 lines)
- Model: `peterhung/vietnamese-accent-marker-xlm-roberta`
- **528 accent tags** loaded

### Tests
- `test_features.py` created
- All tests passed ✅

---

## [0.5.0] - 2025-12-08 - DATASET PREPARATION 📊

### Added
- ✅ **Dataset**: 2,603 Vietnamese SMS messages
  - Ham: 2,319 (89.1%)
  - Smishing: 284 (10.9%)

### Features (from annotation)
- `content` - SMS text
- `label` - 0 (Ham) / 1 (Smishing)
- `has_url` - URL presence
- `has_phone_number` - Phone number presence
- `sender_type` - brandname/shortcode/personal_number

### Files
- `data/raw/dataset.csv`
- `data/dicts/vietnamese-stopwords-dash.txt`
- `data/dicts/selected_tags_names.txt`

---

## [0.1.0] - 2025-12-01 - PROJECT INITIALIZATION 🎬

### Added
- Initial project structure
- `requirements.txt` with dependencies
- Research paper review: DSmishSMS
- Target: 97.93% accuracy (paper benchmark)

### Dependencies
- pandas, numpy
- pyvi (accent restoration)
- underthesea (Vietnamese NLP)
- regex, unicodedata
- iocextract (URL extraction)
- scikit-learn (ML models)
- matplotlib, seaborn (visualization)

---

## 📊 Performance Timeline

```
v0.1.0: Project start          → Target: 97.93%
v0.5.0: Dataset ready          → 2,603 SMS
v0.6.0: Preprocessing done     → Vietnamese support
v0.7.0: Features extracted     → 32 features
v0.8.0: Models trained         → RF: 93.09%
v0.9.0: MLP optimized          → MLP: 93.28% 🏆
v1.0.0: Project reorganized    → Professional structure
```

---

## 🎯 Milestones

- ✅ **Phase 1**: Feature Extraction (COMPLETED)
- ✅ **Phase 2**: Model Training (COMPLETED)
- 🚧 **Phase 3**: Domain Checking (IN PROGRESS)
- 📍 **Phase 4**: Deployment (PLANNED)

---

## 📈 Metrics Progress

| Version | Best Model | Accuracy | Gap to Paper |
|---------|------------|----------|--------------|
| v0.8.0 | Random Forest | 93.09% | -4.84% |
| v0.9.0 | **MLP (20,10)** | **93.28%** | **-4.65%** ✨ |
| Target | - | 97.93% | 0% |

---

## 🙏 Acknowledgments

- **Paper**: DSmishSMS (Mishra & Soni, 2021)
- **Course**: IE403 - Machine Learning - UIT
- **Libraries**: scikit-learn, Underthesea, PyVi, iocextract

---

**Current Version**: 1.0.0  
**Last Updated**: December 9, 2025  
**Status**: Phase 2 Completed ✅

