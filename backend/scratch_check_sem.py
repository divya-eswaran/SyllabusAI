from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT subject_code, subject_name, semester FROM subjects ORDER BY semester, subject_code;"))
    for row in res:
        print(f"Sem {row[2]}: {row[0]} - {row[1]}")
