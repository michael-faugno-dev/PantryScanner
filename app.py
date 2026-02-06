#!/usr/bin/env python3
"""
Pantry Monitor Web App
Modern Flask application for viewing pantry inventory
"""

from flask import Flask, render_template, jsonify, send_from_directory
import pantry_config as config
from database import PantryDatabase
import os
from datetime import datetime

app = Flask(__name__)

def get_db():
    """Get database connection"""
    return PantryDatabase(config.DATABASE_CONFIG)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/inventory')
def api_inventory():
    """API endpoint: Get current inventory"""
    db = get_db()
    items = db.get_current_inventory()
    db.close()
    
    inventory = []
    for item in items:
        item_id, name, category, quantity, first_detected, last_seen = item
        inventory.append({
            'id': item_id,
            'name': name,
            'category': category or 'Uncategorized',
            'quantity': quantity,
            'first_detected': first_detected.isoformat(),
            'last_seen': last_seen.isoformat(),
            'days_in_pantry': (datetime.now() - first_detected).days
        })
    
    return jsonify(inventory)

@app.route('/api/recent-scans')
def api_recent_scans():
    """API endpoint: Get recent scans"""
    db = get_db()
    scans = db.get_recent_scans(10)
    db.close()
    
    scan_list = []
    for scan in scans:
        scan_id, scan_date, image_path, api_cost, input_tokens, output_tokens = scan
        scan_list.append({
            'id': scan_id,
            'date': scan_date.isoformat(),
            'cost': float(api_cost),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        })
    
    return jsonify(scan_list)

@app.route('/api/statistics')
def api_statistics():
    """API endpoint: Get statistics"""
    db = get_db()
    stats = db.get_statistics()
    
    # Get recent changes
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT change_type, COUNT(*) 
        FROM inventory_changes 
        WHERE detected_at > NOW() - INTERVAL '7 days'
        GROUP BY change_type
    """)
    change_breakdown = dict(cursor.fetchall())
    cursor.close()
    
    db.close()
    
    return jsonify({
        'total_scans': stats['total_scans'],
        'active_items': stats['active_items'],
        'total_api_cost': stats['total_api_cost'],
        'changes_last_week': stats['changes_last_week'],
        'change_breakdown': change_breakdown
    })

@app.route('/api/latest-image')
def api_latest_image():
    """API endpoint: Get path to latest image"""
    image_path = os.path.join(config.IMAGE_DIRECTORY, config.CURRENT_IMAGE)
    
    if os.path.exists(image_path):
        # Get file modification time
        mod_time = os.path.getmtime(image_path)
        return jsonify({
            'exists': True,
            'path': '/image/current.jpg',
            'last_updated': datetime.fromtimestamp(mod_time).isoformat()
        })
    else:
        return jsonify({'exists': False})

@app.route('/image/<filename>')
def serve_image(filename):
    """Serve images from pantry_images directory"""
    return send_from_directory(config.IMAGE_DIRECTORY, filename)

@app.route('/api/item-history/<int:item_id>')
def api_item_history(item_id):
    """API endpoint: Get history for a specific item"""
    db = get_db()
    
    # Get item name first
    cursor = db.conn.cursor()
    cursor.execute("SELECT item_name FROM pantry_items WHERE item_id = %s", (item_id,))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        db.close()
        return jsonify({'error': 'Item not found'}), 404
    
    item_name = result[0]
    history = db.get_item_history(item_name)
    cursor.close()
    db.close()
    
    history_list = []
    for entry in history:
        change_type, details, detected_at, scan_date = entry
        history_list.append({
            'change_type': change_type,
            'details': details,
            'detected_at': detected_at.isoformat(),
            'scan_date': scan_date.isoformat()
        })
    
    return jsonify(history_list)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("\n" + "="*60)
    print("PANTRY MONITOR WEB APP")
    print("="*60)
    print("\n🌐 Starting web server...")
    print("📱 Open your browser to: http://localhost:5000")
    print("⌨️  Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)