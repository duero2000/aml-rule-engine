# AML Transaction Monitoring Rule Engine

## Background

This project is part of an ongoing effort to deepen my technical foundation in financial crimes analytics. My prior work spans account takeover detection, enterprise fraud classification, and fraudulent application scoring across academic and consulting engagements. This project shifts that focus toward the BSA/AML space, specifically the rule-based transaction monitoring layer that sits at the front of most financial crimes programs.

The goal was to build something production-informed: a rule engine grounded in real AML typologies, designed the way an actual monitoring system would be designed, and honest about the limitations of the data it runs on.

---

## Project Overview

A Python-based AML transaction monitoring rule engine built on the PaySim synthetic banking dataset. The engine detects four suspicious activity typologies, generates a structured alert output, and surfaces findings through a Streamlit dashboard designed for analyst review.

The stack is Python, SQLite, Jupyter, and Streamlit.

---

## Repo Structure

```
aml-rule-engine/
├── data/                         # PaySim CSV and SQLite database
├── notebooks/
│   ├── 01_ingest_and_explore.ipynb   # Data ingestion and full EDA
│   └── 02_rule_development.ipynb     # Rule prototyping and design decisions
├── src/
│   ├── ingest.py                 # Reusable data ingestion pipeline
│   ├── rules.py                  # Four AML detection rule functions
│   ├── alerts.py                 # Alert generation and CSV export pipeline
│   └── kpis.py                   # KPI aggregation for the dashboard
├── app/
│   └── streamlit_app.py          # Two page Streamlit dashboard
├── outputs/
│   └── alerts/
│       └── alerts.csv            # Generated alert output
├── requirements.txt
└── README.md
```

---

## The Four AML Rules

### 1. Structuring
Detects smurfing behavior where a sender makes multiple sub-threshold transactions to different destinations within a 72 hour window, with a combined total exceeding $10,000.

**Design note:** Standard structuring detection looks for repeated transactions in the $9,000 to $10,000 band. PaySim does not simulate this behavior, so almost no senders repeat in that range. I adapted the rule to target smurfing instead, which is methodologically consistent with real AML frameworks and actually detectable in the dataset. The rule is documented as producing minimal alerts due to this known PaySim limitation.

### 2. Velocity Spike
Flags senders whose aggregate transaction amount exceeds the 95th percentile of the population and who made more than one transaction.

**Design note:** My original approach used individual sender baselines. EDA revealed that the majority of PaySim senders make exactly one transaction, making personal baseline comparisons impossible. I pivoted to a population-level peer comparison, which mirrors how real AML systems handle thin-file customers. The 95th percentile threshold came out to $955,791.

### 3. Dormant Account Activity
Flags sender accounts with a large gap between their first and last transaction that reactivate with a high-value transaction.

**Design note:** A gap of 30 or more steps combined with a reactivation transaction above $50,000 was used as the threshold. This reflects the real AML signal of an account sitting idle then suddenly moving significant funds, which is a common indicator in money mule and layering cases.

### 4. Rapid Movement
Detects two-hop transaction chaining where account A sends funds to intermediary account B, which then forwards funds to a new account C within 24 hours.

**Design note:** The original design flagged senders making multiple transactions within a single hour. EDA showed PaySim senders rarely do this, so the signal was flat. I pivoted to chain detection, which better reflects the layering behavior that rapid movement rules are actually designed to catch.

---

## Alert Output

All four rules produce a standardized alert DataFrame with the following columns:

| Column | Description |
|---|---|
| account_id | The flagged sender account |
| rule | Which rule fired |
| alert_amount | The relevant dollar amount for this alert |
| alert_details | Human readable explanation of the flag |
| transaction_count | Number of transactions involved |

**Alert counts from the current run:**

| Rule | Alerts |
|---|---|
| Dormant Activity | 1,261 |
| Velocity Spike | 228 |
| Rapid Movement | 190 |
| Structuring | 0 (documented limitation) |
| **Total** | **1,679** |

---

## Dashboard

The Streamlit dashboard has two pages.

**Overview** surfaces headline KPIs including total alert count, total flagged amount, active rule count, per-rule alert breakdowns, the velocity spike population threshold, and a top 10 accounts table.

**Alerts Explorer** provides a filterable view of all alerts with filters for rule type, alert amount range, and account ID search.

To run the dashboard from the project root:

```bash
streamlit run app/streamlit_app.py
```

---

## Dataset

PaySim is a synthetic financial dataset simulating mobile money transactions. It was generated using real transaction logs from a mobile money service and is commonly used in fraud and AML research.

Source: [PaySim on Kaggle](https://www.kaggle.com/datasets/ealaxi/paysim1)

**Known limitations:** PaySim does not simulate intentional structuring behavior, personal transaction baselines are unreliable due to low per-sender transaction counts, and all fraud is confined to TRANSFER and CASH_OUT transaction types. Rule parameters and design decisions were adapted to reflect what the dataset can actually support.

---

## Setup

```bash
# Create and activate environment
conda create -n aml-engine python=3.11
conda activate aml-engine

# Install dependencies
pip install -r requirements.txt

# Run ingestion pipeline
python src/ingest.py

# Generate alerts
python -c "
import sqlite3, pandas as pd
from src.alerts import run_alert_pipeline
conn = sqlite3.connect('data/aml_engine.db')
df = pd.read_sql('SELECT * FROM transactions', conn)
run_alert_pipeline(df)
"

# Launch dashboard
streamlit run app/streamlit_app.py
```
