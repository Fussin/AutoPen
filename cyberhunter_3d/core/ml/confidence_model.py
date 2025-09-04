import logging
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)

class ConfidenceModel:
    """
    A class to encapsulate the machine learning model for predicting the
    confidence of a finding being a true positive.
    """
    def __init__(self, model_path: str = "confidence_model.txt"):
        self.model_path = model_path
        self.model: Optional[lgb.Booster] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self._load_model()

    def _load_model(self):
        """Loads the trained model from disk."""
        try:
            self.model = lgb.Booster(model_file=self.model_path)
            log.info(f"Confidence model loaded from {self.model_path}")
        except lgb.basic.LightGBMError:
            log.warning(f"No pre-existing confidence model found at {self.model_path}. Model needs to be trained.")
            self.model = None

    def _preprocess_features(self, findings_df: pd.DataFrame, is_training: bool = False) -> pd.DataFrame:
        """
        Converts raw finding data into features suitable for the model.
        """
        df_copy = findings_df.copy()
        categorical_features = ['severity', 'finding_signature', 'ctx_source_tool']

        # Ensure columns exist, fill NaNs
        for col in categorical_features:
            if col not in df_copy.columns:
                df_copy[col] = 'missing'
        df_copy[categorical_features] = df_copy[categorical_features].fillna('missing')

        # Convert to category dtype, which lightgbm can handle
        for col in categorical_features:
            df_copy[col] = df_copy[col].astype('category')

        return df_copy[categorical_features]

    def train(self, findings_data: List[Dict[str, Any]]):
        """
        Trains the confidence model on historical finding data.
        """
        log.info(f"Starting confidence model training with {len(findings_data)} records.")
        training_data = [f for f in findings_data if f.get('validation_outcome') is not None]
        if len(training_data) < 10: # Lowered for easier testing
            log.warning(f"Not enough validated findings ({len(training_data)}) to train a model. Need at least 10.")
            return

        df = pd.DataFrame(training_data)
        asset_context_df = pd.json_normalize(df['asset_context']).add_prefix('ctx_')
        df = pd.concat([df.drop('asset_context', axis=1), asset_context_df], axis=1)

        X = self._preprocess_features(df, is_training=True)
        y = df['validation_outcome'].astype(int)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        lgbm = lgb.LGBMClassifier(objective='binary', metric='auc')
        lgbm.fit(X_train, y_train, eval_set=[(X_test, y_test)], callbacks=[lgb.early_stopping(5, verbose=False)])

        lgbm.booster_.save_model(self.model_path)
        self.model = lgbm.booster_
        log.info(f"Confidence model trained and saved to {self.model_path}")

    def predict(self, finding_data: Dict[str, Any]) -> float:
        """
        Predicts the confidence score for a single new finding.
        """
        if not self.model:
            return 0.5

        df = pd.DataFrame([finding_data])
        asset_context_df = pd.json_normalize(df['asset_context']).add_prefix('ctx_')
        df = pd.concat([df.drop('asset_context', axis=1), asset_context_df], axis=1)

        X = self._preprocess_features(df, is_training=False)

        prediction = self.model.predict(X, num_iteration=self.model.best_iteration)
        return float(prediction[0])
