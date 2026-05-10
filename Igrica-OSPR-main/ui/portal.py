"""PortalUI — Persona-style difficulty selection before entering dungeon."""
import pygame, math
from settings import *

def _l(a, b, t):    return a + (b - a) * t
def _oc(t):         t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def _ob(t):
    t = max(0., min(1., t)); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def _ic(t):         t = max(0., min(1., t)); return t * t * t
def _sm(c, tgt, s, dt): return c + (tgt - c) * (1. - math.exp(-s * dt))
def _ci(v):         return max(0, min(255, int(v)))

_FC = {}
def _fnt(sz, bold=False):
    k = (sz, bold)
    if k not in _FC:
        for n in ("Nunito", "Segoe UI", "Verdana", None):
            try: _FC[k] = pygame.font.SysFont(n, sz, bold=bold); break
            except: pass
    return _FC[k]

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


class PortalUI:
    _DIFFS = ["Easy", "Medium", "Hard"]
    _COLS  = [(60, 210, 90), (240, 200, 50), (220, 55, 55)]

    _IN_DUR  = 0.44
    _OUT_DUR = 0.30
    _STAG    = 0.10
    _IDUR    = 0.22
    _HS      = 10.

    _BG     = (11, 11, 21, 148)
    _BORDER = (255, 255, 255, 58)
    _LINE   = (255, 255, 255, 160)

    # Main shard panel (fraction of screen)
    _SX0, _SX1 = 0.10, 0.90
    _SY0, _SY1 = 0.09, 0.91
    _SSK        = 0.028

    def __init__(self):
        self.open      = False
        self.diff_sel  = 1
        self._phase    = 'closed'
        self._ft       = 0.
        self._ot       = 0.
        self._hv       = [0.] * 3
        self._hs       = [1.] * 3
        self._it       = [0.] * 3
        self._enter_hv = 0.
        self._last_ms  = 0
        self._prev_hov = -1

    # ── geometry ──────────────────────────────────────────────────────────────
    def _main_pts(self, yo=0):
        sk = int(WIDTH * self._SSK)
        x0 = int(WIDTH * self._SX0)
        x1 = int(WIDTH * self._SX1)
        y0 = int(HEIGHT * self._SY0) + yo
        y1 = int(HEIGHT * self._SY1) + yo
        return [(x0 + sk, y0), (x1, y0), (x1 - sk, y1), (x0, y1)]

    def _card_rect(self, i):
        cw  = int(WIDTH * 0.175)
        gap = int(WIDTH * 0.022)
        tot = 3 * cw + 2 * gap
        cx0 = WIDTH  // 2 - tot // 2
        cy0 = int(HEIGHT * 0.43)
        ch  = int(HEIGHT * 0.32)
        return pygame.Rect(cx0 + i * (cw + gap), cy0, cw, ch)

    def _card_pts(self, rect, yo=0, scale=1.0):
        sk = 12
        cx = rect.centerx
        cy = rect.centery + yo
        hw = rect.width  / 2 * scale
        hh = rect.height / 2 * scale
        return [
            (int(cx - hw + sk), int(cy - hh)),
            (int(cx + hw),      int(cy - hh)),
            (int(cx + hw - sk), int(cy + hh)),
            (int(cx - hw),      int(cy + hh)),
        ]

    def _enter_rect(self, yo=0):
        ew, eh = 215, 48
        return pygame.Rect(WIDTH // 2 - ew // 2, int(HEIGHT * 0.78) + yo, ew, eh)

    def _enter_pts(self, yo=0, scale=1.0):
        r  = self._enter_rect(yo)
        sk = 14
        cx = r.centerx
        cy = r.centery
        hw = r.width  / 2 * scale
        hh = r.height / 2 * scale
        return [
            (int(cx - hw + sk), int(cy - hh)),
            (int(cx + hw),      int(cy - hh)),
            (int(cx + hw - sk), int(cy + hh)),
            (int(cx - hw),      int(cy + hh)),
        ]

    def _hit_diff(self, mx, my):
        for i in range(3):
            if self._card_rect(i).collidepoint(mx, my):
                return i
        return -1

    def _hit_enter(self, mx, my):
        return self._enter_rect().collidepoint(mx, my)

    # ── public API ────────────────────────────────────────────────────────────
    def show(self):
        self.open      = True
        self._phase    = 'opening'
        self._ft       = 0.
        self._ot       = 0.
        self._it       = [0.] * 3
        self._hv       = [0.] * 3
        self._hs       = [1.] * 3
        self._enter_hv = 0.

    def _do_close(self):
        if self._phase in ('opening', 'open'):
            self._phase = 'closing'
            self._ft    = 0.

    # ── internal tick ─────────────────────────────────────────────────────────
    def _tick(self, dt):
        if self._phase == 'closed':
            return

        if self._phase == 'opening':
            self._ft = min(1., self._ft + dt / self._IN_DUR)
            if self._ft >= 1.:
                self._phase = 'open'
                self._ft    = 1.
                self._ot    = 0.

        elif self._phase == 'open':
            self._ot += dt
            for i in range(3):
                tgt = min(1., max(0., (self._ot - i * self._STAG) / self._IDUR))
                self._it[i] = _sm(self._it[i], tgt, 10., dt)

            mx, my = pygame.mouse.get_pos()
            hov = self._hit_diff(mx, my)
            self._prev_hov = hov
            for i in range(3):
                is_h = (i == hov)
                self._hv[i] = _sm(self._hv[i], 1. if is_h else 0., self._HS, dt)
                self._hs[i] = _sm(self._hs[i], 1.04 if is_h else 1., self._HS, dt)

            eh = 1. if self._hit_enter(mx, my) else 0.
            self._enter_hv = _sm(self._enter_hv, eh, self._HS, dt)

        elif self._phase == 'closing':
            self._ft = min(1., self._ft + dt / self._OUT_DUR)
            for i in range(3):
                self._it[i] = _sm(self._it[i], 0., 16., dt)
                self._hv[i] = _sm(self._hv[i], 0., 16., dt)
            if self._ft >= 1.:
                self._phase = 'closed'
                self.open   = False
                self._ot    = 0.

    # ── events ────────────────────────────────────────────────────────────────
    def handle_event(self, ev):
        if not self.open:
            return None

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._do_close()
                return None
            if ev.key in (pygame.K_LEFT,  pygame.K_a):
                self.diff_sel = max(0, self.diff_sel - 1)
            if ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.diff_sel = min(2, self.diff_sel + 1)
            if ev.key == pygame.K_1: self.diff_sel = 0
            if ev.key == pygame.K_2: self.diff_sel = 1
            if ev.key == pygame.K_3: self.diff_sel = 2
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                r = self._DIFFS[self.diff_sel]
                self._do_close()
                return r

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            hi = self._hit_diff(mx, my)
            if hi >= 0:
                self.diff_sel = hi
                return None
            if self._hit_enter(mx, my):
                r = self._DIFFS[self.diff_sel]
                self._do_close()
                return r

        return None

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, screen):
        if not self.open:
            return

        now = pygame.time.get_ticks()
        dt  = min((now - self._last_ms) / 1000., 0.05) if self._last_ms else 0.016
        self._last_ms = now
        self._tick(dt)

        if self._phase == 'opening':
            ep  = _ob(self._ft)
            yo  = int(_l(-(HEIGHT + 100), 0, ep))
            ova = int(160 * self._ft)
        elif self._phase == 'open':
            yo  = 0
            ova = 160
        else:
            yo  = int(_l(0, -(HEIGHT + 100), _ic(self._ft)))
            ova = int(160 * (1. - self._ft))

        a_frac = ova / 160.

        # Dark overlay
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((5, 5, 12, _ci(ova * 0.65)))
        screen.blit(ov, (0, 0))

        # ── Main shard ────────────────────────────────────────────────────────
        mp = self._main_pts(yo)
        _bpoly(screen, mp, self._BG)

        # Top highlight strip
        ys   = [p[1] for p in mp]
        hl_h = max(4, (int(max(ys)) - int(min(ys))) // 10)
        _bpoly(screen, [
            (mp[0][0], mp[0][1]), (mp[1][0], mp[1][1]),
            (mp[1][0], mp[1][1] + hl_h), (mp[0][0], mp[0][1] + hl_h),
        ], (255, 255, 255, 12))
        _bpoly_border(screen, mp, self._BORDER, 2)
        _bline(screen, self._LINE, mp[0], mp[1], 3)

        # ── Title area ────────────────────────────────────────────────────────
        ty  = int(HEIGHT * self._SY0) + yo + 18
        tx  = WIDTH // 2

        lbl = _fnt(13).render("CHOOSE YOUR FATE", True, (120, 100, 185))
        lbl.set_alpha(_ci(220 * a_frac))
        screen.blit(lbl, (tx - lbl.get_width() // 2, ty))

        tsurf = _fnt(30, True).render("ENTER THE DUNGEON", True, (200, 145, 255))
        tsurf.set_alpha(_ci(255 * a_frac))
        screen.blit(tsurf, (tx - tsurf.get_width() // 2, ty + 20))

        div_y = ty + 62 + yo
        lx0   = int(WIDTH * 0.18)
        lx1   = int(WIDTH * 0.82)
        dl = pygame.Surface((lx1 - lx0, 2), pygame.SRCALPHA)
        dl.fill((155, 100, 225, _ci(75 * a_frac)))
        screen.blit(dl, (lx0, div_y))

        # ── Difficulty cards ──────────────────────────────────────────────────
        for i in range(3):
            rect = self._card_rect(i)
            it   = self._it[i]
            hv   = self._hv[i]
            sc   = self._hs[i]
            col  = self._COLS[i]
            sel  = (i == self.diff_sel)

            if it < 0.01:
                continue

            card_yo = int(_l(50, 0, _oc(it))) + yo
            pts = self._card_pts(rect, card_yo, sc)

            _bpoly(screen, pts, (*self._BG[:3], _ci(int(_l(120, 160, hv)) * it * a_frac)))

            if sel:
                _bpoly(screen, pts, (*col, _ci(int(32 * it * a_frac))))

            border_a = _ci(int(_l(58, 200, hv + (0.5 if sel else 0))) * it * a_frac)
            _bpoly_border(screen, pts, (*col, border_a), 2)

            top_a = _ci(int(_l(100, 240, hv + (0.4 if sel else 0))) * it * a_frac)
            _bline(screen, (*col, top_a), pts[0], pts[1], 2)

            if hv > 0.01:
                _bpoly(screen, pts, (*col, _ci(int(hv * 22 * it * a_frac))))

            cy0 = rect.centery + card_yo - int(rect.height / 2 * sc)
            cx  = rect.centerx
            text_a = _ci(int(255 * it * a_frac))

            # Difficulty name
            name_col = (255, 255, 255) if sel else col
            ns = _fnt(20, True).render(self._DIFFS[i], True, name_col)
            ns.set_alpha(text_a)
            screen.blit(ns, (cx - ns.get_width() // 2,
                             cy0 + int(rect.height * sc * 0.12)))

            # Stats
            cfg = DIFFICULTY[self._DIFFS[i]]
            stats = [
                (f"{cfg['stages']} stages", (200, 200, 215)),
                (f"HP  ×{cfg['hp_m']:.2f}",  (155, 225, 170)),
                (f"Gold ×{cfg['gold_m']:.1f}", (255, 215, 100)),
            ]
            for j, (txt, scol) in enumerate(stats):
                ss = _fnt(13).render(txt, True, scol)
                ss.set_alpha(_ci(int(210 * it * a_frac)))
                screen.blit(ss, (cx - ss.get_width() // 2,
                                 cy0 + int(rect.height * sc * (0.38 + j * 0.18))))

            if sel:
                bar_y = cy0 + int(rect.height * sc) - 8
                bar_x = cx - int(rect.width * sc * 0.38)
                bar_w = int(rect.width * sc * 0.76)
                bs = pygame.Surface((bar_w, 4), pygame.SRCALPHA)
                bs.fill((*col, _ci(int(210 * it * a_frac))))
                screen.blit(bs, (bar_x, bar_y))

        # ── ENTER button ──────────────────────────────────────────────────────
        e_sc  = 1.0 + self._enter_hv * 0.04
        epts  = self._enter_pts(yo, e_sc)
        col_e = (255, 205, 50)

        _bpoly(screen, epts, (75, 38, 160, _ci(int(_l(175, 235, self._enter_hv) * a_frac))))
        if self._enter_hv > 0.01:
            _bpoly(screen, epts, (*col_e, _ci(int(self._enter_hv * 30 * a_frac))))
        _bpoly_border(screen, epts, (*col_e, _ci(int(_l(155, 245, self._enter_hv) * a_frac))), 2)
        _bline(screen, (*col_e, _ci(int(_l(160, 255, self._enter_hv) * a_frac))),
               epts[0], epts[1], 2)

        er = self._enter_rect(yo)
        es = _fnt(16, True).render("ENTER  [ Enter ]", True, col_e)
        es.set_alpha(_ci(int(255 * a_frac)))
        screen.blit(es, (er.centerx - es.get_width() // 2,
                         er.centery - es.get_height() // 2))

        # ── Cancel hint ───────────────────────────────────────────────────────
        cs = _fnt(12).render("[Esc] Cancel", True, (80, 75, 105))
        cs.set_alpha(_ci(int(175 * a_frac)))
        screen.blit(cs, (WIDTH // 2 - cs.get_width() // 2,
                         int(HEIGHT * self._SY1) + yo - 26))
