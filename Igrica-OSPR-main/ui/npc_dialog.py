#pogovorno okno za NPC-je — portret, ime, besedilo z animacijo, DA/NE gumba
import pygame, os, math
from settings import WIDTH, HEIGHT, SHOP_NPC_IMG_PATH, STORAGE_NPC_IMG_PATH, TEXT_SFX_PATH

_FC = {}
def _fnt(sz, bold=False):
    k = (sz, bold)
    if k not in _FC:
        for n in ("Nunito", "Segoe UI", "Verdana", None):
            try: _FC[k] = pygame.font.SysFont(n, sz, bold=bold); break
            except: pass
    return _FC[k]


class NpcDialog:
    CHARS_PER_SEC = 30

    # ── Layout ───────────────────────────────────────────────────────────
    _BOX_H   = 148          # text box height
    _PORT_W  = 208          # portrait width
    _PORT_H  = 288          # portrait height
    _PORT_X  = 16           # portrait left margin
    _NAME_H  = 36           # name tag height
    _BTN_W   = 125
    _BTN_H   = 36

    def __init__(self):
        self._open   = False
        self._text   = ""
        self._name   = ""
        self._shown  = 0.0
        self._done   = False
        self._sel    = 0
        self._result = None
        self._kind   = None
        self._anim_t = 0.0

        self._yr = pygame.Rect(0, 0, self._BTN_W, self._BTN_H)
        self._nr = pygame.Rect(0, 0, self._BTN_W, self._BTN_H)

        self._shop_img = None
        self._stor_img = None
        self._sfx      = None
        self._sfx_ch   = pygame.mixer.Channel(7)
        self._vol      = 1.0

        self._load_assets()

    #npc slika in zvok
    def _load_assets(self):
        def _img(path, size):
            try:
                if os.path.exists(path):
                    s = pygame.image.load(path).convert_alpha()
                    return pygame.transform.smoothscale(s, size)
            except Exception as e:
                print(f"NpcDialog img error ({path}): {e}")
            return None

        self._shop_img = _img(SHOP_NPC_IMG_PATH,    (self._PORT_W, self._PORT_H))
        self._stor_img = _img(STORAGE_NPC_IMG_PATH, (self._PORT_W, self._PORT_H))

        try:
            if os.path.exists(TEXT_SFX_PATH):
                self._sfx = pygame.mixer.Sound(TEXT_SFX_PATH)
        except Exception as e:
            print(f"NpcDialog sfx error: {e}")

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def is_open(self): return self._open

    @property
    def result(self): return self._result

    @property
    def kind(self): return self._kind

    def show(self, kind, text, name=None, vol=1.0):
        self._open   = True
        self._kind   = kind
        self._text   = text
        self._name   = name or ('Trgovec' if kind == 'shop' else 'Čuvaj')
        self._shown  = 0.0
        self._done   = False
        self._sel    = 0
        self._result = None
        self._anim_t = 0.0
        self._vol    = vol

    def close(self):
        self._open   = False
        self._result = None

    # ── Update ───────────────────────────────────────────────────────────

    def update(self, dt):
        if not self._open:
            return

        self._anim_t = min(1.0, self._anim_t + dt / 0.20)

        if self._done:
            return

        prev = int(self._shown)
        self._shown = min(float(len(self._text)), self._shown + self.CHARS_PER_SEC * dt)
        cur = int(self._shown)

        #loop in stop glasbe
        if cur > prev and self._sfx and not self._sfx_ch.get_busy():
            self._sfx.set_volume(max(0., min(1., 0.40 * self._vol)))
            self._sfx_ch.play(self._sfx, loops=-1)

        if cur >= len(self._text):
            self._sfx_ch.stop()
            self._done = True

    #input event handle

    def handle_event(self, ev):
        if not self._open:
            return False

        if ev.type == pygame.KEYDOWN:
            if not self._done:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                    self._shown = float(len(self._text))
                    self._sfx_ch.stop()
                    self._done  = True
                elif ev.key == pygame.K_ESCAPE:
                    self._sfx_ch.stop()
                    self._result = 'no'
                    self._open   = False
                return True

            if ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                self._sel = 1 - self._sel
                return True
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                self._result = 'yes' if self._sel == 0 else 'no'
                self._open   = False
                return True
            if ev.key == pygame.K_y:
                self._result = 'yes'
                self._open   = False
                return True
            if ev.key in (pygame.K_n, pygame.K_ESCAPE):
                self._result = 'no'
                self._open   = False
                return True

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self._done:
            if self._yr.collidepoint(ev.pos):
                self._result = 'yes'; self._open = False
            elif self._nr.collidepoint(ev.pos):
                self._result = 'no';  self._open = False

        return True

    # ── Draw ─────────────────────────────────────────────────────────────

    def _ease(self, t):
        t = max(0., min(1., t))
        return 1 - (1 - t) ** 3

    #nariše dve puščici desno od name tag-a (Persona 5 stil)
    def _draw_chevrons(self, screen, x, y_mid, count=2):
        ah    = 22    # total arrow height
        body  = 14    # body width before the tip
        tip   = 10    # tip extension
        notch = 8     # inner notch depth
        gap   = 10    # gap between arrows

        for i in range(count):
            ax = x + i * (body + tip + gap)
            yt = y_mid - ah // 2
            yb = y_mid + ah // 2
            pts = [
                (ax,                 yt),
                (ax + body,          yt),
                (ax + body + tip,    y_mid),
                (ax + body,          yb),
                (ax,                 yb),
                (ax + notch,         y_mid),
            ]
            pygame.draw.polygon(screen, (255, 255, 255), pts)

    def draw(self, screen):
        if not self._open:
            return

        ep  = self._ease(self._anim_t)
        BH  = self._BOX_H
        PW  = self._PORT_W
        PH  = self._PORT_H
        PX  = self._PORT_X
        NH  = self._NAME_H

        # Rest (final) positions
        box_y_rest  = HEIGHT - BH
        port_y_rest = HEIGHT - PH          # portrait bottom = screen bottom
        name_y_rest = box_y_rest - NH + 5  # name tag overlaps box top slightly

        # Slide-in animation (from below)
        slide  = int((1.0 - ep) * (BH + 70))
        box_y  = box_y_rest  + slide
        port_y = port_y_rest + slide
        name_y = name_y_rest + slide

        # ── Dark text box — full screen width ────────────────────────
        box_surf = pygame.Surface((WIDTH, BH), pygame.SRCALPHA)
        box_surf.fill((8, 6, 18, 242))
        pygame.draw.line(box_surf, (255, 255, 255, 160), (0, 1), (WIDTH, 1), 2)
        screen.blit(box_surf, (0, box_y))

        # ── Portrait — overlaps box, bottom-anchored ─────────────────
        port = self._shop_img if self._kind == 'shop' else self._stor_img
        if port:
            screen.blit(port, (PX, port_y))

        #ime
        name_fnt  = _fnt(20, bold=True)
        name_surf = name_fnt.render(self._name, True, (255, 255, 255))
        pad       = 14
        tag_w     = name_surf.get_width() + pad * 2
        tag_x     = PX + PW + 10

        tag_bg = pygame.Surface((tag_w, NH), pygame.SRCALPHA)
        tag_bg.fill((8, 6, 18, 248))
        pygame.draw.rect(tag_bg, (255, 255, 255, 200), tag_bg.get_rect(), 2)
        screen.blit(tag_bg, (tag_x, name_y))
        screen.blit(name_surf, (tag_x + pad,
                                name_y + (NH - name_surf.get_height()) // 2))

        # Chevron arrows to the right of name tag
        self._draw_chevrons(screen, tag_x + tag_w + 10, name_y + NH // 2, count=2)

        # ── Text area (right of portrait) ────────────────────────────
        tx = PX + PW + 24
        ty = box_y + 18
        tw = WIDTH - tx - 28

        # Button positions (used for height clamping)
        bw, bh  = self._BTN_W, self._BTN_H
        area_cx = tx + tw // 2
        btn_y   = box_y + BH - bh - 12
        self._yr = pygame.Rect(area_cx - bw - 10, btn_y, bw, bh)
        self._nr = pygame.Rect(area_cx + 10,       btn_y, bw, bh)

        th = (self._yr.y - ty - 4) if self._done else (BH - 26)
        self._draw_wrapped(screen, self._text[:int(self._shown)],
                           tx, ty, tw, max(20, th))

        #da ne gumba
        if self._done:
            mx, my = pygame.mouse.get_pos()
            for i, (rect, lbl) in enumerate([(self._yr, "DA  [Y]"), (self._nr, "NE  [N]")]):
                hov  = rect.collidepoint(mx, my)
                is_s = (i == self._sel)

                btn_s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                if is_s:
                    btn_s.fill((255, 255, 255, 178))
                elif hov:
                    btn_s.fill((80, 68, 100, 195))
                else:
                    btn_s.fill((22, 16, 36, 210))
                pygame.draw.rect(btn_s,
                                 (200, 200, 200, 160) if is_s else (85, 75, 110, 200),
                                 btn_s.get_rect(), 2, border_radius=8)
                screen.blit(btn_s, rect.topleft)

                tc = (8, 6, 20) if is_s else (220, 220, 255)
                ts = _fnt(17, bold=True).render(lbl, True, tc)
                screen.blit(ts, (rect.centerx - ts.get_width() // 2,
                                 rect.centery - ts.get_height() // 2))

        elif ep > 0.55:
            hs = _fnt(12).render("[ E / Space ]  preskoči", True, (110, 108, 142))
            screen.blit(hs, (WIDTH - hs.get_width() - 18,
                              box_y + BH - hs.get_height() - 10))

    #prelom vrstic in ...
    def _draw_wrapped(self, screen, text, x, y, max_w, max_h):
        fnt   = _fnt(17)
        lh    = fnt.get_height() + 5
        words = text.split(' ')
        lines, cur = [], ''
        for w in words:
            test = (cur + ' ' + w).strip()
            if fnt.size(test)[0] <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        for i, line in enumerate(lines):
            fy = y + i * lh
            if fy + lh > y + max_h:
                s = fnt.render("...", True, (135, 130, 170))
                screen.blit(s, (x, max(y, fy - lh)))
                break
            screen.blit(fnt.render(line, True, (235, 232, 255)), (x, fy))
