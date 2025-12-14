import sys
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, INTERNAL_WIDTH, INTERNAL_HEIGHT, SCALE_FACTOR
from src.engine.game import Game

def main():
    pygame.init()
    pygame.display.set_caption("Gradius III (SNES) Clone - s-type")
    
    # Create the display window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    # Create the internal surface for pixel-perfect rendering
    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))

    # Initialize the Game Engine
    game = Game(screen, internal_surface)
    
    # Start the Game Loop
    game.run()

if __name__ == "__main__":
    main()
