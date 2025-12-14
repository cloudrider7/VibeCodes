import pygame
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def load_master_sheet():
    try:
        # V3 (Centrally Aligned)
        # Use resource_path to find the file in the bundle
        path = resource_path("assets/sprites/gradius_sheet_v3.png")
        sheet = pygame.image.load(path).convert_alpha()
        return sheet
    except FileNotFoundError:
        print(f"Error: Could not find sprite sheet at {path}")
        return None

class SpriteGenerator:
    @staticmethod
    def create_sprite(grid, palette, scale=1):
        rows = len(grid)
        cols = len(grid[0])
        surface = pygame.Surface((cols, rows), pygame.SRCALPHA)
        
        for y, row in enumerate(grid):
            for x, char in enumerate(row):
                if char in palette:
                    surface.set_at((x, y), palette[char])
        
        if scale > 1:
            surface = pygame.transform.scale(surface, (cols * scale, rows * scale))
            
        return surface

# Palettes
VIC_VIPER_PALETTE = {
    'w': (240, 240, 240), # White
    'b': (50, 50, 255),   # Blue
    'g': (100, 100, 100), # Grey
    'c': (100, 200, 255), # Cyan (Cockpit)
    'r': (255, 50, 50),   # Red (Engine)
}

# 16x8 Design (Facing Right)
VIC_VIPER_GRID = [
    "      bb        ",
    "      bbwww     ",
    "    bbwwwwwcc   ",
    "  bbwwwwwwwww   ",
    "bbbbwwwwwwwwww  ",
    "  bbwwwwwwwww   ",
    "    bbwwwww     ",
    "      bb        ",
]

OPTION_PALETTE = {
    'o': (255, 140, 0), # Orange
    'r': (255, 50, 0),  # Red-Orange
    'w': (255, 200, 150) # Highlight
}

OPTION_GRID = [
    "  oooo  ",
    " oooroo ",
    "oorrrroo",
    "oorrrroo",
    " oooroo ",
    "  oooo  ",
]
