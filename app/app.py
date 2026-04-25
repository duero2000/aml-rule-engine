# app/app.py
# Main entry point for the AML Transaction Monitoring dashboard.
# Run with: streamlit run app/app.py from the project root.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

# Walk up two levels from app/app.py to reach the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to path so src/ imports work on Streamlit Cloud
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.kpis import get_alert_summary

# Page configuration must be the first Streamlit command called
st.set_page_config(
    page_title="AML Transaction Monitor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for the financial terminal aesthetic
st.markdown("""
    <style>
    /* Sidebar styling — medium navy */
    [data-testid="stSidebar"] {
        background-color: #2a3f5f;
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

# One sentence descriptions for each rule shown as modal popups on the Alerts Explorer page
RULE_DESCRIPTIONS = {
    "Structuring": (
        "Flags accounts that split large sums into multiple sub-threshold transactions "
        "across different destinations within a 72 hour window. "
        "Produces zero alerts in this dataset due to a known PaySim data limitation — "
        "the synthetic data does not simulate intentional structuring behavior."
    ),
    "Velocity Spike": (
        "Flags senders whose total transaction amount exceeds the 95th percentile "
        "of the full population, indicating an abnormal volume of outgoing funds. "
        "Population threshold is $955,791."
    ),
    "Dormant Activity": (
        "Flags accounts that go silent for 30 or more time steps and then reactivate "
        "with a transaction above $50,000, a pattern consistent with dormant shell account behavior."
    ),
    "Rapid Movement": (
        "Flags two hop transaction chains where funds move from account A to intermediary B, "
        "which then forwards to a new account C within 24 hours, "
        "a pattern consistent with layering in money laundering typologies."
    )
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


# st.dialog turns a function into a modal popup triggered by a button click
# Each rule gets its own dialog function so they render independently
@st.dialog("Structuring")
def dialog_structuring():
    st.write(RULE_DESCRIPTIONS["Structuring"])

@st.dialog("Velocity Spike")
def dialog_velocity_spike():
    st.write(RULE_DESCRIPTIONS["Velocity Spike"])

@st.dialog("Dormant Activity")
def dialog_dormant_activity():
    st.write(RULE_DESCRIPTIONS["Dormant Activity"])

@st.dialog("Rapid Movement")
def dialog_rapid_movement():
    st.write(RULE_DESCRIPTIONS["Rapid Movement"])


def build_alert_count_chart(filtered_df):
    """
    Builds a Plotly horizontal bar chart showing alert counts per rule.
    Uses the filtered DataFrame so the chart responds to sidebar filters.
    """
    # Count alerts per rule from the already-labeled filtered DataFrame
    rule_counts = (
        filtered_df.groupby("rule")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=True)  # Ascending so largest bar is at top
    )

    fig = go.Figure(go.Bar(
        x=rule_counts["count"],
        y=rule_counts["rule"],
        orientation="h",                # Horizontal bars read more cleanly for rule names
        marker_color="#f0a500",         # Gold accent to match the metric card values
        marker_line_color="#1e3a5f",    # Navy border on each bar
        marker_line_width=1,
        text=rule_counts["count"],      # Show count as label on each bar
        textposition="outside",         # Place count outside the bar end
        textfont=dict(color="#f0a500", family="Courier New")
    ))

    fig.update_layout(
        plot_bgcolor="#0d1a2e",         # Dark navy background matching metric cards
        paper_bgcolor="#0d1a2e",
        font=dict(color="#7a9ab8", family="Courier New"),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False        # Count labels on bars make axis ticks redundant
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color="#c0cde0", size=12)
        ),
        margin=dict(l=20, r=60, t=30, b=20),
        height=220
    )

    return fig


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
        "<p style='font-family:Courier New; font-size:0.95rem;'>"
        "FINANCIAL CRIMES ANALYTICS | PAYSIM SYNTHETIC DATASET</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Project description — no hardcoded color so it follows Streamlit's active theme
    st.markdown(
        "<p style='font-family:Courier New; font-size:0.95rem; line-height:1.7;'>"
        "This dashboard simulates a production AML transaction monitoring system built on the PaySim "
        "synthetic dataset, which contains over 6 million mobile money transactions. "
        "Four detection rules scan for structuring, velocity spikes, dormant account reactivation, "
        "and rapid fund movement between accounts. "
        "All 1,679 alerts shown are generated programmatically from rule logic applied to raw transaction data."
        "</p>",
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
        f"<p style='font-family:Courier New; font-size:0.95rem;'>"
        f"VELOCITY SPIKE THRESHOLD (95TH PERCENTILE): "
        f"<span style='color:#f0a500;'>${VELOCITY_THRESHOLD:,.2f}</span></p>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # Top 10 flagged accounts with subheader and explanatory caption
    st.subheader("Top 10 Accounts by Total Flagged Amount")
    st.caption("Ranked by combined alert amount across all triggered rules.")

    top_accounts = summary['top_accounts'].copy()
    top_accounts["rules_triggered"] = top_accounts["rules_triggered"].apply(
        lambda x: ", ".join([RULE_LABELS.get(r.strip(), r.strip()) for r in x.split(",")])
    )
    # hide_index removes the default numeric index column from the display
    st.dataframe(top_accounts, use_container_width=True, hide_index=True)


# Alerts Explorer page
elif page == "Alerts Explorer":
    st.title("Alerts Explorer")
    st.markdown(
        "<p style='font-family:Courier New; font-size:0.85rem;'>"
        "DRILL DOWN BY RULE, ACCOUNT, OR AMOUNT</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Four buttons across the page, one per rule
    # Clicking a button calls its dialog function which opens a modal popup
    rule_col1, rule_col2, rule_col3, rule_col4 = st.columns(4)

    with rule_col1:
        if st.button("Structuring", use_container_width=True):
            dialog_structuring()

    with rule_col2:
        if st.button("Velocity Spike", use_container_width=True):
            dialog_velocity_spike()

    with rule_col3:
        if st.button("Dormant Activity", use_container_width=True):
            dialog_dormant_activity()

    with rule_col4:
        if st.button("Rapid Movement", use_container_width=True):
            dialog_rapid_movement()

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

    # hide_index removes the default numeric index column from the display
    st.dataframe(
        filtered[[
            "account_id", "rule", "alert_amount",
            "transaction_count", "alert_details"
        ]].sort_values("alert_amount", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    # Alert count bar chart built from the filtered DataFrame
    # Chart updates automatically when sidebar filters change
    st.subheader("Alert Count by Rule")
    st.caption("Reflects current filter selection.")
    st.plotly_chart(
        build_alert_count_chart(filtered),
        use_container_width=True
    )