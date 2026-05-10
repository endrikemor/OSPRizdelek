"""
InventoryUI — Persona-style shard panel, mirrored from PauseUI.
Popravljeno: vzporeden nagib z PauseUI, zamik v desno in gladek slide-in.
"""
import pygame, math
from settings import WIDTH, HEIGHT

# ── shared easing / helpers ───────────────────────────────────────────────────
def _l(a, b, t):    return a + (b - a) * t
def _oc(t):         t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def _ic(t):         t = max(0., min(1., t)); return t * t * t
def _sm(c, tgt, s, dt): return c + (tgt - c) * (1. - math.exp(-s * dt))
def _ci(v):         return max(0, min(255, int(v)))

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


# ═══════════════════════════════════════════════════════════════════════════════
class InventoryUI:
    # ── shard geometry (Usklajeno z PauseUI: zamik desno in pozitiven nagib) ──
    _SX0, _SX1   = 0.220, 0.985
    _SY0, _SY1   = 0.055, 0.945
    _SK          = 0.014   # Pozitiven nagib (vzporedno s PauseUI _SC_SK)

    # ── animation ────────────────────────────────────────────────────────────
    _IN_DUR       = 0.48   # Rahlo podaljšano za lepši slide
    _OUT_DUR      = 0.32
    _ITEM_STAG    = 0.038
    _ITEM_DUR     = 0.22
    _HS           = 12.

    # ── palette ──────────────────────────────────────────────────────────────
    _SHARD_BG     = (10, 11, 22, 155)
    _BORDER       = (255, 255, 255, 55)
    _TOP_LINE     = (255, 255, 255, 165)
    _SEL_BG       = (255, 255, 255, 235)
    _SEL_TXT      = (8,   8,  20)
    _HOV_ALPHA    = 50
    _HINT_COL     = (62,  66,  88)
    _HDR_COL      = (220, 225, 255)
    _STAT_COL     = (120, 128, 165)
    _DESC_BG      = (16,  16,  30, 180)
    _DESC_BORDER  = (255, 255, 255, 38)

    _ROW_H_FRAC   = 0.082 
    _ROWS_MAX     = 8 
    _PAD_TOP_FRAC = 0.110 
    _PAD_X_FRAC   = 0.022 

    def __init__(self):
        self._phase      = 'closed'
        self._ft         = 0.
        self._ot         = 0.
        self._it         = []
        self._hv         = []
        self._hs         = []
        self._scroll     = 0
        self._sel        = 0
        self._prev_hov   = -1
        self._last_ms    = 0
        self.on_close_cb = None

    @property
    def is_open(self):
        return self._phase != 'closed'

    def open_inv(self):
        if self._phase == 'closed':
            self._phase  = 'opening'
            self._ft     = 0.
            self._ot     = 0.
            self._scroll = 0
            self._sel    = 0

    def close_inv(self):
        if self._phase in ('opening', 'open'):
            self._phase = 'closing'
            self._ft     = 0.

    # ── geometry helpers (Popravljeno za vzporednost) ────────────────────────
    def _spts(self, xo=0):
        sk  = int(WIDTH * self._SK)
        x0  = int(WIDTH * self._SX0) + xo
        x1  = int(WIDTH * self._SX1) + xo
        y0  = int(HEIGHT * self._SY0)
        y1  = int(HEIGHT * self._SY1)
        # Zgornja robova nagnjena v desno (+sk)
        return [(x0 + sk, y0), (x1 + sk, y0), (x1, y1), (x0, y1)]

    def _inner_rect(self, xo=0):
        sk   = int(WIDTH * self._SK)
        px   = int(WIDTH  * self._PAD_X_FRAC)
        x0   = int(WIDTH  * self._SX0) + xo + px + sk
        x1   = int(WIDTH  * self._SX1) + xo - px
        y0   = int(HEIGHT * self._SY0) + int(HEIGHT * self._PAD_TOP_FRAC)
        y1   = int(HEIGHT * self._SY1) - int(HEIGHT * 0.105)
        return x0, y0, x1 - x0, y1 - y0

    def _row_h(self):
        return int(HEIGHT * self._ROW_H_FRAC)

    def _visible_items(self, n_items):
        return min(self._ROWS_MAX, n_items)

    def _row_bounds(self, vis_idx, xo=0):
        x0, y0, w, _ = self._inner_rect(xo)
        rh = self._row_h()
        ry = y0 + vis_idx * rh
        return x0, ry, w, rh

    def _hit_row(self, mx, my, n_items, xo=0):
        vis = self._visible_items(n_items)
        for vi in range(vis):
            x, y, w, h = self._row_bounds(vi, xo)
            if x <= mx <= x + w and y <= my <= y + h:
                return self._scroll + vi
        return -1

    def _sync_lists(self, n):
        while len(self._it) < n:
            self._it.append(0.); self._hv.append(0.); self._hs.append(1.)
        if len(self._it) > n:
            self._it = self._it[:n]; self._hv = self._hv[:n]; self._hs = self._hs[:n]

    def _slide_xo(self):
        """Uporablja _oc (Cubic Ease Out) za gladek slide-in brez odboja."""
        if self._phase == 'opening':
            return int(_l(WIDTH + 200, 0, _oc(self._ft)))
        elif self._phase == 'open':
            return 0
        elif self._phase == 'closing':
            return int(_l(0, WIDTH + 200, _ic(self._ft)))
        return WIDTH + 200

    def update(self, dt, player=None):
        self._last_ms = pygame.time.get_ticks()
        if self._phase == 'closed':
            return

        n = len(player.inventory) if player else 0
        self._sync_lists(n)

        mx, my = pygame.mouse.get_pos()
        xo     = self._slide_xo()

        if self._phase == 'opening':
            self._ft = min(1., self._ft + dt / self._IN_DUR)
            if self._ft >= 1.:
                self._phase = 'open'
                self._ft    = 1.

        elif self._phase == 'open':
            self._ot += dt
            vis = self._visible_items(n)
            for vi in range(vis):
                i   = self._scroll + vi
                tgt = min(1., max(0., (self._ot - vi * self._ITEM_STAG) / self._ITEM_DUR))
                self._it[i] = _sm(self._it[i], tgt, 10., dt)

            hov = self._hit_row(mx, my, n, xo)
            self._prev_hov = hov

            for i in range(n):
                is_h = (i == hov)
                self._hv[i] = _sm(self._hv[i], 1. if is_h else 0., self._HS, dt)
                self._hs[i] = _sm(self._hs[i], 1.04 if is_h else 1., self._HS, dt)

        elif self._phase == 'closing':
            self._ft = min(1., self._ft + dt / self._OUT_DUR)
            for i in range(len(self._it)):
                self._it[i] = _sm(self._it[i], 0., 18., dt)
            if self._ft >= 1.:
                self._phase = 'closed'
                if callable(self.on_close_cb):
                    self.on_close_cb()

    def handle_event(self, ev, player) -> bool:
        if self._phase == 'closed':
            return False
        n = len(player.inventory) if player else 0
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.close_inv(); return True
            if n == 0: return True
            if ev.key == pygame.K_UP:
                self._sel = max(0, self._sel - 1); self._clamp_scroll(n); return True
            if ev.key == pygame.K_DOWN:
                self._sel = min(n - 1, self._sel + 1); self._clamp_scroll(n); return True
            if ev.key in (pygame.K_e, pygame.K_RETURN):
                self._use(player); return True
            if ev.key == pygame.K_DELETE:
                self._drop(player); return True
        if ev.type == pygame.MOUSEBUTTONDOWN:
            xo = self._slide_xo()
            if ev.button == 1:
                hi = self._hit_row(ev.pos[0], ev.pos[1], n, xo)
                if hi >= 0: self._sel = hi; self._use(player); return True
            if ev.button == 4: self._scroll = max(0, self._scroll - 1); return True
            if ev.button == 5: self._scroll = min(max(0, n - self._ROWS_MAX), self._scroll + 1); return True
        return True

    def _clamp_scroll(self, n):
        vis = self._visible_items(n)
        if self._sel < self._scroll: self._scroll = self._sel
        elif self._sel >= self._scroll + vis: self._scroll = self._sel - vis + 1
        self._scroll = max(0, min(self._scroll, max(0, n - vis)))

    def _use(self, player):
        if not player.inventory: return
        self._sel = min(self._sel, len(player.inventory) - 1)
        itm = player.inventory[self._sel]
        if itm.use(player):
            if getattr(itm, 'stack', False):
                itm.count -= 1
                if itm.count <= 0: player.inventory.pop(self._sel); self._sel = max(0, self._sel - 1)
            else:
                player.inventory.pop(self._sel); self._sel = max(0, self._sel - 1)
        self._sync_lists(len(player.inventory)); self._clamp_scroll(len(player.inventory))

    def _drop(self, player):
        if not player.inventory: return
        self._sel = min(self._sel, len(player.inventory) - 1)
        player.inventory.pop(self._sel); self._sel = max(0, self._sel - 1)
        self._sync_lists(len(player.inventory)); self._clamp_scroll(len(player.inventory))

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, screen, player):
        if self._phase == 'closed': return
        if pygame.time.get_ticks() - self._last_ms > 4:
            self.update(min((pygame.time.get_ticks() - self._last_ms) / 1000., 0.05), player)

        xo = self._slide_xo()
        pts = self._spts(xo)
        alpha_frac = self._ft if self._phase == 'opening' else (1. - self._ft if self._phase == 'closing' else 1.)

        # Shard BG + Border
        _bpoly(screen, pts, (self._SHARD_BG[0], self._SHARD_BG[1], self._SHARD_BG[2], _ci(self._SHARD_BG[3] * alpha_frac)))
        _bpoly_border(screen, pts, (self._BORDER[0], self._BORDER[1], self._BORDER[2], _ci(self._BORDER[3] * alpha_frac)), 2)
        _bline(screen, (self._TOP_LINE[0], self._TOP_LINE[1], self._TOP_LINE[2], _ci(self._TOP_LINE[3] * alpha_frac)), pts[0], pts[1], 3)

        # Header Text (zamaknjen za nagib)
        sk = int(WIDTH * self._SK)
        hdr_x = int(WIDTH * self._SX0) + xo + int(WIDTH * self._PAD_X_FRAC) + sk
        hdr_y = int(HEIGHT * self._SY0) + int(HEIGHT * 0.018)
        hdr_s = _fnt(int(HEIGHT * 0.038), bold=True).render("INVENTORY", True, self._HDR_COL)
        hdr_s.set_alpha(_ci(255 * alpha_frac))
        screen.blit(hdr_s, (hdr_x, hdr_y))

        # Item Rows
        n = len(player.inventory) if player else 0
        vis = self._visible_items(n)
        for vi in range(vis):
            i = self._scroll + vi
            if i >= n: break
            it_prog = self._it[i] if i < len(self._it) else 0.
            if it_prog < 0.004: continue

            ep = _oc(it_prog) # Gladek slide za predmete
            sc, hg, is_s = self._hs[i], self._hv[i], (i == self._sel)
            rx, ry, rw, rh = self._row_bounds(vi, xo)
            slide = int(_l(160, 0, _oc(it_prog)))
            dx, dy = rx + slide, ry - (int(rh * sc) - rh) // 2

            bg = pygame.Surface((rw, int(rh * sc)), pygame.SRCALPHA)
            if is_s: bg.fill((self._SEL_BG[0], self._SEL_BG[1], self._SEL_BG[2], _ci(self._SEL_BG[3] * ep)))
            elif hg > 0.03: bg.fill((255, 255, 255, _ci(hg * self._HOV_ALPHA)))
            screen.blit(bg, (dx, dy))

            itm = player.inventory[i]
            lbl_s = _fnt(max(9, int(rh * 0.34)), bold=True).render(getattr(itm, 'name', '???'), True, self._SEL_TXT if is_s else (220, 220, 255))
            lbl_s.set_alpha(_ci(ep * 255))
            screen.blit(lbl_s, (dx + int(rh * 0.85), dy + int(rh * sc) // 2 - lbl_s.get_height() // 2))

        # Scroll Indicator + Description (dp_x popravljen za sk)
        if player and player.inventory and self._sel < len(player.inventory):
            itm = player.inventory[self._sel]
            dp_x = int(WIDTH * self._SX0) + xo + int(WIDTH * self._PAD_X_FRAC) + sk
            dp_y = int(HEIGHT * self._SY1) - int(HEIGHT * 0.100)
            dp_w = int(WIDTH * (self._SX1 - self._SX0)) - int(WIDTH * self._PAD_X_FRAC * 2) - sk
            pygame.draw.rect(screen, self._DESC_BG, (dp_x, dp_y, dp_w, int(HEIGHT * 0.085)))
            nm_s = _fnt(int(HEIGHT * 0.028), bold=True).render(getattr(itm, 'name', '???'), True, (255, 255, 255))
            screen.blit(nm_s, (dp_x + 10, dp_y + 5))