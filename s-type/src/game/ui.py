import pygame
from src.settings import SCREEN_HEIGHT, INTERNAL_HEIGHT, INTERNAL_WIDTH

class PowerUpBar:
    def __init__(self, surface, powerup_manager):
        self.surface = surface
        self.manager = powerup_manager
        self.font = pygame.font.SysFont("arial", 24) # 8 * 3
        
        # Dimensions
        self.bar_height = 48 # 16 * 3
        self.cell_width = 90 # 30 * 3
        count = len(self.manager.labels)
        self.start_x = (INTERNAL_WIDTH - (self.cell_width * count)) // 2
        self.y = INTERNAL_HEIGHT - self.bar_height - 6 # buffer scaled

    def draw(self):
        # Draw background bar
        # pygame.draw.rect(self.surface, (50, 50, 50), (self.start_x, self.y, self.cell_width * 6, self.bar_height))
        
        for i, label in enumerate(self.manager.labels):
            x = self.start_x + (i * self.cell_width)
            
            # Determine color
            current_idx = self.manager.meter_index
            bg_color = (100, 0, 0) # Inactive Reddish
            text_color = (200, 200, 200)
            
            if i == current_idx:
                bg_color = (255, 0, 0) # Active Bright Red (or Yellow/Orange flashing)
                text_color = (255, 255, 255)
            
            # Draw Cell
            pygame.draw.rect(self.surface, bg_color, (x, self.y, self.cell_width - 2, self.bar_height))
            
            # Draw Text
            # Logic to Hide text if "Active"/"Taken"
            show_text = True
            aw = self.manager.active_weapons
            
            if label == "MISSILE" and aw["missile"]:
                 show_text = False
            elif label == "DOUBLE" and aw["double"]:
                 show_text = False
            elif label == "LASER" and aw["laser"]:
                 show_text = False
            elif label == "OPTION" and aw["option"] >= 4:
                 show_text = False
            elif label == "?" and aw["shield"]:
                 show_text = False
            
            if show_text:
                lbl_surf = self.font.render(label[0:4], False, text_color) # Truncate for space
                self.surface.blit(lbl_surf, (x + 6, self.y + 10)) # Offsets scaled
