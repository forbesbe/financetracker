import cleaner
import pandas as pd
import sqlite3

DB_PATH = "tracker.db"
SCHEMA_PATH = "tracker.sql"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    conn.close()

file_path = "expenses_messy.xlsx" # placeholder
df = pd.read_excel(file_path)

def clean_row(row, user_id, source_upload_id):
    try:
        account = cleaner.clean_account(row["Account"])
    except cleaner.RowInvalidError as e:
        raise cleaner.RowInvalidError(status=e.status, message=f"account: {e.message}")
    try:
        date = cleaner.clean_date(row["Date"])
    except cleaner.RowInvalidError as e:
        raise cleaner.RowInvalidError(status=e.status, message=f"date: {e.message}")
    try:
        amount = cleaner.clean_amount(row["Amount"])
    except cleaner.RowInvalidError as e:
        raise cleaner.RowInvalidError(status=e.status, message=f"amount: {e.message}")
    try:
        description = cleaner.clean_description(row["Description"])
    except cleaner.RowInvalidError as e:
        raise cleaner.RowInvalidError(status=e.status, message=f"description: {e.message}")
    try:
        category = cleaner.clean_category(row["Category"])
    except cleaner.RowInvalidError as e:
        raise cleaner.RowInvalidError(status=e.status, message=f"category: {e.message}")
    return {
        "user_id": user_id,
        "date": date,
        "description": description,
        "category": category,
        "amount": amount,
        "account": account,
        "source_upload_id": source_upload_id
    }

user_id = 1 #placeholder
source_upload_id = 1 #placeholder

successful_rows = []
skipped = []

for index, row in df.iterrows():
    try:
        cleaned = clean_row(row, user_id, source_upload_id)
        successful_rows.append(cleaned)
    except cleaner.RowInvalidError as e:
        skipped.append({"raw_row": row, "status": e.status, "message": e.message})

