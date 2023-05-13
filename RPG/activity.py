import math
import os
import random

import yaml

from .exceptions import *
from .user import *

path = os.path.dirname(__file__)
with open(os.path.join(path, 'config/activity.yaml'), encoding='utf-8') as f:
    conf = yaml.load(f, yaml.SafeLoader)


class Activity:

    def __init__(self, name: str = None, **kwargs) -> None:
        self.name = name
        self.metadata = kwargs

    def __repr__(self) -> str:
        return f'{type(self).__name__}: {self.name}'

    def get_possible_types(*args, **kwargs):
        pass

    def do(*args, **kwargs):
        pass


class Gather(Activity):

    def __init__(self, name: str = None, rarity: int = 0, chance: float = 0, amount: int = 1, **kwargs) -> None:
        '''Item to gather'''
        super().__init__(name, **kwargs)
        self.rarity = int(rarity)
        self.chance = float(chance)
        self.amount = int(amount)

    def __repr__(self) -> str:
        return f'Gather: {self.name}'

    def get_possible_types(ability: Ability = None, *args, **kwargs):
        L = list()
        for name, values in conf['Gather'].items():
            if ability:
                if ability.name == 'Gather' and ability.level < values['rarity']: continue
            L.append(Gather(name, **values))
        return L

    def do(self, ability: Ability, position: Position, *args, **kwargs) -> list[Item]:
        '''Return list of obtained items'''
        if ability.level < self.rarity: raise RPG_exception('沒有足夠專精等級')
        if  position.is_ground != 0: raise RPG_exception('你不在地表')
        if random.random() <= self.chance:
            n = math.ceil(random.random() * self.amount)
            return [Item(name=self.name, amount=n, from_default=True)]
        else:
            return []


class Mine(Activity):

    def __init__(self,
                 name: str = None,
                 hardness: int = 0,
                 chance: float = 0,
                 cluster_size: int = 0,
                 range: list[int] = [0, 0],
                 drop: list[Item] = None,
                 **kwargs) -> None:
        '''Block to mine'''
        super().__init__(name, **kwargs)
        self.hardness = int(hardness)
        self.chance = float(chance)
        self.cluster_size = int(cluster_size)
        self.range = sorted(range)
        self.drop = drop

    def get_possible_types(position: Position = None, tool: Item = None, *args, **kwargs):

        def get_drop(drop, *args, **kwargs):
            return [Item(name=list(i.keys())[0], amount=list(i.values())[0], use_default=True) for i in drop], kwargs

        L = list()
        for name, values in conf['Mine'].items():
            if position:
                if not min(values['range']) <= position.z <= max(values['range']): continue
            if tool:
                tool_level = conf['Pickaxe'][tool.name]['level']
                if tool_level < values['hardness']: continue
            drop, values = get_drop(**values)
            L.append(Mine(name, drop=drop, **values))
        return L

    def do(self, position: Position, tool: Item, *args, **kwargs) -> list[Item]:
        '''Return list of obtained items and also reduce durability of tool'''
        if tool.category != 'Pickaxe': raise RPG_exception('錯誤的工具')
        if not min(self.range) <= position.z <= max(self.range): raise RPG_exception('錯誤的高度')
        tool_level = conf['Pickaxe'][tool.name]['level']
        if tool_level < self.hardness: return []
        L = []
        if random.random() <= self.chance:
            for drop in self.drop:
                durability = tool['durability']
                n = math.ceil(random.random() * self.cluster_size)
                if durability - n < 0: n = durability
                L.append(Item(name=drop.name, amount=n * drop.amount, from_default=True))
                tool.metadata['durability'] = durability - n
        return L


class Craft(Activity):

    def __init__(self, name: str = None, recipe: list[Item] = None, result: Item = None, **kwargs) -> None:
        '''Item to craft'''
        super().__init__(name, **kwargs)
        self.recipe = recipe
        self.result = result
        self.recipe = recipe

    def get_possible_types(inventory: Inventory = None, *args, **kwargs):

        def get_craft(name, recipe, amount):
            recipe = [Item(name=x, amount=i, use_default=True) for x, i in recipe.items()]
            res = Item(name=name, amount=amount, use_default=True)
            return Craft(name, recipe, res)

        L = list()
        for name, values in conf['Craft'].items():
            if inventory:
                for ingredient, amount in values['recipe'].items():
                    i = inventory.get_items_by_name(ingredient)
                    if len(i) == 0: break
                    if i[0].amount < amount: break
                else: L.append(get_craft(name, **values))
            else: L.append(get_craft(name, **values))
        return L

    def do(self, inventory: Inventory, times: int = 1) -> tuple[Item, list[Item]]:
        '''Return list of crafted items and used items (with negative amount), but not reduce amount of items in inventory'''
        L = []
        for ingredient in self.recipe:
            n = ingredient.amount * times
            i = inventory.get_items_by_name(ingredient.name)
            if len(i) == 0: raise RPG_exception('沒有足夠材料')
            if i[0].amount - n < 0: raise RPG_exception('沒有足夠材料')
            L.append(Item(ingredient.category, ingredient.name, -n, ingredient.metadata))
        return Item(self.result.category, self.result.name, self.result.amount * times, self.result.metadata), L


class Eat(Activity):

    def __init__(self, name: str = None,food:Item=None ,saturation: float = 0, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.food=food
        self.saturation=float(saturation)

    def get_possible_types(inventory: Inventory = None, *args, **kwargs):
        L = list()
        for name, values in conf['Food'].items():
            if inventory:
                i = inventory.get_items_by_name(name)
                if len(i) == 0: continue
            L.append(Eat(name, Item(name=name, amount=1, use_default=True), **values))
        return L

    def do(self, inventory: Inventory, amount: int = 1):
        '''Return list of eaten items (with negative amount) and total saturation value, but not restore user's saturation'''
        i= inventory.get_items_by_name(self.name)
        if len(i)==0: raise RPG_exception('沒有足夠食物')
        if i[0].amount<amount: raise RPG_exception('沒有足夠食物')
        return self.saturation*amount, Item(self.food.category, self.food.name, -amount, self.food.metadata)