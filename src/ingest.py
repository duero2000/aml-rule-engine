# src/ingest.py
# Reusable ingestion module for the AML Rule Engine
# Called by the Streamlit app and any downstream scripts

import pandas as pd
import sqlite3
from pathlib import Path

# Central path configuration — all paths are defined once here
# Using Path() keeps this portable across operating systems
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "paysimdataset.csv"
DB_PATH = DATA_DIR / "aml_engine.db"

# Only TRANSFER and CASH_OUT carry fraud signal in PaySim
# Established during EDA in 01_ingest_and_explore.ipynb
AML_RELEVANT_TYPES = ['TRANSFER', 'CASH_OUT']

def load_raw_data(csv_path: Path = CSV_PATH) -> pd.DataFrame:
    """
    Load the raw PaySim CSV into a DataFrame.
    Returns the full unfiltered dataset.
    """
    # Verify the file exists before attempting to load
    # Fails loudly with a clear message rather than a cryptic pandas error
    if not csv_path.exists():
        raise FileNotFoundError(f"PaySim CSV not found at: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"[ingest] Loaded {len(df):,} rows from {csv_path.name}")
    return df


def filter_aml_relevant(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter raw PaySim data to AML-relevant transaction types only.
    Retains TRANSFER and CASH_OUT — the only types with confirmed fraud signal.
    Established in EDA: Cell 3 of 01_ingest_and_explore.ipynb
    """
    # Apply the type filter established during EDA
    aml_df = df[df['type'].isin(AML_RELEVANT_TYPES)].copy()
    
    print(f"[ingest] Filtered to {len(aml_df):,} AML-relevant rows "
          f"({len(aml_df)/len(df)*100:.1f}% of total)")
    
    return aml_df

def write_to_sqlite(df: pd.DataFrame, db_path: Path = DB_PATH) -> None:
    """
    Write the AML-filtered DataFrame to SQLite.
    Creates the database file if it does not exist.
    """
    # Ensure the data/ directory exists before writing
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    # Write to 'transactions' table — replace on each run to avoid duplicates
    df.to_sql(
        name='transactions',
        con=conn,
        if_exists='replace',
        index=False
    )
    
    # Verify write success by reading count back out
    row_count = pd.read_sql(
        "SELECT COUNT(*) as total FROM transactions", conn
    ).values[0][0]
    
    conn.close()
    print(f"[ingest] Wrote {row_count:,} rows to {db_path.name}")


def load_from_sqlite(db_path: Path = DB_PATH) -> pd.DataFrame:
    """
    Load the transactions table from SQLite into a DataFrame.
    Used by rules.py and the Streamlit app instead of reloading the CSV.
    """
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at: {db_path}. Run ingest pipeline first."
        )
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()
    
    print(f"[ingest] Loaded {len(df):,} rows from {db_path.name}")
    return df


def run_ingest_pipeline() -> pd.DataFrame:
    """
    Full ingestion pipeline: load, filter, and write to SQLite.
    Returns the filtered DataFrame for immediate downstream use.
    Call this once to initialize the database.
    """
    print("[ingest] Starting ingestion pipeline...")
    
    # Step 1: load raw CSV
    df_raw = load_raw_data()
    
    # Step 2: filter to AML-relevant types only
    df_aml = filter_aml_relevant(df_raw)
    
    # Step 3: persist to SQLite
    write_to_sqlite(df_aml)
    
    print("[ingest] Pipeline complete.")
    return df_aml


# Allow ingest.py to be run directly from the command line
# This lets us reinitialize the database without opening a notebook
if __name__ == "__main__":
    run_ingest_pipeline()