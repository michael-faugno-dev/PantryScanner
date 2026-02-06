#!/usr/bin/env python3
"""
View Pantry Inventory - Query the database to see current state
"""

import pantry_config as config
from database import PantryDatabase
from datetime import datetime

def view_inventory():
    """Display current pantry inventory from database"""
    
    db = PantryDatabase(config.DATABASE_CONFIG)
    
    print("\n" + "="*60)
    print("CURRENT PANTRY INVENTORY")
    print("="*60 + "\n")
    
    # Get current inventory
    items = db.get_current_inventory()
    
    if not items:
        print("📦 No items in inventory yet.")
    else:
        print(f"📦 {len(items)} Active Items:\n")
        for item in items:
            item_id, name, category, quantity, first_detected, last_seen = item
            print(f"  • {name}")
            print(f"    Quantity: {quantity}")
            print(f"    First seen: {first_detected.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Last seen: {last_seen.strftime('%Y-%m-%d %H:%M')}")
            print()
    
    print("\n" + "="*60)
    print("RECENT SCANS")
    print("="*60 + "\n")
    
    # Get recent scans
    scans = db.get_recent_scans(5)
    
    if not scans:
        print("📸 No scans yet.")
    else:
        for scan in scans:
            scan_id, scan_date, image_path, api_cost, input_tokens, output_tokens = scan
            print(f"Scan #{scan_id} - {scan_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Cost: ${api_cost:.6f} | Tokens: {input_tokens} in, {output_tokens} out")
            print()
    
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60 + "\n")
    
    # Get statistics
    stats = db.get_statistics()
    
    print(f"Total scans: {stats['total_scans']}")
    print(f"Active items: {stats['active_items']}")
    print(f"Total API cost: ${stats['total_api_cost']:.6f}")
    print(f"Changes this week: {stats['changes_last_week']}")
    
    print()
    
    db.close()

if __name__ == "__main__":
    view_inventory()