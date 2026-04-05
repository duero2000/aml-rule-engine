#!/usr/bin/env python
# coding: utf-8

# In[1]:


# src/rules.py
# Each function returns a standardized alerts DataFrame with consistent columns
# so all four rules can be combined cleanly in alerts.py
import pandas as pd

# Every rule in this engine returns these exact columns.
# This contract makes combining rules in alerts.py straightforward.
ALERT_COLUMNS = [
    "account_id",        # the flagged sender account
    "rule",              # which rule fired
    "alert_amount",      # the relevant dollar amount for this alert
    "alert_details",     # human readable explanation of why it was flagged
    "transaction_count"  # number of transactions involved in the alert
]

def _filter_aml_types(df):
    """
    Internal helper function used by all four rules.
    Filters the dataset to only TRANSFER and CASH_OUT transaction types,
    which are the only types where fraud occurs in PaySim.
    Prefixed with underscore to signal this is not meant to be called externally.
    """
    aml_types = ["TRANSFER", "CASH_OUT"]
    return df[df["type"].isin(aml_types)].copy()


# In[2]:


def detect_structuring(df, window=72, individual_max=10000, combined_min=10000, min_count=2):
    """
    Detects smurfing behavior: a sender making multiple sub-threshold transactions
    to different destinations within a time window where the combined total exceeds
    the reporting threshold.

    window: number of steps to group transactions into (72 steps = 3 days in PaySim)
    individual_max: each transaction must be below this amount
    combined_min: combined transactions must exceed this amount
    min_count: minimum number of transactions to trigger an alert
    """

    filtered = _filter_aml_types(df)

    # Keep only transactions individually below the reporting threshold
    below_threshold = filtered[filtered["amount"] < individual_max].copy()

    # Assign each transaction to a time window bucket
    below_threshold["window"] = below_threshold["step"] // window

    # Group by sender and window
    grouped = (
        below_threshold.groupby(["nameOrig", "window"])
        .agg(
            transaction_count=("amount", "count"),
            total_amount=("amount", "sum"),
            unique_destinations=("nameDest", "nunique")
        )
        .reset_index()
    )

    # Apply all three smurfing conditions
    flagged = grouped[
        (grouped["transaction_count"] >= min_count) &
        (grouped["total_amount"] >= combined_min) &
        (grouped["unique_destinations"] > 1)
    ].copy()

    # Build standardized output using the ALERT_COLUMNS contract
    flagged["account_id"] = flagged["nameOrig"]
    flagged["rule"] = "STRUCTURING"
    flagged["alert_amount"] = flagged["total_amount"]
    flagged["alert_details"] = (
        "Sender made " + flagged["transaction_count"].astype(str) +
        " sub-threshold transactions totaling $" +
        flagged["total_amount"].round(2).astype(str) +
        " across " + flagged["unique_destinations"].astype(str) +
        " destinations within a 3 day window"
    )

    return flagged[ALERT_COLUMNS]


# In[ ]:


def detect_velocity_spike(df, percentile=95, min_count=2):
    """
    Flags senders whose total transaction amount exceeds the population-level
    95th percentile threshold and who made more than one transaction.

    percentile: the population threshold to flag against
    min_count: sender must have at least this many transactions to be flagged
    """

    filtered = _filter_aml_types(df)

    # Aggregate total amount and transaction count per sender
    sender_agg = (
        filtered.groupby("nameOrig")
        .agg(
            total_amount=("amount", "sum"),
            transaction_count=("amount", "count")
        )
        .reset_index()
    )

    # Calculate the population level threshold
    threshold = sender_agg["total_amount"].quantile(percentile / 100)

    # Flag senders who exceed the threshold and have multiple transactions
    flagged = sender_agg[
        (sender_agg["total_amount"] >= threshold) &
        (sender_agg["transaction_count"] >= min_count)
    ].copy()

    # Build standardized output using the ALERT_COLUMNS contract
    flagged["account_id"] = flagged["nameOrig"]
    flagged["rule"] = "VELOCITY_SPIKE"
    flagged["alert_amount"] = flagged["total_amount"]
    flagged["alert_details"] = (
        "Sender total of $" +
        flagged["total_amount"].round(2).astype(str) +
        " exceeds the 95th percentile threshold of $" +
        f"{threshold:,.2f} across " +
        flagged["transaction_count"].astype(str) +
        " transactions"
    )

    return flagged[ALERT_COLUMNS]


# In[ ]:


def detect_dormant_activity(df, min_gap=30, min_reactivation_amount=50000):
    """
    Flags sender accounts that were dormant for an extended period and then
    reactivated with a large transaction.

    min_gap: minimum number of steps between first and last transaction
             to consider an account dormant (30 steps = 30 hours in PaySim)
    min_reactivation_amount: the first transaction must exceed this amount
                             to trigger an alert
    """

    filtered = _filter_aml_types(df)

    # For each sender find their first and last transaction step
    sender_activity = (
        filtered.groupby("nameOrig")
        .agg(
            first_step=("step", "min"),
            last_step=("step", "max"),
            transaction_count=("amount", "count")
        )
        .reset_index()
    )

    # Calculate the gap between first and last transaction
    sender_activity["step_gap"] = (
        sender_activity["last_step"] - sender_activity["first_step"]
    )

    # Find the amount of each sender's first transaction
    # This represents the reactivation event after the dormant period
    first_transactions = (
        filtered.sort_values("step")
        .groupby("nameOrig")
        .first()
        .reset_index()[["nameOrig", "amount"]]
        .rename(columns={"amount": "first_transaction_amount"})
    )

    # Merge reactivation amount back onto sender activity
    sender_activity = sender_activity.merge(first_transactions, on="nameOrig")

    # Flag senders who meet both dormancy and reactivation conditions
    flagged = sender_activity[
        (sender_activity["step_gap"] >= min_gap) &
        (sender_activity["first_transaction_amount"] >= min_reactivation_amount)
    ].copy()

    # Build standardized output using the ALERT_COLUMNS contract
    flagged["account_id"] = flagged["nameOrig"]
    flagged["rule"] = "DORMANT_ACTIVITY"
    flagged["alert_amount"] = flagged["first_transaction_amount"]
    flagged["alert_details"] = (
        "Account was dormant for " +
        flagged["step_gap"].astype(str) +
        " steps then reactivated with a transaction of $" +
        flagged["first_transaction_amount"].round(2).astype(str)
    )

    return flagged[ALERT_COLUMNS]


# In[ ]:


def detect_rapid_movement(df, max_step_gap=24):
    """
    Detects two-hop transaction chaining where money moves from account A to B,
    then B quickly sends money onward to C within a short time window.
    This reflects layering behavior where funds are moved through intermediary
    accounts to obscure the origin.

    max_step_gap: maximum number of steps allowed between hop 1 and hop 2
                  (24 steps = 24 hours in PaySim)
    """

    filtered = _filter_aml_types(df)

    # Hop 1: all outbound transactions (A sends to B)
    hop1 = filtered[["step", "nameOrig", "nameDest", "amount"]].copy()
    hop1.columns = ["step_1", "account_a", "account_b", "amount_1"]

    # Hop 2: all outbound transactions (B sends to C)
    hop2 = filtered[["step", "nameOrig", "nameDest", "amount"]].copy()
    hop2.columns = ["step_2", "account_b", "account_c", "amount_2"]

    # Join on account_b where B appears as both destination and sender
    chained = hop1.merge(hop2, on="account_b")

    # Keep only cases where hop 2 happens after hop 1
    chained = chained[chained["step_2"] > chained["step_1"]].copy()

    # Keep only cases within our time window
    chained["step_gap"] = chained["step_2"] - chained["step_1"]
    chained = chained[chained["step_gap"] <= max_step_gap].copy()

    # Drop cases where money returns to the original sender
    chained = chained[chained["account_c"] != chained["account_a"]].copy()

    # Build standardized output using the ALERT_COLUMNS contract
    chained["account_id"] = chained["account_a"]
    chained["rule"] = "RAPID_MOVEMENT"
    chained["alert_amount"] = chained["amount_1"]
    chained["alert_details"] = (
        "Account " + chained["account_a"] +
        " sent $" + chained["amount_1"].round(2).astype(str) +
        " to intermediary " + chained["account_b"] +
        " which forwarded funds to " + chained["account_c"] +
        " within " + chained["step_gap"].astype(str) + " steps"
    )
    chained["transaction_count"] = 2

    return chained[ALERT_COLUMNS]

