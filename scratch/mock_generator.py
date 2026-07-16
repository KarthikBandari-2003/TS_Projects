import os
from PIL import Image, ImageDraw, ImageFont

def create_directory_structure():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subdirs = ['config', 'images', 'logs', 'screenshots', 'reports', 'modules']
    for folder in subdirs:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
    print("Directory structure created successfully.")

def generate_mock_images():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    images_dir = os.path.join(base_dir, 'images')
    scratch_dir = os.path.join(base_dir, 'scratch')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(scratch_dir, exist_ok=True)

    # 1. Create logo template (e.g. blue circle with "OEM" text)
    logo_img = Image.new('RGB', (200, 200), color=(15, 23, 42)) # Deep slate background
    draw = ImageDraw.Draw(logo_img)
    draw.ellipse([20, 20, 180, 180], fill=(59, 130, 246), outline=(255, 255, 255), width=4) # Blue circle
    draw.text((60, 85), "OEM", fill=(255, 255, 255))
    logo_path = os.path.join(images_dir, 'logo.png')
    logo_img.save(logo_path)
    print(f"Saved Logo template to {logo_path}")

    # 2. Create OK button template
    ok_img = Image.new('RGB', (120, 50), color=(34, 197, 94)) # Green background
    draw = ImageDraw.Draw(ok_img)
    draw.rectangle([0, 0, 119, 49], outline=(255, 255, 255), width=2)
    draw.text((45, 18), "OK", fill=(255, 255, 255))
    ok_path = os.path.join(images_dir, 'ok_button.png')
    ok_img.save(ok_path)
    print(f"Saved OK button template to {ok_path}")

    # 3. Create YES button template
    yes_img = Image.new('RGB', (120, 50), color=(59, 130, 246)) # Blue background
    draw = ImageDraw.Draw(yes_img)
    draw.rectangle([0, 0, 119, 49], outline=(255, 255, 255), width=2)
    draw.text((45, 18), "YES", fill=(255, 255, 255))
    yes_path = os.path.join(images_dir, 'yes_button.png')
    yes_img.save(yes_path)
    print(f"Saved YES button template to {yes_path}")

    # 4. Generate mock screen: Boot phase 1 (Black/Loading Screen)
    screen_w, screen_h = 1280, 720
    boot1 = Image.new('RGB', (screen_w, screen_h), color=(0, 0, 0))
    draw_boot1 = ImageDraw.Draw(boot1)
    draw_boot1.text((560, 340), "Android Automotive booting...", fill=(100, 100, 100))
    boot1_path = os.path.join(scratch_dir, 'mock_boot_1.png')
    boot1.save(boot1_path)

    # 5. Generate mock screen: Boot phase 2 (Logo Active)
    boot2 = Image.new('RGB', (screen_w, screen_h), color=(15, 23, 42))
    # Paste logo in the center
    logo_x = (screen_w - 200) // 2
    logo_y = (screen_h - 200) // 2
    boot2.paste(logo_img, (logo_x, logo_y))
    draw_boot2 = ImageDraw.Draw(boot2)
    draw_boot2.text((580, 500), "Starting System...", fill=(200, 200, 200))
    boot2_path = os.path.join(scratch_dir, 'mock_boot_2.png')
    boot2.save(boot2_path)

    # 6. Generate mock screen: Disclaimer with dynamic OK button
    disclaimer = Image.new('RGB', (screen_w, screen_h), color=(30, 41, 59)) # Slate background
    draw_disc = ImageDraw.Draw(disclaimer)
    # Draw disclaimer box
    draw_disc.rectangle([200, 100, 1080, 620], fill=(15, 23, 42), outline=(100, 116, 139), width=3)
    draw_disc.text((450, 140), "SAFETY DISCLAIMER & AGREEMENT", fill=(248, 250, 252))
    disclaimer_text = (
        "Please drive safely and obey traffic rules.\n"
        "Usage of this infotainment system while driving is at your own risk.\n"
        "Do you agree to the terms and conditions to continue?"
    )
    draw_disc.text((300, 240), disclaimer_text, fill=(203, 213, 225))
    
    # Place buttons at dynamic/non-hardcoded locations
    # OK Button at x=850, y=520 (bounding box: 850, 520, 970, 570)
    # YES Button at x=350, y=520
    disclaimer.paste(ok_img, (850, 520))
    disclaimer.paste(yes_img, (350, 520))
    disclaimer_path = os.path.join(scratch_dir, 'mock_disclaimer.png')
    disclaimer.save(disclaimer_path)

    # Write a companion metadata JSON for Mock OCR to read easily
    # This simulates OCR engine results for the mock screen
    import json
    ocr_metadata = {
        "mock_disclaimer.png": [
            {"text": "SAFETY", "box": [450, 140, 520, 160]},
            {"text": "DISCLAIMER", "box": [530, 140, 650, 160]},
            {"text": "YES", "box": [350, 520, 470, 570]},
            {"text": "OK", "box": [850, 520, 970, 570]},
            {"text": "terms", "box": [300, 300, 350, 320]}
        ]
    }
    with open(os.path.join(scratch_dir, 'mock_ocr_metadata.json'), 'w') as f:
        json.dump(ocr_metadata, f, indent=4)

    # 7. Generate mock screen: Success/Home screen
    home = Image.new('RGB', (screen_w, screen_h), color=(15, 23, 42))
    draw_home = ImageDraw.Draw(home)
    # Header
    draw_home.rectangle([0, 0, screen_w, 60], fill=(30, 41, 59))
    draw_home.text((50, 20), "12:00 PM | LTE | Temp 22 C", fill=(255, 255, 255))
    # Icons
    draw_home.rectangle([200, 200, 400, 400], fill=(59, 130, 246), outline=(255,255,255), width=2)
    draw_home.text((270, 290), "Navigation", fill=(255, 255, 255))
    draw_home.rectangle([540, 200, 740, 400], fill=(16, 185, 129), outline=(255,255,255), width=2)
    draw_home.text((615, 290), "Media", fill=(255, 255, 255))
    draw_home.rectangle([880, 200, 1080, 400], fill=(245, 158, 11), outline=(255,255,255), width=2)
    draw_home.text((945, 290), "Settings", fill=(255, 255, 255))
    
    draw_home.text((500, 550), "Home Screen Loaded Successfully", fill=(34, 197, 94))
    home_path = os.path.join(scratch_dir, 'mock_home.png')
    home.save(home_path)

    print("Generated all mock screen and template images in scratch/ and images/")

if __name__ == '__main__':
    create_directory_structure()
    generate_mock_images()
