#HUD — hp/stamina/xp vrstice, zlato, stage info in cooldown kartice za skille
import pygame
from settings import (WIDTH, GAME_H, HUD_H, DASH_CD, SKILL_TREES)

_FC = {}
def _fnt(sz, bold=False):
    k = (sz, bold)
    if k not in _FC:
        for n in ("Nunito", "Segoe UI", "Verdana", None):
            try: _FC[k] = pygame.font.SysFont(n, sz, bold=bold); break
            except: pass
    return _FC[k]

#cooldown
_SKILL_MAX_CD = {}
_SKILL_LABEL  = {}
for _tree in SKILL_TREES.values():
    for _s in _tree:
        if _s.get('cd', 0) > 0:
            _SKILL_MAX_CD[_s['id']] = _s['cd']
            _SKILL_LABEL[_s['id']]  = _s['name'].upper()


class HUD:
    _CARD_W   = 176
    _CARD_H   = 40
    _CARD_GAP = 5
    _FADE_SPD = 7.0   # alpha units per second (0 → 1 scale)

    def __init__(self):
        self._cds     = {}   # key → {label, max, rem, alpha(0..1), dying}
        self._last_ms = None

    #sledi cooldownu — doda/posodobi/označi kot "dying" ko se izteče
    def _track(self, key, label, cd, max_cd):
        if cd > 0:
            if key not in self._cds:
                self._cds[key] = {
                    'label': label, 'max': max_cd,
                    'rem': cd, 'alpha': 0.0, 'dying': False,
                }
            else:
                self._cds[key]['rem']   = cd
                self._cds[key]['dying'] = False
        elif key in self._cds and not self._cds[key]['dying']:
            self._cds[key]['dying'] = True
            self._cds[key]['rem']   = 0.0

    def _update(self, dt, player):
        self._track('dash', 'DASH', player.dash_cd, DASH_CD)
        for sid, cd in player.skill_cds.items():
            if sid in _SKILL_MAX_CD:
                self._track(sid, _SKILL_LABEL.get(sid, sid.upper()), cd, _SKILL_MAX_CD[sid])

        for key in list(self._cds.keys()):
            info = self._cds[key]
            if info['dying']:
                info['alpha'] -= self._FADE_SPD * dt
                if info['alpha'] <= 0:
                    del self._cds[key]
            else:
                info['alpha'] = min(1.0, info['alpha'] + self._FADE_SPD * dt)

   
    #nacrt
    def draw(self, screen, player, stage=0, max_stage=0, room_type="normal"):
        # internal dt so dungeon_scene doesn't need to call update() separately
        now = pygame.time.get_ticks()
        dt  = min((now - self._last_ms) / 1000., 0.05) if self._last_ms else 0.016
        self._last_ms = now
        self._update(dt, player)

        #sam HUD
        pygame.draw.rect(screen, (9, 7, 18), (0, GAME_H, WIDTH, HUD_H))
        sep = pygame.Surface((WIDTH, 2), pygame.SRCALPHA)
        sep.fill((255, 255, 255, 35))
        screen.blit(sep, (0, GAME_H))

        #HP bar
        BAR_W, BAR_H = 204, 17
        bx = 42
        by = GAME_H + 11

        hp_pct = max(0.0, player.hp / player.max_hp)
        hp_col = (55, 200, 75) if hp_pct > 0.50 else \
                 (190, 200, 45) if hp_pct > 0.25 else (200, 60, 45)

        lbl = _fnt(15, bold=True).render("HP", True, (170, 165, 188))
        screen.blit(lbl, (bx - 30, by))
        pygame.draw.rect(screen, (12, 38, 16), (bx, by, BAR_W, BAR_H), border_radius=4)
        if hp_pct > 0:
            pygame.draw.rect(screen, hp_col,
                             (bx, by, int(BAR_W * hp_pct), BAR_H), border_radius=4)
        pygame.draw.rect(screen, (55, 90, 60), (bx, by, BAR_W, BAR_H), 1, border_radius=4)
        hp_txt = _fnt(13, bold=True).render(f"{int(player.hp)} / {player.max_hp}", True, (230, 255, 232))
        screen.blit(hp_txt, (bx + BAR_W // 2 - hp_txt.get_width() // 2, by + 1))

        #Stamina bar
        sy  = by + BAR_H + 5
        SH  = 13
        st_pct = max(0.0, player.stamina / player.max_stamina)

        lbl2 = _fnt(15, bold=True).render("ST", True, (170, 165, 188))
        screen.blit(lbl2, (bx - 30, sy))
        pygame.draw.rect(screen, (10, 22, 40), (bx, sy, BAR_W, SH), border_radius=3)
        if st_pct > 0:
            pygame.draw.rect(screen, (55, 175, 215),
                             (bx, sy, int(BAR_W * st_pct), SH), border_radius=3)
        pygame.draw.rect(screen, (45, 62, 82), (bx, sy, BAR_W, SH), 1, border_radius=3)
        st_txt = _fnt(11, bold=True).render(f"{int(player.stamina)} / {player.max_stamina}", True, (210, 238, 248))
        screen.blit(st_txt, (bx + BAR_W // 2 - st_txt.get_width() // 2, sy + 1))

        # ── XP bar (thin) ─────────────────────────────────────────────
        xy     = sy + SH + 6
        xp_pct = max(0.0, player.xp / max(1, player.xp_to_next))
        pygame.draw.rect(screen, (18, 14, 32), (bx, xy, BAR_W, 5), border_radius=2)
        if xp_pct > 0:
            pygame.draw.rect(screen, (118, 72, 210),
                             (bx, xy, int(BAR_W * xp_pct), 5), border_radius=2)
        lv_s = _fnt(11).render(f"Lv. {player.level}", True, (128, 108, 195))
        screen.blit(lv_s, (bx + BAR_W + 7, xy - 1))

        #gold
        gx = bx + BAR_W + 54
        g_s = _fnt(18, bold=True).render(f"◆  {player.gold}", True, (215, 185, 55))
        screen.blit(g_s, (gx, GAME_H + 16))
        cl_s = _fnt(12).render(player.cls, True, (95, 90, 115))
        screen.blit(cl_s, (gx, GAME_H + 44))

        #Stage
        if stage > 0:
            st_s = _fnt(18, bold=True).render(
                f"Stage  {stage} / {max_stage}", True, (225, 222, 248))
            screen.blit(st_s, (WIDTH // 2 - st_s.get_width() // 2, GAME_H + 13))
            rt_s = _fnt(12).render(room_type.upper(), True, (110, 105, 148))
            screen.blit(rt_s, (WIDTH // 2 - rt_s.get_width() // 2, GAME_H + 40))

        #cooldown
        self._draw_cards(screen)

    def _draw_cards(self, screen):
        if not self._cds:
            return

        cw, ch = self._CARD_W, self._CARD_H
        rx = WIDTH - cw - 14          # right-aligned
        entries = list(self._cds.values())

        for i, info in enumerate(entries):
            a01 = info['alpha']
            if a01 <= 0:
                continue

            cy = GAME_H - 40 - (i + 1) * (ch + self._CARD_GAP)

            # progress: 0 = just started, 1 = cooldown done
            pct = 1.0 - (info['rem'] / info['max']) if info['max'] > 0 else 1.0
            pct = max(0.0, min(1.0, pct))

            ai = int(a01 * 255)

            #bacground
            card = pygame.Surface((cw, ch), pygame.SRCALPHA)
            card.fill((8, 6, 18, int(a01 * 215)))
            # top white accent line
            pygame.draw.line(card, (255, 255, 255, int(a01 * 100)),
                             (0, 0), (cw, 0), 1)
            screen.blit(card, (rx, cy))

            #ime
            nm_s = _fnt(12, bold=True).render(info['label'], True, (218, 215, 238))
            nm_s.set_alpha(ai)
            screen.blit(nm_s, (rx + 9, cy + 7))

            #stanje
            if info['dying']:
                rem_txt = "READY"
                rem_col = (100, 215, 110)
            else:
                rem_txt = f"{info['rem']:.1f}s"
                rem_col = (185, 182, 210)
            tm_s = _fnt(11).render(rem_txt, True, rem_col)
            tm_s.set_alpha(ai)
            screen.blit(tm_s, (rx + cw - tm_s.get_width() - 9, cy + 8))

            # ── fill bar (white, fills left→right as cooldown recovers) ──
            bx2 = rx + 9
            by2 = cy + ch - 11
            bw2 = cw - 18
            bh2 = 5

            bg2 = pygame.Surface((bw2, bh2), pygame.SRCALPHA)
            bg2.fill((38, 35, 55, int(a01 * 200)))
            screen.blit(bg2, (bx2, by2))

            if pct > 0:
                fw = max(1, int(bw2 * pct))
                fill = pygame.Surface((fw, bh2), pygame.SRCALPHA)
                fill.fill((255, 255, 255, int(a01 * 235)))
                screen.blit(fill, (bx2, by2))
