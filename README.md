## AAE4011 Group 1 - ROLAND and YOLO model training

**Course**: AAE4011 - Artificial Intelligence in Unmanned Autonomous Systems  
**Group Members**: WANG Xuanting,LONG Yiqi, HU Junye  
The Hong Kong Polytechnic University, Department of Aeronautical and Aviation Engineering

## Project Overview
This repository presents the complete replication and extension of the open-source [engcang/ROLAND](https://github.com/engcang/ROLAND) project within a standardized Gazebo simulation environment. The work fulfills course requirements, with particular emphasis on:

- Successful execution of the Jackal robot + UAV precision landing simulation
- Extraction of first-person UAV camera footage synchronized with the 3D pose data of the ground vehicle
- YOLO-based object detection model training and validation using simulation data
- Full working implementation and demonstration
    

## Directory Structure

```text
AAE4011-group1-ROLAND-and-AI-training/
│    
├── AAE4011/                  # ROS Catkin workspace (core simulation package)
│   ├── ROLAND/               # Ported original ROLAND project (jackal_package_for_gazebo + EKF)
│   ├── AAE4011_Vinsfusion/   # VINS-Fusion related packages
│   ├── CMakeLists.txt
│   └── .catkin_workspace
├── AAE4011_Vinsfusion/       # Additional VINS-Fusion workspace (top-level)
├── Gazebo_car_YOLO/          # YOLOv6 training and inference pipeline (AI module)
│   ├── dataset/              # Training/validation dataset
│   │   ├── images/
│   │   │   ├── train/
│   │   │   └── val/
│   │   └── labels/
│   │       ├── train/
│   │       └── val/
│   ├── gazebo_car/           # Training outputs (weights, metrics, PR curves, confusion matrices, etc.)
│   ├── train_script.py       # Training script (150 epochs, imgsz=1280, batch=10, geometric augmentations)
│   ├── vedieo3.mp4           # Demo inference video (first-person UAV view)
│   └── yolo26n.pt            # Trained model weights
├── .catkin_workspace
├── .gitignore
├── Presentation_Grp1.pdf     # Full project presentation
├── requirements.txt
└── README.md                 # This file
```

## Quick Start

### 1. Simulation Environment Setup
```bash
cd ~/AAE4011-group1-ROLAND-and-AI-training/AAE4011
catkin_make
source devel/setup.bash
```

Set Gazebo model path (execute once):
```bash
echo "export GAZEBO_MODEL_PATH=\$HOME/AAE4011-group1-ROLAND-and-AI-training/AAE4011/ROLAND/gazebo_maps/bounding_wall_world:\$HOME/AAE4011-group1-ROLAND-and-AI-training/AAE4011/ROLAND/gazebo_maps/common_models:\$GAZEBO_MODEL_PATH" >> ~/.bashrc
source ~/.bashrc
```

Launch the simulation (refer to exact launch files inside AAE4011/ROLAND/):

```bash
roslaunch ekf_landing world.launch      
roslaunch ekf_landing kalman.launch     
```
Control the Jackal robot using a keypad.  

### 2. Recording First-Person UAV Video + Synchronized 3D Car Coordinates  

As described in the project presentation (Methodology → Data Collection, pages 13–14):  

*  In Gazebo/RViz, switch to the UAV first-person camera view (/camera/image_raw topic).  
*  Record the screen using OBS Studio or rosbag record /camera/image_raw /tf /ekf/pose to capture:  
   First-person video (time-stamped)  
   3D coordinates of the ground vehicle (x, y, z) published via tf / EKF  
*  Extract frames from the recorded video using tools such as Ezgif.  
*  Synchronize 3D labels using the timestamp alignment between video frames and pose data.  

Example demonstration videos (same as presentation):  
https://youtu.be/HdqZ7y4VsfE   
https://youtu.be/ttil_f1V08EE

### 3. YOLO Model Training & Inference

```bash
cd ~/AAE4011-group1-ROLAND-and-AI-training/Gazebo_car_YOLO

conda create -n yolo_env python=3.8
conda activate yolo_env
pip install -r requirements.txt

python train_script.py --data dataset/auto.yaml --model yolo26n.pt # Train the model  
```

Run inference demo on https://www.youtube.com/watch?v=W2YqDLe378M to verify real-time car detection.
    

## Dependencies

All Python dependencies are listed in requirements.txt.  


## Components

- ROS-YOLO using OpenCV/OpenVINO code: from [here](https://github.com/engcang/ros-yolo-sort/tree/master/YOLO_and_ROS_ver)  
- Jackal Gazebo model: from [here](https://github.com/jackal)  
- Drone and Jackal controll joystick code: from [here](https://github.com/engcang/mavros-gazebo-application/blob/master/mavros_joy_controller.py) , also refer [here](https://github.com/engcang/mavros-gazebo-application/blob/master/README.md#mission--joystick-controller---supports-kobuki-and-jackal)  
- UWB Gazebo sensor plugin and message from uwb gazebo [plugin](https://github.com/valentinbarral/gazebosensorplugins) and [uwb ROS msg](https://github.com/GTEC-UDC/rosmsgs)  
- [VINS-Fusion](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion) frame_id and OpenCV edited version from [here](https://github.com/engcang/vins-application#-vins-fusion-1)  * camera_models package is edited to be compatible with OpenCV4  
- Gazebo [map](https://github.com/engcang/gazebo_maps) 
    

## Results & Demonstration

- YOLO model successfully trained and validated in simulation  
- Real-time detection accuracy confirmed in vedieo3.mp4  
- Full replication of ROLAND EKF + Gazebo environment achieved  
- All source code, dataset, trained weights, and documentation provided
    

## References

Original ROLAND repository: https://github.com/engcang/ROLAND

