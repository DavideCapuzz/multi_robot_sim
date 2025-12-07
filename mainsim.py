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
RECOMPUTE_PATH_ON_STUCK = False

STEP_LOOKUP = np.array([
    [0, LENGTH],
    [0, -LENGTH],
    [LENGTH, 0],
    [-LENGTH, 0]
], dtype=int)


# ==========================================================
#                      PLAYER CLASS
# ==========================================================
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
        self.bot_color = (255, 0, 0) if manual else (0, 0, 0)

        self.list_percep = []
        self.list_comm = []

        self.last_move = np.array([0.0, 0.0])
        self.draw_player()

    # --------------------------------------------------
    # DRAWING
    # --------------------------------------------------
    def draw_player(self):
        self.image.fill((0, 0, 0, 0))
        center = (self.radius_ext, self.radius_ext)

        pygame.draw.circle(self.image, (0, 0, 255, 80), center, self.radius_ext, 2)
        pygame.draw.circle(self.image, (0, 255, 255, 80), center, self.radius_mid, 2)
        pygame.draw.circle(self.image, self.bot_color, center, RADIUS_BOT)

        font = pygame.font.Font(None, 24)
        text_surface = font.render(str(self.id_bot), True, WHITE)
        text_rect = text_surface.get_rect(center=center)
        self.image.blit(text_surface, text_rect)

    def draw_path(self):
        for i in range(len(self.path) - 1):
            pygame.draw.line(screen, GREEN, self.path[i], self.path[i+1], 4)

    # --------------------------------------------------
    # MOVEMENT LOGIC
    # --------------------------------------------------
    def move_point_towards(self, current_point, target_point):
        vec = target_point - current_point
        dist = np.linalg.norm(vec)

        if dist <= SPEED or dist == 0:
            self.last_move = target_point - current_point
            return target_point

        self.last_move = (vec / dist) * SPEED
        return current_point + self.last_move

    def auto_update(self, players, recompute_on_stuck=False):
        self.pose = self.move_point_towards(self.pose, self.path[0])
        self.update(self.pose[0], self.pose[1])
        self.draw_path()

        if np.linalg.norm(self.pose - self.path[0]) < 0.01:
            self.path.pop(0)
            self.update_path(self.path)

        # Resolve collisions; if stuck, optionally recompute path
        self.resolve_overlap(players, recompute_on_stuck)

    def update(self, x, y):
        x = min(max(x, 0), MAP_WIDTH)
        y = min(max(y, 0), MAP_HEIGHT)
        self.rect.center = (x, y)

    def manual_update(self, direction):
        self.last_move = np.array([0.0, 0.0])
        if direction == "UP":
            self.last_move[1] -= SPEED
        if direction == "DOWN":
            self.last_move[1] += SPEED
        if direction == "LEFT":
            self.last_move[0] -= SPEED
        if direction == "RIGHT":
            self.last_move[0] += SPEED

        self.pose += self.last_move
        self.pose[0] = min(max(self.pose[0], 0), MAP_WIDTH)
        self.pose[1] = min(max(self.pose[1], 0), MAP_HEIGHT)
        self.rect.center = self.pose

    # --------------------------------------------------
    # COLLISION PREVENTION
    # If robots collide, undo last move and stop
    # --------------------------------------------------
    def resolve_overlap(self, players, recompute_on_stuck=False):
        stuck = False
        for other in players:
            if other is self:
                continue
            dist = self.get_dist(other.pose)

            min_dist = RADIUS_BOT * 2

            if dist < min_dist:
                # Undo last move for this robot
                self.pose -= self.last_move
                self.update(self.pose[0], self.pose[1])
                self.last_move = np.array([0.0, 0.0])
                stuck = True

                # Undo move for other only if it's an auto bot
                if not other.manual:
                    other.pose -= other.last_move
                    other.update(other.pose[0], other.pose[1])
                    other.last_move = np.array([0.0, 0.0])

        # Recompute path if stuck AND the flag is True
        if stuck and not self.manual and recompute_on_stuck:
            self.path = self.init_path(self.pose[0], self.pose[1])

    # --------------------------------------------------
    # PATH GENERATION
    # --------------------------------------------------
    def get_start_point(self):
        return (
            random.randint(1, MAP_WIDTH // LENGTH) * LENGTH,
            random.randint(1, MAP_HEIGHT // LENGTH) * LENGTH
        )

    def append_set(self, out_path, add_set):
        new_point = out_path[-1] + add_set
        if 0 <= new_point[0] < MAP_WIDTH and 0 <= new_point[1] < MAP_HEIGHT:
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

    # --------------------------------------------------
    # ROBOT INTERACTIONS
    # --------------------------------------------------
    def get_dist(self, pose_opp):
        return np.linalg.norm(self.pose - pose_opp)

    def get_near_list(self, player_list):
        self.list_percep = []
        self.list_comm = []
        for p in player_list:
            if p is self:
                continue
            dist = self.get_dist(p.pose)
            if dist < RADIUS_PERCEP:
                self.list_percep.append(p.id_bot)
                self.list_comm.append(p.id_bot)
            elif dist < RADIUS_COMM:
                self.list_comm.append(p.id_bot)


# ==========================================================
# SIDE BAR
# ==========================================================
def draw_sidebar(screen, players, scroll_offset):
    x0 = SCREEN_WIDTH - SIDEBAR_WIDTH
    pygame.draw.rect(screen, (220, 220, 220), (x0, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))

    font = pygame.font.Font(None, 22)
    y = 10 + scroll_offset

    for p in players:
        screen.blit(font.render(f"Robot {p.id_bot}", True, BLACK), (x0 + 10, y))
        y += 20
        screen.blit(font.render(f"Percep: {p.list_percep}", True, (0, 100, 0)), (x0 + 20, y))
        y += 20
        screen.blit(font.render(f"Comm:   {p.list_comm}", True, (0, 0, 150)), (x0 + 20, y))
        y += 25


# ==========================================================
# GAME SETUP
# ==========================================================
players = []
auto_players = []
all_sprites = pygame.sprite.Group()

manual_player = Player(0, True)
players.append(manual_player)
all_sprites.add(manual_player)

for i in range(N_BOT):
    p = Player(i + 1, False)
    players.append(p)
    auto_players.append(p)
    all_sprites.add(p)

clock = pygame.time.Clock()
run = True

# ==========================================================
# MAIN LOOP
# ==========================================================
while run:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.MOUSEWHEEL:
            scroll_offset += event.y * 30
            scroll_offset = max(min(scroll_offset, 0), -MAX_SCROLL)

    # Manual movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        manual_player.manual_update("UP")
    if keys[pygame.K_DOWN]:
        manual_player.manual_update("DOWN")
    if keys[pygame.K_LEFT]:
        manual_player.manual_update("LEFT")
    if keys[pygame.K_RIGHT]:
        manual_player.manual_update("RIGHT")

    manual_player.resolve_overlap(players)

    # Auto bots
    for p in auto_players:
        p.auto_update(players, recompute_on_stuck=RECOMPUTE_PATH_ON_STUCK)

    # update perception lists
    for p in players:
        p.get_near_list(players)

    all_sprites.draw(screen)
    draw_sidebar(screen, players, scroll_offset)
    pygame.display.update()
    clock.tick(60)

pygame.quit()
