import pygame

# Screen Dimensions (Native HD: 768x672)
# No scaling needed anymore
INTERNAL_WIDTH = 768
INTERNAL_HEIGHT = 672
SCALE_FACTOR = 1
SCREEN_WIDTH = INTERNAL_WIDTH * SCALE_FACTOR
SCREEN_HEIGHT = INTERNAL_HEIGHT * SCALE_FACTOR
FPS = 60

# Authenticity
SLOWDOWN_ENABLED = True
SLOWDOWN_THRESHOLD = 20  # Number of entities before slowdown kicks in (arbitrary start value)

# Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
