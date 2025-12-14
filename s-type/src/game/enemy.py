import pygame
from src.engine.entity import Entity
from src.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT

class Enemy(Entity):
    def __init__(self, groups, x, y, hp=1):
        super().__init__(groups, x, y)
        self.hp = hp
        self.image.fill((200, 50, 50)) # Generic Red Enemy
        
    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()

class Walker(Enemy):
    def __init__(self, groups, x, y):
        super().__init__(groups, x, y, hp=1)
        self.image.fill((150, 150, 150)) # Grey Walker
        self.image = pygame.transform.scale(self.image, (48, 48)) # 16 * 3
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pygame.math.Vector2(-3, 0) # -1 * 3
        
    def update(self, *args):
        super().update(*args)
        if self.rect.right < 0:
            self.kill()

class Fan(Enemy): # The flying ones that come in waves
    def __init__(self, groups, x, y, wave_offset_y=0):
        super().__init__(groups, x, y, hp=1)
        self.image.fill((255, 100, 0)) # Orange
        self.image = pygame.transform.scale(self.image, (42, 42)) # 14 * 3
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pygame.math.Vector2(-6, 0) # -2 * 3
        self.wave_offset = wave_offset_y
        self.t = 0
    
    def update(self, *args):
        import math
        self.t += 0.1
        self.vel.y = math.sin(self.t + self.wave_offset) * 4.5 # 1.5 * 3
        super().update(*args)
        if self.rect.right < 0:
            self.kill()
