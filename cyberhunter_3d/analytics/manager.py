import time
from datetime import datetime
from functools import wraps
from cyberhunter_3d.web.models import db, Scan
from cyberhunter_3d.analytics.models import ScanMetrics

class AnalyticsManager:
    """
    Manages the collection and persistence of scan analytics and metrics.
    """
    def __init__(self, scan_id, app):
        self.scan_id = scan_id
        self.app = app
        self.metrics_obj = self._get_or_create_metrics_obj()

    def _get_or_create_metrics_obj(self):
        """
        Retrieves the ScanMetrics object for the current scan, creating it if it doesn't exist.
        """
        with self.app.app_context():
            metrics_obj = ScanMetrics.query.filter_by(scan_id=self.scan_id).first()
            if not metrics_obj:
                print(f"No ScanMetrics found for scan {self.scan_id}, creating a new one.")
                # Ensure the parent scan exists before creating metrics for it
                scan = Scan.query.get(self.scan_id)
                if not scan:
                    # This case should ideally not be hit in the normal application flow
                    raise ValueError(f"Cannot create metrics for a non-existent scan with ID {self.scan_id}")

                metrics_obj = ScanMetrics(scan_id=self.scan_id, metrics={})
                db.session.add(metrics_obj)
                db.session.commit()
            return metrics_obj

    def _update_metric(self, key, value):
        """
        Updates a specific key in the metrics JSONB field.
        This is a simplified implementation. For high-frequency updates,
        a more sophisticated approach might be needed to avoid race conditions
        or performance bottlenecks (e.g., using native JSON update functions).
        """
        with self.app.app_context():
            # Re-fetch the object to ensure we have the latest version
            current_metrics_obj = ScanMetrics.query.get(self.metrics_obj.id)
            if current_metrics_obj:
                # Create a mutable copy of the metrics dictionary
                new_metrics = dict(current_metrics_obj.metrics)
                new_metrics[key] = value
                current_metrics_obj.metrics = new_metrics
                db.session.commit()
                # Update the instance's metrics_obj to reflect the change
                self.metrics_obj = current_metrics_obj
            else:
                print(f"Warning: Could not find ScanMetrics with ID {self.metrics_obj.id} to update.")

    def track_phase_duration(self, phase_name):
        """
        A decorator to time a function and record its duration as a phase metric.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                self._update_metric(f'performance.{phase_name}.start_time_utc', datetime.utcnow().isoformat())

                result = func(*args, **kwargs)

                end_time = time.time()
                duration = round(end_time - start_time, 2)

                self._update_metric(f'performance.{phase_name}.end_time_utc', datetime.utcnow().isoformat())
                self._update_metric(f'performance.{phase_name}.duration_seconds', duration)
                print(f"Analytics: Phase '{phase_name}' completed in {duration} seconds.")

                return result
            return wrapper
        return decorator

    def increment_metric(self, key, value=1):
        """
        Increments a numeric value in the metrics.
        Example: increment_metric('discovery.subdomains.total', 5)
        """
        with self.app.app_context():
            current_metrics_obj = ScanMetrics.query.get(self.metrics_obj.id)
            if current_metrics_obj:
                new_metrics = dict(current_metrics_obj.metrics)

                # Navigate nested keys if needed, e.g., 'discovery.subdomains.total'
                keys = key.split('.')
                d = new_metrics
                for k in keys[:-1]:
                    d = d.setdefault(k, {})

                last_key = keys[-1]
                d[last_key] = d.get(last_key, 0) + value

                current_metrics_obj.metrics = new_metrics
                db.session.commit()
                self.metrics_obj = current_metrics_obj

    def track_vulnerability_severity(self, severity):
        """
        Increments the count for a given vulnerability severity.
        """
        severity = severity.lower()
        self.increment_metric(f'vulnerability.by_severity.{severity}')

    def update_scan_coverage(self, total_targets, scanned_targets):
        """
        Calculates and updates the scan coverage percentage.
        """
        if total_targets > 0:
            coverage = round((scanned_targets / total_targets) * 100, 2)
            self._update_metric('business.scan_coverage_percentage', coverage)
        else:
            self._update_metric('business.scan_coverage_percentage', 0)
