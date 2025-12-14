import pygame
from src.engine.entity import Entity

class Capsule(Entity):
    def __init__(self, groups, x, y):
        super().__init__(groups, x, y)
        self.image.fill((255, 0, 0)) # Red
        self.image = pygame.transform.scale(self.image, (36, 24)) # 12x8 * 3
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pygame.math.Vector2(-3, 0) # Slowly move left (-1 * 3)
    
    def update(self, *args):
        super().update(*args)
        if self.rect.right < 0:
            self.kill()
