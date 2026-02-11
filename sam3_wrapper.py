import argparse
import sys
import json
import numpy as np
import torch
from PIL import Image
from transformers import Sam3TrackerModel, Sam3TrackerProcessor
import cv2
import math

# We reuse the geometry logic from our existing utils
try:
    import greenery_utils
except ImportError:
    pass

def pixel_to_latlon(px, py, width, height, center_lat, center_lon, zoom):
    # World size in pixels at this zoom
    n = 2.0 ** zoom
    world_size_px = 512.0 * n  # 512 for Mapbox High Res
    
    # 1. Project Center Lat/Lon to Global Pixel Coordinates (Mercator)
    center_px_x = (center_lon + 180.0) / 360.0 * world_size_px
    
    lat_rad = math.radians(center_lat)
    center_px_y = (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * world_size_px
    
    # 2. Calculate Global Pixel Coordinates of the target pixel (px, py)
    # (px, py) inputs are 0-indexed from Top-Left of the image
    
    # Offset from center of image
    offset_x = px - (width / 2.0)
    offset_y = py - (height / 2.0)
    
    target_px_x = center_px_x + offset_x
    target_px_y = center_px_y + offset_y
    
    # 3. Operations reversed: Global Pixels -> Lat/Lon
    
    # Lon
    lon = (target_px_x / world_size_px) * 360.0 - 180.0
    
    # Lat
    y_norm = 1.0 - (target_px_y / world_size_px) * 2.0
    lat = math.degrees(math.atan(math.sinh(y_norm * math.pi)))
    
    return lat, lon

def run_sam3(image_path, lat, lon, zoom):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Load Model (SAM3)
    model = Sam3TrackerModel.from_pretrained("facebook/sam3").to(device)
    processor = Sam3TrackerProcessor.from_pretrained("facebook/sam3")

    # Load Image
    img_pil = Image.open(image_path).convert("RGB")
    width, height = img_pil.size
    
    # Center Point Calculation
    # We assume we want to segment the object at the exact center of the requested image
    x = width // 2
    y = height // 2
    
    # Prepare Inputs
    # shape: [image, object, points, 2]
    # Reverting to Point Prompt as per user request (Box method was less accurate)
    input_points = [[[[x, y]]]]
    input_labels = [[[1]]]

    inputs = processor(
        images=img_pil,
        input_points=input_points,
        input_labels=input_labels,
        return_tensors="pt",
    ).to(device)

    # Inference
    with torch.no_grad():
        outputs = model(**inputs)

    # Post-process
    masks = processor.post_process_masks(outputs.pred_masks.cpu(), inputs["original_sizes"])[0]
    scores = outputs.iou_scores.squeeze().cpu().numpy()
    
    # Get best mask
    best_idx = int(np.argmax(scores))
    best_mask = masks[0, best_idx].numpy().astype(np.uint8) # 0 or 1
    
    # Convert Mask to Contours
    # OpenCV requires uint8 image
    contours, _ = cv2.findContours(best_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return json.dumps({"error": "No contours found in mask."})
        
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Simplify contour slightly to reduce WKT size
    epsilon = 0.002 * cv2.arcLength(largest_contour, True)
    approx_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    # Convert points to Lat/Lon
    wkt_points = []
    for point in approx_contour:
        px, py = point[0]
        p_lat, p_lon = pixel_to_latlon(px, py, width, height, lat, lon, zoom)
        wkt_points.append(f"{p_lon} {p_lat}") # WKT is LON LAT
    
    # Close the loop
    wkt_points.append(wkt_points[0])
    
    wkt_string = f"POLYGON (({', '.join(wkt_points)}))"
    
    result = {
        "status": "success",
        "wkt": wkt_string,
        "score": float(scores[best_idx]),
        "area_pixels": float(cv2.contourArea(largest_contour))
    }
    
    return json.dumps(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to satellite image")
    parser.add_argument("--lat", type=float, required=True, help="Center Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Center Longitude")
    parser.add_argument("--zoom", type=int, default=18, help="Mapbox Zoom Level")
    
    args = parser.parse_args()
    
    try:
        output = run_sam3(args.image, args.lat, args.lon, args.zoom)
        print(output)
    except Exception as e:
        err = {"status": "error", "message": str(e)}
        print(json.dumps(err))
