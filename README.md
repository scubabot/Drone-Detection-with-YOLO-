# Drone Detection System — YOLOv8 on Jetson Orin Nano

A full end-to-end computer vision pipeline for real-time drone detection. This project covers everything from dataset preparation and model fine-tuning with YOLOv8x, to image/video inference and live camera testing on a Jetson Orin Nano with ModalAI VOXL hardware. Also includes ROS 2 integration for camera streaming and flight data recording.

---

## Table of Contents

1. [Hardware & Software Requirements](#hardware--software-requirements)
2. [Connecting to the Jetson Orin Nano](#connecting-to-the-jetson-orin-nano)
3. [Installing Ultralytics & YOLO on the Jetson](#installing-ultralytics--yolo-on-the-jetson)
4. [Preparing Your Dataset](#preparing-your-dataset)
5. [Training the Model](#training-the-model)
6. [Running Inference](#running-inference)
7. [Viewing & Transferring Results](#viewing--transferring-results)
8. [Camera Server Setup (VOXL)](#camera-server-setup-voxl)
9. [ROS 2 Integration](#ros-2-integration)
10. [Recording Flight Data](#recording-flight-data)
11. [Tips & Troubleshooting](#tips--troubleshooting)

---

## Hardware & Software Requirements

**Hardware**
- Jetson Orin Nano (8GB VRAM)
- ModalAI VOXL flight computer
- USB-to-serial adapter (for screen/serial connection)

**Software**
- Ubuntu (on Jetson)
- Python 3
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- ROS 2 Jazzy / Foxy
- `ffmpeg` for frame extraction
- `nmtui` for WiFi setup
- `screen` for serial connection

---

## Connecting to the Jetson Orin Nano

### Option 1 — SSH (recommended)
Once connected to the same WiFi network:

```bash
ssh <username>@<DEVICE_IP>
```

You should see: `<username>@ubuntu:~$`

### Option 2 — Serial via Screen
Find the port name:

```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

Connect:

```bash
sudo screen <PORT> 115200
```

### Setting Up WiFi via Screen
Once in the serial terminal:

```bash
sudo nmtui
```

Navigate to **"Activate a connection"**, select your network, enter credentials, then restart the device.

---

## Installing Ultralytics & YOLO on the Jetson

Run these commands on the Jetson after connecting via SSH:

```bash
pip3 install ultralytics --break-system-packages
pip3 install torch torchvision --break-system-packages
```

Verify the install worked:

```bash
yolo --version
python3 -c "from ultralytics import YOLO; print('Ultralytics ready')"
```

---

## Preparing Your Dataset

This project uses a custom drone image dataset built from video footage and labeled in Roboflow.

> **Dataset:** [ADD YOUR ROBOFLOW DATASET LINK HERE]
>  **Trained Model:** [ADD YOUR MODEL LINK HERE]

### Step 1 — Extract Frames from Video

Use `ffmpeg` to pull one frame per second from your footage:

```bash
mkdir -p ~/drone_video_frames
ffmpeg -i ~/Videos/<your_video_file>.webm -vf fps=1 ~/drone_video_frames/frame_%04d.jpg
```

This produces a folder of `.jpg` images, one per second of video. Adjust `fps=1` to extract more or fewer frames.

> A helper script for this step is available in [`scripts/video_to_frames.py`](scripts/video_to_frames.py)

### Step 2 — Upload to Roboflow

1. Go to [roboflow.com](https://roboflow.com) and open your project
2. Click **Upload**
3. Select all images from your frames folder (`Ctrl+A`) and drag them into Roboflow

### Step 3 — Label Images

- Draw bounding boxes around the drone in each image
- For images with no drone — leave them blank with no boxes (these are useful negative examples)
- Use **Auto-Label** to speed things up — it uses your existing model to pre-draw boxes for you to review and correct

### Step 4 — Generate & Export Dataset

1. Click **Generate**
2. Set your train / valid / test split
3. Click **Export** → choose **YOLOv8** format → download the ZIP

### Step 5 — Set Up Project Folder & Unzip

```bash
mkdir -p ~/drone_project/dataset
cd ~/drone_project
unzip ~/Downloads/<your_dataset_name>.zip -d ~/drone_project/dataset/
```

Your folder structure should look like this:

```
drone_project/
├── dataset/
│   ├── data.yaml
│   ├── train/
│   │   ├── images/
│   │   └── labels/
│   ├── valid/
│   │   ├── images/
│   │   └── labels/
│   └── test/
│       ├── images/
│       └── labels/
```

---

## Training the Model

Run training from the project directory:

```bash
cd ~/drone_project
yolo detect train model=best.pt data=dataset/data.yaml epochs=30 imgsz=640 batch=4 lr0=0.001 freeze=10
```

**Parameter breakdown:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| `model` | `best.pt` | Pretrained weights to fine-tune |
| `epochs` | `30` | Number of training passes |
| `imgsz` | `640` | Input image resolution |
| `batch` | `4` | Small batch to avoid out-of-memory on 8GB VRAM |
| `lr0` | `0.001` | Initial learning rate |
| `freeze` | `10` | Freeze first 10 layers (speeds up training) |

During training you will see a live table like this:

```
Epoch    GPU_mem    box_loss    cls_loss    dfl_loss
1/30     3.2G       1.523       2.341       1.234
2/30     3.2G       1.401       2.102       1.198
...
```

Trained weights are saved to: `~/drone_project/runs/detect/<train_run>/weights/best.pt`

### Viewing Training Results

```bash
ls ~/drone_project/runs/detect/<train_run>/
eog ~/drone_project/runs/detect/<train_run>/results.png
```

Copy all result plots to your Desktop:

```bash
cp ~/drone_project/runs/detect/<train_run>/*.png ~/Desktop/
```

---

## Running Inference

### On a Folder of Images

```bash
python3 -c "
from ultralytics import YOLO
model = YOLO('weight/best.pt')
model.predict(source='/home/<username>/<image_folder>/', save=True, project='/home/<username>/results', name='drone_test')
"
```

Output will say `"no detection"` for images with no drone found, and save annotated results to the specified project folder.

### On a Video File

```bash
cd ~/drone_project
yolo detect predict model=runs/detect/<train_run>/weights/best.pt \
  source=~/Videos/<your_video_file>.webm \
  save=True conf=0.5 iou=0.7
```

### On Live Drone Camera

```bash
cd ~/drone_project
yolo detect predict model=runs/detect/<train_run>/weights/best.pt \
  source=~/<image_folder>/ \
  save=True
```

---

## Viewing & Transferring Results

### Transfer Images to the Jetson

```bash
scp ~/<local_image_folder>/* <username>@<DEVICE_IP>:~/<remote_image_folder>/
```

### Transfer Results Back to Your Computer

```bash
scp -r <username>@<DEVICE_IP>:~/results/drone_test/ ~/Desktop/drone_results/
```

If the folder doesn't appear, try:

```bash
scp -r <username>@<DEVICE_IP>:~/results/drone_test/ ~/Desktop/
ls ~/Desktop/
```

### View Results on Device

```bash
eog ~/drone_project/runs/detect/predict/
```

---

## Camera Server Setup (VOXL)

Check if camera services are running:

```bash
voxl-inspect-services
```

Start the camera server:

```bash
systemctl start voxl-camera-server
```

Edit the config if needed:

```bash
vi /etc/modalai/voxl-camera-server.conf
```

Then stop and restart the service after any config changes.

Available camera streams: `tracking_front`, `tracking_down`, `tracking_back`

---

## ROS 2 Integration

### Start the ROS 2 Bridge (on VOXL)

```bash
ros2 run voxl_mpa_to_ros2 voxl_mpa_to_ros2_node
```

### Set Up ROS 2 Environment (on PC)

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
```

### Verify the Bridge is Running

```bash
ros2 topic echo /your/camera/topic
```

### Preview Camera Feed

```bash
ros2 run rqt_image_view rqt_image_view
```

Select your camera topic from the dropdown to wake up the bridge before recording.

---

## Recording Flight Data

### Record a Single Topic

```bash
ros2 bag record /hires_color -o <recording_name>
```

```bash
ros2 bag record /tracking_front/image_raw -o <recording_name> --storage mcap
```

### Record Multiple Topics

```bash
ros2 bag record /tracking_front /tracking_rear -o <recording_name>
```

Press `Ctrl+C` to stop recording.

### Inspect a Bag File

```bash
ros2 bag info <recording_name>
```

This shows topics recorded, message count, start/end times, and duration.

### Play Back a Recording

```bash
ros2 bag play <recording_name>
```

In a separate terminal, view the playback:

```bash
ros2 run rqt_image_view rqt_image_view
```

### Record via ADB Shell (on drone directly)

```bash
# Start bridge
ros2 run voxl_mpa_to_ros2 voxl_mpa_to_ros2_node

# Wake up bridge
ros2 topic echo /tracking_front --field header

# In another terminal — navigate and record
cd /data
mkdir -p my_recordings && cd my_recordings
ros2 bag record /tracking_front/image_raw -o <recording_name>_YYYYMMDD
```

---

## Tips & Troubleshooting

**Out of memory during training?**
Reduce batch size to `4` or lower. YOLOv8x is a large model and 8GB VRAM is tight with larger batches.

**Can't connect via SSH?**
Run `hostname -I` on the Jetson to confirm its current IP address, then retry.

**Camera server not starting?**
Run `voxl-inspect-services` to check status, then stop and restart `voxl-camera-server`.

**SCP file not showing up?**
Try copying directly to `~/Desktop/` and then run `ls ~/Desktop/` to confirm.

**ROS 2 bridge not responding?**
Make sure `ROS_DOMAIN_ID` matches on both terminals, and that you ran `rqt_image_view` to wake up the bridge before recording.

**Ultralytics not found after install?**
Try running `pip3 install ultralytics --break-system-packages --upgrade` and restart your terminal session.

---

## Project Structure

```
drone_project/
├── dataset/                   # Training data (from Roboflow)
├── scripts/
│   └── video_to_frames.py     # Helper: extract frames from video
├── runs/                      # Training outputs and inference results
│   └── detect/
│       ├── train*/            # Training run folders (weights, plots)
│       └── predict*/          # Inference result folders
└── results/                   # Detection output images
```

---

## Credits

- Dataset labeled and managed with [Roboflow](https://roboflow.com)
- Detection powered by [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- Deployed on [NVIDIA Jetson Orin Nano](https://developer.nvidia.com/embedded/jetson-orin-nano-devkit)
