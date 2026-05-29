"""Inference pipeline for fraud predictions using trained XGBoost model bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Allow importing engineer_features from the same src/ directory
sys.path.insert(0, str(Path(__file__).parent))
from train_xgboost_model import engineer_features  # noqa: E402

import pickle


def predict_batch(model_path: Path, data_dir: Path) -> pd.DataFrame:
    """Predict fraud on entire transaction dataset using the trained model bundle."""
    print(f"[INFO] Loading model from: {model_path}")

    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    model           = bundle["model"]
    feature_columns = bundle["feature_columns"]
    best_threshold  = bundle.get("best_threshold", 0.5)

    print(f"[INFO] Loading transaction data from: {data_dir}")
    df = pd.read_csv(data_dir / "transactions.csv")
    print(f"[INFO] Preparing features for {len(df)} records...")

    X, y, _, _ = engineer_features(df.copy())

    # Align columns to what the model expects
    for col in feature_columns:
        if col not in X.columns:
            X[col] = 0.0
    X = X[feature_columns].fillna(0)

    print("[INFO] Making predictions...")
    proba      = model.predict_proba(X)[:, 1]
    predictions = (proba >= best_threshold).astype(int)

    results_df = pd.DataFrame({
        "txn_id":                 df["txn_id"],
        "farmer_id":              df["farmer_id"],
        "dealer_id":              df["dealer_id"],
        "actual_label":           df["is_fraud"],
        "predicted_fraud":        predictions,
        "fraud_probability":      np.round(proba, 4),
        "subsidy_amount":         df["subsidy_amount"],
        "quantity":               df["quantity"],
        "distance_farmer_dealer": df["distance_farmer_dealer"],
        "district":               df.get("district", ""),
        "fraud_type":             df.get("fraud_type", "None"),
    })

    results_df["risk_level"] = pd.cut(
        results_df["fraud_probability"],
        bins=[-0.001, 0.35, 0.60, 1.001],
        labels=["Low", "Medium", "High"]
    ).astype(str)

    results_df = results_df.sort_values("fraud_probability", ascending=False)
    return results_df


def generate_fraud_report(results_df: pd.DataFrame, output_dir: Path | None = None) -> None:
    """Generate fraud detection report and save CSV outputs."""
    if output_dir is None:
        output_dir = Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)

    total          = len(results_df)
    predicted_fraud= (results_df["predicted_fraud"] == 1).sum()
    actual_fraud   = (results_df["actual_label"] == 1).sum()

    print("\n[REPORT] Fraud Detection Summary")
    print("=" * 60)
    print(f"Total Transactions Analyzed  : {total}")
    print(f"Predicted as Fraud           : {predicted_fraud} ({predicted_fraud/total*100:.2f}%)")
    print(f"Ground Truth Fraud           : {actual_fraud} ({actual_fraud/total*100:.2f}%)")

    high_risk = results_df[results_df["fraud_probability"] > 0.7]
    print(f"\n[ALERT] High-Risk Transactions (>70% probability): {len(high_risk)}")

    print("\n[DIST] Fraud Probability Distribution:")
    for thr in [0.9, 0.7, 0.5]:
        cnt = len(results_df[results_df["fraud_probability"] > thr])
        print(f"  >{int(thr*100)}% confidence: {cnt}")
    print(f"  <=50% confidence: {len(results_df[results_df['fraud_probability'] <= 0.5])}")

    dealer_risk = (
        results_df.groupby("dealer_id")
        .agg({
            "fraud_probability": ["mean", "max", "count"],
            "predicted_fraud":   "sum",
        })
        .round(4)
    )
    dealer_risk.columns = ["avg_fraud_prob", "max_fraud_prob", "total_txns", "fraud_count"]
    dealer_risk = dealer_risk.sort_values("avg_fraud_prob", ascending=False)

    print("\n[TOP10] Top 10 Dealers by Avg Fraud Probability:")
    print(dealer_risk.head(10).to_string())

    # Save outputs
    report_path     = output_dir / "fraud_predictions.csv"
    high_risk_path  = output_dir / "high_risk_transactions.csv"
    dealer_path     = output_dir / "dealer_fraud_summary.csv"

    results_df.to_csv(report_path, index=False)
    high_risk.to_csv(high_risk_path, index=False)
    dealer_risk.to_csv(dealer_path)

    print(f"\n[SAVE] Detailed predictions  -> {report_path}")
    print(f"[SAVE] High-risk transactions -> {high_risk_path}")
    print(f"[SAVE] Dealer summary         -> {dealer_path}")
    print("\n[DONE] Prediction pipeline complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Run fraud predictions on agricultural subsidy transactions."
    )
    parser.add_argument("--model-path",  type=Path, default=Path("models/fraud_detector.pkl"))
    parser.add_argument("--data-dir",    type=Path, default=Path("data"))
    parser.add_argument("--output-dir",  type=Path, default=Path("results"))
    args = parser.parse_args()

    if not args.model_path.exists():
        print(f"[ERROR] Model not found at: {args.model_path}")
        print("        Train the model first: python src/train_xgboost_model.py")
        return

    results_df = predict_batch(args.model_path, args.data_dir)
    generate_fraud_report(results_df, args.output_dir)


if __name__ == "__main__":
    main()
