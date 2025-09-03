import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from threading import Thread

from cyberhunter_3d.web.models import db, Schedule, Scan, Target, now_utc
from cyberhunter_3d.core.scan_manager import launch_scan

log = logging.getLogger(__name__)

class SchedulerService:
    """
    A service to manage scheduled scans.
    """
    def __init__(self, app: Flask):
        self.app = app
        self.scheduler = BackgroundScheduler(daemon=True)

    def _is_due(self, schedule: Schedule) -> bool:
        """
        Checks if a scheduled scan is due to run.
        """
        if not schedule.last_run_at:
            return True  # Never run before

        now = now_utc()
        last_run_aware = schedule.last_run_at
        if last_run_aware.tzinfo is None:
            last_run_aware = last_run_aware.replace(tzinfo=timezone.utc)

        if schedule.frequency == 'daily':
            return now >= last_run_aware + timedelta(days=1)
        elif schedule.frequency == 'weekly':
            return now >= last_run_aware + timedelta(weeks=1)
        elif schedule.frequency == 'monthly':
            return now >= last_run_aware + timedelta(days=30)

        return False

    def _check_and_run_scans(self):
        """
        The job that checks the database for scheduled scans that are due.
        """
        with self.app.app_context():
            log.info("Scheduler job running: Checking for due scans...")
            due_schedules = [s for s in Schedule.query.filter_by(is_active=True).all() if self._is_due(s)]

            if not due_schedules:
                log.info("No scans are due to run.")
                return

            log.info(f"Found {len(due_schedules)} scans to run.")
            for schedule in due_schedules:
                log.info(f"Triggering scan for target: {schedule.target.value}")

                new_scan = Scan(
                    status='QUEUED',
                    user_id=schedule.target.scan.user_id,
                    in_scope_rules=schedule.target.scan.in_scope_rules,
                    out_of_scope_rules=schedule.target.scan.out_of_scope_rules,
                )
                new_scan.targets.append(schedule.target)
                db.session.add(new_scan)

                schedule.last_run_at = now_utc()
                db.session.commit()

                scan_thread = Thread(
                    target=launch_scan,
                    args=(new_scan.id, self.app)
                )
                scan_thread.daemon = True
                scan_thread.start()

    def start(self):
        """
        Starts the scheduler and adds the recurring job.
        """
        log.info("Starting scheduler service...")
        self.scheduler.add_job(
            self._check_and_run_scans,
            'interval',
            minutes=1,
            id='check_scans_job',
            replace_existing=True
        )
        self.scheduler.start()
        log.info("Scheduler service started.")

    def shutdown(self):
        """
        Shuts down the scheduler.
        """
        log.info("Shutting down scheduler service...")
        self.scheduler.shutdown()
        log.info("Scheduler service shut down.")
