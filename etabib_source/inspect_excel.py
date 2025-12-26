import pandas as pd
import os

file_path = '/home/server/PycharmProjects/etabibstore_docker/drugs/updates_official/NOMENCLATURE-VERSION-NOVEMBRE-2025.xlsx'

try:
    # Load the Excel file
    xl = pd.ExcelFile(file_path)
    print(f"Sheet names: {xl.sheet_names}")

    # Inspect each sheet
    for sheet in xl.sheet_names:
        print(f"\n--- Sheet: {sheet} ---")
        df = xl.parse(sheet, nrows=5)
        print(df.columns.tolist())
        print(df.head())

except Exception as e:
    print(f"Error reading file: {e}")
