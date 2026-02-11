try:
    from transformers import Sam3TrackerModel
    print("SUCCESS: Sam3TrackerModel found!")
except ImportError as e:
    print(f"FAILURE: {e}")
