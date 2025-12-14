import pygame
from src.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT
from src.engine.entity import Entity
from src.game.sprite_factory import load_master_sheet

# Shared sheet loader helper (or just load in each for now to depend less on engine changes)
def get_sheet():
    return load_master_sheet()

class Projectile(Entity):
    def __init__(self, groups, x, y, speed_x, speed_y, color):
        super().__init__(groups, x, y)
        self.image.fill(color)
        self.image = pygame.transform.scale(self.image, (24, 12)) 
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pygame.math.Vector2(speed_x, speed_y)

    def update(self, *args):
        super().update(*args)
        if (self.rect.right < 0 or self.rect.left > INTERNAL_WIDTH or
            self.rect.bottom < 0 or self.rect.top > INTERNAL_HEIGHT):
            self.kill()

class NormalShot(Projectile):
    def __init__(self, groups, x, y):
        super().__init__(groups, x, y, 24, 0, (255, 255, 0))
        sheet = get_sheet()
        if sheet:
            # User specified: 145, 106 (Orange Sprite)
            # Assuming ~16x10 size based on spacing
            self.image = sheet.subsurface((145, 106, 16, 8)) 
            self.image = pygame.transform.scale(self.image, (24, 12)) 
        
class Missile(Projectile):
    def __init__(self, groups, x, y, dx=6, dy=6):
        super().__init__(groups, x, y, dx, dy, (255, 0, 0))
        sheet = get_sheet()
        if sheet:
            # User specified 45-degree missile at 130, 158 (8x8)
            # Pending full animation implementation later.
            self.image = sheet.subsurface((130, 158, 8, 8)) 
            self.image = pygame.transform.scale(self.image, (24, 24)) 
        
        # Logic for falling until ground...
    
    def update(self, *args):
        super().update(*args)
        if self.rect.bottom >= INTERNAL_HEIGHT - 30: 
            self.vel.y = 0
            self.vel.x = 9 
        else:
            self.vel.y = 6 
            self.vel.x = 3 

class Double(Projectile):
    def __init__(self, groups, x, y, direction_y=-1):
        super().__init__(groups, x, y, 15, 15 * direction_y, (0, 255, 255))
        sheet = get_sheet()
        if sheet:
            # User specified Double sprite at 133, 104 (6x6)
            # "Diagonal sprite"
            self.image = sheet.subsurface((133, 104, 6, 6)) 
            self.image = pygame.transform.scale(self.image, (18, 18)) # 3x Scale

class Laser(Projectile):
    def __init__(self, groups, x, y):
        # Laser is unique: huge hitbox, piercing (handled elsewhere?), animation.
        super().__init__(groups, x, y, 36, 0, (100, 100, 255))
        sheet = get_sheet()
        self.frames = []
        if sheet:
            # User specified: 112, 109 and 122, 109
            # Distance is 10px. Width is likely 10. Height maybe 4?
            f1 = sheet.subsurface((112, 109, 10, 4))
            f2 = sheet.subsurface((122, 109, 10, 4))
            
            # Scale to long beam
            self.frames.append(pygame.transform.scale(f1, (144, 24)))
            self.frames.append(pygame.transform.scale(f2, (144, 24)))
            
            self.image = self.frames[0]
            # Reset rect to match scaled size if needed, though Entity init did it with fallback color surf
            self.rect = self.image.get_rect(topleft=(x, y))
            
        self.animation_timer = 0
        
    def update(self, *args):
        super().update(*args)
        # Flicker Animation
        if self.frames:
            self.animation_timer += 1
            if self.animation_timer % 4 == 0: # Toggle every 4 frames
                idx = (self.animation_timer // 4) % 2
                self.image = self.frames[idx]
