# Consumption Analytics Project

**Purpose**: Analytics solution for consumption data using patterns and best practices from the Race project.

---

## Project Status

🚧 **In Development** - Project initialized, ready for development

---

## Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud SDK (`gcloud`)
- BigQuery access to project dataset

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth application-default login
   ```

3. **Configure project**:
   - Update `PROJECT_ID`, `DATASET_ID` in configuration
   - Set up BigQuery credentials

---

## Project Structure

```
Consumption/
├── sql/                          # SQL queries and table definitions
├── python/                       # Python scripts for data updates
├── *_dashboard.py               # Streamlit dashboard (to be created)
├── requirements.txt             # Python dependencies (to be created)
├── README.md                    # This file
└── RACE_PROJECT_LEARNINGS.md    # Key learnings from Race project
```

---

## Key Learnings Reference

See `RACE_PROJECT_LEARNINGS.md` for comprehensive patterns, best practices, and solutions from the Race project.

### Key Patterns to Apply

- ✅ Multi-method BigQuery authentication
- ✅ Optimized SQL with combined CTEs
- ✅ Streamlit dashboard with filters and dimensions
- ✅ Comprehensive documentation
- ✅ Incremental update patterns
- ✅ Error handling and user experience

---

## Next Steps

1. Define data model and tables
2. Create SQL queries
3. Build Streamlit dashboard
4. Set up deployment
5. Add documentation

---

**Project Started**: January 2025  
**Based on**: Race Event Analytics Project
