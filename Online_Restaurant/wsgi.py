# WSGI file for PythonAnywhere deployment

import sys
import os

# Add the project directory to the Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application

# Initialize database tables if they don't exist
with application.app_context():
    from models import db
    db.create_all()

if __name__ == "__main__":
    application.run()


