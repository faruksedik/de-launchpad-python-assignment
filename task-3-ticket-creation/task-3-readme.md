# Jira Automated Request Creation Pipeline

## Project Overview

This project automates the **creation of Jira Service Desk requests** directly from database rows.  
It eliminates the need for manual ticket creation by integrating Jira’s REST API with a Postgres database.

Each run fetches new data, validates it, maps it to Jira form fields, and automatically creates Jira requests.  
The system is designed with **incremental data processing**, **error tracking**, and **field mapping intelligence**.

---

## Key Features

- **Incremental Processing:** Only processes new rows since the last successful run.
- **Dynamic Field Mapping:** Reads Jira form definitions dynamically — no hardcoded field IDs.
- **Choice Normalization:** Correctly maps labels even when DB entries have inconsistent casing or spacing.
- **Validation Logic:** Ensures temporary requests contain valid date ranges before creating tickets.
- **Automatic Tracking:** Maintains a JSON state file (`tracking.json`) to prevent duplicate processing.
- **Robust Logging:** Captures successes, failures, and warnings for audit and debugging.

---

## Project Architecture

```
/task-3-ticket-creation
│
├── main.py                 # Main entry point that coordinates the full pipeline execution
├── config.py               # Project configuration constants (Jira IDs, DB settings, tokens, etc.)
├── db_helpers.py           # Functions to connect & fetch candidate rows from Postgres DB
├── form_mapping.py         # Extract Jira form questions & build choice mappings
├── jira_helpers.py         # Handles Jira Cloud REST API calls (create tickets, fetch form json)
├── mappers.py              # Field mapping logic that converts DB values → Jira expected formats
├── processors.py           # Processes each DB row, validation & triggers jira ticket creation
├── transformer.py          # Data normalization & transformation utilities
├── state_manager.py        # Reads & writes state (tracking.json) consistently
├── tracking_manager.py     # Higher level helper for updating tracking state safely
├── tracking.json           # Persistent tracking state file for incremental processing
├── logging_config.py       # Central logging setup
├── requirements.txt        # Python dependencies list
├── ticket_processor.log    # Run output logs (debug / audit)
└── README.md
```

## How It Works

### 1. Load Tracking State

The pipeline begins by reading the `tracking.json` file.  
This file keeps track of:
- The **last run date**
- Already processed **emails**
- **Flagged requests** (validation errors)
- **Email to issue mapping**

### 2. Fetch Jira Form Definition

The function `fetch_form_definition_cloud()` retrieves the latest form configuration from Jira Cloud.  
This allows the system to understand what questions and fields exist in the form dynamically.

### 3. Build Helper Mappings

- `extract_questions_from_form()` extracts form question data.
- `build_choice_label_to_id_map()` builds a dictionary of normalized labels to Jira choice IDs.

### 4. Read Candidate Rows

`fetch_rows_on_or_after()` retrieves database rows created after the last recorded run date.

### 5. Apply Filtering

`filter_rows_for_processing()` ensures only new and valid rows are processed — avoiding reprocessing of old or duplicate entries.

### 6. Process Each Row

Each row goes through:
- **Validation:** Ensures timeframe and date logic are correct.
- **Mapping:** Converts DB fields into Jira form-compatible structures.
- **Submission:** Creates a Jira request using `create_request_on_jira()`.

### 7. Update Tracking

After each row is processed successfully:
- The tracking file is updated with new issue keys.
- Emails processed today are logged to prevent duplication.

### 8. Finalize Run

At the end of the process:
- The last run date is updated to today’s date.
- The updated tracking state is saved to disk.

---

## Tracking File Structure

Example `tracking.json`:

```json
{
  "last_run_date": "2025-11-09",
  "processed_emails_same_date": ["john.doe@company.com"],
  "email_to_issue": {
    "john.doe@company.com": "CJP-10234"
  },
  "flagged_requests": {
    "jane.doe@company.com": "Invalid timeframe: temporary"
  }
}
```

This file is automatically updated after each successful run.

---

## Example Workflow

1. **New form submissions** arrive in the Postgres database.
2. The script checks `tracking.json` to determine the last processed record.
3. Jira form definition is fetched dynamically.
4. Each unprocessed record is mapped and validated.
5. Valid rows are sent to Jira via API.
6. Jira issues are created automatically.
7. Tracking file is updated for the next run.

---

## Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

| Variable | Description |
|-----------|-------------|
| POSTGRES_HOST | Database host |
| POSTGRES_DB | Database name |
| POSTGRES_USER | Database user |
| POSTGRES_PASSWORD | Database password |
| JIRA_USER | Jira email |
| JIRA_API_TOKEN | Jira API token |
| CLOUD_ID | Jira Cloud ID |
| SERVICE_DESK_ID | Jira Service Desk ID |
| REQUEST_TYPE_ID | Jira Request Type ID |

> For learning purposes, you may hardcode credentials directly in code.

### 3. Run the pipeline
```bash
python main.py
```

---

## Logging Example

```
INFO - Starting run. last_run_date=2025-11-08
INFO - Fetching Jira form definition...
INFO - Processing row for john.doe@company.com
INFO - Created Jira request SD-10234
INFO - Run complete.
```

---

## Future Improvements

- Store tracking state in a database instead of JSON.
- Send notifications for flagged rows.
- Containerize with Docker for easier deployment.

---

## Author

**Faruk Sedik**  
Data Engineer

---

## Summary

This pipeline delivers a **fully automated Jira request creation system**, leveraging dynamic form parsing, data validation, and persistent tracking.  
It replaces slow, error-prone manual processes with a reliable, production-ready automation pipeline.
