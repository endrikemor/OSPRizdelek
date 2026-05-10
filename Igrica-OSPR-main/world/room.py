"""Room generation and tile rendering."""
import os, math, pygame, random
from settings import *
from items import Item, NORMAL_DROP, RARE_DROP

T_WALL  = 0
T_FLOOR = 1

RT_NORMAL   = "normal"
RT_BOSS     = "boss"
RT_SHOP     = "shop"
RT_TREASURE = "treasure"
RT_START    = "start"
RT_MAZE     = "maze"

# ── Tileset ──────────────────────────────────────────────────────────
_TS  = None   # pygame.Surface or False
_TC  = {}     # (tx, ty) → scaled Surface
_SRC = 16     # source tile size in px

def _load_ts():
    global _TS
    if _TS is not None:
        return None if _TS is False else _TS
    path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), '..', 'assets', 'images', 'tiles', 'tiles.png'))
    try:
        _TS = pygame.image.load(path).convert_alpha()
    except Exception:
        _TS = False
    return None if _TS is False else _TS

def _tile(tx, ty):
    """Return tile at tileset grid (tx, ty) scaled to TILE×TILE, or None."""
    if (tx, ty) in _TC:
        return _TC[(tx, ty)]
    sheet = _load_ts()
    if sheet is None:
        _TC[(tx, ty)] = None
        return None
    buf = pygame.Surface((_SRC, _SRC), pygame.SRCALPHA)
    buf.blit(sheet, (0, 0), (tx * _SRC, ty * _SRC, _SRC, _SRC))
    out = pygame.transform.scale(buf, (TILE, TILE))
    _TC[(tx, ty)] = out
    return out

# Tileset layout (16×16 source tiles):
#   Wall autotile : cols 0-5, rows 0-5  (6×6 grid)
#   Floor autotile: cols 6-9, rows 0-2  (4×3 grid, starts at px 96)
#
# Wall tile selection:
#   row 0 → top-cap  (floor to south  → top face visible)
#   row 2 → body     (surrounded by walls)
#   row 5 → bot-cap  (floor to north  → bottom edge)
#   col 0 → left edge (floor to west)
#   col 5 → right edge(floor to east)

def _wall_coords(tiles, row, col):
    """Return (tx, ty) tileset grid coords for wall at (row, col)."""
    H, W = len(tiles), len(tiles[0])

    def floor_at(dr, dc):
        r2, c2 = row + dr, col + dc
        if r2 < 0 or r2 >= H or c2 < 0 or c2 >= W:
            return False
        return tiles[r2][c2] == T_FLOOR

    fs = floor_at(+1, 0)   # floor to south (below)
    fn = floor_at(-1, 0)   # floor to north (above)
    fw = floor_at(0, -1)   # floor to west  (left)
    fe = floor_at(0, +1)   # floor to east  (right)

    if fs:
        # Top face of wall is visible
        if fw and not fe:  return (0, 0)   # top-left corner cap
        if fe and not fw:  return (5, 0)   # top-right corner cap
        return (3, 0)                       # top center strip
    if fn:
        return (3, 5)                       # bottom cap
    if fw and not fe:
        return (0, 2)                       # left-edge face
    if fe and not fw:
        return (5, 2)                       # right-edge face
    return (3, 2)                           # solid interior


def _build_tile_surface(tiles, doors):
    surf = pygame.Surface((ROOM_W * TILE, ROOM_H * TILE))
    surf.fill(WALL_CLR)
    ts_ok = _load_ts() is not None

    for row in range(ROOM_H):
        for col in range(ROOM_W):
            rx, ry = col * TILE, row * TILE

            if tiles[row][col] == T_FLOOR:
                if ts_ok:# dve vrsti tile-da ni vse isto
                    ftx = 6 + ((row + col) % 2)
                    t = _tile(ftx, 0)
                    if t:
                        surf.blit(t, (rx, ry))
                        continue
                # Fallback solid colour
                shade = 8 if (row + col) % 2 == 0 else 0
                fc = tuple(max(0, c - shade) for c in FLOOR_CLR)
                pygame.draw.rect(surf, fc, (rx, ry, TILE, TILE))
                pygame.draw.rect(surf, tuple(max(0, c - 18) for c in fc),
                                 (rx, ry, TILE, TILE), 1)
            else:
                if ts_ok:
                    tx, ty = _wall_coords(tiles, row, col)
                    t = _tile(tx, ty)
                    if t:
                        surf.blit(t, (rx, ry))
                        continue
                # Fallback solid colour
                pygame.draw.rect(surf, WALL_CLR, (rx, ry, TILE, TILE))
                pygame.draw.rect(surf, tuple(min(255, c + 22) for c in WALL_CLR),
                                 (rx, ry, TILE, 6))
                pygame.draw.rect(surf, tuple(max(0, c - 10) for c in WALL_CLR),
                                 (rx, ry + TILE - 4, TILE, 4))

    # vrata
    door_col = DOOR_OPEN
    half     = TILE * 2
    mid_col  = (ROOM_W // 2) * TILE - TILE

    if doors.get("N"):
        pygame.draw.rect(surf, door_col, (mid_col, 0, half, TILE))
        pygame.draw.rect(surf, GOLD,     (mid_col, 0, half, 4))
    if doors.get("S"):
        pygame.draw.rect(surf, door_col, (mid_col, (ROOM_H - 1) * TILE, half, TILE))
        pygame.draw.rect(surf, GOLD,     (mid_col, (ROOM_H - 1) * TILE, half, 4))

    return surf


def _draw_torch(screen, sx, sy, t):
    """Draw an animated wall torch at screen position (sx, sy)."""
    flicker = 0.85 + 0.15 * math.sin(t * 9.3 + sx * 0.07)

    #glow
    gr = int(52 * flicker)
    glow = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 130, 0, 35), (gr, gr), gr)
    screen.blit(glow, (sx - gr, sy - gr))

    #una svetilka al neki
    pygame.draw.rect(screen,(90, 55, 18),(sx - 3, sy - 14, 6, 14))
    pygame.draw.rect(screen,(120, 80, 30), (sx - 2, sy - 13, 4, 11))

    #kres
    fh = int(11 * flicker)
    fw2 = int(8 * flicker)
    pygame.draw.ellipse(screen, (255, 180, 0),
                        (sx - fw2 // 2, sy - 14 - fh, fw2, fh + 2))
    pygame.draw.ellipse(screen, (255, 80, 0),
                        (sx - fw2 // 2 + 1, sy - 13 - fh + 2, fw2 - 2, fh - 1))


class Room:
    def __init__(self, rtype=RT_NORMAL, stage=1,
                 diff="Medium", diff_m=1.0, has_north=False, has_south=False):
        self.rtype   = rtype
        self.stage   = stage
        self.diff    = diff
        self.diff_m  = diff_m
        self.tiles   = [[T_WALL] * ROOM_W for _ in range(ROOM_H)]
        self.enemies = []
        self.items   = []
        self.cleared = (rtype in (RT_SHOP, RT_TREASURE, RT_START))
        self.visited = False
        self.doors   = {"N": has_north, "S": has_south}
        self._surf   = None
        self._dirty  = True
        self.shop_stock = []
        self.torches    = []
        self._generate()

    def _generate(self): #Notranjost spremeni v tla
        if self.rtype != RT_MAZE:
            for r in range(1, ROOM_H - 1):
                for c in range(1, ROOM_W - 1):
                    self.tiles[r][c] = T_FLOOR
        self._carve_doors()

        if self.rtype == RT_NORMAL:
            self._add_obstacles()
            self._spawn_enemies()
            if random.random() < 0.3:
                self._drop_items(NORMAL_DROP, count=random.randint(1, 2))
        elif self.rtype == RT_BOSS:
            self._add_obstacles(count=2)
            self._spawn_boss()
        elif self.rtype == RT_TREASURE:
            self._drop_items(RARE_DROP, count=3)
        elif self.rtype == RT_SHOP:
            from items import RUN_SHOP_STOCK
            self.shop_stock = list(RUN_SHOP_STOCK)
        elif self.rtype == RT_MAZE:
            self._add_maze()

    def _add_maze(self):#tukaj se ustvari labirint z algoritmom recursive backtracking... In je čisi AI.
        """Recursive-backtracking maze: 4×2 cell grid, 3-tile corridors, 2-tile walls.

        Cell (cx,cy): rows 1+cy*5..3+cy*5, cols 1+cx*5..3+cx*5.
        Door mid cols (9,10) align with the wall between cx=1 and cx=2.
        """
        MZ_W, MZ_H = 4, 2
        CELL, WALL  = 3, 2
        STEP        = CELL + WALL   # 5 tiles per unit
        H, W = ROOM_H, ROOM_W
        visited = [[False] * MZ_W for _ in range(MZ_H)]

        def ok(r, c):
            return 0 < r < H - 1 and 0 < c < W - 1

        def carve_cell(cy, cx):
            r0, c0 = 1 + cy * STEP, 1 + cx * STEP
            for dr in range(CELL):
                for dc in range(CELL):
                    if ok(r0 + dr, c0 + dc):
                        self.tiles[r0 + dr][c0 + dc] = T_FLOOR

        def carve_link(cy, cx, ny, nx):
            if nx > cx:
                r0, c0, rows, cols=1+cy*STEP,1+cx*STEP+CELL,CELL,WALL
            elif nx < cx:
                r0, c0, rows, cols = 1 + cy*STEP, 1 + nx*STEP + CELL, CELL, WALL
            elif ny > cy:
                r0, c0, rows, cols = 1 + cy*STEP + CELL, 1 + cx*STEP, WALL, CELL
            else:
                r0,c0,rows,cols=1+ny*STEP+CELL, 1+cx*STEP,WALL,CELL
            for dr in range(rows):
                for dc in range(cols):
                    if ok(r0+dr,c0+dc):
                        self.tiles[r0+dr][c0+dc]=T_FLOOR

        def dfs(cy, cx):#funkcija za izdelavo labirinta.
            visited[cy][cx] = True
            carve_cell(cy, cx)
            nbrs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            random.shuffle(nbrs)
            for dy, dx in nbrs:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny<MZ_H and 0<=nx<MZ_W and not visited[ny][nx]:
                    carve_link(cy, cx, ny, nx)
                    dfs(ny, nx)

        dfs(random.randint(0, MZ_H - 1), random.randint(0, MZ_W - 1))

        # Cols 9-10 = wall between cx=1 and cx=2; force-open in both corridors
        if self.doors.get("N"):
            for r in range(1, 1 + CELL):                          # rows 1-3
                self.tiles[r][9]=self.tiles[r][10]=T_FLOOR
        if self.doors.get("S"):
            for r in range(1+STEP,1+STEP+CELL):            # rows 6-8
                if ok(r, 9):
                    self.tiles[r][9]=self.tiles[r][10]=T_FLOOR

        # Torches on walls whose south neighbour is floor
        for r in range(1, H - 2):
            for c in range(1, W - 1):
                if (self.tiles[r][c] == T_WALL
                        and self.tiles[r + 1][c] == T_FLOOR
                        and random.random() < 0.10):
                    self.torches.append(
                        (c * TILE + TILE // 2, r * TILE + TILE - 8))

        self._spawn_enemies()
        if random.random() < 0.35:
            self._drop_items(NORMAL_DROP, count=random.randint(1, 2))
        self._dirty = True

    def _carve_doors(self):
        mid = ROOM_W // 2 - 1
        if self.doors.get("N"):
            self.tiles[0][mid] = T_FLOOR; self.tiles[0][mid + 1] = T_FLOOR
        if self.doors.get("S"):
            self.tiles[ROOM_H - 1][mid] = T_FLOOR; self.tiles[ROOM_H - 1][mid + 1] = T_FLOOR

    def _add_obstacles(self, count=None):#doda ovire
        n = count if count is not None else random.randint(2, 7)
        for _ in range(n):
            c = random.randint(3, ROOM_W - 4); r = random.randint(2, ROOM_H - 3)
            self.tiles[r][c] = T_WALL
            if random.random() < 0.45:#45% da se okoli ovire pojavi še ena
                nc = c + random.choice([-1, 1]); nr = r + random.choice([-1, 1])
                if 2 <= nc < ROOM_W - 2 and 2 <= nr < ROOM_H - 2:
                    self.tiles[nr][nc] = T_WALL
        self._dirty = True

    def _spawn_enemies(self):#doda enemy-je glede na stage in težavnost 
        from entities import Slime, Skeleton, Orc
        count = random.randint(3, 5) + min(self.stage // 3, 4)
        pool  = ["slime"] * 3 + ["skeleton"] * 2 + ["orc"]
        if self.stage >= 5:
            pool += ["orc", "skeleton"]
        for _ in range(count):
            etype = random.choice(pool)
            c,r=self._random_floor_tile(margin=3) #funkcija ki izbere random ploščico ki ni stena, ipd.
            x=c * TILE + TILE // 2; y = r * TILE + TILE // 2
            cls={"slime": Slime, "skeleton": Skeleton, "orc": Orc}[etype]
            self.enemies.append(cls(x, y, self.diff_m))

    def _spawn_boss(self):
        from entities import Boss
        x=(ROOM_W // 2)*TILE + TILE // 2
        y=(ROOM_H // 2)*TILE + TILE // 2
        self.enemies.append(Boss(x, y, self.diff_m, self.stage))

    def _drop_items(self, pool, count=1):
        for _ in range(count):
            itype = random.choice(pool)
            c, r  = self._random_floor_tile(margin=3)
            self.items.append(Item(c*TILE+TILE//2, r*TILE +TILE//2, itype))

    def _random_floor_tile(self, margin=2):#ta funkcija izbira naključne ploščice ki nis stena,itd.
        for _ in range(200):
            c = random.randint(margin, ROOM_W-margin-1)
            r = random.randint(margin, ROOM_H-margin-1)
            if self.tiles[r][c]==T_FLOOR:
                return c, r
        return ROOM_W//2, ROOM_H//2

    def get_walls(self):
        return [pygame.Rect(col * TILE, row * TILE, TILE, TILE)
                for row in range(ROOM_H)
                for col in range(ROOM_W)
                if self.tiles[row][col] == T_WALL]

    def check_cleared(self):
        if not self.cleared:
            if all(not e.alive for e in self.enemies):
                self.cleared = True
                self._drop_reward()
        return self.cleared

    def _drop_reward(self):
        if self.rtype != RT_NORMAL: return
        pool  = RARE_DROP if random.random() < 0.25 else NORMAL_DROP
        count = random.randint(1, 2)
        for _ in range(count):
            itype = random.choice(pool)
            c, r  = self._random_floor_tile(margin=3)
            self.items.append(Item(c * TILE + TILE // 2, r * TILE + TILE // 2, itype))

    def get_surface(self):
        if self._surf is None or self._dirty:
            self._surf  = _build_tile_surface(self.tiles, self.doors)
            self._dirty = False
        return self._surf

    def draw(self, screen, offset=(0, 0)):
        ox, oy = offset
        screen.blit(self.get_surface(), (-ox, -oy))
        for item in self.items:
            item.draw(screen, offset)
        for enemy in self.enemies: 
            enemy.draw(screen, offset)
        if self.torches:
            t = pygame.time.get_ticks() / 1000.0
            for tx, ty in self.torches:
                sx, sy = tx - ox, ty - oy
                if -TILE <= sx <= WIDTH + TILE and -TILE <= sy <= GAME_H + TILE:
                    _draw_torch(screen, sx, sy, t)

    def update(self, dt, player, walls):
        for enemy in self.enemies: 
            enemy.update(dt, player, walls)
        for item  in self.items:   
            item.update(dt)
