import pygame
import random
from src.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT
from src.game.enemy import Walker, Fan

class Level:
    def __init__(self, game):
        self.game = game
        self.timer = 0
        
        # Background
        self.bg_color = (20, 10, 5) # Dark sandy space
        self.scroll_x = 0
        self.scroll_speed = 0.5
        
        # Stars / Sand particles
        self.stars = []
        for _ in range(50):
            self.stars.append([random.randint(0, INTERNAL_WIDTH), random.randint(0, INTERNAL_HEIGHT), random.choice([0.5, 1, 2])])

    def update(self):
        self.timer += 1
        self.scroll_background()
        self.spawn_enemies()

    def scroll_background(self):
        self.scroll_x -= self.scroll_speed
        if self.scroll_x <= -INTERNAL_WIDTH:
            self.scroll_x = 0
            
        for star in self.stars:
            star[0] -= star[2] # Move by speed
            if star[0] < 0:
                star[0] = INTERNAL_WIDTH
                star[1] = random.randint(0, INTERNAL_HEIGHT)

    def draw_background(self, surface):
        surface.fill(self.bg_color)
        
        # Draw "Stars" / Sand grains
        for star in self.stars:
            pygame.draw.circle(surface, (200, 180, 150), (int(star[0]), int(star[1])), 1)

    def spawn_enemies(self):
        # Very simple spawn script for demo
        # Wave of Fans every 200 frames
        if self.timer % 200 == 0:
            for i in range(5):
                offset_x = i * 60 # 20 * 3
                Fan([self.game.all_sprites, self.game.enemy_group], INTERNAL_WIDTH + offset_x, INTERNAL_HEIGHT // 2, i * 0.5)
        
        # Walkers on the "floor" randomly
        if self.timer % 150 == 0:
             if random.random() > 0.5:
                 Walker([self.game.all_sprites, self.game.enemy_group], INTERNAL_WIDTH, INTERNAL_HEIGHT - 90) # Floor buffer scaled
