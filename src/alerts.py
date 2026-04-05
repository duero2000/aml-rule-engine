# src/alerts.py
# Combines all four rule outputs into a single standardized alerts DataFrame
# and saves it to outputs/alerts/ for use in the Streamlit dashboard.

import pandas as pd
import os
from src.rules import (
    detect_structuring,
    detect_velocity_spike,
    detect_dormant_activity,
    detect_rapid_movement
)

def generate_alerts(df):
    """
    Runs all four AML rules against the input DataFrame and combines
    the results into a single alerts DataFrame.
    """

    # Run each rule and collect the results in a list
    rule_outputs = [
        detect_structuring(df),
        detect_velocity_spike(df),
        detect_dormant_activity(df),
        detect_rapid_movement(df)
    ]

    # Combine all rule outputs into one DataFrame
    alerts = pd.concat(rule_outputs, ignore_index=True)

    return alerts


def save_alerts(alerts, output_path=None):
    """
    Saves the combined alerts DataFrame to a CSV file.
    Anchors the output path to the location of this file using pathlib,
    which handles Windows path resolution more reliably than os.path.
    """
    from pathlib import Path

    # Path(__file__) points to src/alerts.py
    # .parent gives us src/
    # .parent again gives us the project root
    project_root = Path(__file__).resolve().parent.parent

    if output_path is None:
        output_path = project_root / "outputs" / "alerts" / "alerts.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving to: {output_path}")
    alerts.to_csv(output_path, index=False)
    print(f"Alerts saved successfully. Total alerts: {len(alerts)}")


def run_alert_pipeline(df):
    """
    End to end function that generates and saves alerts in one call.
    This is the primary entry point used by the Streamlit app and notebooks.
    """

    alerts = generate_alerts(df)
    save_alerts(alerts)

    return alerts