from flask import Flask

from db import init_db

app = Flask(__name__)


@app.route("/")
def index():
    return "OK"


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
