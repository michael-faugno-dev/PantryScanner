# AI-Powered Pantry Monitor

An automated inventory tracking system that uses webcam capture, Claude AI vision analysis, and PostgreSQL to monitor pantry changes in real-time.

![Pantry Dashboard](pantry-dashboard.png)

## Overview

The Pantry Monitor automatically tracks inventory changes by capturing daily webcam images of your pantry and using Claude's vision AI to detect what's been added, removed, or changed. All changes are stored in a PostgreSQL database and displayed in a real-time web dashboard.

## Features

- **Automated Image Capture**: Daily webcam snapshots of your pantry
- **AI-Powered Analysis**: Claude Sonnet 4.5 vision model detects inventory changes
- **Smart Change Tracking**: Identifies added, removed, and quantity-changed items
- **PostgreSQL Database**: Persistent storage with full change history
- **Real-Time Dashboard**: Flask web app with live inventory view
- **API Cost Tracking**: Monitor Claude API usage and costs
- **Change History**: Complete timeline of all inventory modifications

## Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: PostgreSQL
- **AI**: Anthropic Claude API (Sonnet 4.5)
- **Computer Vision**: OpenCV (webcam capture)
- **Frontend**: HTML/CSS/JavaScript (dashboard)

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Webcam
- Anthropic API key

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/pantry-monitor.git
cd pantry-monitor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure PostgreSQL**
```bash
# Install PostgreSQL if not already installed
# On macOS:
brew install postgresql

# On Ubuntu:
sudo apt-get install postgresql postgresql-contrib

# Start PostgreSQL service
# On macOS:
brew services start postgresql

# On Ubuntu:
sudo service postgresql start
```

4. **Set up configuration**

Edit `pantry_config.py` with your settings:

```python
# Your Anthropic API Key
ANTHROPIC_API_KEY = "your-api-key-here"

# Webcam settings
WEBCAM_INDEX = 0  # Change if you have multiple cameras

# Database configuration
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'pantry_monitor',
    'user': 'postgres',
    'password': 'your-password-here'
}
```

5. **Initialize the database**
```bash
python setup_database.py
```

## Usage

### Running a Scan

Capture a new image and analyze changes:

```bash
python pantry_scanner.py
```

The scanner will:
1. Capture a webcam image
2. Send it to Claude for analysis
3. Detect added/removed items
4. Update the PostgreSQL database
5. Display changes in the terminal

### Viewing Inventory

Check current inventory from the command line:

```bash
python view_inventory.py
```

### Web Dashboard

Launch the web interface:

```bash
python app.py
```

Then open your browser to `http://localhost:5000`

The dashboard displays:
- **Live Pantry View**: Most recent webcam capture
- **Current Inventory**: All active items with quantities
- **Recent Changes**: Timeline of additions/removals
- **API Cost Tracker**: Claude API usage statistics

## Database Schema

### Tables

**pantry_scans**
- Stores each scan record with image path and API metadata

**pantry_items**
- Tracks current inventory with quantities and timestamps

**inventory_changes**
- Complete history of all detected changes

## API Costs

The system uses Claude Sonnet 4.5:
- Input: $3 per million tokens
- Output: $15 per million tokens

Typical scan costs: $0.005 - $0.02 per image analysis

## Configuration Options

### Camera Settings

```python
WEBCAM_INDEX = 0  # Adjust for multiple cameras
```

### Model Selection

```python
# Current model (recommended)
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# Faster/cheaper alternative
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Most powerful (higher cost)
CLAUDE_MODEL = "claude-opus-4-5-20251101"
```

### Scan Frequency

Set up automated scans with cron (Linux/Mac):

```bash
# Daily scan at 6 AM
0 6 * * * /usr/bin/python3 /path/to/pantry_scanner.py
```

Or Task Scheduler (Windows)

## Troubleshooting

### Webcam not detected
```python
# Try different camera indices
WEBCAM_INDEX = 1  # or 2, 3, etc.
```

### Database connection failed
- Verify PostgreSQL is running
- Check credentials in `pantry_config.py`
- Ensure database exists: `python setup_database.py`

### Reset database
```bash
python reset_database.py
```

## Project Structure

```
pantry-monitor/
├── pantry_scanner.py      # Main scanning script
├── app.py                 # Flask web dashboard
├── database.py            # Database operations
├── pantry_config.py       # Configuration
├── setup_database.py      # Database initialization
├── reset_database.py      # Database reset utility
├── view_inventory.py      # CLI inventory viewer
├── templates/             # HTML templates
├── static/                # CSS/JS assets
└── pantry_images/         # Stored webcam captures
```

## Security Notes

- **Never commit `pantry_config.py`** with real API keys
- Add to `.gitignore`:
  ```
  pantry_config.py
  pantry_images/
  *.pyc
  __pycache__/
  ```
- Use environment variables for production deployments

## Future Enhancements

- [ ] Expiration date tracking
- [ ] Shopping list generation
- [ ] Mobile app integration
- [ ] Multi-pantry support
- [ ] Recipe suggestions based on inventory
- [ ] Barcode scanning integration

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/claude)
- Database: [PostgreSQL](https://www.postgresql.org/)
- Web framework: [Flask](https://flask.palletsprojects.com/)

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

---

**Note**: This project requires an active Anthropic API key. API usage will incur costs based on Claude's current pricing.
