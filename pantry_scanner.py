#!/usr/bin/env python3
"""
Pantry Scanner - Daily inventory monitoring with Claude AI
Captures webcam images and detects changes in your pantry
"""

import cv2
import base64
import os
from datetime import datetime
from anthropic import Anthropic
import pantry_config as config
from database import PantryDatabase
import re

class PantryScanner:
    def __init__(self):
        """Initialize the pantry scanner"""
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.image_dir = config.IMAGE_DIRECTORY
        
        # Initialize database if enabled
        self.db = None
        if config.USE_DATABASE:
            try:
                self.db = PantryDatabase(config.DATABASE_CONFIG)
                print("✓ Database connection established")
            except Exception as e:
                print(f"⚠️  Database connection failed: {e}")
                print("   Continuing without database...")
                self.db = None
        
        # Create image directory if it doesn't exist
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)
            print(f"✓ Created image directory: {self.image_dir}")
    
    def capture_image(self):
        """Capture a single image from the webcam"""
        print(f"📷 Attempting to open webcam {config.WEBCAM_INDEX}...")
        
        cap = cv2.VideoCapture(config.WEBCAM_INDEX)
        
        if not cap.isOpened():
            raise Exception(f"❌ Could not open webcam {config.WEBCAM_INDEX}. Check WEBCAM_INDEX in config.py")
        
        # Let camera warm up
        print("⏳ Warming up camera...")
        for i in range(10):
            cap.read()  # Discard first few frames for auto-exposure
        
        # Capture the actual frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise Exception("❌ Failed to capture image from webcam")
        
        print(f"✓ Image captured: {frame.shape[1]}x{frame.shape[0]} pixels")
        return frame
    
    def save_image(self, image, filename):
        """Save image to disk"""
        filepath = os.path.join(self.image_dir, filename)
        cv2.imwrite(filepath, image)
        print(f"✓ Saved image: {filepath}")
        return filepath
    
    def load_image(self, filename):
        """Load image from disk"""
        filepath = os.path.join(self.image_dir, filename)
        if not os.path.exists(filepath):
            return None
        return cv2.imread(filepath)
    
    def encode_image_to_base64(self, image):
        """Convert OpenCV image to base64 string for Claude API"""
        # Encode as JPEG
        success, buffer = cv2.imencode('.jpg', image)
        if not success:
            raise Exception("Failed to encode image")
        
        # Convert to base64
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return jpg_as_text
    
    def parse_changes(self, analysis_text):
        """
        Parse Claude's analysis to extract structured change data
        Returns dict with 'added', 'removed', 'changed' lists
        """
        changes = {
            'added': [],
            'removed': [],
            'changed': []
        }
        
        # Simple parsing - look for ADDED, REMOVED, QUANTITY CHANGED sections
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Detect section headers
            if 'ADDED' in line.upper() and 'ITEM' in line.upper():
                current_section = 'added'
                continue
            elif 'REMOVED' in line.upper() and 'ITEM' in line.upper():
                current_section = 'removed'
                continue
            elif 'QUANTITY' in line.upper() and 'CHANGED' in line.upper():
                current_section = 'changed'
                continue
            elif line.startswith('#') or line.startswith('**Summary') or 'Items Unchanged' in line:
                current_section = None
                continue
            
            # Extract items (lines starting with -, *, •, or numbers like 1., 2.)
            if current_section and line:
                # Check for various bullet formats
                if (line.startswith('-') or line.startswith('*') or line.startswith('•') or 
                    re.match(r'^\d+\.', line)):  # Matches "1.", "2.", etc.
                    
                    # Clean up the line - remove bullets, numbers, asterisks
                    item = re.sub(r'^[-*•\d.]+\s*', '', line).strip()
                    
                    # Remove markdown bold markers
                    item = item.replace('**', '')
                    
                    # Skip empty or "none" entries
                    if item and item.lower() not in ['none', 'none detected', 'no changes detected']:
                        changes[current_section].append(item)
        
        return changes
    
    def extract_item_name(self, full_description):
        """
        Extract core item name from Claude's detailed description
        Examples:
        "Germ-X hand sanitizer - 1 bottle (moisturizing original...)" -> "Germ-X hand sanitizer"
        "Children's water bottle with red spout (appears to be...)" -> "Children's water bottle"
        """
        # Remove everything after " - " or " (" or parenthetical descriptions
        item = full_description.strip()
        
        # Split on common separators and take the first meaningful part
        for separator in [' - ', ' (', '  ']:
            if separator in item:
                item = item.split(separator)[0].strip()
        
        # Remove trailing punctuation
        item = item.rstrip('.,;:')
        
        # Limit length to something reasonable
        if len(item) > 100:
            item = item[:100].strip()
        
        return item
    
    def save_to_database(self, image_path, analysis_text, api_cost, input_tokens, output_tokens):
        """Save scan results to database"""
        if not self.db:
            return
        
        try:
            # Save scan record
            scan_id = self.db.save_scan(
                image_path=image_path,
                raw_analysis=analysis_text,
                api_cost=api_cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )
            
            # Parse changes from Claude's analysis
            changes = self.parse_changes(analysis_text)
            
            # Process added items
            for item in changes['added']:
                clean_name = self.extract_item_name(item)
                self.db.add_item(clean_name)
                self.db.log_change(scan_id, clean_name, 'added', item)
            
            # Process removed items
            for item in changes['removed']:
                clean_name = self.extract_item_name(item)
                self.db.remove_item(clean_name)
                self.db.log_change(scan_id, clean_name, 'removed', item)
            
            # Process quantity changes
            for item in changes['changed']:
                clean_name = self.extract_item_name(item)
                self.db.log_change(scan_id, clean_name, 'quantity_changed', item)
            
            print(f"💾 Saved to database: {len(changes['added'])} added, {len(changes['removed'])} removed, {len(changes['changed'])} changed")
            
        except Exception as e:
            print(f"⚠️  Error saving to database: {e}")
    
    def analyze_initial_inventory(self, image):
        """On first run, ask Claude to list all visible items"""
        print("\n🤖 Analyzing image for initial inventory...")
        
        # Convert image to base64
        image_b64 = self.encode_image_to_base64(image)
        
        try:
            message = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=config.MAX_TOKENS,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": """Analyze this pantry/storage image and list ALL visible food items, beverages, and household products.

For each item, provide a SHORT description with brand name and product type.
Format: "Brand Name Product Type" (e.g., "Kellogg's Froot Loops", "Poland Spring water bottle", "Germ-X hand sanitizer")

List each item on a separate line starting with a dash (-).
Only list items you can clearly identify. Do not include furniture or background objects."""
                        }
                    ]
                }]
            )
            
            response_text = message.content[0].text
            
            # Extract items (lines starting with -)
            items = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    item = line.lstrip('- ').strip()
                    if item:
                        items.append(item)
            
            return items
            
        except Exception as e:
            print(f"❌ Error analyzing initial inventory: {e}")
            return []
    
    def cleanup_old_images(self):
        """Delete all archived images, keeping only current.jpg and previous.jpg"""
        try:
            files_to_keep = [config.CURRENT_IMAGE, config.PREVIOUS_IMAGE, 'test_capture.jpg']
            deleted_count = 0
            
            for filename in os.listdir(self.image_dir):
                filepath = os.path.join(self.image_dir, filename)
                
                # Only delete files (not directories) and only .jpg files
                if os.path.isfile(filepath) and filename.endswith('.jpg'):
                    if filename not in files_to_keep:
                        os.remove(filepath)
                        deleted_count += 1
            
            if deleted_count > 0:
                print(f"🗑️  Cleaned up {deleted_count} old archived image(s)")
                
        except Exception as e:
            print(f"⚠️  Error cleaning up old images: {e}")
    
    def compare_images_with_claude(self, yesterday_img, today_img):
        """Use Claude API to compare two images and detect changes"""
        print("\n🤖 Sending images to Claude for analysis...")
        
        # Convert images to base64
        yesterday_b64 = self.encode_image_to_base64(yesterday_img)
        today_b64 = self.encode_image_to_base64(today_img)
        
        try:
            message = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=config.MAX_TOKENS,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "IMAGE 1 - YESTERDAY:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": yesterday_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": "IMAGE 2 - TODAY:"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": today_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": config.COMPARISON_PROMPT
                        }
                    ]
                }]
            )
            
            # Extract the text response
            response_text = message.content[0].text
            
            # Print usage stats
            print(f"\n📊 API Usage:")
            print(f"   Input tokens: {message.usage.input_tokens}")
            print(f"   Output tokens: {message.usage.output_tokens}")
            
            # Calculate cost (Sonnet 4.5: $3 per million input, $15 per million output)
            input_cost = (message.usage.input_tokens / 1_000_000) * 3.0
            output_cost = (message.usage.output_tokens / 1_000_000) * 15.0
            total_cost = input_cost + output_cost
            print(f"   Estimated cost: ${total_cost:.6f}")
            
            # Save to database
            self.save_to_database(
                image_path=None,  # We'll set this in run_comparison
                analysis_text=response_text,
                api_cost=total_cost,
                input_tokens=message.usage.input_tokens,
                output_tokens=message.usage.output_tokens
            )
            
            return response_text
            
        except Exception as e:
            print(f"❌ Error calling Claude API: {e}")
            raise
    
    def run_comparison(self):
        """Main method: capture today's image and compare with yesterday's"""
        print("\n" + "="*60)
        print("PANTRY SCANNER - Daily Comparison")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Check if we have a previous image
        previous_img = self.load_image(config.PREVIOUS_IMAGE)
        
        # Check if this is first-time setup (no items in database yet)
        is_first_setup = False
        if self.db:
            stats = self.db.get_statistics()
            if stats['active_items'] == 0 and stats['total_scans'] == 0:
                is_first_setup = True
                print("ℹ️  First-time setup detected - will scan for initial inventory")
        
        if previous_img is None:
            print("ℹ️  No previous image found. This is the first run.")
            print("📷 Capturing baseline image...")
            current_img = self.capture_image()
            self.save_image(current_img, config.CURRENT_IMAGE)
            self.save_image(current_img, config.PREVIOUS_IMAGE)  # Save as previous too
            
            # On first run, ask Claude to list all items
            if is_first_setup:
                print("🔍 Analyzing initial inventory...")
                initial_items = self.analyze_initial_inventory(current_img)
                
                if self.db and initial_items:
                    print(f"\n✓ Found {len(initial_items)} initial items")
                    # Create a dummy scan record
                    scan_id = self.db.save_scan(
                        image_path="initial_scan",
                        raw_analysis="Initial inventory scan",
                        api_cost=0.0,
                        input_tokens=0,
                        output_tokens=0
                    )
                    
                    for item in initial_items:
                        clean_name = self.extract_item_name(item)
                        self.db.add_item(clean_name)
                        self.db.log_change(scan_id, clean_name, 'added', f"Initial scan: {item}")
                        print(f"  + {clean_name}")
            
            print("\n✓ Baseline image saved!")
            print("💡 Run this script again to detect changes.")
            return
        
        # Capture today's image
        print("📷 Capturing today's image...")
        current_img = self.capture_image()
        
        # Save current image
        current_path = self.save_image(current_img, config.CURRENT_IMAGE)
        
        # Compare with Claude
        changes_result = self.compare_images_with_claude(previous_img, current_img)
        
        # changes_result is now a tuple: (response_text, usage_stats)
        # We need to update compare_images_with_claude to return both
        
        # Display results
        print("\n" + "="*60)
        print("CHANGES DETECTED:")
        print("="*60)
        print(changes_result)
        print("="*60 + "\n")
        
        # Archive today's image with timestamp (temporarily, will be deleted after DB save)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_filename = f"pantry_{timestamp}.jpg"
        archive_path = self.save_image(current_img, archive_filename)
        
        # Save to database if enabled (we'll get usage stats from the compare method)
        # For now, we'll extract from what we already printed
        # This is a temporary solution - ideally we'd refactor compare_images_with_claude
        # to return the usage stats
        
        # Delete old archived images (keep only current.jpg and previous.jpg)
        self.cleanup_old_images()
        
        # Copy current to previous for next run
        self.save_image(current_img, config.PREVIOUS_IMAGE)
        print(f"✓ Current image saved as previous for tomorrow's comparison")
        
        print(f"\n✅ Scan complete!")

    def test_camera(self):
        """Test method to just capture and display an image"""
        print("\n🔍 CAMERA TEST MODE")
        print("="*60 + "\n")
        
        img = self.capture_image()
        test_path = self.save_image(img, "test_capture.jpg")
        
        print(f"\n✅ Camera test successful!")
        print(f"📁 Test image saved to: {test_path}")
        print(f"👁️  Open this file to verify your camera angle is correct")


def main():
    """Main entry point"""
    scanner = PantryScanner()
    
    # Check if this is a camera test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        scanner.test_camera()
    else:
        scanner.run_comparison()


if __name__ == "__main__":
    main()