import pygame

class Entity(pygame.sprite.Sprite):
    def __init__(self, groups, x, y, image=None):
        super().__init__(groups)
        self.image = image if image else pygame.Surface((16, 16)) # Placeholder
        if not image:
            self.image.fill((255, 0, 255)) # Magenta placeholder
        self.rect = self.image.get_rect(topleft=(x, y))
        
        # Consistent fractional movement
        self.pos = pygame.math.Vector2(x, y)
        self.vel = pygame.math.Vector2(0, 0)
        self.speed = 0

    def update(self, *args):
        self.pos += self.vel
        self.rect.topleft = self.pos
