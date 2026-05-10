"""StorageUI — Persona-style dual-panel storage UI.
Left shard: player's inventory (deposit items).
Right shard: storage contents (withdraw items).
Tab / Left-Right switches active panel; Enter/E transfers selected item.
"""
import pygame, math
from settings import WIDTH, HEIGHT

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


class StorageUI:
    # Left shard: player inventory (narrow, like compressed pause)
    _L_X0, _L_X1 = 0.035, 0.218
    _L_Y0, _L_Y1 = 0.055, 0.945
    _L_SK         = 0.014

    # Right shard: storage (wider, like InventoryUI)
    _R_X0, _R_X1 = 0.230, 0.985
    _R_Y0, _R_Y1 = 0.055, 0.945
    _R_SK         = 0.014

    _ROWS_MAX     = 8
    _ROW_H_FRAC   = 0.080
    _PAD_TOP_FRAC = 0.105
    _PAD_X_FRAC   = 0.016

    _IN_DUR    = 0.46
    _OUT_DUR   = 0.30
    _STAG      = 0.034
    _ITEM_DUR  = 0.20
    _HS        = 12.

    _BG        = (10, 11, 22, 148)
    _BORDER    = (255, 255, 255,  55)
    _BORDER_A  = (255, 215,   0, 220)   # gold — active panel
    _LINE      = (255, 255, 255, 160)
    _LINE_A    = (255, 215,   0, 255)
    _SEL_BG    = (255, 255, 255, 230)
    _SEL_TXT   = (8,   8,  20)
    _HDR_A     = (255, 215,   0)
    _HDR_I     = (165, 162, 205)
    _HINT      = (62,  65,  88)

    def __init__(self):
        self.open    = False
        self._phase  = 'closed'
        self._ft     = 0.
        self._ot     = 0.
        self._panel  = 'storage'   # which panel is active: 'inventory' | 'storage'
        self._l_sel  = 0
        self._r_sel  = 0
        self._l_scr  = 0
        self._r_scr  = 0
        self._l_it   = []
        self._l_hv   = []
        self._l_hs   = []
        self._r_it   = []
        self._r_hv   = []
        self._r_hs   = []
        self._last_ms = 0
        self._msg    = ""
        self._msg_t  = 0.

    def show(self):
        self.open   = True
        self._phase = 'opening'
        self._ft    = 0.
        self._ot    = 0.
        self._panel = 'storage'
        self._msg   = ""
        self._msg_t = 0.

    def hide(self):
        if self._phase in ('opening', 'open'):
            self._phase = 'closing'
            self._ft    = 0.

    @property
    def is_open(self):
        return self.open

    # ── geometry ──────────────────────────────────────────────────────────────

    def _lpts(self, yo=0):
        sk = int(WIDTH * self._L_SK)
        x0 = int(WIDTH * self._L_X0)
        x1 = int(WIDTH * self._L_X1)
        y0 = int(HEIGHT * self._L_Y0) + yo
        y1 = int(HEIGHT * self._L_Y1) + yo
        return [(x0 + sk, y0), (x1 + sk, y0), (x1, y1), (x0, y1)]

    def _rpts(self, yo=0):
        sk = int(WIDTH * self._R_SK)
        x0 = int(WIDTH * self._R_X0)
        x1 = int(WIDTH * self._R_X1)
        y0 = int(HEIGHT * self._R_Y0) + yo
        y1 = int(HEIGHT * self._R_Y1) + yo
        return [(x0 + sk, y0), (x1 + sk, y0), (x1, y1), (x0, y1)]

    def _lrow(self, vi, yo=0):
        sk  = int(WIDTH * self._L_SK)
        x0  = int(WIDTH * self._L_X0) + int(WIDTH * self._PAD_X_FRAC) + sk
        x1  = int(WIDTH * self._L_X1) - int(WIDTH * self._PAD_X_FRAC)
        y0s = int(HEIGHT * self._L_Y0) + int(HEIGHT * self._PAD_TOP_FRAC)
        rh  = int(HEIGHT * self._ROW_H_FRAC)
        return x0, y0s + vi * rh + yo, x1 - x0, rh

    def _rrow(self, vi, yo=0):
        sk  = int(WIDTH * self._R_SK)
        x0  = int(WIDTH * self._R_X0) + int(WIDTH * self._PAD_X_FRAC) + sk
        x1  = int(WIDTH * self._R_X1) - int(WIDTH * self._PAD_X_FRAC)
        y0s = int(HEIGHT * self._R_Y0) + int(HEIGHT * self._PAD_TOP_FRAC)
        rh  = int(HEIGHT * self._ROW_H_FRAC)
        return x0, y0s + vi * rh + yo, x1 - x0, rh

    def _vis(self, n):
        return min(self._ROWS_MAX, n)

    # ── list sync ─────────────────────────────────────────────────────────────

    def _sync(self, inv_n, stor_n):
        def _fit(lst, n, default):
            while len(lst) < n:
                lst.append(default)
            del lst[n:]
        _fit(self._l_it, inv_n,  0.)
        _fit(self._l_hv, inv_n,  0.)
        _fit(self._l_hs, inv_n,  1.)
        _fit(self._r_it, stor_n, 0.)
        _fit(self._r_hv, stor_n, 0.)
        _fit(self._r_hs, stor_n, 1.)

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, dt, player):
        self._last_ms = pygame.time.get_ticks()

        if self._msg_t > 0:
            self._msg_t = max(0., self._msg_t - dt)
            if self._msg_t == 0:
                self._msg = ""

        if self._phase == 'closed':
            return

        inv_n  = len(player.inventory)             if player                              else 0
        stor_n = len(player.storage)               if player and hasattr(player, 'storage') else 0
        self._sync(inv_n, stor_n)

        if self._phase == 'opening':
            self._ft = min(1., self._ft + dt / self._IN_DUR)
            if self._ft >= 1.:
                self._phase = 'open'
                self._ft    = 1.
                self._ot    = 0.

        elif self._phase == 'open':
            self._ot += dt

            for vi in range(self._vis(inv_n)):
                i   = self._l_scr + vi
                tgt = min(1., max(0., (self._ot - vi * self._STAG) / self._ITEM_DUR))
                self._l_it[i] = _sm(self._l_it[i], tgt, 10., dt)

            for vi in range(self._vis(stor_n)):
                i   = self._r_scr + vi
                tgt = min(1., max(0., (self._ot - vi * self._STAG) / self._ITEM_DUR))
                self._r_it[i] = _sm(self._r_it[i], tgt, 10., dt)

        elif self._phase == 'closing':
            self._ft = min(1., self._ft + dt / self._OUT_DUR)
            for lst in (self._l_it, self._r_it, self._l_hv, self._r_hv):
                for i in range(len(lst)):
                    lst[i] = _sm(lst[i], 0., 18., dt)
            if self._ft >= 1.:
                self._phase = 'closed'
                self.open   = False

    # ── events ────────────────────────────────────────────────────────────────

    def handle_event(self, ev, player):
        if not self.open:
            return False

        inv  = player.inventory                             if player                              else []
        stor = player.storage if player and hasattr(player, 'storage') else []

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.hide()
                return True

            # Switch active panel
            if ev.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
                self._panel = 'inventory' if self._panel == 'storage' else 'storage'
                self._ot    = 0.
                for i in range(len(self._l_it)): self._l_it[i] = 0.
                for i in range(len(self._r_it)): self._r_it[i] = 0.
                return True

            if self._panel == 'storage':
                n = len(stor)
                if ev.key == pygame.K_DOWN:
                    self._r_sel = min(self._r_sel + 1, max(0, n - 1))
                    if self._r_sel >= self._r_scr + self._ROWS_MAX:
                        self._r_scr = self._r_sel - self._ROWS_MAX + 1
                elif ev.key == pygame.K_UP:
                    self._r_sel = max(0, self._r_sel - 1)
                    if self._r_sel < self._r_scr:
                        self._r_scr = self._r_sel
                elif ev.key in (pygame.K_RETURN, pygame.K_e):
                    self._withdraw(player)
            else:
                n = len(inv)
                if ev.key == pygame.K_DOWN:
                    self._l_sel = min(self._l_sel + 1, max(0, n - 1))
                    if self._l_sel >= self._l_scr + self._ROWS_MAX:
                        self._l_scr = self._l_sel - self._ROWS_MAX + 1
                elif ev.key == pygame.K_UP:
                    self._l_sel = max(0, self._l_sel - 1)
                    if self._l_sel < self._l_scr:
                        self._l_scr = self._l_sel
                elif ev.key in (pygame.K_RETURN, pygame.K_e):
                    self._deposit(player)
            return True

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            inv_n  = len(inv)
            stor_n = len(stor)
            for vi in range(self._vis(inv_n)):
                i = self._l_scr + vi
                x, y, w, h = self._lrow(vi, 0)
                if x <= mx <= x + w and y <= my <= y + h:
                    if self._panel == 'inventory' and i == self._l_sel:
                        self._deposit(player)
                    else:
                        self._panel = 'inventory'
                        self._l_sel = i
                    return True
            for vi in range(self._vis(stor_n)):
                i = self._r_scr + vi
                x, y, w, h = self._rrow(vi, 0)
                if x <= mx <= x + w and y <= my <= y + h:
                    if self._panel == 'storage' and i == self._r_sel:
                        self._withdraw(player)
                    else:
                        self._panel = 'storage'
                        self._r_sel = i
                    return True

        if ev.type == pygame.MOUSEWHEEL:
            if self._panel == 'storage':
                stor_n = len(stor)
                if ev.y < 0:
                    self._r_scr = min(max(0, stor_n - self._ROWS_MAX), self._r_scr + 1)
                elif ev.y > 0:
                    self._r_scr = max(0, self._r_scr - 1)
            else:
                inv_n = len(inv)
                if ev.y < 0:
                    self._l_scr = min(max(0, inv_n - self._ROWS_MAX), self._l_scr + 1)
                elif ev.y > 0:
                    self._l_scr = max(0, self._l_scr - 1)
            return True

        return True

    # ── transfer helpers ──────────────────────────────────────────────────────

    def _deposit(self, player):
        inv = player.inventory
        if not inv:
            return
        self._l_sel = min(self._l_sel, len(inv) - 1)
        stor = player.storage
        itm  = inv[self._l_sel]
        if itm.stack:
            for ex in stor:
                if ex.itype == itm.itype:
                    ex.count += itm.count
                    inv.pop(self._l_sel)
                    self._l_sel = max(0, self._l_sel - 1)
                    self._msg   = f"Deponiral: {itm.name}"
                    self._msg_t = 1.8
                    self._ot    = 0.
                    return
        stor.append(inv.pop(self._l_sel))
        self._l_sel = max(0, self._l_sel - 1)
        self._msg   = f"Deponiral: {stor[-1].name}"
        self._msg_t = 1.8
        self._ot    = 0.

    def _withdraw(self, player):
        stor = player.storage
        if not stor:
            return
        self._r_sel = min(self._r_sel, len(stor) - 1)
        max_slots   = getattr(player, 'max_inv_slots', 20)
        inv         = player.inventory
        if len(inv) >= max_slots:
            self._msg   = "Inventar je poln!"
            self._msg_t = 1.8
            return
        itm = stor[self._r_sel]
        if itm.stack:
            for ex in inv:
                if ex.itype == itm.itype:
                    ex.count += itm.count
                    stor.pop(self._r_sel)
                    self._r_sel = max(0, self._r_sel - 1)
                    self._msg   = f"Vzel: {itm.name}"
                    self._msg_t = 1.8
                    self._ot    = 0.
                    return
        inv.append(stor.pop(self._r_sel))
        self._r_sel = max(0, self._r_sel - 1)
        self._msg   = f"Vzel: {inv[-1].name}"
        self._msg_t = 1.8
        self._ot    = 0.

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, player):
        if not self.open:
            return
        if pygame.time.get_ticks() - self._last_ms > 4:
            self.update(min((pygame.time.get_ticks() - self._last_ms) / 1000., 0.05), player)

        inv  = player.inventory                             if player                              else []
        stor = player.storage if player and hasattr(player, 'storage') else []

        if self._phase == 'opening':
            ep  = _ob(self._ft)
            yo  = int(_l(-(HEIGHT + 100), 0, ep))
            ova = int(170 * self._ft)
        elif self._phase == 'open':
            yo  = 0
            ova = 170
        else:
            yo  = int(_l(0, HEIGHT + 100, _ic(self._ft)))
            ova = int(170 * (1. - self._ft))

        a_frac = ova / 170.

        # Dark overlay
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((5, 5, 12, _ci(ova * 0.65)))
        screen.blit(ov, (0, 0))

        lact = (self._panel == 'inventory')
        ract = (self._panel == 'storage')

        # ── Left shard (INVENTAR) ──────────────────────────────────
        lp = self._lpts(yo)
        _bpoly(screen, lp, self._BG)
        _bpoly_border(screen, lp, self._BORDER_A if lact else self._BORDER, 2)
        _bline(screen, self._LINE_A if lact else self._LINE, lp[0], lp[1], 3)

        lsk = int(WIDTH * self._L_SK)
        lhx = int(WIDTH * self._L_X0) + lsk + int(WIDTH * self._PAD_X_FRAC) + 2
        lhy = int(HEIGHT * self._L_Y0) + yo + 10
        lhc = self._HDR_A if lact else self._HDR_I
        lhs = _fnt(int(HEIGHT * 0.028), bold=True).render("INVENTAR", True, lhc)
        lhs.set_alpha(_ci(255 * a_frac))
        screen.blit(lhs, (lhx, lhy))

        inv_n = len(inv)
        for vi in range(self._vis(inv_n)):
            i = self._l_scr + vi
            if i >= inv_n:
                break
            it_p = self._l_it[i] if i < len(self._l_it) else 0.
            if it_p < 0.004:
                continue

            ep_i   = _oc(it_p)
            is_sel = (i == self._l_sel) and lact
            itm    = inv[i]
            rx, ry, rw, rh = self._lrow(vi, yo)
            dx = rx + int(_l(-85, 0, ep_i))
            dy = ry

            bg = pygame.Surface((rw, rh), pygame.SRCALPHA)
            if is_sel:
                bg.fill((255, 255, 255, _ci(225 * ep_i)))
            screen.blit(bg, (dx, dy))

            nm_c = self._SEL_TXT if is_sel else (200, 200, 240)
            nm_s = _fnt(max(8, int(rh * 0.38)), bold=True).render(
                getattr(itm, 'name', '???'), True, nm_c)
            nm_s.set_alpha(_ci(ep_i * 255))
            screen.blit(nm_s, (dx + 8, dy + rh // 2 - nm_s.get_height() // 2))

            if getattr(itm, 'stack', False) and getattr(itm, 'count', 1) > 1:
                cs = _fnt(max(7, int(rh * 0.27))).render(
                    f"x{itm.count}", True,
                    (40, 40, 80) if is_sel else (155, 150, 195))
                cs.set_alpha(_ci(ep_i * 200))
                screen.blit(cs, (dx + rw - cs.get_width() - 6,
                                 dy + rh // 2 - cs.get_height() // 2))

        # Deposit hint when inventory panel is active
        if lact and inv_n > 0:
            ar = _fnt(11, bold=True).render("→ DEPONIRAJ [Enter]", True, (255, 215, 0))
            ar.set_alpha(_ci(160 * a_frac))
            screen.blit(ar, (lhx, int(HEIGHT * self._L_Y1) + yo - 22))

        # ── Right shard (STORAGE) ──────────────────────────────────
        rp = self._rpts(yo)
        _bpoly(screen, rp, self._BG)
        _bpoly_border(screen, rp, self._BORDER_A if ract else self._BORDER, 2)
        _bline(screen, self._LINE_A if ract else self._LINE, rp[0], rp[1], 3)

        rsk = int(WIDTH * self._R_SK)
        rhx = int(WIDTH * self._R_X0) + rsk + int(WIDTH * self._PAD_X_FRAC) + 2
        rhy = int(HEIGHT * self._R_Y0) + yo + 10
        rhc = self._HDR_A if ract else self._HDR_I
        rhs = _fnt(int(HEIGHT * 0.036), bold=True).render("STORAGE", True, rhc)
        rhs.set_alpha(_ci(255 * a_frac))
        screen.blit(rhs, (rhx, rhy))

        stor_n = len(stor)
        if stor_n == 0:
            es = _fnt(int(HEIGHT * 0.026)).render("Storage je prazen.", True, (75, 72, 108))
            es.set_alpha(_ci(150 * a_frac))
            screen.blit(es, (rhx, rhy + rhs.get_height() + int(HEIGHT * 0.04)))

        for vi in range(self._vis(stor_n)):
            i = self._r_scr + vi
            if i >= stor_n:
                break
            it_p = self._r_it[i] if i < len(self._r_it) else 0.
            if it_p < 0.004:
                continue

            ep_i   = _oc(it_p)
            is_sel = (i == self._r_sel) and ract
            itm    = stor[i]
            rx, ry, rw, rh = self._rrow(vi, yo)
            dx = rx + int(_l(110, 0, ep_i))
            dy = ry

            bg = pygame.Surface((rw, rh), pygame.SRCALPHA)
            if is_sel:
                bg.fill((255, 255, 255, _ci(225 * ep_i)))
            screen.blit(bg, (dx, dy))

            nm_c = self._SEL_TXT if is_sel else (200, 200, 240)
            nm_s = _fnt(max(8, int(rh * 0.38)), bold=True).render(
                getattr(itm, 'name', '???'), True, nm_c)
            nm_s.set_alpha(_ci(ep_i * 255))
            screen.blit(nm_s, (dx + 12, dy + rh // 2 - nm_s.get_height() // 2))

            if getattr(itm, 'stack', False) and getattr(itm, 'count', 1) > 1:
                cs = _fnt(max(7, int(rh * 0.27))).render(
                    f"x{itm.count}", True,
                    (40, 40, 80) if is_sel else (155, 150, 195))
                cs.set_alpha(_ci(ep_i * 200))
                screen.blit(cs, (dx + rw - cs.get_width() - 6,
                                 dy + rh // 2 - cs.get_height() // 2))

        # Withdraw hint when storage panel is active
        if ract:
            ar = _fnt(11, bold=True).render("← VZEMI [Enter]", True, (255, 215, 0))
            ar.set_alpha(_ci(160 * a_frac))
            screen.blit(ar, (rhx, int(HEIGHT * self._R_Y1) + yo - 22))

        # Shared controls hint at bottom
        if self._phase == 'open' and self._ot > 0.55:
            ht = _fnt(13).render(
                "[ Tab / ←→ ] Zamenjaj panel    [ ↑↓ ] Navigiraj    [ Enter ] Premakni    [ Esc ] Zapri",
                True, self._HINT)
            ht.set_alpha(_ci(min(110, (self._ot - 0.55) * 220)))
            screen.blit(ht, (rhx, int(HEIGHT * self._R_Y1) + yo - 22))

        # Transfer feedback message (centered)
        if self._msg:
            mc = (80, 210, 80) if "poln" not in self._msg else (210, 90, 90)
            ms = _fnt(int(HEIGHT * 0.026), bold=True).render(self._msg, True, mc)
            ms.set_alpha(_ci(min(255, self._msg_t * 300)))
            screen.blit(ms, (WIDTH // 2 - ms.get_width() // 2,
                              int(HEIGHT * 0.020) + yo))
