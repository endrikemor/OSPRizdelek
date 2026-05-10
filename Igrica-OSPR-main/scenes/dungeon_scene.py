"""DungeonScene — extracted from scenes.py"""
import pygame
from settings import *
from entities import Player, FloatingText, PlayerProjectile
from world import Dungeon
from world.room import RT_BOSS, RT_SHOP, RT_START
from ui import HUD, ShopUI, PauseUI
from ui.helpers import draw_text, font
from ui.helpers import add_to_inv

class DungeonScene:
    def __init__(self, player: Player, difficulty="Medium", settings=None):
        self.player     = player
        self.difficulty = difficulty
        self.dungeon    = Dungeon(difficulty, player.cls)
        self.player.x   = (ROOM_W // 2) * TILE + TILE // 2
        self.player.y   = (ROOM_H // 2) * TILE + TILE // 2
        self.player.hp  = float(self.player.max_hp)
        self.player.stamina    = float(self.player.max_stamina)
        self.player.atk_timer  = 99.0
        self.player.dashing    = False
        self.player.dash_cd    = 0.0
        self.player.floats     = []
        self.player.alive      = True
        self.player.pending_projectiles = []

        self.cam_x = 0.0; self.cam_y = 0.0
        self._sett    = settings
        self.hud      = HUD()
        self.pause_ui = PauseUI()          #inventory v pauseUI
        self.pause_ui._sett = settings     #settings za volume v pause menuju
        self.shop_ui  = ShopUI()

        self._transition  = False
        self._trans_dir   = 0
        self._trans_timer = 0.0
        self._trans_dur   = 0.40
        self._room_msg    = ""
        self._room_msg_t  = 0.0
        self.next_scene   = None
        self.won          = False
        self._projectiles = []
        self._win_timer   = 0.0
        self._xp_given    = set()

        try:
            pygame.mixer.music.load(DUNGEON_MUSIC_PATH)
            pygame.mixer.music.set_volume(0.35 * (settings.vol_music if settings else 1.0))
            pygame.mixer.music.play(-1)
        except Exception:
            pass

        self._show_banner()

    #pomozne metode oz dostop do UI komponent v pause menu
    @property
    def inv_ui(self):
        """Backwards-compat: inventory lives inside pause_ui."""
        return self.pause_ui.inv_ui

    @property
    def room(self): return self.dungeon.room

    def _walls(self): return self.room.get_walls()

    def _show_banner(self):
        labels = {
            "normal":   f"Stage {self.room.stage}  –  Clear the room!",
            "boss":     "  BOSS STAGE  ",
            "shop":     "Merchant's Den  [E] shop",
            "treasure": "Treasure Room!",
            "start":    "Dungeon Entrance",
        }
        self._room_msg   = labels.get(self.room.rtype, "")
        self._room_msg_t = 3.0

    def update(self, dt, events):
        if self._sett:
            pygame.mixer.music.set_volume(0.35 * self._sett.vol_music)

        if self._transition:
            self._do_transition(dt)
            return

        keys  = pygame.key.get_pressed()
        mpos  = pygame.mouse.get_pos()
        mbtns = pygame.mouse.get_pressed()

        #update pause_ui (vkljucno z inv_ui znotraj)
        self.pause_ui.update(dt)

        for ev in events:
            # pause dobi prednost (vključno z inventory znotraj)
            if self.pause_ui.phase != 'closed':
                self.pause_ui.handle_event(ev, self)
                continue

            if self.shop_ui.open:
                self.shop_ui.handle_event(ev, self.player)
                continue

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.pause_ui.toggle()          # ESC odpre pavzo (ne takoj lobby)
                    continue


                if ev.key == pygame.K_e:
                    self._try_interact()

                for i, k in enumerate([pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]):
                    if ev.key == k:
                        cam = (int(self.cam_x), int(self.cam_y))
                        self.player.use_skill(i, self.room.enemies, mpos, cam, self._walls())

        # ── zaustavi svet med pavzo ───────────────────────────────────────────
        if self.pause_ui.phase != 'closed':
            return

        if self.shop_ui.open:
            self.shop_ui.update(dt)
            return

        walls = self._walls()
        cam   = (int(self.cam_x), int(self.cam_y))
        self.player.update(dt, keys, mpos, mbtns, walls, self.room.enemies, cam) #premakni playerja, preveri napade, interakcije, ...
        if keys[pygame.K_LSHIFT] and not self.player.dashing:#shift za dash
            self.player.start_dash(keys)
        if not self.player.alive:
            self.next_scene = "lobby"
            return

        for pp in self.player.pending_projectiles:
            self._projectiles.append(pp)
        self.player.pending_projectiles.clear()
        for pp in self._projectiles:
            pp.update(dt, walls, self.room.enemies)
        self._projectiles = [pp for pp in self._projectiles if pp.alive]

        self.room.update(dt, self.player, walls)
        cleared = self.room.check_cleared()

        for e in self.room.enemies:
            eid = id(e)
            if not e.alive and eid not in self._xp_given:
                self._xp_given.add(eid)
                self.player.gain_xp(e.xp_value)
                gold = int(e.gold_value * DIFFICULTY[self.difficulty]["gold_m"])
                self.player.gold += gold

        if self.room.rtype == RT_BOSS and cleared and not self.won:
            self.won = True
            self.player.gain_xp(200 + self.room.stage * 20)
            gold_r = int(80 * DIFFICULTY[self.difficulty]["gold_m"])
            self.player.gold += gold_r
            self.player.floats.append(
                FloatingText(self.player.x, self.player.y - 80,
                             f"+{gold_r} GOLD!", GOLD, 26, 3.0))
            self._room_msg   = "BOSS DEFEATED!  YOU WIN!"
            self._room_msg_t = 4.0 #parametr za prikaz sporočila ob zmagi
            self._win_timer  = 4.5#parametr za čas do prehoda v lobby po zmagi

        if self.won:
            self._win_timer -= dt
            if self._win_timer <= 0:
                self.next_scene = "lobby"
            return
        #pobiranje itemov
        self._check_item_pickups()
        self._check_door_transitions()
        #premik kamere (smoothing)
        tw = ROOM_W * TILE; th = ROOM_H * TILE
        tx = max(0, min(self.player.x - WIDTH // 2, tw - WIDTH))
        ty = max(0, min(self.player.y - GAME_H // 2, th - GAME_H))
        self.cam_x += (tx - self.cam_x) * min(1.0, CAM_SMOOTH * dt)
        self.cam_y += (ty - self.cam_y) * min(1.0, CAM_SMOOTH * dt)
        self.shop_ui.update(dt)
        if self._room_msg_t > 0:
            self._room_msg_t = max(0.0, self._room_msg_t - dt)

    def _try_interact(self):
        if self.room.rtype == RT_SHOP and self.room.shop_stock:
            self.shop_ui.show(self.room.shop_stock, "DUNGEON MERCHANT")

    def _check_item_pickups(self):
        pr = pygame.Rect(int(self.player.x) - 22, int(self.player.y) - 22, 44, 44)
        for itm in self.room.items:
            if itm.picked: continue
            if pr.colliderect(itm.get_rect()):
                itm.picked = True
                if itm.itype == "gold_coin":
                    itm.use(self.player)
                else:
                    add_to_inv(self.player, itm)

    def _check_door_transitions(self): #ali si sel cez vrata
        px, py2 = self.player.x, self.player.y
        mid = (ROOM_W // 2) * TILE
        if (self.room.doors.get("N") and self.room.cleared
                and py2 < TILE * 0.6 and mid - TILE < px < mid + TILE * 2):
            self._start_transition(-1)
        if (self.room.doors.get("S") and self.room.cleared
                and py2 > (ROOM_H - 1) * TILE + TILE * 0.4
                and mid - TILE < px < mid + TILE * 2):
            self._start_transition(+1)

    def _start_transition(self, d):
        self._transition  = True
        self._trans_dir   = d
        self._trans_timer = 0.0

    def _do_transition(self, dt):
        self._trans_timer += dt
        if self._trans_timer < self._trans_dur:
            return
        self._transition = False
        self._projectiles.clear()
        if self._trans_dir == +1:
            if self.dungeon.is_last: return
            self.dungeon.next_room()
            self.player.x = (ROOM_W // 2) * TILE + TILE // 2
            self.player.y = TILE * 1.5
        else:
            self.dungeon.prev_room()
            self.player.x = (ROOM_W // 2) * TILE + TILE // 2
            self.player.y = (ROOM_H - 2) * TILE - TILE // 2
        self.cam_x = 0.0; self.cam_y = 0.0
        self._show_banner()

    def draw(self, screen):
        off = (int(self.cam_x), int(self.cam_y))
        self.room.draw(screen, off)

        # dark ambient overlay
        _amb = pygame.Surface((WIDTH, GAME_H), pygame.SRCALPHA)
        _amb.fill((0, 0, 10, 72))
        screen.blit(_amb, (0, 0))

        for pp in self._projectiles:
            pp.draw(screen, off)
        self.player.draw(screen, off)

        if self._transition:
            a    = int(255 * min(1.0, self._trans_timer / self._trans_dur))
            fade = pygame.Surface((WIDTH, GAME_H), pygame.SRCALPHA)
            fade.fill((0, 0, 0, a))
            screen.blit(fade, (0, 0))

        if self._room_msg_t > 0:
            a   = min(1.0, self._room_msg_t / 0.5) if self._room_msg_t < 0.5 else 1.0
            col = GOLD if self.won else (RED if self.room.rtype == RT_BOSS else YELLOW)
            s   = font(26, True).render(self._room_msg, True, col)
            s.set_alpha(int(255 * a))
            screen.blit(s, (WIDTH // 2 - s.get_width() // 2, 60))

        if self.room.rtype == RT_SHOP and not self.shop_ui.open:
            draw_text(screen, "[ E ]  Talk to Merchant",
                      WIDTH // 2, GAME_H // 2 + 80, 18, GOLD, bold=True, center=True)
        if not self.room.cleared and self.room.rtype in ("normal", "maze"):
            living = sum(1 for e in self.room.enemies if e.alive)
            draw_text(screen, f"Enemies remaining: {living}",
                      WIDTH // 2, 26, 15, ORANGE, center=True)

        self.hud.draw(screen, self.player, stage=self.room.stage,
                      max_stage=self.dungeon.max_stages, room_type=self.room.rtype)
        self.shop_ui.draw(screen, self.player)
        self.pause_ui.draw(screen)          # pause + inventory znotraj
        self._draw_minimap(screen)
        s2 = font(12).render("[Esc] Pause", True, GRAY)
        screen.blit(s2, (WIDTH - s2.get_width() - 10, 10))

    def _draw_minimap(self, screen):
        data = self.dungeon.get_minimap_data()
        n    = len(data)
        sw   = 13; sh = 9; gap = 3
        total_w = n * (sw + gap) - gap
        mx = WIDTH - total_w - 14
        my = GAME_H - 24
        for idx, rtype, visited, current in data:
            rx = mx + idx * (sw + gap)
            if not visited:
                pygame.draw.rect(screen, DARK_GRAY, (rx, my, sw, sh), border_radius=2)
            else:
                col = {"normal": FLOOR_CLR, "boss": RED, "shop": GOLD,
                       "treasure": CYAN, "start": GREEN,
                       "maze": PURPLE}.get(rtype, GRAY)
                pygame.draw.rect(screen, col, (rx, my, sw, sh), border_radius=2)
            if current:
                pygame.draw.rect(screen, WHITE, (rx, my, sw, sh), 2, border_radius=2)