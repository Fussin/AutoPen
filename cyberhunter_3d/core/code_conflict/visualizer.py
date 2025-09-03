"""
This module contains the Code Conflict Visualizer.
"""
import os
from datetime import datetime

class Visualizer:
    """
    Visualizes code conflicts.
    """
    def __init__(self, conflicts):
        self.conflicts = conflicts

    def _generate_report_text(self):
        """
        Generates the text content for the report.
        """
        report_lines = ["--- Code Conflict Report ---"]
        if not self.conflicts:
            report_lines.append("No conflicts found.")
            return "\n".join(report_lines)

        for i, conflict in enumerate(self.conflicts, 1):
            report_lines.append(f"\n#{i}: {conflict.get('type')} [{conflict.get('severity')}]")
            report_lines.append(f"  File: {conflict.get('file')}")
            if conflict.get('dependency'):
                report_lines.append(f"  Dependency: {conflict.get('dependency')}")
                report_lines.append(f"    Detected Version: {conflict.get('detected_version')}")
                report_lines.append(f"    Affected Versions: {conflict.get('affected_versions')}")
            report_lines.append(f"  Description: {conflict.get('description')}")

        report_lines.append("\n--- End of Report ---")
        return "\n".join(report_lines)

    def visualize(self):
        """
        Prints a text-based visualization of the conflicts to the console.
        """
        report_text = self._generate_report_text()
        print(report_text)

    def save_report(self, output_dir):
        """
        Saves the text-based report to a timestamped file.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"conflict_report_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)

        report_text = self._generate_report_text()

        with open(filepath, "w") as f:
            f.write(report_text)

        print(f"Report saved to {filepath}")
        return filepath
