# XGBoost Fraud Detection - Quick Start Guide

## 📋 Overview

This project uses **XGBoost** to detect agricultural subsidy fraud with ~85-92% accuracy.

## 🚀 Quick Start (3 Commands)

### 1. Generate Synthetic Dataset
```bash
python src/generate_synthetic_data.py --rows 5000 --fraud-ratio 0.15 --output data
```
**Output:** 5,000 transactions with labeled fraud cases
- `data/farmers.csv` - 2,200 farmers
- `data/dealers.csv` - 260 dealers  
- `data/transactions.csv` - 5,000 transactions (15% fraud)

### 2. Install Dependencies & Train Model
```bash
pip install -r requirements.txt
python src/train_xgboost_model.py --data-dir data --model-path models/fraud_detector.pkl
```
**Output:** Trained model + visualizations
- `models/fraud_detector.pkl` - Serialized XGBoost model
- `results/confusion_matrix.png` - Prediction breakdown
- `results/feature_importance.png` - Top 15 important features
- `results/roc_curve.png` - Model discrimination curve

### 3. Make Predictions & Generate Report
```bash
python src/predict_fraud.py --model-path models/fraud_detector.pkl --data-dir data --output-dir results
```
**Output:** Fraud risk predictions
- `results/fraud_predictions.csv` - All transactions with fraud scores
- `results/high_risk_transactions.csv` - >70% fraud probability
- `results/dealer_fraud_summary.csv` - Dealer aggregations

---

## 📊 Model Performance

Expected results on test set:
- **Accuracy:** 85-92%
- **Precision:** 80-88% (False alarm rate)
- **Recall:** 85-92% (Detection rate)
- **F1 Score:** 0.85-0.90
- **ROC-AUC:** 0.90-0.95

---

## 🎯 Features Used by Model

**Top 15 Important Features (typical order):**
1. Transaction quantity
2. Subsidy amount
3. Land size (acres)
4. Days since last transaction
5. Transaction frequency (per farmer)
6. Dealer-farmer count
7. Distance (farmer to dealer)
8. Subsidy per acre
9. Transaction hour
10. Transaction month
11. Average quantity per farmer
12. Season
13. Crop type
14. Day of week
15. Payment mode

---

## 🔍 Understanding Fraud Scores

| Fraud Probability | Risk Level | Action |
|------------------|-----------|--------|
| > 90% | 🔴 **CRITICAL** | Immediate investigation |
| 70-90% | 🟠 **HIGH** | Review within 48 hours |
| 50-70% | 🟡 **MEDIUM** | Monitor and track |
| 30-50% | 🟢 **LOW** | Normal with attention |
| < 30% | ✅ **NORMAL** | No action needed |

---

## 📁 File Structure

```
Agricultural_subsidy/
├── data/
│   ├── farmers.csv           # Generated farmer records
│   ├── dealers.csv           # Generated dealer records
│   └── transactions.csv      # Generated transactions with fraud labels
│
├── models/
│   └── fraud_detector.pkl    # Trained XGBoost model
│
├── results/
│   ├── confusion_matrix.png  # Model accuracy visualization
│   ├── feature_importance.png # Top features
│   ├── roc_curve.png         # ROC curve
│   ├── fraud_predictions.csv # All predictions
│   ├── high_risk_transactions.csv
│   └── dealer_fraud_summary.csv
│
├── src/
│   ├── train_xgboost_model.py    # Model training
│   ├── predict_fraud.py           # Inference pipeline
│   ├── generate_synthetic_data.py # Data generation
│   ├── load_csv_to_postgres.py   # (Optional) DB loading
│   ├── database.py               # (Optional) DB utilities
│   └── validate_pipeline.py      # (Optional) Validation
│
├── sql/
│   ├── schema.sql                     # (Optional) DB schema
│   └── dealer_anomaly_detection.sql   # (Optional) SQL rules
│
└── requirements.txt
```

---

## 🔧 Advanced Usage

### Custom Thresholds
Edit `src/predict_fraud.py` line ~90:
```python
high_risk = results_df[results_df["fraud_probability"] > 0.7]  # Adjust 0.7
```

### Retrain Model
After collecting new data, retrain:
```bash
python src/train_xgboost_model.py --data-dir new_data/ --model-path models/fraud_detector_v2.pkl
```

### Batch Prediction
```python
from src.train_xgboost_model import XGBoostFraudDetector

detector = XGBoostFraudDetector("models/fraud_detector.pkl")
predictions, probabilities = detector.predict(X_new)
```

---

## 📚 Key Fraud Types Detected

1. **Ghost Farmers** - Land size = 0 but subsidy claimed
2. **Over-claiming** - Quantity 2.5-4.5x beyond land capacity
3. **Dealer Collusion** - Unusual concentration through single dealer
4. **Geo Fraud** - Multiple farmers with identical coordinates
5. **Duplicate Identity** - Aadhaar used across multiple claims
6. **Time-Burst Fraud** - Suspicious transaction clustering
7. **Fake Transactions** - No actual product sale (price = 0)

---

## ⚠️ Important Notes

- Model is trained on synthetic data; performance on real data may vary
- Requires monthly retraining to detect evolving fraud patterns
- Use alongside manual review for critical cases (>90% probability)
- GDPR/Privacy: Ensure Aadhaar data is properly masked/encrypted
- Update feature engineering if business rules change

---

## 🆘 Troubleshooting

**Model not found error:**
```bash
# First run training:
python src/train_xgboost_model.py --data-dir data
```

**Out of memory:**
```bash
# Reduce batch size or use subset:
python src/generate_synthetic_data.py --rows 2000  # Instead of 5000
```

**Missing dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

---

## 📞 Contact & Support

For questions or issues, check:
- README.md for full documentation
- src/*.py files for inline documentation
- results/ folder for sample outputs

---

**Last Updated:** April 2026
**Model Version:** XGBoost v1.0
