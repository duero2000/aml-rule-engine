# app/streamlit_app.py
# Main entry point for the AML Transaction Monitoring dashboard.
# Run with: streamlit run app/streamlit_app.py from the project root.

import streamlit as st
import pandas as pd
import sys
import os

# Walk up two levels from app/streamlit_app.py to reach the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to path so src/ imports work on Streamlit Cloud
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from src.kpis import get_alert_summary

# Page configuration must be the first Streamlit command called
st.set_page_config(
    page_title="AML Transaction Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the financial terminal aesthetic
st.markdown("""
    <style>
    /* Main background and text */

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0d1526;
        border-right: 1px solid #1e3a5f;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #0d1a2e;
        border: 1px solid #1e3a5f;
        border-radius: 6px;
        padding: 16px;
    }

    /* Metric value color */
    [data-testid="stMetricValue"] {
        color: #f0a500;
        font-family: 'Courier New', monospace;
        font-size: 1.8rem;
    }

    /* Metric label color */
    [data-testid="stMetricLabel"] {
        color: #7a9ab8;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* DataFrame table styling */
    [data-testid="stDataFrame"] {
        border: 1px solid #1e3a5f;
    }

    /* Header text */
    h1, h2, h3 {
        color: #e0e6f0;
        font-family: 'Courier New', monospace;
    }
    </style>
""", unsafe_allow_html=True)

# Maps internal rule names to clean human readable labels for display
RULE_LABELS = {
    "DORMANT_ACTIVITY": "Dormant Activity",
    "VELOCITY_SPIKE": "Velocity Spike",
    "RAPID_MOVEMENT": "Rapid Movement",
    "STRUCTURING": "Structuring"
}

# Velocity spike threshold surfaced once here instead of repeating in every alert row
VELOCITY_THRESHOLD = 955791.02


@st.cache_data
def load_alerts():
    """
    Loads the alerts CSV from the outputs folder.
    Cached so Streamlit only reads the file once per session.
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "outputs", "alerts", "alerts.csv"
    )
    return pd.read_csv(path)


# Sidebar navigation
st.sidebar.title("AML Monitor")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Alerts Explorer"]
)

# Load data and summary
alerts = load_alerts()
summary = get_alert_summary(alerts)


# Overview page
if page == "Overview":
    st.title("Transaction Monitoring Rule Engine")
    st.markdown(
        "<p style='color:#4a6580; font-family:Courier New; font-size:0.95rem;'>"
        "FINANCIAL CRIMES ANALYTICS | PAYSIM SYNTHETIC DATASET</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Row 1: Headline KPI metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Total Alerts Generated",
            value=f"{summary['total_alerts']:,}"
        )

    with col2:
        st.metric(
            label="Total Flagged Amount",
            value=f"${summary['total_flagged_amount']:,.0f}"
        )

    with col3:
        st.metric(
            label="Active Rules",
            value=len(summary['alerts_by_rule'])
        )

    st.markdown("---")

    # Row 2: Alert count broken down by rule as KPI boxes
    st.subheader("Alerts by Rule")
    col4, col5, col6 = st.columns(3)

    alerts_by_rule = summary['alerts_by_rule'].set_index("rule")

    with col4:
        count = int(alerts_by_rule.loc["DORMANT_ACTIVITY", "alert_count"]) if "DORMANT_ACTIVITY" in alerts_by_rule.index else 0
        st.metric(label="Dormant Activity", value=f"{count:,}")

    with col5:
        count = int(alerts_by_rule.loc["RAPID_MOVEMENT", "alert_count"]) if "RAPID_MOVEMENT" in alerts_by_rule.index else 0
        st.metric(label="Rapid Movement", value=f"{count:,}")

    with col6:
        count = int(alerts_by_rule.loc["VELOCITY_SPIKE", "alert_count"]) if "VELOCITY_SPIKE" in alerts_by_rule.index else 0
        st.metric(label="Velocity Spike", value=f"{count:,}")

    st.markdown("---")

    # Velocity spike threshold displayed once here instead of in every alert row
    st.markdown(
        f"<p style='color:#4a6580; font-family:Courier New; font-size:0.95rem;'>"
        f"VELOCITY SPIKE THRESHOLD (95TH PERCENTILE): "
        f"<span style='color:#f0a500;'>${VELOCITY_THRESHOLD:,.2f}</span></p>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Top 10 flagged accounts with clean readable rule labels
    st.subheader("Top 10 Accounts by Flagged Amount")
    top_accounts = summary['top_accounts'].copy()
    top_accounts["rules_triggered"] = top_accounts["rules_triggered"].apply(
        lambda x: ", ".join([RULE_LABELS.get(r.strip(), r.strip()) for r in x.split(",")])
    )
    st.dataframe(top_accounts, use_container_width=True)


# Alerts Explorer page
elif page == "Alerts Explorer":
    st.title("Alerts Explorer")
    st.markdown(
        "<p style='color:#7a9ab8; font-family:Courier New; font-size:0.85rem;'>"
        "DRILL DOWN BY RULE, ACCOUNT, OR AMOUNT</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Sidebar filters for the explorer page
    st.sidebar.markdown("### Filters")

    # Rule filter using clean readable labels
    rule_options = ["All"] + list(RULE_LABELS.values())
    selected_rule_label = st.sidebar.selectbox("Filter by Rule", rule_options)

    # Reverse lookup from label back to raw rule name for filtering
    label_to_rule = {v: k for k, v in RULE_LABELS.items()}

    # Amount range filter
    min_amount = int(alerts["alert_amount"].min())
    max_amount = int(alerts["alert_amount"].max())
    amount_range = st.sidebar.slider(
        "Alert Amount Range",
        min_value=min_amount,
        max_value=max_amount,
        value=(min_amount, max_amount)
    )

    # Account ID search
    account_search = st.sidebar.text_input("Search Account ID")

    # Apply filters to the alerts DataFrame
    filtered = alerts.copy()

    # Apply clean label to the display copy before filtering
    filtered["rule"] = filtered["rule"].map(RULE_LABELS).fillna(filtered["rule"])

    if selected_rule_label != "All":
        filtered = filtered[filtered["rule"] == selected_rule_label]

    filtered = filtered[
        (filtered["alert_amount"] >= amount_range[0]) &
        (filtered["alert_amount"] <= amount_range[1])
    ]

    if account_search:
        # Partial match so users don't need to type exact account IDs
        filtered = filtered[
            filtered["account_id"].str.contains(account_search, case=False)
        ]

    # Show how many alerts are currently visible after filtering
    st.markdown(
        f"<p style='color:#7a9ab8;'>Showing <span style='color:#f0a500;'>"
        f"{len(filtered):,}</span> alerts</p>",
        unsafe_allow_html=True
    )

    # Display the filtered and sorted alerts table
    st.dataframe(
        filtered[[
            "account_id", "rule", "alert_amount",
            "transaction_count", "alert_details"
        ]].sort_values("alert_amount", ascending=False),
        use_container_width=True
    )
