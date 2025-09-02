"""
This script runs the autonomous Code Conflict Analyzer on the project root directory
and saves the report to a file.
"""
import os
from cyberhunter_3d.core.code_conflict import Analyzer, Visualizer

def main():
    """
    Main function to run the analysis and save the report.
    """
    project_root = "." # Analyze the current project
    output_dir = "reports"

    print(f"Starting analysis of requirements files in: {os.path.abspath(project_root)}")

    # 1. Analyze the codebase
    analyzer = Analyzer(project_root)
    conflicts = analyzer.analyze()

    # 2. Save the report
    visualizer = Visualizer(conflicts)
    visualizer.save_report(output_dir)

if __name__ == "__main__":
    main()
