# ================================================================
#  main.py  –  Entry point & game state machine
# ================================================================
import pygame, sys, math, random

from settings import *
from entities import Player
from scenes   import MainScreen, LobbyScene, DungeonScene
from scenes.main_screen import SettingsPanel
from ui       import draw_text, draw_panel, font

pygame.init()
pygame.mixer.set_num_channels(12)   # channels 0-11; shop/dialog use 7-9
pygame.display.set_caption(TITLE)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock  = pygame.time.Clock()


#kr neki
class Particle:
    def __init__(self): self.reset()

    def reset(self):
        self.x=random.uniform(0, WIDTH)
        self.y=random.uniform(0, HEIGHT)
        self.vx=random.uniform(-18, 18)
        self.vy=random.uniform(-30, -8)
        self.life=random.uniform(2.0, 5.0)
        self.t=0.0
        self.r=random.randint(2, 5)
        self.col=random.choice([PURPLE, ACCENT, CYAN, (180, 100, 255), (100, 80, 200)])

    def update(self, dt):
        self.t+=dt
        self.x+=self.vx * dt
        self.y+=self.vy * dt
        if self.t>=self.life or self.y<-10:
            self.reset(); self.y=HEIGHT+5

    def draw(self, surf):
        a = int(200 * max(0, 1.0-self.t / self.life))
        s = pygame.Surface((self.r*2, self.r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.col, a), (self.r, self.r), self.r)
        surf.blit(s, (int(self.x)-self.r, int(self.y)-self.r))


PARTICLES=[Particle() for _ in range(80)]


def draw_bg(surf, t):
    surf.fill(DARK_BG)
    for p in PARTICLES:
        p.draw(surf)
    for i in range(6):
        y=(HEIGHT*i//6 + int(t*18))%HEIGHT
        a=int(20 + 10 * math.sin(t+i))
        s2=pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
        s2.fill((*ACCENT, a))
        surf.blit(s2, (0, y))


def update_bg(dt):
    for p in PARTICLES:
        p.update(dt)


def _draw_menu_btn(surf, label, cx, cy):
    mx, my=pygame.mouse.get_pos()
    hover=abs(mx - cx) < 100 and abs(my - cy) < 24
    bg=(70, 50, 100) if hover else (40, 28, 62)
    brd= GOLD if hover else ACCENT
    rect=pygame.Rect(cx-110, cy-26,220,52)
    draw_panel(surf, rect, bg=bg, border=brd, radius=10)
    col=GOLD if hover else WHITE
    draw_text(surf, label, cx, cy-12, 24, col, bold=True, center=True)


#class select
def menu_class(t):
    """Returns chosen class name, '__quit__', or '__back__', or None."""
    draw_bg(screen, t)
    draw_text(screen, "CHOOSE YOUR CLASS",
              WIDTH // 2, 60, 36, GOLD, bold=True, center=True)
    draw_text(screen, "Click a class or press 1 / 2 / 3",
              WIDTH // 2, 108, 16, GRAY, center=True)

    classes = ["Knight", "Mage", "Assassin"]
    descs   = {
        "Knight":   ["High HP & Armor", "Wide melee swing",
                     "Medium speed",    "Low crit chance"],
        "Mage":     ["Long-range staff", "Very high damage",
                     "High stamina pool","Glass cannon"],
        "Assassin": ["Dual daggers",     "Fastest speed",
                     "Highest crit rate","Medium HP"],
    }
    colors = {k: CLASSES[k]["color"] for k in classes}

    cw  = 280; gap = 40
    total = len(classes) * cw + (len(classes) - 1) * gap
    sx0 = WIDTH // 2 - total // 2
    cy  = HEIGHT // 2 - 60; ch = 300
    mx, my = pygame.mouse.get_pos()

    for i, cls in enumerate(classes):
        bx    = sx0 + i * (cw + gap)
        hover = bx < mx < bx + cw and cy < my < cy + ch
        pulse = abs(math.sin(t * 2 + i))
        bg    = (55, 40, 82) if hover else (28, 20, 44)
        brd   = colors[cls]  if hover else ACCENT
        draw_panel(screen, pygame.Rect(bx, cy, cw, ch), bg=bg, border=brd, radius=12)
        if hover:
            g = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.draw.rect(g, (*colors[cls], int(30 + 20 * pulse)), g.get_rect(), border_radius=12)
            screen.blit(g, (bx, cy))
        draw_text(screen, f"[{i + 1}]", bx + 14, cy + 10, 14, GRAY)
        draw_text(screen, cls, bx + cw // 2, cy + 24, 28, colors[cls], bold=True, center=True)
        pygame.draw.line(screen, brd, (bx + 20, cy + 62), (bx + cw - 20, cy + 62), 1)

        stats_map = {
            "Knight":   dict(HP=150, DMG=35, SPD=200, STAM=100),
            "Mage":     dict(HP=80,  DMG=65, SPD=185, STAM=160),
            "Assassin": dict(HP=100, DMG=50, SPD=260, STAM=130),
        }
        maxes = dict(HP=150, DMG=65, SPD=260, STAM=160)
        st    = stats_map[cls]
        bar_y = cy + 76
        bar_x_label = bx + 14; bar_x_start = bx + 60; bar_w = cw - 80
        for sname, sval in st.items():
            pct = sval / maxes[sname]
            draw_text(screen, sname, bar_x_label, bar_y, 12, LIGHT_GRAY)
            pygame.draw.rect(screen, (30, 22, 46),
                             (bar_x_start, bar_y + 2, bar_w, 11), border_radius=3)
            pygame.draw.rect(screen, colors[cls],
                             (bar_x_start, bar_y + 2, int(bar_w * pct), 11), border_radius=3)
            bar_y += 20

        dy = bar_y + 8
        for line in descs[cls]:
            if dy + 16 > cy + ch - 30: break
            draw_text(screen, f"• {line}", bx + 14, dy, 12, LIGHT_GRAY)
            dy += 17

        if hover:
            draw_text(screen, "Click to Select", bx + cw // 2, cy + ch - 30,
                      14, GOLD, bold=True, center=True)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:        return "__quit__"
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_1:      return "Knight"
            if ev.key == pygame.K_2:      return "Mage"
            if ev.key == pygame.K_3:      return "Assassin"
            if ev.key == pygame.K_ESCAPE: return "__back__"
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, cls in enumerate(classes):
                bx = sx0 + i * (cw + gap)
                if bx < mx < bx + cw and cy < my < cy + ch:
                    return cls
    return None


#koncni ekran
def screen_end(won: bool, player: Player, t_start: float):
    """Loop error v lobby ali quit"""
    t = 0.0
    accent=GOLD if won else RED
    panel_bg=(10, 6, 2) if won else (6, 2, 14)

    pw, ph=580, 380
    px=WIDTH //2-pw//2
    py=HEIGHT// 2-ph//2-30
    btn1_y=py+ph + 68
    btn2_y=py+ph + 136

    while True:
        dt=clock.tick(FPS)/1000.0
        t+=dt
        update_bg(dt)
        draw_bg(screen, t)
        pulse = 0.5 + 0.5 * math.sin(t * 1.1)
        # layered glow around panel
        for r in (3, 2, 1):
            gs = pygame.Surface((pw + r * 24, ph + r * 24), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*accent, int(55 * pulse / r)), gs.get_rect(), border_radius=20)
            screen.blit(gs, (px - r * 12, py - r * 12))

        # main panel
        draw_panel(screen, pygame.Rect(px, py, pw, ph),
                   bg=panel_bg, border=accent, radius=14)

        # corner gems
        csz = 10
        for cx2, cy2 in [(px + 8, py + 8), (px + pw - csz - 8, py + 8),
                         (px + 8, py + ph - csz - 8), (px + pw - csz - 8, py + ph - csz - 8)]:
            pygame.draw.rect(screen, accent, (cx2, cy2, csz, csz), border_radius=2)

        # title
        if won:
            scale=1.0+0.05*math.sin(t*1.4)
            tf=font(int(66*scale), True)
            ts=tf.render("VICTORY!", True, GOLD)
            sub_txt="bravoski!"
            sub_col=YELLOW
        else:
            flicker=0.78+0.22*math.sin(t*3.2)
            tf=font(70, True)
            ts=tf.render("YOU DIED", True,(int(210*flicker), int(35*flicker), int(35*flicker)))
            sub_txt="ne bravoski"
            sub_col=LIGHT_GRAY
        screen.blit(ts, (WIDTH//2-ts.get_width()//2, py+28))
        draw_text(screen, sub_txt, WIDTH//2, py+108, 19, sub_col, center=True)

        # divider with diamond centrepiece
        div_y = py + 138
        pygame.draw.line(screen, accent, (px + 50, div_y), (px + pw - 50, div_y), 1)
        dm = 5
        pygame.draw.polygon(screen, accent, [
            (WIDTH // 2,      div_y - dm),
            (WIDTH // 2 + dm, div_y),
            (WIDTH // 2,      div_y + dm),
            (WIDTH // 2 - dm, div_y),
        ])

        #Statistike run-na
        lx=px+pw//3
        vx=px+pw*2//3
        row_h=38
        stats=[
            ("Gold collected",str(player.gold),GOLD),
            ("Damage bonus",f"+{player.dmg_bonus}",ORANGE),
            ("Speed bonus",f"+{player.speed_bonus}",GREEN),
            ("Items in bag",str(len(player.inventory)),LIGHT_GRAY),
        ]
        for i, (label, val, vc) in enumerate(stats):
            ry = div_y + 16 + i * row_h
            if i % 2 == 0:
                alt = pygame.Surface((pw - 40, row_h - 4), pygame.SRCALPHA)
                alt.fill((255, 255, 255, 10))
                screen.blit(alt, (px + 20, ry - 2))
            draw_text(screen, label, lx, ry + 9, 16, GRAY,           center=True)
            draw_text(screen, val,   vx, ry + 9, 19, vc, bold=True,  center=True)

        #ostalo
        _draw_menu_btn(screen, "BACK TO LOBBY",WIDTH//2,btn1_y)
        _draw_menu_btn(screen, "QUIT",WIDTH//2,btn2_y)
        draw_text(screen, "[ R ] Lobby    [ Esc ] Quit", WIDTH // 2, HEIGHT - 24, 13, GRAY, center=True)
        pygame.display.flip()
        mx, my = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: 
                return "quit"
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_r, pygame.K_RETURN): 
                    return "lobby"
                if ev.key == pygame.K_ESCAPE:                
                    return "quit"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if abs(mx - WIDTH // 2) < 110:
                    if abs(my - btn1_y) < 26: 
                        return "lobby"
                    if abs(my - btn2_y) < 26: 
                        return "quit"


#pause
def draw_pause(screen):
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 150))
    screen.blit(ov, (0, 0))
    draw_text(screen, "PAUSED", WIDTH // 2, HEIGHT // 2 - 60,
              52, WHITE, bold=True, center=True)
    draw_text(screen, "[ Esc ] Resume / Back to Lobby",
              WIDTH // 2, HEIGHT // 2 + 10, 18, GRAY, center=True)


# ================================================================
#  Main game loop
# ================================================================
def main():
    #trenutno stanje
    state   = "mainscreen"
    player  = None
    lobby   = None
    dungeon = None
    t       = 0.0
    t_run_start = 0.0
    ms      = None   # MainScreen instance
    saved_settings = SettingsPanel(0.7, 0.5, 0.5, 0.5, 0.5, 1)  # shared settings skozi celotno igro

    while True:
        fps_target=SettingsPanel.FPS_OPTIONS[saved_settings.fps_idx] #poskus fps nastavitev
        dt = min(clock.tick(fps_target) / 1000.0, 0.05)
        t += dt
        update_bg(dt)

        # ── MAIN SCREEN ───────────────────────────────────────────
        if state == "mainscreen":
            if ms is None:
                ms = MainScreen(screen, clock, settings=saved_settings)

            result = ms.run()          # blocks until ('play', class) or 'quit'

            if result == "quit":
                pygame.quit(); sys.exit()
            elif isinstance(result, tuple) and result[0] == "play":
                chosen_class = result[1]
                ms.stop_music(fade_ms=500)
                ms = None
                player = Player(
                    LOBBY_W // 2 * TILE + TILE // 2,
                    LOBBY_H // 2 * TILE + TILE // 2,
                    chosen_class,
                )
                player.max_inv_slots = INV_SLOTS_START
                lobby = LobbyScene(player)
                lobby.pause_ui._sett = saved_settings   # poveži settings s pause menijem
                state = "lobby"

        # ── LOBBY ─────────────────────────────────────────────────
        elif state == "lobby":
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            lobby.update(dt, events)
            screen.fill(DARK_BG)
            lobby.draw(screen)

            # preveri scene po update
            if lobby.next_scene == "mainmenu":
                lobby.next_scene = None
                lobby = None
                ms = MainScreen(screen, clock, settings=saved_settings)
                state = "mainscreen"
            elif lobby.next_scene == "quit":
                pygame.quit(); sys.exit()
            elif lobby.next_scene:
                _, diff = lobby.next_scene
                lobby.next_scene = None
                dungeon = DungeonScene(player, diff, settings=saved_settings)
                t_run_start = t
                state = "dungeon"

            pygame.display.flip()

        #dungeon scene
        elif state == "dungeon":
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            dungeon.update(dt, events)
            screen.fill(DARK_BG)
            dungeon.draw(screen)

            if dungeon.next_scene == "lobby":
                won    = dungeon.won
                pygame.mixer.music.fadeout(700)
                result = screen_end(won, player, t_run_start)
                if result == "quit":
                    pygame.quit(); sys.exit()

                # reset player position & state for next run
                player.x       = LOBBY_W // 2 * TILE + TILE // 2
                player.y       = LOBBY_H // 2 * TILE + TILE // 2
                player.hp      = float(player.max_hp)
                player.stamina = float(player.max_stamina)
                player.alive   = True
                player.dashing = False
                player.floats  = []

                lobby   = LobbyScene(player)
                lobby.pause_ui._sett = saved_settings   # poveži settings tudi po vrnitvi iz dungeonа
                dungeon = None
                state   = "lobby"

            pygame.display.flip()


# ================================================================
if __name__ == "__main__":
    main()