# Project Documentation

**Document Owner:** [Insert Name/Title]  
**Date:** [YYYY-MM-DD]  
**Version:** [e.g., 1.0.0]  

---

## 1. PDR (Project Definition Report)

*This section outlines the strategic vision, objectives, and scope of the project before diving into technical details.*

### 1.1 Executive Summary
> **Instructions:** Briefly describe what this project is and why it matters.
**Project Name:** [e.g., Municipal Health Facility Portal]  
**Problem Statement:** [Describe the current pain point. e.g., Manual reconciliation of HR spreadsheets and local database records is time-consuming and prone to inconsistencies.]  
**Proposed Solution:** [High-level description of the solution. e.g., A serverless web form that generates structured change logs for active professionals and facility data.]  

### 1.2 Objectives & Key Results (OKRs)
> **Instructions:** List the measurable goals this project aims to achieve.
* **Objective 1:** [e.g., Standardize data collection across all municipal management nodes.]
  * **KR 1:** [e.g., Achieve 100% compliance with the 7-digit CNES format on all new entries.]
* **Objective 2:** [Insert Objective]
  * **KR 2:** [Insert Key Result]

### 1.3 Scope Definition
> **Instructions:** Clearly define what is included and excluded to prevent scope creep.
**In Scope:**
* [e.g., Web form interface for data entry]
* [e.g., Generation of JSON change logs (Audit Trail)]
* [e.g., Integration with Google Sheets API for log storage]

**Out of Scope:**
* [e.g., Direct write access or automated overwriting of the master postgresql database]
* [e.g., Complex user authentication (SSO) for phase 1]

### 1.4 Target Audience & Stakeholders
* **Primary Users:** [e.g., Facility Managers, Administrative Clerks]
* **Secondary Users/Data Consumers:** [e.g., Data Engineers, HR Department]
* **Key Stakeholders:** [e.g., Secretary of Health, IT Coordination]

---

## 2. Specs (Technical Specifications)

*This section details the architectural choices, data flow, and specific technical requirements necessary to build the solution defined in the PDR.*

### 2.1 System Architecture
> **Instructions:** Outline the tech stack and infrastructure components.
* **Frontend/UI:** Streamlit Community Cloud (Python)
* **State Management:** Event-driven session state for dynamic UI
* **Storage/Database:** * **Read (Source):** Static CSV exports (e.g., `facilities.csv`, `professionals.csv`) updated daily. These files are hosted in a secure Git repository. The web application fetches these files directly from the repository at runtime, ensuring the form uses up-to-date information without requiring a direct connection to the internal municipal database.
  * **Write (Destination):** Centralized Google Sheet via API (for storing generated Change Logs)

### 2.2 Data Models & Schema
> **Instructions:** Define the primary data entities and their expected formats.

#### Entity: `Facility`
| Field Name | Data Type | Validation Rules | Description |
| :--- | :--- | :--- | :--- |
| `cnes` | String | Exactly 7 digits | [e.g., National registry code] |
| `name` | String | Min 3 chars | [e.g., Official establishment name] |
| `phone_number` | String | Valid phone number formmat| [e.g., Official establishment phone number] |
| `contact_email` | String | Valid email regex | [e.g., Official communication channel] |

#### Entity: `Professional`
| Field Name | Data Type | Validation Rules | Description |
| :--- | :--- | :--- | :--- |
| `name` | String | Min 3 chars, Not Null | [e.g., Full registered name] |
| `role` | String | Dropdown predefined | [e.g., Doctor, Nurse, Clerk] |
| `action_flag` | String | CREATE, DELETE, UPDATE | [e.g., Tracks session state changes] |

### 2.3 Application Logic & Validation
> **Instructions:** Describe critical functional rules and workflows.

* **Initialization Workflow:** 1. **Source Data Fetch:** Upon application load, the system retrieves the latest static CSV files from the Git repository and caches them in memory.
  2. **Autocomplete Search:** The user is presented with a dynamic search input field. As the user types, an autocomplete dropdown filters the available facilities and role professionals. The user can search using *either* the 7-digit CNES Facility ID *or* the Facility Name (e.g., typing "1234567" or "Posto de Saúde Central" will yield the same result).
  3. **State Population:** Once a facility is selected from the autocomplete list, the system cross-references the `cnes` with the cached professionals data. The existing roster for that specific facility is then loaded into the temporary Session State.
  4. **UI Render:** The form dynamically renders the establishment's basic data and populates the interface with the current professionals, making it ready for additions, deletions, or updates.

* **Business Rules:**
  * **Duplicate Prevention:** System blocks adding a professional with the exact same name and role in a single session.
  * **Mandatory Justification:** If a user deletes all professionals from a facility, a text explanation is required before submission.

### 2.4 Payload / Output Structure
> **Instructions:** Define the format of the data being passed or saved at the end of the process.
**Change Log JSON Structure:**
```json
{
  "timestamp": "[YYYY-MM-DDTHH:MM:SSZ]",
  "cnes": "[7-digit string]",
  "metadata": {
    "user_ip": "[IP Address]",
    "data_goal": "[User defined reason for change]"
  },
  "modifications": {
    "CREATE": [ {"name": "...", "role": "..."} ],
    "DELETE": [ {"id": "..."} ],
    "UPDATE": { "contact_email": "..." }
  }
}
```

### 2.5 Security & Compliance
> **Instructions:** List any security protocols or compliance standards the project must adhere to.
* [e.g., No direct external exposure of local servers; read-only exports used.]
* [e.g., Compliance with municipal data privacy regulations regarding employee names.]