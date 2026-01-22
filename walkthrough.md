# farmOS MCP Server Walkthrough

This guide explains how to use the farmOS MCP server to manage your farm assets using natural language in VS Code (Roo Code).

## 1. Prerequisites

*   VS Code with **Roo Code** extension installed.
*   **farmOS** instance running (e.g., `https://myfarm2u.farmos.net`).
*   **Python 3.11+** environment with `farmOS` library and `fastmcp` installed.
*   **MCP Server Configuration** in `Retry Logic` enabled (handled by the updated server code).

## 2. Server Configuration

Ensure your `farmos_mcp.py` is running or configured in Roo Code's MCP settings.

**File Path:** `/home/cvl/farmos_env/farmos_mcp.py`

**Environment Variables:**
*   `FARMOS_HOST`
*   `FARMOS_USER`
*   `FARMOS_PASSWORD`
*   `FARMOS_CLIENT_ID`
*   `FARMOS_CLIENT_SECRET`

## 3. Example Prompts (Robust)

The following prompts have been tested and verify that:
1.  Assets are created.
2.  Locations are created.
3.  Assets are **linked** to locations via Movement Logs (essential for farmOS 2.x).
4.  Timestamps are valid.

### Example 1: Watermelon (Complex Linking)
> Create a land asset named "Watermelon Patch" (type 'land', land_type 'field', is_location True).
>
> Then, create a plant asset named "Sugar Baby Watermelon" (type 'plant', plant_type 'Watermelon') located in "Watermelon Patch". Add the note "Harvest when tendril creates a loop".

### Example 2: Pumpkins
> Create a land asset named "Pumpkin Patch" (type 'land', land_type 'field', is_location True).
>
> Then, create a plant asset named "Giant Pumpkin" (type 'plant', plant_type 'Pumpkin') located in "Pumpkin Patch". Add the note "Check for vine borers".

## 4. Troubleshooting

### "Location is N/A"
*   **Cause:** The asset creation and linking happened too fast, or the tool definition in Roo Code was outdated.
*   **Solution:** Reload VS Code window (`Ctrl+Shift+P` -> "Reload Window"). The server now includes "Retry Logic" to wait for the location to appear.

### "422 Unprocessable Content"
*   **Cause:** Timestamp format included microseconds.
*   **Solution:** The server code has been patched to use clean ISO timestamps. Reload Window to apply.

### "Asset Created but not Linked"
*   **Cause:** Old tool logic used direct relationship updates instead of Movement Logs.
*   **Solution:** The server receives regular updates. Reload Window to ensure you are using the version that creates **Movement Logs**.

## 5. Verification
You can verify assets in the farmOS dashboard:
*   Go to **Assets** -> **Plants**.
*   Click on an asset (e.g., "Sugar Baby Watermelon").
*   Look at the "Current Location" field. It should say "Watermelon Patch".
*   Look at the **Logs** tab. You should see a "Move to Watermelon Patch" activity log.
