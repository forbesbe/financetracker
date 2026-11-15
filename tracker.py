import cleaner
import pandas as pd
import json
import sqlite3
from datetime import datetime
import db

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

def process_upload(file_path, user_id):
    df = pd.read_excel(file_path)

    conn = db.get_connection()
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

if __name__ == "__main__":
    db.clear_db()
    db.init_db()

    conn = db.get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO users (id, first_name, last_name, username, email_address, password, salt)
        VALUES (1, 'Benjamin', 'Forbes', 'ben', 'ben@example.com', 'hash', 'salt')
    """)
    conn.commit()
    conn.close()

    user_id = 1  # placeholder

    upload_id_1 = process_upload("expenses_clean.xlsx", user_id)
    upload_id_2 = process_upload("expenses_messy.xlsx", user_id)

    conn = db.get_connection()
    for uid in (upload_id_1, upload_id_2):
        row = conn.execute("""
            SELECT filename, rows_total, rows_inserted, rows_skipped_duplicate, rows_skipped_invalid
            FROM uploads WHERE id = ?
        """, (uid,)).fetchone()
        print(f"upload {uid}: {row}")

    total_transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    total_skipped_rows = conn.execute("SELECT COUNT(*) FROM skipped_rows").fetchone()[0]
    print(f"total rows in transactions table: {total_transactions}")
    print(f"total rows in skipped_rows table: {total_skipped_rows}")
    conn.close()
