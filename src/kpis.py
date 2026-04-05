# src/kpis.py
# Calculates summary KPIs from the combined alerts DataFrame.
# These metrics are consumed directly by the Streamlit dashboard.

import pandas as pd

def get_total_alert_count(alerts):
    """
    Returns the total number of alerts across all rules.
    Simple but important headline metric for the dashboard.
    """
    return len(alerts)


def get_alerts_by_rule(alerts):
    """
    Returns a DataFrame with alert counts broken down by rule.
    Used to populate the rule distribution chart in the dashboard.
    """
    return (
        alerts.groupby("rule")["account_id"]
        .count()
        .reset_index()
        .rename(columns={"account_id": "alert_count"})
        .sort_values("alert_count", ascending=False)
    )


def get_total_flagged_amount(alerts):
    """
    Returns the total dollar amount across all flagged alerts.
    Gives a sense of the financial exposure captured by the rule engine.
    """
    return alerts["alert_amount"].sum()


def get_top_accounts(alerts, n=10):
    """
    Returns the top N accounts ranked by alert amount.
    Helps investigators prioritize which accounts to review first.
    """
    return (
        alerts.groupby("account_id")
        .agg(
            total_alert_amount=("alert_amount", "sum"),
            alert_count=("rule", "count"),
            rules_triggered=("rule", lambda x: ", ".join(x.unique()))
        )
        .reset_index()
        .sort_values("total_alert_amount", ascending=False)
        .head(n)
    )


def get_alert_summary(alerts):
    """
    Returns a single dictionary of all KPIs in one call.
    This is the primary entry point used by the Streamlit app.
    """
    return {
        "total_alerts": get_total_alert_count(alerts),
        "alerts_by_rule": get_alerts_by_rule(alerts),
        "total_flagged_amount": get_total_flagged_amount(alerts),
        "top_accounts": get_top_accounts(alerts)
    }