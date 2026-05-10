import pygame
from settings import *
from ..ui.helpers import draw_text, draw_panel, font


class SkillTreeUI:
    def __init__(self):
        self.open = False
        self.sel  = 0

    def toggle(self):
        self.open = not self.open

    def handle_event(self, ev, player):
        if not self.open: return False
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_k, pygame.K_ESCAPE):
                self.open = False
                return True
            tree = SKILL_TREES.get(player.cls, [])
            n    = len(tree)
            if ev.key == pygame.K_RIGHT: self.sel = (self.sel + 1) % max(1, n)
            if ev.key == pygame.K_LEFT:  self.sel = (self.sel - 1) % max(1, n)
            if ev.key in (pygame.K_RETURN, pygame.K_u):
                if 0 <= self.sel < n:
                    player.unlock_skill(tree[self.sel]["id"])
                return True
        return True

    def draw(self, screen, player):
        if not self.open: return
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 175))
        screen.blit(ov, (0, 0))

        pw = 820; ph = 500
        px = WIDTH // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2

        draw_panel(screen, pygame.Rect(px, py, pw, ph), bg=(16, 10, 28), border=PURPLE)
        draw_text(screen, f"SKILL TREE  –  {player.cls}",
                  px + pw // 2, py + 12, 22, PURPLE, bold=True, center=True)
        draw_text(screen, f"Skill Points: {player.skill_points}  Level: {player.level}",
                  px + pw // 2, py + 40, 15, GOLD, bold=True, center=True)
        draw_text(screen, "[</> ] Select   [U] Unlock   [K] Close",
                  px + pw // 2, py + 62, 12, GRAY, center=True)

        tree = SKILL_TREES.get(player.cls, [])
        sw   = 270; sh = 108; gapx = 36; gapy = 16
        COLS = 2
        grid_w = COLS * sw + (COLS - 1) * gapx
        gx0    = px + pw // 2 - grid_w // 2
        gy0    = py + 90

        # connector lines
        for skill in tree:
            req = skill.get("req")
            if req:
                parent = next((s for s in tree if s["id"] == req), None)
                if parent:
                    x1 = gx0 + parent["col"] * (sw + gapx) + sw // 2
                    y1 = gy0 + parent["row"] * (sh + gapy) + sh
                    x2 = gx0 + skill["col"]  * (sw + gapx) + sw // 2
                    y2 = gy0 + skill["row"]  * (sh + gapy)
                    lc = GREEN if req in player.unlocked_skills else (55, 45, 75)
                    pygame.draw.line(screen, lc, (x1, y1), (x2, y2), 2)

        for i, skill in enumerate(tree):
            bx   = gx0 + skill["col"] * (sw + gapx)
            by_  = gy0 + skill["row"] * (sh + gapy)
            unlocked = skill["id"] in player.unlocked_skills
            req      = skill.get("req")
            can      = (not unlocked and player.skill_points >= skill["cost"]
                        and (req is None or req in player.unlocked_skills))
            sel = (i == self.sel)

            if unlocked:   bg = (28, 55, 28); brd = GREEN
            elif sel:      bg = (55, 44, 80); brd = GOLD
            elif can:      bg = (38, 28, 56); brd = PURPLE
            else:          bg = (18, 14, 28); brd = (48, 38, 62)

            draw_panel(screen, pygame.Rect(bx, by_, sw, sh), bg=bg, border=brd, radius=10)
            tc = GREEN if unlocked else WHITE if can else GRAY
            draw_text(screen, skill["name"], bx + sw // 2, by_ + 8,  15, tc, bold=True, center=True)
            draw_text(screen, skill["desc"], bx + sw // 2, by_ + 30, 11, LIGHT_GRAY, center=True)
            tag_col = CYAN if skill["stype"] == "active" else YELLOW
            draw_text(screen, skill["stype"].upper(), bx + 10, by_ + 54, 10, tag_col)

            if unlocked:
                draw_text(screen, "UNLOCKED", bx + sw // 2, by_ + 70, 11, GREEN, bold=True, center=True)
            else:
                draw_text(screen, f"Cost: {skill['cost']} SP", bx + sw - 70, by_ + 70,
                          11, GOLD if can else GRAY)
                if req:
                    pname = next((s["name"] for s in tree if s["id"] == req), "?")
                    draw_text(screen, f"Req: {pname[:14]}", bx + 10, by_ + 70, 10, GRAY)
            if sel and not unlocked:
                draw_text(screen, "[U] Unlock", bx + sw // 2, by_ + sh - 16,
                          11, GOLD if can else RED, center=True)

        draw_text(screen, "Hotbar:", px + 14, py + ph - 56, 13, LIGHT_GRAY)
        for i, sid in enumerate(player.active_skills):
            bx2 = px + 90 + i * 120
            by2 = py + ph - 62
            draw_panel(screen, pygame.Rect(bx2, by2, 112, 44), bg=(26, 18, 40), border=ACCENT)
            draw_text(screen, f"[{i + 1}]", bx2 + 6, by2 + 4, 11, GRAY)
            if sid:
                sdata = next((s for s in tree if s["id"] == sid), None)
                draw_text(screen, sdata["name"] if sdata else sid,
                          bx2 + 56, by2 + 12, 11, CYAN, center=True)
            else:
                draw_text(screen, "empty", bx2 + 56, by2 + 12, 10, GRAY, center=True)
