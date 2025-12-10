"""
Prediction script for SMS classification
"""

import sys
sys.path.append('..')

from src.models import load_model
from src.features import extract_all_features
import pandas as pd


def predict_sms(message, sender_type='unknown'):
    """
    Predict if SMS is Smishing or Ham
    
    Args:
        message: SMS content
        sender_type: 'brandname', 'shortcode', 'personal_number', 'unknown'
    
    Returns:
        dict with prediction and confidence
    """
    # Load model
    model, scaler = load_model()
    
    # Extract features
    features = extract_all_features(message, sender_type)
    
    # Select top 5 features
    top_5 = ['has_url', 'has_phone', 'num_financial_keywords', 
             'num_urgency_keywords', 'is_personal_number']
    X = pd.DataFrame([features])[top_5]
    
    # Scale if needed
    if scaler:
        X = scaler.transform(X)
    
    # Predict
    prediction = model.predict(X)[0]
    probability = model.predict_proba(X)[0]
    
    return {
        'label': 'Smishing' if prediction == 1 else 'Ham',
        'confidence': probability[prediction] * 100,
        'prediction': int(prediction),
        'probabilities': {
            'Ham': probability[0] * 100,
            'Smishing': probability[1] * 100
        }
    }


if __name__ == "__main__":
    # Test examples
    test_messages = [
        ("ACB: Tai khoan bi khoa. Truy cap http://fake.com", "brandname"),
        ("Viettel thong bao so du 50.000d", "shortcode"),
    ]
    
    print("🔍 Testing Predictions...")
    print("="*80)
    
    for msg, sender in test_messages:
        result = predict_sms(msg, sender)
        print(f"\nMessage: {msg[:60]}...")
        print(f"Prediction: {result['label']} ({result['confidence']:.2f}%)")
        print("-"*80)
