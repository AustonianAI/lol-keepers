# LOL Keepers - Flask CLI Application

A Flask-based command-line application for the LOL Keepers project.

## Setup

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

1. **Clone the repository** (if not already done):

   ```bash
   git clone <repository-url>
   cd lol-keepers
   ```

2. **Create and activate virtual environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env  # Create your local .env file
   # Edit .env with your specific configuration
   ```

### Using the Application

#### Web Interface

1. **Activate virtual environment**:

   ```bash
   source .venv/bin/activate
   ```

2. **Start the web server**:

   ```bash
   # Option 1: Use Flask development server (recommended)
   flask run --debug

   # Option 2: Run directly with Python
   python app.py

   # Option 3: Specify port manually if needed
   flask run --debug --port 5001
   ```

3. **Access the web interface**:
   - Keeper Analysis: http://127.0.0.1:5001/

#### CLI Commands

1. **Run CLI commands**:

   ```bash
   # See all available commands
   flask --help

   # Run analysis commands
   flask keeper-analysis
   flask league-standings
   ```

### Development

- Add new CLI commands using the `@app.cli.command()` decorator
- Environment variables are loaded from `.env` file
- Use `flask --help` to see all available commands

### Project Structure

```
lol-keepers/
├── .venv/              # Virtual environment (not tracked in git)
├── data/               # Data storage directory
│   ├── draft_results.json  # 2024 fantasy football draft results
│   └── fantasy_pros.csv     # 2025 fantasy projections
├── templates/          # HTML templates for web interface
│   ├── base.html       # Base template with styling
│   ├── keeper_analysis.html  # Interactive data table (home page)
│   └── error.html      # Error page
├── app.py              # Main Flask application with CLI commands
├── .flaskenv           # Flask-specific environment variables (port 5001)
├── requirements.txt    # Python dependencies
├── .gitignore         # Git ignore patterns
└── README.md          # This file
```

## CLI Commands

### Basic Commands

- `flask hello` - Simple Hello World command
- `flask status` - Check application status and configuration

### Draft Management Commands

- `flask draft-summary` - Display 2024 fantasy football draft summary with managers
- `flask league-standings` - Display league standings with manager ratings and levels
- `flask team-roster` - Show roster for a specific team (interactive, keepers marked with K)

### Keeper Management Commands

- `flask list-keepers` - Display all players marked as keepers
- `flask update-keeper` - Mark a player as keeper or remove keeper status (interactive)

### 2025 Keeper Eligibility Commands

- `flask eligible-keepers` - Show 2024 keepers and their 2025 eligibility status
- `flask keeper-ineligible` - Display players NOT eligible to be kept for 2025

### Keeper Analysis & Projections

- `flask keeper-analysis` - Generate comprehensive keeper analysis with 2025 projections
- `create_keeper_analysis_dataframe()` - Python function returning pandas DataFrame with all player data

### Web Interface

- **Keeper Analysis:** `http://127.0.0.1:5001/` - Interactive sortable table with filters
  - Sort by any column (click headers)
  - Filter: All Players | Current Keepers | 2025 Eligible | Valuable Keepers
  - Search by player name or team
  - Responsive design for mobile/desktop

### Built-in Flask Commands

- `flask routes` - Show available routes (Flask built-in)
- `flask shell` - Open interactive shell with app context (Flask built-in)
- `flask run` - Start the Flask development server

## Contributing

1. Make sure your virtual environment is activated
2. Install dependencies: `pip install -r requirements.txt`
3. Make your changes
4. Test your changes
5. Create a pull request
