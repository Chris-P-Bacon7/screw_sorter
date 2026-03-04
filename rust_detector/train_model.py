from roboflow import Roboflow
from ultralytics import YOLO
import os
from dotenv import load_dotenv

load_dotenv(os.path.join("rust_detector", ".env"))

# --- Paste snippet from Roboflow here. Omit the import commands ---

api_key = os.getenv("API_KEY")
rf = Roboflow(api_key)
project = rf.workspace("elevator-0iq4p").project("screw-yquuz")
version = project.version(4)
dataset = version.download("yolo26")

# -------------------------------
print("Dataset downloaded.")
model = YOLO("yolov8l.pt")
print("Starting training...")

results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=300,
    imgsz=640,
    batch=4,
    device="cpu",
    patience=30,
    plots=True
)

print("Training complete!")