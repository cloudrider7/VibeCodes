import pygame
from src.engine.entity import Entity

class Shield(Entity):
    def __init__(self, groups, x, y, player, offset_x=36, hp=5):
        super().__init__(groups, x, y)
        self.player = player
        self.offset_x = offset_x
        self.offset_y = 0 
        self.hp = hp 
        
        from src.game.sprite_factory import load_master_sheet
        sheet = load_master_sheet()
        
        if sheet:
             self.phase_sprites = []
             def grab(x, w):
                 s = sheet.subsurface((x, 136, w, 16))
                 return pygame.transform.scale(s, (w*3, 16*3))
                 
             # Phase 1
             self.phase_sprites.append([grab(13, 16), grab(32, 16)])
             # Phase 2
             self.phase_sprites.append([grab(52, 14), grab(71, 14)])
             # Phase 3
             self.phase_sprites.append([grab(88, 12), grab(104, 12)])
             # Phase 4
             self.phase_sprites.append([grab(121, 10), grab(137, 10)])
             # Phase 5
             self.phase_sprites.append([grab(154, 8)])
             
             self.image = self.phase_sprites[0][0]
        else:
             self.image = pygame.Surface((18, 36), pygame.SRCALPHA)
             pygame.draw.circle(self.image, (0, 100, 255, 180), (9, 18), 9)
             self.image = pygame.transform.scale(self.image, (18, 36))
             self.phase_sprites = []
             
        self.rect = self.image.get_rect(center=(x, y))
        
    def update(self, *args):
        # Do NOT call super().update()!
        
        # 1. Follow Player with Offset
        self.rect.centerx = self.player.rect.right + self.offset_x
        self.rect.centery = self.player.rect.centery + self.offset_y
        
        # 2. visual updates
        if self.phase_sprites:
            # 5 Sprites, HP 5.
            # HP 5 -> Index 0
            # HP 1 -> Index 4
            phase_idx = 5 - self.hp
            if phase_idx < 0: phase_idx = 0
            if phase_idx >= len(self.phase_sprites): phase_idx = len(self.phase_sprites) - 1
            
            sprites = self.phase_sprites[phase_idx]
            
            # Animation Timer (Global Sync)
            tick = pygame.time.get_ticks() // 100 
            step = tick % 4
            
            if len(sprites) == 2:
                # Pair Logic: LR, UD, LR(Inv), UD(Inv)
                if step == 0:
                    self.image = sprites[0]
                elif step == 1:
                    self.image = sprites[1]
                elif step == 2:
                    self.image = pygame.transform.flip(sprites[0], True, False) # Flip X
                elif step == 3:
                    self.image = pygame.transform.flip(sprites[1], False, True) # Flip Y
            else:
                # Single Logic: Rot 0, 90, 180, 270
                angle = step * 90
                self.image = pygame.transform.rotate(sprites[0], angle)
            
            # Re-center
            self.rect = self.image.get_rect(center=self.rect.center)

    def take_damage(self, amount):
        self.hp -= amount
        print(f"Shield HP: {self.hp}")
        if self.hp <= 0:
            self.kill()
