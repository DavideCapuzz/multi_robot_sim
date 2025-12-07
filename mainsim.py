import pygame
import random
import numpy as np
import math

pygame.init()

SIDEBAR_WIDTH = 250
MAP_WIDTH = 800
MAP_HEIGHT = 600
SCREEN_WIDTH = MAP_WIDTH + SIDEBAR_WIDTH
SCREEN_HEIGHT = MAP_HEIGHT

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

SPEED = 2
LENGTH = 40
N_SEG = 10
N_BOT = 20

RADIUS_COMM = 150
RADIUS_PERCEP = 50
RADIUS_BOT = 12

scroll_offset = 0
MAX_SCROLL = (N_BOT + 1) * 37

STEP_LOOKUP = np.array([
    [0, LENGTH],      # down
    [0, -LENGTH],     # up
    [LENGTH, 0],      # right
    [-LENGTH, 0]      # left
], dtype=int)


class Player(pygame.sprite.Sprite):
    def __init__(self, id_bot, manual):
        super().__init__()
        self.id_bot = id_bot
        self.manual = manual

        self.pose = np.array(self.get_start_point(), dtype=float)
        self.radius_mid = RADIUS_PERCEP
        self.radius_ext = RADIUS_COMM
        self.image = pygame.Surface((self.radius_ext * 2, self.radius_ext * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=self.pose)
        self.path = self.init_path(self.pose[0], self.pose[1])
        self.bot_color = (0, 0, 0)
        self.list_percep = []
        self.list_comm = []
        if self.manual:
            self.bot_color = (255, 0, 0)
        self.draw_player()

    # ----------------------------------------------
    # DRAWING
    # ----------------------------------------------
    def draw_player(self):
        self.image.fill((0, 0, 0, 0))
        center = (self.radius_ext, self.radius_ext)
        pygame.draw.circle(self.image, (0, 0, 255, 100), center, self.radius_ext, 2) # Communication outer radius (line)
        pygame.draw.circle(self.image, (0, 255, 255, 100), center, self.radius_mid, 2) # Perception radius (line)
        pygame.draw.circle(self.image, self.bot_color, center, RADIUS_BOT) # Inner robot body
        # ---- Draw ID text ----
        font = pygame.font.Font(None, 24)
        text_surface = font.render(str(self.id_bot), True, WHITE)
        text_rect = text_surface.get_rect(center=center)
        self.image.blit(text_surface, text_rect)

    def draw_path(self):
        for i in range(len(self.path) - 1):
            pygame.draw.line(screen, (0, 255, 0), self.path[i], self.path[i + 1], width=4)

    # ----------------------------------------------
    # MOVEMENT
    # ----------------------------------------------
    def auto_update(self):
        self.pose = self.move_point_towards(self.pose, self.path[0])
        self.update(self.pose[0], self.pose[1])
        self.draw_path()

        if np.linalg.norm(self.pose - self.path[0]) < 0.01:
            self.path.pop(0)
            self.update_path(self.path)

    def move_point_towards(self, current_point, target_point):
        vec = target_point - current_point
        dist = np.linalg.norm(vec)

        if dist <= SPEED or dist == 0:
            return target_point

        return current_point + (vec / dist) * SPEED

    def update(self, x, y):
        self.rect.center = (min(max(x,0), MAP_WIDTH), min(max(y,0), MAP_HEIGHT))

    def manual_update(self, direction):
        if direction == "UP":
            self.pose = (self.pose[0], self.pose[1] - SPEED)  # Decrease y for UP
        if direction == "DOWN":
            self.pose = (self.pose[0], self.pose[1] + SPEED)  # Increase y for DOWN
        if direction == "LEFT":
            self.pose = (self.pose[0] - SPEED, self.pose[1])  # Decrease x for LEFT
        if direction == "RIGHT":
            self.pose = (self.pose[0] + SPEED, self.pose[1])  # Increase x for RIGHT

        # Ensure the player stays within the screen bounds
        self.pose = (min(max(self.pose[0], 0), MAP_WIDTH), min(max(self.pose[1], 0), MAP_HEIGHT))

        # Update rect and draw path
        self.rect.center = self.pose

    # ----------------------------------------------
    # PATH GENERATION
    # ----------------------------------------------
    def get_start_point(self):
        return (
            random.randint(1, MAP_WIDTH // LENGTH) * LENGTH,
            random.randint(1, MAP_HEIGHT // LENGTH) * LENGTH
        )

    def append_set(self, out_path, add_set):
        new_point = out_path[-1] + add_set

        if (0 <= new_point[0] < MAP_WIDTH) and (0 <= new_point[1] < MAP_HEIGHT):
            out_path.append(new_point)

        return out_path

    def update_path(self, out_path):
        while len(out_path) < N_SEG:
            step = STEP_LOOKUP[random.randint(0, 3)]
            self.append_set(out_path, step)
        return out_path

    def init_path(self, x, y):
        out_path = [np.array([x, y], dtype=float)]
        return self.update_path(out_path)
    # ----------------------------------------------
    # ROBOT INTERACTION
    # ----------------------------------------------
    def get_dist(self, pose_opp):
        return np.sqrt((self.pose[0]-pose_opp[0])**2 + (self.pose[1]-pose_opp[1])**2)

    def get_near_list(self, player_list):
        self.list_percep = []
        self.list_comm = []
        for p in player_list:
            if p is self:  # optional safety
                continue
            dist = self.get_dist(p.pose)
            if dist<RADIUS_PERCEP:
                self.list_percep.append(p.id_bot)
                self.list_comm.append(p.id_bot)
            elif dist<RADIUS_COMM:
                self.list_comm.append(p.id_bot)
# ----------------------------------------------
# SIDE BAR
# ----------------------------------------------
def draw_sidebar(screen, players, scroll_offset):
    x0 = SCREEN_WIDTH - SIDEBAR_WIDTH
    # background
    pygame.draw.rect(screen, (220, 220, 220), (x0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))

    font = pygame.font.Font(None, 22)

    # starting y position WITH SCROLL
    y = 10 + scroll_offset

    for p in players:
        # Robot title
        text = font.render(f"Robot {p.id_bot}", True, (0,0,0))
        screen.blit(text, (x0 + 10, y))
        y += 20

        # Perception list
        text = font.render(f"Percep: {p.list_percep}", True, (0, 100, 0))
        screen.blit(text, (x0 + 20, y))
        y += 20

        # Communication list
        text = font.render(f"Comm:   {p.list_comm}", True, (0, 0, 150))
        screen.blit(text, (x0 + 20, y))
        y += 25
# ----------------------

players = []
auto_players = []
all_sprites = pygame.sprite.Group()

manual_player = Player(0, True)
all_sprites.add(manual_player)
players.append(manual_player)

for i in range(N_BOT):
    p = Player(i+1, False)
    players.append(p)
    auto_players.append(p)
    all_sprites.add(p)

clock = pygame.time.Clock()
run = True

while run:
    screen.fill(WHITE)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.MOUSEWHEEL:
            scroll_offset += event.y * 30  # scroll speed
            scroll_offset = max(min(scroll_offset, 0), -MAX_SCROLL)

    # -------- MOVEMENT FIXED --------
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        manual_player.manual_update("UP")
    if keys[pygame.K_DOWN]:
        manual_player.manual_update("DOWN")
    if keys[pygame.K_LEFT]:
        manual_player.manual_update("LEFT")
    if keys[pygame.K_RIGHT]:
        manual_player.manual_update("RIGHT")

    for p in auto_players:
        p.auto_update()

    for p in players:
        p.get_near_list(players)

    all_sprites.draw(screen)
    draw_sidebar(screen, players, scroll_offset)
    pygame.display.update()
    clock.tick(60)

pygame.quit()
