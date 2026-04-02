from roboflow import Roboflow
from ultralytics import YOLO
import os
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    # --- Paste snippet from Roboflow here. Omit the import commands ---

    api_key = os.getenv("ROBOFLOW_API_KEY")
    rf = Roboflow(api_key)
    project = rf.workspace("automated-game-bot").project("screw-yquuz-6ltpr")
    version = project.version(3)
    dataset = version.download("yolo26")
                    

    # --------  -----------------------
    print("Dataset downloaded.")
    model = YOLO("yolov8n.pt")
    print("Starting training...")

    results = model.train(
                data=f"{dataset.location}/data.yaml",
                epochs=300,
                imgsz=512,
                batch=16, # Significantly increased batch size for the RTX 5070
                device=0,
                workers=8, # Utilize the multi-core Ryzen CPU for faster data loading
                patience=30,
                plots=True
            )

    print("Training complete!")