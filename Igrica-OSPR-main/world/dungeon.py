import random
from settings import *
from .room import Room, RT_NORMAL, RT_BOSS, RT_SHOP, RT_TREASURE, RT_START, RT_MAZE


class Dungeon:
    def __init__(self, difficulty="Medium", start_class="Knight"):
        cfg             = DIFFICULTY[difficulty]
        self.diff       = difficulty
        self.diff_m     = cfg["hp_m"]
        self.gold_m     = cfg["gold_m"]
        self.max_stages = cfg["stages"]
        self.start_class= start_class
        self.rooms      = []
        self.current    = 0
        self._build()

    #random generacija sob
    def _build(self):
        n = self.max_stages
        for i in range(n):
            has_n = (i > 0)
            has_s = (i < n - 1)

            if   i == 0:        rtype = RT_START
            elif i == n - 1:    rtype = RT_BOSS
            elif i % 4 == 3:    rtype = RT_SHOP      #vsaka 4. soba je shop
            elif i % 5 == 4:    rtype = RT_TREASURE   #vsaka 5. je zakladnica
            elif random.random() < 0.30: rtype = RT_MAZE
            else:               rtype = RT_NORMAL

            self.rooms.append(Room(
                rtype     = rtype,
                stage     = i + 1,
                diff      = self.diff,
                diff_m    = self.diff_m,
                has_north = has_n,
                has_south = has_s,
            ))

    #trenutna soba
    @property
    def room(self) -> Room:
        return self.rooms[self.current]

    #ali v zadnji sobi
    @property
    def is_last(self) -> bool:
        return self.current >= len(self.rooms) - 1

    def next_room(self):
        if not self.is_last:
            self.current += 1
            self.room.visited = True

    def prev_room(self):
        if self.current > 0:
            self.current -= 1

    #minimap
    def get_minimap_data(self):
        return [
            (i, r.rtype, r.visited or i <= self.current, i == self.current)
            for i, r in enumerate(self.rooms)
        ]
