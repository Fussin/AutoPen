import psutil
import pandas as pd
from sqlalchemy import func, case
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from cyberhunter_3d.web.models import db, Technology, Vulnerability, ToolSuccessRate, Asset

class ScanOptimizationEngine:
    """
    The ScanOptimizationEngine uses historical data, real-time adjustments,
    and machine learning predictions to optimize the scanning process.
    """

    def __init__(self, scan_id, app):
        self.scan_id = scan_id
        self.app = app
        self.historical_data = self._analyze_historical_data()

    def _analyze_historical_data(self):
        """
        Analyzes historical scan data to calculate success rates and average execution times for tools.
        """
        print("Analyzing historical data...")
        with self.app.app_context():
            tool_stats = {}
            results = db.session.query(
                ToolSuccessRate.tool_name,
                func.count(ToolSuccessRate.id),
                func.sum(case((ToolSuccessRate.success, 1), else_=0)),
                func.avg(ToolSuccessRate.execution_time)
            ).group_by(ToolSuccessRate.tool_name).all()

            for tool_name, total_runs, total_successes, avg_time in results:
                success_rate = (total_successes / total_runs) * 100 if total_runs > 0 else 0
                tool_stats[tool_name] = {
                    "success_rate": success_rate,
                    "avg_time": avg_time
                }

        return {
            "tool_stats": tool_stats
        }

    def _get_heuristic_predictions(self, assets):
        """
        Trains a simple ML model on historical data to predict vulnerability likelihood.
        """
        print("Generating ML predictions...")
        with self.app.app_context():
            history = ToolSuccessRate.query.all()
            if len(history) < 10:  # Not enough data to train a model
                print("Not enough historical data to train ML model. Falling back to heuristics.")
                return self._fallback_heuristic_predictions(assets)

            # Create a DataFrame from the historical data
            df = pd.DataFrame([{
                'tool_name': r.tool_name,
                'tech_stack': r.tech_stack.get('name', 'Unknown'),
                'success': r.success
            } for r in history])

            # One-hot encode categorical features
            X = pd.get_dummies(df[['tool_name', 'tech_stack']], drop_first=True)
            y = df['success']

            # Train a simple logistic regression model
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = LogisticRegression()
            model.fit(X_train, y_train)

            # "Predict" for the current assets
            predictions = {}
            all_tools = df['tool_name'].unique()
            all_tech = df['tech_stack'].unique()

            for asset in assets:
                asset_tech = "Unknown"
                if asset.technologies:
                    asset_tech = asset.technologies[0].name # Simplification

                # Predict for each tool
                for tool_name in all_tools:
                    # Create a feature vector for the current asset-tool pair
                    features = {f'tool_name_{t}': 0 for t in all_tools if t != df['tool_name'].iloc[0]}
                    features.update({f'tech_stack_{t}': 0 for t in all_tech if t != df['tech_stack'].iloc[0]})

                    if f'tool_name_{tool_name}' in features:
                        features[f'tool_name_{tool_name}'] = 1
                    if f'tech_stack_{asset_tech}' in features:
                        features[f'tech_stack_{asset_tech}'] = 1

                    feature_vector = pd.DataFrame([features], columns=X_train.columns)

                    try:
                        proba = model.predict_proba(feature_vector)[0][1]
                        predictions.setdefault(asset.id, {})[tool_name] = proba
                    except Exception as e:
                        # Fallback for new tools/tech not seen in training
                        predictions.setdefault(asset.id, {})[tool_name] = 0.1

        return {
            "vulnerability_scores": predictions,
            "optimal_payloads": {},
            "time_estimation": "N/A"
        }

    def _fallback_heuristic_predictions(self, assets):
        """
        A simple heuristic model when there's not enough data for ML.
        """
        vulnerability_scores = {}
        for asset in assets:
            score = 0
            if asset.details and 'http' in asset.details.get('service', ''):
                score += 10
            vulnerability_scores[asset.id] = score
            asset.details['vulnerability_score'] = score
        return {
            "vulnerability_scores": vulnerability_scores,
            "optimal_payloads": {},
            "time_estimation": "N/A"
        }

    def _get_real_time_adjustments(self, assets, predictions):
        """
        Adjusts the scan plan based on heuristic predictions and system load.
        """
        print("Making real-time adjustments...")

        # Adjust thread count based on system load
        cpu_load = psutil.cpu_percent()
        if cpu_load > 80:
            thread_count = 5
        elif cpu_load < 50:
            thread_count = 20
        else:
            thread_count = 10

        adjustments = {
            "assets_to_prioritize": [],
            "skipped_tools": {},
            "thread_count": thread_count
        }
        scores = predictions.get("vulnerability_scores", {})
        priority_threshold = 15

        for asset in assets:
            # Prioritize assets based on score
            if scores.get(asset.id, 0) > priority_threshold:
                asset.details['priority'] = 'high'
                adjustments['assets_to_prioritize'].append(asset.id)
            else:
                asset.details['priority'] = 'low'

            # Skip irrelevant tools based on tech stack
            # This is a simplified example. A real implementation would have a mapping of tools to technologies.
            tech_stack = [tech.name for tech in asset.technologies]
            if "PHP" not in tech_stack:
                adjustments["skipped_tools"].setdefault(asset.id, []).append("php-vuln-scanner")
            if "WordPress" not in tech_stack:
                 adjustments["skipped_tools"].setdefault(asset.id, []).append("wpscan")

        return adjustments

    def get_ranked_tasks(self):
        """
        The main entry point for the optimization engine.
        Returns a ranked list of tasks for the execution phase.
        """
        with self.app.app_context():
            assets = Asset.query.filter_by(
                scan_id=self.scan_id,
                is_approved_for_scan=True
            ).all()

            predictions = self._get_heuristic_predictions(assets)
            adjustments = self._get_real_time_adjustments(assets, predictions)

            # Create a list of tasks
            tasks = []
            tool_stats = self.historical_data.get("tool_stats", {})
            for asset in assets:
                for tool_name, stats in tool_stats.items():
                    if tool_name in adjustments.get("skipped_tools", {}).get(asset.id, []):
                        continue

                    # Calculate priority score
                    likelihood_score = predictions.get("vulnerability_scores", {}).get(asset.id, {}).get(tool_name, 0)
                    success_rate = stats.get("success_rate", 0)
                    avg_time = stats.get("avg_time", 1)
                    priority = (success_rate * likelihood_score) / avg_time if avg_time > 0 else 0

                    tasks.append({
                        "tool": tool_name,
                        "asset_id": asset.id,
                        "priority": priority
                    })

            # Rank tasks by priority
            ranked_tasks = sorted(tasks, key=lambda x: x['priority'], reverse=True)

            # Save changes to the database
            db.session.commit()

            print("Scan optimization complete.")
            return ranked_tasks
