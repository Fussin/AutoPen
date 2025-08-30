import logging
import re
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import FunctionTransformer

log = logging.getLogger(__name__)

# --- Feature Extraction Functions ---

def get_length(text):
    return pd.DataFrame([len(t) for t in text])

def get_subdomain_parts(text):
    return pd.DataFrame([t.count('.') + 1 for t in text])

def has_numbers(text):
    return pd.DataFrame([any(char.isdigit() for char in t) for t in text])

def has_hyphens(text):
    return pd.DataFrame(['-' in t for t in text])

# --- Main Classifier Class ---

class NoiseFilter:
    def __init__(self, model_path="noise_filter_model.joblib"):
        self.model_path = model_path
        self.pipeline = self._build_pipeline()
        try:
            self.model = joblib.load(self.model_path)
            log.info(f"Loaded noise filter model from {self.model_path}")
        except FileNotFoundError:
            self.model = None
            log.warning(f"Noise filter model not found at {self.model_path}. Please train the model.")

    def _build_pipeline(self):
        """Builds the scikit-learn pipeline for feature extraction and classification."""

        # Feature extraction pipeline
        feature_pipeline = FeatureUnion([
            ('length', FunctionTransformer(get_length, validate=False)),
            ('parts', FunctionTransformer(get_subdomain_parts, validate=False)),
            ('has_numbers', FunctionTransformer(has_numbers, validate=False)),
            ('has_hyphens', FunctionTransformer(has_hyphens, validate=False)),
            ('chars', CountVectorizer(analyzer='char', ngram_range=(1, 3))),
        ])

        # Full pipeline with classifier
        pipeline = Pipeline([
            ('features', feature_pipeline),
            ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        return pipeline

    def train(self, labeled_data):
        """
        Trains the classifier on labeled data.
        :param labeled_data: A list of tuples, where each tuple is (subdomain_string, is_false_positive_boolean)
        """
        log.info("Training noise filter model...")
        if not labeled_data:
            log.error("No labeled data provided for training.")
            return

        df = pd.DataFrame(labeled_data, columns=['subdomain', 'is_false_positive'])
        X = df['subdomain']
        y = df['is_false_positive']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.pipeline.fit(X_train, y_train)

        accuracy = self.pipeline.score(X_test, y_test)
        log.info(f"Model training complete. Accuracy: {accuracy:.2f}")

        joblib.dump(self.pipeline, self.model_path)
        log.info(f"Saved trained model to {self.model_path}")
        self.model = self.pipeline

    def predict(self, subdomains):
        """
        Predicts which subdomains are likely to be false positives.
        :param subdomains: A list of subdomain strings.
        :return: A list of subdomains predicted to be valid (not false positives).
        """
        if self.model is None:
            log.warning("No trained model available. Skipping noise filtering.")
            return subdomains

        if not subdomains:
            return []

        predictions = self.model.predict(subdomains)

        valid_subdomains = [sub for sub, pred in zip(subdomains, predictions) if not pred]

        log.info(f"Filtered {len(subdomains) - len(valid_subdomains)} subdomains as noise.")
        return valid_subdomains
