# Globalne konstane ki so prelepo poravnane DungeonIgricaOSPR
import os

# poti
BASE_DIR    = os.path.dirname(__file__)
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
MUSIC_DIR   = os.path.join(ASSETS_DIR, "music")
SOUNDS_DIR  = os.path.join(ASSETS_DIR, "sounds")
IMAGES_DIR  = os.path.join(ASSETS_DIR, "images")

MUSIC_PATH      = os.path.join(MUSIC_DIR,  "Flood Escape 2 OST - Lobby (2020 Version).mp3")
BENEATH_PATH       = os.path.join(MUSIC_DIR,  "Beneath the mask - Persona 5.mp3")
DUNGEON_MUSIC_PATH = os.path.join(MUSIC_DIR, "MusicDungeon", "Flood Escape 2 OST - Snowy Peaks.mp3")
HOVER_SFX_PATH  = os.path.join(SOUNDS_DIR, "HoverSound.mp3")
SELECT_SFX_PATH = os.path.join(SOUNDS_DIR, "SelectSound.mp3")
LOGO_SFX_PATH        = os.path.join(SOUNDS_DIR, "LogoSound.mp3")
TEXT_SFX_PATH        = os.path.join(SOUNDS_DIR, "TextSound.MP3")
OSU_LOGO_PATH        = os.path.join(IMAGES_DIR, "GameLogo.png")
SHOP_NPC_IMG_PATH    = os.path.join(IMAGES_DIR, "ShopClovek.png")
STORAGE_NPC_IMG_PATH = os.path.join(IMAGES_DIR, "StorageClovek.png")
BARRIER_PATH         = os.path.join(BASE_DIR, ".barriers")

# window
WIDTH,  HEIGHT  = 1280, 720
HUD_H           = 80
GAME_H          = HEIGHT - HUD_H   # 640 px  – playable viewport
FPS             = 60
TITLE           = "Erik Kobe – DungeonIgricaOSPR"

#color
BLACK       = (  0,   0,   0)
WHITE       = (255, 255, 255)
RED         = (210,  50,  50)
DARK_RED    = (120,  20,  20)
GREEN       = ( 50, 190,  50)
DARK_GREEN  = ( 20,  90,  20)
BLUE        = ( 55, 110, 215)
YELLOW      = (240, 210,   0)
GOLD        = (255, 200,   0)
GRAY        = (110, 110, 115)
DARK_GRAY   = ( 42,  38,  50)
LIGHT_GRAY  = (195, 195, 200)
ORANGE      = (255, 145,   0)
PURPLE      = (150,  55, 225)
CYAN        = ( 55, 205, 230)

# UI in world colors
DARK_BG     = ( 12,   8,  18)
LOBBY_BG    = ( 16,  12,  26)
FLOOR_CLR   = ( 52,  44,  68)
WALL_CLR    = ( 26,  20,  38)
DOOR_OPEN   = ( 90,  70,  42)
DOOR_SHUT   = ( 55,  48,  68)
ACCENT      = ( 90,  55, 140)

#Velikost tile-ov, velikost sobe, velikost lobija
TILE    = 64
ROOM_W  = 20
ROOM_H  = 10
LOBBY_W = 24
LOBBY_H = 12

#classi
CLASSES = {
    "Knight": dict(
        max_hp=150, max_stamina=100, speed=200,
        damage=35,  atk_range=80,   atk_rate=1.3,
        crit=0.10,  color=(155, 155, 230)
    ),
    "Mage": dict(
        max_hp=80,  max_stamina=160, speed=185,
        damage=65,  atk_range=320,  atk_rate=0.9,
        crit=0.15,  color=(110, 110, 255)
    ),
    "Assassin": dict(
        max_hp=100, max_stamina=130, speed=260,
        damage=50,  atk_range=75,   atk_rate=2.2,
        crit=0.25,  color=(210,  60,  60)
    ),
}

#settings za tezavnost
DIFFICULTY = {
    "Easy":   dict(stages=5,  hp_m=0.70, dmg_m=0.70, gold_m=1.0),
    "Medium": dict(stages=10, hp_m=1.00, dmg_m=1.00, gold_m=1.5),
    "Hard":   dict(stages=15, hp_m=1.50, dmg_m=1.50, gold_m=2.0),
}

# dash
DASH_SPEED  = 650
DASH_DUR    = 0.13
DASH_CD     = 1.00
DASH_COST   = 28

# ── Stamina regen ────────────────────────────────────────────────
STAM_REGEN  = 22

# ── Camera smoothing ─────────────────────────────────────────────
CAM_SMOOTH  = 8.0

#inventory settings
INV_SLOTS_START = 20
INV_SLOTS_MAX   = 60
INV_STACK_MAX   = 64

#leveling
def xp_to_level(level: int) -> int:
    return int(100 + (level - 1) * 80)

# ── Skill Trees ──────────────────────────────────────────────────
SKILL_TREES = {
    "Knight": [
        dict(id="fortify",      name="Fortify",       desc="+25 Max HP",
             cost=1, req=None,          stype="passive", row=0, col=0),
        dict(id="shield_bash",  name="Shield Bash",   desc="AOE knockback (hotbar)",
             cost=1, req=None,          stype="active",  row=0, col=1, cd=6.0),
        dict(id="cleave",       name="Cleave",         desc="Attack arc +35°",
             cost=2, req="fortify",     stype="passive", row=1, col=0),
        dict(id="charge",       name="Charge",         desc="Dash deals 40 damage",
             cost=2, req="shield_bash", stype="passive", row=1, col=1),
        dict(id="iron_skin",    name="Iron Skin",      desc="Take 20% less damage",
             cost=3, req="cleave",      stype="passive", row=2, col=0),
        dict(id="battle_cry",   name="Battle Cry",     desc="+60% dmg 5s (hotbar)",
             cost=3, req="charge",      stype="active",  row=2, col=1, cd=15.0),
    ],
    "Mage": [
        dict(id="arcane_mastery", name="Arcane Mastery", desc="+20 spell damage",
             cost=1, req=None,               stype="passive", row=0, col=0),
        dict(id="fireball",       name="Fireball",        desc="Shoots fireball (hotbar)",
             cost=1, req=None,               stype="active",  row=0, col=1, cd=3.0),
        dict(id="mana_shield",    name="Mana Shield",     desc="Stamina absorbs damage",
             cost=2, req="arcane_mastery",   stype="passive", row=1, col=0),
        dict(id="blink",          name="Blink",           desc="Teleport to cursor (hotbar)",
             cost=2, req="fireball",         stype="active",  row=1, col=1, cd=8.0),
        dict(id="overload",       name="Overload",        desc="25% chance: triple damage",
             cost=3, req="mana_shield",      stype="passive", row=2, col=0),
        dict(id="chain_lightning",name="Chain Lightning", desc="AOE lightning (hotbar)",
             cost=3, req="blink",            stype="active",  row=2, col=1, cd=10.0),
    ],
    "Assassin": [
        dict(id="quick_hands",   name="Quick Hands",   desc="+0.5 attacks/sec",
             cost=1, req=None,            stype="passive", row=0, col=0),
        dict(id="poison_blade",  name="Poison Blade",  desc="Toggle poison (hotbar)",
             cost=1, req=None,            stype="active",  row=0, col=1, cd=0.0),
        dict(id="shadow_step",   name="Shadow Step",   desc="Dash costs 0 stamina",
             cost=2, req="quick_hands",   stype="passive", row=1, col=0),
        dict(id="smoke_screen",  name="Smoke Screen",  desc="3s invincible (hotbar)",
             cost=2, req="poison_blade",  stype="active",  row=1, col=1, cd=20.0),
        dict(id="execute",       name="Execute",       desc="+100% dmg vs low-HP",
             cost=3, req="shadow_step",   stype="passive", row=2, col=0),
        dict(id="fan_of_knives", name="Fan of Knives", desc="360° attack (hotbar)",
             cost=3, req="smoke_screen",  stype="active",  row=2, col=1, cd=8.0),
    ],
}
