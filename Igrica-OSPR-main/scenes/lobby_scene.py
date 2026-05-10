import os, pygame, math, threading, time
from settings import *
from entities import Player
from world import Lobby
from items import LOBBY_SHOP_STOCK
from ui import HUD, ShopUI, PortalUI, PauseUI, StorageUI, NpcDialog
from ui.helpers import draw_text, draw_panel, font, add_to_inv
from .main_screen import _detect_beats

_FC = {}

def _font(size, bold=False):
    k = (size, bold)
    if k not in _FC:
        for n in ["Nunito", "Segoe UI", "Arial Rounded MT Bold", "Verdana"]:
            try:
                _FC[k] = pygame.font.SysFont(n, size, bold=bold)
                break
            except Exception:
                pass
        else:
            _FC[k] = pygame.font.SysFont(None, size, bold=bold)
    return _FC[k]

# Za dodatne barrierje
_FOREGROUND_RECTS = []
_EXTRA_WALLS = []

#dialogi
_SHOP_TEXT    = "Mercator kongresni trg"
_STORAGE_TEXT = "To je skladišče... Mislim da daš lahko stvari not če dela :)"

#interacion range
_INTERACT_RANGE = 180


def _smooth(c, tgt, spd, dt):
    return c + (tgt - c) * (1. - math.exp(-spd * dt))

class LobbyScene:
    def __init__(self, player=None):
        self.world = Lobby()

        spawn_x = LOBBY_W // 2 * TILE + TILE // 2
        spawn_y = (LOBBY_H - 3) * TILE

        if player:
            self.player = player
            self.player.x = spawn_x
            self.player.y = spawn_y
        else:
            self.player = Player(spawn_x, spawn_y, "Knight")
            self.player.max_inv_slots = INV_SLOTS_START

        if not hasattr(self.player, 'max_inv_slots'):
            self.player.max_inv_slots = INV_SLOTS_START

        # storage is initialized in Player.__init__; ensure it exists for old saves
        if not hasattr(self.player, 'storage'):
            self.player.storage = []

        self.walls = self.world.get_walls()
        if not os.path.exists(BARRIER_PATH):
            self.walls += _EXTRA_WALLS
        self.walls += _FOREGROUND_RECTS

        self.cam_x = 0.0
        self.cam_y = 0.0
        self.hud        = HUD()
        self.shop_ui    = ShopUI()
        self.storage_ui = StorageUI()
        self.portal_ui  = PortalUI()
        self.pause_ui   = PauseUI()
        self.dialog     = NpcDialog()
        # inventory lives inside pause_ui — self.pause_ui.inv_ui

        self.font_small = _font(13)
        self.font_np    = _font(17, bold=True)
        self.now_playing_t = 0.0
        self.eq_heights = [5.0] * 6
        self._music_vol     = 0.0    # current volume
        self._music_vol_tgt = 0.15   # target volume
        self._music_fade_t  = 0.0    # elapsed fade time
        self._music_fade_dur = 1.5   # seconds to reach full volume
        self._start_lobby_music()
        self.beat_times  = []
        self.beat_idx    = 0
        self.beats_ready = False
        self.beat_flash  = 0.0
        self.smooth_beat = 0.0
        self.last_mouse_move = pygame.time.get_ticks()
        self.ui_alpha = 255
        self.ui_scale = 1.0
        self.is_hovered = False
        self._screen_fade_alpha = 255.0
        self._screen_fade_dur   = 1.5
        threading.Thread(target=self._load_beats, daemon=True).start()

        self.teleporter_rect = pygame.Rect(LOBBY_W // 2 * TILE - TILE, TILE, 2*TILE, 2*TILE)
        self.shop_rect       = pygame.Rect(3*TILE, 4*TILE, 3*TILE, 2*TILE)
        self.storage_rect    = pygame.Rect((LOBBY_W - 6) * TILE, 4*TILE, 4*TILE, 3*TILE)

        self._lobby_stock = list(LOBBY_SHOP_STOCK) + [("bag_upgrade", 100)]
        self.next_scene = None

    # ── convenience property ─────────────────────────────────────────────────
    @property
    def inv_ui(self):
        """Backwards-compat: inventory lives inside pause_ui."""
        return self.pause_ui.inv_ui

    # ── Update ───────────────────────────────────────────────────────────────
    def update(self, dt, events):
        keys = pygame.key.get_pressed()
        mpos = pygame.mouse.get_pos()
        current_time = pygame.time.get_ticks()

        # ── meniji odprti? ───────────────────────────────────────────────────
        any_menu_open = (
            self.pause_ui.phase != 'closed' or
            self.pause_ui.inv_ui.is_open or
            self.shop_ui.open or
            self.storage_ui.is_open or
            self.portal_ui.open or
            self.dialog.is_open
        )

        ui_rect = pygame.Rect(28, HEIGHT - 62, 220, 44)
        self.is_hovered = ui_rect.collidepoint(mpos)

        if any_menu_open:
            self.ui_alpha = max(0,   self.ui_alpha - 1000 * dt)
            self.ui_scale = max(0.8, self.ui_scale - 2.0  * dt)
        elif self.is_hovered:
            self.ui_alpha = min(255, self.ui_alpha + 800 * dt)
            self.ui_scale = min(1.0, self.ui_scale + 0.5  * dt)
            self.last_mouse_move = current_time
        else:
            if current_time - self.last_mouse_move > 0:
                self.ui_alpha = max(120, self.ui_alpha - 150 * dt)
                self.ui_scale = max(0.9, self.ui_scale - 0.5  * dt)
            else:
                self.ui_alpha = min(255, self.ui_alpha + 500 * dt)
                self.ui_scale = min(1.0, self.ui_scale + 2.0  * dt)

        # ── update pause_ui (vključno z notranjim inv_ui) ────────────────────
        self.pause_ui.update(dt)

        # ── eventi ───────────────────────────────────────────────────────────
        for ev in events:
            # 1. Pause menu has highest priority
            if self.pause_ui.phase != 'closed':
                self.pause_ui.handle_event(ev, self)
                continue

            # 2. NPC dialog
            if self.dialog.is_open:
                self.dialog.handle_event(ev)
                # Check result immediately after event (dialog may have just closed)
                if not self.dialog.is_open and self.dialog.result == 'yes':
                    if self.dialog.kind == 'shop':
                        self.shop_ui.show(self._lobby_stock, "MERCHANT")
                    elif self.dialog.kind == 'storage':
                        self.storage_ui.show()
                continue

            # 3. storage UI
            if self.storage_ui.is_open:
                self.storage_ui.handle_event(ev, self.player)
                continue

            # 4. Shop UI (receives all events — UP/DOWN/ENTER/ESC)
            if self.shop_ui.open:
                self.shop_ui.handle_event(ev, self.player)
                continue

            # 5. Portal UI
            if self.portal_ui.open:
                result = self.portal_ui.handle_event(ev)
                if result:
                    self.next_scene = ("dungeon", result)
                continue

            # 6. Regular key events
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.pause_ui.toggle()
                    continue

                if ev.key == pygame.K_e:
                    self._interact()


        # ── screen fade-in ────────────────────────────────────────────────────
        if self._screen_fade_alpha > 0:
            self._screen_fade_alpha = max(0.0, self._screen_fade_alpha - (255.0 / self._screen_fade_dur) * dt)

        # ── music volume — always runs so pause can't override it ───────────────
        self._update_music_fade(dt)

        # ── zaustavi svet med pavzo ───────────────────────────────────────────
        if self.pause_ui.phase != 'closed':
            return

        # ── animacije (tečejo tudi če so drugi meniji odprti) ─────────────────
        self.shop_ui.update(dt)
        self.storage_ui.update(dt, self.player)
        self.dialog.update(dt)
        self._update_beat_state()
        self.beat_flash *= math.exp(-2.2 * dt)
        self.smooth_beat = _smooth(self.smooth_beat, self.beat_flash, 5., dt)
        self._update_now_playing(dt)

        if (self.shop_ui.open or self.portal_ui.open
                or self.storage_ui.is_open or self.dialog.is_open):
            return

        #smooth kamera 2.0 test
        cam = (int(self.cam_x), int(self.cam_y))
        self.player.update(dt, keys, mpos, (False, False, False), self.walls, [], cam)

        tw, th = LOBBY_W * TILE, LOBBY_H * TILE
        tx = max(0, min(self.player.x - WIDTH  // 2, tw - WIDTH))
        ty = max(0, min(self.player.y - GAME_H // 2, th - GAME_H))
        self.cam_x += (tx - self.cam_x) * min(1.0, CAM_SMOOTH * dt)
        self.cam_y += (ty - self.cam_y) * min(1.0, CAM_SMOOTH * dt)

    def _interact(self):
        r = _INTERACT_RANGE
        pr = pygame.Rect(int(self.player.x) - r, int(self.player.y) - r, r * 2, r * 2)
        if pr.colliderect(self.teleporter_rect):
            self.portal_ui.show()
        elif pr.colliderect(self.shop_rect):
            self.dialog.show('shop', _SHOP_TEXT)
        elif pr.colliderect(self.storage_rect):
            self.dialog.show('storage', _STORAGE_TEXT)

    #Lobby glasba fade in
    def _start_lobby_music(self):
        self.music_start_t = None
        if os.path.exists(BENEATH_PATH):
            try:
                pygame.mixer.music.load(BENEATH_PATH)
                pygame.mixer.music.set_volume(0.0)
                pygame.mixer.music.play(-1)
                self.music_start_t = time.time()
            except Exception as e:
                print(f"Lobby music error: {e}")

    def _update_music_fade(self, dt):
        sett = getattr(self.pause_ui, '_sett', None)
        scale = sett.vol_music if sett else 1.0
        effective_tgt = self._music_vol_tgt * scale

        self._music_fade_t += dt
        t = min(1.0, self._music_fade_t / self._music_fade_dur)
        self._music_vol = effective_tgt * (t * t) if t < 1.0 else effective_tgt
        pygame.mixer.music.set_volume(self._music_vol)

    #zazna beat-e glasbe v ozadju (threading da ne zamrzne igre)
    def _load_beats(self):
        if not os.path.exists(BENEATH_PATH):
            self.beats_ready = True
            return
        try:
            self.beat_times = _detect_beats(BENEATH_PATH)
        except Exception as e:
            print(f"Beat detection error: {e}")
            self.beat_times = []
        self.beats_ready = True

    BENEATH_DURATION = 293.0

    def _update_beat_state(self):
        if not (self.music_start_t and self.beats_ready and self.beat_times):
            return
        elapsed = (time.time() - self.music_start_t) % self.BENEATH_DURATION
        while self.beat_idx < len(self.beat_times) and self.beat_times[self.beat_idx][0] < elapsed - 0.05:
            self.beat_idx += 1
        if self.beat_idx >= len(self.beat_times):
            self.beat_idx = 0
        if self.beat_idx < len(self.beat_times) and abs(elapsed - self.beat_times[self.beat_idx][0]) < 0.06:
            _, bs = self.beat_times[self.beat_idx]
            self.beat_flash = bs
            self.beat_idx += 1

    def _update_now_playing(self, dt):
        if self.beats_ready and self.beat_times:
            bass = max(0.15, self.smooth_beat)
        else:
            self.now_playing_t += dt * 2.4
            bass = 0.24 + 0.12 * abs(math.sin(self.now_playing_t * 2.9))

        targets = [bass*0.9, bass*0.65, bass, bass*0.75, bass*0.55, bass*0.8]
        for i, tgt in enumerate(targets):
            self.eq_heights[i] = _smooth(self.eq_heights[i], tgt*28+5, 12., dt)

    #ustvari NowPlaying panel
    def _draw_now_playing(self, screen):
        canvas_w, canvas_h = 250, 60
        canvas = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
        if self.ui_alpha == 0:
            return

        base_x, base_y = 28, HEIGHT - 62
        panel_rect = pygame.Rect(0, 0, 240, 55)
        pygame.draw.rect(canvas, (6, 6, 10, int(self.ui_alpha * 0.9)), panel_rect, border_radius=12)
        pygame.draw.rect(canvas, (255, 255, 255, int(self.ui_alpha * 0.3)), panel_rect, 1, border_radius=12)

        for i, h in enumerate(self.eq_heights):
            bh = int(h * 0.8)
            pygame.draw.rect(canvas, (180, 205, 230, int(self.ui_alpha)),
                             (15 + i*7, 38 - bh, 5, bh), border_radius=2)

        def draw_alpha_text(surf, text, fnt, color, pos, alpha):
            if not text: return
            t_surf = fnt.render(text, True, color)
            t_surf.set_alpha(alpha)
            surf.blit(t_surf, pos)

        text_x_offset = 70
        draw_alpha_text(canvas, "ZDAJ IGRA",        self.font_small, (160, 160, 175), (text_x_offset,  8), self.ui_alpha)
        draw_alpha_text(canvas, "Beneath the mask", self.font_np,    (235, 235, 255), (text_x_offset, 22), self.ui_alpha)
        draw_alpha_text(canvas, "Persona 5",        self.font_small, (140, 140, 160), (text_x_offset, 38), self.ui_alpha)

        if self.ui_scale < 1.0:
            new_w = int(canvas_w * self.ui_scale)
            new_h = int(canvas_h * self.ui_scale)
            canvas = pygame.transform.smoothscale(canvas, (new_w, new_h))
            off_x  = (canvas_w - new_w) // 2
            off_y  = (canvas_h - new_h) // 2
            final_pos = (base_x + off_x, base_y + off_y)
        else:
            final_pos = (base_x, base_y)

        screen.blit(canvas, final_pos)

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self, screen):
        screen.fill((14, 11, 22))
        off = (int(self.cam_x), int(self.cam_y))
        ox, oy = off

        self.world.draw(screen, off)
        self._draw_portal_glow(screen, off)
        self.player.draw(screen, off)

        bg_surf = self.world.get_surface()
        for rect in _FOREGROUND_RECTS:
            sx2 = rect.x - ox
            sy2 = rect.y - oy
            if sx2 < WIDTH and sy2 < GAME_H and sx2 + rect.w > 0 and sy2 + rect.h > 0:
                screen.blit(bg_surf, (sx2, sy2), rect)

        # Interaction prompts (farther range)
        r = _INTERACT_RANGE
        pr = pygame.Rect(int(self.player.x) - r, int(self.player.y) - r, r * 2, r * 2)
        if not (self.dialog.is_open or self.shop_ui.open or self.storage_ui.is_open):
            if pr.colliderect(self.teleporter_rect) and not self.portal_ui.open:
                self._draw_prompt(screen, "[ E ]  Dungeon",    WIDTH // 2, GAME_H - 48)
            elif pr.colliderect(self.shop_rect):
                self._draw_prompt(screen, "[ E ]  Open Shop",  WIDTH // 2, GAME_H - 48)
            elif pr.colliderect(self.storage_rect):
                self._draw_prompt(screen, "[ E ]  Open Storage",     WIDTH // 2, GAME_H - 48)

        self.shop_ui.draw(screen, self.player)
        self.storage_ui.draw(screen, self.player)
        self.portal_ui.draw(screen)
        self.dialog.draw(screen)
        self.pause_ui.draw(screen)          # pause + inventory znotraj (on top)
        self._draw_now_playing(screen)

        draw_text(screen, "LOBBY — Varna cona", WIDTH // 2, 10, 15,
                  (120, 110, 150), center=True)
        s = font(12).render("[Esc] Menu", True, GRAY)
        screen.blit(s, (WIDTH - s.get_width() - 10, 10))

        if self._screen_fade_alpha > 0:
            fade_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, int(self._screen_fade_alpha)))
            screen.blit(fade_surf, (0, 0))

    #og portal
    def _draw_portal_glow(self, screen, off):
        ox, oy = off
        r  = self.teleporter_rect
        cx = r.x - ox + TILE
        cy = r.y - oy + TILE
        t  = pygame.time.get_ticks() / 1000.0
        _pb = (55, 172, 255)
        for ring in range(3):
            pulse = abs(math.sin(t * 2.8 + ring * 0.8))
            rad   = 18 + ring * 9 + int(pulse * 5)
            gs    = pygame.Surface((rad*2, rad*2), pygame.SRCALPHA)
            alpha = int(45 - ring*10 + pulse*15)
            pygame.draw.circle(gs, (*_pb, alpha), (rad, rad), rad)
            screen.blit(gs, (cx - rad, cy - rad))

    def _draw_prompt(self, screen, text, x, y):
        s  = font(16, True).render(text, True, YELLOW)
        bg = pygame.Surface((s.get_width() + 20, s.get_height() + 8), pygame.SRCALPHA)
        bg.fill((20, 14, 32, 200))
        screen.blit(bg, (x - s.get_width() // 2 - 10, y - 4))
        screen.blit(s,  (x - s.get_width() // 2, y))
