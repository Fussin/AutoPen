# You no longer need to pass the app object around
from .core.scan_manager import run_discovery_phase
from run_web import celery_app # Import the Celery app instance

@celery_app.task(name="run_scan_discovery")
def run_discovery_task(scan_id: int):
    """
    Celery task to run the discovery phase of a scan.
    The FlaskTask class we defined earlier automatically provides the app context.
    """
    print(f"Starting discovery task for scan ID: {scan_id}")
    run_discovery_phase(scan_id)
    print(f"Finished discovery task for scan ID: {scan_id}")

# You can define other tasks here, e.g., for the execution phase
# @celery_app.task(name="run_scan_execution")
# def run_execution_task(scan_id: int):
#     run_execution_phase(scan_id)
