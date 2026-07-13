"""ML model service — loads XGBoost model and runs inference + SHAP explanations."""
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Allow importing engineer_features from src/
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.append(str(SRC_DIR))
from features import engineer_features  # noqa: E402


class MLService:
    """Singleton ML service wrapping the trained XGBoost model."""

    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_columns = []
        self.best_threshold = 0.5
        self.metrics = {}
        self._loaded = False

    def load(self, model_path: Path) -> bool:
        try:
            with open(model_path, "rb") as f:
                bundle = pickle.load(f)
            self.model           = bundle["model"]
            self.label_encoders  = bundle.get("label_encoders", {})
            self.feature_columns = bundle.get("feature_columns", [])
            self.best_threshold  = bundle.get("best_threshold", 0.5)
            self.metrics         = bundle.get("metrics", {})
            self._loaded = True
            print(f"[ML] Model loaded. Features: {len(self.feature_columns)} | "
                  f"AUC: {self.metrics.get('roc_auc','N/A')}")
            return True
        except Exception as e:
            print(f"[ML] WARNING: Could not load model: {e}")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict_transactions(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Run batch inference on raw transaction rows. Returns df with fraud_probability column."""
        if not self._loaded:
            df_raw["fraud_probability"] = 0.5
            df_raw["risk_level"]        = "Unknown"
            return df_raw

        X, _, _, _ = engineer_features(df_raw.copy())
        # Align columns
        for col in self.feature_columns:
            if col not in X.columns:
                X[col] = 0.0
        X = X[self.feature_columns]
        X.fillna(0, inplace=True)

        proba = self.model.predict_proba(X)[:, 1]
        df_raw = df_raw.copy()
        df_raw["fraud_probability"] = np.round(proba, 4)
        df_raw["risk_level"]        = pd.cut(
            proba,
            bins=[-0.001, 0.35, 0.60, 1.001],
            labels=["Low", "Medium", "High"]
        ).astype(str)
        return df_raw

    def predict_single(self, row: dict) -> dict:
        """Predict fraud probability for a single transaction row."""
        df = pd.DataFrame([row])
        result = self.predict_transactions(df)
        prob = float(result["fraud_probability"].iloc[0])
        return {
            "fraud_probability": prob,
            "risk_level": _risk_level(prob),
        }

    def get_shap_explanations(self, df_raw: pd.DataFrame, max_rows: int = 200) -> list[dict]:
        """Return top SHAP features for each transaction."""
        if not self._loaded:
            return []
        try:
            import shap
            X, _, _, _ = engineer_features(df_raw.copy())
            for col in self.feature_columns:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[self.feature_columns].fillna(0).head(max_rows)
            explainer   = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X)
            results = []
            for i in range(len(X)):
                vals = shap_values[i]
                top_idx  = np.argsort(np.abs(vals))[::-1][:5]
                top_feats = [{"feature": self.feature_columns[j],
                               "shap_value": round(float(vals[j]), 4),
                               "value": round(float(X.iloc[i, j]), 4)}
                              for j in top_idx]
                results.append(top_feats)
            return results
        except Exception:
            return []


def _risk_level(prob: float) -> str:
    if prob >= 0.60:   return "High"
    if prob >= 0.35:   return "Medium"
    return "Low"


# Singleton instance
ml_service = MLService()
