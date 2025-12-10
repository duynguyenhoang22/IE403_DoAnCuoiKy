# 🚀 Smishing Detection System

Hệ thống phát hiện tin nhắn SMS lừa đảo (Smishing) cho tiếng Việt.

## 📊 Quick Results

| Model | Accuracy | Precision | Recall | F1-Score |
|-------|----------|-----------|--------|----------|
| **MLP (20,10)** | **93.28%** | 86.67% | 45.61% | 59.77% |
| Random Forest | 93.09% | 86.21% | 43.86% | 58.14% |
| SVM | 93.09% | 86.21% | 43.86% | 58.14% |
| Logistic Reg | 93.09% | 92.00% | 40.35% | 56.10% |

**Paper Benchmark**: 97.93% (Gap: -4.65%)

## 📁 Project Structure

```
Smishing_system/
├── src/              # Source code
├── notebooks/        # Jupyter notebooks
├── experiments/      # Training experiments
├── data/            # Datasets & models
├── docs/            # Documentation
├── tests/           # Unit tests
├── scripts/         # Utility scripts
└── deployment/      # API & Docker
```

## 🚀 Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Feature Extraction

```bash
jupyter notebook notebooks/01_feature_extraction.ipynb
```

### 3. Model Training

```python
from src.models import train_best_model

model, results = train_best_model()
print(f"Accuracy: {results['accuracy']:.2f}%")
```

### 4. Prediction

```python
from scripts.predict import predict_sms

message = "ACB: Tai khoan da bi khoa. Truy cap http://fake.com"
result = predict_sms(message)

print(f"Prediction: {result['label']}")  # Smishing/Ham
print(f"Confidence: {result['confidence']:.2f}%")
```

## 📚 Documentation

- [Feature Summary](docs/FEATURES_SUMMARY.md) - 32 features extracted
- [Model Results](docs/MODEL_RESULTS.md) - Detailed comparison
- [Training Summary](docs/TRAINING_SUMMARY.md) - Training process
- [API Usage](docs/API_USAGE.md) - How to use the API

## 🏗️ Architecture

### Phase 1: Feature Extraction ✅
- 32 features from SMS content
- Top 5 features: `has_url`, `has_phone`, `num_financial_keywords`, `num_urgency_keywords`, `is_personal_number`

### Phase 2: Model Training ✅
- 4 models: MLP, Random Forest, SVM, Logistic Regression
- Best: MLP with (20,10) architecture
- 93.28% accuracy

### Phase 3: Domain Checking 🚧
- URL legitimacy checking
- WHOIS lookup
- Blacklist checking

### Phase 4: Deployment 📍
- REST API
- Docker container
- Web interface

## 📊 Dataset

- **Total**: 2,603 SMS messages
- **Ham**: 2,319 (89.1%)
- **Smishing**: 284 (10.9%)
- **Language**: Vietnamese

## 🎯 Next Steps

1. ⏳ Implement Domain Checking Phase
2. 🎯 Handle imbalanced data (SMOTE)
3. ⚙️ Hyperparameter tuning
4. 🚀 Deploy API

## 📖 References

- Paper: DSmishSMS (Mishra & Soni, 2021)
- Course: IE403 - Machine Learning - UIT

## 👥 Contributors

IE403 Final Project Team

---

**Status**: Phase 2 Completed ✅ | Accuracy: 93.28%
