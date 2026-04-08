# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CnesForms** is a Streamlit web application for managing Brazilian health facility data (CNES — Cadastro Nacional de Estabelecimentos de Saúde). It allows municipal health administrators to view, add, update, and delete professionals associated with a facility, then submit a structured JSON change log to Google Sheets.

The full project spec is in `CNESform.md`.

## Tech Stack

- **Language:** Python
- **UI Framework:** Streamlit (hosted on Streamlit Community Cloud)
- **Data Source (read):** Static CSV files (`facilities.csv`, `professionals.csv`) fetched from a Git repository at runtime
- **Data Destination (write):** Google Sheets via API (change log storage)
- **State:** Streamlit `st.session_state` (event-driven, ephemeral)

## Commands

Once the Python environment is set up:

```bash
# Run the app locally
streamlit run app.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Data Flow

1. On load, fetch CSV files from the Git repo URL into memory (cached via `@st.cache_data`)
2. User searches for a facility by CNES ID (7 digits) or name — autocomplete filters the CSV
3. Selecting a facility loads its current professionals into `st.session_state`
4. User makes modifications (CREATE / DELETE / UPDATE actions on professionals)
5. On submit, the app generates a JSON change log payload and appends it to Google Sheets

### Key Business Rules

- **Facility lookup:** Search must accept both the 7-digit CNES ID and the facility name interchangeably
- **Duplicate prevention:** Blocks adding a professional with the same name + role in a single session
- **Mandatory justification:** If all professionals are removed from a facility, a text reason is required before submission

### Change Log Payload Shape

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "facility_id": "7-digit string"
  "metadata": {
    "user_ip": "...",
    "data_goal": "user-entered reason"
  },
  "modifications": {
    "CREATE": [{"name": "...", "role": "..."}],
    "DELETE": [{"id": "..."}],
    "UPDATE": {"contact_email": "..."}
  }
}
```

### Data Models

**Facility:** `cnes` (7-digit string), `name`, `contact_email`

**Professional:** `name`, `role` (predefined dropdown), `action_flag` (CREATE | DELETE | UPDATE)
