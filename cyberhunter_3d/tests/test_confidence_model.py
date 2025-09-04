import unittest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.ml.confidence_model import ConfidenceModel

class TestConfidenceModel(unittest.TestCase):

    def setUp(self):
        self.model_path = "test_confidence_model.txt"
        self.confidence_model = ConfidenceModel(model_path=self.model_path)

        self.findings_data = [
            {
                'finding_signature': 'nuclei:cve-2021-44228', 'severity': 'Critical',
                'asset_context': {'source_tool': 'nuclei'}, 'validation_outcome': True
            },
            {
                'finding_signature': 'trufflehog:generic', 'severity': 'High',
                'asset_context': {'source_tool': 'trufflehog'}, 'validation_outcome': True
            },
            {
                'finding_signature': 'nuclei:misconfiguration', 'severity': 'Medium',
                'asset_context': {'source_tool': 'nuclei'}, 'validation_outcome': False
            },
            *[{
                'finding_signature': 'nuclei:generic-vuln', 'severity': 'Low',
                'asset_context': {'source_tool': 'nuclei'}, 'validation_outcome': False
            }] * 10
        ]

    def tearDown(self):
        if os.path.exists(self.model_path):
            os.remove(self.model_path)

    def test_preprocess_features(self):
        df = pd.DataFrame(self.findings_data)
        asset_context_df = pd.json_normalize(df['asset_context']).add_prefix('ctx_')
        df = pd.concat([df.drop('asset_context', axis=1), asset_context_df], axis=1)

        # We test the private method, so we pass only the columns it expects
        features_df = self.confidence_model._preprocess_features(
            df[['severity', 'finding_signature', 'ctx_source_tool']], is_training=True
        )

        self.assertTrue(pd.api.types.is_categorical_dtype(features_df['severity']))
        # The label_encoders dict is no longer used, so we can remove this check
        # self.assertEqual(len(self.confidence_model.label_encoders), 3)

    def test_train_creates_model_file(self):
        self.assertFalse(os.path.exists(self.model_path))
        self.confidence_model.train(self.findings_data)
        self.assertTrue(os.path.exists(self.model_path))

    def test_predict_returns_score(self):
        self.confidence_model.train(self.findings_data)
        new_finding = {
            'finding_signature': 'nuclei:new-vuln', 'severity': 'High',
            'asset_context': {'source_tool': 'nuclei'}
        }
        score = self.confidence_model.predict(new_finding)
        self.assertIsInstance(score, float)

    def test_predict_without_trained_model(self):
        new_model = ConfidenceModel(model_path="non_existent_model.txt")
        new_finding = {'finding_signature': 'nuclei:new-vuln', 'severity': 'High', 'asset_context': {'source_tool': 'nuclei'}}
        score = new_model.predict(new_finding)
        self.assertEqual(score, 0.5)

if __name__ == '__main__':
    unittest.main()
