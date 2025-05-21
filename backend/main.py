from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import os
import sys
import shutil
import json
import cv2
import numpy as np
import base64
from pathlib import Path
from datetime import datetime
import time
import io
import subprocess
import signal
import errno
import stat
from pydantic import BaseModel

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import PSL modules
import PSL.helper.db_helper as dbh
import PSL.helper.helperFunc as helper
import PSL.helper.move as move
import PSL.helper.scale as scale
import PSL.helper.plot as plot
import PSL.retrain as retrain
import PSL.alphabet_recognition.alphabet_recognition as alphabet
import PSL.word_recognition.word_recognition as word

# Define models
class CaptureRequest(BaseModel):
    duration: int
    mode: str = "alphabet"  # Can be "alphabet" or "word"

class InferenceRequest(BaseModel):
    image_base64: str
    speech_enabled: bool = False
    mode: str = "alphabet"  # Can be "alphabet" or "word"

class LabelRequest(BaseModel):
    label: str

class DeleteRequest(BaseModel):
    image_id: int

# Create FastAPI app
app = FastAPI(title="PSL API", description="Pakistan Sign Language API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# For serving static files
os.makedirs("backend/static/captured_images", exist_ok=True)
os.makedirs("backend/static/temp_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Global variables
openpose_process = None
last_detected_label = ""
last_inference_time = 0
inference_cooldown = 1.0  # 1 second cooldown between inferences
rem_file_names = []

# Helper functions for file operations
def handle_remove_readonly(func, path, exc):
    excvalue = exc[1]
    if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # 0777
        func(path)
    else:
        raise Exception

def clean_temp_directories():
    """Remove all temporary directories"""
    try:
        shutil.rmtree("Keypoints", ignore_errors=True, onerror=handle_remove_readonly)
        shutil.rmtree("backend/static/captured_images", ignore_errors=True, onerror=handle_remove_readonly)
        shutil.rmtree("backend/static/temp_images", ignore_errors=True, onerror=handle_remove_readonly)
        os.makedirs("backend/static/captured_images", exist_ok=True)
        os.makedirs("backend/static/temp_images", exist_ok=True)
        print('All temp directories cleaned')
    except Exception as e:
        print(f"Error cleaning temp directories: {e}")

def stop_openpose():
    """Stop OpenPose process if running"""
    global openpose_process
    if openpose_process:
        try:
            os.system("taskkill /f /im OpenPoseDemo.exe")
            openpose_process = None
            print("OpenPose stopped")
        except Exception as e:
            print(f"Error stopping OpenPose: {e}")

def start_openpose():
    """Start OpenPose process"""
    global openpose_process
    
    # Create temporary directories if they don't exist
    dirName = 'Keypoints'
    init_file = 'PSL\\000000000000_keypoints.json'
    
    try:
        os.makedirs(dirName, exist_ok=True)
        os.makedirs("backend/static/captured_images", exist_ok=True)
        os.makedirs("backend/static/temp_images", exist_ok=True)
        
        # Copy initializing file
        shutil.copy(init_file, dirName)
        print(f"Directory {dirName} ready")
    except Exception as e:
        print(f"Error creating directories: {e}")
    
    try:
        # Change directory to openpose
        os.chdir('bin\\openpose')
        openpose_process = subprocess.Popen(
            'bin\\OpenPoseDemo.exe --hand --write_json ..\\..\\Keypoints --net_resolution 128x128 --number_people_max 1', 
            shell=True
        )
        os.chdir('..\\..')
        print("OpenPose started")
    except Exception as e:
        print(f"Error starting OpenPose: {e}")
        os.chdir('..\\..')

def plot_pose(pose_points, hand_right_points, hand_left_points):
    """Plot pose using OpenCV"""
    POSE_PAIRS = [[1, 0], [1, 2], [1, 5], [2, 3], [3, 4], [5, 6], [6, 7],
                  [1, 8], [0, 15], [15, 17], [0, 16], [16, 18]]

    HAND_PAIRS = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [0, 9], [9, 10],
                  [10, 11], [11, 12], [0, 13], [13, 14], [14, 15], [15, 16], [0, 17], [17, 18],
                  [18, 19], [19, 20]]

    colors = [[0, 0, 130], [0, 0, 175], [0, 0, 210], [0, 0, 250],
              [0, 200, 160], [0, 180, 150], [0, 230, 186], [0, 255, 255],
              [82, 201, 8], [82, 204, 0], [92, 230, 0], [102, 252, 6],
              [197, 88, 17], [204, 82, 0], [179, 71, 0], [227, 94, 5],
              [204, 0, 163], [200, 0, 163], [196, 0, 163], [230, 0, 184]]

    background = "PSL\\BLACK_background.jpg"
    frame = cv2.imread(background)

    count = 0
    # Draw Skeleton
    for pair in POSE_PAIRS:
        partA = pair[0]
        partB = pair[1]

        if pose_points[partA] and pose_points[partB] and pose_points[partA][0] != 0 and pose_points[partA][1] != 0 and \
                pose_points[partB][0] != 0 and pose_points[partB][1] != 0:
            cv2.line(frame, pose_points[partA], pose_points[partB], colors[count], 10)
            cv2.circle(frame, pose_points[partA], 5, (0, 0, 255), thickness=10, lineType=cv2.FILLED)
            cv2.circle(frame, pose_points[partB], 5, (255, 255, 255), thickness=15, lineType=cv2.FILLED)
        count += 1

    count = 0
    for pair in HAND_PAIRS:
        partA = pair[0]
        partB = pair[1]

        if hand_right_points[partA] and hand_right_points[partB]:
            cv2.line(frame, hand_right_points[partA], hand_right_points[partB], colors[count], 10)
            cv2.circle(frame, hand_right_points[partA], 5, (0, 0, 255), thickness=3, lineType=cv2.FILLED)
            cv2.circle(frame, hand_right_points[partB], 5, (255, 255, 255), thickness=4, lineType=cv2.FILLED)
        count += 1

    count = 0
    for pair in HAND_PAIRS:
        partA = pair[0]
        partB = pair[1]

        if hand_left_points[partA] and hand_left_points[partB]:
            cv2.line(frame, hand_left_points[partA], hand_left_points[partB], colors[count], 10)
            cv2.circle(frame, hand_left_points[partA], 5, (0, 0, 255), thickness=3, lineType=cv2.FILLED)
            cv2.circle(frame, hand_left_points[partB], 5, (255, 255, 255), thickness=4, lineType=cv2.FILLED)
        count += 1

    return frame

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    stop_openpose()
    clean_temp_directories()

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Pakistan Sign Language API is running"}

@app.post("/start-openpose")
async def api_start_openpose():
    """Start OpenPose"""
    try:
        start_openpose()
        return {"message": "OpenPose started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting OpenPose: {str(e)}")

@app.post("/stop-openpose")
async def api_stop_openpose():
    """Stop OpenPose"""
    try:
        stop_openpose()
        return {"message": "OpenPose stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping OpenPose: {str(e)}")

@app.post("/capture")
async def capture(request: CaptureRequest, background_tasks: BackgroundTasks):
    """Capture sign language data"""
    global rem_file_names
    
    try:
        # Start OpenPose if not already running
        if not openpose_process:
            start_openpose()
        
        # Wait for the specified duration
        time.sleep(request.duration)
        
        # Stop OpenPose
        stop_openpose()
        
        # Process the captured data
        conf_threshold = 10
        file_names = []
        
        # Scan temporary folder for JSON files
        for entry in os.scandir('Keypoints'):
            if entry.is_file() and os.path.splitext(entry)[1] == ".json":
                file_names.append(entry.name)
        
        # Remove files with low confidence
        for x in range(len(file_names)):
            try:
                with open(f'Keypoints/{file_names[x]}', 'r') as f:
                    js = json.loads(f.read())
                
                for items in js['people']:
                    hand_right = items["hand_right_keypoints_2d"]
                
                conf_points = helper.confidencePoints(hand_right)
                confidence = helper.confidence(conf_points)
                
                if confidence < conf_threshold:
                    os.remove(f'Keypoints/{file_names[x]}')
            except Exception as e:
                print(f"Error processing file {file_names[x]}: {e}")
        
        # Plot and save captured data
        background = 'big_background.png'
        file_names = []
        
        for entry in os.scandir('Keypoints'):
            if entry.is_file() and os.path.splitext(entry)[1] == ".json":
                file_names.append(entry.name)
        
        frame = cv2.imread(background)
        i = 1
        rem_file_names = []
        
        for x in range(len(file_names)):
            try:
                with open(f'Keypoints/{file_names[x]}', 'r') as f:
                    js = json.loads(f.read())
                
                for items in js['people']:
                    hand_right = items["hand_right_keypoints_2d"]
                
                hand_points = helper.removePoints(hand_right)
                p1 = [hand_points[0], hand_points[1]]
                p2 = [hand_points[18], hand_points[19]]
                distance = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                
                result, points = scale.dummy_scalePoints(hand_points, distance)
                hand_right_results, hand_right_points = move.dummy_centerPoints(result)
                
                frame = plot.plot_dataset(hand_right_points, 'black')
                
                cv2.imwrite(f'backend/static/captured_images/{i}.jpg', frame)
                i += 1
                rem_file_names.append(file_names[x])
            except Exception as e:
                print(f"Error processing file {file_names[x]}: {e}")
        
        return {
            "message": "Capture completed successfully",
            "files_count": i - 1,
            "mode": request.mode
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during capture: {str(e)}")

@app.get("/get-file-count")
async def get_file_count():
    """Get the count of captured files"""
    try:
        names = []
        for entry in os.scandir('backend/static/captured_images'):
            names.append(entry.name)
        return {"count": len(names)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting file count: {str(e)}")

@app.post("/delete-image")
async def delete_image(request: DeleteRequest):
    """Delete a captured image"""
    global rem_file_names
    
    try:
        image_id = request.image_id
        if 0 < image_id <= len(rem_file_names):
            try:
                os.remove(f'Keypoints/{rem_file_names[image_id-1]}')
            except Exception as e:
                print(f"Error removing keypoint file: {e}")
        
        try:
            os.remove(f'backend/static/captured_images/{image_id}.jpg')
        except Exception as e:
            print(f"Error removing image file: {e}")
        
        return {"message": f"Image {image_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting image: {str(e)}")

@app.post("/save-label")
async def save_label(request: LabelRequest):
    """Save captured data with a label"""
    try:
        label = request.label.strip()
        
        # Find subfolder matching label
        for entry in os.scandir('data/datasets/alphabets_dataset'):
            if entry.name == label:
                # Create folder with timestamp
                now = datetime.now()
                timestamp = str(datetime.timestamp(now))
                dir_name = f"data/datasets/alphabets_dataset/{entry.name}/{timestamp}"
                
                os.makedirs(dir_name, exist_ok=True)
                
                # Copy keypoints to the created folder
                shutil.copytree("Keypoints", dir_name, dirs_exist_ok=True)
        
        # Clean up temp folders
        clean_temp_directories()
        
        return {"message": f"Data saved with label: {label}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving label: {str(e)}")

@app.post("/retrain")
async def retrain_model(background_tasks: BackgroundTasks):
    """Retrain the model"""
    try:
        background_tasks.add_task(retrain.re_train, 1)
        return {"message": "Model retraining started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retraining model: {str(e)}")

@app.post("/infer")
async def infer(request: InferenceRequest):
    """Perform inference on an image"""
    global last_detected_label, last_inference_time
    
    try:
        # Check if enough time has passed since the last inference
        current_time = time.time()
        if current_time - last_inference_time < inference_cooldown:
            return {"label": last_detected_label}
        
        last_inference_time = current_time
        
        # Start OpenPose if not already running
        if not openpose_process:
            start_openpose()
        
        # Get the latest JSON file
        latest_file = None
        for entry in os.scandir('Keypoints'):
            if entry.is_file() and os.path.splitext(entry)[1] == ".json":
                latest_file = entry.name
        
        if not latest_file:
            return {"label": "No data available"}
        
        try:
            with open(f'Keypoints/{latest_file}', 'r') as f:
                js = json.loads(f.read())
            
            for items in js['people']:
                pose = items["pose_keypoints_2d"]
                hand_right = items["hand_right_keypoints_2d"]
                hand_left = items["hand_left_keypoints_2d"]
            
            pose_points = helper.removePoints(pose)
            pose_points_joined = helper.join_points(pose_points)
            
            hand_right_points = helper.removePoints(hand_right)
            hand_right_points_joined = helper.join_points(hand_right_points)
            
            hand_left_points = helper.removePoints(hand_left)
            hand_left_points_joined = helper.join_points(hand_left_points)
            
            frame = plot_pose(pose_points_joined, hand_right_points_joined, hand_left_points_joined)
            
            cv2.imwrite(f'backend/static/temp_images/{latest_file}.jpg', frame)
            
            # Perform inference
            if request.mode == "alphabet":
                label = alphabet.match_ann(f'Keypoints/{latest_file}')
            else:
                label = word.match_ann(f'Keypoints/{latest_file}')
            
            if label not in ["no match", "no confidence"]:
                last_detected_label = label
            
            return {
                "label": label if label not in ["no match", "no confidence"] else last_detected_label,
                "image_path": f"/static/temp_images/{latest_file}.jpg"
            }
        except Exception as e:
            print(f"Error processing JSON: {e}")
            return {"label": last_detected_label}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during inference: {str(e)}")

# Skip sign endpoint for the learning feature
@app.post("/skip-sign")
async def skip_sign():
    """Skip the current sign in learning mode"""
    return {"message": "Sign skipped successfully"}

# Learn mode endpoints
@app.post("/start-learning")
async def start_learning():
    """Start the learning process"""
    try:
        # Start OpenPose if not already running
        if not openpose_process:
            start_openpose()
        
        return {"message": "Learning mode started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting learning mode: {str(e)}")

@app.get("/get-alphabet/{index}")
async def get_alphabet(index: int):
    """Get alphabet data for learning mode"""
    try:
        # In the original code, this simply returns an index to load an image
        # The frontend would load the image from "images/alphabet/{index}.png"
        return {"index": index}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting alphabet: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
