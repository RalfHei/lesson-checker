# Tahvel Lesson Checker

A command-line tool to verify that all planned lessons have corresponding journal entries in the Tahvel educational management system.

## Overview

Tahvel Lesson Checker helps teachers and educational administrators ensure that all planned lessons have been properly documented in the Tahvel system. It compares planned lesson dates with actual journal entries and highlights any discrepancies.

## Features

- List and select from available study years
- View and select journals to check
- Display a comparison table showing planned vs. entered lessons
- Calculate and display completion statistics
- Process single journals or all journals in a study year
- Save authentication cookies for future use


## Installation

### Prerequisites

- Python 3.6 or higher
- `pip` (Python package manager)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Download the script

Clone this repository or download the files:

```bash
git clone https://github.com/yourusername/tahvel-checker.git
cd tahvel-checker
```

## Usage

### Basic usage

```bash
python main.py
```

This will prompt you to select a study year and journal to check. If you have saved a cookie, it will be used automatically.

### Command-line arguments

```
python main.py [options]

options:
  -h, --help            Show this help message and exit
  -j ID, --journal-id ID
                        Journal ID to check (if not provided, will list all available journals)
  -c COOKIE, --cookie COOKIE
                        Authentication cookie for Tahvel (if not provided, will use saved cookie)
  -s, --save-cookie     Save the provided cookie for future use
  -a, --all-journals    Process all journals for the selected study year
```

### Examples

Check a specific journal:
```bash
python main.py --journal-id 12345 --cookie "your_cookie_value"
```

Save your cookie for future use:
```bash
python main.py --cookie "your_cookie_value" --save-cookie
```

Process all journals in a selected study year:
```bash
python main.py --all-journals
```

## Getting Your Tahvel Cookie

To use this script, you'll need to provide an authentication cookie for Tahvel. Here's how to get it:

1. Log in to your Tahvel account in a web browser
2. Open the browser's developer tools:
   - Chrome/Edge: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)
   - Firefox: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)
   - Safari: Enable Developer menu in preferences, then Safari > Develop > Show Web Inspector
3. Go to the "Application" tab (in Chrome/Edge) or "Storage" tab (in Firefox)
4. Look for "Cookies" in the sidebar and click on the Tahvel domain
5. Find the "JSESSIONID" cookie (or similar authentication cookie)
6. Copy the entire value

When using the script, pass this cookie value using the `--cookie` option.

**Note**: For security reasons, never share this cookie value with anyone as it provides access to your Tahvel account.

## Cookie Storage

When you use the `--save-cookie` flag, the cookie is saved to `~/.tahvel-checker/cookies.pickle` on your system. This allows you to run the script without manually providing the cookie each time.

To clear saved cookies, simply delete this file:

```bash
rm ~/.tahvel-checker/cookies.pickle
```

## Troubleshooting

### Authentication Issues

If you see an error like:
```
HTTP Error: 401 Client Error: Unauthorized for url: ...
Authentication failed. Your cookie may be expired or invalid.
```

Your cookie is likely expired. Get a new cookie from your browser and provide it using the `--cookie` option.

### No Study Years or Journals Found

Make sure:
1. Your cookie is valid
2. You have access to journals in the Tahvel system
3. The selected study year contains journals

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
