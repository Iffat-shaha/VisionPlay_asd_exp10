import json
import math
import os
import sys
import threading
import time
import ctypes
from collections import deque

import cv2
import mediapipe as mp
import pygame


pygame.init()

BASE_WIDTH, BASE_HEIGHT = 1000, 600
TARGET_DISPLAY_WIDTH, TARGET_DISPLAY_HEIGHT = 1920, 1080
DISPLAY_INFO = pygame.display.Info()
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
WIDTH, HEIGHT, FPS = WINDOW_WIDTH, WINDOW_HEIGHT, 60
GRAVITY, MOVE_SPEED = 0.62, 5.2
JUMP_VELOCITY, DOUBLE_JUMP_VELOCITY = -15.5, -14.2
ATTACK_COOLDOWN, ATTACK_DURATION, ATTACK_RANGE = 28, 10, 54
MAX_HP = 100
PLAYER_WIDTH, PLAYER_HEIGHT = 38, 62
HIDEOUT_DURATION, HIDEOUT_COOLDOWN, HIDEOUT_HEAL_PER_SECOND = 20.0, 120.0, 10.0
COYOTE_TIME_FRAMES, GROUND_Y = 8, HEIGHT - 60
SKY_BLUE, SKY_BLUE_DEEP = (135, 206, 235), (95, 183, 234)
ORANGE, BLUE, RED, WHITE, BLACK = (235, 140, 52), (60, 110, 255), (225, 70, 70), (245, 245, 245), (35, 35, 35)
YELLOW, GREEN, GRAY, BROWN, LEAF_GREEN, PINK = (245, 220, 70), (90, 220, 100), (100, 100, 100), (132, 82, 45), (54, 170, 74), (255, 170, 205)
ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "visionplay_accounts.json")

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("VisionPlay: Battle Arena")
clock = pygame.time.Clock()
FONT_SMALL = pygame.font.SysFont("consolas", 24, bold=True)
FONT_MEDIUM = pygame.font.SysFont("consolas", 36, bold=True)
FONT_LARGE = pygame.font.SysFont("consolas", 54, bold=True)

try:
    hwnd = pygame.display.get_wm_info().get("window")
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 3)
except Exception:
    pass


def update_window_size(width, height):
    global screen, WIDTH, HEIGHT, GROUND_Y
    WIDTH = max(960, int(width))
    HEIGHT = max(540, int(height))
    GROUND_Y = HEIGHT - 60
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)


def sx(value):
    return int(value * WIDTH / BASE_WIDTH)


def sy(value):
    return int(value * HEIGHT / BASE_HEIGHT)


def smin(value):
    return int(value * min(WIDTH / BASE_WIDTH, HEIGHT / BASE_HEIGHT))


def display_sx(value):
    return int(value * WIDTH / TARGET_DISPLAY_WIDTH)


def display_sy(value):
    return int(value * HEIGHT / TARGET_DISPLAY_HEIGHT)


class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surface):
        pygame.draw.rect(surface, ORANGE, self.rect)
        pygame.draw.rect(surface, (255, 185, 105), (self.rect.x, self.rect.y, self.rect.w, 5))
        for px in range(self.rect.x + 4, self.rect.right, 12):
            pygame.draw.rect(surface, (255, 175, 80), (px, self.rect.y + 6, 5, self.rect.h - 8))
        for px in range(self.rect.x, self.rect.right, 20):
            pygame.draw.rect(surface, (198, 110, 36), (px, self.rect.bottom - 6, 10, 6))
        pygame.draw.rect(surface, BLACK, self.rect, 2)


class FloatingItem:
    def __init__(self, x, y, kind):
        self.base_pos = pygame.Vector2(x, y)
        self.pos = pygame.Vector2(x, y)
        self.kind = kind
        self.radius = 12
        self.collected = False
        self.anim_time = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.pos.x - self.radius), int(self.pos.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt):
        self.anim_time += dt
        self.pos.y = self.base_pos.y + math.sin(self.anim_time * 3.0) * 6

    def apply(self, player):
        self.collected = True
        if self.kind == "health":
            player.hp = min(player.max_hp, player.hp + 20)
        elif self.kind == "health_small":
            player.hp = min(player.max_hp, player.hp + 5)
        else:
            player.power_timer = 360

    def draw(self, surface):
        if self.collected:
            return
        center = (int(self.pos.x), int(self.pos.y))
        body = None
        pygame.draw.circle(surface, (255, 245, 200) if self.kind == "health" else (195, 255, 195), center, self.radius + 5, 2)
        if self.kind == "health":
            body = pygame.Rect(center[0] - 11, center[1] - 9, 22, 18)
            pygame.draw.ellipse(surface, (255, 194, 40), body)
            pygame.draw.ellipse(surface, (250, 225, 90), (body.x + 2, body.y + 1, 10, 8))
            pygame.draw.line(surface, BROWN, (center[0], center[1] - 11), (center[0] + 2, center[1] - 18), 3)
            pygame.draw.ellipse(surface, LEAF_GREEN, (center[0] + 1, center[1] - 18, 10, 6))
        elif self.kind == "health_small":
            body = pygame.Rect(center[0] - 12, center[1] - 11, 24, 22)
            pygame.draw.ellipse(surface, (77, 215, 92), body)
            pygame.draw.ellipse(surface, (120, 245, 140), (body.x + 3, body.y + 2, 10, 8))
            pygame.draw.line(surface, BROWN, (center[0], center[1] - 12), (center[0] - 2, center[1] - 19), 3)
            pygame.draw.ellipse(surface, LEAF_GREEN, (center[0] - 10, center[1] - 20, 11, 7))
        else:
            body = pygame.Rect(center[0] - 12, center[1] - 11, 24, 22)
            pygame.draw.ellipse(surface, (77, 215, 92), body)
            pygame.draw.ellipse(surface, (120, 245, 140), (body.x + 3, body.y + 2, 10, 8))
            pygame.draw.line(surface, BROWN, (center[0], center[1] - 12), (center[0] - 2, center[1] - 19), 3)
            pygame.draw.ellipse(surface, LEAF_GREEN, (center[0] - 10, center[1] - 20, 11, 7))
        pygame.draw.ellipse(surface, WHITE, (body.x + 4, body.y + 3, 5, 5))
        pygame.draw.ellipse(surface, BLACK, body, 2)


class Bullet:
    def __init__(self, x, y, direction, color, damage):
        self.rect = pygame.Rect(x, y, 14, 6)
        self.direction = direction
        self.speed = 12
        self.color = color
        self.damage = damage
        self.active = True

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.right < 0 or self.rect.left > WIDTH:
            self.active = False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        pygame.draw.rect(surface, WHITE, (self.rect.x + 2, self.rect.y + 1, 4, 2))
        pygame.draw.rect(surface, BLACK, self.rect, 1)


class Hideout:
    def __init__(self, x, owner_name, color):
        self.owner_name = owner_name
        self.color = color
        self.rect = pygame.Rect(x, GROUND_Y - 70, 88, 70)
        self.occupant = None
        self.timer = 0.0
        self.cooldown_timer = 0.0

    def can_enter(self, player):
        return player.name == self.owner_name and self.occupant is None and self.cooldown_timer <= 0.0

    def try_enter(self, player):
        if self.can_enter(player) and player.rect.colliderect(self.rect):
            self.occupant = player
            self.timer = HIDEOUT_DURATION
            player.enter_hideout(self)
            return True
        return False

    def release(self):
        if not self.occupant:
            return
        self.occupant.exit_hideout()
        self.occupant = None
        self.timer = 0.0
        self.cooldown_timer = HIDEOUT_COOLDOWN

    def update(self, dt):
        if self.cooldown_timer > 0.0:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)
        if not self.occupant:
            return
        self.timer = max(0.0, self.timer - dt)
        self.occupant.hp = min(self.occupant.max_hp, self.occupant.hp + HIDEOUT_HEAL_PER_SECOND * dt)
        self.occupant.anchor_to_hideout(self.rect)
        if self.timer <= 0.0:
            self.release()

    def draw(self, surface):
        fill = self.color if self.occupant else ((130, 130, 130) if self.cooldown_timer <= 0 else (80, 80, 80))
        pygame.draw.rect(surface, fill, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 3)
        pygame.draw.rect(surface, BLACK, (self.rect.x + 26, self.rect.y + 24, 36, 46))
        label = FONT_SMALL.render(self.owner_name, True, WHITE)
        surface.blit(label, label.get_rect(center=(self.rect.centerx, self.rect.y - 18)))
        if self.occupant:
            text = f"{self.timer:04.1f}s"
        elif self.cooldown_timer > 0.0:
            text = f"CD {self.cooldown_timer:03.0f}s"
        else:
            text = None
        if text:
            img = FONT_SMALL.render(text, True, WHITE)
            surface.blit(img, img.get_rect(center=(self.rect.centerx, self.rect.bottom + 18)))


class Player:
    def __init__(self, x, y, color, name):
        self.name = name
        self.color = color
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.speed = MOVE_SPEED
        self.max_hp = MAX_HP
        self.hp = MAX_HP
        self.facing = 1
        self.on_ground = False
        self.jump_count = 0
        self.attack_cooldown = 0
        self.attack_timer = 0
        self.invuln_timer = 0
        self.power_timer = 0
        self.hidden = False
        self.hideout = None
        self.coyote_timer = 0
        self.run_cycle = 0.0
        self.weapon_type = "glove"
        self.weapon_range = ATTACK_RANGE

    def move(self, direction):
        if self.hidden:
            self.vel_x = 0
            return
        self.vel_x = direction * self.speed
        if direction:
            self.run_cycle += 0.25
        if direction > 0:
            self.facing = 1
        elif direction < 0:
            self.facing = -1

    def stop(self):
        self.vel_x = 0

    def jump(self):
        if self.hidden:
            return False
        if self.jump_count == 0 or self.coyote_timer > 0:
            self.vel_y = JUMP_VELOCITY
            self.on_ground = False
            self.jump_count = 1
            self.coyote_timer = 0
            return True
        return False

    def double_jump(self):
        if self.hidden or self.jump_count != 1:
            return False
        self.vel_y = DOUBLE_JUMP_VELOCITY
        self.on_ground = False
        self.jump_count = 2
        return True

    def attack(self):
        if self.hidden or self.attack_cooldown > 0:
            return False
        self.attack_cooldown = ATTACK_COOLDOWN
        self.attack_timer = ATTACK_DURATION
        return True

    def attack_rect(self):
        if self.attack_timer <= 0 or self.hidden:
            return None
        if self.weapon_type == "gun":
            return None
        if self.facing == 1:
            return pygame.Rect(self.rect.right, self.rect.y + 8, self.weapon_range, self.rect.h - 16)
        return pygame.Rect(self.rect.x - self.weapon_range, self.rect.y + 8, self.weapon_range, self.rect.h - 16)

    def projectile_spawn(self):
        if self.facing == 1:
            return self.rect.right + 8, self.rect.y + 14
        return self.rect.x - 22, self.rect.y + 14

    def take_damage(self, amount, knockback):
        if self.invuln_timer > 0 or self.hidden:
            return
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = 24
        self.vel_x = knockback
        self.vel_y = -5

    def enter_hideout(self, hideout):
        self.hidden = True
        self.hideout = hideout
        self.attack_timer = 0
        self.vel_x = 0
        self.vel_y = 0
        self.anchor_to_hideout(hideout.rect)

    def anchor_to_hideout(self, rect):
        self.rect.midbottom = (rect.centerx, rect.bottom)
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = True

    def exit_hideout(self):
        if not self.hideout:
            return
        self.hidden = False
        spawn_x = self.hideout.rect.right + 8 if self.hideout.owner_name == "P1" else self.hideout.rect.x - self.rect.w - 8
        self.rect.x = max(0, min(WIDTH - self.rect.w, spawn_x))
        self.rect.bottom = GROUND_Y
        self.vel_x = 0
        self.vel_y = 0
        self.hideout = None

    def update_physics(self, platforms):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        if self.power_timer > 0:
            self.power_timer -= 1
        if self.hidden:
            return
        self.rect.x += int(self.vel_x)
        self.rect.x = max(0, min(WIDTH - self.rect.w, self.rect.x))
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)
        was_on_ground = self.on_ground
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y >= 0 and self.rect.bottom - self.vel_y <= platform.rect.top + 8:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    self.jump_count = 0
                elif self.vel_y < 0 and self.rect.top - self.vel_y >= platform.rect.bottom - 8:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0
        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0
            self.on_ground = True
            self.jump_count = 0
        if self.on_ground or (was_on_ground and not self.on_ground):
            self.coyote_timer = COYOTE_TIME_FRAMES
        elif self.coyote_timer > 0:
            self.coyote_timer -= 1

    def collect_items(self, items):
        for item in items:
            if not item.collected and self.rect.colliderect(item.rect):
                item.apply(self)

    def draw(self, surface):
        if self.hidden:
            return
        color = WHITE if self.invuln_timer > 0 and self.invuln_timer % 4 < 2 else self.color
        self.draw_sprite(surface, color)
        if self.attack_timer > 0:
            pygame.draw.rect(surface, (255, 240, 170), self.attack_rect(), 2)
        if self.power_timer > 0:
            pygame.draw.circle(surface, YELLOW, self.rect.midtop, 8, 2)

    def draw_sprite(self, surface, color):
        skin, shadow, boot = (255, 224, 180), (25, 25, 35), (70, 42, 20)
        accent = (220, 240, 255) if self.color == BLUE else (255, 215, 215)
        x, y = self.rect.x, self.rect.y
        bob = 1 if abs(self.vel_x) > 0.1 and self.on_ground and int(self.run_cycle * 2) % 2 == 0 else 0
        leg_shift = 3 if abs(self.vel_x) > 0.1 and self.on_ground else 0
        pygame.draw.rect(surface, shadow, (x - 2, y + 50, 40, 6))
        pygame.draw.rect(surface, skin, (x + 8, y - 12 + bob, 20, 14))
        pygame.draw.rect(surface, BLACK, (x + 8, y - 12 + bob, 20, 14), 2)
        pygame.draw.rect(surface, BLACK, (x + 13, y - 8 + bob, 3, 3))
        pygame.draw.rect(surface, BLACK, (x + 20, y - 8 + bob, 3, 3))
        pygame.draw.line(surface, BLACK, (x + 15, y - 3 + bob), (x + 21, y - 3 + bob), 1)
        pygame.draw.rect(surface, color, (x + 4, y + 2, 28, 28))
        pygame.draw.rect(surface, BLACK, (x + 4, y + 2, 28, 28), 2)
        pygame.draw.rect(surface, accent, (x + 10, y + 8, 16, 7))
        pygame.draw.rect(surface, BLACK, (x + 10, y + 8, 16, 7), 1)
        arm_y = y + 10
        if self.attack_timer > 0:
            pygame.draw.rect(surface, skin, (x + 30, arm_y, 16, 7) if self.facing == 1 else (x - 10, arm_y, 16, 7))
            if self.weapon_type == "sword":
                sword = pygame.Rect(x + 38, y + 12, 34, 6) if self.facing == 1 else pygame.Rect(x - 36, y + 12, 34, 6)
                pygame.draw.rect(surface, (200, 200, 220), sword)
                pygame.draw.rect(surface, BLACK, sword, 1)
            elif self.weapon_type == "gun":
                gun = pygame.Rect(x + 34, y + 10, 18, 10) if self.facing == 1 else pygame.Rect(x - 16, y + 10, 18, 10)
                pygame.draw.rect(surface, GRAY, gun)
                pygame.draw.rect(surface, BLACK, gun, 1)
        else:
            pygame.draw.rect(surface, skin, (x - 4, arm_y, 8, 18))
            pygame.draw.rect(surface, skin, (x + 32, arm_y, 8, 18))
        pygame.draw.rect(surface, color, (x + 7, y + 30, 10, 18))
        pygame.draw.rect(surface, color, (x + 20, y + 30, 10, 18))
        pygame.draw.rect(surface, boot, (x + 6 - leg_shift, y + 46, 12, 7))
        pygame.draw.rect(surface, boot, (x + 18 + leg_shift, y + 46, 12, 7))
        pygame.draw.rect(surface, BLACK, (x + 6 - leg_shift, y + 46, 12, 7), 1)
        pygame.draw.rect(surface, BLACK, (x + 18 + leg_shift, y + 46, 12, 7), 1)


class EnemyAI(Player):
    def __init__(self, x, y, color, name):
        super().__init__(x, y, color, name)
        self.jump_lock = 0
        self.strategy = "approach"
        self.strategy_timer = 0
        self.speed = 4.0

    def set_difficulty(self, profile):
        self.speed = profile["enemy_speed"]

    def choose_strategy(self, target):
        distance = abs(target.rect.centerx - self.rect.centerx)
        if self.hp <= 28:
            self.strategy = "retreat"
        elif target.attack_timer > 0 and distance < 125:
            self.strategy = "bait"
        elif distance > 200:
            self.strategy = "approach"
        else:
            self.strategy = "pressure"

    def current_platform(self, platforms):
        probe = pygame.Rect(self.rect.x + 4, self.rect.bottom, self.rect.w - 8, 4)
        for platform in platforms:
            if probe.colliderect(platform.rect):
                return platform
        return None

    def update_ai(self, target, platforms):
        if self.hidden:
            return
        if self.jump_lock > 0:
            self.jump_lock -= 1
        if self.strategy_timer > 0:
            self.strategy_timer -= 1
        if target.hidden:
            self.stop()
            return
        if self.strategy_timer == 0:
            self.choose_strategy(target)
            self.strategy_timer = 30
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        gap = target.rect.bottom < self.rect.top - 20
        if self.strategy == "bait" and abs(dx) < 125:
            self.move(-1 if dx > 0 else 1)
        elif self.strategy != "retreat" and abs(dx) > 20:
            self.move(1 if dx > 0 else -1)
        else:
            self.stop()
        if self.strategy != "retreat" and abs(dx) < 80 and abs(target.rect.centery - self.rect.centery) < 44:
            self.attack()
        if gap and self.on_ground and self.jump_lock == 0:
            self.jump()
            self.jump_lock = 18
        elif self.on_ground and self.jump_lock == 0:
            standing = self.current_platform(platforms)
            if standing is not None:
                if dx > 0 and self.rect.right >= standing.rect.right - 10 and target.rect.centerx > self.rect.centerx:
                    self.jump()
                    self.jump_lock = 18
                elif dx < 0 and self.rect.left <= standing.rect.left + 10 and target.rect.centerx < self.rect.centerx:
                    self.jump()
                    self.jump_lock = 18
        if dy < -110 and self.jump_count == 1 and self.jump_lock == 0:
            self.double_jump()
            self.jump_lock = 18


class GestureController:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        self.status = "Starting webcam..."
        self.command = {"move": 0, "jump": False, "double_jump": False, "attack": False, "hideout_action": False, "cursor": (WIDTH // 2, HEIGHT // 2), "select": False}
        self.last_jump_time = 0.0
        self.last_double_jump_time = 0.0
        self.last_attack_time = 0.0
        self.last_select_time = 0.0
        self.last_hideout_time = 0.0
        self.select_hold_start = 0.0
        self.select_latched = False
        self.move_history = deque(maxlen=8)
        self.up_frames = 0
        self.pinch_frames = 0
        self.double_frames = 0
        self.cursor_history = deque(maxlen=7)
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _finger_up(self, lm, tip, pip):
        return lm[tip].y < lm[pip].y

    def _pinch(self, lm):
        hand_scale = max(0.001, math.hypot(lm[9].x - lm[0].x, lm[9].y - lm[0].y))
        pinch = math.hypot(lm[8].x - lm[4].x, lm[8].y - lm[4].y)
        return pinch / hand_scale < 0.38

    def _direction(self, lm):
        dx = lm[8].x - lm[6].x
        dy = lm[6].y - lm[8].y
        rise = lm[5].y - lm[8].y
        if abs(dx) > abs(rise) and abs(dx) > 0.045:
            return "right" if dx > 0 else "left"
        if rise > 0.12 and abs(dx) < 0.08 and dy > 0.04:
            return "up"
        return "none"

    def _tilt_direction(self, lm):
        wrist = lm[0]
        middle_mcp = lm[9]
        tilt = middle_mcp.x - wrist.x
        if tilt > 0.1:
            return "right"
        if tilt < -0.1:
            return "left"
        return "none"

    def _only_index(self, lm):
        return self._finger_up(lm, 8, 6) and not self._finger_up(lm, 12, 10) and not self._finger_up(lm, 16, 14) and not self._finger_up(lm, 20, 18)

    def _two_fingers(self, lm):
        return self._finger_up(lm, 8, 6) and self._finger_up(lm, 12, 10) and not self._finger_up(lm, 16, 14) and not self._finger_up(lm, 20, 18)

    def _fist(self, lm):
        return not self._finger_up(lm, 8, 6) and not self._finger_up(lm, 12, 10) and not self._finger_up(lm, 16, 14) and not self._finger_up(lm, 20, 18)

    def _run(self):
        if not self.cap.isOpened():
            with self.lock:
                self.status = "Webcam unavailable"
            return
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
        with mp_hands.Hands(max_num_hands=2, model_complexity=0, min_detection_confidence=0.6, min_tracking_confidence=0.6) as hands:
            with self.lock:
                self.status = "Gesture control ready"
            while self.running:
                ok, frame = self.cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)
                now = time.time()
                move = 0
                jump = False
                double_jump = False
                attack = False
                hideout_action = False
                select = False
                frame_moves = []
                pinch_detected = False
                index_detected = False
                two_detected = False
                fist_detected = False
                cursor = (WIDTH // 2, HEIGHT // 2)
                if results.multi_hand_landmarks:
                    for hand in results.multi_hand_landmarks:
                        lm = hand.landmark
                        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                        cursor = (int(lm[8].x * WIDTH), int(lm[8].y * HEIGHT))
                        tilt_direction = self._tilt_direction(lm)
                        if tilt_direction == "right":
                            frame_moves.append(1)
                        elif tilt_direction == "left":
                            frame_moves.append(-1)
                        if self._only_index(lm):
                            index_detected = True
                        if self._two_fingers(lm):
                            two_detected = True
                        if self._fist(lm):
                            fist_detected = True
                        if self._pinch(lm):
                            pinch_detected = True
                else:
                    self.double_frames = 0
                self.move_history.append(sum(frame_moves) / len(frame_moves) if frame_moves else 0)
                smoothed = sum(self.move_history) / len(self.move_history)
                if smoothed > 0.55:
                    move = 1
                elif smoothed < -0.55:
                    move = -1
                self.up_frames = self.up_frames + 1 if index_detected else 0
                self.pinch_frames = self.pinch_frames + 1 if pinch_detected else 0
                self.double_frames = self.double_frames + 1 if two_detected else 0
                if self.up_frames >= 3 and now - self.last_jump_time > 0.55:
                    jump = True
                    self.last_jump_time = now
                    self.up_frames = 0
                if self.pinch_frames >= 3 and now - self.last_attack_time > 0.45:
                    attack = True
                    self.last_attack_time = now
                    self.pinch_frames = 0
                if pinch_detected:
                    if self.select_hold_start == 0.0:
                        self.select_hold_start = now
                    elif not self.select_latched and now - self.select_hold_start >= 2.0:
                        select = True
                        self.last_select_time = now
                        self.select_latched = True
                else:
                    self.select_hold_start = 0.0
                    self.select_latched = False
                if self.double_frames >= 4 and now - self.last_double_jump_time > 0.8:
                    double_jump = True
                    self.last_double_jump_time = now
                    self.double_frames = 0
                if fist_detected and now - self.last_hideout_time > 0.75:
                    hideout_action = True
                    self.last_hideout_time = now
                self.cursor_history.append(cursor)
                avg_x = int(sum(pt[0] for pt in self.cursor_history) / len(self.cursor_history))
                avg_y = int(sum(pt[1] for pt in self.cursor_history) / len(self.cursor_history))
                cv2.circle(frame, (avg_x * frame.shape[1] // WIDTH, avg_y * frame.shape[0] // HEIGHT), 12, (0, 255, 255), 2)
                cv2.circle(frame, (avg_x * frame.shape[1] // WIDTH, avg_y * frame.shape[0] // HEIGHT), 3, (0, 255, 255), -1)
                cv2.rectangle(frame, (8, 8), (560, 52), (0, 0, 0), -1)
                cv2.putText(frame, f"Tilt:{move} Index:{jump} Two:{double_jump} Pinch:{attack} Fist:{hideout_action}", (16, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (255, 255, 255), 2)
                cv2.imshow("VisionPlay Gesture Controller", frame)
                cv2.waitKey(1)
                with self.lock:
                    self.command = {"move": move, "jump": jump, "double_jump": double_jump, "attack": attack, "hideout_action": hideout_action, "cursor": (avg_x, avg_y), "select": select}
        self.cap.release()
        cv2.destroyAllWindows()

    def get_command(self):
        with self.lock:
            return dict(self.command)

    def shutdown(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()


class AccountManager:
    def __init__(self, path):
        self.path = path
        self.accounts = self.load()

    def load(self):
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.accounts, handle, indent=2)

    def create_account(self, name, color):
        profile = {"username": name.strip() or "Player", "color": list(color), "current_level": 1, "password": ""}
        return profile

    def create_account_with_password(self, name, color, password):
        profile = {"username": name.strip() or "Player", "color": list(color), "current_level": 1, "password": password, "tutorial_done": False}
        if any(acct["username"].lower() == profile["username"].lower() for acct in self.accounts):
            return None
        self.accounts.append(profile)
        self.save()
        return profile

    def all_accounts(self):
        return list(self.accounts)

    def verify_login(self, username, password):
        for account in self.accounts:
            if account["username"].lower() == username.lower() and account.get("password", "") == password:
                return dict(account)
        return None

    def remove_account(self, username, password):
        for i, account in enumerate(self.accounts):
            if account["username"].lower() == username.lower() and account.get("password", "") == password:
                self.accounts.pop(i)
                self.save()
                return True
        return False

    def update_progress(self, username, current_level):
        for account in self.accounts:
            if account["username"].lower() == username.lower():
                account["current_level"] = current_level
                break
        self.save()

    def mark_tutorial_done(self, username):
        for account in self.accounts:
            if account["username"].lower() == username.lower():
                account["tutorial_done"] = True
                break
        self.save()


class MenuSystem:
    def __init__(self, accounts):
        self.accounts = accounts
        self.current_profile = None
        self.selected = 0
        self.mode_selected = None
        self.options = ["Create Account", "Login", "Delete Account", "Exit to Mode", "Exit"]
        self.mode_options = ["Keyboard Mode", "Gesture Mode", "Exit Game"]
        self.outfits = [("Blue Ranger", BLUE), ("Pink Hero", PINK), ("Leaf Knight", GREEN), ("Sun Rider", YELLOW)]
        self.gesture_controller = None
        self.menu_last_move = 0.0
        self.menu_last_select = 0.0
        self.virtual_rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]

    def default_profile(self):
        return self.current_profile or {"username": "Player", "color": list(BLUE), "current_level": 1}

    def ensure_gesture_controller(self):
        if self.mode_selected == "gesture" and self.gesture_controller is None:
            self.gesture_controller = GestureController()

    def shutdown_gesture_controller(self):
        if self.gesture_controller:
            self.gesture_controller.shutdown()
            self.gesture_controller = None

    def apply_menu_gesture(self, option_count):
        if self.mode_selected != "gesture" or not self.gesture_controller:
            return False
        command = self.gesture_controller.get_command()
        now = time.time()
        if command["move"] == -1 and now - self.menu_last_move > 0.35:
            self.selected = (self.selected - 1) % option_count
            self.menu_last_move = now
        elif command["move"] == 1 and now - self.menu_last_move > 0.35:
            self.selected = (self.selected + 1) % option_count
            self.menu_last_move = now
        if command["attack"] and now - self.menu_last_select > 0.45:
            self.menu_last_select = now
            return True
        if command.get("select") and now - self.menu_last_select > 0.35:
            self.menu_last_select = now
            return True
        return False

    def draw_gesture_pointer(self):
        if self.mode_selected != "gesture" or not self.gesture_controller:
            return
        command = self.gesture_controller.get_command()
        x, y = command.get("cursor", (WIDTH // 2, HEIGHT // 2))
        radius = max(8, smin(10))
        pygame.draw.circle(screen, YELLOW, (x, y), radius, 2)
        pygame.draw.circle(screen, YELLOW, (x, y), max(3, radius // 3))

    def login_option_rect(self, index):
        box_w = min(sx(520), WIDTH - sx(120))
        box_h = max(sy(42), 38)
        gap = max(sy(12), 8)
        start_y = sy(118)
        return pygame.Rect((WIDTH - box_w) // 2, start_y + index * (box_h + gap), box_w, box_h)

    def gesture_click_pos(self):
        if self.mode_selected == "gesture" and self.gesture_controller:
            command = self.gesture_controller.get_command()
            if command.get("select"):
                return command.get("cursor", (WIDTH // 2, HEIGHT // 2))
        return None

    def draw_virtual_keyboard(self, text, base_y=332):
        keys = []
        key_w = max(28, min(46, sx(34)))
        key_h = max(28, min(46, sy(34)))
        gap = max(4, min(10, smin(6)))
        total_w = key_w * 10 + gap * 9
        start_x = (WIDTH - total_w) // 2
        y = int(base_y)
        for row in self.virtual_rows:
            x = start_x
            for ch in row:
                rect = pygame.Rect(x, y, key_w, key_h)
                pygame.draw.rect(screen, ORANGE, rect)
                pygame.draw.rect(screen, BLACK, rect, 2)
                img = FONT_SMALL.render(ch, True, BLACK)
                screen.blit(img, img.get_rect(center=rect.center))
                keys.append((ch, rect))
                x += key_w + gap
            y += key_h + gap
        special_w = (total_w - gap * 2) // 3
        specials = [
            ("SPACE", pygame.Rect(start_x, y, special_w, key_h)),
            ("BACK", pygame.Rect(start_x + special_w + gap, y, special_w, key_h)),
            ("DONE", pygame.Rect(start_x + (special_w + gap) * 2, y, special_w, key_h)),
        ]
        for label, rect in specials:
            pygame.draw.rect(screen, YELLOW, rect)
            pygame.draw.rect(screen, BLACK, rect, 2)
            img = FONT_SMALL.render(label, True, BLACK)
            screen.blit(img, img.get_rect(center=rect.center))
            keys.append((label, rect))
        return keys

    def click_hits(self, rect, pos):
        padding = 14 if self.mode_selected == "gesture" else 0
        return rect.inflate(padding * 2, padding * 2).collidepoint(pos)

    def apply_virtual_key(self, key, text, max_len):
        if key == "BACK":
            return text[:-1]
        if key == "SPACE":
            return text + (" " if len(text) < max_len else "")
        if key == "DONE":
            return text
        if len(text) < max_len:
            return text + key
        return text

    def draw_preview(self, color):
        Player(WIDTH // 2 - 18, sy(315), color, "Preview").draw(screen)

    def menu_content_layout(self, item_count, item_w, item_h, item_gap, title_space, footer_space):
        margin_x = max(display_sx(120), 36)
        margin_y = max(display_sy(70), 30)
        safe_w = max(200, WIDTH - margin_x * 2)
        safe_h = max(200, HEIGHT - margin_y * 2)
        clamped_item_w = min(item_w, safe_w)
        buttons_h = item_count * item_h + max(0, item_count - 1) * item_gap
        content_h = title_space + buttons_h + footer_space
        clamped_content_h = min(content_h, safe_h)
        top = margin_y + max(0, (safe_h - clamped_content_h) // 2)
        left = margin_x + max(0, (safe_w - clamped_item_w) // 2)
        start_y = top + max(0, min(title_space, clamped_content_h - buttons_h - footer_space))
        bottom = top + clamped_content_h
        return left, start_y, top, bottom, clamped_item_w, clamped_content_h

    def home_option_rect(self, index):
        option_w = min(display_sx(760), WIDTH - display_sx(260))
        option_h = max(display_sy(82), 48)
        option_gap = max(display_sy(28), 16)
        left, start_y, _, _, option_w, _ = self.menu_content_layout(len(self.options), option_w, option_h, option_gap, sy(118), sy(70))
        return pygame.Rect(left, start_y + index * (option_h + option_gap), option_w, option_h)

    def draw_home(self):
        screen.fill(SKY_BLUE)
        option_w = min(display_sx(760), WIDTH - display_sx(260))
        option_h = max(display_sy(82), 48)
        option_gap = max(display_sy(28), 16)
        left_x, start_y, top, bottom, option_w, content_h = self.menu_content_layout(len(self.options), option_w, option_h, option_gap, display_sy(150), display_sy(90))
        panel_margin_x = max(display_sx(48), 24)
        panel_margin_y = max(display_sy(36), 22)
        panel_x = max(panel_margin_x, left_x - panel_margin_x)
        panel_y = max(panel_margin_y, top - panel_margin_y)
        panel_w = min(WIDTH - panel_x - panel_margin_x, option_w + panel_margin_x * 2)
        panel_h = min(HEIGHT - panel_y - panel_margin_y, content_h + panel_margin_y * 2)
        panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        header_h = min(display_sy(210), panel.h // 3)
        pygame.draw.rect(screen, SKY_BLUE_DEEP, panel)
        pygame.draw.rect(screen, (220, 245, 255), (panel.x, panel.y + header_h, panel.w, panel.h - header_h))
        pygame.draw.rect(screen, BLACK, panel, 3)
        title = FONT_LARGE.render("VisionPlay", True, BLACK)
        subtitle = FONT_MEDIUM.render("Pixel Battle Arena", True, BLACK)
        screen.blit(title, title.get_rect(center=(panel.centerx, panel.y + display_sy(68))))
        screen.blit(subtitle, subtitle.get_rect(center=(panel.centerx, panel.y + display_sy(128))))
        for i, option in enumerate(self.options):
            box = self.home_option_rect(i)
            pygame.draw.rect(screen, YELLOW if i == self.selected else ORANGE, box)
            pygame.draw.rect(screen, BLACK, box, 3)
            img = FONT_SMALL.render(option, True, BLACK)
            screen.blit(img, img.get_rect(center=box.center))
        mode_text = FONT_SMALL.render(f"Selected Mode: {self.mode_selected or 'Not Chosen'}", True, BLACK)
        screen.blit(mode_text, mode_text.get_rect(center=(panel.centerx, start_y - display_sy(34))))
        hint = FONT_SMALL.render("Choose mode first, then login/create account", True, BLACK)
        screen.blit(hint, hint.get_rect(center=(panel.centerx, panel.bottom - display_sy(28))))
        self.draw_gesture_pointer()

    def mode_select_screen(self):
        selected = 0
        while True:
            self.ensure_gesture_controller()
            gesture_select = self.apply_menu_gesture(len(self.mode_options))
            box_w = min(display_sx(760), WIDTH - display_sx(260))
            box_h = max(display_sy(86), 50)
            box_gap = max(display_sy(28), 16)
            left_x, start_y, top, bottom, box_w, content_h = self.menu_content_layout(len(self.mode_options), box_w, box_h, box_gap, display_sy(170), display_sy(94))
            panel_margin_x = max(display_sx(58), 26)
            panel_margin_y = max(display_sy(40), 22)
            panel_x = max(panel_margin_x, left_x - panel_margin_x)
            panel_y = max(panel_margin_y, top - panel_margin_y)
            panel_w = min(WIDTH - panel_x - panel_margin_x, box_w + panel_margin_x * 2)
            panel_h = min(HEIGHT - panel_y - panel_margin_y, content_h + panel_margin_y * 2)
            panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            game_title_y = panel.y + display_sy(54)
            title_y = panel.y + display_sy(126)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(self.mode_options)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(self.mode_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        option = self.mode_options[selected]
                        if option == "Exit Game":
                            self.shutdown_gesture_controller()
                            return "exit"
                        self.mode_selected = "keyboard" if option == "Keyboard Mode" else "gesture"
                        if self.mode_selected != "gesture":
                            self.shutdown_gesture_controller()
                        return self.mode_selected
                if event.type == pygame.MOUSEMOTION:
                    for i in range(len(self.mode_options)):
                        box = pygame.Rect(left_x, start_y + i * (box_h + box_gap), box_w, box_h)
                        if box.collidepoint(event.pos):
                            selected = i
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, option in enumerate(self.mode_options):
                        box = pygame.Rect(left_x, start_y + i * (box_h + box_gap), box_w, box_h)
                        if box.collidepoint(event.pos):
                            if option == "Exit Game":
                                self.shutdown_gesture_controller()
                                return "exit"
                            self.mode_selected = "keyboard" if option == "Keyboard Mode" else "gesture"
                            if self.mode_selected != "gesture":
                                self.shutdown_gesture_controller()
                            return self.mode_selected
            if gesture_select:
                option = self.mode_options[selected]
                if option == "Exit Game":
                    self.shutdown_gesture_controller()
                    return "exit"
                self.mode_selected = "keyboard" if option == "Keyboard Mode" else "gesture"
                return self.mode_selected

            screen.fill(SKY_BLUE)
            header_h = min(display_sy(220), panel.h // 3)
            pygame.draw.rect(screen, SKY_BLUE_DEEP, panel)
            pygame.draw.rect(screen, (220, 245, 255), (panel.x, panel.y + header_h, panel.w, panel.h - header_h))
            pygame.draw.rect(screen, BLACK, panel, 3)
            game_title = FONT_LARGE.render("VisionPlay", True, BLACK)
            title = FONT_MEDIUM.render("Choose Control Mode", True, BLACK)
            screen.blit(game_title, game_title.get_rect(center=(WIDTH // 2, game_title_y)))
            screen.blit(title, title.get_rect(center=(WIDTH // 2, title_y)))
            for i, option in enumerate(self.mode_options):
                box = pygame.Rect(left_x, start_y + i * (box_h + box_gap), box_w, box_h)
                pygame.draw.rect(screen, YELLOW if i == selected else ORANGE, box)
                pygame.draw.rect(screen, BLACK, box, 3)
                img = FONT_SMALL.render(option, True, BLACK)
                screen.blit(img, img.get_rect(center=box.center))
            hint = FONT_SMALL.render("Choose how menus are controlled", True, BLACK)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, panel.bottom - display_sy(28))))
            self.draw_gesture_pointer()
            pygame.display.flip()
            clock.tick(FPS)

    def create_account_screen(self):
        name = ""
        password = ""
        outfit = 0
        active_field = "name"
        while True:
            gesture_pos = self.gesture_click_pos()
            mouse_click = None
            panel_w = min(sx(620), WIDTH - sx(120))
            field_w = min(sx(440), panel_w - sx(60))
            field_h = max(sy(44), 40)
            field_x = (WIDTH - field_w) // 2
            title_y = sy(62)
            prompt_y = sy(102)
            name_y = sy(138)
            pass_y = name_y + field_h + sy(16)
            preview_y = pass_y + field_h + sy(34)
            outfit_btn_y = preview_y + sy(62)
            outfit_label_y = outfit_btn_y + sy(56)
            keyboard_y = min(max(outfit_label_y + sy(34), sy(350)), HEIGHT - sy(190))
            button_y = min(keyboard_y + sy(154), HEIGHT - sy(62))
            left_box = pygame.Rect(WIDTH // 2 - sx(170), outfit_btn_y, sx(54), max(sy(40), 36))
            right_box = pygame.Rect(WIDTH // 2 + sx(116), outfit_btn_y, sx(54), max(sy(40), 36))
            create_box = pygame.Rect(WIDTH // 2 - sx(170), button_y, sx(150), max(sy(38), 36))
            cancel_box = pygame.Rect(WIDTH // 2 + sx(20), button_y, sx(150), max(sy(38), 36))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_click = event.pos
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_TAB:
                        active_field = "password" if active_field == "name" else "name"
                    elif event.key == pygame.K_BACKSPACE:
                        if active_field == "name":
                            name = name[:-1]
                        else:
                            password = password[:-1]
                    elif event.key == pygame.K_LEFT:
                        outfit = (outfit - 1) % len(self.outfits)
                    elif event.key == pygame.K_RIGHT:
                        outfit = (outfit + 1) % len(self.outfits)
                    elif event.key == pygame.K_RETURN and name.strip() and password.strip():
                        created = self.accounts.create_account_with_password(name, self.outfits[outfit][1], password)
                        if created:
                            self.current_profile = created
                            return created
                        else:
                            self.message_screen("Username already exists. Choose another name.")
                        return None
                    elif event.unicode.isprintable():
                        if active_field == "name" and len(name) < 14:
                            name += event.unicode
                        elif active_field == "password" and len(password) < 18:
                            password += event.unicode
            screen.fill(SKY_BLUE)
            title = FONT_MEDIUM.render("Create Account", True, BLACK)
            prompt = FONT_SMALL.render("Type name + password. Left/Right changes clothes.", True, BLACK)
            name_box = pygame.Rect(field_x, name_y, field_w, field_h)
            pass_box = pygame.Rect(field_x, pass_y, field_w, field_h)
            pygame.draw.rect(screen, WHITE if active_field == "name" else (235, 235, 235), name_box)
            pygame.draw.rect(screen, WHITE if active_field == "password" else (235, 235, 235), pass_box)
            pygame.draw.rect(screen, BLACK, name_box, 3)
            pygame.draw.rect(screen, BLACK, pass_box, 3)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, title_y)))
            screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, prompt_y)))
            typed = FONT_MEDIUM.render(name or "Enter Name", True, BLACK)
            screen.blit(typed, typed.get_rect(center=name_box.center))
            pass_text = FONT_MEDIUM.render(("*" * len(password)) or "Enter Password", True, BLACK)
            screen.blit(pass_text, pass_text.get_rect(center=pass_box.center))
            preview = Player(WIDTH // 2 - 18, preview_y, self.outfits[outfit][1], "Preview")
            preview.draw(screen)
            pygame.draw.rect(screen, ORANGE, left_box)
            pygame.draw.rect(screen, ORANGE, right_box)
            pygame.draw.rect(screen, YELLOW if name.strip() and password.strip() else GRAY, create_box)
            pygame.draw.rect(screen, ORANGE, cancel_box)
            pygame.draw.rect(screen, BLACK, left_box, 2)
            pygame.draw.rect(screen, BLACK, right_box, 2)
            pygame.draw.rect(screen, BLACK, create_box, 2)
            pygame.draw.rect(screen, BLACK, cancel_box, 2)
            left_img = FONT_SMALL.render("<", True, BLACK)
            right_img = FONT_SMALL.render(">", True, BLACK)
            create_img = FONT_SMALL.render("Create", True, BLACK)
            cancel_img = FONT_SMALL.render("Cancel", True, BLACK)
            screen.blit(left_img, left_img.get_rect(center=left_box.center))
            screen.blit(right_img, right_img.get_rect(center=right_box.center))
            screen.blit(create_img, create_img.get_rect(center=create_box.center))
            screen.blit(cancel_img, cancel_img.get_rect(center=cancel_box.center))
            outfit_text = FONT_SMALL.render(f"Clothes: {self.outfits[outfit][0]}", True, BLACK)
            screen.blit(outfit_text, outfit_text.get_rect(center=(WIDTH // 2, outfit_label_y)))
            virtual_keys = []
            if self.mode_selected == "gesture":
                virtual_keys = self.draw_virtual_keyboard("", keyboard_y)
                hint = FONT_SMALL.render("Tap fields/buttons and hold pinch 2 sec to click", True, BLACK)
            else:
                hint = FONT_SMALL.render("Enter to create and start. Tab switches field.", True, BLACK)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - sy(16))))
            self.draw_gesture_pointer()
            pygame.display.flip()
            if self.mode_selected == "gesture":
                click_pos = gesture_pos
                if click_pos:
                    if self.click_hits(name_box, click_pos):
                        active_field = "name"
                    elif self.click_hits(pass_box, click_pos):
                        active_field = "password"
                    elif self.click_hits(left_box, click_pos):
                        outfit = (outfit - 1) % len(self.outfits)
                    elif self.click_hits(right_box, click_pos):
                        outfit = (outfit + 1) % len(self.outfits)
                    elif self.click_hits(create_box, click_pos):
                        if name.strip() and password.strip():
                            created = self.accounts.create_account_with_password(name, self.outfits[outfit][1], password)
                            if created:
                                self.current_profile = created
                                return created
                            self.message_screen("Username already exists. Choose another name.")
                            return None
                    elif self.click_hits(cancel_box, click_pos):
                        return None
                    else:
                        for key, rect in virtual_keys:
                            if self.click_hits(rect, click_pos):
                                if key == "DONE":
                                    if name.strip() and password.strip():
                                        created = self.accounts.create_account_with_password(name, self.outfits[outfit][1], password)
                                        if created:
                                            self.current_profile = created
                                            return created
                                        self.message_screen("Username already exists. Choose another name.")
                                        return None
                                elif active_field == "name":
                                    name = self.apply_virtual_key(key, name, 14)
                                else:
                                    password = self.apply_virtual_key(key, password, 18)
            clock.tick(FPS)

    def message_screen(self, text):
        frames = 0
        while frames < 120:
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.KEYDOWN):
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
            screen.fill(SKY_BLUE)
            img = FONT_SMALL.render(text, True, BLACK)
            screen.blit(img, img.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
            pygame.display.flip()
            clock.tick(FPS)
            frames += 1
        return None

    def login_password_screen(self, account):
        password = ""
        back_box = pygame.Rect(WIDTH // 2 - sx(170), sy(520), sx(150), max(sy(38), 36))
        login_box = pygame.Rect(WIDTH // 2 + sx(20), sy(520), sx(150), max(sy(38), 36))
        while True:
            gesture_pos = self.gesture_click_pos()
            pass_w = min(sx(460), WIDTH - sx(160))
            pass_h = max(sy(48), 40)
            pass_box = pygame.Rect((WIDTH - pass_w) // 2, sy(220), pass_w, pass_h)
            keyboard_y = min(pass_box.bottom + sy(28), HEIGHT - sy(180))
            back_box = pygame.Rect(WIDTH // 2 - sx(170), min(keyboard_y + sy(154), HEIGHT - sy(62)), sx(150), max(sy(38), 36))
            login_box = pygame.Rect(WIDTH // 2 + sx(20), min(keyboard_y + sy(154), HEIGHT - sy(62)), sx(150), max(sy(38), 36))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "back"
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    elif event.key == pygame.K_RETURN:
                        verified = self.accounts.verify_login(account["username"], password)
                        if verified:
                            return verified
                        self.message_screen("Incorrect password.")
                        password = ""
                    elif event.unicode.isprintable() and len(password) < 18:
                        password += event.unicode
            screen.fill(SKY_BLUE)
            title = FONT_MEDIUM.render("Enter Password", True, BLACK)
            user_text = FONT_SMALL.render(f"User: {account['username']}", True, BLACK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, sy(80))))
            screen.blit(user_text, user_text.get_rect(center=(WIDTH // 2, sy(132))))
            preview = Player(WIDTH // 2 - PLAYER_WIDTH // 2, sy(150), tuple(account["color"]), "Preview")
            preview.draw(screen)
            pygame.draw.rect(screen, WHITE, pass_box)
            pygame.draw.rect(screen, BLACK, pass_box, 3)
            pass_img = FONT_SMALL.render(("*" * len(password)) or "Type Password", True, BLACK)
            screen.blit(pass_img, pass_img.get_rect(center=pass_box.center))
            pygame.draw.rect(screen, ORANGE, back_box)
            pygame.draw.rect(screen, YELLOW, login_box)
            pygame.draw.rect(screen, BLACK, back_box, 2)
            pygame.draw.rect(screen, BLACK, login_box, 2)
            back_img = FONT_SMALL.render("Back", True, BLACK)
            login_img = FONT_SMALL.render("Login", True, BLACK)
            screen.blit(back_img, back_img.get_rect(center=back_box.center))
            screen.blit(login_img, login_img.get_rect(center=login_box.center))
            virtual_keys = []
            if self.mode_selected == "gesture":
                virtual_keys = self.draw_virtual_keyboard("", keyboard_y)
                hint = FONT_SMALL.render("Hold pinch 2 sec to click. Back returns to user list.", True, BLACK)
            else:
                hint = FONT_SMALL.render("Enter to login. Esc or Back returns to user list.", True, BLACK)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - sy(16))))
            self.draw_gesture_pointer()
            pygame.display.flip()
            if self.mode_selected == "gesture" and gesture_pos:
                if self.click_hits(back_box, gesture_pos):
                    return "back"
                if self.click_hits(login_box, gesture_pos):
                    verified = self.accounts.verify_login(account["username"], password)
                    if verified:
                        return verified
                    self.message_screen("Incorrect password.")
                    password = ""
                for key, rect in virtual_keys:
                    if self.click_hits(rect, gesture_pos):
                        if key == "DONE":
                            verified = self.accounts.verify_login(account["username"], password)
                            if verified:
                                return verified
                            self.message_screen("Incorrect password.")
                            password = ""
                        else:
                            password = self.apply_virtual_key(key, password, 18)
            clock.tick(FPS)

    def login_screen(self):
        accounts = self.accounts.all_accounts()
        selected = 0
        if not accounts:
            return self.message_screen("No accounts saved yet. Create one first.")
        while True:
            gesture_pos = self.gesture_click_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(accounts)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(accounts)
                    elif event.key == pygame.K_RETURN:
                        result = self.login_password_screen(accounts[selected])
                        if result == "back":
                            continue
                        if result:
                            return result
            screen.fill(SKY_BLUE)
            title = FONT_MEDIUM.render("Select User", True, BLACK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, sy(60))))
            for i, account in enumerate(accounts):
                box = self.login_option_rect(i)
                pygame.draw.rect(screen, tuple(account["color"]) if i == selected else WHITE, box)
                pygame.draw.rect(screen, BLACK, box, 3)
                img = FONT_SMALL.render(account["username"], True, BLACK)
                screen.blit(img, img.get_rect(center=box.center))
            hint = FONT_SMALL.render("Choose a user to open the password screen", True, BLACK)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - sy(16))))
            self.draw_gesture_pointer()
            pygame.display.flip()
            if self.mode_selected == "gesture":
                click_pos = gesture_pos
                if click_pos:
                    for i, account in enumerate(accounts):
                        if self.login_option_rect(i).collidepoint(click_pos):
                            selected = i
                            result = self.login_password_screen(account)
                            if result == "back":
                                break
                            if result:
                                return result
            clock.tick(FPS)

    def delete_account_screen(self):
        accounts = self.accounts.all_accounts()
        selected = 0
        password = ""
        if not accounts:
            return self.message_screen("No accounts available to delete.")
        while True:
            gesture_pos = self.gesture_click_pos()
            pass_w = min(sx(460), WIDTH - sx(160))
            pass_h = max(sy(44), 40)
            list_bottom = self.login_option_rect(len(accounts) - 1).bottom if accounts else sy(150)
            pass_box = pygame.Rect((WIDTH - pass_w) // 2, min(list_bottom + sy(26), HEIGHT - sy(240)), pass_w, pass_h)
            keyboard_y = min(pass_box.bottom + sy(18), HEIGHT - sy(180))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(accounts)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(accounts)
                    elif event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    elif event.key == pygame.K_RETURN:
                        username = accounts[selected]["username"]
                        if self.accounts.remove_account(username, password):
                            if self.current_profile and self.current_profile["username"].lower() == username.lower():
                                self.current_profile = None
                            self.message_screen("Account deleted.")
                            return None
                        self.message_screen("Wrong password. Account not deleted.")
                        password = ""
                    elif event.unicode.isprintable() and len(password) < 18:
                        password += event.unicode
            screen.fill(SKY_BLUE)
            title = FONT_MEDIUM.render("Delete Account", True, BLACK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, sy(60))))
            for i, account in enumerate(accounts):
                box = self.login_option_rect(i)
                pygame.draw.rect(screen, tuple(account["color"]) if i == selected else WHITE, box)
                pygame.draw.rect(screen, BLACK, box, 3)
                img = FONT_SMALL.render(account["username"], True, BLACK)
                screen.blit(img, img.get_rect(center=box.center))
            pygame.draw.rect(screen, WHITE, pass_box)
            pygame.draw.rect(screen, BLACK, pass_box, 3)
            pass_img = FONT_SMALL.render(("*" * len(password)) or "Type Password", True, BLACK)
            screen.blit(pass_img, pass_img.get_rect(center=pass_box.center))
            virtual_keys = []
            if self.mode_selected == "gesture":
                virtual_keys = self.draw_virtual_keyboard("", keyboard_y)
                hint = FONT_SMALL.render("Click/tap user and virtual keyboard", True, BLACK)
            else:
                hint = FONT_SMALL.render("Select user, type password, Enter to delete", True, BLACK)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - sy(16))))
            self.draw_gesture_pointer()
            pygame.display.flip()
            if self.mode_selected == "gesture":
                click_pos = gesture_pos
                if click_pos:
                    for i, account in enumerate(accounts):
                        if self.login_option_rect(i).collidepoint(click_pos):
                            selected = i
                    for key, rect in virtual_keys:
                        if rect.collidepoint(click_pos):
                            if key == "DONE":
                                username = accounts[selected]["username"]
                                if self.accounts.remove_account(username, password):
                                    if self.current_profile and self.current_profile["username"].lower() == username.lower():
                                        self.current_profile = None
                                    self.message_screen("Account deleted.")
                                    return None
                                self.message_screen("Wrong password. Account not deleted.")
                                password = ""
                            else:
                                password = self.apply_virtual_key(key, password, 18)
            clock.tick(FPS)

    def player_hub_screen(self, profile):
        options = ["Continue Level", "Choose Level", "Logout", "Back to Home"]
        selected = 0
        while True:
            gesture_select = self.apply_menu_gesture(len(options))
            option_w = min(sx(500), WIDTH - sx(160))
            option_h = max(sy(42), 38)
            option_gap = max(sy(16), 12)
            start_y = max(sy(290), HEIGHT // 2)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return {"action": "exit"}
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(options)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(options)
                    elif event.key == pygame.K_ESCAPE:
                        return {"action": "home"}
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        option = options[selected]
                        if option == "Continue Level":
                            if self.mode_selected:
                                return {"action": "start", "control_mode": self.mode_selected, "profile": profile, "level_index": max(0, profile.get("current_level", 1) - 1)}
                        if option == "Choose Level":
                            chosen = self.choose_level_screen(profile)
                            if chosen is not None:
                                return {"action": "start", "control_mode": self.mode_selected, "profile": profile, "level_index": chosen}
                        if option == "Logout":
                            self.current_profile = None
                            return {"action": "home"}
                        return {"action": "home"}
                if event.type == pygame.MOUSEMOTION:
                    for i in range(len(options)):
                        box = pygame.Rect((WIDTH - option_w) // 2, start_y + i * (option_h + option_gap), option_w, option_h)
                        if box.collidepoint(event.pos):
                            selected = i
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, option in enumerate(options):
                        box = pygame.Rect((WIDTH - option_w) // 2, start_y + i * (option_h + option_gap), option_w, option_h)
                        if box.collidepoint(event.pos):
                            selected = i
                            if option == "Continue Level":
                                return {"action": "start", "control_mode": self.mode_selected, "profile": profile, "level_index": max(0, profile.get("current_level", 1) - 1)}
                            if option == "Choose Level":
                                chosen = self.choose_level_screen(profile)
                                if chosen is not None:
                                    return {"action": "start", "control_mode": self.mode_selected, "profile": profile, "level_index": chosen}
                            if option == "Logout":
                                self.current_profile = None
                            return {"action": "home"}
            if gesture_select:
                option = options[selected]
                if option == "Continue Level":
                    return {"action": "start", "control_mode": self.mode_selected, "profile": profile, "level_index": max(0, profile.get("current_level", 1) - 1)}
                if option == "Choose Level":
                    chosen = self.choose_level_screen(profile)
                    if chosen is not None:
                        return {"action": "start", "control_mode": self.mode_selected, "profile": profile, "level_index": chosen}
                if option == "Logout":
                    self.current_profile = None
                return {"action": "home"}

            screen.fill(SKY_BLUE)
            pygame.draw.rect(screen, SKY_BLUE_DEEP, (0, 0, WIDTH, sy(170)))
            title = FONT_MEDIUM.render(f"Welcome, {profile['username']}", True, BLACK)
            level_no = profile.get("current_level", 1)
            level_name = GameManager.DIFFICULTIES[level_no - 1]["name"]
            level_text = FONT_SMALL.render(f"Current Stage: Level {level_no} - {level_name}", True, BLACK)
            cloth_text = FONT_SMALL.render(f"Mode: {self.mode_selected or 'Choose from Home'}", True, BLACK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, sy(62))))
            screen.blit(level_text, level_text.get_rect(center=(WIDTH // 2, sy(100))))
            screen.blit(cloth_text, cloth_text.get_rect(center=(WIDTH // 2, sy(136))))
            preview = Player(WIDTH // 2 - 18, sy(200), tuple(profile["color"]), "Preview")
            preview.draw(screen)

            for i, option in enumerate(options):
                box = pygame.Rect((WIDTH - option_w) // 2, start_y + i * (option_h + option_gap), option_w, option_h)
                pygame.draw.rect(screen, YELLOW if i == selected else ORANGE, box)
                pygame.draw.rect(screen, BLACK, box, 3)
                img = FONT_SMALL.render(option, True, BLACK)
                screen.blit(img, img.get_rect(center=box.center))

            pygame.display.flip()
            clock.tick(FPS)

    def choose_level_screen(self, profile):
        options = ["Level 1 - Easy", "Level 2 - Medium", "Back"]
        selected = 0
        while True:
            option_w = min(sx(460), WIDTH - sx(180))
            option_h = max(sy(48), 40)
            option_gap = max(sy(18), 12)
            start_y = max(sy(230), HEIGHT // 2 - sy(40))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(options)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if selected == 2:
                            return None
                        if selected == 1 and profile.get("current_level", 1) < 2:
                            continue
                        return selected
                if event.type == pygame.MOUSEMOTION:
                    for i in range(len(options)):
                        box = pygame.Rect((WIDTH - option_w) // 2, start_y + i * (option_h + option_gap), option_w, option_h)
                        if box.collidepoint(event.pos):
                            selected = i
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i in range(len(options)):
                        box = pygame.Rect((WIDTH - option_w) // 2, start_y + i * (option_h + option_gap), option_w, option_h)
                        if box.collidepoint(event.pos):
                            if i == 2:
                                return None
                            if i == 1 and profile.get("current_level", 1) < 2:
                                continue
                            return i
            screen.fill(SKY_BLUE)
            title = FONT_MEDIUM.render("Choose Level", True, BLACK)
            stage = FONT_SMALL.render(f"Current unlocked level: {profile.get('current_level', 1)}", True, BLACK)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, sy(120))))
            screen.blit(stage, stage.get_rect(center=(WIDTH // 2, sy(165))))
            for i, option in enumerate(options):
                box = pygame.Rect((WIDTH - option_w) // 2, start_y + i * (option_h + option_gap), option_w, option_h)
                locked = i == 1 and profile.get("current_level", 1) < 2
                fill = GRAY if locked else (YELLOW if i == selected else ORANGE)
                pygame.draw.rect(screen, fill, box)
                pygame.draw.rect(screen, BLACK, box, 3)
                text = option if not locked else "Level 2 - Locked"
                img = FONT_SMALL.render(text, True, BLACK)
                screen.blit(img, img.get_rect(center=box.center))
            pygame.display.flip()
            clock.tick(FPS)

    def run(self):
        self.ensure_gesture_controller()
        while True:
            gesture_select = self.apply_menu_gesture(len(self.options))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.shutdown_gesture_controller()
                    return {"action": "exit"}
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        self.selected = (self.selected + 1) % len(self.options)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.selected = (self.selected - 1) % len(self.options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        option = self.options[self.selected]
                        if option == "Create Account":
                            if not self.mode_selected:
                                self.mode_select_screen()
                            if not self.mode_selected:
                                continue
                            created = self.create_account_screen()
                            if created:
                                self.current_profile = created
                                self.shutdown_gesture_controller()
                                return {"action": "start", "control_mode": self.mode_selected, "profile": created}
                        elif option == "Login":
                            if not self.mode_selected:
                                self.mode_select_screen()
                            if not self.mode_selected:
                                continue
                            profile = self.login_screen()
                            if profile:
                                self.current_profile = profile
                                return self.player_hub_screen(profile)
                        elif option == "Delete Account":
                            self.delete_account_screen()
                        elif option == "Exit to Mode":
                            self.mode_selected = None
                            self.shutdown_gesture_controller()
                            chosen = self.mode_select_screen()
                            if chosen == "exit":
                                return {"action": "exit"}
                            if not chosen:
                                continue
                        elif option == "Exit":
                            self.shutdown_gesture_controller()
                            return {"action": "exit"}
                if event.type == pygame.MOUSEMOTION:
                    for i in range(len(self.options)):
                        box = self.home_option_rect(i)
                        if box.collidepoint(event.pos):
                            self.selected = i
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, option in enumerate(self.options):
                        box = self.home_option_rect(i)
                        if box.collidepoint(event.pos):
                            self.selected = i
                            if option == "Create Account":
                                if not self.mode_selected:
                                    self.mode_select_screen()
                                if not self.mode_selected:
                                    continue
                                created = self.create_account_screen()
                                if created:
                                    self.current_profile = created
                                    self.shutdown_gesture_controller()
                                    return {"action": "start", "control_mode": self.mode_selected, "profile": created}
                            elif option == "Login":
                                if not self.mode_selected:
                                    self.mode_select_screen()
                                if not self.mode_selected:
                                    continue
                                profile = self.login_screen()
                                if profile:
                                    self.current_profile = profile
                                    return self.player_hub_screen(profile)
                            elif option == "Delete Account":
                                self.delete_account_screen()
                            elif option == "Exit to Mode":
                                self.mode_selected = None
                                self.shutdown_gesture_controller()
                                chosen = self.mode_select_screen()
                                if chosen == "exit":
                                    return {"action": "exit"}
                                if not chosen:
                                    continue
                            else:
                                self.shutdown_gesture_controller()
                                return {"action": "exit"}
            if gesture_select:
                option = self.options[self.selected]
                if option == "Create Account":
                    if not self.mode_selected:
                        self.mode_select_screen()
                    if not self.mode_selected:
                        continue
                    created = self.create_account_screen()
                    if created:
                        self.current_profile = created
                        self.shutdown_gesture_controller()
                        return {"action": "start", "control_mode": self.mode_selected, "profile": created}
                elif option == "Login":
                    if not self.mode_selected:
                        self.mode_select_screen()
                    if not self.mode_selected:
                        continue
                    profile = self.login_screen()
                    if profile:
                        self.current_profile = profile
                        return self.player_hub_screen(profile)
                elif option == "Delete Account":
                    self.delete_account_screen()
                elif option == "Exit to Mode":
                    self.mode_selected = None
                    self.shutdown_gesture_controller()
                    chosen = self.mode_select_screen()
                    if chosen == "exit":
                        return {"action": "exit"}
                    if not chosen:
                        continue
                else:
                    self.shutdown_gesture_controller()
                    return {"action": "exit"}
            self.draw_home()
            pygame.display.flip()
            clock.tick(FPS)


class GameManager:
    DIFFICULTIES = [
        {"level": 1, "name": "Easy", "enemy_hp": 85, "enemy_speed": 3.6, "enemy_damage": 6, "player_damage": 14},
        {"level": 2, "name": "Medium", "enemy_hp": 100, "enemy_speed": 4.1, "enemy_damage": 8, "player_damage": 15},
    ]

    def __init__(self, mode, profile, diff_index):
        self.control_mode = mode
        self.profile = profile
        self.player_name = profile["username"]
        self.difficulty = self.DIFFICULTIES[diff_index]
        platform_h = max(18, sy(22))
        layouts = {
            1: [
                Platform(0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y),
                Platform(int(WIDTH * 0.11), int(HEIGHT * 0.76), int(WIDTH * 0.18), platform_h),
                Platform(int(WIDTH * 0.39), int(HEIGHT * 0.62), int(WIDTH * 0.17), platform_h),
                Platform(int(WIDTH * 0.67), int(HEIGHT * 0.50), int(WIDTH * 0.16), platform_h),
            ],
            2: [
                Platform(0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y),
                Platform(int(WIDTH * 0.15), int(HEIGHT * 0.73), int(WIDTH * 0.16), platform_h),
                Platform(int(WIDTH * 0.44), int(HEIGHT * 0.58), int(WIDTH * 0.18), platform_h),
                Platform(int(WIDTH * 0.71), int(HEIGHT * 0.44), int(WIDTH * 0.15), platform_h),
            ],
        }
        self.platforms = layouts[self.difficulty["level"]]
        self.player = Player(110, GROUND_Y - PLAYER_HEIGHT, tuple(profile["color"]), "P1")
        self.enemy = EnemyAI(WIDTH - 150, GROUND_Y - PLAYER_HEIGHT, RED, "Enemy")
        self.enemy.max_hp = self.difficulty["enemy_hp"]
        self.enemy.hp = self.difficulty["enemy_hp"]
        self.enemy.set_difficulty(self.difficulty)
        if self.difficulty["level"] == 1:
            self.items = [FloatingItem(int(WIDTH * 0.20), int(HEIGHT * 0.64), "health"), FloatingItem(int(WIDTH * 0.47), int(HEIGHT * 0.49), "health_small"), FloatingItem(int(WIDTH * 0.76), int(HEIGHT * 0.34), "health")]
        else:
            self.items = [FloatingItem(int(WIDTH * 0.22), int(HEIGHT * 0.61), "health"), FloatingItem(int(WIDTH * 0.54), int(HEIGHT * 0.41), "health_small"), FloatingItem(int(WIDTH * 0.79), int(HEIGHT * 0.24), "health_small"), FloatingItem(int(WIDTH * 0.63), int(HEIGHT * 0.27), "health_small")]
        self.hideouts = [Hideout(20, "P1", tuple(profile["color"])), Hideout(WIDTH - 108, "Enemy", RED)]
        self.gesture_controller = GestureController() if mode == "gesture" else None
        self.running = True
        self.bullets = []
        self.last_w_press = 0.0
        self.keyboard_jump_buffer = False
        self.keyboard_double_jump_buffer = False
        self.keyboard_attack_buffer = False
        self.keyboard_hideout_exit = False
        self.attack_hits = set()
        self.winner_text = None
        self.player_won = False
        self.fruit_spawn_timer = 0.0
        if self.difficulty["level"] == 2:
            self.player.weapon_type = "sword"
            self.player.weapon_range = 92

    def shutdown(self):
        if self.gesture_controller:
            self.gesture_controller.shutdown()
            self.gesture_controller = None

    def draw_cloud(self, x, y, scale):
        parts = [
            pygame.Rect(x, y, int(60 * scale), int(26 * scale)),
            pygame.Rect(x + int(24 * scale), y - int(14 * scale), int(58 * scale), int(34 * scale)),
            pygame.Rect(x + int(55 * scale), y, int(60 * scale), int(26 * scale)),
        ]
        for part in parts:
            pygame.draw.ellipse(screen, WHITE, part)
            pygame.draw.ellipse(screen, (220, 238, 248), part, 2)

    def draw_background(self):
        screen.fill(SKY_BLUE)
        pygame.draw.rect(screen, SKY_BLUE_DEEP, (0, 0, WIDTH, HEIGHT // 3))
        for x in range(0, WIDTH, max(24, sx(40))):
            pygame.draw.line(screen, (150, 220, 245), (x, 0), (x, HEIGHT), 1)
        for cloud in [
            (int(WIDTH * 0.08), int(HEIGHT * 0.12), 1.0),
            (int(WIDTH * 0.27), int(HEIGHT * 0.18), 0.8),
            (int(WIDTH * 0.58), int(HEIGHT * 0.13), 1.1),
        ]:
            self.draw_cloud(*cloud)
        back_mountains = [
            (0, GROUND_Y),
            (int(WIDTH * 0.12), int(HEIGHT * 0.60)),
            (int(WIDTH * 0.24), GROUND_Y),
            (int(WIDTH * 0.40), int(HEIGHT * 0.56)),
            (int(WIDTH * 0.58), GROUND_Y),
            (int(WIDTH * 0.74), int(HEIGHT * 0.58)),
            (WIDTH, GROUND_Y),
        ]
        front_mountains = [
            (0, GROUND_Y),
            (int(WIDTH * 0.09), int(HEIGHT * 0.67)),
            (int(WIDTH * 0.22), GROUND_Y),
            (int(WIDTH * 0.37), int(HEIGHT * 0.63)),
            (int(WIDTH * 0.54), GROUND_Y),
            (int(WIDTH * 0.71), int(HEIGHT * 0.65)),
            (WIDTH, GROUND_Y),
        ]
        pygame.draw.polygon(screen, (105, 190, 118), back_mountains)
        pygame.draw.polygon(screen, (84, 170, 100), front_mountains)
        sun_rect = pygame.Rect(WIDTH - display_sx(140), display_sy(40), display_sx(56), display_sy(56))
        pygame.draw.rect(screen, (255, 221, 90), sun_rect)
        pygame.draw.rect(screen, (255, 240, 150), (sun_rect.x + display_sx(8), sun_rect.y + display_sy(8), display_sx(16), display_sy(16)))
        pygame.draw.rect(screen, (235, 170, 50), sun_rect, 2)

    def read_keyboard_input(self):
        keys = pygame.key.get_pressed()
        move = (-1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0) + (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0)
        return {
            "move": move,
            "jump": self.keyboard_jump_buffer,
            "double_jump": self.keyboard_double_jump_buffer,
            "attack": self.keyboard_attack_buffer,
            "hideout_action": self.keyboard_hideout_exit,
        }

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            if event.type == pygame.VIDEORESIZE:
                update_window_size(event.w, event.h)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.hideouts[0].occupant is self.player:
                        self.keyboard_hideout_exit = True
                        continue
                    return self.pause_menu()
                if event.key in (pygame.K_q, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.keyboard_hideout_exit = True
                if self.control_mode == "keyboard":
                    if event.key in (pygame.K_w, pygame.K_UP):
                        now = time.time()
                        self.keyboard_double_jump_buffer = now - self.last_w_press <= 0.3
                        self.keyboard_jump_buffer = not self.keyboard_double_jump_buffer
                        self.last_w_press = now
                    elif event.key == pygame.K_SPACE:
                        self.keyboard_attack_buffer = True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self.control_mode == "keyboard":
                self.keyboard_attack_buffer = True
        return "continue"

    def resolve_inputs(self):
        if self.control_mode == "gesture" and self.gesture_controller:
            command = self.gesture_controller.get_command()
            command["hideout_action"] = command.get("hideout_action", False) or self.keyboard_hideout_exit
            return command
        return self.read_keyboard_input()

    def try_hideout_entry(self, player):
        for hideout in self.hideouts:
            if hideout.can_enter(player):
                hideout.try_enter(player)

    def move_toward_hideout(self, player, hideout):
        if player.hidden:
            return
        if player.rect.centerx < hideout.rect.centerx - 8:
            player.move(1)
        elif player.rect.centerx > hideout.rect.centerx + 8:
            player.move(-1)
        else:
            player.stop()

    def update_player(self, command):
        if command["hideout_action"]:
            if self.hideouts[0].occupant is self.player:
                self.hideouts[0].release()
            else:
                self.try_hideout_entry(self.player)
        self.player.move(command["move"])
        if command["move"] == 0:
            self.player.stop()
        if command["jump"]:
            self.player.jump()
        if command["double_jump"]:
            self.player.double_jump()
        if command["attack"]:
            if self.player.attack():
                self.spawn_player_attack()
        self.player.update_physics(self.platforms)
        self.player.collect_items(self.items)

    def spawn_player_attack(self):
        if self.player.weapon_type != "gun":
            return
        bullet_x, bullet_y = self.player.projectile_spawn()
        bullet_damage = self.difficulty["player_damage"] + (2 if self.player.power_timer > 0 else 0)
        self.bullets.append(Bullet(bullet_x, bullet_y, self.player.facing, YELLOW, bullet_damage))

    def update_enemy(self):
        hideout = self.hideouts[1]
        if self.enemy.hidden and self.enemy.hp >= self.enemy.max_hp * 0.72:
            hideout.release()
        elif self.enemy.hp <= 34 and not self.enemy.hidden and hideout.cooldown_timer <= 0 and hideout.occupant is None:
            self.move_toward_hideout(self.enemy, hideout)
            if self.enemy.rect.colliderect(hideout.rect):
                hideout.try_enter(self.enemy)
        else:
            self.enemy.update_ai(self.player, self.platforms)
        self.enemy.update_physics(self.platforms)
        self.enemy.collect_items(self.items)

    def resolve_attacks(self):
        player_hitbox = self.player.attack_rect()
        enemy_hitbox = self.enemy.attack_rect()
        player_damage = self.difficulty["player_damage"] + (2 if self.player.power_timer > 0 else 0)
        enemy_damage = self.difficulty["enemy_damage"]
        if player_hitbox and not self.enemy.hidden and player_hitbox.colliderect(self.enemy.rect) and "player" not in self.attack_hits:
            self.enemy.take_damage(player_damage, 8 * self.player.facing)
            self.attack_hits.add("player")
        if enemy_hitbox and not self.player.hidden and enemy_hitbox.colliderect(self.player.rect) and "enemy" not in self.attack_hits:
            self.player.take_damage(enemy_damage, 7 * self.enemy.facing)
            self.attack_hits.add("enemy")
        if not player_hitbox:
            self.attack_hits.discard("player")
        if not enemy_hitbox:
            self.attack_hits.discard("enemy")

    def update_items(self, dt):
        for item in self.items:
            if not item.collected:
                item.update(dt)
        for hideout in self.hideouts:
            hideout.update(dt)
        if self.difficulty["level"] == 2:
            self.fruit_spawn_timer += dt
            active_small = sum(1 for item in self.items if not item.collected and item.kind == "health_small")
            if self.fruit_spawn_timer >= 4.5 and active_small < 4:
                self.fruit_spawn_timer = 0.0
                spawn_points = [
                    (int(WIDTH * 0.24), int(HEIGHT * 0.60)),
                    (int(WIDTH * 0.52), int(HEIGHT * 0.42)),
                    (int(WIDTH * 0.78), int(HEIGHT * 0.22)),
                    (int(WIDTH * 0.66), int(HEIGHT * 0.32)),
                ]
                sx, sy = spawn_points[int(time.time()) % len(spawn_points)]
                self.items.append(FloatingItem(sx, sy, "health_small"))
        for bullet in self.bullets:
            bullet.update()
            if bullet.active and not self.enemy.hidden and bullet.rect.colliderect(self.enemy.rect):
                self.enemy.take_damage(bullet.damage, 9 * self.player.facing)
                bullet.active = False
        self.bullets = [bullet for bullet in self.bullets if bullet.active]

    def separate_fighters(self):
        if self.player.hidden or self.enemy.hidden:
            return
        if self.player.rect.colliderect(self.enemy.rect):
            overlap = self.player.rect.clip(self.enemy.rect)
            shift = max(4, overlap.width // 2 + 2)
            if self.player.rect.centerx < self.enemy.rect.centerx:
                self.player.rect.x -= shift
                self.enemy.rect.x += shift
            else:
                self.player.rect.x += shift
                self.enemy.rect.x -= shift
            self.player.rect.x = max(0, min(WIDTH - self.player.rect.width, self.player.rect.x))
            self.enemy.rect.x = max(0, min(WIDTH - self.enemy.rect.width, self.enemy.rect.x))

    def check_game_over(self):
        if self.player.hp <= 0:
            self.winner_text = "Enemy Wins!"
            self.player_won = False
            return True
        if self.enemy.hp <= 0:
            self.winner_text = f"{self.player_name} Wins!"
            self.player_won = True
            return True
        return False

    def hideout_status(self, hideout, label):
        if hideout.occupant:
            return f"{label} Hide: {hideout.timer:04.1f}s"
        if hideout.cooldown_timer > 0:
            return f"{label} Hide CD: {hideout.cooldown_timer:03.0f}s"
        return f"{label} Hide: Ready"

    def draw_bar(self, x, y, w, h, ratio, color):
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(screen, BLACK, (x, y, w, h))
        pygame.draw.rect(screen, (235, 235, 235), (x + 2, y + 2, w - 4, h - 4))
        inner = pygame.Rect(x + 3, y + 3, int((w - 6) * ratio), h - 6)
        pygame.draw.rect(screen, color, inner)
        if inner.w > 14:
            pygame.draw.rect(screen, WHITE, (inner.x + 4, inner.y + 3, max(8, inner.w // 3), 5))
        pygame.draw.rect(screen, BLACK, (x, y, w, h), 2)

    def draw_hud(self):
        bar_w = min(sx(260), WIDTH // 4)
        bar_h = max(sy(24), 20)
        left_x = sx(20)
        top_y = sy(18)
        right_x = WIDTH - left_x - bar_w
        self.draw_bar(left_x, top_y, bar_w, bar_h, self.player.hp / self.player.max_hp, tuple(self.profile["color"]))
        self.draw_bar(right_x, top_y, bar_w, bar_h, self.enemy.hp / self.enemy.max_hp, RED)
        screen.blit(FONT_SMALL.render(f"{self.player_name} HP: {int(self.player.hp)}", True, BLACK), (left_x + 4, top_y))
        right_text = FONT_SMALL.render(f"Enemy HP: {int(self.enemy.hp)}", True, BLACK)
        screen.blit(right_text, (right_x + bar_w - right_text.get_width() - 4, top_y))
        level = FONT_SMALL.render(f"Level {self.difficulty['level']} - {self.difficulty['name']}", True, BLACK)
        screen.blit(level, level.get_rect(center=(WIDTH // 2, top_y + bar_h // 2)))
        screen.blit(FONT_SMALL.render(self.hideout_status(self.hideouts[0], "P1"), True, BLACK), (left_x + 4, top_y + bar_h + sy(8)))
        enemy_status = FONT_SMALL.render(self.hideout_status(self.hideouts[1], "Enemy"), True, BLACK)
        screen.blit(enemy_status, (WIDTH - enemy_status.get_width() - left_x, top_y + bar_h + sy(8)))
        if self.control_mode == "gesture" and self.gesture_controller:
            status = FONT_SMALL.render(self.gesture_controller.status, True, BLACK)
            screen.blit(status, status.get_rect(center=(WIDTH // 2, top_y + bar_h + sy(12))))
        help_text = FONT_SMALL.render("A/D or Arrows move  W/Up jump  Space/Right Click attack  Q/Shift hideout  Esc exit hideout/menu", True, BLACK)
        screen.blit(help_text, help_text.get_rect(center=(WIDTH // 2, HEIGHT - sy(24))))

    def draw_level_map(self):
        map_box = pygame.Rect(WIDTH - sx(210), sy(88), sx(170), sy(96))
        pygame.draw.rect(screen, (248, 250, 255), map_box)
        pygame.draw.rect(screen, BLACK, map_box, 2)
        scale_x = (map_box.w - sx(20)) / WIDTH
        scale_y = (map_box.h - sy(26)) / HEIGHT
        for platform in self.platforms:
            mini = pygame.Rect(map_box.x + sx(10) + int(platform.rect.x * scale_x), map_box.y + sy(10) + int(platform.rect.y * scale_y), max(6, int(platform.rect.w * scale_x)), max(4, int(platform.rect.h * scale_y)))
            pygame.draw.rect(screen, ORANGE, mini)
        p_dot = (map_box.x + sx(10) + int(self.player.rect.centerx * scale_x), map_box.y + sy(10) + int(self.player.rect.centery * scale_y))
        e_dot = (map_box.x + sx(10) + int(self.enemy.rect.centerx * scale_x), map_box.y + sy(10) + int(self.enemy.rect.centery * scale_y))
        pygame.draw.circle(screen, tuple(self.profile["color"]), p_dot, max(4, smin(4)))
        pygame.draw.circle(screen, RED, e_dot, max(4, smin(4)))
        label = FONT_SMALL.render("Level Map", True, BLACK)
        screen.blit(label, label.get_rect(center=(map_box.centerx, map_box.y - sy(12))))

    def draw_world(self):
        self.draw_background()
        for platform in self.platforms:
            platform.draw(screen)
        for hideout in self.hideouts:
            hideout.draw(screen)
        for item in self.items:
            item.draw(screen)
        for bullet in self.bullets:
            bullet.draw(screen)
        self.player.draw(screen)
        self.enemy.draw(screen)
        self.draw_hud()
        self.draw_level_map()

    def overlay_menu(self, title, options):
        selected = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "Exit Game"
                if event.type == pygame.VIDEORESIZE:
                    update_window_size(event.w, event.h)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(options)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(options)
                    elif event.key == pygame.K_RETURN:
                        return options[selected]
                    elif event.key == pygame.K_ESCAPE and title == "Paused":
                        return "Continue"
            self.draw_world()
            panel = pygame.Rect((WIDTH - min(sx(420), WIDTH - sx(220))) // 2, max(sy(150), HEIGHT // 4), min(sx(420), WIDTH - sx(220)), min(sy(250), HEIGHT - sy(220)))
            pygame.draw.rect(screen, (25, 25, 35), panel)
            pygame.draw.rect(screen, WHITE, panel, 3)
            title_img = FONT_MEDIUM.render(title, True, WHITE)
            screen.blit(title_img, title_img.get_rect(center=(panel.centerx, panel.y + sy(40))))
            for i, option in enumerate(options):
                box_w = min(sx(300), panel.w - sx(80))
                box_h = max(sy(42), 38)
                box_gap = max(sy(16), 12)
                box = pygame.Rect(panel.centerx - box_w // 2, panel.y + sy(78) + i * (box_h + box_gap), box_w, box_h)
                pygame.draw.rect(screen, YELLOW if i == selected else ORANGE, box)
                pygame.draw.rect(screen, BLACK, box, 2)
                img = FONT_SMALL.render(option, True, BLACK)
                screen.blit(img, img.get_rect(center=box.center))
            pygame.display.flip()
            clock.tick(FPS)

    def pause_menu(self):
        result = self.overlay_menu("Paused", ["Continue", "Exit to Home", "Exit Game"])
        if result == "Continue":
            return "continue"
        if result == "Exit to Home":
            return "home"
        return "exit"

    def end_menu(self):
        result = self.overlay_menu(self.winner_text, ["Continue", "Exit to Home", "Exit Game"])
        if result == "Continue":
            return "continue"
        if result == "Exit to Home":
            return "home"
        return "exit"

    def run(self):
        dt = 1 / FPS
        result = "home"
        while self.running:
            event_result = self.handle_events()
            if event_result in ("home", "exit"):
                result = event_result
                break
            command = self.resolve_inputs()
            self.update_player(command)
            self.update_enemy()
            self.resolve_attacks()
            self.update_items(dt)
            self.separate_fighters()
            self.draw_world()
            pygame.display.flip()
            self.keyboard_jump_buffer = False
            self.keyboard_double_jump_buffer = False
            self.keyboard_attack_buffer = False
            self.keyboard_hideout_exit = False
            if self.check_game_over():
                result = self.end_menu()
                break
            clock.tick(FPS)
        self.shutdown()
        return result, self.player_won


def run_tutorial_screen(control_mode):
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"
            if event.type == pygame.VIDEORESIZE:
                update_window_size(event.w, event.h)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    waiting = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                waiting = False
        screen.fill(SKY_BLUE)
        pygame.draw.rect(screen, SKY_BLUE_DEEP, (0, 0, WIDTH, sy(180)))
        title = FONT_MEDIUM.render("Tutorial Level", True, BLACK)
        lines = [
            "Move on platforms and learn the arena before Level 1.",
            "Use hideouts to heal, and collect fruits to recover health.",
            "Blue upgrades to a sword in Level 2.",
            f"Current control mode: {control_mode.title()}",
            "Press Enter, click, or tap gesture select to continue.",
        ]
        screen.blit(title, title.get_rect(center=(WIDTH // 2, sy(90))))
        for i, line in enumerate(lines):
            img = FONT_SMALL.render(line, True, BLACK)
            screen.blit(img, img.get_rect(center=(WIDTH // 2, sy(200) + i * sy(52))))
        pygame.display.flip()
        clock.tick(FPS)
    return "continue"


def main():
    account_manager = AccountManager(ACCOUNTS_FILE)
    menu = MenuSystem(account_manager)
    if not menu.mode_selected:
        chosen = menu.mode_select_screen()
        if chosen == "exit" or not chosen:
            pygame.quit()
            sys.exit()
    while True:
        menu_result = menu.run()
        if menu_result["action"] == "exit":
            break
        mode = menu_result["control_mode"]
        profile = menu_result["profile"]
        selected_level_index = menu_result.get("level_index")
        if profile.get("username") != "Player" and not profile.get("tutorial_done", False):
            tutorial_result = run_tutorial_screen(mode)
            if tutorial_result == "exit":
                break
            profile["tutorial_done"] = True
            account_manager.mark_tutorial_done(profile["username"])
        difficulty_index = selected_level_index if selected_level_index is not None else max(0, min(len(GameManager.DIFFICULTIES) - 1, profile.get("current_level", 1) - 1))
        while True:
            game = GameManager(mode, profile, difficulty_index)
            result, won = game.run()
            if result == "exit":
                pygame.quit()
                sys.exit()
            if result == "home":
                break
            if won and difficulty_index < len(GameManager.DIFFICULTIES) - 1:
                difficulty_index += 1
                profile["current_level"] = difficulty_index + 1
                if profile["username"] != "Player":
                    account_manager.update_progress(profile["username"], profile["current_level"])
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
