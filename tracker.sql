CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email_address TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    salt TEXT NOT NULL
);

CREATE TABLE uploads (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    rows_total INTEGER NOT NULL,
    rows_inserted INTEGER NOT NULL,
    rows_skipped_duplicate INTEGER NOT NULL,
    rows_skipped_invalid INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    amount INTEGER NOT NULL,
    account TEXT NOT NULL,
    source_upload_id INTEGER NOT NULL,
    UNIQUE (user_id, date, description, amount, account),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (source_upload_id) REFERENCES uploads(id)
);