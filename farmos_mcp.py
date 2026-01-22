import os
import sys
import json
import datetime
import time
import math
from mcp.server.fastmcp import FastMCP
from farmOS import farmOS
import greenery_utils  # Import our new detection library
import cv2

# Mapbox Token
MAPBOX_TOKEN = "pk.eyJ1IjoiYXphbTJ1IiwiYSI6ImNta2twa3RoejFuemszcHB1d2lmcXBleDMifQ.CnaChrJUYvwa08Eg9ZrJrg"

# Set up the FastMCP server
mcp = FastMCP("FarmOS")

# Allow OAuth over insecure transport (needed for some internal/proxied setups)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configuration from Environment Variables
HOSTNAME = os.environ.get("FARMOS_HOST", "https://try.farmos.net")
USERNAME = os.environ.get("FARMOS_USER", "mark")
PASSWORD = os.environ.get("FARMOS_PASSWORD", "E1D5S9UO5O0S")
CLIENT_ID = os.environ.get("FARMOS_CLIENT_ID", "farm")
CLIENT_SECRET = os.environ.get("FARMOS_CLIENT_SECRET", "")
TIMEZONE = datetime.timezone.utc


def get_client():
    """Helper to authenticate and return farmOS client."""
    print(f"Connecting to {HOSTNAME}...", file=sys.stderr)
    try:
        farm = farmOS(HOSTNAME, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        token = farm.authorize(USERNAME, PASSWORD)
        return farm
    except Exception as e:
        print(f"Auth failed: {e}", file=sys.stderr)
        if hasattr(e, 'response'):
             print(e.response.text, file=sys.stderr)
        raise RuntimeError(f"Failed to authenticate with farmOS: {e}")

def find_asset_id_by_name(farm, name):
    """
    Search for an asset by name across common bundles.
    Returns (id, type) or None.
    Retry up to 3 times to allow for indexing delays.
    """
    # Common bundles to search
    bundles = ['plant', 'animal', 'land', 'structure', 'equipment', 'water', 'input', 'compost']
    
    for attempt in range(3):
        for bundle in bundles:
            try:
                res = farm.asset.get(bundle, params={"filter[name]": name, "page[limit]": 1})
                if res and res.get('data') and len(res['data']) > 0:
                    asset = res['data'][0]
                    return asset['id'], asset['type']
            except:
                continue
        
        # If not found, wait and retry
        if attempt < 2:
            print(f"Asset '{name}' not found yet, retrying in 1s...", file=sys.stderr)
            time.sleep(1)
            
    return None

@mcp.tool()
def get_server_info() -> str:
    """Get information about the connected farmOS server."""
    farm = get_client()
    info = farm.info()
    return f"Connected to {info.get('name')} ({info.get('system_name')})"

@mcp.tool()
def create_asset(
    name: str,
    type: str,
    attributes_json: str = "{}",
    plant_type: str = None,
    land_type: str = None,
    structure_type: str = None,
    location_name: str = None,
    is_location: bool = False,
    latitude: float = None,
    longitude: float = None,
    geometry: str = None,
    shape_width_m: float = None,
    shape_height_m: float = None
) -> str:
    """
    Create an asset in farmOS.
    
    Args:
        name: Name of the asset
        type: Type of asset (e.g., 'plant', 'animal', 'land', 'structure')
        attributes_json: Additional attributes as a valid JSON string.
                         Example: '{"notes": "needs water"}' (will be normalized)
        plant_type: (For plants) Name of the plant type (e.g., 'Tomato').
        land_type: (For land) Type of land (e.g., 'bed', 'field', 'greenhouse').
        structure_type: (For structure) Type of structure (e.g., 'shed', 'barn').
        location_name: Name of another asset to use as a parent location (e.g. 'Field 1').
        is_location: Whether this asset is itself a location.
        latitude: GPS Latitude (decimal degrees). Center point if shape dims provided.
        longitude: GPS Longitude (decimal degrees). Center point if shape dims provided.
        geometry: WKT Geometry string (e.g., 'POLYGON ((...))'). Overrides lat/lon if provided.
        shape_width_m: Width of rectangular shape in meters. Requires lat/lon.
        shape_height_m: Height of rectangular shape in meters. Requires lat/lon.
    """
    try:
        attributes = json.loads(attributes_json)
    except json.JSONDecodeError:
        return "Error: attributes_json must be a valid JSON string."

    if not isinstance(attributes, dict):
        attributes = {}
        
    if 'notes' in attributes and isinstance(attributes['notes'], str):
        attributes['notes'] = {
            "value": attributes['notes'],
            "format": "plain_text"
        }
        
    if 'notes' in attributes and isinstance(attributes['notes'], str):
        attributes['notes'] = {
            "value": attributes['notes'],
            "format": "plain_text"
        }
        
    
    # Smart GPS Routing
    # Fixed assets: Intrinsic Geometry
    # Movable assets: Geometry on Movement Log (if linked) or Intrinsic (fallback)
    fixed_types = ['land', 'structure', 'water', 'sensor']
    is_fixed = type in fixed_types or is_location
    
    # Store geometry string for later use
    wkt_geometry = geometry
    
    # Generate Polygon from Center + Dimensions if provided (and no explicit geometry)
    if not wkt_geometry and latitude is not None and longitude is not None and shape_width_m and shape_height_m:
        # Approximate meters to degrees
        # 1 deg lat ~= 111111 m
        # 1 deg lon ~= 111111 * cos(lat) m
        
        half_width = shape_width_m / 2.0
        half_height = shape_height_m / 2.0
        
        lat_delta = half_height / 111111.0
        lon_delta = half_width / (111111.0 * math.cos(math.radians(latitude)))
        
        # Rectangle corners (counter-clockwise from top-left, closing loop)
        # TL: lat+d, lon-d
        # TR: lat+d, lon+d
        # BR: lat-d, lon+d
        # BL: lat-d, lon-d
        
        p1 = (longitude - lon_delta, latitude + lat_delta) # TL
        p2 = (longitude + lon_delta, latitude + lat_delta) # TR
        p3 = (longitude + lon_delta, latitude - lat_delta) # BR
        p4 = (longitude - lon_delta, latitude - lat_delta) # BL
        
        wkt_geometry = f"POLYGON (({p1[0]} {p1[1]}, {p2[0]} {p2[1]}, {p3[0]} {p3[1]}, {p4[0]} {p4[1]}, {p1[0]} {p1[1]}))"
    
    if not wkt_geometry and latitude is not None and longitude is not None:
        wkt_geometry = f"POINT ({longitude} {latitude})"

    # 1. Fixed Asset -> Set Intrinsic Immediately
    if wkt_geometry and is_fixed:
        attributes['intrinsic_geometry'] = {
            "value": wkt_geometry
        }
    # 2. Movable Asset (Unlinked) -> Set Intrinsic as fallback
    elif wkt_geometry and not location_name:
         attributes['intrinsic_geometry'] = {
            "value": wkt_geometry
        }
    
    farm = get_client()
    
    payload = {
        "type": type,
        "attributes": {
            "name": name,
            "status": "active",
            "is_location": is_location,
            **attributes
        },
        "relationships": {}
    }
    
    # Handle Land Type requirement
    if type == "land":
        if land_type:
            payload["attributes"]["land_type"] = land_type
        else:
             payload["attributes"]["land_type"] = "other"

    # Handle Structure Type requirement
    if type == "structure":
        if structure_type:
            payload["attributes"]["structure_type"] = structure_type
        else:
            payload["attributes"]["structure_type"] = "building" # Default to building/shed equivalent


    # Handle Plant Type Relationship
    if type == "plant" and plant_type:
        print(f"Resolving plant_type: {plant_type}", file=sys.stderr)
        filters = {"filter[name]": plant_type}
        terms = farm.term.get("plant_type", params=filters)
        
        term_id = None
        if terms and terms.get('data'):
            term_id = terms['data'][0]['id']
        else:
            # Create new term
            new_term = {
                "type": "taxonomy_term--plant_type",
                "attributes": {"name": plant_type}
            }
            term_resp = farm.term.send("plant_type", new_term)
            term_id = term_resp.get('data', {}).get('id')
            
        if term_id:
            payload["relationships"]["plant_type"] = {
                "data": [{"type": "taxonomy_term--plant_type", "id": term_id}]
            }

    # Handle Location Linking via Movement Log
    # farmOS 2.x best practice: Use movement logs to set location, not direct relationship update.
    # Create the Asset FIRST
    try:
        response = farm.asset.send(type, payload)
        new_id = response.get('data', {}).get('id')
        if not new_id:
             new_id = response.get('id')
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
             return f"Error creating asset: {e}\nServer Response: {e.response.text}"
        return f"Error creating asset: {e}"

    
    result_msg = f"Created asset '{name}' (ID: {new_id})"

    # Handle Location Linking via Movement Log
    if location_name:
        print(f"Resolving location: {location_name}", file=sys.stderr)
        loc_info = find_asset_id_by_name(farm, location_name)
        if loc_info:
            loc_id, loc_type = loc_info
            # Create a movement log
            print(f"Creating movement log to link to {location_name}...", file=sys.stderr)
            log_payload = {
                "type": "log--activity",
                "attributes": {
                    "name": f"Move to {location_name}",
                    "timestamp": datetime.datetime.now(TIMEZONE).replace(microsecond=0).isoformat(),
                    "status": "done",
                    "is_movement": True
                },
                "relationships": {
                    "asset": {
                        "data": [{"type": f"asset--{type}", "id": new_id}]
                    },
                    "location": {
                        "data": [{"type": loc_type, "id": loc_id}]
                    }
                }
            }
            
            # Attach Geometry to Log if Movable and GPS provided
            if wkt_geometry and not is_fixed:
                 log_payload['attributes']['geometry'] = {
                     "value": wkt_geometry
                 }

            try:
                farm.log.send("activity", log_payload)
                result_msg += f". Linked to '{location_name}'."
            except Exception as e:
                err_text = str(e)
                print(f"Failed to create movement log: {err_text}", file=sys.stderr)
                result_msg += f". WARNING: Failed to link to location: {err_text}"
        else:
            print(f"Warning: Location '{location_name}' not found.", file=sys.stderr)
            result_msg += f". WARNING: Location '{location_name}' not found (tried linking)."

    return result_msg

@mcp.tool()
def update_asset_location(
    asset_name: str,
    location_name: str
) -> str:
    """
    Move an existing asset to a new location.
    
    Args:
        asset_name: Name of the asset to move.
        location_name: Name of the location asset.
    """
    farm = get_client()
    
    # Find Asset
    asset_info = find_asset_id_by_name(farm, asset_name)
    if not asset_info:
        return f"Error: Asset '{asset_name}' not found."
    asset_id, asset_type = asset_info
    
    # Find Location
    loc_info = find_asset_id_by_name(farm, location_name)
    if not loc_info:
        return f"Error: Location '{location_name}' not found."
    loc_id, loc_type = loc_info
    
    # Create Update Payload (setting relationships.location)
    # Note: Using 'asset--' prefix in type might be required or just base bundle?
    # get_all returns JSON:API type 'asset--plant'
    
    
    # Create Movement Log
    log_payload = {
        "type": "log--activity",
        "attributes": {
            "name": f"Move to {location_name}",
            "timestamp": datetime.datetime.now(TIMEZONE).replace(microsecond=0).isoformat(),
            "status": "done",
            "is_movement": True
        },
        "relationships": {
            "asset": {
                "data": [{"type": asset_type, "id": asset_id}]
            },
            "location": {
                "data": [{"type": loc_type, "id": loc_id}]
            }
        }
    }
    
    try:
        farm.log.send("activity", log_payload)
        return f"Successfully moved '{asset_name}' to '{location_name}'."
    except Exception as e:
        if hasattr(e, 'response'):
             return f"Error updating location: {e}\n{e.response.text}"
        return f"Error updating location: {e}"

@mcp.tool()
def create_log(
    name: str,
    type: str,
    timestamp: str = None,
    asset_names: list[str] = None,
    attributes_json: str = "{}",
    latitude: float = None,
    longitude: float = None
) -> str:
    """
    Create a log in farmOS.

    Args:
        name: Log name
        type: Log type (e.g., 'seeding', 'activity', 'observation')
        timestamp: ISO format timestamp. Defaults to now.
        asset_names: List of asset names to associate this log with.
        attributes_json: Additional attributes as a valid JSON string.
        latitude: GPS Latitude.
        longitude: GPS Longitude.
    """
    try:
        attributes = json.loads(attributes_json)
    except json.JSONDecodeError:
        return "Error: attributes_json must be a valid JSON string."
        
    if timestamp is None:
        timestamp = datetime.datetime.now(TIMEZONE).replace(microsecond=0).isoformat()
        
    # Normalize notes
    if 'notes' in attributes and isinstance(attributes['notes'], str):
        attributes['notes'] = {
            "value": attributes['notes'],
            "format": "plain_text"
        }

    # Handle Geo location
    if latitude is not None and longitude is not None:
        attributes['geometry'] = {
            "value": f"POINT ({longitude} {latitude})"
        }

    farm = get_client()
    
    # Resolve Assets
    asset_ids = []
    if asset_names:
        for asset_name in asset_names:
            print(f"Resolving asset: {asset_name}", file=sys.stderr)
            res_info = find_asset_id_by_name(farm, asset_name)
            if res_info:
                 asset_ids.append({
                     "type": res_info[1],
                     "id": res_info[0]
                 })
            else:
                print(f"Warning: Asset '{asset_name}' not found.", file=sys.stderr)
    
    payload = {
        "type": f"log--{type}",
        "attributes": {
            "name": name,
            "timestamp": timestamp,
            "status": "done",
            **attributes
        },
        "relationships": {}
    }

    if asset_ids:
        payload["relationships"]["asset"] = {
            "data": asset_ids
        }

    try:
        bundle = type.replace("log--", "")
        response = farm.log.send(bundle, payload)
        new_id = response.get('data', {}).get('id') or response.get('id')
        return f"Created log '{name}' (ID: {new_id})"
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
             return f"Error creating log: {e}\nServer Response: {e.response.text}"
        return f"Error creating log: {e}"

@mcp.tool()
def create_asset_from_satellite(latitude: float, longitude: float, name: str = "Satellite Detected Field", land_type: str = "bed") -> str:
    """
    Create a FarmOS asset by detecting a field shape from satellite imagery.
    
    This tool uses computer vision to analyzing the texture and color of the land 
    at the specified latitude/longitude (using Mapbox Satellite).
    It automatically generates a precise polygon shape for the field and creating an asset.
    
    Args:
        latitude: Latitude of the center of the field.
        longitude: Longitude of the center of the field.
        name: Name of the asset (default: "Satellite Detected Field").
        land_type: Type of land (e.g. 'bed', 'planting', 'paddock').
    """
    print(f"📡 Analyzing satellite imagery for {latitude}, {longitude}...", file=sys.stderr)
    
    # 1. Fetch Image
    try:
        # Fixed zoom 18 and size 800x800 as validated
        zoom = 18
        width = 800
        height = 800
        img = greenery_utils.get_mapbox_image(latitude, longitude, zoom, width, height, MAPBOX_TOKEN)
    except Exception as e:
        return f"Error fetching satellite image: {str(e)}"
    
    # 2. Detect Region
    # Uses our robust "Iterative Flood Fill" with "Area Averaging"
    try:
        contours = greenery_utils.detect_similar_regions(img)
    except Exception as e:
        return f"Error during detection logic: {str(e)}"
    
    if not contours:
        return "No distinct region found at these coordinates."
        
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    print(f"   Found region: {area} pixels", file=sys.stderr)
    
    # 3. Convert to WKT
    try:
        wkt_geometry = greenery_utils.contour_to_wkt(largest_contour, width, height, latitude, longitude, zoom)
    except Exception as e:
        return f"Error converting detected shape to geometry: {str(e)}"
    
    # 4. Create Asset
    farm = get_client() # Use shared auth helper
    
    new_asset = {
        "type": "land",
        "attributes": {
            "name": name,
            "land_type": land_type,
            "status": "active",
            "intrinsic_geometry": {
                "value": wkt_geometry
            },
            "is_fixed": True  # Assuming land assets are fixed
        }
    }
    
    try:
        response = farm.asset.send("land", new_asset)
        if response and 'id' in response:
            return f"Successfully created asset '{name}' (ID: {response['id']}) with detected geometry."
        # FarmOS 2.x API usually returns data object, wrapper does some magic.
        # Fallback check
        new_id = response.get('data', {}).get('id') or response.get('id')
        if new_id:
             return f"Successfully created asset '{name}' (ID: {new_id}) with detected geometry."
        else:
             return f"Failed to create asset. Response: {response}"
    except Exception as e:
         return f"Error creating asset: {str(e)}"

if __name__ == "__main__":
    mcp.run()
