# MindFuel ZenQuotes Email Automation Project

## Overview

MindFuel is an automated email delivery platform designed to send motivational quotes to subscribed users daily or weekly using the **ZenQuotes API**.  
It fetches quotes, sends personalized emails, logs results in a PostgreSQL database, and provides an automated summary report to the administrator.

---

## Features

- Fetches motivational quotes from **ZenQuotes API**
- Sends **daily** and **weekly** quotes to subscribers
- Retries failed email sends using **exponential backoff**
- Logs email activity and status in **PostgreSQL**
- Sends **daily performance summary** to admin
- Modularized architecture with strong logging and error handling

---

## Project Structure

```
mindfuel/
│
├── main.py                # Application entry point (fetch + send + summary)
├── db.py                  # Database operations (PostgreSQL)
├── quotes.py              # Fetch and manage motivational quotes
├── email_sender.py        # Email delivery and retry logic
├── logger_config.py       # Logging setup (console + file logs)
├── config.py              # Configuration file (credentials & constants)
├── requirements.txt       # Important Dependecies
├── logs/                  # Log files directory
│   └── app.log
└── README.md              # Project documentation
```

---

## Setup Instructions

### 1. Prerequisites

- Python 3.10+  
- PostgreSQL running locally or on a server  
- SMTP credentials (e.g., Gmail App Password if using Gmail)

### 2. Clone the Repository

```bash
git clone https://github.com/yourusername/mindfuel-zenquotes.git
cd mindfuel-zenquotes
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`config.py`)

Update your `config.py` file with the following parameters:

```python
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "mindfuel_db"
PG_USER = "postgres"
PG_PASSWORD = "your_password"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"

FROM_EMAIL = "your_email@gmail.com"
ADMIN_EMAIL = "admin_email@gmail.com"

ZEN_QUOTES_URL = "https://zenquotes.io/api/quotes"
EMAIL_MAX_RETRIES = 3
EMAIL_RETRY_BASE_SECONDS = 2

users_from_database = [
    {"email": "user@email.com", "name": "John", "subscription_status": "active", "email_frequency": "daily"},
    {...},
    {...}
]
```

---

## Database Setup

### Initialize the Database and Tables

Run this **once** to create required tables and add users:

```bash
python main.py
```

In `main.py`, **uncomment** this line before running:

```python
setup_users()
```

It will:
- Create tables (`users`, `email_logs`)
- Insert predefined users from `config.py`

After setup, **comment it back** to avoid re-inserting users.

---

## Running the Quote Dispatch

Once your database and users are set up:

```bash
python main.py
```

The `run_quote_dispatch()` workflow will:

1. Fetch quotes from ZenQuotes API  
2. Send emails to **daily** and **weekly** subscribers  
3. Log all deliveries (success/failure) in the database  
4. Send a **summary email** to the admin  

---
## Automated Daily Scheduling (Local PC / Server)

### Windows Task Scheduler (Daily at 7AM)

PowerShell command:

```powershell
schtasks /create /sc daily /tn "MindFuelDaily" /tr "C:\Users\<your_user>\AppData\Local\Programs\Python\Python311\python.exe C:\Users\USER\Documents\de-launchpad\launchpad-python-projects\task-1-mind-fuel-app\main.py" /st 07:00
```

### Linux Cron Job (Daily at 9AM)

```bash
crontab -e
```

Add:

```bash
0 7 * * * /usr/bin/python3 /home/path/to/the/script/main.py >> /home/path/to/the/logs/cron.log 2>&1
```

---

## Logging

All logs are stored in `logs/app.log` with rotation (max 5 MB per file).  
Logs include timestamps, function names, levels, and detailed tracebacks for errors.

Example Log Entry:

```
2025-10-31 12:41:39,129 - INFO - db - (log_email) - Email log created for 'user@example.com' (status=sent, attempt=1). Log ID: 2
```

---

## Key Functions

### `fetch_quotes()`
Fetches motivational quotes from ZenQuotes API with full error handling for:
- Network timeouts
- JSON parsing issues
- API downtime

### `send_email_with_retries()`
Sends email with **retry + exponential backoff**, handling:
- SMTP auth errors
- Temporary network issues
- Recipient rejection

### `log_email()`
Stores detailed logs of all delivery attempts.

### `send_summary_to_admin()`
Sends a formatted daily report to admin showing:
- Total emails sent
- Failed deliveries
- Success rate

---

## Example Output

When successful, the console/logs will show:

```
INFO - quotes - Fetched 20 quotes successfully from ZenQuotes API.
INFO - email_sender - Found 5 eligible daily subscribers.
INFO - email_sender - Email sent successfully to user@example.com (attempt 1).
INFO - email_sender - Summary email successfully sent to admin admin_email@gmail.com
```

---

## Troubleshooting

| Issue | Possible Cause | Fix |
|-------|----------------|-----|
| No quotes fetched | ZenQuotes API downtime or network issue | Try again later or check internet connection |
| Emails not sending | Wrong SMTP credentials or port | Verify credentials and Gmail app password |

---

## Author
**Faruk Sedik**  
Data Engineer

---

## License
This project is licensed under the MIT License — free to use and modify.
