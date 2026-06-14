import sqlite3
import json

def main():
    conn = sqlite3.connect("orca.db")
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables in database:", tables)
    
    if "documents" in tables:
        cursor.execute("SELECT id, filename, file_type, chunk_count, status, user_id, source_type FROM documents;")
        rows = cursor.fetchall()
        print(f"\n--- Documents ({len(rows)}) ---")
        for r in rows:
            print(f"ID: {r[0]} | Name: {r[1]} | Type: {r[2]} | Chunks: {r[3]} | Status: {r[4]} | User: {r[5]} | Source: {r[6]}")
            
    conn.close()

if __name__ == "__main__":
    main()
