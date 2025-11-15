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
│   └── create_fact_consumption_daily_new_ver_temp.sql
├── python/                       # Python scripts for data updates
├── *_dashboard.py               # Streamlit dashboard (to be created)
├── requirements.txt             # Python dependencies (to be created)
├── README.md                    # This file
├── RACE_PROJECT_LEARNINGS.md    # Key learnings from Race project
├── QUICK_REFERENCE.md           # Quick code snippets
└── FACT_CONSUMPTION_DAILY_DOCUMENTATION.md  # Consumption table docs
```

## Data Tables

### fact_consumption_daily_new_ver_temp

**Purpose**: Documents credits inflow and outflow by source

**Granularity**: `date`, `distinct_id`, `source` (mp_event_name)

**Key Features**:
- Tracks both inflow (rewards) and outflow (spending)
- Source-level breakdown (each event type is a separate row)
- Enriched with player dimensions (chapter, payment flags, country, version)
- Daily aggregation with 7-day rolling window

**Documentation**: See `FACT_CONSUMPTION_DAILY_DOCUMENTATION.md`

---

## Key Learnings Reference

See `RACE_PROJECT_LEARNINGS.md` for comprehensive patterns, best practices, and solutions from the Race project.

## Data Documentation

- **main data documentation.pdf**: Complete data documentation for event schema, fields, and business logic
- **FACT_CONSUMPTION_DAILY_DOCUMENTATION.md**: Documentation specific to the consumption table

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
