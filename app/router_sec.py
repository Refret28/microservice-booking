import configparser
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import cv2


app = FastAPI()

config = configparser.ConfigParser()
config.read('config.ini')
rtsp = config['RTSP']['RTSP']

def generate_frames():
    cap = cv2.VideoCapture(rtsp)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.get("/mjpeg")
def mjpeg_stream():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")
