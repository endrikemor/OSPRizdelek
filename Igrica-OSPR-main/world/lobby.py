"""Lobby world — lobby_bg.png / lobby.png background z definiranimi barrierji."""
import pygame, math, os
from settings import *

try:
    from .room import T_WALL, T_FLOOR
except ImportError:
    from world.room import T_WALL, T_FLOOR

class Lobby:
    def __init__(self):
        # Inicializiramo celo mapo s tlemi
        self.tiles = [[T_FLOOR] * LOBBY_W for _ in range(LOBBY_H)]
        self._build()
        self._surf = None
        self.lobby_image = pygame.image.load(os.path.join(IMAGES_DIR, "lobby.png")).convert()

    def _build(self):
        # 1. Zunanji robovi (Stene na čisto vseh robovih mape)
        for r in range(LOBBY_H):
            for c in range(LOBBY_W):
                if r == 0 or r == LOBBY_H - 1 or c == 0 or c == LOBBY_W - 1:
                    self.tiles[r][c] = T_WALL

        # 2. Trgovina levo (Pult in stena)
        for r in range(2, 7): 
            self.tiles[r][1] = T_WALL
        for c in range(1, 8):
            self.tiles[6][c] = T_WALL
        for r in range(4, 7):
            self.tiles[r][7] = T_WALL

        # 3. Portal v sredini (Lok in vstop)
        # Vodoravna linija pred portalom
        for c in range(6, 12):
            self.tiles[4][c] = T_WALL
        # Stranski stebri portala
        for r in range(1, 5):
            self.tiles[r][6] = T_WALL
            self.tiles[r][11] = T_WALL

        # 4. Skrinje in prehod desno
        for c in range(11, 15):
            self.tiles[4][c] = T_WALL
        for r in range(4, 6):
            self.tiles[r][15] = T_WALL
        for c in range(15, 20):
            self.tiles[5][c] = T_WALL

        # 5. Miza s knjigo (Vertikalna bariera na desni)
        for r in range(6, 12):
            self.tiles[r][19] = T_WALL

        # 6. Sodi spodaj (Samo tam, kjer so dejansko sodi)
        self.tiles[10][12] = T_WALL
        self.tiles[10][13] = T_WALL

    def get_walls(self):
        """Vrne seznam Rect-ov za kolizijo."""
        return [
            pygame.Rect(col*TILE, row*TILE, TILE, TILE)
            for row in range(LOBBY_H)
            for col in range(LOBBY_W)
            if self.tiles[row][col] == T_WALL
        ]

    def _build_surface(self):
        W, H = LOBBY_W * TILE, LOBBY_H * TILE
        return pygame.transform.scale(self.lobby_image, (W, H))

    def get_surface(self):
        if self._surf is None:
            self._surf = self._build_surface()
        return self._surf

    def draw(self, screen, offset=(0, 0)):
        ox, oy = offset
        # Izris osnovne slike lobbyja
        screen.blit(self.get_surface(), (-ox, -oy))
        
        # --- DEBUG RISANJE BARRIERJEV ---
        # Ko boš zadovoljen, lahko spodnji del pobrišeš.
        for wall in self.get_walls():
            debug_rect = wall.move(-ox, -oy)