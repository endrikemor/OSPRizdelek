"""ShopUI — Persona-style shard shop panel (matching PauseUI design)."""
import pygame, math, os
from settings import WIDTH, HEIGHT
from items import ITEM_DATA

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


class ShopUI:
    # S1 – main item list (left shard, slightly wider than pause S1)
    _S1_X0, _S1_X1 = 0.048, 0.445
    _S1_Y0, _S1_Y1 = 0.062, 0.938
    _S1_SK          = 0.028

    # S2 – item details (upper-right corner shard, like pause S2)
    _S2_X0, _S2_X1 = 0.460, 0.710
    _S2_Y0, _S2_Y1 = 0.055, 0.530
    _S2_SK          = 0.020

    _VISIBLE  = 6
    _IN_DUR   = 0.46
    _OUT_DUR  = 0.32
    _STAG     = 0.038
    _IDUR     = 0.16
    _HS       = 11.

    _BG        = (11, 11, 21, 145)
    _BG2       = ( 9,  9, 18, 110)
    _BORDER    = (255, 255, 255,  58)
    _LINE      = (255, 255, 255, 160)
    _SEL_BG    = (255, 215,   0, 238)   # gold selection for shop
    _SEL_TXT   = (8,   8,  20)
    _HOV_BG    = (255, 255, 255,  52)
    _HINT      = (65,  68,  90)

    def __init__(self):
        self.open   = False
        self.stock  = []
        self.sel    = 0
        self.scroll = 0
        self.msg    = ""
        self._msg_t = 0.
        self.title  = "MERCHANT"

        self._phase       = 'closed'
        self._ft          = 0.
        self._ot          = 0.
        self._it          = []
        self._hv          = []
        self._hs          = []
        self._last_ms     = 0
        self._prev_hov    = -1
        self._prev_scroll = 0
        self._stable      = set()   # item indices that stay visible across a scroll

        self._sfx_hover  = self._load_sfx("hover")
        self._sfx_select = self._load_sfx("select")
        self._hover_ch  = None
        self._select_ch = None

    def _load_sfx(self, kind):
        try:
            from settings import HOVER_SFX_PATH, SELECT_SFX_PATH
            p = HOVER_SFX_PATH if kind == "hover" else SELECT_SFX_PATH
            if os.path.exists(p):
                return pygame.mixer.Sound(p)
        except Exception:
            pass
        return None

    def _play_sfx(self, snd, vol=0.5):
        if not snd:
            return
        snd.set_volume(max(0., min(1., vol)))
        snd.play()

    # ── public API ────────────────────────────────────────────────────────────

    def show(self, stock, title="MERCHANT"):
        self.stock        = list(stock)
        self.sel          = 0
        self.scroll       = 0
        self._prev_scroll = 0
        self._stable      = set()
        self.msg          = ""
        self.title        = title
        self.open         = True
        self._phase       = 'opening'
        self._ft          = 0.
        self._ot          = 0.
        self._sync_lists()

    def hide(self):
        if self._phase in ('opening', 'open'):
            self._phase = 'closing'
            self._ft    = 0.

    # ── geometry ──────────────────────────────────────────────────────────────

    def _s1pts(self, yo=0):
        sk = int(WIDTH * self._S1_SK)
        x0 = int(WIDTH * self._S1_X0)
        x1 = int(WIDTH * self._S1_X1)
        y0 = int(HEIGHT * self._S1_Y0) + yo
        y1 = int(HEIGHT * self._S1_Y1) + yo
        return [(x0 + sk, y0), (x1 + sk, y0), (x1, y1), (x0, y1)]

    def _s2pts(self, yo=0):
        sk    = int(WIDTH * self._S2_SK)
        x0    = int(WIDTH * self._S2_X0)
        x1    = int(WIDTH * self._S2_X1)
        y0    = int(HEIGHT * self._S2_Y0) + yo
        y1    = int(HEIGHT * self._S2_Y1) + yo
        notch = int(HEIGHT * 0.020)
        return [(x0 + sk, y0), (x1, y0 - notch), (x1 - sk // 2, y1), (x0, y1)]

    def _ibnd(self, vi, yo=0):
        sk   = int(WIDTH * self._S1_SK)
        x0   = int(WIDTH * self._S1_X0) + sk
        x1   = int(WIDTH * self._S1_X1)
        y0_s = int(HEIGHT * self._S1_Y0)
        pad  = int(HEIGHT * 0.088)
        avail = int(HEIGHT * (self._S1_Y1 - self._S1_Y0)) - pad - int(HEIGHT * 0.042)
        ih   = min(avail // self._VISIBLE, int(HEIGHT * 0.118))
        blk  = ih * self._VISIBLE
        sy   = y0_s + pad + (avail - blk) // 2
        return x0, sy + vi * ih + yo, x1 - x0, ih

    def _hit(self, mx, my, yo=0):
        for vi in range(min(self._VISIBLE, len(self.stock))):
            x, y, w, h = self._ibnd(vi, yo)
            if x <= mx <= x + w and y <= my <= y + h:
                return vi + self.scroll
        return -1

    # ── list sync ─────────────────────────────────────────────────────────────

    def _sync_lists(self):
        n = len(self.stock)
        while len(self._it) < n:
            self._it.append(0.); self._hv.append(0.); self._hs.append(1.)
        del self._it[n:]; del self._hv[n:]; del self._hs[n:]

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        self._last_ms = pygame.time.get_ticks()

        if self._msg_t > 0:
            self._msg_t = max(0., self._msg_t - dt)
            if self._msg_t == 0:
                self.msg = ""

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
            vis = min(self._VISIBLE, len(self.stock))
            for vi in range(vis):
                i = self.scroll + vi
                if i in self._stable:
                    self._it[i] = 1.       # stable: already visible, no re-animation
                    continue
                tgt = min(1., max(0., (self._ot - vi * self._STAG) / self._IDUR))
                self._it[i] = _sm(self._it[i], tgt, 10., dt)

            mx, my = pygame.mouse.get_pos()
            hov = self._hit(mx, my, 0)
            if hov != self._prev_hov and hov >= 0:
                self._play_sfx(self._sfx_hover, 0.4)
            self._prev_hov = hov

            for i in range(len(self.stock)):
                is_h = (i == hov)
                self._hv[i] = _sm(self._hv[i], 1. if is_h else 0., self._HS, dt)
                self._hs[i] = _sm(self._hs[i], 1.06 if is_h else 1., self._HS, dt)

        elif self._phase == 'closing':
            self._ft = min(1., self._ft + dt / self._OUT_DUR)
            for i in range(len(self._it)):
                self._it[i] = _sm(self._it[i], 0., 16., dt)
                self._hv[i] = _sm(self._hv[i], 0., 16., dt)
            if self._ft >= 1.:
                self._phase = 'closed'
                self.open   = False
                self._ot    = 0.

    # ── events ────────────────────────────────────────────────────────────────

    def handle_event(self, ev, player):
        if not self.open:
            return False
        n = len(self.stock)

        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_e):
                self.hide()
                return True
            if ev.key == pygame.K_DOWN:
                old = self.sel
                self.sel = min(self.sel + 1, n - 1)
                if self.sel != old:
                    self._play_sfx(self._sfx_hover, 0.4)
                if self.sel >= self.scroll + self._VISIBLE:
                    self._prev_scroll = self.scroll
                    self.scroll = self.sel - self._VISIBLE + 1
                    self._reset_anim()
                return True
            if ev.key == pygame.K_UP:
                old = self.sel
                self.sel = max(self.sel - 1, 0)
                if self.sel != old:
                    self._play_sfx(self._sfx_hover, 0.4)
                if self.sel < self.scroll:
                    self._prev_scroll = self.scroll
                    self.scroll = self.sel
                    self._reset_anim()
                return True
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._play_sfx(self._sfx_select, 0.5)
                self._buy(player)
                return True

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            hi = self._hit(ev.pos[0], ev.pos[1], 0)
            if hi >= 0:
                if hi == self.sel:
                    self._play_sfx(self._sfx_select, 0.5)
                    self._buy(player)
                else:
                    self._play_sfx(self._sfx_hover, 0.4)
                    self.sel = hi
                return True

        if ev.type == pygame.MOUSEWHEEL:
            if ev.y < 0:
                self.sel = min(self.sel + 1, n - 1)
                if self.sel >= self.scroll + self._VISIBLE:
                    self._prev_scroll = self.scroll
                    self.scroll += 1
                    self._reset_anim()
            elif ev.y > 0:
                self.sel = max(self.sel - 1, 0)
                if self.sel < self.scroll:
                    self._prev_scroll = self.scroll
                    self.scroll -= 1
                    self._reset_anim()
            return True

        return True

    def _reset_anim(self):
        n = len(self.stock)
        old_vis = set(range(self._prev_scroll,
                            min(self._prev_scroll + self._VISIBLE, n)))
        new_vis = set(range(self.scroll,
                            min(self.scroll + self._VISIBLE, n)))
        self._stable = old_vis & new_vis   # items visible in both: keep at 1.0
        for i in range(len(self._it)):
            if i in self._stable:
                self._it[i] = 1.           # already shown — don't re-animate
            elif i in new_vis:
                self._it[i] = 0.           # new item: animate in
        self._ot = 0.

    # ── buy logic ─────────────────────────────────────────────────────────────

    def _buy(self, player):
        if not self.stock:
            return
        iid, price = self.stock[self.sel]
        if player.gold < price:
            self.msg    = "Premalo zlata!"
            self._msg_t = 2.0
            return
        player.gold -= price
        if iid == "bag_upgrade":
            from settings import INV_SLOTS_MAX, INV_SLOTS_START
            player.max_inv_slots = min(
                INV_SLOTS_MAX,
                getattr(player, "max_inv_slots", INV_SLOTS_START) + 10)
            self.msg    = f"Torba razširjena! ({player.max_inv_slots} mest)"
            self._msg_t = 2.5
            return
        from items import Item
        from ui.helpers import add_to_inv
        itm = Item(0, 0, iid)
        add_to_inv(player, itm)
        self.msg    = f"Kupljeno: {itm.name}!"
        self._msg_t = 2.0

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen, player):
        if not self.open:
            return
        if pygame.time.get_ticks() - self._last_ms > 4:
            self.update(min((pygame.time.get_ticks() - self._last_ms) / 1000., 0.05))

        if self._phase == 'opening':
            ep  = _ob(self._ft)
            yo  = int(_l(-(HEIGHT + 100), 0, ep))
            ova = int(165 * self._ft)
        elif self._phase == 'open':
            yo  = 0
            ova = 165
        else:
            yo  = int(_l(0, HEIGHT + 100, _ic(self._ft)))
            ova = int(165 * (1. - self._ft))

        a_frac = ova / 165.

        # Dark overlay
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((5, 5, 12, _ci(ova * 0.65)))
        screen.blit(ov, (0, 0))

        # ── S1 shard (item list) ───────────────────────────────────
        p1 = self._s1pts(yo)
        _bpoly(screen, p1, self._BG)

        # Subtle highlight strip at top
        xs = [p[0] for p in p1]; ys = [p[1] for p in p1]
        bh = max(1, int(max(ys)) - int(min(ys)))
        hl_h = max(4, bh // 8)
        _bpoly(screen, [
            (p1[0][0], p1[0][1]), (p1[1][0], p1[1][1]),
            (p1[1][0], p1[1][1] + hl_h), (p1[0][0], p1[0][1] + hl_h),
        ], (255, 255, 255, 12))
        _bpoly_border(screen, p1, self._BORDER, 2)
        _bline(screen, self._LINE, p1[0], p1[1], 3)

        sk  = int(WIDTH * self._S1_SK)
        hx  = int(WIDTH * self._S1_X0) + sk + 18
        hy  = int(HEIGHT * self._S1_Y0) + yo + 12

        # Title
        tit = _fnt(int(HEIGHT * 0.040), bold=True).render(self.title, True, (255, 215, 0))
        tit.set_alpha(_ci(255 * a_frac))
        screen.blit(tit, (hx, hy))

        # Gold display
        gs = _fnt(int(HEIGHT * 0.024)).render(f"Zlato: {player.gold}", True, (215, 195, 110))
        gs.set_alpha(_ci(220 * a_frac))
        screen.blit(gs, (hx, hy + tit.get_height() + 4))

        # Items
        vis = min(self._VISIBLE, len(self.stock))
        for vi in range(vis):
            i      = self.scroll + vi
            iid, price = self.stock[i]
            d      = ITEM_DATA.get(iid, {})
            col    = d.get("color", (200, 200, 220))
            icn    = d.get("icon",  "?")
            nm     = d.get("name",  iid)
            desc   = d.get("desc",  "")

            it_p = self._it[i] if i < len(self._it) else 0.
            if it_p < 0.004:
                continue

            ep_i   = _oc(it_p)
            sc     = self._hs[i]
            hg     = self._hv[i]
            is_sel = (i == self.sel)

            ix, iy_b, iw, ih = self._ibnd(vi, yo)
            dh = int(ih * sc)
            dx = ix
            dy = iy_b - (dh - ih) // 2

            # Row background
            bg = pygame.Surface((iw, dh), pygame.SRCALPHA)
            if is_sel:
                bg.fill((255, 255, 255, _ci(160 * ep_i)))
            elif hg > 0.03:
                bg.fill((255, 255, 255, _ci(hg * 52 * ep_i)))
            screen.blit(bg, (dx, dy))

            # Selection bar
            if is_sel and ep_i > 0.05:
                bar_w = max(1, int(ih * 0.045))
                bar = pygame.Surface((bar_w, dh), pygame.SRCALPHA)
                bar.fill((8, 8, 20, _ci(200 * ep_i)))
                screen.blit(bar, (dx, dy))

            # Text colours
            tc_nm  = self._SEL_TXT if is_sel else (220, 220, 255)
            tc_dsc = (60, 55, 80)  if is_sel else (135, 132, 165)
            can    = player.gold >= price
            tc_pr  = (60, 55, 80)  if is_sel else ((200, 175, 70) if can else (200, 75, 75))

            # Icon letter
            ic_s = _fnt(int(ih * 0.50), bold=True).render(icn, True, col)
            ic_s.set_alpha(_ci(ep_i * 255))
            screen.blit(ic_s, (dx + int(ih * 0.12),
                                dy + dh // 2 - ic_s.get_height() // 2))

            # Name
            nm_s = _fnt(max(10, int(ih * 0.35)), bold=True).render(nm, True, tc_nm)
            nm_s.set_alpha(_ci(ep_i * 255))
            screen.blit(nm_s, (dx + int(ih * 0.82), dy + int(dh * 0.11)))

            # Description
            ds_s = _fnt(max(8, int(ih * 0.25))).render(desc[:48], True, tc_dsc)
            ds_s.set_alpha(_ci(ep_i * 200))
            screen.blit(ds_s, (dx + int(ih * 0.82), dy + int(dh * 0.50)))

            # Price (right edge)
            pr_s = _fnt(max(10, int(ih * 0.35)), bold=True).render(f"{price}g", True, tc_pr)
            pr_s.set_alpha(_ci(ep_i * 255))
            screen.blit(pr_s, (dx + iw - pr_s.get_width() - 14,
                                dy + dh // 2 - pr_s.get_height() // 2))

        # Scroll arrows
        if self.scroll > 0:
            ar = _fnt(15).render("▲", True, (115, 112, 145))
            ar.set_alpha(_ci(ova * 1.5))
            x0, y0a, w, _ = self._ibnd(0, yo)
            screen.blit(ar, (x0 + w // 2 - ar.get_width() // 2, y0a - 17))
        if self.scroll + self._VISIBLE < len(self.stock):
            ar = _fnt(15).render("▼", True, (115, 112, 145))
            ar.set_alpha(_ci(ova * 1.5))
            x0, ylast, w, ih = self._ibnd(
                min(self._VISIBLE - 1, len(self.stock) - 1), yo)
            screen.blit(ar, (x0 + w // 2 - ar.get_width() // 2, ylast + ih + 4))

        # Hint line
        if self._phase == 'open' and self._ot > 0.55:
            ht = _fnt(13).render(
                "[ ↑↓ ] Izbira    [ Enter ] Kupi    [ E / Esc ] Zapri",
                True, self._HINT)
            ht.set_alpha(_ci(min(108, (self._ot - 0.55) * 220)))
            screen.blit(ht, (hx, int(HEIGHT * self._S1_Y1) + yo - 26))

        # ── S2 shard (item details) ────────────────────────────────
        if self._phase == 'open' and self.stock and self._ot > 0.35:
            vis2 = min(1., (self._ot - 0.35) / 0.38)
            idx  = min(self.sel, len(self.stock) - 1)
            iid2, price2 = self.stock[idx]
            d2   = ITEM_DATA.get(iid2, {})
            p2   = self._s2pts(yo)

            _bpoly(screen, p2, (self._BG2[0], self._BG2[1], self._BG2[2],
                                 _ci(110 * vis2)))
            _bpoly_border(screen, p2, (255, 255, 255, _ci(42 * vis2)), 2)
            _bline(screen, (255, 255, 255, _ci(80 * vis2)), p2[0], p2[1], 3)

            s2x = int(WIDTH * self._S2_X0) + int(WIDTH * self._S2_SK) + 16
            s2y = int(HEIGHT * self._S2_Y0) + yo + 16

            n2 = _fnt(int(HEIGHT * 0.040), bold=True).render(
                d2.get("name", iid2), True, (255, 215, 0))
            n2.set_alpha(_ci(255 * vis2))
            screen.blit(n2, (s2x, s2y))

            ds2 = _fnt(int(HEIGHT * 0.025)).render(
                d2.get("desc", ""), True, (188, 185, 220))
            ds2.set_alpha(_ci(210 * vis2))
            screen.blit(ds2, (s2x, s2y + n2.get_height() + 8))

            can2 = player.gold >= price2
            pc2  = (95, 215, 95) if can2 else (215, 85, 85)
            pr2  = _fnt(int(HEIGHT * 0.034), bold=True).render(f"{price2}g", True, pc2)
            pr2.set_alpha(_ci(255 * vis2))
            screen.blit(pr2, (s2x, s2y + n2.get_height() + ds2.get_height() + 20))

            af_txt = "Can buy ✓" if can2 else "Not enough gold"
            af  = _fnt(int(HEIGHT * 0.021)).render(af_txt, True, pc2)
            af.set_alpha(_ci(195 * vis2))
            screen.blit(af, (s2x, s2y + n2.get_height() + ds2.get_height()
                               + pr2.get_height() + 26))

        # Purchase feedback
        if self.msg:
            mc = (78, 210, 78) if ("Kupljeno" in self.msg or "razšir" in self.msg) \
                 else (210, 85, 85)
            ms = _fnt(int(HEIGHT * 0.027), bold=True).render(self.msg, True, mc)
            ms.set_alpha(_ci(min(255, self._msg_t * 300)))
            screen.blit(ms, (hx, int(HEIGHT * self._S1_Y1) + yo - 52))
