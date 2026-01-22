import greenery_utils
import cv2
import os

LAT = 35.030775
LON = 135.578498
TOK = "pk.eyJ1IjoiYXphbTJ1IiwiYSI6ImNta2twa3RoejFuemszcHB1d2lmcXBleDMifQ.CnaChrJUYvwa08Eg9ZrJrg"
ZOOM = 18
WIDTH = 800
HEIGHT = 800

print(f"Downloading image for {LAT}, {LON}...")
try:
    img = greenery_utils.get_mapbox_image(LAT, LON, ZOOM, WIDTH, HEIGHT, TOK)
    filename = "user_requested_satellite.jpg"
    cv2.imwrite(filename, img)
    print(f"Saved to {os.path.abspath(filename)}")
except Exception as e:
    print(f"Error: {e}")
