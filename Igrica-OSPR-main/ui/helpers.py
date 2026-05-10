import pygame
from settings import *

_FONTS: dict = {}

#shranjuje zelene fonte
def font(size: int, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return _FONTS[key]

#izris besedila na zelen center
def draw_text(surf, text, x, y, size=20, color=WHITE, bold=False, center=False):
    s = font(size, bold).render(str(text), True, color)
    if center:
        x -= s.get_width() // 2
    surf.blit(s, (x, y))
    return s.get_width()

#zaobljen panel
def draw_panel(surf, rect, bg=(30, 24, 44), border=ACCENT, radius=8, alpha=220):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*bg, alpha),   s.get_rect(), border_radius=radius)
    pygame.draw.rect(s, (*border, 220), s.get_rect(), 2, border_radius=radius)
    surf.blit(s, rect.topleft)

#dodaj v inv
def add_to_inv(player, itm):
    max_slots = getattr(player, "max_inv_slots", INV_SLOTS_START)
    if itm.stack:
        for ex in player.inventory:
            if ex.itype == itm.itype and ex.count < INV_STACK_MAX:
                ex.count += 1
                return
    if len(player.inventory) < max_slots:
        player.inventory.append(itm)
