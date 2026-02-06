#!/usr/bin/env python3
"""
Setup script for Pantry Monitor Database
Run this once to create the database and tables
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pantry_config as config
from database import PantryDatabase

def create_database():
    """Create the pantry_monitor database if it doesn't exist"""
    
    print("\n" + "="*60)
    print("PANTRY MONITOR - Database Setup")
    print("="*60 + "\n")
    
    # Connect to postgres database to create our database
    try:
        print("📡 Connecting to PostgreSQL server...")
        conn = psycopg2.connect(
            host=config.DATABASE_CONFIG['host'],
            port=config.DATABASE_CONFIG['port'],
            database='postgres',  # Connect to default postgres database
            user=config.DATABASE_CONFIG['user'],
            password=config.DATABASE_CONFIG['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✓ Connected to PostgreSQL server")
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.DATABASE_CONFIG['database'],)
        )
        
        if cursor.fetchone():
            print(f"ℹ️  Database '{config.DATABASE_CONFIG['database']}' already exists")
        else:
            # Create the database
            print(f"📦 Creating database '{config.DATABASE_CONFIG['database']}'...")
            cursor.execute(f"CREATE DATABASE {config.DATABASE_CONFIG['database']}")
            print(f"✓ Database '{config.DATABASE_CONFIG['database']}' created successfully")
        
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed!")
        print(f"Error: {e}")
        print("\nPlease check:")
        print("1. PostgreSQL is running")
        print("2. Your password in pantry_config.py is correct")
        print("3. User 'postgres' has permission to create databases")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Now create the tables
    try:
        print(f"\n📊 Creating tables in '{config.DATABASE_CONFIG['database']}'...")
        db = PantryDatabase(config.DATABASE_CONFIG)
        db.create_tables()
        db.close()
        
        print("\n" + "="*60)
        print("✅ Setup Complete!")
        print("="*60)
        print("\nYour database is ready to use.")
        print("You can now run: python pantry_scanner.py")
        print("\nDatabase contains:")
        print("  • pantry_scans - Records of each scan")
        print("  • pantry_items - Current inventory items")
        print("  • inventory_changes - History of all changes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_database()
    
    if not success:
        print("\n⚠️  Setup failed. Please fix the errors above and try again.")
        exit(1)