# PSL API - Pakistan Sign Language API

This is a FastAPI-based backend for the Pakistan Sign Language Interpreter project.

## Features

- Sign language detection and inference
- Data capture for model training
- Model retraining
- Learning mode

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the API:
   ```
   uvicorn main:app --reload
   ```

## API Endpoints

The API provides the following endpoints:

- `GET /`: Root endpoint to check if the API is running
- `POST /start-openpose`: Start the OpenPose process
- `POST /stop-openpose`: Stop the OpenPose process
- `POST /capture`: Capture sign language data
- `GET /get-file-count`: Get the count of captured files
- `POST /delete-image`: Delete a captured image
- `POST /save-label`: Save captured data with a label
- `POST /retrain`: Retrain the model
- `POST /infer`: Perform inference on an image
- `POST /skip-sign`: Skip the current sign in learning mode
- `POST /start-learning`: Start the learning process
- `GET /get-alphabet/{index}`: Get alphabet data for learning mode

## Docker Support

You can build and run the API using Docker:

