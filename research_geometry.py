import os
import sys
import json
from farmOS import farmOS

# Configuration
HOSTNAME = os.environ.get("FARMOS_HOST", "https://myfarm2u.farmos.net")
USERNAME = os.environ.get("FARMOS_USER", "Azam")
PASSWORD = os.environ.get("FARMOS_PASSWORD", "8IK1S1ZQIGU2")
CLIENT_ID = os.environ.get("FARMOS_CLIENT_ID", "farm")
CLIENT_SECRET = os.environ.get("FARMOS_CLIENT_SECRET", "")

def get_client():
    try:
        farm = farmOS(HOSTNAME, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        farm.authorize(USERNAME, PASSWORD)
        return farm
    except Exception as e:
        print(f"Auth failed: {e}")
        sys.exit(1)

def main():
    farm = get_client()
    
    name = "GPS Test Asset"
    # Random coords: Tokyo Tower approx 139.7454, 35.6586 (Lon, Lat)
    # WKT format is POINT (LON LAT)
    wkt = "POINT (139.7454 35.6586)"
    
    print(f"Creating asset '{name}' with geometry: {wkt}")
    
    payload = {
        "type": "asset--land",
        "attributes": {
            "name": name,
            "status": "active",
            "land_type": "other",
            "is_location": True,
            "geometry": {
                "value": wkt
            }
        }
    }
    
    try:
        # Try nested value object first (common in Drupal)
        res = farm.asset.send("land", payload)
        print("Created! ID:", res.get('data', {}).get('id'))
        print("Attributes:", json.dumps(res.get('data', {}).get('attributes'), indent=2))
    except Exception as e:
        print("Failed with nested object:", e)
        if hasattr(e, 'response'):
             print(e.response.text)
             
        # Fallback: Try raw string if generic 422? (Unlikely for Drupal fields but possible)
        try:
            print("\nRetrying with raw string...")
            payload["attributes"]["geometry"] = wkt
            res = farm.asset.send("land", payload)
            print("Created with raw string! ID:", res.get('data', {}).get('id'))
        except Exception as e2:
             print("Failed with raw string:", e2)

if __name__ == "__main__":
    main()
