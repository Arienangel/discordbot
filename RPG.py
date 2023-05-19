import math
import yaml
import os
from typing import Callable
import random
import aiosqlite
import json
import uuid
import datetime
from typing import Union

path = os.path.dirname(__file__)
with open(os.path.join(path, 'config/RPG/user.yaml'), encoding='utf-8') as f:
    conf = yaml.load(f, yaml.SafeLoader)
with open(os.path.join(path, 'config/RPG/item.yaml'), encoding='utf-8') as f:
    default_item = yaml.load(f, yaml.SafeLoader)
with open(os.path.join(path, 'config/RPG/activity.yaml'), encoding='utf-8') as f:
    activity_data = yaml.load(f, yaml.SafeLoader)


class RPG_exception(Exception):
    pass


class Ability:

    def __init__(self, name: str, experience: int = 0) -> None:
        self.name = name
        self.experience = experience

    def __repr__(self) -> str:
        return f'Ability: {self.name} {self.level} ({self.experience}/{self.upgrade_required})'

    @property
    def level(self) -> int:
        return math.ceil(0.64 * math.log(self.experience + 1))

    @property
    def upgrade_required(self) -> int:
        return math.ceil(math.exp(self.level / 0.64) - 1)

    def add_experience(self, n: int):
        self.experience = self.experience + n

    def get_default(name):
        if name in conf['Ability']:
            return Ability(name, conf['Ability'][name]['experience'])
        else:
            raise ValueError(f'Default value of ability: {name} does not exists')


class AbilityTree:

    def __init__(self, *ability: Ability) -> None:
        self.abilities = list(ability)

    def __iter__(self):
        yield from self.abilities

    def __repr__(self) -> str:
        return f'Ability tree: {", ".join([i.name for i in self])}'

    def __getitem__(self, name: str) -> Ability:
        for ability in self:
            if ability.name == name:
                return ability
        else:
            return None

    def __setitem__(self, name: str, experience: int):
        for ability in self:
            if ability.name == name:
                ability.experience = experience
                return
        else:
            self.add_ability(Ability(name, experience))

    def get_default():
        return AbilityTree(*[Ability(name, values['experience']) for name, values in conf['Ability'].items()])

    def add_ability(self, ability: Ability):
        self.abilities.append(ability)

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['Ability'])
            if await cursor.fetchone():
                async with db.execute(f'SELECT * FROM "Ability"') as cur:
                    return AbilityTree(*[Ability(*row) async for row in cur])
            else:
                return AbilityTree.get_default()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "Ability" ("key" TEXT UNIQUE, "value" INTEGAR);')
            for a in self:
                await db.execute(f'INSERT OR REPLACE INTO "Ability" VALUES (?,?);', [a.name, a.experience])
            await db.commit()
        finally:
            if close: await db.close()


class Finance:

    def __init__(self, deposit: int = 0, debt: int = 0) -> None:
        self.deposit = deposit
        self.debt = debt

    def __repr__(self) -> str:
        return f'Finance: {self.total} dollars'

    @property
    def total(self) -> int:
        return self.deposit - self.debt

    @property
    def interest_rate(self) -> float:
        return conf['Finance']['interest_rate']

    def get_default(deposit: int = None, debt: int = None):
        return Finance(deposit or conf['Finance']['deposit'], debt or conf['Finance']['debt'])

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['Finance'])
            if await cursor.fetchone():
                async with db.execute(f'SELECT * FROM "Finance"') as cur:
                    return Finance(**{key: value async for key, value in cur})
            else:
                return Finance.get_default()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "Finance" ("key" TEXT UNIQUE, "value" INTEGAR);')
            await db.execute(f'INSERT OR REPLACE INTO "Finance" VALUES (?, ?);', ['deposit', self.deposit])
            await db.execute(f'INSERT OR REPLACE INTO "Finance" VALUES (?, ?);', ['debt', self.debt])
            await db.commit()
        finally:
            if close: await db.close()


class Item:

    def __init__(self, id: str, display_name: str = None, amount: int = 0, *, uid: str = None, **tag) -> None:
        ''' 
        id (str): tool:diamond_pickaxe
        display_name (str, Optional): 鑽石鎬
        amount (int, Optional): 1
        tag (dict, Optional): {'durability': 128}
        '''
        self.id = id
        self.display_name = display_name or id.split(':')[1]
        self.amount = amount
        self.tag = tag
        self.uid = uid or uuid.uuid4().hex

    def __repr__(self) -> str:
        return f'Item: {self.display_name}*{self.amount}'

    @property
    def category(self):
        return self.id.rsplit(':', 1)[0]

    @property
    def name(self):
        return self.id.rsplit(':', 1)[1]

    @property
    def is_stackable(self) -> bool:
        if self.tag: return False
        return default_item[self.id]['stackable']

    def get_default(id: str, amount: int = 0, **kwargs):
        if id in default_item:
            if 'tag' in default_item[id]:
                return Item(id, default_item[id]['name'], amount, **default_item[id]['tag'], **kwargs)
            else:
                return Item(id, default_item[id]['name'], amount, **kwargs)
        else:
            return Item(id, None, amount)

    def stack(self, item):
        if self.id != item.id: raise ValueError('Can not stack item with different id')
        if not self.is_stackable: raise ValueError('Item is not stackable')
        self.amount = self.amount + item.amount


class Inventory:

    def __init__(self, *item: Item) -> None:
        self.items = list(item)

    def __iter__(self):
        yield from self.items

    def __repr__(self) -> str:
        return 'Inventory: ' + ', '.join([f'{i.name}*{i.amount}' for i in self])

    def __getitem__(self, id: str) -> Union[list[Item], Item]:
        if ':' in id:
            return [item for item in self if item.id == id]
        else:
            for i in self:
                if i.uid == id: return i
            else: return None

    @property
    def get_all_category(self) -> set[str]:
        return {item.category for item in self}

    @property
    def group_items_by_category(self) -> dict:
        D = dict()
        for item in self:
            category = item.category
            if category not in D: D.update({category: []})
            D[category].append(item)
        return D

    def get_items(self, func: Callable[[Item], bool]) -> list[Item]:
        return [item for item in self if func(item)]

    def add_items(self, *item: Item):
        for add in item:
            if (not add.is_stackable) or add.tag: self.items.append(add)
            else:
                for inv in self:
                    if inv.id == add.id:
                        inv.stack(add)
                        break
                else:
                    self.items.append(add)

    def remove_items(self, *item: Item):
        '''This will remove item regardless of amount, otherwise use add_items() with negative amount'''
        for rm in item:
            self.items.remove(rm)

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):

        async def delrow(uid):
            await db.execute(f' DELETE FROM "inventory" WHERE uid=?;', [uid])
            await db.commit()

        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['Inventory'])
            if await cursor.fetchone():
                async with db.execute(f'SELECT * FROM "Inventory"') as cur:
                    L = []
                    async for id, display_name, amount, tag, uid in cur:
                        tag = json.loads(tag)
                        if amount == 0:
                            await db.execute(f' DELETE FROM "inventory" WHERE uid=?;', [uid])
                            await db.commit()
                            continue
                        if 'durability' in tag:
                            if tag['durability'] == 0:
                                await db.execute(f' DELETE FROM "inventory" WHERE uid=?;', [uid])
                                await db.commit()
                                continue
                        if 'pending' in tag:
                            if float(datetime.datetime.now().timestamp()) >= tag['pending']:
                                L.extend([Item.get_default(**i) for i in tag['result']])
                                tag.pop('result')
                                tag.pop('pending')
                        L.append(Item(id, display_name, amount, **tag, uid=uid))
                    return Inventory(*L)
            else:
                return Inventory()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "Inventory" ("id" TEXT, "display_name" TEXT, "amount"	INTEGER, "tag"	TEXT, "uid" INTEGAR UNIQUE);')
            for i in self:
                await db.execute(f'INSERT OR REPLACE INTO "Inventory" VALUES (?,?,?,?,?);', [i.id, i.display_name, i.amount, json.dumps(i.tag, ensure_ascii=False), i.uid])
            await db.commit()
        finally:
            if close: await db.close()


class Position:

    def __init__(self, x: int = 0, y: int = 0, z: int = 0) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self) -> str:
        return f'Position: ({self.x}, {self.y}, {self.z})'

    @property
    def ground(self) -> int:
        return conf['Position']['ground']

    @property
    def coordinate(self) -> list[int]:
        return (self.x, self.y, self.z)

    @property
    def is_ground(self) -> int:
        '''-1: underground, 0: at ground, 1: sky'''
        if self.z < self.ground: return -1
        elif self.z == self.ground: return 0
        elif self.z > self.ground: return 1

    def move(self, dx: int = 0, dy: int = 0, dz: int = 0):
        self.x = self.x + dx
        self.y = self.y + dy
        self.z = self.z + dz

    def goto(self, x: int = None, y: int = None, z: int = None):
        if x: self.x = x
        if y: self.y = y
        if z: self.z = z

    def distance(self, position, horizon_mode: bool = False) -> float:
        '''horizon_mode: xy plane go first'''
        if horizon_mode: ((self.x - position.x)**2 + (self.y - position.y)**2)**0.5 + (self.z - position.z)**2
        else: return ((self.x - position.x)**2 + (self.y - position.y)**2 + (self.z - position.z)**2)**0.5

    def get_default(x: int = None, y: int = None, z: int = None):
        return Position(x or conf['Position']['x'], y or conf['Position']['y'], z or conf['Position']['z'])

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['Position'])
            if await cursor.fetchone():
                cur = await db.execute(f'SELECT * FROM "Position"')
                return Position(**{key: value async for key, value in cur})
            else:
                return Position.get_default()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "Position" ("key" TEXT UNIQUE, "value" INTEGAR);')
            await db.execute(f'INSERT OR REPLACE INTO "Position" VALUES (?, ?);', ['x', self.x])
            await db.execute(f'INSERT OR REPLACE INTO "Position" VALUES (?, ?);', ['y', self.y])
            await db.execute(f'INSERT OR REPLACE INTO "Position" VALUES (?, ?);', ['z', self.z])
            await db.commit()
        finally:
            if close: await db.close()


class Health:

    def __init__(self, health: float = 0, saturation: float = 0, nutrient: dict = {}) -> None:
        self.health = health
        self.saturation = saturation
        if isinstance(nutrient, str): nutrient = json.loads(nutrient)
        self.nutrient = nutrient

    def __repr__(self) -> str:
        return f'Health: health({self.health}), saturation({self.saturation})'

    @property
    def health_range(self) -> list[float]:
        return sorted(conf['Health']['health']['range'])

    @property
    def saturation_range(self) -> list[float]:
        return sorted(conf['Health']['saturation']['range'])

    @property
    def is_saturated(self) -> int:
        '''-1: hungry, 0: normal, 1: oversaturated'''
        if self.saturation < self.saturation_range[0]: return -1
        elif self.saturation_range[0] <= self.saturation <= self.saturation_range[1]: return 0
        elif self.saturation_range[1] < self.saturation: return 1

    def nutrient_level(self, name):
        return 1 - math.exp(-self.nutrient[name] / 50)

    @property
    def nutrient_balance(self):
        L = [self.nutrient_level(key) for key in self.nutrient]
        return sum(L)/len(L)

    def add_saturation(self, n: float = 0):
        self.saturation = self.saturation + n

    def add_nutrient(self, name, value):
        if name in self.nutrient:
            self.nutrient[name] = self.nutrient[name] + value
        else:
            self.nutrient.update({name, value})

    def get_default():
        return Health(conf['Health']['health']['level'], conf['Health']['saturation']['level'], conf['Health']['nutrient'])

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['Health'])
            if await cursor.fetchone():
                cur = await db.execute(f'SELECT * FROM "Health"')
                return Health(**{key: value async for key, value in cur})
            else:
                return Health.get_default()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "Health" ("key" TEXT UNIQUE, "value" INTEGAR);')
            await db.execute(f'INSERT OR REPLACE INTO "Health" VALUES (?, ?);', ['health', self.health])
            await db.execute(f'INSERT OR REPLACE INTO "Health" VALUES (?, ?);', ['saturation', self.saturation])
            await db.execute(f'INSERT OR REPLACE INTO "Health" VALUES (?, ?);', ['nutrient', json.dumps(self.nutrient, ensure_ascii=False)])
            await db.commit()
        finally:
            if close: await db.close()


class User:

    def __init__(self, id: int, display_name: str = None, position: Position = Position(), health: Health = Health(), finance: Finance = Finance(), inventory: Inventory = Inventory(), abilitytree: AbilityTree = AbilityTree()) -> None:
        self.id = id
        self.display_name = display_name
        self.position = position
        self.health = health
        self.finance = finance
        self.inventory = inventory
        self.abilitytree = abilitytree

    def __repr__(self) -> str:
        return f'User: {self.display_name or self.id}'

    def get_default(id: int, display_name: str = None, position: Position = None, health: Health = None, finance: Finance = None, inventory: Inventory = None, abilitytree: AbilityTree = None):
        return User(id, display_name, position or Position.get_default(), health or Health.get_default(), finance or Finance.get_default(), inventory or Inventory(), abilitytree or AbilityTree.get_default())

    def do_activity(self, activity_name: str, tool: Item = None, to_craft: Item = None, to_use: Item = None, times: int = 1, fuel: Item = None, furnace: Item = None, **kwargs):
        if activity_name == 'Gather':
            if self.position.is_ground != 0: RPG_exception('你不在地表')
            if self.health.saturation - activity_data['Gather']['hungry'] < 0: raise RPG_exception('沒體力了')
            self.health.add_saturation(-activity_data['Gather']['hungry'])
            L = []
            for item_id, values in activity_data['Gather']['target'].items():
                if self.abilitytree['Gather'].level < values['rarity']: continue
                if random.random() < values['chance']:
                    amount = math.ceil(random.random() * values['amount'])
                    L.append(Item.get_default(item_id, amount))
            self.inventory.add_items(*L)
            self.abilitytree['Gather'] = self.abilitytree['Gather'].experience + activity_data['Gather']['experience']
            return L

        elif activity_name == 'Mine':
            '''tool (Item)'''
            if self.position.is_ground == 1: RPG_exception('你不在地底')
            if self.health.saturation - activity_data['Mine']['hungry'] < 0: raise RPG_exception('沒體力了')
            self.health.add_saturation(-activity_data['Mine']['hungry'])
            if tool.id not in activity_data['Mine']['tool']: raise RPG_exception('錯誤的工具')
            hardness = activity_data['Mine']['tool'][tool.id]['hardness']
            L = []
            for item_id, values in activity_data['Mine']['target'].items():
                if hardness < values['hardness']: continue
                if not min(values['range']) <= self.position.z <= max(values['range']): continue
                if random.random() < values['chance']:
                    for drop in values['drop']:
                        drop_id, drop_amount = list(drop.items())[0]
                        amount = math.ceil(random.random() * drop_amount * values['cluster_size'])
                        if tool.tag['durability'] - amount < 0: amount = tool.tag['durability']
                        if tool.tag['durability'] == 0: break
                        tool.tag['durability'] = tool.tag['durability'] - amount
                        L.append(Item.get_default(drop_id, amount))
            self.inventory.add_items(*L)
            self.abilitytree['Mine'] = self.abilitytree['Mine'].experience + activity_data['Mine']['experience']
            return L

        elif activity_name == 'Craft':
            '''to_craft (Item), times (int, Optional)'''
            if self.health.saturation - activity_data['Craft']['hungry'] < 0: raise RPG_exception('沒體力了')
            self.health.add_saturation(-activity_data['Craft']['hungry'])
            values = activity_data['Craft']['target'][to_craft.id]
            L = []
            for ingredient, amount in values['recipe'].items():
                i = self.inventory[ingredient]
                if len(i) == 0: raise RPG_exception('沒有足夠材料')
                if i[0].amount - amount * times < 0: raise RPG_exception('沒有足夠材料')
                L.append(Item.get_default(ingredient, -amount * times))
            self.inventory.add_items(*L)
            to_craft.amount = values['amount'] * times
            if to_craft.is_stackable:
                self.inventory.add_items(to_craft)
            else:
                for _ in range(to_craft.amount):
                    self.inventory.add_items(Item.get_default(to_craft.id, 1))
            self.abilitytree['Craft'] = self.abilitytree['Craft'].experience + activity_data['Craft']['experience']
            return to_craft, L

        elif activity_name == 'Smelt':
            '''to_craft (Item), times (int, Optional), fuel (Item), furnace (Item)'''
            to_craft.amount = activity_data['Smelt']['target'][to_craft.id]['amount'] * times
            if self.health.saturation - activity_data['Smelt']['hungry'] < 0: raise RPG_exception('沒體力了')
            self.health.add_saturation(-activity_data['Smelt']['hungry'])
            if furnace.id not in activity_data['Smelt']['furnace']: raise RPG_exception('這不是熔爐')
            if furnace.tag['durability'] - to_craft.amount < 0: raise RPG_exception('熔爐沒有足夠耐久度')
            if 'pending' in furnace.tag: raise RPG_exception('熔爐正在使用中')
            values = activity_data['Smelt']['target'][to_craft.id]
            if fuel.id not in activity_data['Smelt']['fuel']: raise RPG_exception('這不能當燃料')
            if activity_data['Smelt']['furnace'][furnace.id]['temperature'] < activity_data['Smelt']['fuel'][fuel.id]['temperature']: raise RPG_exception('熔爐無法承受此溫度')
            if activity_data['Smelt']['furnace'][furnace.id]['temperature'] < values['temperature']: raise RPG_exception('熔爐無法承受此溫度')
            if activity_data['Smelt']['fuel'][fuel.id]['temperature'] < values['temperature']: raise RPG_exception('燃料溫度不足')
            if fuel.amount * activity_data['Smelt']['fuel'][fuel.id]['duration'] < values['duration']: raise RPG_exception('燃料不足')
            fuel.amount = -fuel.amount
            L = []
            for ingredient, amount in values['recipe'].items():
                i = self.inventory[ingredient]
                if len(i) == 0: raise RPG_exception('沒有足夠材料')
                if i[0].amount - amount * times < 0: raise RPG_exception('沒有足夠材料')
                L.append(Item.get_default(ingredient, -amount * times))
            L.append(fuel)
            self.inventory.add_items(*L)
            finish_time = datetime.datetime.now() + datetime.timedelta(seconds=values['duration'])
            furnace.tag.update({'pending': round(finish_time.timestamp()), 'result': [{'id': to_craft.id, 'amount': to_craft.amount}]})  # change this amount according to ability level
            furnace.tag['durability'] = furnace.tag['durability'] - to_craft.amount
            self.abilitytree['Smelt'] = self.abilitytree['Smelt'].experience + activity_data['Smelt']['experience']
            return to_craft, L, furnace

        elif activity_name == 'Farm':
            pass

        elif activity_name == 'Feed':
            pass

        elif activity_name == 'Eat':
            '''to_use (Item), times (int, Optional)'''
            values = activity_data['Eat']['food'][to_use.id]
            if self.health.saturation + values['level'] * times > max(self.health.saturation_range): raise RPG_exception('你吃不下這些食物')
            restore = values['level'] * times
            self.health.add_saturation(restore)
            for nutrient, n, in values['nutrient'].items():
                self.health.add_nutrient(nutrient, n * times)
            to_use.amount = to_use.amount - times
            return restore, Item.get_default(to_use.id, -times)

        elif activity_name == 'Sell':
            pass

        else:
            raise ValueError('Unknown activity')

    @property
    def get_possible_ore(self) -> list[Item]:
        g = self.inventory.group_items_by_category
        if 'tool:pickaxe' in g:
            tools = g['tool:pickaxe']
            tool_level = max(map(lambda x: activity_data['Mine']['tool'][x.id]['hardness'], tools))
            return [Item.get_default(key) for key, values in activity_data['Mine']['target'].items() if (min(values['range']) <= self.position.z <= max(values['range'])) and (values['hardness'] <= tool_level)]
        else:
            return []

    @property
    def get_possible_craft(self) -> list[Item]:
        L = list()
        for key, values in activity_data['Craft']['target'].items():
            for ingredient, amount in values['recipe'].items():
                i = self.inventory[ingredient]
                if len(i) == 0: break
                if i[0].amount < amount: break
            else: L.append(Item.get_default(key))
        return L

    @property
    def get_possible_smelt(self) -> list[Item]:
        L = list()
        for key, values in activity_data['Smelt']['target'].items():
            for ingredient, amount in values['recipe'].items():
                i = self.inventory[ingredient]
                if len(i) == 0: break
                if i[0].amount < amount: break
            else: L.append(Item.get_default(key))
        return L

    @property
    def get_possible_fuel(self) -> list[dict[Item]]:
        L = list()
        for key, values in activity_data['Smelt']['fuel'].items():
            i = self.inventory[key]
            if len(i) == 0: continue
            else: L.append({Item.get_default(key, i[0].amount): values})
        return L

    def get_recipe(id=None) -> Union[list[Item], dict]:
        if id:
            if id in activity_data['Craft']['target']:
                values = activity_data['Craft']['target'][id]
                return {Item.get_default(id, values['amount']): {'recipe': [Item.get_default(ingredient, amount) for ingredient, amount in values['recipe'].items()]}}
            elif id in activity_data['Smelt']['target']:
                values = activity_data['Smelt']['target'][id]
                return {Item.get_default(id, values['amount']): {'recipe': [Item.get_default(ingredient, amount) for ingredient, amount in values['recipe'].items()], 'temperature': values['temperature'], 'duration': values['duration']}}
            else:
                return {}
        else:
            craft = [{Item.get_default(key, values['amount']): {'recipe': [Item.get_default(ingredient, amount) for ingredient, amount in values['recipe'].items()]}} for key, values in activity_data['Craft']['target'].items()]
            smelt = [{Item.get_default(key, values['amount']): {'recipe': [Item.get_default(ingredient, amount) for ingredient, amount in values['recipe'].items()], 'temperature': values['temperature'], 'duration': values['duration']}} for key, values in activity_data['Smelt']['target'].items()]
            return craft + smelt

    async def read_sql(id: int, name: str = None):
        async with aiosqlite.connect(os.path.join(path, f'data/RPG/{id}.db')) as db:
            p = await Position.read_sql(id, db, close=False)
            s = await Health.read_sql(id, db, close=False)
            c = await Finance.read_sql(id, db, close=False)
            i = await Inventory.read_sql(id, db, close=False)
            a = await AbilityTree.read_sql(id, db, close=False)
            return User(id, name, p, s, c, i, a)

    async def write_sql(self):
        async with aiosqlite.connect(os.path.join(path, f'data/RPG/{self.id}.db')) as db:
            if self.position: await self.position.write_sql(self.id, db, close=False)
            if self.health: await self.health.write_sql(self.id, db, close=False)
            if self.finance: await self.finance.write_sql(self.id, db, close=False)
            if self.inventory: await self.inventory.write_sql(self.id, db, close=False)
            if self.abilitytree: await self.abilitytree.write_sql(self.id, db, close=False)
