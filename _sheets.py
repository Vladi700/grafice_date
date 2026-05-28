"""Helper for reading Google Sheets as CSV via public export."""

import pandas as pd


def read_sheet(spreadsheet_id: str, gid: str) -> pd.DataFrame:
    """Read a Google Sheet tab as CSV. Sheet must be public (Anyone with link can view)."""
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    return pd.read_csv(url)
