import os
import shutil
from ultralytics import YOLO

def train_custom_yolo():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_yaml = os.path.join(project_root, 'scratch', 'yolo_dataset', 'dataset.yaml')
    
    # Path where we want to save our final model
    config_dir = os.path.join(project_root, 'config')
    os.makedirs(config_dir, exist_ok=True)
    final_model_path = os.path.join(config_dir, 'yolov8n_logo_button.pt')
    
    print(f"Loading pre-trained YOLOv8n model...")
    # Load pre-trained model (downloads automatically if not locally cached)
    model = YOLO('yolov8n.pt')
    
    print(f"Starting training on custom dataset: {dataset_yaml}")
    # Train the model
    # We set epochs=5 for low latency local verification
    results = model.train(
        data=dataset_yaml.replace('\\', '/'),
        epochs=5,
        imgsz=640,
        batch=4,
        project=os.path.join(project_root, 'scratch', 'runs').replace('\\', '/'),
        name='train_logo_button',
        exist_ok=True,
        verbose=True
    )
    
    # Copy best weights to the final destination in the config folder
    trained_best_path = os.path.join(project_root, 'scratch', 'runs', 'train_logo_button', 'weights', 'best.pt')
    if os.path.exists(trained_best_path):
        shutil.copy(trained_best_path, final_model_path)
        print(f"\nTraining completed successfully!")
        print(f"Custom YOLOv8n model weights copied to: {final_model_path}")
    else:
        print(f"\nError: Trained weights not found at expected location: {trained_best_path}")

if __name__ == '__main__':
    train_custom_yolo()
