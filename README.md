# Marker-Free Drone-to-Drone Detection
 
This package gives a ModalAI Starling 2 the ability to see and identify other drones using only its onboard cameras — no GPS, no AprilTags, no external markers.
 
It uses a custom-trained YOLOv8 model converted to TensorFlow Lite and deployed on the VOXL 2's onboard `voxl-tflite-server`, running inference in real time on the drone's front tracking camera. It's part of a larger effort at the SCUBA Lab at Florida Atlantic University to build a fully autonomous multi-drone system that operates in GPS-denied environments.
 
Check out the first live onboard detection below:
 
## Demo
 
> *Demo video coming soon — first live detection confirmed April 26, 2026* 🎉
 
<!-- Once you have media, replace with:
![Detection Demo](results/demo/detection_sample.gif)
-->
 
## Hardware
 
- ModalAI Starling 2
- NVIDIA Jetson Orin Nano
- VOXL 2 front tracking camera
- ModalAI `voxl-tflite-server` (SDK 1.6.0+)
## Repository Structure
 
```
drone_detection/
├── README.md
├── requirements.txt
├── train.py
├── inference_test.py
├── export_tflite.py                   # Exports best.pt → TFLite for Starling 2
├── dataset/
│   ├── data.yaml
│   ├── train/
│   ├── valid/
│   └── test/
├── weights/
│   ├── best.pt                        # Best YOLOv8 PyTorch weights
│   └── drone_detector.tflite          # Deployed TFLite model
└── results/
    ├── training_runs/                 # Loss curves and metrics per training run
    └── demo/                          # Detection demo footage
```
 
 
## Dependencies
 
- Python 3.8+
- [Ultralytics YOLOv8](https://docs.ultralytics.com)
- TensorFlow 2.19.0 (for TFLite export)
- ModalAI VOXL SDK 1.6.0+
- ROS 2 Jazzy (for data collection)
- Roboflow (dataset management)
## Installation
 
### 1. Clone the repository
 
```bash
git clone https://github.com/<your-username>/drone_detection.git
cd drone_detection
```
 
### 2. Set up Python environment
 
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
 
### 3. Set up the dataset
 
Export your dataset from Roboflow in **YOLOv8 format**, then:
 
```bash
mkdir -p ~/drone_project/dataset
unzip ~/Downloads/<your_dataset>.zip -d ~/drone_project/dataset/
```
 
## Training
 
Training was done iteratively — images were collected directly from the Starling 2's tracking camera, labeled in Roboflow, and used to retrain after each round. The dataset grew from ~80 images to over 3,000 across more than a dozen training runs, with each round targeting whatever the current model struggled with (false positives, upside-down poses, far-distance detection).
 
```bash
cd ~/drone_project
yolo detect train \
  model=best.pt \
  data=dataset/data.yaml \
  epochs=50 \
  imgsz=640 \
  batch=4 \
  lr0=0.0005 \
  freeze=10 \
  patience=20
```
 
`batch=4` keeps memory usage within 8GB VRAM. `freeze=10` freezes the first 10 backbone layers to speed up fine-tuning from the pretrained weights.
 
Training results are saved to:
```
runs/detect/<train_run>/weights/best.pt
```
 
## Training Results
 
| Run | Epochs | mAP@0.5 | mAP@0.5-95 | Precision | Recall |
|-----|--------|---------|-----------|-----------|--------|
| train | 50 | 0.770 | 0.558 | 0.798 | 0.757 |
| train2 | 21 | 0.778 | 0.517 | 0.858 | 0.732 |
| train3 | 100 | 0.944 | 0.672 | 0.945 | 0.915 |
| train4 | 50 | 0.964 | 0.706 | 0.980 | 0.938 |
| train5 | 50 | 0.972 | 0.735 | 0.979 | 0.954 |
| train6 | 35 | 0.984 | 0.590 | 0.976 | 0.947 |
| **train7** | 35 | **0.992** | **0.626** | **0.983** | **0.981** |
| train12 | 32 | 0.953 | 0.527 | 0.951 | 0.903 |
| train13 | 29 | 0.951 | 0.526 | 0.960 | 0.894 |
| **train18** | **20** | **0.953** | **0.538** | **0.962** | **0.920** |
 
train9, train14, train17, and train-2/train-3 were incomplete or interrupted runs with no final metrics recorded.
 
**Best validation mAP:** train7 at 0.992 | **Deployed model:** train18
 
train7 achieved the highest mAP on the validation set but produced significant false positives on real drone footage — misclassifying background objects as drones. train18 is slightly lower on paper but far more precise in real-world conditions, making it the better deployed model. This is a good reminder that validation metrics don't always reflect real-world performance.
 
## Usage
 
### Running inference locally
 
```bash
yolo detect predict \
  model=runs/detect/train18/weights/best.pt \
  source=<path_to_images_or_video> \
  save=True conf=0.5 iou=0.7
```
 
Add `max_det=1` to limit the model to one detection per frame, which eliminates the double-bounding-box issue seen on some frames:
 
```bash
yolo detect predict model=runs/detect/train18/weights/best.pt \
  source=<video> save=True conf=0.5 iou=0.7 max_det=1
```
 
View results:
 
```bash
eog ~/drone_project/runs/detect/predict*/
vlc ~/drone_project/runs/detect/predict*/*.avi
```
 
### Deploying to the Starling 2
 
**Step 1 — Export to TFLite**
 
```bash
python3 -m venv ~/tflite-export-env
source ~/tflite-export-env/bin/activate
pip install ultralytics tensorflow==2.19.0
 
yolo export model=runs/detect/train18/weights/best.pt format=tflite imgsz=320 half=True
```
 
**Step 2 — Push to drone**
 
```bash
adb push runs/detect/train18/weights/best_saved_model/best_float16.tflite \
  /usr/bin/dnn/drone_detector.tflite
```
 
**Step 3 — Update the config**
 
```bash
adb shell
vi /etc/modalai/voxl-tflite-server.conf
```
 
```json
{
  "skip_n_frames": 0,
  "model": "/usr/bin/dnn/drone_detector.tflite",
  "input_pipe": "/run/mpa/tracking_front_misp_grey/",
  "delegate": "gpu",
  "requires_labels": true,
  "labels": "/usr/bin/dnn/drone_labels.txt",
  "allow_multiple": false,
  "output_pipe_prefix": "drone_detector"
}
```
 
**Step 4 — Restart and verify**
 
```bash
systemctl restart voxl-tflite-server
journalctl -u voxl-tflite-server -f
```
 
## Data Collection
 
Camera data was recorded directly from the drone using ROS 2 bags via `adb shell`. One non-obvious thing: the ROS 2 bridge needs to be "woken up" with a dummy subscriber before recording — otherwise the bag file will record 0 messages even though it appears to work.
 
```bash
# Terminal 1 — start the MPA-to-ROS2 bridge
ros2 run voxl_mpa_to_ros2 voxl_mpa_to_ros2_node
 
# Terminal 2 — wake up the bridge (required before recording)
ros2 topic echo /tracking_front --field header
 
# Terminal 3 — record
cd /data && mkdir -p my_recordings && cd my_recordings
ros2 bag record /tracking_front/image_raw -o recording_YYYYMMDD
 
# Verify it actually captured frames
ros2 bag info recording_YYYYMMDD
```
 
Message count should be well above 0. If it shows 0, the bridge wasn't fully active before recording started.
 
## Troubleshooting
 
**Zero detections after deployment:** Check your model filename. If it matches any of ModalAI's default model names (e.g. `yolov5_float16_quant.tflite`), rename it to something unique and restart the service.
 
**voxl-tflite-server not starting:** Verify VOXL SDK version with `voxl-version` — must be 1.6.0 or higher. Check the model file path in the config matches where you actually pushed it.
 
**ROS 2 bag records 0 messages:** Run a `ros2 topic echo` on the camera topic before starting the bag record to wake up the bridge. See Data Collection above.
 
**Jetson PyTorch install fails:** The Jetson uses an ARM chip, so standard pip installs for PyTorch won't work. Pull from NVIDIA's Jetson package index instead and install PyTorch, Torchvision, and Ultralytics in that order.
 
**Model drawing multiple bounding boxes on the same drone in a single frame:** Add `max_det=1` to your predict command to limit the model to one detection per frame:
 
```bash
yolo detect predict model=runs/detect/train18/weights/best.pt \
  source=<video> save=True conf=0.5 iou=0.7 max_det=1
```
 
**Model detecting random objects as drones (false positives):** Add negative examples to your dataset — images with no drone present and no bounding boxes. Without them, the model has never been shown what "not a drone" looks like and will confidently misclassify background clutter. This was the single most effective fix across all training runs and eliminated detections of things like pillows, pictures, and cage walls.
 
**Model accurate at close range but misses at distance:** Add more labeled images of the drone at farther distances. This was the primary failure mode after Training 4 and was addressed in subsequent runs.
 
## About
 
**SCUBA Lab — Florida Atlantic University**  
Researcher: Emily King | Mentor: Dr. Pratik Mukherjee  
Supported by the FAU Office of Undergraduate Research and Inquiry

