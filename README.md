# Top Camera Palletizing & QR Detection System

## Overview

The **Top Camera Palletizing & QR Detection System** is an industrial computer vision solution designed for automated keg detection, QR code scanning, and pallet data synchronization.  
The system is optimized to run on **industrial edge devices** such as the **Advantech ICAM-540** and supports real-time operator interaction through a **Kivy-based HMI**.

It combines **YOLOv8-based object detection**, **QR code decoding**, **local persistence**, and **cloud communication** to ensure reliable palletizing operations even in unstable network conditions.

---

## Key Features

- Real-time top-camera keg detection
- QR code decoding using PyZbar
- YOLOv8-based object localization
- Industrial V4L2 camera support (ICAM-540)
- Local SQLite persistence for fail-safe operation
- Cloud REST API integration
- WebSocket-based live location updates
- Operator confirmation via HMI popups
- Automatic retry and recovery logic
- Offline-safe auto-sync mechanism

---

## Supported Platforms

- Ubuntu 20.04+
- Industrial Linux-based edge devices
- Advantech ICAM-540 (V4L2)
- Python 3.8+

---

## System Architecture

- **Camera Layer:** Industrial top-mounted camera (`/dev/video10`)
- **Detection Layer:** YOLOv8 + QR decoding
- **Logic Layer:** Pallet session controller and business rules
- **Persistence Layer:** Local SQLite database
- **UI Layer:** Kivy-based HMI
- **Cloud Layer:** REST APIs and WebSocket communication

---

## Installation

### Clone Repository

```bash
git clone https://github.com/<your-org>/top-camera-pallet-system.git
cd top-camera-pallet-system
````

### Create Virtual Environment (Optional)

```bash
python3 -m venv venv
source venv/bin/activate
```

(Windows: `venv\Scripts\activate`)

---

## System Dependencies (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y libzbar0 libgl1-mesa-glx
```

---

## Python Dependencies

Install required Python packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Required libraries include:

* `opencv-python`
* `ultralytics`
* `pyzbar`
* `kivy`
* `requests`
* `python-socketio`
* `websocket-client`

---

## Running the Application

### Set Permissions

```bash
chmod +x start_app.sh
sudo chmod 666 /dev/video10
```

### Start the System

#### Option 1: Using Launch Script (Recommended)

```bash
./start_app.sh
```

#### Option 2: Direct Execution

```bash
export DISPLAY=:0
python3 main.py
```

This starts:

* Camera stream
* Detection pipeline
* Operator HMI
* Cloud sync services

---

## System Workflow

1. System initializes and connects to the top camera.
2. YOLOv8 detects kegs entering the camera frame.
3. QR codes are decoded from detected regions.
4. Each detected keg ID is saved immediately to the local SQLite database.
5. WebSocket listens for location update commands from the cloud.
6. Operator receives a popup for location confirmation.
7. Confirmed pallet data is submitted to the cloud API.

---

## Configuration

All configurable values are maintained in `config.py`.


## Version

* **Version:** 2.0.0
* **Last Updated:** January 2026

---

## License

Proprietary – All rights reserved.
