#!/bin/bash

# 1. Move to the project directory
cd "$(dirname "$0")"

# 2. Ensure the script has access to the X server (for the HMI window)
export DISPLAY=:0

# 3. Optional: Fix for camera permission issues if they occur
# sudo chmod 666 /dev/video10

# 4. Run the application using the system Python
echo "Launching Top Camera System..."
python3 main.py

# 5. Prevent the window from closing instantly if an error occurs
if [ $? -ne 0 ]; then
    echo "------------------------------------------------"
    echo "ERROR: Application exited with a non-zero code."
    echo "Check 'top_camera.log' for the full traceback."
    echo "------------------------------------------------"
    read -p "Press Enter to exit..."
fi