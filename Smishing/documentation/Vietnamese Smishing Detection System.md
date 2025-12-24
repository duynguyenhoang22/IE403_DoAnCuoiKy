# Project Documentation: Vietnamese Smishing Detection System

## 1. Project Overview

<p align='justify'>This project aims to detect fraudulent SMS messages (Smishing) targeting Vietnamese users. Unlike standard spam filters, this system utilizes a hybrid approach combining a Deep Linguistic Feature pipeline, an XGBoost Machine Learning model, and a real-time Domain Verification engine. It is designed to handle specific Vietnamese evasion techniques such as Teencode, Leet Speak (visual text obfuscation), and homoglyphs. </p>


**Key Capabilities**
- **Linguistic Analysis:** Deconstructs SMS text through 4 layers of processing to identify anomalies.

- **Hybrid Detection:** Combines AI probability scores with deterministic rules (Domain Checking, Keyword Safety Nets).

- **Real-time Domain Verification:** Actively validates URLs using Search Engines (DuckDuckGo) and Source Code analysis.

- **Obfuscation Resilience:** Detects and normalizes masked URLs (e.g., vcb . com . vn) and Leet speak (e.g., h0tro, b@nk).

## System Architecture

The system follows a linear pipeline for training and a branching logic for prediction.

**Directory Structure**
```
IE403_DoAnCuoiKy/
├── Smishing/                         # Main application code
│   ├── app_ui.py                       # Streamlit web interface
│   ├── data_loader.py                  # Robust CSV Loading
│   ├── domain_check.py                 # Domain Verification Engine
│   ├── features.py                     # Feature Extraction Orchestrator
│   ├── main_preprocessing.py           # Batch Data Processing
│   ├── model.py                        # XGBoost model training
│   ├── predict_system.py               # Inference & Hybrid Logic
│   ├── tune_params.py                  # Hyperparameter tuning for XGBoost model
│   ├── preprocessing/                  # Layer 1: Entity Extraction 
│   │   └── layer1_masking.py
│   ├── linguistic_features/            # Layers 2-4: Text analysis & Feature Engineering Logic
│   │   ├── layer2_normalization.py
│   │   ├── layer3_whitelist.py
│   │   ├── layer4_misspell.py
│   └── run_tests_25.py                 # Test cases
├── data/                             # Datasets and processed data
├── dicts/                            # Dictionaries for Vietnamese validation
├── tool_for_phone_sms_IE403/         # Data annotation tools for phone's sms
├── research_paper/                   # Academic documentation
└── requirements.ipynb                # Dependencies
```

## 3. The Feature Engineering Pipeline (27 Dimensions)
<p align='justify'>
The core innovation of this project is the 4-Layer Feature Extraction 
system managed by SmishingFeatureExtractor in features.py.
</p>

### Layer 1: Aggressive Masking & Entity Extraction

- **File:** preprocessing/layer1_masking.py

- **Function:** Identifies and masks entities using complex Regex, converting them into tokens (e.g., <URL>, <PHONE>) while counting their occurrences.

- **Key Features (12):**

    - **Platforms:** zalo_count, telegram_count, email_count.

    - **Phone Numbers:** Distinction between mobile_count, landline_count, hotline_count (1800/1900), and shortcode_count (e.g., 9029).

    - **Financial:** bank_acc_count (detects STK patterns), money_count, code_count (OTP/Service codes).

    - **Web:** url_count.

- **Highlight:** Uses "Protocol-Agnostic" and "Broken Shortener" patterns to catch obfuscated URLs like bi t . ly or vcb . com.

- **Notice:** Cannot catches heavily obfuscated URLs, which have patterns easily mistaked with normal content. 

### Layer 2: Normalization & Leet Speak Detection

- **File:** linguistic_features/layer2_normalization.py

- **Function:** Normalizes text for analysis and quantifies text obfuscation attempts.

- **Key Features (7):**

    - leet_count, teencode_count: Counts usage of teen slang (e.g., ko, ck).

    - visual_leet_count: Counts number-for-letter swaps (e.g., 0 -> o, 3 -> e).

    - symbol_leet_count: Counts symbol swaps (e.g., @ -> a, $ -> s).

    - weighted_leet_score: A severity score based on the type of obfuscation (Symbols are weighted higher than Teencode).

- **Mechanism:** Decodes the Leet speak back to standard Vietnamese to prepare for the next layer.


### Layer 3: Whitelist Filtering

- **File:** linguistic_features/layer3_whitelist.py

- **Function:** Filters out known legitimate tokens to prevent false positives in the misspelling check.

- **Key Feature (1):**

    - whitelist_count: Count of recognized tokens.

- Database: Includes legitimate Banks (VCB, ACB), Telcos (Viettel, Vina), and common tech jargon (OTP, App, Link).

### Layer 4: Misspell & Anomaly Detection

- **File:** linguistic_features/layer4_misspell.py

- **Function:** Analyzes the remaining tokens (after masking and whitelisting) for linguistic anomalies.

- **Key Features (7):**

    - oov_count, oov_density: Tokens not found in the Vietnamese dictionary.

    - gibberish_count: Random strings without vowels or pronounceable structure.

    - run_on_word_count: Words stuck together (e.g., vuilong instead of vui long).

    - broken_telex_count: Typing errors specific to Vietnamese input methods (Telex).

## 4. Domain Verification Engine

A standalone module used to verify the legitimacy of URLs found in the text.

- **File:** domain_check.py

- **Logic:** Uses a 3-tier algorithm:

    **1. Static Whitelist:** Immediate pass for known safe domains (vietcombank.com.vn, google.com).

    **2. Search Verification (DuckDuckGo):** Searches for {Brand Name} {Domain} official website. If the domain appears in the top results, it is marked Safe.

    **3. Source Code Analysis:** Crawls the target site to check if it contains internal links pointing back to verified/whitelisted domains.

- **Output:** risk_score (1.0 = Phishing, -1.0 = Legit, 0.0 = Unknown).

## 5. Machine Learning Model
- File: model.py

- Algorithm: XGBoost Classifier.

- Configuration:

    - Imbalance Handling: Uses scale_pos_weight to handle the disparity between Smishing and Clean samples.

    - Hyperparameters: Learning rate: 0.05, Max Depth: 4, Estimators: 200.

    - Threshold: Optimized at 0.46 based on F1-Score analysis.

- Features: Uses the 27 features extracted by SmishingFeatureExtractor + sender_type (encoded). Total ***28 features.***

## 6. Hybrid Prediction System (Inference)
<p align='jusitfy'>
The SmishingDetectionSystem class in predict_system.py orchestrates the final decision, acting as a "Safety Net" around the AI model. 
</p>

**Decision Logic Flow**

- **AI Scoring:** The XGBoost model calculates a probability (ai_prob).

- **Domain Check:** The DomainVerifier assigns a risk score to any URLs.

- **Context Analysis:**

    - **Conversation Guard:** Detects personal/conversational language (e.g., "tao", "may", "an com") to reduce false positives.

    - **Danger Guard:** Detects high-risk keywords ("vay", "chuyen khoan", "cong an") that override the Conversation Guard.

**Final Decision Rules**
| Priority | Condition | Decision | Phase | Confidence | Reasoning |
|----------|-----------|----------|--------|------------|----------|
| **1** | Domain Risk ≥ 0.8 | **SMISHING** | Domain Risk | 1.0 | Phát hiện liên kết độc hại hoặc bị làm nhiễu (ưu tiên cao nhất, override AI) |
| **2** | Domain Risk = -1.0 AND UGC Platform AND AI > 0.65 | **SMISHING** | Hybrid Warning | ai_prob | Tên miền sạch nhưng nội dung có dấu hiệu lừa đảo (Google Forms/Drive, etc.) |
| **2** | Domain Risk = -1.0 AND UGC Platform AND AI ≤ 0.65 | **SAFE** | Hybrid Safe | 0.2 | Tên miền dịch vụ lưu trữ/rút gọn uy tín |
| **2** | Domain Risk = -1.0 AND NOT UGC Platform | **SAFE** | Authority Whitelist | 0.0 | Tên miền chính chủ đã được xác thực |
| **3** | AI ≥ 0.46 AND Conversational AND NOT Dangerous | **SAFE** | Conversation Guard | 0.25 | AI nghi ngờ nhưng văn phong hội thoại cá nhân |
| **3** | AI ≥ 0.46 AND (NOT Conversational OR Dangerous) | **SMISHING** | AI Detection | ai_prob | AI phát hiện cấu trúc văn bản thường thấy trong tin nhắn rác/lừa đảo. |
| **3** | AI < 0.46 AND Has Danger Keywords AND Sender ≠ 'brandname' | **SMISHING** | Keyword Trigger | 0.6 | Nội dung chứa từ khóa rủi ro cao (tài chính/giả danh) cần xác minh |
| **3** | AI < 0.46 AND (No Danger Keywords OR Sender = 'brandname') | **SAFE** | AI Model | ai_prob | Không tìm thấy yếu tố rủi ro trong nội dung |


**Notes:**

**UGC Platform:** Cloud/Sharing platforms like Google (Drive/Docs/Sheets/Forms), Dropbox, Bit.ly, TinyURL, ZaloPay

**Conversational:** have keywords like: tao, may, ba, me, bo, anh, em, chi, minh, vo, chong, hoặc cụm: ăn cơm, đi chơi, etc.

**Danger Keywords:** finacial/job keywords like: vay, nợ xấu, lãi suất, chuyển khoản, công an, tòa án, việc nhẹ, tuyển dụng, etc.

**Threshold:** AI_prob threshold = 0.46, can be modify.

**Priority:**  1 = highest, 3 = lowest; top-down priority.

**Mechanism:** Domain Risk → Whitelist → AI + Safety Net, each stages can override decision of lower stages.

## 7. Usage Guide 

### A. Training the Model
To process the raw data and train the model:

1. Place your dataset in data/dataset.csv.

2. Run preprocessing to generate features for dataset:
```
    py main_preprocessing.py
```
3. Train the model, you can choose to train with XGBoost model by running only the *train_smishing_model* and comment out the *train_and_compare_models*;
or vice versa to train with XGBoost, Decision Tree, Random Forest and automatically save the best model based on F1-score.
```
    py model.py
```

### B. Making Predictions
The system provides multiple ways to make predictions on SMS messages for smishing detection:

**Web Interface (Recommended for End Users)**
The easiest way to use the system is through the Streamlit web application:
```
    cd Smishing
    py -m streamlit run app_ui.py
```
The web interface provides three modes:

**Manual Checking Mode:**

- Input SMS text and select sender type
- Choose between XGBoost or Random Forest model
- Adjust detection threshold (default: 0.46)
- Get detailed analysis with confidence scores and explanations

**Automated Test Cases Mode:**

- Runs 25 predefined test cases covering various smishing scenarios
- Includes legitimate messages, scams, and edge cases
- Displays results in a sortable table with color coding

**Model Comparison Mode:**
- Compare XGBoost and Random Forest models side-by-side
- Same input, different model outputs
- Analyze discrepancies and confidence differences

**Available Sender Types:**
- Unknown (Số lạ): Messages from unknown source
- Personal Number (Số cá nhân): Messages from personal numbers
- Brandname (Thương hiệu): Messages from verified business senders

## 8. Dependecies

**Python Version Requirements**
- Python 3.8+
- Recommend 3.13.5, we create the project on this Python version.

**One-line installation** 
```
    pip install -r requirements.txt
```