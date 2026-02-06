#!/usr/bin/env python3
"""
Reset Database - Clear all data and start fresh
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pantry_config as config

def reset_database():
    """Drop and recreate the pantry_monitor database"""
    
    print("\n" + "="*60)
    print("⚠️  DATABASE RESET - This will delete ALL data!")
    print("="*60 + "\n")
    
    confirm = input("Type 'YES' to confirm reset: ")
    
    if confirm != 'YES':
        print("❌ Reset cancelled.")
        return
    
    try:
        # Connect to postgres database
        print("\n📡 Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host=config.DATABASE_CONFIG['host'],
            port=config.DATABASE_CONFIG['port'],
            database='postgres',
            user=config.DATABASE_CONFIG['user'],
            password=config.DATABASE_CONFIG['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✓ Connected")
        
        # Terminate existing connections
        print("🔌 Disconnecting active sessions...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{config.DATABASE_CONFIG['database']}'
            AND pid <> pg_backend_pid()
        """)
        
        # Drop the database
        print(f"🗑️  Dropping database '{config.DATABASE_CONFIG['database']}'...")
        cursor.execute(f"DROP DATABASE IF EXISTS {config.DATABASE_CONFIG['database']}")
        print("✓ Database dropped")
        
        # Recreate the database
        print(f"📦 Creating fresh database '{config.DATABASE_CONFIG['database']}'...")
        cursor.execute(f"CREATE DATABASE {config.DATABASE_CONFIG['database']}")
        print("✓ Database created")
        
        cursor.close()
        conn.close()
        
        # Now create tables
        print("\n📊 Creating tables...")
        from database import PantryDatabase
        db = PantryDatabase(config.DATABASE_CONFIG)
        db.create_tables()
        db.close()
        
        print("\n" + "="*60)
        print("✅ Database Reset Complete!")
        print("="*60)
        print("\nYour database is now empty and ready for fresh scans.")
        print("Run: python pantry_scanner.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. No other programs are using the database")
        print("2. The web app (app.py) is not running")
        print("3. Your PostgreSQL credentials are correct")

if __name__ == "__main__":
    reset_database()