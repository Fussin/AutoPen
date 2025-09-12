# CyberHunter Reconnaissance Framework

CyberHunter is an automated reconnaissance and asset discovery framework designed to streamline security assessments. It integrates a suite of popular open-source tools into a cohesive pipeline, managed via a web interface or a REST API, and provides powerful visualization of discovered assets.

## Key Features

* **Multi-Source Reconnaissance**: Gathers data using passive DNS, active brute-forcing, ASN lookups, and organization name expansion.
* **Modular Plugin System**: Easily extendable architecture for wrapping and integrating any command-line security tool.
* **Web Dashboard**: A user-friendly Flask-based interface for managing scans, reviewing discovered assets, and visualizing results.
* **3D Graph Visualization**: An interactive 3D force-directed graph helps visualize the relationships between targets, assets, and vulnerabilities.
* **REST API**: A secure, key-based API for programmatic control over scans and results retrieval.
* **Scope Management**: Clearly define in-scope and out-of-scope targets using wildcard rules.

## Architecture Overview

CyberHunter consists of three main components:
1.  **Core Engine**: Orchestrates the reconnaissance pipeline, from initial target parsing to running discovery and enrichment plugins.
2.  **Plugins**: Wrappers around external tools like Subfinder, Nmap, httpx, and Nuclei.
3.  **Web Application**: A Flask server that provides the user dashboard and the REST API.

## Installation

### Prerequisites
- Python 3.9+
- Go (for installing most of the security tools)
- A number of external security tools (see `scripts/install_tools.sh`)

### Quick Install
A convenience script is provided to install all required Go tools and Python packages on Debian-based systems.

```bash
# Clone the repository
git clone https://github.com/your-username/cyberhunter-3d.git
cd cyberhunter-3d

# Run the installer
chmod +x scripts/install_tools.sh
./scripts/install_tools.sh

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### 1. Set Up Environment Variables
Before running the application, create a `.env` file in the project root. You can copy the example file:
```bash
cp .env.example .env
```
Now, open the `.env` file and set a strong, unique `SECRET_KEY`.

### 2. Initialize the Database
This project uses Flask-Migrate to handle database schema migrations.

```bash
# To set the FLASK_APP environment variable
export FLASK_APP=run_web.py

# For the first time setup:
flask db init

# For creating a new migration after changing models:
flask db migrate -m "Initial migration."

# To apply the migration to the database:
flask db upgrade
```

### 3. Run the Web Server
```bash
python run_web.py
```
Navigate to `http://127.0.0.1:5001` to access the dashboard.

### 3. Using the API
You can create and manage scans programmatically. First, retrieve your API key from the "Profile" page in the web UI.

**Example: Start a new scan**
```bash
curl -X POST http://127.0.0.1:5001/api/v1/scans \
-H "Content-Type: application/json" \
-H "X-API-Key: YOUR_API_KEY_HERE" \
-d '{
    "targets": ["example.com", "*.example.com"],
    "in_scope_rules": "*.example.com",
    "out_of_scope_rules": "api.example.com"
}'
```

## Contributing
Contributions are welcome! Please feel free to open an issue or submit a pull request.

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
