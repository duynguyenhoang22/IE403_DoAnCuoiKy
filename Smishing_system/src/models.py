"""
Consolidated models module
Chứa tất cả ML models và training functions
"""

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def load_data(features_path='data/processed/features_top5.csv'):
    """Load preprocessed features"""
    df = pd.read_csv(features_path)
    X = df.drop('label', axis=1)
    y = df['label']
    return X, y


def train_test_split_data(X, y, test_size=0.2, random_state=42):
    """Split data with stratification"""
    return train_test_split(X, y, test_size=test_size, 
                           random_state=random_state, stratify=y)


def get_best_mlp():
    """Get best MLP configuration"""
    return MLPClassifier(
        hidden_layer_sizes=(20, 10),
        activation='relu',
        solver='adam',
        max_iter=2000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1
    )


def get_best_rf():
    """Get best Random Forest configuration"""
    return RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )


def train_best_model(model_type='mlp'):
    """
    Train best model
    
    Args:
        model_type: 'mlp' or 'rf'
    
    Returns:
        model, results dict
    """
    X, y = load_data()
    X_train, X_test, y_train, y_test = train_test_split_data(X, y)
    
    # Scale for MLP
    if model_type == 'mlp':
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        model = get_best_mlp()
    else:
        model = get_best_rf()
        scaler = None
    
    # Train
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    results = {
        'accuracy': accuracy_score(y_test, y_pred) * 100,
        'precision': precision_score(y_test, y_pred) * 100,
        'recall': recall_score(y_test, y_pred) * 100,
        'f1_score': f1_score(y_test, y_pred) * 100
    }
    
    return model, scaler, results


def load_model(model_path='data/processed/best_mlp_final.pkl',
               scaler_path='data/processed/mlp_scaler.pkl'):
    """Load trained model and scaler"""
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path) if scaler_path else None
    return model, scaler
