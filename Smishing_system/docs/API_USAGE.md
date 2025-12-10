# 🔌 API Usage Guide

## 📋 Overview

REST API cho Smishing Detection System. Cho phép detect tin nhắn Smishing real-time qua HTTP requests.

**Status**: 🚧 Under Development (Phase 3)

---

## 🚀 Quick Start

### 1. Start API Server (Coming Soon)

```bash
cd deployment/api
python app.py
```

Server will run on: `http://localhost:5000`

---

## 📡 API Endpoints

### **POST `/predict`**

Detect if SMS is Smishing or Ham

#### Request

```http
POST /predict HTTP/1.1
Content-Type: application/json

{
  "message": "ACB: Tai khoan bi khoa. Truy cap http://fake.com",
  "sender_type": "brandname"
}
```

#### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | SMS content |
| `sender_type` | string | ❌ No | `brandname`, `shortcode`, `personal_number`, `unknown` (default) |

#### Response (Success)

```json
{
  "success": true,
  "prediction": {
    "label": "Smishing",
    "confidence": 86.21,
    "prediction": 1
  },
  "probabilities": {
    "Ham": 13.79,
    "Smishing": 86.21
  },
  "features": {
    "has_url": 1,
    "has_phone": 0,
    "num_financial_keywords": 3,
    "num_urgency_keywords": 2,
    "is_personal_number": 0
  },
  "model": "MLP_Backpropagation",
  "version": "1.0.0",
  "timestamp": "2025-12-09T18:30:00Z"
}
```

#### Response (Error)

```json
{
  "success": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Message cannot be empty"
  }
}
```

---

### **GET `/health`**

Check API health status

#### Response

```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "1.0.0",
  "uptime": 3600
}
```

---

### **GET `/stats`**

Get model statistics

#### Response

```json
{
  "model": "MLP_Backpropagation",
  "architecture": "(20, 10)",
  "accuracy": 93.28,
  "precision": 86.67,
  "recall": 45.61,
  "f1_score": 59.77,
  "total_predictions": 1250,
  "last_updated": "2025-12-09T12:00:00Z"
}
```

---

## 💻 Python Client Example

### Install

```bash
pip install requests
```

### Usage

```python
import requests

API_URL = "http://localhost:5000"

def predict_sms(message, sender_type="unknown"):
    """
    Predict if SMS is Smishing
    
    Args:
        message: SMS content
        sender_type: Type of sender
    
    Returns:
        Prediction result dict
    """
    response = requests.post(
        f"{API_URL}/predict",
        json={
            "message": message,
            "sender_type": sender_type
        },
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.text}")

# Example
result = predict_sms(
    "ACB: Tai khoan bi khoa. Truy cap http://fake.com",
    "brandname"
)

print(f"Prediction: {result['prediction']['label']}")
print(f"Confidence: {result['prediction']['confidence']:.2f}%")

if result['prediction']['label'] == 'Smishing':
    print("⚠️  WARNING: This appears to be a Smishing attempt!")
```

---

## 🔧 cURL Examples

### Basic Prediction

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Viettel thong bao so du 50.000d",
    "sender_type": "shortcode"
  }'
```

### Health Check

```bash
curl http://localhost:5000/health
```

---

## 🐳 Docker Deployment

### Build Image

```bash
cd deployment/docker
docker build -t smishing-detector:latest .
```

### Run Container

```bash
docker run -d -p 5000:5000 \
  --name smishing-api \
  smishing-detector:latest
```

### Test

```bash
curl http://localhost:5000/health
```

---

## 📊 Rate Limits

| Tier | Requests/Hour | Requests/Day |
|------|---------------|--------------|
| Free | 100 | 1,000 |
| Basic | 1,000 | 10,000 |
| Pro | 10,000 | 100,000 |

---

## ⚠️ Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Invalid request parameters |
| `MODEL_ERROR` | 500 | Model prediction failed |
| `RATE_LIMIT` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

---

## 🔐 Authentication (Future)

### API Key

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"message": "..."}'
```

---

## 📈 Monitoring

### Prometheus Metrics

Endpoint: `/metrics`

Metrics:
- `smishing_predictions_total`
- `smishing_prediction_duration_seconds`
- `smishing_model_accuracy`

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/test_api.py
```

### Integration Tests

```bash
pytest tests/test_api_integration.py
```

### Load Testing

```bash
locust -f tests/load_test.py
```

---

## 📚 Additional Resources

- [Deployment Guide](../deployment/README.md)
- [Model Documentation](MODEL_RESULTS.md)
- [Feature Documentation](FEATURES_SUMMARY.md)

---

## 🤝 Support

**Issues**: Report bugs on GitHub Issues  
**Email**: support@smishing-detector.com  
**Docs**: https://docs.smishing-detector.com

---

**Status**: 🚧 API under development  
**Expected Release**: Phase 3  
**Version**: 1.0.0-alpha


