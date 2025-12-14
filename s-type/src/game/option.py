import pygame
from src.engine.entity import Entity
from src.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT
from src.game.weapons import NormalShot, Missile, Double, Laser
from src.game.sprite_factory import SpriteGenerator, OPTION_PALETTE, OPTION_GRID

class Option(Entity):
    def __init__(self, groups, x, y, player, delay_frames=15, bullet_groups=None):
        super().__init__(groups, x, y)
        
        from src.game.sprite_factory import load_master_sheet
        sheet = load_master_sheet()
        
        self.frames = []
        if sheet:
             # User specified 147, 78, 16, 12 (Correcting 116 typo to 16)
             base = sheet.subsurface((147, 78, 16, 12))
             
             # Create Scales
             # User requested 50%, 75%, 100% of "Full" (3x) size.
             # Full (3x) = 48x36.
             
             # 50% = 24x18
             self.frames.append(pygame.transform.scale(base, (24, 18)))
             # 75% = 36x27
             self.frames.append(pygame.transform.scale(base, (36, 27)))
             # 100% = 48x36
             self.frames.append(pygame.transform.scale(base, (48, 36)))
             
             self.image = self.frames[2] # Start Full
        else:
             self.image = SpriteGenerator.create_sprite(OPTION_GRID, OPTION_PALETTE, scale=6) 
             self.frames = []
             
        self.rect = self.image.get_rect(center=(x, y))
        self.animation_timer = 0
        
        self.player = player
        self.delay = delay_frames
        # If no specific bullet groups passed, fallback to Entity groups
        self.bullet_groups = bullet_groups if bullet_groups else groups
        
    def update(self, *args):
        # Do NOT call super().update()! 
        # Entity.update forces rect to match self.pos (physics).
        # We are manually positioned by the Player trace, so we skip physics logic.
        
        # Pulse Animation
        if self.frames:
            # Sync all options to global time so they pulse together
            # Approx 60 FPS = ~16ms per frame.
            current_frame = pygame.time.get_ticks() // 16
            cycle = current_frame % 16
            
            frame_idx = 0
            if cycle < 4:
                frame_idx = 0 # Small
            elif cycle < 8:
                frame_idx = 1 # Mid
            elif cycle < 12:
                frame_idx = 2 # Full
            else:
                frame_idx = 1 # Mid
                
            self.image = self.frames[frame_idx]
            # Maintain center position when resizing
            self.rect = self.image.get_rect(center=self.rect.center)
            
        # Position is handled by the Player class updating options based on trace history

    def fire_primary(self, active_weapons):
        cx, cy = self.rect.centerx, self.rect.centery
        
        # Use self.bullet_groups for projectiles so they hit enemies!
        bg = self.bullet_groups
        
        if active_weapons["laser"]:
            Laser(bg, self.rect.right, cy)
        elif active_weapons["double"]:
            NormalShot(bg, self.rect.right, cy)
            Double(bg, cx, self.rect.top) 
        else:
            NormalShot(bg, self.rect.right, cy)
            
    def fire_missile(self, active_weapons):
        cx = self.rect.centerx
        bg = self.bullet_groups
        if active_weapons["missile"]:
            Missile(bg, cx, self.rect.bottom)
