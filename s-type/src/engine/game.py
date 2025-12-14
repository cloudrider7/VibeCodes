import pygame
import sys
import time
from src.settings import FPS, SLOWDOWN_ENABLED, SLOWDOWN_THRESHOLD, COLOR_BLACK, SCALE_FACTOR, INTERNAL_HEIGHT, INTERNAL_WIDTH
from src.engine.input_handler import InputHandler
from src.game.player import Player
from src.game.ui import PowerUpBar
from src.game.capsule import Capsule
from src.game.level import Level
import random

class Game:
    def __init__(self, screen, internal_surface):
        self.screen = screen
        self.internal_surface = internal_surface
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Input
        self.input_handler = InputHandler()

        # Entity Groups
        self.all_sprites = pygame.sprite.Group()
        self.enemy_group = pygame.sprite.Group()
        self.bullet_group = pygame.sprite.Group() # Player bullets
        self.capsule_group = pygame.sprite.Group()
        
        # Entities
        # Pass bullet_group so weapons act properly
        self.player = Player([self.all_sprites], 20, INTERNAL_HEIGHT // 2)
        self.player.bullet_groups = [self.all_sprites, self.bullet_group] 
        
        # Level Manager
        self.level = Level(self)
        
        # UI
        self.powerup_bar = PowerUpBar(self.internal_surface, self.player.powerup_manager)
        
        # Debug / Testing
        self.slowdown_active = SLOWDOWN_ENABLED
        self.respawn_timer = 0
        
    def respawn_player(self):
        print("Respawning Player...")
        # Create fresh player (resetting all powerups)
        self.player = Player([self.all_sprites], 20, INTERNAL_HEIGHT // 2)
        # Re-link groups
        self.player.bullet_groups = [self.all_sprites, self.bullet_group] 
        self.player.powerup_manager.player = self.player # Ensure logic links back if needed, though clean init usually sets it.
        # Note: PowerUpBar holds a reference to the OLD powerup_manager. We need to update it!
        self.powerup_bar.manager = self.player.powerup_manager
        self.respawn_timer = 0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    self.slowdown_active = not self.slowdown_active
                    print(f"Slowdown Enabled: {self.slowdown_active}")
                
    def update(self):
        # 0. Respawn Logic
        if not self.player.alive():
            if self.respawn_timer == 0:
                self.respawn_timer = pygame.time.get_ticks()
            
            # Wait 2 seconds
            if pygame.time.get_ticks() - self.respawn_timer > 2000: 
                self.respawn_player()
                # Activate 3s invulnerability
                self.player.activate_invulnerability(3000)
            
            # PAUSE GAME: Return early so enemies don't move/spawn while you are dead
            return 
        
        # 1. Get Input
        input_data = self.input_handler.update()
        
        # Debug Capsule Spawn
        if input_data.get('debug_capsule', False):
             c = Capsule([self.all_sprites, self.capsule_group], INTERNAL_WIDTH, random.randint(20, INTERNAL_HEIGHT - 20))

        # 2. Update Level (Spawning, Background)
        self.level.update()

        # 3. Update all sprites
        self.all_sprites.update(1, input_data)
        
        # 4. Collision Logic
        if self.player.alive() and not self.player.invulnerable:
            # Player vs Capsule logic (can collect while invulnerable? usually yes. Collision logic split.)
            pass # See below
            
        # Player vs Capsule (Always collect)
        if self.player.alive():
             hits = pygame.sprite.spritecollide(self.player, self.capsule_group, True)
             for hit in hits:
                 self.player.powerup_manager.collect_capsule()
        
        # Player vs Enemies (Only if not invulnerable)
        if self.player.alive() and not self.player.invulnerable:
            hits = pygame.sprite.spritecollide(self.player, self.enemy_group, True) # True: Kill enemy on impact
            if hits:
                self.player.take_damage()
            
        # Bullets vs Enemies
        # groupcollide(group1, group2, dokill1, dokill2)
        hits = pygame.sprite.groupcollide(self.enemy_group, self.bullet_group, False, True)
        for enemy, bullets in hits.items():
            enemy.take_damage(1) # Simple 1 dmg per shot
            if enemy.hp <= 0:
                # Spawn Capsule
                # Dialed back to 15% chance
                if random.random() < 0.15:
                    Capsule([self.all_sprites, self.capsule_group], enemy.rect.centerx, enemy.rect.centery)
            
        # Slowdown Logic
        if self.slowdown_active:
            entity_count = len(self.all_sprites)
            if entity_count > SLOWDOWN_THRESHOLD:
                # Artificial lag
                time.sleep(0.01) 

    def draw(self):
        # 1. Clear internal surface
        # self.internal_surface.fill(COLOR_BLACK) # Level draws background now
        
        # 2. Draw Background
        self.level.draw_background(self.internal_surface)
        
        # 3. Draw everything to internal surface
        self.all_sprites.draw(self.internal_surface)
        
        # 4. Draw UI
        self.powerup_bar.draw()
        
        # 5. Scale and Blit to main screen
        scaled_surface = pygame.transform.scale(self.internal_surface, self.screen.get_size())
        self.screen.blit(scaled_surface, (0, 0))
        
        # 6. Flip display
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()
