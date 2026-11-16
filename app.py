from flask import Flask

import db
from user import user_bp
from review import review_bp

app = Flask(__name__)

with open("key.txt", "r") as key_file:
    app.secret_key = key_file.read().strip()

db.init_db()

app.register_blueprint(user_bp)
app.register_blueprint(review_bp)

if __name__ == "__main__":
    app.run(debug=True)