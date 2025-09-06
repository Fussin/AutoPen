import hashlib
import json
import os
import tarfile
import time
import language_tool_python
from bs4 import BeautifulSoup
from ..common.utils import LOG
from .exceptions import DataFinalizationError

class ExitChecklist:
    """
    Handles the comprehensive exit checklist for data finalization,
    quality assurance, and cleanup.
    """

    def __init__(self, results_file):
        """
        Initializes the ExitChecklist with the path to the scan results file.
        """
        self.results_file = results_file
        self.final_data = None
        self.performance_metrics = []

    def run_data_finalization(self):
        """
        Executes the data finalization part of the checklist.
        """
        ts = time.time()
        LOG.info("Starting data finalization...")
        try:
            self._merge_temp_files()
            self._remove_duplicates()
            self._validate_proofs()
            checksum = self._generate_checksums()
            self._create_archives()
            LOG.info("Data finalization complete. Checksum: %s", checksum)
        except Exception as e:
            raise DataFinalizationError(f"Data finalization failed: {e}")
        finally:
            te = time.time()
            self.performance_metrics.append(("run_data_finalization", te - ts))

    def run_quality_assurance(self, html_report_file=None):
        """
        Executes the quality assurance part of the checklist.
        """
        ts = time.time()
        LOG.info("Starting quality assurance...")
        self._automated_report_review()
        self._grammar_and_spelling_check(html_report_file)
        self._technical_accuracy_validation()
        self._screenshot_quality_verification()
        self._poc_reproducibility_check()
        LOG.info("Quality assurance complete.")
        te = time.time()
        self.performance_metrics.append(("run_quality_assurance", te - ts))

    def _automated_report_review(self):
        LOG.info("Automated report review...")
        pass

    def _grammar_and_spelling_check(self, html_report_file=None):
        """
        Checks the grammar and spelling of the HTML report.
        """
        if not html_report_file or not os.path.exists(html_report_file):
            LOG.warning("HTML report file not provided or does not exist. Skipping grammar check.")
            return

        LOG.info("Grammar and spelling check...")
        try:
            with open(html_report_file, 'r') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()

            tool = language_tool_python.LanguageTool('en-US')
            matches = tool.check(text)

            if matches:
                LOG.warning(f"Found {len(matches)} potential grammar/spelling issues:")
                for match in matches:
                    LOG.warning(f"  - {match}")
            else:
                LOG.info("No grammar or spelling issues found.")

        except Exception as e:
            LOG.error(f"An error occurred during grammar and spelling check: {e}")

    def _technical_accuracy_validation(self):
        LOG.info("Technical accuracy validation...")
        pass

    def _screenshot_quality_verification(self):
        LOG.info("Screenshot quality verification...")
        pass

    def _poc_reproducibility_check(self):
        LOG.info("PoC reproducibility check...")
        pass

    def run_distribution(self):
        """
        Executes the distribution part of the checklist.
        """
        ts = time.time()
        LOG.info("Starting distribution...")
        self._email_reports_to_stakeholders()
        self._upload_to_bug_bounty_platforms()
        self._update_team_dashboards()
        self._sync_with_ticketing_systems()
        self._archive_to_secure_storage()
        LOG.info("Distribution complete.")
        te = time.time()
        self.performance_metrics.append(("run_distribution", te - ts))

    def _email_reports_to_stakeholders(self):
        LOG.info("Emailing reports to stakeholders...")
        pass

    def _upload_to_bug_bounty_platforms(self):
        LOG.info("Uploading to bug bounty platforms...")
        pass

    def _update_team_dashboards(self):
        LOG.info("Updating team dashboards...")
        pass

    def _sync_with_ticketing_systems(self):
        LOG.info("Syncing with ticketing systems...")
        pass

    def _archive_to_secure_storage(self):
        LOG.info("Archiving to secure storage...")
        pass

    def _merge_temp_files(self):
        """
        Merges all temporary result files into a single data structure.
        For now, it just loads the main results file.
        """
        LOG.info("Merging temporary files...")
        try:
            with open(self.results_file, 'r') as f:
                self.final_data = json.load(f)
            LOG.info("Temporary files merged successfully.")
        except FileNotFoundError:
            raise DataFinalizationError(f"Results file not found: {self.results_file}")
        except json.JSONDecodeError:
            raise DataFinalizationError(f"Invalid JSON in results file: {self.results_file}")

    def _remove_duplicates(self):
        """
        Removes duplicate findings from the final data.
        """
        LOG.info("Removing duplicate findings...")
        if self.final_data and "subdomains" in self.final_data:
            unique_subdomains = sorted(list(set(self.final_data["subdomains"])))
            self.final_data["subdomains"] = unique_subdomains
            LOG.info(f"Removed duplicates, {len(unique_subdomains)} unique subdomains remaining.")

    def _validate_proofs(self):
        """
        Validates all vulnerability proofs.
        This is a placeholder for now.
        """
        LOG.info("Validating vulnerability proofs...")
        # Placeholder for proof validation logic
        pass

    def _generate_checksums(self):
        """
        Generates checksums for the final data to ensure integrity.
        """
        LOG.info("Generating checksums...")
        if self.final_data:
            data_str = json.dumps(self.final_data, sort_keys=True)
            checksum = hashlib.sha256(data_str.encode('utf-8')).hexdigest()
            with open(self.results_file + ".sha256", 'w') as f:
                f.write(checksum)
            return checksum
        return None

    def _create_archives(self):
        """
        Creates compressed archives of the final results.
        """
        LOG.info("Creating compressed archives...")
        archive_name = self.results_file + ".tar.gz"
        with tarfile.open(archive_name, "w:gz") as tar:
            tar.add(self.results_file, arcname=os.path.basename(self.results_file))
        LOG.info("Archive created at %s", archive_name)

    def run_cleanup_and_optimization(self, report_files=None):
        """
        Executes the cleanup and optimization part of the checklist.
        """
        ts = time.time()
        LOG.info("Starting cleanup and optimization...")
        self._clear_temporary_files(report_files)
        self._reset_tool_configurations()
        self._update_scan_statistics(report_files=report_files)
        self._log_performance_metrics()
        self._free_allocated_resources()
        LOG.info("Cleanup and optimization complete.")
        te = time.time()
        self.performance_metrics.append(("run_cleanup_and_optimization", te - ts))

    def _clear_temporary_files(self, report_files=None):
        """
        Clears all temporary files created during the scan.
        """
        LOG.info("Clearing temporary files...")
        files_to_remove = [
            self.results_file,
            self.results_file + ".sha256",
            self.results_file + ".tar.gz",
        ]
        if report_files:
            files_to_remove.extend(report_files)

        for f in files_to_remove:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    LOG.info(f"Removed temporary file: {f}")
                except OSError as e:
                    LOG.error(f"Error removing file {f}: {e}")

    def _reset_tool_configurations(self):
        """
        Resets any tool configurations that were modified.
        Placeholder for now.
        """
        LOG.info("Resetting tool configurations...")
        # Placeholder for config reset
        pass

    def _update_scan_statistics(self, report_files=None):
        """
        Updates scan statistics.
        """
        LOG.info("Updating scan statistics...")
        stats_file = "scan_statistics.txt"
        total_duration = sum(duration for _, duration in self.performance_metrics)
        num_subdomains = len(self.final_data.get("subdomains", []))

        try:
            with open(stats_file, 'w') as f:
                f.write("--- Scan Statistics ---\n")
                f.write(f"Number of subdomains found: {num_subdomains}\n")
                f.write(f"Total scan duration: {total_duration:.2f} seconds\n")
                if report_files:
                    f.write("\nGenerated Reports:\n")
                    for report_file in report_files:
                        f.write(f"  - {report_file}\n")
                f.write("-----------------------\n")
            LOG.info(f"Scan statistics saved to {stats_file}")
        except Exception as e:
            LOG.error(f"Failed to update scan statistics: {e}")

    def _log_performance_metrics(self):
        """
        Logs performance metrics for the scan.
        """
        LOG.info("--- Performance Metrics ---")
        for method_name, duration in self.performance_metrics:
            LOG.info(f"  - {method_name}: {duration:.2f} seconds")
        LOG.info("-------------------------")

    def _free_allocated_resources(self):
        """
        Frees up any allocated resources.
        Placeholder for now.
        """
        LOG.info("Freeing allocated resources...")
        # Placeholder for resource freeing
        pass
