#!/usr/bin/env python3
"""
Quick-start script: creates the PostgreSQL database if it doesn't exist,
then starts the FastAPI backend server.
Run from the /backend directory.
"""
import subprocess
import sys
import os

DB_NAME = "syllabusai"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

def create_db():
    """Create the database if it doesn't exist."""
    try:
        result = subprocess.run(
            ["psql", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, "-lqt"],
            capture_output=True, text=True, timeout=10
        )
        if DB_NAME in result.stdout:
            print(f"✓ Database '{DB_NAME}' already exists")
            return
        subprocess.run(
            ["createdb", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, DB_NAME],
            check=True, timeout=10
        )
        print(f"✓ Created database '{DB_NAME}'")
    except FileNotFoundError:
        print("ℹ PostgreSQL tools (psql) not in PATH — will automatically use local SQLite database.")
    except subprocess.SubprocessError:
        print("ℹ Could not connect to PostgreSQL — will automatically use local SQLite database.")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    create_db()

    # Prefer project virtual environment (../venv) if present
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    venv_py_win = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    venv_py_unix = os.path.join(base_dir, "venv", "bin", "python")

    python_bin = sys.executable
    if os.path.exists(venv_py_win):
        python_bin = venv_py_win
    elif os.path.exists(venv_py_unix):
        python_bin = venv_py_unix

    print("Starting FastAPI server on http://localhost:8000 ...")
    subprocess.run([
        python_bin, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ])

