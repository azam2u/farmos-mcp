import requests
import os

# User provided token
MAPBOX_TOKEN = "pk.eyJ1IjoiYXphbTJ1IiwiYSI6ImNta2twa3RoejFuemszcHB1d2lmcXBleDMifQ.CnaChrJUYvwa08Eg9ZrJrg"

def verify_mapbox():
    # Kyoto Imperial Palace coordinates (~35.025, 135.762)
    lat = 35.025
    lon = 135.762
    zoom = 16
    width = 600
    height = 400
    
    # Mapbox Static Images API URL
    url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{zoom}/{width}x{height}?access_token={MAPBOX_TOKEN}"
    
    print(f"Requesting image from: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            filename = "mapbox_test.jpg"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Success! Image saved to {filename}")
            print(f"Image size: {len(response.content)} bytes")
        else:
            print("Failed.")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_mapbox()
