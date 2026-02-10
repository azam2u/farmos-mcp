
import sys
import os
from farmOS import farmOS

def inspect_farm():
    print("Inspecting farmOS library...")
    try:
        # Dummy auth
        f = farmOS("https://try.farmos.net", "client_id", "client_secret")
        
        # Check attributes
        print("farm object attributes:", dir(f))
        
        if hasattr(f, 'file'):
            print("farm.file attributes:", dir(f.file))
            # Check methods on an endpoint object usually like get, send, delete
        
        # Check if there is a specific method for uploading
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_farm()
