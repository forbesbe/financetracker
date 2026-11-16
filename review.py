import json
import math
from flask import Blueprint, request, session

import cleaner
import db
from tracker import clean_row, insert_or_flag_duplicate

review_bp = Blueprint('review', __name__)

REQUIRED_FIELDS = ("Account", "Date", "Amount", "Description", "Category")


@review_bp.route('/skipped_rows/<int:row_id>/discard', methods=['POST'])
def discard_skipped_row(row_id):
    user_id = session.get('user_id')
    if not user_id:
        response_data = {'status': 0, "message": "Not logged in."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT skipped_rows.id
            FROM skipped_rows
            JOIN uploads ON skipped_rows.upload_id = uploads.id
            WHERE skipped_rows.id = ? AND uploads.user_id = ? AND resolved = 0
        """, (row_id, user_id))
        match = cursor.fetchone()

        if not match:
            response_data = {'status': 2, "message": "Row not found."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        cursor.execute("""
            UPDATE skipped_rows SET resolved = 1 WHERE id = ?
        """, (row_id,))
        conn.commit()

        response_data = {'status': 1, "message": "Row discarded."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}
    finally:
        conn.close()

@review_bp.route('/skipped_rows/<int:row_id>/add', methods=['POST'])
def add_skipped_row(row_id):
    user_id = session.get('user_id')
    if not user_id:
        response_data = {'status': 0, "message": "Not logged in."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT sr.raw_row, sr.upload_id
            FROM skipped_rows AS sr
            JOIN uploads AS u ON sr.upload_id = u.id
            WHERE sr.id = ? AND u.user_id = ? AND sr.resolved = 0 AND sr.is_duplicate = 1
        """, (row_id, user_id))
        data = cursor.fetchone()
        if not data:
            response_data = {'status': 2, "message": "Row not found."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        raw_row, upload_id = data
        parsed = json.loads(raw_row)

        try:
            cleaned = clean_row(parsed, user_id, upload_id)
        except cleaner.RowInvalidError as e:
            response_data = {'status': 3, "message": f"Row failed re-cleaning: {e.message}"}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        cursor.execute("""
            INSERT INTO transactions (user_id, date, description, category, amount, account, source_upload_id)
            VALUES (:user_id, :date, :description, :category, :amount, :account, :source_upload_id)
        """, cleaned)
        cursor.execute("""
            UPDATE skipped_rows SET resolved = 1 WHERE id = ?
        """, (row_id,))

        conn.commit()
        response_data = {'status': 1, "message": "Row successfully added to transactions."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}
    finally:
        conn.close()

@review_bp.route('/skipped_rows/<int:row_id>/resubmit', methods=['POST'])
def resubmit_skipped_row(row_id):
    user_id = session.get('user_id')
    if not user_id:
        response_data = {'status': 0, "message": "Not logged in."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    data = request.get_json() or {}
    if not all(field in data for field in REQUIRED_FIELDS):
        response_data = {'status': 4, "message": "Missing required fields."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT sr.upload_id FROM skipped_rows AS sr
            JOIN uploads AS u ON sr.upload_id = u.id
            WHERE sr.id = ? AND u.user_id = ? AND sr.resolved = 0 AND sr.is_duplicate = 0
        """, (row_id, user_id))
        match = cursor.fetchone()
        if not match:
            response_data = {'status': 2, "message": "Row not found."}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        upload_id = match[0]

        cursor.execute("""
            UPDATE skipped_rows SET resolved = 1 WHERE id = ?
        """, (row_id,))

        try:
            cleaned = clean_row(data, user_id, upload_id)
        except cleaner.RowInvalidError as e:
            cursor.execute("""
                INSERT INTO skipped_rows (upload_id, raw_row, status, message)
                VALUES (?, ?, ?, ?)
            """, (upload_id, json.dumps(data), e.status, e.message))
            conn.commit()
            response_data = {'status': 3, "message": f"Row failed re-cleaning: {e.message}"}
            return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

        result = insert_or_flag_duplicate(cursor, cleaned, json.dumps(data), upload_id)
        conn.commit()

        if result == "duplicate":
            response_data = {'status': 5, "message": "Valid row is a duplicate."}
        else:
            response_data = {'status': 1, "message": "Row successfully added to transactions."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}
    finally:
        conn.close()

@review_bp.route('/skipped_rows', methods=['GET'])
def list_skipped_rows():
    user_id = session.get('user_id')
    if not user_id:
        response_data = {'status': 0, "message": "Not logged in."}
        return json.dumps(response_data), 200, {'Content-Type': 'application/json'}

    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT sr.id, sr.raw_row, sr.status, sr.message, sr.is_duplicate
            FROM skipped_rows AS sr
            JOIN uploads AS u ON sr.upload_id = u.id
            WHERE u.user_id = ? AND sr.resolved = 0
            ORDER BY sr.id
        """, (user_id,))
        results = cursor.fetchall()

        rows = []
        for row_id, raw_row, status, message, is_duplicate in results:
            parsed = json.loads(raw_row)
            parsed = {key: (None if isinstance(value, float) and math.isnan(value) else value)
                      for key, value in parsed.items()}
            rows.append({
                "id": row_id,
                "is_duplicate": is_duplicate,
                "status": status,
                "message": message,
                "raw_row": parsed
            })

        response_data = {'status': 1, "rows": rows}
        return json.dumps(response_data, allow_nan=False), 200, {'Content-Type': 'application/json'}
    finally:
        conn.close()