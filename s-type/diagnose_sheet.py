import pygame
import os

pygame.init()
try:
    path = "assets/sprites/gradius_sheet_v3.png"
    # path = "assets/sprites/gradius_sheet_v2.png" # Backup
    if not os.path.exists(path):
        print(f"Error: {path} not found.")
    else:
        surf = pygame.image.load(path)
        print(f"Dimensions: {surf.get_size()}")
        
        # Scan for first non-transparent pixel
        found = False
        # Scan Row 136-151 for blobs
        print("Scanning Shield Row (Y=136-151)...")
        y_start = 136
        y_end = 151
        
        # Scan horizontal line at mid-point (approx y=143) to find distinct objects
        # or simple bounding box detection
        current_blob_start = -1
        blobs = []
        
        for x in range(surf.get_width()):
            # Check vertical column at x
            has_pixel = False
            for y in range(y_start, y_end):
                if surf.get_at((x, y))[3] > 0:
                    has_pixel = True
                    break
            
            if has_pixel:
                if current_blob_start == -1:
                    current_blob_start = x
            else:
                if current_blob_start != -1:
                    blobs.append((current_blob_start, x - current_blob_start))
                    current_blob_start = -1
                    
        print(f"Found {len(blobs)} blobs: {blobs}")
except Exception as e:
    print(f"Exception: {e}")
