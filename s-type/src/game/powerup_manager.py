import pygame

class PowerUpManager:
    def __init__(self, player):
        self.player = player
        self.meter_index = -1 # -1 means nothing highlighted
        self.labels = ["SPEED UP", "MISSILE", "DOUBLE", "LASER", "OPTION", "?", "!"]
        self.max_index = len(self.labels) - 1
        
        # Loadout definitions (Edit Mode defaults)
        self.active_weapons = {
            "missile": False,
            "double": False,
            "laser": False,
            "option": 0, # Count
            "shield": False
        }

    def collect_capsule(self):
        self.meter_index = (self.meter_index + 1) % len(self.labels)
        print(f"PowerUp Bar: {self.labels[self.meter_index]}")

    def activate(self):
        if self.meter_index == -1:
            return

        selected = self.labels[self.meter_index]
        print(f"Activating: {selected}")
        
        # Activation Logic with Blocking
        success = False
        
        if selected == "SPEED UP":
            self.player.speed_up()
            success = True
        elif selected == "MISSILE":
            if not self.active_weapons["missile"]:
                self.active_weapons["missile"] = True
                success = True
        elif selected == "DOUBLE":
            self.active_weapons["double"] = True
            self.active_weapons["laser"] = False
            success = True
        elif selected == "LASER":
            self.active_weapons["laser"] = True
            self.active_weapons["double"] = False
            success = True
        elif selected == "OPTION":
            if self.active_weapons["option"] < 4:
                self.player.add_option()
                self.active_weapons["option"] += 1
                success = True
        elif selected == "?": # Shield
            if not self.active_weapons["shield"]:
                self.active_weapons["shield"] = True
                self.player.activate_shield()
                success = True
        elif selected == "(!)" or selected == "!": # Mega Crush / Recharge
            # User requested Shield Recharge
            if self.active_weapons["shield"]:
                self.player.recharge_shield()
                success = True
            else:
                 print("Cannot Recharge: No Shield Active")
            
        # Reset meter logic ONLY if successful use
        if success:
            self.meter_index = -1
            print(f"Activated: {selected}")
        else:
            print(f"Cannot activate {selected} (Already Active/Maxed)")
