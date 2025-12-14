import pygame

class InputHandler:
    def __init__(self):
        self.actions = {
            'up': False,
            'down': False,
            'left': False,
            'right': False,
            'shoot': False, # Z or Button 1
            'missile': False, # X or Button 2
            'powerup': False # A or Button 3
        }

        self.keys_prev = pygame.key.get_pressed()

    def update(self):
        keys = pygame.key.get_pressed()
        
        self.actions['up'] = keys[pygame.K_UP]
        self.actions['down'] = keys[pygame.K_DOWN]
        self.actions['left'] = keys[pygame.K_LEFT]
        self.actions['right'] = keys[pygame.K_RIGHT]
        
        self.actions['shoot'] = keys[pygame.K_z]
        self.actions['missile'] = keys[pygame.K_x]
        self.actions['shoot_both'] = keys[pygame.K_s]
        
        # Just pressed logic for Powerup
        self.actions['powerup'] = keys[pygame.K_a] and not self.keys_prev[pygame.K_a]
        # Just pressed logic for Debug Capsule
        self.actions['debug_capsule'] = keys[pygame.K_c] and not self.keys_prev[pygame.K_c]
        
        self.keys_prev = keys
        
        return self.actions
