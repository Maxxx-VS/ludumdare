import random
from config import WIDTH, HEIGHT

class SignalBlock:
    def __init__(self, pose_type, speed):
        self.pose = pose_type
        self.x = random.randint(50, WIDTH - 200)
        self.y = -50
        self.speed = speed
        self.hit = False

    def move(self):
        self.y += self.speed

class GameEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.score = 0
        self.combo = 0
        self.signal = 100
        self.blocks = []
        self.state = "MENU"
        self.speed_mult = 1.0

    def spawn_block(self):
        pose = random.choice(["T_POSE", "HANDS_UP", "CROSS_ARMS", "SQUAT"])
        self.blocks.append(SignalBlock(pose, 2.5 * self.speed_mult))

    def update(self, current_pose):
        if self.state != "PLAYING": return

        # Зона захвата
        capture_min, capture_max = HEIGHT - 120, HEIGHT - 20

        for b in self.blocks[:]:
            b.move()
            if b.y > HEIGHT:
                self.blocks.remove(b)
                self.combo = 0
                self.signal -= 15
            elif capture_min < b.y < capture_max:
                if b.pose == current_pose and not b.hit:
                    b.hit = True
                    self.score += 100 + (self.combo * 10)
                    self.combo += 1
                    self.signal = min(100, self.signal + 10)
                    self.blocks.remove(b)

        self.signal -= 0.1
        if self.signal <= 0: self.state = "GAME_OVER"