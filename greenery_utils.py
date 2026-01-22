import requests
import cv2
import numpy as np
import math
import os

def get_mapbox_image(lat, lon, zoom, width, height, token):
    """Fetch static satellite image from Mapbox."""
    url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{zoom}/{width}x{height}?access_token={token}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Mapbox API Error: {response.text}")
    
    # Decode image to OpenCV format
    image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return img

def detect_similar_regions(img, center_px=None):
    """
    Return a list of contours (pixels) that match the color at the center of the image.
    If center_px is provided (x, y), samples color from there.
    Otherwise samples from image center.
    """
    height, width, _ = img.shape
    
    if center_px is None:
        center_x, center_y = width // 2, height // 2
    else:
        center_x, center_y = center_px

    # 0. Pre-processing: Median Blur (Important for FloodFill to not get stuck on noise)
    img_blurred = cv2.medianBlur(img, 5)

    # 1. Sample Color from Area (Region of Interest)
    # User requested 10m x 10m.
    # At Zoom 18 (Lat ~35), 1 pixel ~= 0.5m.
    # So 10m is ~20 pixels.
    # We use range_px = 10 -> (center-10 to center+10) = 21x21 pixels (~10.5m x 10.5m)
    range_px = 10
    
    roi = img_blurred[max(0, center_y-range_px):min(height, center_y+range_px+1), 
                      max(0, center_x-range_px):min(width, center_x+range_px+1)]
    
    if roi.size == 0:
         return [] 
         
    # Convert ROI to HSV to check average
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    avg_color = np.mean(hsv_roi, axis=(0, 1)) # (H, S, V) average
    
    print(f"   Sampled Area (21x21 px ~10.5m): Average HSV({int(avg_color[0])}, {int(avg_color[1])}, {int(avg_color[2])})")
    
    # 2. Iterative Flood Fill
    # IMPORTANT: FloodFill uses the color of the *seed pixel* in the input image.
    # If the exact center pixel is an outlier (noise), the whole fill fails.
    # We MUST overwrite the seed pixel with our calculated AVERAGE color
    # to ensure we look for the "Average Soil Color", not "That One Stone's Color".
    
    h, w, _ = img.shape
    hsv_img = cv2.cvtColor(img_blurred, cv2.COLOR_BGR2HSV)
    
    # Force set the center pixel to the average color so floodFill uses it as reference
    target_pixel = np.array([int(avg_color[0]), int(avg_color[1]), int(avg_color[2])], dtype=np.uint8)
    hsv_img[center_y, center_x] = target_pixel
    
    # We try multiple tolerance levels to find a "stable" region size.
    # Start tight, and relax until we get a significant area that isn't HUGE.
    
    thresholds = [
        # (lo, up) tuples for (Hue, Sat, Val)
        # Finer steps to find the exact boundary
        ((2, 10, 10), (2, 10, 10)),   
        ((3, 20, 20), (3, 20, 20)),   
        ((4, 30, 30), (4, 30, 30)),
        ((5, 35, 35), (5, 35, 15)),   # Asymmetric Val (Stop getting brighter)
        ((6, 40, 40), (6, 40, 20)),   # Asymmetric
        ((6, 42, 42), (6, 42, 22)),   # NEW Intermediate (Slightly relaxed)
        ((7, 45, 45), (7, 45, 25)),   # New intermediate
        ((8, 50, 50), (8, 50, 30)),   # New intermediate
        ((9, 60, 60), (9, 60, 40)),   
    ]
    
    best_contours = []
    best_area = 0
    img_area = h * w
    
    print(f"   Center Pixel HSV: {hsv_img[center_y, center_x]}")
    
    for i, (lo, up) in enumerate(thresholds):
        flood_mask = np.zeros((h+2, w+2), np.uint8)
        flood_temp = hsv_img.copy()
        flags = 4 | (255 << 8) | cv2.FLOODFILL_FIXED_RANGE
        
        cv2.floodFill(flood_temp, flood_mask, (center_x, center_y), (0,0,255), lo, up, flags)
        
        mask = flood_mask[1:h+1, 1:w+1]
        pixel_count = cv2.countNonZero(mask)
        # Solidity = Area / ConvexHullArea. 
        # High (>0.7) means compact/field-like. Low means spidery/leaking.
        solidity = 0
        if pixel_count > 0:
            contours_check, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours_check:
                c = max(contours_check, key=cv2.contourArea)
                hull = cv2.convexHull(c)
                hull_area = cv2.contourArea(hull)
                if hull_area > 0:
                    solidity = float(pixel_count) / hull_area
        
        print(f"   Level {i+1} Tolerances: Lo{lo} Up{up} -> Area: {pixel_count} px, Solidity: {solidity:.2f}")

        # Heuristic Logic:
        if pixel_count > (img_area * 0.90):
             print(f"   -> Stops: Covered >90% image.")
             break
        
        # Growth Check
        if best_area > 500:
            growth_factor = pixel_count / best_area
            
            if growth_factor > 5.0:
                 # It exploded. Is it a good explosion (valid field) or bad (leak)?
                 if solidity > 0.65:
                     print(f"   -> Accepted massive growth ({growth_factor:.1f}x) because shape is solid ({solidity:.2f}).")
                 else:
                     print(f"   -> Stops: Massive leak detected ({growth_factor:.1f}x) and shape is irregular ({solidity:.2f}).")
                     break
                 
        # If passed checks, update best
        best_contours = contours_check
        best_area = pixel_count
    
    return best_contours
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # 5. Flood Fill / Connected Components
    # We only want the region connected to the center, not ANY pixel of that color
    # Create a mask for floodFill (needs to be 2 pixels larger)
    h, w = mask.shape
    flood_mask = np.zeros((h+2, w+2), np.uint8)
    flood_fill_img = mask.copy()
    
    # Seed point is center
    # Check if center is actually within the color mask
    if mask[center_y, center_x] == 0:
        print("Note: Center pixel is not within threshold. Detection might fail.")
        # Try to find nearest valid pixel? Or just proceed.
    
    # Flood fill from center (255) to fill connected component
    cv2.floodFill(flood_fill_img, flood_mask, (center_x, center_y), 255)
    
    # The flood filled area is now effectively valid, but floodFill modifies in-place.
    # To isolate ONLY the connected component:
    # Any pixel that was 255 in original 'mask' might be disconnected.
    # We want to find contours only on the flood_fill result?
    # Actually, floodFill changes the value. Let's start with empty image.
    
    connected_mask = np.zeros_like(mask)
    # Copy original mask to connected_mask, then floodfill on connected_mask
    connected_mask[:] = mask[:]
    flood_mask = np.zeros((h+2, w+2), np.uint8)
    
    # FloodFill from center. Using value 128 to distinguish
    if mask[center_y, center_x] != 0:
        cv2.floodFill(connected_mask, flood_mask, (center_x, center_y), 128)
        
        # Now keep only pixels with value 128
        final_mask = cv2.inRange(connected_mask, 128, 128)
    else:
        # Fallback: if center isn't valid, look for closest valid pixel or just return all?
        # Let's return all matching colors for now if center is bad, or maybe just fail.
        print("   Center pixel out of range. Returning all matching regions.")
        final_mask = mask
    
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def pixel_to_latlon(px, py, width, height, center_lat, center_lon, zoom):
    """
    Convert pixel coordinates (px, py) to (Lat, Lon) using Web Mercator math.
    Assumes (px,py) is relative to the center of the image.
    """
    # World size in pixels at this zoom
    # Mapbox Static Images uses 512x512 tiles by default (unlike standard OSM 256x256)
    n = 2.0 ** zoom
    world_size_px = 512.0 * n
    
    # 1. Project Center Lat/Lon to Global Pixel Coordinates (Mercator)
    center_px_x = (center_lon + 180.0) / 360.0 * world_size_px
    
    lat_rad = math.radians(center_lat)
    center_px_y = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * world_size_px
    
    # 2. Calculate Global Pixel Coordinates of the target pixel
    # Image (0,0) is at (center_px_x - width/2, center_px_y - height/2)
    target_global_x = center_px_x - (width / 2.0) + px
    target_global_y = center_px_y - (height / 2.0) + py
    
    # 3. Unproject Global Pixel to Lat/Lon
    res_lon = (target_global_x / world_size_px) * 360.0 - 180.0
    
    n2 = math.pi - (2.0 * math.pi * target_global_y) / world_size_px
    res_lat = math.degrees(math.atan(0.5 * (math.exp(n2) - math.exp(-n2))))
    
    return res_lat, res_lon

def contour_to_wkt(contour, width, height, center_lat, center_lon, zoom):
    """Convert an OpenCV contour to WKT Polygon string."""
    points = []
    
    # Simplify contour slightly to reduce WKT size (epsilon 1% of arc length)
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.01 * peri, True)
    
    if len(approx) < 3:
        return None
        
    for point in approx:
        px, py = point[0]
        lat, lon = pixel_to_latlon(px, py, width, height, center_lat, center_lon, zoom)
        points.append(f"{lon} {lat}")
    
    # Close the loop
    points.append(points[0])
    
    return f"POLYGON (({', '.join(points)}))"
