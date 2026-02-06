#!/usr/bin/env python3
"""
Database module for Pantry Scanner
Handles PostgreSQL storage of inventory changes and scans
"""

import psycopg2
from psycopg2.extras import Json
from datetime import datetime
import json


class PantryDatabase:
    """Handle all database operations for pantry scanner"""
    
    def __init__(self, db_config):
        """
        Initialize database connection
        
        Args:
            db_config: Dictionary with keys: host, database, user, password, port
        """
        self.config = db_config
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.config['host'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                port=self.config.get('port', 5432)
            )
            print("✓ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        
        try:
            # Table to store each scan
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pantry_scans (
                    scan_id SERIAL PRIMARY KEY,
                    scan_date TIMESTAMP NOT NULL DEFAULT NOW(),
                    image_path VARCHAR(500),
                    raw_analysis TEXT,
                    api_cost DECIMAL(10, 6),
                    input_tokens INTEGER,
                    output_tokens INTEGER
                )
            """)
            
            # Table to store detected items and their current state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pantry_items (
                    item_id SERIAL PRIMARY KEY,
                    item_name VARCHAR(200) NOT NULL,
                    category VARCHAR(100),
                    first_detected TIMESTAMP DEFAULT NOW(),
                    last_seen TIMESTAMP DEFAULT NOW(),
                    current_quantity INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Table to track all changes (added/removed/quantity)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_changes (
                    change_id SERIAL PRIMARY KEY,
                    scan_id INTEGER REFERENCES pantry_scans(scan_id),
                    item_name VARCHAR(200) NOT NULL,
                    change_type VARCHAR(20) NOT NULL,  -- 'added', 'removed', 'quantity_changed'
                    details TEXT,
                    detected_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pantry_items_name 
                ON pantry_items(item_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_inventory_changes_scan 
                ON inventory_changes(scan_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pantry_scans_date 
                ON pantry_scans(scan_date)
            """)
            
            self.conn.commit()
            print("✓ Database tables created successfully")
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error creating tables: {e}")
            raise
        finally:
            cursor.close()
    
    def save_scan(self, image_path, raw_analysis, api_cost, input_tokens, output_tokens):
        """
        Save a scan record
        
        Returns:
            scan_id: The ID of the newly created scan record
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO pantry_scans (image_path, raw_analysis, api_cost, input_tokens, output_tokens)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING scan_id
            """, (image_path, raw_analysis, api_cost, input_tokens, output_tokens))
            
            scan_id = cursor.fetchone()[0]
            self.conn.commit()
            
            print(f"✓ Saved scan record (ID: {scan_id})")
            return scan_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error saving scan: {e}")
            raise
        finally:
            cursor.close()
    
    def add_item(self, item_name, category=None):
        """Add a new item or update if it already exists"""
        cursor = self.conn.cursor()
        
        try:
            # Check if item exists
            cursor.execute("""
                SELECT item_id FROM pantry_items 
                WHERE LOWER(item_name) = LOWER(%s)
            """, (item_name,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing item
                cursor.execute("""
                    UPDATE pantry_items 
                    SET last_seen = NOW(),
                        is_active = TRUE,
                        current_quantity = current_quantity + 1
                    WHERE item_id = %s
                """, (existing[0],))
                item_id = existing[0]
            else:
                # Insert new item
                cursor.execute("""
                    INSERT INTO pantry_items (item_name, category)
                    VALUES (%s, %s)
                    RETURNING item_id
                """, (item_name, category))
                item_id = cursor.fetchone()[0]
            
            self.conn.commit()
            return item_id
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error adding item: {e}")
            raise
        finally:
            cursor.close()
    
    def remove_item(self, item_name):
        """Mark an item as removed (decrease quantity or mark inactive)"""
        cursor = self.conn.cursor()
        
        try:
            # First try exact match (case-insensitive)
            cursor.execute("""
                UPDATE pantry_items 
                SET current_quantity = GREATEST(current_quantity - 1, 0),
                    is_active = CASE WHEN current_quantity <= 1 THEN FALSE ELSE TRUE END,
                    last_seen = NOW()
                WHERE LOWER(item_name) = LOWER(%s)
                RETURNING item_id
            """, (item_name,))
            
            result = cursor.fetchone()
            
            # If no exact match, try fuzzy matching (contains)
            if not result:
                # First find matching items
                cursor.execute("""
                    SELECT item_id FROM pantry_items
                    WHERE LOWER(item_name) LIKE LOWER(%s)
                    AND is_active = TRUE
                    LIMIT 1
                """, (f'%{item_name}%',))
                
                match = cursor.fetchone()
                
                if match:
                    # Now update that specific item
                    cursor.execute("""
                        UPDATE pantry_items 
                        SET current_quantity = GREATEST(current_quantity - 1, 0),
                            is_active = CASE WHEN current_quantity <= 1 THEN FALSE ELSE TRUE END,
                            last_seen = NOW()
                        WHERE item_id = %s
                        RETURNING item_id
                    """, (match[0],))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"  ℹ️  Fuzzy matched removal: '{item_name}'")
            
            self.conn.commit()
            
            if not result:
                print(f"  ⚠️  Item not found for removal: '{item_name}'")
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error removing item: {e}")
            raise
        finally:
            cursor.close()
    
    def log_change(self, scan_id, item_name, change_type, details=None):
        """Log an inventory change"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO inventory_changes (scan_id, item_name, change_type, details)
                VALUES (%s, %s, %s, %s)
            """, (scan_id, item_name, change_type, details))
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error logging change: {e}")
            raise
        finally:
            cursor.close()
    
    def get_current_inventory(self):
        """Get all currently active items"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT item_id, item_name, category, current_quantity, 
                       first_detected, last_seen
                FROM pantry_items
                WHERE is_active = TRUE
                ORDER BY item_name
            """)
            
            items = cursor.fetchall()
            return items
            
        finally:
            cursor.close()
    
    def get_recent_scans(self, limit=10):
        """Get recent scan records"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT scan_id, scan_date, image_path, api_cost, 
                       input_tokens, output_tokens
                FROM pantry_scans
                ORDER BY scan_date DESC
                LIMIT %s
            """, (limit,))
            
            scans = cursor.fetchall()
            return scans
            
        finally:
            cursor.close()
    
    def get_item_history(self, item_name):
        """Get change history for a specific item"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT ic.change_type, ic.details, ic.detected_at, ps.scan_date
                FROM inventory_changes ic
                JOIN pantry_scans ps ON ic.scan_id = ps.scan_id
                WHERE LOWER(ic.item_name) = LOWER(%s)
                ORDER BY ic.detected_at DESC
            """, (item_name,))
            
            history = cursor.fetchall()
            return history
            
        finally:
            cursor.close()
    
    def get_statistics(self):
        """Get overall statistics"""
        cursor = self.conn.cursor()
        
        try:
            stats = {}
            
            # Total scans
            cursor.execute("SELECT COUNT(*) FROM pantry_scans")
            stats['total_scans'] = cursor.fetchone()[0]
            
            # Active items
            cursor.execute("SELECT COUNT(*) FROM pantry_items WHERE is_active = TRUE")
            stats['active_items'] = cursor.fetchone()[0]
            
            # Total API cost
            cursor.execute("SELECT COALESCE(SUM(api_cost), 0) FROM pantry_scans")
            stats['total_api_cost'] = float(cursor.fetchone()[0])
            
            # Recent changes (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) FROM inventory_changes
                WHERE detected_at > NOW() - INTERVAL '7 days'
            """)
            stats['changes_last_week'] = cursor.fetchone()[0]
            
            return stats
            
        finally:
            cursor.close()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")