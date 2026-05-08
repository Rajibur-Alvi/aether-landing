import os
import psycopg2
from config import get_settings

settings = get_settings()

def get_dsn():
    url = settings.supabase_url
    service_key = settings.supabase_service_key
    project_ref = url.split('://')[1].split('.')[0]
    return f"postgresql://postgres:{service_key}@db.{project_ref}.supabase.co:5432/postgres"

def table_exists(cursor, table_name):
    cursor.execute("""
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = %s
    """, (table_name,))
    return bool(cursor.fetchone())

def check_and_apply_migration():
    dsn = get_dsn()
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()

    if table_exists(cursor, 'user_profiles'):
        print("Schema already applied.")
        cursor.close()
        conn.close()
        return

    # Apply migration
    sql_path = os.path.join(os.path.dirname(__file__), '..', 'supabase', 'migrations', '001_initial_schema.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()

    cursor.execute(sql)
    conn.commit()
    print("Migration applied successfully.")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_and_apply_migration()