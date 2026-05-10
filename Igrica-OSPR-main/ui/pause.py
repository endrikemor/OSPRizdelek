"""
Pause menu – Persona-style dark frosted-glass shards.
"""
import pygame, pygame.gfxdraw, math, os
from settings import WIDTH, HEIGHT
from ui.inventory import InventoryUI

def _l(a, b, t):         return a + (b - a) * t
def _oc(t):              t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def _ob(t):
    t = max(0., min(1., t)); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def _ic(t):              t = max(0., min(1., t)); return t * t * t
def _oe(t):              return 0. if t == 0 else 1 - 2 ** (-10 * max(0., min(1., t)))
def _sm(c, tgt, s, dt):  return c + (tgt - c) * (1. - math.exp(-s * dt))
def _ci(v):              return max(0, min(255, int(v)))

_FPC = {}
def _fnt(sz, bold=False):
    k = (sz, bold)
    if k not in _FPC:
        for n in ("Nunito", "Segoe UI", "Verdana", None):
            try: _FPC[k] = pygame.font.SysFont(n, sz, bold=bold); break
            except: pass
    return _FPC[k]

def _bpoly(dst, pts, col):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox, oy = int(min(xs)), int(min(ys))
    w = max(1, int(max(xs)) - ox + 2)
    h = max(1, int(max(ys)) - oy + 2)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(s, col, [(int(p[0]) - ox, int(p[1]) - oy) for p in pts])
    dst.blit(s, (ox, oy))

def _bpoly_border(dst, pts, col, thick=2):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ox, oy = int(min(xs)) - thick, int(min(ys)) - thick
    w = max(1, int(max(xs)) - int(min(xs)) + thick * 4)
    h = max(1, int(max(ys)) - int(min(ys)) + thick * 4)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.polygon(s, col, [(int(p[0]) - ox, int(p[1]) - oy) for p in pts], thick)
    dst.blit(s, (ox, oy))

def _bline(dst, col, p1, p2, thick=2):
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(s, col, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), thick)
    dst.blit(s, (0, 0))


class PauseUI:
    ITEMS = [
        ("continue",  "CONTINUE"),
        ("inventory", "INVENTORY"),
        ("settings",  "SETTINGS"),
        ("mainmenu",  "MAIN MENU"),
        ("quit",      "EXIT"),
    ]
    N = len(ITEMS)

    _S1_X0, _S1_X1 = 0.048, 0.390
    _S1_Y0, _S1_Y1 = 0.062, 0.938
    _S1_SK          = 0.028

    _SC_X0, _SC_X1 = -0.005, 0.175
    _SC_SK          = 0.014

    _S2_X0, _S2_X1 = 0.405, 0.595
    _S2_Y0, _S2_Y1 = 0.055, 0.475
    _S2_SK          = 0.020

    _IN_DUR   = 0.50
    _OUT_DUR  = 0.36
    _STAG     = 0.062
    _IDUR     = 0.28
    _HS       = 11.
    _COMP_SPD = 9.

    _SHARD_BG  = (11, 11, 21, 145)
    _SHARD_BG2 = (9,   9, 18, 110)
    _BORDER    = (255, 255, 255,  58)
    _TOP_LINE  = (255, 255, 255, 160)
    _SEL_BG    = (255, 255, 255, 242)
    _SEL_TXT   = (8,   8,  20)
    _HOV_BG    = (255, 255, 255,  52)
    _HINT_COL  = (65,  68,  90)

    def __init__(self):
        self.phase         = 'closed'
        self.open          = False
        self.sel           = 0
        self._ft           = 0.
        self._it           = [0.] * self.N
        self._hv           = [0.] * self.N
        self._hs           = [1.] * self.N
        self._ot           = 0.
        self.settings_open = False
        self._last_ms      = 0
        self._prev_hov     = -1

        self._comp         = 0.
        self._comp_tgt     = 0.

        self.inv_ui        = InventoryUI()
        self.inv_ui.on_close_cb = self._on_inv_closed

        self._hover_ch     = pygame.mixer.Channel(5)
        self._select_ch    = pygame.mixer.Channel(6)
        self._sfx_hover    = self._load_sfx("hover")
        self._sfx_select   = self._load_sfx("select")

        self._scene_ref    = None
        self._sett         = None

    def _load_sfx(self, kind):
        try:
            from settings import HOVER_SFX_PATH, SELECT_SFX_PATH
            path = HOVER_SFX_PATH if kind == "hover" else SELECT_SFX_PATH
            if os.path.exists(path):
                return pygame.mixer.Sound(path)
        except Exception:
            pass
        return None

    def _play_sfx(self, ch, snd, vol=0.5):
        if not snd:
            return
        v = vol * (self._sett.vol_sfx if self._sett else 1.0)
        snd.set_volume(max(0., min(1., v)))
        ch.stop()
        ch.play(snd)

    def _bind_scene(self, scene):
        if self._scene_ref is scene:
            return
        self._scene_ref = scene
        if hasattr(scene, 'main_screen') and scene.main_screen is not None:
            self._sett = scene.main_screen.settings
        elif hasattr(scene, '_sett') and scene._sett is not None:
            self._sett = scene._sett
        else:
            try:
                from scenes.main_screen import SettingsPanel
                self._sett = SettingsPanel(0.7, 0.5, 0.5, 0.5, 0.5, 1)
            except Exception:
                self._sett = None

    # ── inventory callbacks ───────────────────────────────────────────────────
    def _on_inv_closed(self):
        self._comp_tgt = 0.

    def _close_settings_now(self):
        """Zapre settings s pravilno toggle animacijo."""
        if self._sett and self._sett.open:
            self._sett.toggle(self._sett.anchor_x, self._sett.anchor_y)
        self.settings_open = False

    def _open_inventory(self):
        self._close_settings_now()   # medsebojno izključevanje
        self._comp_tgt = 1.
        self.inv_ui.open_inv()

    # ── geometry ──────────────────────────────────────────────────────────────
    def _s1pts(self, yo=0):
        c    = self._comp
        x0   = _l(WIDTH * self._S1_X0, WIDTH * self._SC_X0, c)
        x1   = _l(WIDTH * self._S1_X1, WIDTH * self._SC_X1, c)
        sk   = _l(WIDTH * self._S1_SK, WIDTH * self._SC_SK, c)
        x0, x1, sk = int(x0), int(x1), int(sk)
        y0   = int(HEIGHT * self._S1_Y0) + yo
        y1   = int(HEIGHT * self._S1_Y1) + yo
        return [(x0 + sk, y0), (x1 + sk, y0), (x1, y1), (x0, y1)]

    def _s2pts(self, yo=0):
        sk  = int(WIDTH * self._S2_SK)
        x0  = int(WIDTH * self._S2_X0)
        x1  = int(WIDTH * self._S2_X1)
        y0  = int(HEIGHT * self._S2_Y0) + yo
        y1  = int(HEIGHT * self._S2_Y1) + yo
        notch = int(HEIGHT * 0.022)
        return [(x0 + sk, y0), (x1, y0 - notch), (x1 - sk // 2, y1), (x0, y1)]

    def _ibnd(self, idx):
        c    = self._comp
        x0_n = int(WIDTH * self._S1_X0) + int(WIDTH * self._S1_SK)
        x1_n = int(WIDTH * self._S1_X1)
        x0_c = int(WIDTH * self._SC_X0) + int(WIDTH * self._SC_SK)
        x1_c = int(WIDTH * self._SC_X1)
        x0   = int(_l(x0_n, x0_c, c))
        x1   = int(_l(x1_n, x1_c, c))
        y0   = int(HEIGHT * self._S1_Y0)
        pad  = int(HEIGHT * 0.040)
        avail = int(HEIGHT * (self._S1_Y1 - self._S1_Y0)) - pad * 2
        ih   = min(avail // self.N, int(HEIGHT * 0.135))
        blk  = ih * self.N
        sy   = y0 + pad + (avail - blk) // 2
        return x0, sy + idx * ih, x1 - x0, ih

    def _hit(self, mx, my):
        if self.inv_ui.is_open:
            return -1
        for i in range(self.N):
            x, y, w, h = self._ibnd(i)
            if x <= mx <= x + w and y <= my <= y + h:
                return i
        return -1

    # ── public API ────────────────────────────────────────────────────────────
    def toggle(self):
        if self.phase == 'closed':
            self.open  = True
            self.phase = 'opening'
            self._ft   = 0.
            self._ot   = 0.
            self.sel   = 0
            self._it   = [0.] * self.N
            self.settings_open = False
        else:
            self._bclose()

    def close(self):
        self._bclose()

    def _bclose(self):
        if self.phase in ('opening', 'open'):
            self.phase = 'closing'
            self._ft   = 0.
            self._close_settings_now()
            if self.inv_ui.is_open:
                self.inv_ui.close_inv()
                self._comp_tgt = 0.

    def _auto_dt(self):
        now = pygame.time.get_ticks()
        dt  = min((now - self._last_ms) / 1000., 0.05) if self._last_ms else 0.016
        self._last_ms = now
        return dt

    # ── update ────────────────────────────────────────────────────────────────
    def update(self, dt):
        self._last_ms = pygame.time.get_ticks()
        if self.phase == 'closed':
            return

        self._comp = _sm(self._comp, self._comp_tgt, self._COMP_SPD, dt)

        mx, my = pygame.mouse.get_pos()

        if self.phase == 'opening':
            self._ft = min(1., self._ft + dt / self._IN_DUR)
            if self._ft >= 1.:
                self.phase = 'open'
                self._ft   = 1.
                self._ot   = 0.

        elif self.phase == 'open':
            self._ot += dt
            for i in range(self.N):
                tgt = min(1., max(0., self._ot - i * self._STAG) / self._IDUR)
                self._it[i] = _sm(self._it[i], tgt, 10., dt)

            hov = self._hit(mx, my)
            if hov != self._prev_hov and hov != -1:
                self._play_sfx(self._hover_ch, self._sfx_hover, 0.5)
            self._prev_hov = hov

            for i in range(self.N):
                is_h = (i == hov)
                self._hv[i] = _sm(self._hv[i], 1. if is_h else 0., self._HS, dt)
                self._hs[i] = _sm(self._hs[i], 1.07 if is_h else 1., self._HS, dt)

            if self._sett:
                self._sett.zazeni(dt)
                if not self._sett.open and self._sett.t < 0.02:
                    self.settings_open = False

        elif self.phase == 'closing':
            self._ft = min(1., self._ft + dt / self._OUT_DUR)
            for i in range(self.N):
                self._it[i] = _sm(self._it[i], 0., 16., dt)
                self._hv[i] = _sm(self._hv[i], 0., 16., dt)
            if self._ft >= 1.:
                self.phase = 'closed'
                self.open  = False
                self._ot   = 0.

        self.inv_ui.update(dt, getattr(self._scene_ref, 'player', None)
                              if self._scene_ref else None)

    # ── events ────────────────────────────────────────────────────────────────
    def handle_event(self, ev, scene) -> bool:
        self._bind_scene(scene)
        if self.phase == 'closed':
            return False

        # inventory dobi prioriteto
        if self.inv_ui.is_open:
            player = getattr(scene, 'player', None)
            return self.inv_ui.handle_event(ev, player)

        # ── settings panel ────────────────────────────────────────────────────
        if self.settings_open and self._sett:
            mx, my = pygame.mouse.get_pos()

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                hi = self._hit(mx, my)
                if hi >= 0:
                    if self.ITEMS[hi][0] == "settings":
                        # Klik na SETTINGS gumb → zapri settings
                        self._close_settings_now()
                    else:
                        # Klik na drug gumb → zapri settings + izvedi akcijo
                        self._close_settings_now()
                        self.sel = hi
                        self._act(scene)
                    return True

            # posreduj event settings panelu (drag sliderjev itd.)
            self._sett.event_handler(ev, mx, my)

            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._close_settings_now()
                return True

            return True

        # ── pause keyboard ────────────────────────────────────────────────────
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._bclose(); return True
            if ev.key == pygame.K_UP:
                self.sel = (self.sel - 1) % self.N; return True
            if ev.key == pygame.K_DOWN:
                self.sel = (self.sel + 1) % self.N; return True
            if ev.key in (pygame.K_RETURN, pygame.K_e):
                return self._act(scene)

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.phase == 'open':
                mx, my = pygame.mouse.get_pos()
                hi = self._hit(mx, my)
                if hi >= 0:
                    self.sel = hi
                    return self._act(scene)

        return True

    def _act(self, scene) -> bool:
        self._play_sfx(self._select_ch, self._sfx_select, 0.6)
        k = self.ITEMS[self.sel][0]

        if k == "continue":
            self._bclose()

        elif k == "inventory":
            self._open_inventory()

        elif k == "settings" and self._sett:
            # zapri inventory, če je odprt
            if self.inv_ui.is_open:
                self.inv_ui.close_inv()
                self._comp_tgt = 0.

            if self._sett.open:
                # Settings je odprt → zapri ga
                self._close_settings_now()
            else:
                # Settings je zaprt → odpri ga na dinamičnem px
                x1_cur = int(_l(WIDTH * self._S1_X1, WIDTH * self._SC_X1, self._comp))
                px = x1_cur + 18
                total_h = (len(self._sett.vrstice()) * self._sett.ITEM_H
                           + self._sett.PAD_TOP * 2)
                py = max(20, HEIGHT // 2 - total_h // 2)
                self._sett.toggle(px, py)
                self.settings_open = self._sett.open

        elif k == "mainmenu":
            scene.next_scene = "mainmenu"; self._bclose()

        elif k == "quit":
            scene.next_scene = "quit";     self._bclose()

        return True

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, screen):
        if self.phase == 'closed':
            return
        if pygame.time.get_ticks() - self._last_ms > 4:
            self.update(self._auto_dt())

        if self.phase == 'opening':
            ep1  = _ob(self._ft)
            yo1  = int(_l(-(HEIGHT + 100), 0, ep1))
            ft2  = min(1., max(0., (self._ft - 0.08) / 0.92))
            yo2  = int(_l(-(HEIGHT + 100), 0, _ob(ft2)))
            ova  = int(188 * self._ft)
        elif self.phase == 'open':
            yo1  = yo2 = 0
            ova  = 188
        else:
            ep_out = _ic(self._ft)
            yo1  = int(_l(0,  HEIGHT + 100, ep_out))
            yo2  = int(_l(0,  HEIGHT + 100, _ic(min(1., self._ft * 1.20))))
            ova  = int(188 * (1. - self._ft))

        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((5, 5, 12, _ci(int(ova * 0.65))))
        screen.blit(ov, (0, 0))

        s2_vis = max(0., 1. - self._comp * 2.)
        if s2_vis > 0.01:
            vis2 = s2_vis * (1.0 if self.phase == 'open' else (
                min(1., (self._ft - 0.08) / 0.92) if self.phase == 'opening'
                else max(0., 1. - self._ft * 1.3)))
            if vis2 > 0.01:
                p2 = self._s2pts(yo2)
                a2 = int(110 * vis2)
                _bpoly(screen, p2, (self._SHARD_BG2[0], self._SHARD_BG2[1],
                                    self._SHARD_BG2[2], a2))
                _bpoly_border(screen, p2, (255, 255, 255, int(45 * vis2)), 2)
                _bline(screen, (255, 255, 255, int(90 * vis2)), p2[0], p2[1], 3)

        p1 = self._s1pts(yo1)
        _bpoly(screen, p1, self._SHARD_BG)

        xs = [p[0] for p in p1]; ys = [p[1] for p in p1]
        bw = max(1, int(max(xs)) - int(min(xs)))
        bh = max(1, int(max(ys)) - int(min(ys)))
        if bw > 1 and bh > 1:
            hl_h = max(4, bh // 8)
            _bpoly(screen, [
                (p1[0][0], p1[0][1]),
                (p1[1][0], p1[1][1]),
                (p1[1][0], p1[1][1] + hl_h),
                (p1[0][0], p1[0][1] + hl_h),
            ], (255, 255, 255, 14))

        _bpoly_border(screen, p1, self._BORDER, 2)
        _bline(screen, self._TOP_LINE, p1[0], p1[1], 3)

        if self._comp > 0.35:
            lbl_a = _ci(int(255 * min(1., (self._comp - 0.35) / 0.40)))
            lbl_s = _fnt(max(9, int(HEIGHT * 0.022)), bold=True).render(
                "PAUSE", True, (200, 200, 230))
            lbl_s.set_alpha(lbl_a)
            lbl_x = p1[0][0] + (p1[1][0] - p1[0][0]) // 2 - lbl_s.get_width() // 2
            lbl_y = int(HEIGHT * 0.5) - lbl_s.get_height() // 2
            screen.blit(lbl_s, (lbl_x + yo1 // 10, lbl_y))

        item_alpha_mul = max(0., 1. - self._comp * 3.)

        if item_alpha_mul > 0.01:
            for i, (_, label) in enumerate(self.ITEMS):
                it = self._it[i]
                if it < 0.004:
                    continue

                ix, iy, iw, ih = self._ibnd(i)
                iy += yo1

                ep    = _ob(it)
                slide = int(_l(-130, 0, _oc(it)))
                hg    = self._hv[i]
                sc    = self._hs[i]
                is_sel = (i == self.sel)

                dh = int(ih * sc)
                dw = int(iw * sc)
                dx = ix + slide
                dy = iy - (dh - ih) // 2

                bg = pygame.Surface((dw, dh), pygame.SRCALPHA)
                if is_sel:
                    bg.fill((self._SEL_BG[0], self._SEL_BG[1], self._SEL_BG[2],
                              _ci(self._SEL_BG[3] * ep * item_alpha_mul)))
                elif hg > 0.03:
                    bg.fill((255, 255, 255, _ci(hg * 52 * item_alpha_mul)))
                screen.blit(bg, (dx, dy))

                fsize = max(10, int(dh * 0.38))
                if is_sel:
                    tc = self._SEL_TXT
                else:
                    bri = int(_l(108, 248, hg))
                    tc  = (bri, bri, int(_l(125, 255, hg)))

                txt = _fnt(fsize, bold=True).render(label, True, tc)
                txt.set_alpha(int(min(255, ep * item_alpha_mul * 255)))
                tx = dx + int(dh * 0.22)
                ty = dy + dh // 2 - txt.get_height() // 2
                screen.blit(txt, (tx, ty))

                if is_sel and ep > 0.05:
                    bar_w = max(1, int(dh * 0.050))
                    bar   = pygame.Surface((bar_w, dh), pygame.SRCALPHA)
                    bar.fill((8, 8, 20, _ci(200 * ep * item_alpha_mul)))
                    screen.blit(bar, (dx, dy))

                if hg > 0.05 and not is_sel:
                    gl = pygame.Surface((3, dh), pygame.SRCALPHA)
                    for row in range(dh):
                        t  = row / max(dh - 1, 1)
                        ga = int(math.sin(t * math.pi) * hg * 120 * item_alpha_mul)
                        if ga > 0:
                            gl.set_at((0, row), (255, 255, 255, ga))
                            gl.set_at((1, row), (255, 255, 255, ga // 2))
                    screen.blit(gl, (dx + dw - 3, dy))

        # settings – ne izrisuj čez inventory
        if (self._sett and self.settings_open and self._sett.t > 0.01
                and not self.inv_ui.is_open):
            self._sett.settings_UI(screen, *pygame.mouse.get_pos())

        if (self.phase == 'open' and self._ot > 0.55
                and not self.inv_ui.is_open and item_alpha_mul > 0.5):
            sk  = int(WIDTH * self._S1_SK)
            hx  = int(WIDTH * self._S1_X0) + sk + 18
            hy  = int(HEIGHT * self._S1_Y1) + yo1 - 34
            htxt = _fnt(14).render("[ ESC ]  Close", True, self._HINT_COL)
            htxt.set_alpha(int(min(108, (self._ot - 0.55) * 200) * item_alpha_mul))
            screen.blit(htxt, (hx, hy))

        # inventory izrišemo ZADNJI (na vrhu vsega)
        if self.inv_ui.is_open:
            player = getattr(self._scene_ref, 'player', None)
            self.inv_ui.draw(screen, player)