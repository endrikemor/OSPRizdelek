# ================================================================
#  entities.py  –  Player, Enemies, Projectiles, FloatingText
# ================================================================
import pygame, math, random
from settings import *

#lebdeče številke ki se prikazejo ob škodi, healing, XP
class FloatingText:
    _cache: dict = {}

    def __init__(self, x, y, text, color=WHITE, size=20, dur=1.2):
        self.x, self.y = float(x), float(y)
        self.text  = text
        self.color = color
        self.dur   = dur
        self.t     = 0.0
        self.vy    = -65.0
        if size not in FloatingText._cache:
            FloatingText._cache[size] = pygame.font.SysFont("Arial", size, bold=True)
        self._font = FloatingText._cache[size]

    def update(self, dt):
        self.t  += dt
        self.y  += self.vy * dt
        self.vy *= 0.93        # decelerate

    @property
    def alive(self): return self.t < self.dur

    def draw(self, screen, ox=0, oy=0):
        alpha = max(0, int(255 * (1.0 - self.t / self.dur)))
        surf  = self._font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        screen.blit(surf, (int(self.x - ox) - surf.get_width()  // 2,
                           int(self.y - oy) - surf.get_height() // 2))


#puščica — projektil skeletov in bossa
class Arrow:
    def __init__(self, x, y, dx, dy, dmg, speed=310, col=None):
        self.x,  self.y  = float(x), float(y)
        self.vx, self.vy = dx * speed, dy * speed
        self.dmg   = dmg
        self.col   = col or (220, 200, 100)
        self.alive = True
        self._age  = 0.0

    def update(self, dt, walls):
        self._age += dt
        if self._age > 4.0:
            self.alive = False
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        r = pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)
        for w in walls:
            if r.colliderect(w):
                self.alive = False
                return

    def draw(self, screen, offset=(0, 0)):
        ox, oy = offset
        sx, sy = int(self.x - ox), int(self.y - oy)
        ang = math.atan2(self.vy, self.vx)
        tail = (sx - math.cos(ang) * 10, sy - math.sin(ang) * 10)
        pygame.draw.line(screen, self.col, (int(tail[0]), int(tail[1])),
                         (sx, sy), 3)
        pygame.draw.circle(screen, self.col, (sx, sy), 4)



def _angle_diff(a, b):
    d = b - a
    while d >  math.pi: d -= math.tau
    while d < -math.pi: d += math.tau
    return d


def _circle_rect(cx, cy, r, rect):
    nx = max(rect.left, min(cx, rect.right))
    ny = max(rect.top,  min(cy, rect.bottom))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


#class — gibanje, attack, stats, inventory
class Player:
    def __init__(self, x, y, cls="Knight"):
        self.x, self.y   = float(x), float(y)
        self.cls         = cls
        st               = CLASSES[cls]

        # ── base stats ───────────────────────────────────────────
        self.max_hp       = st["max_hp"]
        self.hp           = float(self.max_hp)
        self.max_stamina  = st["max_stamina"]
        self.stamina      = float(self.max_stamina)
        self.speed        = st["speed"]
        self.base_damage  = st["damage"]
        self.atk_range    = st["atk_range"]
        self.atk_rate     = st["atk_rate"]
        self.crit_chance  = st["crit"]
        self.color        = st["color"]
        self.radius       = 20

        # ── bonus stats (from items) ──────────────────────────────
        self.dmg_bonus    = 0
        self.speed_bonus  = 0

        # ── economy ──────────────────────────────────────────────
        self.gold         = 0

        # ── combat timers ────────────────────────────────────────
        self.atk_timer    = 99.0
        self.atk_anim     = 0.0
        self.atk_angle    = 0.0
        self.face_angle   = 0.0
        self.inv_timer    = 0.0    # invincibility frames after hit

        # ── dash ─────────────────────────────────────────────────
        self.dashing      = False
        self.dash_timer   = 0.0
        self.dash_dir     = (0.0, 0.0)
        self.dash_cd      = 0.0

        # ── animation ────────────────────────────────────────────
        self.walk_anim    = 0.0

        # ── inventory ────────────────────────────────────────────
        self.inventory    = []     # list[Item]
        self.storage      = []     # list[Item] — persistent lobby storage

        # ── floating texts ───────────────────────────────────────
        self.floats       = []

        # ── alive ────────────────────────────────────────────────
        self.alive        = True

        # ── XP / Level ───────────────────────────────────────────
        self.xp            = 0
        self.level         = 1
        self.xp_to_next    = 100
        self.skill_points  = 0
        self.unlocked_skills: set  = set()
        self.active_skills: list   = [None, None, None, None]  # hotbar

        # ── active skill state ───────────────────────────────────
        self.skill_cds: dict       = {}   # id → remaining cooldown
        self.poison_active         = False
        self.poison_stacks         = 0    # hits remaining
        self.battle_cry_timer      = 0.0
        self.smoke_screen_timer    = 0.0
        self.dmg_reduction         = 0.0  # fraction  e.g. 0.20

        # ── pending projectiles (filled by use_skill) ────────────
        self.pending_projectiles: list = []

    # ── derived stats ────────────────────────────────────────────
    @property
    def damage(self): return self.base_damage + self.dmg_bonus

    # ── main update ──────────────────────────────────────────────
    def update(self, dt, keys, mpos, mbtns, walls, enemies, cam=(0, 0)):
        if not self.alive:
            return

        self.atk_timer = min(self.atk_timer + dt, 99.0)
        self.atk_anim  = max(0.0, self.atk_anim  - dt * 5)
        self.inv_timer = max(0.0, self.inv_timer  - dt)
        self.dash_cd   = max(0.0, self.dash_cd    - dt)
        self.battle_cry_timer   = max(0.0, self.battle_cry_timer   - dt)
        self.smoke_screen_timer = max(0.0, self.smoke_screen_timer - dt)
        for k in list(self.skill_cds):
            self.skill_cds[k] = max(0.0, self.skill_cds[k] - dt)

        if not self.dashing:
            self.stamina = min(self.max_stamina,
                               self.stamina + STAM_REGEN * dt)

        for f in self.floats: f.update(dt)
        self.floats = [f for f in self.floats if f.alive]

        # ── dash movement ────────────────────────────────────────
        if self.dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.dashing = False
            else:
                self._move(self.dash_dir[0] * DASH_SPEED * dt,
                           self.dash_dir[1] * DASH_SPEED * dt, walls)
            return

        # ── normal movement ──────────────────────────────────────
        vx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
             int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        vy = int(keys[pygame.K_s] or keys[pygame.K_DOWN])  - \
             int(keys[pygame.K_w] or keys[pygame.K_UP])
        if vx and vy:
            vx *= 0.7071; vy *= 0.7071
        spd = self.speed + self.speed_bonus
        if vx or vy:
            self.walk_anim += dt * 8
        self._move(vx * spd * dt, vy * spd * dt, walls)

        # ── face mouse ───────────────────────────────────────────
        mx = mpos[0] + cam[0] - self.x
        my = mpos[1] + cam[1] - self.y
        self.face_angle = math.atan2(my, mx)

        # ── attack on LMB ────────────────────────────────────────
        if mbtns[0] and self.atk_timer >= 1.0 / self.atk_rate:
            self._do_attack(enemies)

    #dash
    def start_dash(self, keys):
        if self.dash_cd > 0 or self.stamina < DASH_COST:
            return
        vx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
             int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        vy = int(keys[pygame.K_s] or keys[pygame.K_DOWN])  - \
             int(keys[pygame.K_w] or keys[pygame.K_UP])
        if vx == 0 and vy == 0:
            dx, dy = math.cos(self.face_angle), math.sin(self.face_angle)
        else:
            mag = math.hypot(vx, vy) or 1
            dx, dy = vx / mag, vy / mag
        self.dashing    = True
        self.dash_timer = DASH_DUR
        self.dash_cd    = DASH_CD
        self.stamina   -= DASH_COST
        self.dash_dir   = (dx, dy)

    #napad z lokom — preveri sovražnike v kotu pred igralcem
    def _do_attack(self, enemies):
        self.atk_timer = 0.0
        self.atk_angle = self.face_angle
        self.atk_anim  = 1.0

        arc_bonus = math.radians(35) if "cleave" in self.unlocked_skills else 0
        arc = math.radians(
            110 if self.cls == "Knight" else
             80 if self.cls == "Assassin" else 15
        ) + arc_bonus

        for e in enemies:
            if not e.alive: continue
            dx = e.x - self.x
            dy = e.y - self.y
            dist = math.hypot(dx, dy)
            if dist <= self.atk_range + e.radius:
                to_enemy = math.atan2(dy, dx)
                if abs(_angle_diff(self.atk_angle, to_enemy)) <= arc / 2:
                    crit = random.random() < self.crit_chance
                    dmg  = int(self.damage
                               * (2.0 if crit else 1.0)
                               * random.uniform(0.88, 1.12))
                    # battle cry bonus
                    if self.battle_cry_timer > 0:
                        dmg = int(dmg * 1.6)
                    # execute bonus (Assassin)
                    if "execute" in self.unlocked_skills:
                        if e.hp / e.max_hp < 0.30:
                            dmg = int(dmg * 2.0)
                    # overload (Mage)
                    if "overload" in self.unlocked_skills:
                        if random.random() < 0.25:
                            dmg = int(dmg * 3.0)
                            crit = True
                    e.take_damage(dmg)
                    # poison blade
                    if self.poison_active and self.poison_stacks > 0:
                        e.apply_poison(8, 4.0)
                        self.poison_stacks -= 1
                        if self.poison_stacks <= 0:
                            self.poison_active = False
                    # knockback
                    if dist > 0:
                        e.kb_vx += (dx / dist) * 220
                        e.kb_vy += (dy / dist) * 220
                    col = YELLOW if crit else ORANGE
                    lbl = f"CRIT {dmg}!" if crit else str(dmg)
                    self.floats.append(
                        FloatingText(e.x, e.y - 30, lbl, col,
                                     22 if crit else 18))

    #prejme škodo — upošteva neranljivost, mana shield, iron skin
    def take_damage(self, dmg):
        if self.inv_timer > 0 or self.dashing or self.smoke_screen_timer > 0:
            return
        # mana_shield: absorb with stamina first
        if "mana_shield" in self.unlocked_skills and self.stamina > 0:
            absorbed = min(self.stamina, dmg)
            self.stamina -= absorbed
            dmg -= int(absorbed)
        # iron_skin damage reduction
        dmg = int(dmg * (1.0 - self.dmg_reduction))
        if dmg <= 0:
            return
        self.hp = max(0.0, self.hp - dmg)
        self.inv_timer = 0.45
        self.floats.append(FloatingText(self.x, self.y - 50,
                                         f"-{dmg}", RED, 20))
        if self.hp <= 0:
            self.alive = False

    #heal
    def heal(self, amount):
        old = self.hp
        self.hp = min(float(self.max_hp), self.hp + amount)
        gained = int(self.hp - old)
        if gained > 0:
            self.floats.append(FloatingText(self.x, self.y - 40,
                                             f"+{gained}", GREEN, 18))

    #hitbox movement
    def _move(self, dx, dy, walls):
        self.x += dx
        for w in walls:
            if _circle_rect(self.x, self.y, self.radius, w):
                self.x = (w.right  + self.radius) if dx < 0 else \
                         (w.left   - self.radius)
        self.y += dy
        for w in walls:
            if _circle_rect(self.x, self.y, self.radius, w):
                self.y = (w.bottom + self.radius) if dy < 0 else \
                         (w.top    - self.radius)

    # ── draw ─────────────────────────────────────────────────────
    def draw(self, screen, offset=(0, 0)):
        ox, oy = offset
        sx, sy = int(self.x - ox), int(self.y - oy)
        bob    = int(math.sin(self.walk_anim) * 3)

        # shadow
        pygame.draw.ellipse(screen, (20, 15, 30),
                            (sx - 20, sy + 14, 40, 12))

        # ── Knight specific ──────────────────────────────────────
        if self.cls == "Knight":
            col = self.color
            # body
            pygame.draw.circle(screen, col, (sx, sy + bob), self.radius)
            # armour shine
            pygame.draw.circle(screen,
                               tuple(min(255, c + 40) for c in col),
                               (sx - 6, sy + bob - 6), 8)
            # helmet
            pygame.draw.rect(screen, (130, 130, 195),
                             (sx - 13, sy - 24 + bob, 26, 20),
                             border_radius=4)
            pygame.draw.rect(screen, (160, 160, 220),
                             (sx - 11, sy - 22 + bob, 22, 15),
                             border_radius=3)
            # visor slit
            pygame.draw.rect(screen, (50, 50, 75),
                             (sx - 8, sy - 14 + bob, 16, 4))
            # sword
            fa  = self.face_angle
            base = (sx + math.cos(fa) * (self.radius + 4),
                    sy + math.sin(fa) * (self.radius + 4) + bob)
            tip  = (sx + math.cos(fa) * (self.radius + 40),
                    sy + math.sin(fa) * (self.radius + 40) + bob)
            pygame.draw.line(screen, (210, 200, 165),
                             (int(base[0]), int(base[1])),
                             (int(tip[0]),  int(tip[1])), 4)
            # crossguard
            perp = fa + math.pi / 2
            gx = sx + math.cos(fa) * (self.radius + 9)
            gy = sy + math.sin(fa) * (self.radius + 9) + bob
            pygame.draw.line(screen, (180, 170, 140),
                             (int(gx + math.cos(perp) * 7),
                              int(gy + math.sin(perp) * 7)),
                             (int(gx - math.cos(perp) * 7),
                              int(gy - math.sin(perp) * 7)), 3)

        # ── Mage ─────────────────────────────────────────────────
        elif self.cls == "Mage":
            pygame.draw.circle(screen, (200, 180, 255),
                               (sx, sy + bob), self.radius)
            fa  = self.face_angle
            tip = (sx + math.cos(fa) * (self.radius + 44),
                   sy + math.sin(fa) * (self.radius + 44) + bob)
            pygame.draw.line(screen, (160, 140, 100),
                             (sx, sy + bob),
                             (int(tip[0]), int(tip[1])), 3)
            pygame.draw.circle(screen, PURPLE,
                               (int(tip[0]), int(tip[1])), 7)
            pygame.draw.circle(screen, (220, 180, 255),
                               (int(tip[0]), int(tip[1])), 4)

        # ── Assassin ─────────────────────────────────────────────
        else:
            pygame.draw.circle(screen, self.color, (sx, sy + bob), self.radius)
            fa = self.face_angle
            for off in (-0.18, 0.18):
                ang = fa + off
                tip = (sx + math.cos(ang) * (self.radius + 36),
                       sy + math.sin(ang) * (self.radius + 36) + bob)
                pygame.draw.line(screen, (220, 70, 70),
                                 (sx, sy + bob),
                                 (int(tip[0]), int(tip[1])), 3)

        # ── attack arc flash ─────────────────────────────────────
        if self.atk_anim > 0:
            arc_deg = (110 if self.cls == "Knight" else
                        80 if self.cls == "Assassin" else 25)
            r2 = self.atk_range
            s  = pygame.Surface((r2 * 2 + 12, r2 * 2 + 12), pygame.SRCALPHA)
            # negate angle: pygame.draw.arc uses standard math coords
            # but atan2 was computed in screen coords (Y flipped)
            sa = -math.degrees(self.atk_angle) - arc_deg / 2
            pygame.draw.arc(s, (255, 220, 0, int(180 * self.atk_anim)),
                            (6, 6, r2 * 2, r2 * 2),
                            math.radians(sa),
                            math.radians(sa + arc_deg), 4)
            screen.blit(s, (sx - r2 - 6, sy - r2 - 6))

        # ── dash ghost ───────────────────────────────────────────
        if self.dashing:
            g = pygame.Surface((self.radius * 4, self.radius * 4),
                               pygame.SRCALPHA)
            pygame.draw.circle(g, (*self.color, 60),
                               (self.radius * 2, self.radius * 2),
                               self.radius + 4)
            screen.blit(g, (sx - self.radius * 2, sy - self.radius * 2))

        # ── invincibility flicker ─────────────────────────────────
        if self.inv_timer > 0 and int(self.inv_timer * 10) % 2 == 0:
            pygame.draw.circle(screen, WHITE,
                               (sx, sy + bob), self.radius + 2, 2)

        # ── floating numbers ─────────────────────────────────────
        for f in self.floats:
            f.draw(screen, ox, oy)

    # ── XP / levelling ───────────────────────────────────────────
    def gain_xp(self, amount: int):
        from settings import xp_to_level
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.xp        -= self.xp_to_next
            self.level     += 1
            self.xp_to_next = xp_to_level(self.level)
            self.skill_points += 1
            self.floats.append(
                FloatingText(self.x, self.y - 70,
                             f"LEVEL UP! ({self.level})", GOLD, 24, 2.5))

    # unlock za skill tree
    def unlock_skill(self, skill_id: str) -> bool:
        from settings import SKILL_TREES
        tree  = SKILL_TREES.get(self.cls, [])
        skill = next((s for s in tree if s["id"] == skill_id), None)
        if not skill: return False
        if skill_id in self.unlocked_skills: return False
        req = skill.get("req")
        if req and req not in self.unlocked_skills: return False
        if self.skill_points < skill["cost"]: return False
        self.skill_points -= skill["cost"]
        self.unlocked_skills.add(skill_id)
        self._apply_passive(skill)
        if skill["stype"] == "active":
            for i in range(4):
                if self.active_skills[i] is None:
                    self.active_skills[i] = skill_id; break
        return True

    def _apply_passive(self, skill: dict):
        sid = skill["id"]
        if sid == "fortify":        self.max_hp += 25; self.hp = min(self.hp+25, self.max_hp)
        elif sid == "iron_skin":    self.dmg_reduction = min(0.50, self.dmg_reduction + 0.20)
        elif sid == "arcane_mastery": self.dmg_bonus += 20
        elif sid == "quick_hands":  self.atk_rate += 0.5

    # ── use active skill (slot 0-3) ──────────────────────────────
    def use_skill(self, slot: int, enemies: list, mpos: tuple,
                  cam: tuple, walls: list):
        if slot >= len(self.active_skills): return
        sid = self.active_skills[slot]
        if not sid: return
        if self.skill_cds.get(sid, 0) > 0: return
        from settings import SKILL_TREES
        tree  = SKILL_TREES.get(self.cls, [])
        sdata = next((s for s in tree if s["id"] == sid), None)
        self.skill_cds[sid] = sdata.get("cd", 5.0) if sdata else 5.0
        wx = mpos[0] + cam[0]; wy = mpos[1] + cam[1]

        if sid == "shield_bash":
            for e in enemies:
                if not e.alive: continue
                dist = math.hypot(e.x-self.x, e.y-self.y)
                if dist < 130:
                    e.take_damage(int(self.damage*0.8))
                    if dist > 0: e.kb_vx += (e.x-self.x)/dist*400; e.kb_vy += (e.y-self.y)/dist*400
            self.floats.append(FloatingText(self.x, self.y-50, "SHIELD BASH!", CYAN, 22))
        elif sid == "battle_cry":
            self.battle_cry_timer = 5.0
            self.floats.append(FloatingText(self.x, self.y-50, "BATTLE CRY!", ORANGE, 22))
        elif sid == "fireball":
            dx = wx-self.x; dy = wy-self.y; n = max(1, math.hypot(dx,dy))
            self.pending_projectiles.append(
                PlayerProjectile(self.x, self.y, dx/n, dy/n, int(self.damage*1.8), 380, ORANGE, 10))
        elif sid == "blink":
            tx = max(64.0, min(float(wx), 1280-64.0))
            ty = max(64.0, min(float(wy),  640-64.0))
            if not any(_circle_rect(tx, ty, self.radius, w) for w in walls):
                self.x, self.y = tx, ty
            self.floats.append(FloatingText(self.x, self.y-50, "BLINK!", PURPLE, 22))
        elif sid == "chain_lightning":
            for e in sorted([e for e in enemies if e.alive],
                            key=lambda e: math.hypot(e.x-self.x, e.y-self.y))[:5]:
                e.take_damage(int(self.damage*1.2))
                e.kb_vx += random.uniform(-150,150); e.kb_vy += random.uniform(-150,150)
            self.floats.append(FloatingText(self.x, self.y-50, "LIGHTNING!", CYAN, 22))
        elif sid == "poison_blade":
            self.poison_active = True; self.poison_stacks = 8
            self.floats.append(FloatingText(self.x, self.y-50, "POISON BLADE!", GREEN, 22))
        elif sid == "smoke_screen":
            self.smoke_screen_timer = 3.0; self.inv_timer = 3.0
            self.floats.append(FloatingText(self.x, self.y-50, "SMOKE SCREEN!", GRAY, 22))
        elif sid == "fan_of_knives":
            for e in enemies:
                if e.alive and math.hypot(e.x-self.x, e.y-self.y) < self.atk_range*1.5:
                    e.take_damage(int(self.damage*1.1))
            self.atk_anim = 1.0
            self.floats.append(FloatingText(self.x, self.y-50, "FAN OF KNIVES!", RED, 22))


#stats enemy
ENEMY_STATS = {
    "slime":    dict(hp=40,  spd=95,  dmg=8,  rng=36,  rate=1.0,
                     rad=18, xp=5,   gold=3,  col=(55,  180, 55)),
    "skeleton": dict(hp=55,  spd=110, dmg=12, rng=280, rate=0.7,
                     rad=16, xp=8,   gold=5,  col=(200, 200,180)),
    "orc":      dict(hp=120, spd=80,  dmg=22, rng=46,  rate=0.6,
                     rad=26, xp=15,  gold=10, col=(80,  140, 60)),
    "boss":     dict(hp=400, spd=115, dmg=28, rng=66,  rate=0.8,
                     rad=36, xp=100, gold=50, col=(175,  40,175)),
}

class Enemy:
    def __init__(self, x, y, etype, diff_m=1.0):
        self.x, self.y = float(x), float(y)
        self.etype = etype
        st = ENEMY_STATS[etype]

        self.max_hp    = int(st["hp"]  * diff_m)
        self.hp        = self.max_hp
        self.speed     = st["spd"]
        self.damage    = int(st["dmg"] * diff_m)
        self.atk_range = st["rng"]
        self.atk_rate  = st["rate"]
        self.color     = st["col"]
        self.radius    = st["rad"]
        self.xp_value  = st["xp"]
        self.gold_value= st["gold"]

        self.atk_timer  = 0.0
        self.inv_timer  = 0.0
        self.hit_flash  = 0.0
        self.state      = "idle"
        self.los_timer  = 0.0   # seconds since last confirmed LoS
        self.detect_r   = 290
        self.kb_vx = self.kb_vy = 0.0
        self.walk_anim  = 0.0
        self.alive      = True
        self.floats     = []
        self.projectiles= []
        # poison
        self.poison_timer = 0.0
        self.poison_dmg   = 0
        self.poison_tick  = 0.0

    # ── update loop ──────────────────────────────────────────────
    def update(self, dt, player, walls):
        if not self.alive:
            return

        self.atk_timer += dt
        self.inv_timer  = max(0.0, self.inv_timer - dt)
        self.hit_flash  = max(0.0, self.hit_flash  - dt)

        # knockback decay
        if abs(self.kb_vx) > 1 or abs(self.kb_vy) > 1:
            self.kb_vx *= 0.80
            self.kb_vy *= 0.80
            self._move(self.kb_vx * dt, self.kb_vy * dt, walls)

        for f in self.floats: f.update(dt)
        self.floats = [f for f in self.floats if f.alive]

        # poison damage tick
        if self.poison_timer > 0:
            self.poison_timer -= dt
            self.poison_tick  -= dt
            if self.poison_tick <= 0:
                self.poison_tick = 0.5
                self.hp = max(0, self.hp - self.poison_dmg)
                self.floats.append(
                    FloatingText(self.x, self.y - self.radius - 8,
                                 str(self.poison_dmg), GREEN, 15))
                if self.hp <= 0:
                    self.hp = 0; self.alive = False; return

        # hit check in update projectiles
        for p in self.projectiles:
            p.update(dt, walls)
        for p in self.projectiles:
            if p.alive:
                if math.hypot(p.x - player.x,
                              p.y - player.y) < player.radius + 6:
                    player.take_damage(self.damage)
                    p.alive = False
        self.projectiles = [p for p in self.projectiles if p.alive]

        # line of sight
        dist    = math.hypot(player.x - self.x, player.y - self.y)
        can_see = dist < self.detect_r and self._has_los(player.x, player.y, walls)
        if can_see:
            self.state    = "chase"
            self.los_timer = 0.0
        elif self.state in ("chase", "attack"):
            self.los_timer += dt
            if self.los_timer > 2.0:
                self.state    = "idle"
                self.los_timer = 0.0

        if self.state == "chase":
            if dist <= self.atk_range:
                self.state = "attack"
            else:
                dx = player.x - self.x
                dy = player.y - self.y
                n  = max(1.0, math.hypot(dx, dy))
                self._move(dx / n * self.speed * dt,
                           dy / n * self.speed * dt, walls)
                self.walk_anim += dt * 6

        if self.state == "attack":
            if dist > self.atk_range * 1.6:
                self.state = "chase"
            elif self.atk_timer >= 1.0 / self.atk_rate:
                self.do_attack(player)
                self.atk_timer = 0.0

    def do_attack(self, player): pass

    def _has_los(self, tx, ty, walls) -> bool:
        """Ray-cast LoS — True if no wall tile blocks the straight path."""
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return True
        steps = max(4, int(dist / 8))   # ~8 px per step → precise
        for i in range(1, steps):
            t  = i / steps
            px = int(self.x + dx * t)
            py = int(self.y + dy * t)
            for w in walls:
                if w.collidepoint(px, py):
                    return False
        return True

    def apply_poison(self, dmg_per_tick: int, duration: float):
        self.poison_dmg   = max(self.poison_dmg, dmg_per_tick)
        self.poison_timer = max(self.poison_timer, duration)
        self.poison_tick  = min(self.poison_tick, 0.5) if self.poison_tick > 0 else 0.5

    def take_damage(self, dmg):
        if self.inv_timer > 0:
            return
        self.hp -= dmg
        self.hit_flash = 0.15
        self.inv_timer = 0.10
        self.floats.append(
            FloatingText(self.x + random.uniform(-10, 10),
                         self.y - self.radius - 8,
                         str(dmg), RED, 17))
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False

    def _move(self, dx, dy, walls):
        self.x += dx
        for w in walls:
            if _circle_rect(self.x, self.y, self.radius, w):
                self.x = (w.right  + self.radius) if dx < 0 else \
                         (w.left   - self.radius)
        self.y += dy
        for w in walls:
            if _circle_rect(self.x, self.y, self.radius, w):
                self.y = (w.bottom + self.radius) if dy < 0 else \
                         (w.top    - self.radius)

    def draw(self, screen, offset=(0, 0)):
        if not self.alive:
            return
        ox, oy = offset
        sx, sy = int(self.x - ox), int(self.y - oy)
        bob    = int(math.sin(self.walk_anim) * 3)
        col    = WHITE if self.hit_flash > 0 else self.color

        # shadow
        pygame.draw.ellipse(screen, (20, 15, 30),
                            (sx - self.radius, sy + self.radius - 5,
                             self.radius * 2, 10))

        self._draw_body(screen, sx, sy, col, bob)

        # life bar
        bw = self.radius * 2 + 10
        bx = sx - bw // 2
        by = sy - self.radius - 16
        pygame.draw.rect(screen, DARK_RED, (bx, by, bw, 6))
        pct = max(0, self.hp / self.max_hp)
        pygame.draw.rect(screen, RED, (bx, by, int(bw * pct), 6))
        pygame.draw.rect(screen, LIGHT_GRAY, (bx, by, bw, 6), 1)

        for f in self.floats:     f.draw(screen, ox, oy)
        for p in self.projectiles: p.draw(screen, offset)

    def _draw_body(self, screen, sx, sy, col, bob):
        pygame.draw.circle(screen, col, (sx, sy + bob), self.radius)


# ================================================================
#  Slime
# ================================================================
class Slime(Enemy):
    def __init__(self, x, y, diff_m=1.0):
        super().__init__(x, y, "slime", diff_m)

    def do_attack(self, player):
        player.take_damage(self.damage)

    def _draw_body(self, screen, sx, sy, col, bob):
        sq = abs(math.sin(self.walk_anim * 0.5))
        w  = int(self.radius * 2 * (1 + sq * 0.3))
        h  = int(self.radius * 2 * (1 - sq * 0.2))
        pygame.draw.ellipse(screen, col,
                            (sx - w // 2, sy - h // 2 + bob, w, h))
        # shine
        pygame.draw.ellipse(screen,
                            tuple(min(255, c + 50) for c in col),
                            (sx - w // 2 + 4, sy - h // 2 + bob + 3,
                             w // 3, h // 4))
        # eyes
        o = int(self.radius * 0.35)
        for ex, dot in ((sx + o, 1), (sx - o, 1)):
            pygame.draw.circle(screen, (20, 20, 20), (ex, sy - 3 + bob), 3)
            pygame.draw.circle(screen, WHITE, (ex + 1, sy - 4 + bob), 1)


#skeleton
class Skeleton(Enemy):
    PREFERRED_DIST = 210

    def __init__(self, x, y, diff_m=1.0):
        super().__init__(x, y, "skeleton", diff_m)

    def update(self, dt, player, walls):
        if not self.alive: return

        self.atk_timer += dt
        self.inv_timer  = max(0.0, self.inv_timer - dt)
        self.hit_flash  = max(0.0, self.hit_flash  - dt)

        if abs(self.kb_vx) > 1 or abs(self.kb_vy) > 1:
            self.kb_vx *= 0.80; self.kb_vy *= 0.80
            self._move(self.kb_vx * dt, self.kb_vy * dt, walls)

        for f in self.floats: f.update(dt)
        self.floats = [f for f in self.floats if f.alive]

        for p in self.projectiles: p.update(dt, walls)
        for p in self.projectiles:
            if p.alive and math.hypot(p.x - player.x,
                                      p.y - player.y) < player.radius + 6:
                player.take_damage(self.damage); p.alive = False
        self.projectiles = [p for p in self.projectiles if p.alive]

        dist    = math.hypot(player.x - self.x, player.y - self.y)
        can_see = dist < self.detect_r and self._has_los(player.x, player.y, walls)
        if can_see:
            self.state    = "chase"
            self.los_timer = 0.0
        elif self.state in ("chase", "attack"):
            self.los_timer += dt
            if self.los_timer > 2.0:
                self.state    = "idle"
                self.los_timer = 0.0

        if self.state in ("chase", "attack"):
            # strafe to keep preferred distance
            dx = player.x - self.x
            dy = player.y - self.y
            n  = max(1, math.hypot(dx, dy))
            if dist < self.PREFERRED_DIST - 25:
                self._move(-dx / n * self.speed * 0.6 * dt,
                           -dy / n * self.speed * 0.6 * dt, walls)
            elif dist > self.PREFERRED_DIST + 25:
                self._move( dx / n * self.speed * 0.6 * dt,
                             dy / n * self.speed * 0.6 * dt, walls)
                self.walk_anim += dt * 5

            if self.atk_timer >= 1.0 / self.atk_rate and \
               dist <= self.atk_range:
                self.do_attack(player)
                self.atk_timer = 0.0

    def do_attack(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        n  = max(1, math.hypot(dx, dy))
        self.projectiles.append(
            Arrow(self.x, self.y, dx / n, dy / n, self.damage))

    def _draw_body(self, screen, sx, sy, col, bob):
        # skull
        pygame.draw.circle(screen, col, (sx, sy - 5 + bob), 12)
        # eye sockets
        pygame.draw.circle(screen, (20, 20, 20), (sx - 4, sy - 6 + bob), 2)
        pygame.draw.circle(screen, (20, 20, 20), (sx + 4, sy - 6 + bob), 2)
        # spine & ribs
        pygame.draw.rect(screen,  col, (sx - 4, sy + 6 + bob, 8, 16))
        pygame.draw.line(screen,  col, (sx - 13, sy + 8  + bob),
                                       (sx - 4,  sy + 8  + bob), 2)
        pygame.draw.line(screen,  col, (sx + 4,  sy + 8  + bob),
                                       (sx + 13, sy + 8  + bob), 2)
        pygame.draw.line(screen,  col, (sx - 11, sy + 13 + bob),
                                       (sx - 4,  sy + 13 + bob), 2)
        pygame.draw.line(screen,  col, (sx + 4,  sy + 13 + bob),
                                       (sx + 11, sy + 13 + bob), 2)


# ================================================================
#  Orc  (heavy melee)
# ================================================================
class Orc(Enemy):
    def __init__(self, x, y, diff_m=1.0):
        super().__init__(x, y, "orc", diff_m)

    def do_attack(self, player):
        player.take_damage(self.damage)

    def _draw_body(self, screen, sx, sy, col, bob):
        pygame.draw.circle(screen, col, (sx, sy + bob), self.radius)
        # tusks
        pygame.draw.line(screen, (240, 220, 180),
                         (sx - 8,  sy + 8  + bob),
                         (sx - 10, sy + 16 + bob), 3)
        pygame.draw.line(screen, (240, 220, 180),
                         (sx + 8,  sy + 8  + bob),
                         (sx + 10, sy + 16 + bob), 3)
        # brow ridge
        pygame.draw.line(screen, (50, 100, 40),
                         (sx - 10, sy - 6 + bob),
                         (sx + 10, sy - 6 + bob), 3)
        # eyes
        for ex in (sx - 7, sx + 7):
            pygame.draw.circle(screen, (210, 55, 55), (ex, sy + bob), 4)
            pygame.draw.circle(screen, BLACK,          (ex, sy + bob), 2)


# ================================================================
#  Boss  (two-phase)
# ================================================================
class Boss(Enemy):
    def __init__(self, x, y, diff_m=1.0, stage=1):
        super().__init__(x, y, "boss", diff_m)
        self.stage       = stage
        self.phase       = 1
        self._spread_cd  = 0.0

    def update(self, dt, player, walls):
        if self.hp < self.max_hp * 0.5:
            self.phase = 2
        super().update(dt, player, walls)

        # phase 2: extra spread shots
        if self.phase == 2 and self.alive:
            self._spread_cd -= dt
            if self._spread_cd <= 0:
                self._spread_cd = 0.70
                dx = player.x - self.x
                dy = player.y - self.y
                n  = max(1, math.hypot(dx, dy))
                for spread in (-0.44, 0.0, 0.44):
                    ang = math.atan2(dy, dx) + spread
                    self.projectiles.append(
                        Arrow(self.x, self.y,
                              math.cos(ang), math.sin(ang),
                              self.damage // 3, speed=230, col=PURPLE))

    def do_attack(self, player):
        player.take_damage(self.damage)

    def _draw_body(self, screen, sx, sy, col, bob):
        # phase 2 glow
        if self.phase == 2:
            g = pygame.Surface((self.radius * 4, self.radius * 4),
                               pygame.SRCALPHA)
            pygame.draw.circle(g, (255, 0, 0, 45),
                               (self.radius * 2, self.radius * 2),
                               self.radius * 2)
            screen.blit(g, (sx - self.radius * 2, sy - self.radius * 2))

        pygame.draw.circle(screen, col, (sx, sy + bob), self.radius)

        # crown
        pts = [
            (sx - 16, sy - self.radius     + bob),
            (sx - 11, sy - self.radius - 14 + bob),
            (sx -  5, sy - self.radius     + bob),
            (sx,      sy - self.radius - 20 + bob),
            (sx +  5, sy - self.radius     + bob),
            (sx + 11, sy - self.radius - 14 + bob),
            (sx + 16, sy - self.radius     + bob),
        ]
        pygame.draw.polygon(screen, GOLD, pts)

        # eyes  (red in phase 2)
        ec = RED if self.phase == 2 else YELLOW
        for ex in (sx - 11, sx + 11):
            pygame.draw.circle(screen, ec,    (ex, sy - 4 + bob), 6)
            pygame.draw.circle(screen, BLACK, (ex, sy - 4 + bob), 3)


# ================================================================
#  Skill tree ability
# ================================================================
class PlayerProjectile:
    def __init__(self, x, y, dx, dy, dmg, speed=380, col=ORANGE, rad=10):
        self.x,  self.y  = float(x), float(y)
        self.vx, self.vy = dx * speed, dy * speed
        self.dmg   = dmg
        self.col   = col
        self.rad   = rad
        self.alive = True
        self._age  = 0.0

    def update(self, dt, walls, enemies):
        self._age += dt
        if self._age > 4.0:
            self.alive = False; return
        self.x += self.vx * dt
        self.y += self.vy * dt
        r = pygame.Rect(int(self.x)-self.rad, int(self.y)-self.rad,
                        self.rad*2, self.rad*2)
        for w in walls:
            if r.colliderect(w):
                self.alive = False; return
        for e in enemies:
            if not e.alive: continue
            if math.hypot(self.x-e.x, self.y-e.y) < self.rad + e.radius:
                e.take_damage(self.dmg)
                self.alive = False; return

    def draw(self, screen, offset=(0,0)):
        ox, oy = offset
        sx, sy = int(self.x-ox), int(self.y-oy)
        glow = pygame.Surface((self.rad*4, self.rad*4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.col, 80),
                           (self.rad*2, self.rad*2), self.rad*2)
        screen.blit(glow, (sx-self.rad*2, sy-self.rad*2))
        pygame.draw.circle(screen, self.col,  (sx,sy), self.rad)
        pygame.draw.circle(screen, WHITE,      (sx,sy), self.rad//3)