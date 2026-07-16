import os
import random
import yaml
from PIL import Image, ImageDraw

def generate_yolo_dataset():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(project_root, 'scratch', 'yolo_dataset')
    
    # Define subdirectories
    subdirs = [
        'images/train', 'images/val',
        'labels/train', 'labels/val'
    ]
    for subdir in subdirs:
        os.makedirs(os.path.join(dataset_dir, subdir), exist_ok=True)
        
    print(f"Created YOLO dataset directories in: {dataset_dir}")
    
    # 1. Create standard graphics templates to paste
    # OEM logo template
    logo_w, logo_h = 160, 160
    logo_tmpl = Image.new('RGB', (logo_w, logo_h), color=(15, 23, 42))
    draw_l = ImageDraw.Draw(logo_tmpl)
    draw_l.ellipse([10, 10, 150, 150], fill=(59, 130, 246), outline=(255, 255, 255), width=3)
    draw_l.text((45, 65), "OEM", fill=(255, 255, 255))
    
    # OK Button template
    ok_w, ok_h = 110, 45
    ok_tmpl = Image.new('RGB', (ok_w, ok_h), color=(34, 197, 94))
    draw_ok = ImageDraw.Draw(ok_tmpl)
    draw_ok.rectangle([0, 0, ok_w - 1, ok_h - 1], outline=(255, 255, 255), width=2)
    draw_ok.text((45, 15), "OK", fill=(255, 255, 255))
    
    # YES Button template
    yes_w, yes_h = 110, 45
    yes_tmpl = Image.new('RGB', (yes_w, yes_h), color=(59, 130, 246))
    draw_yes = ImageDraw.Draw(yes_tmpl)
    draw_yes.rectangle([0, 0, yes_w - 1, yes_h - 1], outline=(255, 255, 255), width=2)
    draw_yes.text((40, 15), "YES", fill=(255, 255, 255))
    
    # Configuration lists
    # Classes: 0: logo, 1: button_ok, 2: button_yes
    resolutions = [(1280, 720), (1920, 1080), (1024, 600)]
    bg_colors = [(15, 23, 42), (0, 0, 0), (30, 41, 59), (9, 9, 11), (24, 24, 27)]
    
    # Helper to generate a single image and label
    def create_sample(index, split):
        # Pick random resolution and background
        screen_w, screen_h = random.choice(resolutions)
        color = random.choice(bg_colors)
        
        img = Image.new('RGB', (screen_w, screen_h), color=color)
        draw = ImageDraw.Draw(img)
        
        annotations = []
        
        # Decide screen type: 0 = Booting screen (just logo), 1 = Disclaimer screen (logo + buttons or just buttons)
        screen_type = random.choice([0, 1])
        
        if screen_type == 0:
            # Booting screen: paste logo in the center (with small random offset)
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-50, 50)
            x = (screen_w - logo_w) // 2 + offset_x
            y = (screen_h - logo_h) // 2 + offset_y
            
            # Draw logo
            img.paste(logo_tmpl, (x, y))
            draw.text((x + 10, y + logo_h + 10), "Android Loading...", fill=(200, 200, 200))
            
            # Save label coordinates: class_id, center_x, center_y, width, height (normalized)
            cx = (x + logo_w / 2) / screen_w
            cy = (y + logo_h / 2) / screen_h
            nw = logo_w / screen_w
            nh = logo_h / screen_h
            annotations.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            
        else:
            # Disclaimer screen: draw background box
            box_x1, box_y1 = int(screen_w * 0.15), int(screen_h * 0.15)
            box_x2, box_y2 = int(screen_w * 0.85), int(screen_h * 0.85)
            draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=(9, 9, 11), outline=(100, 116, 139), width=2)
            draw.text((box_x1 + 40, box_y1 + 30), "SAFETY WARNING & USER PRIVACY AGREEMENT", fill=(255, 255, 255))
            
            # Sometimes include logo in top center of warning box
            include_logo = random.choice([True, False])
            if include_logo:
                lx = (screen_w - logo_w) // 2
                ly = box_y1 + 60
                img.paste(logo_tmpl, (lx, ly))
                cx = (lx + logo_w / 2) / screen_w
                cy = (ly + logo_h / 2) / screen_h
                nw = logo_w / screen_w
                nh = logo_h / screen_h
                annotations.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            
            # Place buttons: OK and YES
            # We place OK on the right side and YES on the left side of the warning box
            # Add some randomization to button coordinates
            y_btn = int(box_y2 - ok_h - 40 - random.randint(-15, 15))
            
            # OK button (class 1)
            ok_x = int(box_x2 - ok_w - 50 - random.randint(-20, 20))
            img.paste(ok_tmpl, (ok_x, y_btn))
            cx = (ok_x + ok_w / 2) / screen_w
            cy = (y_btn + ok_h / 2) / screen_h
            nw = ok_w / screen_w
            nh = ok_h / screen_h
            annotations.append(f"1 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            
            # YES button (class 2)
            yes_x = int(box_x1 + 50 + random.randint(-20, 20))
            img.paste(yes_tmpl, (yes_x, y_btn))
            cx = (yes_x + yes_w / 2) / screen_w
            cy = (y_btn + yes_h / 2) / screen_h
            nw = yes_w / screen_w
            nh = yes_h / screen_h
            annotations.append(f"2 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            
        # Save files
        img_filename = f"screen_{index:03d}.png"
        lbl_filename = f"screen_{index:03d}.txt"
        
        img.save(os.path.join(dataset_dir, f"images/{split}", img_filename))
        
        with open(os.path.join(dataset_dir, f"labels/{split}", lbl_filename), 'w') as f:
            f.write('\n'.join(annotations))

    # Generate train split (40 images)
    for i in range(1, 41):
        create_sample(i, 'train')
        
    # Generate validation split (20 images)
    for i in range(41, 61):
        create_sample(i, 'val')
        
    # 2. Write dataset.yaml configuration file
    dataset_yaml = {
        'path': dataset_dir.replace('\\', '/'), # Forward slashes for standard yaml parser
        'train': 'images/train',
        'val': 'images/val',
        'names': {
            0: 'logo',
            1: 'button_ok',
            2: 'button_yes'
        }
    }
    
    yaml_path = os.path.join(dataset_dir, 'dataset.yaml')
    with open(yaml_path, 'w') as f:
        yaml.dump(dataset_yaml, f, default_flow_style=False)
        
    print(f"Generated {40} training images and {20} validation images.")
    print(f"Created YOLO dataset yaml file at: {yaml_path}")

if __name__ == '__main__':
    generate_yolo_dataset()
