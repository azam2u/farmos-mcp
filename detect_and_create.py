import os
import sys
import greenery_utils
from farmOS import farmOS

# Configuration
MAPBOX_TOKEN = "pk.eyJ1IjoiYXphbTJ1IiwiYSI6ImNta2twa3RoejFuemszcHB1d2lmcXBleDMifQ.CnaChrJUYvwa08Eg9ZrJrg"

# FarmOS Config
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
HOSTNAME = "https://try.farmos.net"
USERNAME = "mark"
PASSWORD = "E1D5S9UO5O0S"
CLIENT_ID = "farm"

def get_client():
    print(f"Connecting to {HOSTNAME}...", file=sys.stderr)
    try:
        farm = farmOS(HOSTNAME, client_id=CLIENT_ID)
        token = farm.authorize(USERNAME, PASSWORD)
        return farm
    except Exception as e:
        print(f"Auth failed: {e}", file=sys.stderr)
        raise

def main():
    # Target Location: User Provided (Test 5)
    # 35.011493, 135.596751
    lat = 35.011493
    lon = 135.596751
    zoom = 18 
    width = 800
    height = 800
    
    print("1. Fetching Satellite Image...")
    try:
        img = greenery_utils.get_mapbox_image(lat, lon, zoom, width, height, MAPBOX_TOKEN)
        # Save for manual verification as requested
        import cv2
        cv2.imwrite("latest_satellite.jpg", img)
        print("   Saved image to 'latest_satellite.jpg'")
    except Exception as e:
        print(f"Failed to get image: {e}")
        return

    print("2. Analyzing Similarity to Center Point...")
    # Center pixel is (width//2, height//2)
    contours = greenery_utils.detect_similar_regions(img)
    print(f"   Found {len(contours)} similar regions.")
    
    if not contours:
        print("No greenery found.")
        return

    # Find largest contour
    largest_contour = max(contours, key=lambda c: greenery_utils.cv2.contourArea(c))
    area_px = greenery_utils.cv2.contourArea(largest_contour)
    
    if area_px < 100:
        print("Largest area too small. Skipping.")
        return
        
    print(f"   Largest region size: {area_px} pixels")
    
    print("3. Converting to GPS Polygon...")
    wkt = greenery_utils.contour_to_wkt(largest_contour, width, height, lat, lon, zoom)
    
    if not wkt:
        print("Failed to generate WKT (shape too complex or invalid).")
        return
        
    print(f"   WKT: {wkt[:50]}... (truncated)")

    print("4. Creating FarmOS Asset...")
    farm = get_client()
    
    payload = {
        "type": "land",
        "attributes": {
            "name": "Auto-Detected Greenery Field",
            "status": "active",
            "land_type": "bed",
            "notes": "Automatically detected from Mapbox Satellite imagery.",
            "intrinsic_geometry": {
                "value": wkt
            }
        }
    }
    
    try:
        response = farm.asset.send("land", payload)
        new_id = response.get('data', {}).get('id') or response.get('id')
        print(f"SUCCESS! Created Asset ID: {new_id}")
        
    except Exception as e:
        print(f"Failed to create asset: {e}")
        if hasattr(e, 'response') and e.response:
             print(e.response.text)

if __name__ == "__main__":
    main()
