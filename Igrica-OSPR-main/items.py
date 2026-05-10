# ================================================================
#  items.py  –  Item catalogue + pickup class
# ================================================================
import pygame, math, random
from settings import *

# ── Master item catalogue ────────────────────────────────────────
#   key        : internal ID used everywhere
#   name       : display name
#   desc       : tooltip text
#   color      : icon / glow colour
#   icon       : single character drawn on the pickup
#   value      : base shop price (gold)
#   stack      : True → consumable (multiple per slot)
#                False → equipment (one per slot)
ITEM_DATA = {
    "health_potion":  dict(name="Health Potion",   desc="Restores 50 HP",
                           color=RED,    icon="H", value=30,  stack=True),
    "stamina_potion": dict(name="Stamina Elixir",  desc="Restores 60 Stamina",
                           color=CYAN,   icon="S", value=25,  stack=True),
    "damage_boost":   dict(name="Power Gem",        desc="+10 Attack Damage (permanent)",
                           color=ORANGE, icon="D", value=60,  stack=False),
    "speed_boost":    dict(name="Wind Boots",        desc="+20 Move Speed (permanent)",
                           color=GREEN,  icon="V", value=55,  stack=False),
    "max_hp_up":      dict(name="Vitality Stone",    desc="+25 Max HP (permanent)",
                           color=RED,    icon="+", value=80,  stack=False),
    "gold_coin":      dict(name="Gold Coin",          desc="Worth 5 gold",
                           color=GOLD,   icon="G", value=5,   stack=True),
    "torch":          dict(name="Torch",               desc="Lights dark rooms",
                           color=ORANGE, icon="T", value=20,  stack=True),
}

# ── Shop stock lists  (item_id, price) ───────────────────────────
LOBBY_SHOP_STOCK = [
    ("health_potion",  30),
    ("stamina_potion", 25),
    ("damage_boost",   60),
    ("speed_boost",    55),
    ("max_hp_up",      80),
    ("torch",          20),
]

RUN_SHOP_STOCK = [
    ("health_potion",  20),
    ("stamina_potion", 15),
    ("damage_boost",   40),
    ("speed_boost",    35),
    ("torch",          15),
]

# ── Drop pools ───────────────────────────────────────────────────
NORMAL_DROP = ["health_potion", "stamina_potion", "gold_coin",
               "gold_coin",     "gold_coin"]
RARE_DROP   = ["damage_boost",  "speed_boost",    "max_hp_up",
               "health_potion", "stamina_potion"]


# ================================================================
class Item:
    """A world-space pickup that the player walks over."""

    _font_cache: dict = {}

    def __init__(self, x: float, y: float, itype: str):
        self.x, self.y = x, y
        self.itype     = itype
        self.picked    = False
        self._phase    = random.uniform(0, math.tau)   # bob offset
        self.count     = 1                              # for stacking

        d = ITEM_DATA.get(itype, {})
        self.name  = d.get("name",  itype)
        self.desc  = d.get("desc",  "")
        self.color = d.get("color", WHITE)
        self.icon  = d.get("icon",  "?")
        self.value = d.get("value", 0)
        self.stack = d.get("stack", False)

    # ── font helper ──────────────────────────────────────────────
    @classmethod
    def _font(cls, size: int = 18):
        if size not in cls._font_cache:
            cls._font_cache[size] = pygame.font.SysFont("Arial", size, bold=True)
        return cls._font_cache[size]

    # ── apply effect to player ───────────────────────────────────
    def use(self, player) -> bool:
        """Apply this item's effect.  Returns True if consumed."""
        match self.itype:
            case "health_potion":
                player.heal(50);                          return True
            case "stamina_potion":
                player.stamina = min(player.max_stamina,
                                     player.stamina + 60); return True
            case "damage_boost":
                player.dmg_bonus  += 10;                  return True
            case "speed_boost":
                player.speed_bonus += 20;                  return True
            case "max_hp_up":
                player.max_hp += 25
                player.hp = min(player.hp + 25, player.max_hp); return True
            case "gold_coin":
                player.gold += 5;                         return True
            case "torch":
                return True   # torch managed by scene
        return False

    # ── per-frame update ─────────────────────────────────────────
    def update(self, dt: float):
        self._phase += dt * 2.5

    # ── draw ─────────────────────────────────────────────────────
    def draw(self, screen: pygame.Surface, offset: tuple = (0, 0)):
        if self.picked:
            return
        ox, oy = offset
        sx = int(self.x - ox)
        sy = int(self.y - oy) + int(math.sin(self._phase) * 4)

        # soft glow
        glow = pygame.Surface((52, 52), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*self.color, 55), (26, 26), 24)
        screen.blit(glow, (sx - 26, sy - 26))

        # body
        pygame.draw.circle(screen, DARK_GRAY, (sx, sy), 16)
        pygame.draw.circle(screen, self.color,  (sx, sy), 16, 2)

        # icon letter
        lbl = self._font(18).render(self.icon, True, self.color)
        screen.blit(lbl, (sx - lbl.get_width() // 2,
                          sy - lbl.get_height() // 2))

    # ── collision rect ───────────────────────────────────────────
    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - 16, int(self.y) - 16, 32, 32)

    # ── str / repr ───────────────────────────────────────────────
    def __repr__(self):
        return f"Item({self.itype}, x{self.count})"
