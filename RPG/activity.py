import math
import random

from RPG import item
from RPG import user


class Activity:

    def __init__(self, hunger: float = 0) -> None:
        self.hunger = hunger


class Mining(Activity):

    def __init__(self, hunger: int = 0.2, durability_cost: int = 1) -> None:
        super().__init__(hunger)
        self.durability_cost = durability_cost

    async def mine(self, user: user.User, tool: item.Tool) -> list[item.Item]:
        if tool not in user.inventory: raise Exception('Item does not exists')
        if tool.type != 'Tool': raise Exception('Wrong tool')
        if user.saturation.level - self.hunger < user.saturation.min: raise Exception('Not enough saturation')
        L = list()
        for ore in await user.position.get_possible_oregen_type():
            if tool.level >= ore.level:
                if random.random() * 100 <= ore.chance:
                    n = math.ceil(random.random() * ore.size)
                    if n > 0:
                        drop = ore.drop
                        drop.amount = n
                        L.append(drop)
                        tool.durability = tool.durability - self.durability_cost*n
        user.inventory.add_items(*L)
        if tool.durability <= 0: user.inventory.remove_items([tool])
        return sorted(L, key=lambda x: (-x.amount, x.name))
