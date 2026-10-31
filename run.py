import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # The Flask debug console can run code, so it is off unless you ask: FLASK_DEBUG=1 python run.py
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
