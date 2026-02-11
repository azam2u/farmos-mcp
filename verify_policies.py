
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Helper for decorator mocking
def pass_through_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

# Mock libraries before importing
mock_fastmcp = MagicMock()
mock_fastmcp_instance = MagicMock()
mock_fastmcp.return_value = mock_fastmcp_instance
# Make @mcp.tool() return the pass_through decorator
mock_fastmcp_instance.tool.side_effect = pass_through_decorator

sys.modules['mcp.server.fastmcp'] = MagicMock()
sys.modules['mcp.server.fastmcp'].FastMCP = mock_fastmcp
sys.modules['farmOS'] = MagicMock()
sys.modules['greenery_utils'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['subprocess'] = MagicMock() # Mock globally for local import

# Mock env vars
os.environ["FARMOS_HOST"] = "mock_host"
os.environ["FARMOS_USER"] = "mock_user"
os.environ["FARMOS_PASSWORD"] = "mock_pass"

# Import target
# Import target
import farmos_mcp
import subprocess # Use the global mock to check calls

# Mock create_asset_from_sam3 to avoid external calls
farmos_mcp.create_asset_from_sam3 = MagicMock(return_value="Successfully created SAM3 Asset 'Test' (ID: 123)")
farmos_mcp.create_log = MagicMock()

def test_apple_policy():
    print("Testing Apple Policy...")
    # Reset mock
    subprocess.Popen.reset_mock()
    
    # Mock os.path.exists to True to simulate existing dataset
    with patch('os.path.exists', return_value=True):
        farmos_mcp.collect_fruit_data(fruit="apple", latitude=10.0, longitude=20.0, duration=15)
    
    # Check subprocess call
    if not subprocess.Popen.called:
        print("FAIL: subprocess.Popen not called")
        return

    args, _ = subprocess.Popen.call_args
    cmd_list = args[0]
    
    # Verify mapping
    cmd_str = " ".join(cmd_list)
    print(f"Command: {cmd_str}")
    
    # Verify timestamp in ID
    # azam2u/eval_apple2_YYYYMMDD_HHMM
    found_id = False
    for arg in cmd_list:
        if arg.startswith("--dataset.repo_id="):
            val = arg.split("=")[1]
            if "azam2u/eval_apple2_" in val:
                 print(f"PASS: Dataset ID has timestamp: {val}")
                 found_id = True
            else:
                 print(f"FAIL: Unexpected Dataset ID: {val}")
    
    if not found_id:
        print("FAIL: No dataset ID found")

    if "--resume" in cmd_list:
        print("FAIL: --resume should not be present")
    else:
        print("PASS: --resume check ok (not present)")

def test_orange_policy():
    print("\nTesting Orange Policy...")
    subprocess.Popen.reset_mock()
    
    res = farmos_mcp.collect_fruit_data(fruit="orange", latitude=10.0, longitude=20.0, duration=15)
    print(f"Result: {res}")
    
    if not subprocess.Popen.called:
        print("FAIL: subprocess.Popen not called")
        return

    args, _ = subprocess.Popen.call_args
    cmd_list = args[0]
    
    cmd_str = " ".join(cmd_list)
    print(f"Command: {cmd_str}")

    if "--dataset.repo_id=azam2u/eval_orange1" in cmd_list:
         print("PASS: Correct Dataset ID")
    else:
         print(f"FAIL: Expected azam2u/eval_orange1, got {cmd_list}")

    if "--policy.path=azam2u/detect_orange" in cmd_list:
         print("PASS: Correct Policy Path")
    else:
         print(f"FAIL: Expected azam2u/detect_orange, got {cmd_list}")

if __name__ == "__main__":
    test_apple_policy()
    test_orange_policy()
