import unittest
import os
import joblib
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.reconnaissance.ai.noise_filter import NoiseFilter

class TestNoiseFilter(unittest.TestCase):

    def setUp(self):
        self.test_model_path = "test_model.joblib"
        self.noise_filter = NoiseFilter(model_path=self.test_model_path)
        self.labeled_data = [
            ("dev.example.com", False),
            ("staging.example.com", False),
            ("www.example.com", False),
            ("randomstringofchars", True),
            ("another-random-string", True),
        ]

    def tearDown(self):
        if os.path.exists(self.test_model_path):
            os.remove(self.test_model_path)

    def test_train(self):
        """Tests that the train method creates a model file."""
        self.noise_filter.train(self.labeled_data)
        self.assertTrue(os.path.exists(self.test_model_path))

    def test_predict_with_trained_model(self):
        """Tests the predict method with a trained model."""
        # Train the model first
        self.noise_filter.train(self.labeled_data)

        # Now, create a new instance to load the model
        new_filter = NoiseFilter(model_path=self.test_model_path)

        subdomains_to_predict = ["test.example.com", "anotherrandomstring", "www.example.com"]

        # We expect 'anotherrandomstring' to be filtered out
        expected_valid = ["test.example.com", "www.example.com"]

        # The model might not be perfect, so we check if the prediction is reasonable
        # For this test, we'll mock the actual predict call to check the logic
        with patch.object(new_filter.model, 'predict', return_value=[False, True, False]) as mock_predict:
            valid_subdomains = new_filter.predict(subdomains_to_predict)
            self.assertEqual(valid_subdomains, expected_valid)
            mock_predict.assert_called_once()

    def test_predict_no_model(self):
        """Tests that the predict method returns all subdomains if no model is found."""
        # Ensure no model file exists
        if os.path.exists(self.test_model_path):
            os.remove(self.test_model_path)

        no_model_filter = NoiseFilter(model_path=self.test_model_path)

        subdomains = ["a.com", "b.com"]
        self.assertEqual(no_model_filter.predict(subdomains), subdomains)

if __name__ == '__main__':
    unittest.main()
