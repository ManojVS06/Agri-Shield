"""
Complete walkthrough script for Agricultural Subsidy Fraud Detection pipeline.

This script demonstrates the full workflow:
1. Generate synthetic data
2. Load data into PostgreSQL (optional)
3. Train XGBoost model
4. Make predictions
5. Generate fraud reports
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a shell command and report status."""
    print(f"\n{'='*70}")
    print(f"📌 STEP: {description}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, cwd=Path(__file__).parent)
        print(f"✅ SUCCESS: {description}\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {description}")
        print(f"Error: {e}\n")
        return False
    except FileNotFoundError:
        print(f"❌ FAILED: Command not found")
        print(f"Make sure all dependencies are installed: pip install -r requirements.txt\n")
        return False


def main():
    """Execute complete fraud detection pipeline."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║   Agricultural Subsidy Fraud Detection - Complete Pipeline     ║
║                                                                ║
║  This will walk through all steps from data generation to      ║
║  model training and fraud prediction.                          ║
╚════════════════════════════════════════════════════════════════╝
    """)

    python_exe = sys.executable
    src_dir = Path(__file__).parent / "src"

    steps = [
        (
            [python_exe, str(src_dir / "generate_synthetic_data.py"),
             "--rows", "5000", "--fraud-ratio", "0.15", "--seed", "42", "--output", "data"],
            "Generate synthetic fraud dataset (5000 transactions)",
        ),
        (
            [python_exe, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            "Install ML dependencies (xgboost, scikit-learn, matplotlib, seaborn)",
        ),
        (
            [python_exe, str(src_dir / "train_xgboost_model.py"),
             "--data-dir", "data", "--model-path", "models/fraud_detector.pkl",
             "--results-dir", "results", "--n-trials", "100", "--cv-folds", "5"],
            "Train XGBoost fraud detection model",
        ),
        (
            [python_exe, str(src_dir / "predict_fraud.py"),
             "--model-path", "models/fraud_detector.pkl", "--data-dir", "data",
             "--output-dir", "results"],
            "Run fraud predictions and generate reports",
        ),
    ]

    completed = 0
    failed = 0

    for cmd, description in steps:
        if run_command(cmd, description):
            completed += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'='*70}")
    print("📊 PIPELINE SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Completed: {completed}/{len(steps)}")
    print(f"❌ Failed: {failed}/{len(steps)}")

    if failed == 0:
        print(f"""
╔════════════════════════════════════════════════════════════════╗
║                    ✨ SUCCESS ✨                              ║
║                                                                ║
║  All pipeline steps completed successfully!                   ║
║                                                                ║
║  📁 Output Files:                                             ║
║    - data/ - Synthetic dataset (farmers, dealers, transactions)║
║    - models/fraud_detector.pkl - Trained XGBoost model        ║
║    - results/fraud_predictions.csv - All predictions          ║
║    - results/high_risk_transactions.csv - >70% fraud prob     ║
║    - results/dealer_fraud_summary.csv - Dealer analysis       ║
║    - results/*.png - Visualizations (confusion matrix, etc)   ║
║                                                                ║
║  🚀 Next Steps:                                               ║
║    1. Review results/fraud_predictions.csv for suspicious     ║
║       transactions                                            ║
║    2. Check results/dealer_fraud_summary.csv for dealers      ║
║       with high average fraud probability                     ║
║    3. Use models/fraud_detector.pkl for inference on new data ║
║    4. Retrain model monthly with updated data for drift       ║
║       detection                                               ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)
    else:
        print(f"""
╔════════════════════════════════════════════════════════════════╗
║                    ⚠️  SOME STEPS FAILED                       ║
║                                                                ║
║  Please check error messages above and ensure:                ║
║    1. All dependencies are installed:                         ║
║       pip install -r requirements.txt                         ║
║    2. PostgreSQL is running (if using database steps)         ║
║    3. All directories exist (data/, models/, results/)        ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
