import cleaner
import pandas as pd
import sqlite3
import json
import sqlite3
from datetime import datetime

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

init_db()

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

def process_upload(file_path, user_id):
    df = pd.read_excel(file_path)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO uploads (user_id, filename, uploaded_at, rows_total, rows_inserted, rows_skipped_duplicate, rows_skipped_invalid)
        VALUES (?, ?, ?, ?, 0, 0, 0)
    """, (user_id, file_path, datetime.now().isoformat(), len(df)))
    source_upload_id = cursor.lastrowid

    rows_inserted = 0
    rows_skipped_duplicate = 0
    rows_skipped_invalid = 0

    for index, row in df.iterrows():
        try:
            cleaned = clean_row(row, user_id, source_upload_id)
        except cleaner.RowInvalidError as e:
            cursor.execute("""
                INSERT INTO skipped_rows (upload_id, raw_row, status, message)
                VALUES (?, ?, ?, ?)
            """, (source_upload_id, json.dumps(row.to_dict(), default=str), e.status, e.message))
            rows_skipped_invalid += 1
            continue

        try:
            cursor.execute("""
                INSERT INTO transactions (user_id, date, description, category, amount, account, source_upload_id)
                VALUES (:user_id, :date, :description, :category, :amount, :account, :source_upload_id)
            """, cleaned)
            rows_inserted += 1
        except sqlite3.IntegrityError:
            rows_skipped_duplicate += 1

    cursor.execute("""
        UPDATE uploads
        SET rows_inserted = ?, rows_skipped_duplicate = ?, rows_skipped_invalid = ?
        WHERE id = ?
    """, (rows_inserted, rows_skipped_duplicate, rows_skipped_invalid, source_upload_id))

    conn.commit()
    conn.close()

    return source_upload_id

'''conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("""
    INSERT OR IGNORE INTO users (id, username, email_address, password, salt)
    VALUES (1, 'testuser', 'test@example.com', 'placeholder', 'placeholder')
""")
conn.commit()
conn.close()

process_upload(file_path, user_id)'''