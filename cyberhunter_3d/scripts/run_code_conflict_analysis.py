"""
This script provides an example of how to use the Code Conflict Analyzer and Visualizer.
It creates a dummy requirements.txt file, analyzes it, and prints the results.
"""
import os
import shutil
from cyberhunter_3d.core.code_conflict import Analyzer, Visualizer

def main():
    """
    Main function to run the analysis and visualization.
    """
    # Create a temporary directory and a dummy requirements.txt for demonstration
    temp_dir = "temp_codebase"
    os.makedirs(temp_dir, exist_ok=True)
    requirements_path = os.path.join(temp_dir, "requirements.txt")
    with open(requirements_path, "w") as f:
        f.write("requests==2.24.0\n") # Vulnerable
        f.write("django==3.0.0\n")   # Vulnerable
        f.write("numpy>=1.20.0\n")   # Not in our DB
        f.write("requests==2.25.0\n") # Safe version

    print(f"Created a dummy requirements.txt at: {requirements_path}")
    print("Running conflict analysis...")

    try:
        # 1. Analyze the dummy codebase
        analyzer = Analyzer(temp_dir)
        conflicts = analyzer.analyze()

        # 2. Visualize the results
        visualizer = Visualizer(conflicts)
        visualizer.visualize()
    finally:
        # 3. Clean up the temporary directory
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    main()
