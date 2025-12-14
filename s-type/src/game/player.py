import pygame
from src.engine.entity import Entity
from src.settings import INTERNAL_WIDTH, INTERNAL_HEIGHT
from src.game.powerup_manager import PowerUpManager
from src.game.weapons import NormalShot, Missile, Double, Laser
from src.game.option import Option
from src.game.shield import Shield
from src.game.sprite_factory import SpriteGenerator, VIC_VIPER_PALETTE, VIC_VIPER_GRID

class Player(Entity):
    def __init__(self, groups, x, y):
        super().__init__(groups, x, y)
        # Try loading master sheet
        sheet = SpriteGenerator.load_master_sheet() if hasattr(SpriteGenerator, 'load_master_sheet') else None
        
        # Actually, we defined it as a standalone function in the factory.
        from src.game.sprite_factory import load_master_sheet
        sheet = load_master_sheet()
        
        if sheet:
             # V3 Sheet Implementation
             # 5 Across: Down -> Up
             # Stride approx 35px (175 / 5)
             # Row 1 (Normal): Y=0
             self.sheet = sheet # Keep ref for animation updates
             self.base_rect = pygame.Rect(0, 0, 32, 16) # Standard hitbox size
             self.images = []
             for i in range(5):
                 # Grab 32x16 frames with 35px stride
                 # User says sprites are 36x16 approx. 
                 # Sheet is 175px wide -> 35px per slot.
                 # Reduced height to 16 to avoid clipping next row.
                 frame = sheet.subsurface((i * 35, 0, 35, 16)) 
                 scaled = pygame.transform.scale(frame, (105, 48)) # 3x Scale (35x16 -> 105x48)
                 self.images.append(scaled)
             
             self.image = self.images[2] # Start Straight (Index 2)
             self.rect = self.image.get_rect(topleft=(x, y)) # Re-calc rect due to new size
        else:
            # Fallback to generator if file moved/missing
            self.image = SpriteGenerator.create_sprite(VIC_VIPER_GRID, VIC_VIPER_PALETTE, scale=6) # 2*3 = 6
            self.images = []
            
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos = pygame.math.Vector2(x, y)
        
        # Movement stats
        self.base_speed = 6.0 # 2.0 * 3
        self.speed_level = 0
        self.max_speed_level = 5
        self.current_speed = self.base_speed
        
        # Systems
        self.powerup_manager = PowerUpManager(self)
        self.bullet_groups = groups # Use same groups for now, or separate
        self.shoot_cooldown = 0
        self.missile_cooldown = 0
        
        # Options
        self.options = [] # List of Option entities
        self.shields = [] # List of Shield entities
        self.position_trace = [] # History of (x, y) tuples
        self.max_trace_length = 100 
        
        # Invulnerability
        self.invulnerable = False
        self.invulnerable_timer = 0
        self.flash_timer = 0
        self.visible = True

    def activate_invulnerability(self, duration):
        self.invulnerable = True
        self.invulnerable_timer = duration
        self.flash_timer = 0
        print(f"Invulnerability Active for {duration}ms") 

    def update(self, delta_time, input_data):
        self.handle_movement(input_data)
        
        # Update Trace
        # Only record history if we moved! Gradius options follow "distance", effectively.
        if not self.position_trace or self.position_trace[0] != self.rect.center:
            self.position_trace.insert(0, self.rect.center)
            if len(self.position_trace) > self.max_trace_length:
                self.position_trace.pop()
            
        # Update Options Positions
        # Each option is N frames behind the previous one (or the player)
        for i, opt in enumerate(self.options):
            idx = (i + 1) * 15 # 15 frames delay per option
            if idx < len(self.position_trace):
                pos = self.position_trace[idx]
                opt.rect.center = pos
        
        self.handle_combat(input_data)
        super().update()
        self.clamp_to_screen()
        
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.missile_cooldown > 0:
            self.missile_cooldown -= 1
            
        # Invulnerability Logic
        if self.invulnerable:
            dt = delta_time * 16 # Approx ms
            self.invulnerable_timer -= dt
            
            # Flash effect
            self.flash_timer += dt
            if self.flash_timer > 100: # Flash every 100ms
                self.visible = not self.visible
                self.flash_timer = 0
                
                # Toggle alpha/visibility
                if self.visible:
                    self.image.set_alpha(255)
                else:
                    self.image.set_alpha(50) # Semi-transparent
            
            if self.invulnerable_timer <= 0:
                self.invulnerable = False
                self.visible = True
                # Reset ALL images to full opacity to prevent stuck alpha on unused frames
                for img in self.images:
                    img.set_alpha(255)
                self.image.set_alpha(255) # Ensure current is also done if not in list
                print("Invulnerability Ended")
        else:
            # Safe-guard: Ensure current image is opaque if logic missed it
             if self.image.get_alpha() != 255:
                 self.image.set_alpha(255)
                 self.visible = True

    def handle_movement(self, input_data):
        direction = pygame.math.Vector2(0, 0)
        
        if input_data['up']:
            direction.y = -1
        if input_data['down']:
            direction.y = 1
        if input_data['left']:
            direction.x = -1
        if input_data['right']:
            direction.x = 1

        if direction.length_squared() > 0:
            direction = direction.normalize()
        
        self.vel = direction * self.current_speed
        
        # Animation
        if hasattr(self, 'images') and len(self.images) == 5:
            idx = 2 # Straight
            if self.vel.y < -3: idx = 4 # Up Max
            elif self.vel.y < -0.1: idx = 3 # Up Slight
            elif self.vel.y > 3: idx = 0 # Down Max
            elif self.vel.y > 0.1: idx = 1 # Down Slight
            
            self.image = self.images[idx]

    def handle_combat(self, input_data):
        # Powerup Activation
        if input_data.get('powerup', False): # 'A' press
            self.powerup_manager.activate()
            
        # Debug: Simulate collecting a capsule with 'C'
        if input_data.get('debug_capsule', False):
            self.powerup_manager.collect_capsule()

        # Shooting (Primary)
        should_shoot = input_data['shoot'] or input_data.get('shoot_both', False)
        if should_shoot and self.shoot_cooldown == 0:
            self.fire_primary()
            # Fire Options too
            for opt in self.options:
                opt.fire_primary(self.powerup_manager.active_weapons)
            self.shoot_cooldown = 10 
            
        # Shooting (Missile)
        should_missile = input_data['missile'] or input_data.get('shoot_both', False)
        if should_missile and self.missile_cooldown == 0 and self.powerup_manager.active_weapons["missile"]:
            self.fire_missile()
            # Fire Option Missiles
            for opt in self.options:
                opt.fire_missile(self.powerup_manager.active_weapons)
            self.missile_cooldown = 30

    def fire_primary(self):
        # Logic for Laser vs Double vs Normal
        if self.powerup_manager.active_weapons["laser"]:
            Laser(self.bullet_groups, self.rect.right, self.rect.centery)
        elif self.powerup_manager.active_weapons["double"]:
            NormalShot(self.bullet_groups, self.rect.right, self.rect.centery)
            Double(self.bullet_groups, self.rect.centerx, self.rect.top) # Tailgun or Up-Double?
        else:
            NormalShot(self.bullet_groups, self.rect.right, self.rect.centery)

    def fire_missile(self):
        missile_groups = self.bullet_groups
        Missile(missile_groups, self.rect.centerx, self.rect.bottom)

    def speed_up(self):
        if self.speed_level < self.max_speed_level:
            self.speed_level += 1
            print(f"Speed Up! Level {self.speed_level}")
        else:
            self.speed_level = 1 # Revert back to 1 as requested (0 is too slow?)
            print(f"Speed Cycle! Back to Level {self.speed_level}")
            
        self.current_speed = self.base_speed + (self.speed_level * 1.0)

    def add_option(self):
        if len(self.options) < 4:
            # Spawn option using same groups as player context
            # Pass bullet_groups so Option shots can kill enemies
            opt = Option(self.groups(), self.rect.centerx, self.rect.centery, self, bullet_groups=self.bullet_groups)
            self.options.append(opt)
            print(f"Option added! Total: {len(self.options)}")
    
    def activate_shield(self):
        # Only activate if no shields present
        self.shields = [s for s in self.shields if s.alive()]
        
        if len(self.shields) == 0:
            print("Shield activated!")
            # Spawn 1 shield blob in front with HD Offsets
            # User requested distinct single sprite closer to nose.
            # Reduced offset_x from 54 to 15.
            s1 = Shield(self.groups(), self.rect.right + 15, self.rect.centery, self, offset_x=15)
            self.shields.append(s1)
        else:
            print("Shield already active!")

    def kill(self):
        # Cleanup dependent entities
        for opt in self.options:
            if opt.alive():
                opt.kill()
        for s in self.shields:
            if s.alive():
                s.kill()
        super().kill()

    def recharge_shield(self):
        # Restore HP of all active shields to 5
        active = [s for s in self.shields if s.alive()]
        if active:
            for s in active:
                s.hp = 5
            print("Shield Recharged to 100%!")

    def clamp_to_screen(self):
        # Keep player fully within the internal resolution
        if self.rect.left < 0:
            self.pos.x = 0
            self.rect.left = 0
        if self.rect.right > INTERNAL_WIDTH:
            self.pos.x = INTERNAL_WIDTH - self.rect.width
            self.rect.right = INTERNAL_WIDTH
        
        if self.rect.top < 0:
            self.pos.y = 0
            self.rect.top = 0
        if self.rect.bottom > INTERNAL_HEIGHT:
            self.pos.y = INTERNAL_HEIGHT - self.rect.height
            self.rect.bottom = INTERNAL_HEIGHT
            
        self.pos = pygame.math.Vector2(self.rect.topleft) # Sync floating point pos back if clamped

    def take_damage(self):
        # Check for active shields
        active_shields = [s for s in self.shields if s.alive()]
        
        if active_shields:
            # Hit the first available shield
            # (In Gradius, usually front shields take hits, but here we just take the first one)
            s = active_shields[0]
            s.take_damage(1)
            print("Shield Hit!")
            
            # Check if it died from that hit
            if not s.alive():
                self.powerup_manager.active_weapons["shield"] = False
                print("Shield Exhausted! Can redeploy.")
        else:
            print("Player Destroyed!")
            self.kill()
            # In a real game, this would trigger Game Over state or respawn logic.
