import os, psycopg2, sys
url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL not set"); sys.exit(1)
try:
    conn = psycopg2.connect(url)
    print("OK: connected")
    conn.close()
except Exception as e:
    print("ERROR:", e); sys.exit(1)
