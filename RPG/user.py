import json
import math
import os

import aiosqlite
import yaml

from .exceptions import *

path = os.path.dirname(__file__)
with open(os.path.join(path, 'config/app.yaml'), encoding='utf-8') as f:
    conf = yaml.load(f, yaml.SafeLoader)
with open(os.path.join(path, 'config/items.yaml'), encoding='utf-8') as f:
    default_items = yaml.load(f, yaml.SafeLoader)


class Position:

    def __init__(self, x: int = None, y: int = None, z: int = None, *, use_default=False, **kwargs) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.metadata = kwargs
        if use_default:
            if not self.x: self.x = conf['Position']['x']
            if not self.y: self.y = conf['Position']['y']
            if not self.z: self.z = conf['Position']['z']
            if 'metadata' in conf['Position']: 
                d=dict(conf['Position']['metadata'])
                d.update(self.metadata)
                self.metadata=d

    def __getitem__(self, n):
        if hasattr(self, n): return getattr(self, n)
        else: return self.metadata[n]

    def __repr__(self) -> str:
        return f'Position: ({self.x}, {self.y}, {self.z})'

    @property
    def coordinate(self) -> list[int]:
        return (self.x, self.y, self.z)

    @property
    def is_ground(self) -> int:
        '''-1: underground, 0: at ground, 1: sky'''
        if self.z < self['ground']: return -1
        elif self.z == self['ground']: return 0
        elif self.z > self['ground']: return 1

    def move(self, dx: int = 0, dy: int = 0, dz: int = 0):
        self.x = self.x + int(dx)
        self.y = self.y + int(dy)
        self.z = self.z + int(dz)

    def goto(self, x: int = None, y: int = None, z: int = None):
        if x: self.x = int(x)
        if y: self.y = int(y)
        if z: self.z = int(z)

    def distance(self, position, horizon_mode: bool = False) -> float:
        '''horizon_mode: xy plane go first'''
        if horizon_mode: ((self.x - position.x)**2 + (self.y - position.y)**2)**0.5 + (self.z - position.z)**2
        else: return ((self.x - position.x)**2 + (self.y - position.y)**2 + (self.z - position.z)**2)**0.5

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['data'])
            if await cursor.fetchone():
                cursor = await db.execute(f'SELECT "value" FROM "data" WHERE key=?;', ['position'])
                r = await cursor.fetchone()
                x, y, z = json.loads(r[0])
                return Position(x, y, z, use_default=True)
            else:
                return Position(use_default=True)
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "data" ("key" TEXT UNIQUE, "value");')
            await db.execute(f'INSERT OR REPLACE INTO "data" VALUES ("position", ?);', [json.dumps(self.coordinate, ensure_ascii=False)])
            await db.commit()
        finally:
            if close: await db.close()


class Saturation:

    def __init__(self, level: float = None, range: list[float] = None, *, use_default: bool = False, **kwargs) -> None:
        self.level = level
        self.range = range
        self.metadata = kwargs
        if use_default:
            if not self.level: self.level = conf['Saturation']['level']
            if not self.range: self.range = conf['Saturation']['range']
            if 'metadata' in conf['Saturation']: 
                d=dict(conf['Saturation']['metadata'])
                d.update(self.metadata)
                self.metadata=d

    def __getitem__(self, n):
        if hasattr(self, n): return getattr(self, n)
        else: return self.metadata[n]

    def __getitem__(self, n):
        return self.metadata[n]

    def __repr__(self) -> str:
        return f'Saturation: {self.level}'

    @property
    def is_saturated(self) -> int:
        '''-1: hungry, 0: normal, 1: oversaturated'''
        if self.level < self.range[0]: return -1
        elif self.range[0] <= self.level <= self.range[1]: return 0
        elif self.range[1] < self.level: return 1

    def add_saturation(self, n: float = 0):
        self.level = self.level + float(n)

    def do_activity(self, activity):
        '''Reduce saturation level'''
        hungry=conf['Activity'][type(activity).__name__]['hungry']
        self.level=self.level-hungry

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['data'])
            if await cursor.fetchone():
                cursor = await db.execute(f'SELECT "value" FROM "data" WHERE key=?;', ['saturation'])
                s = await cursor.fetchone()
                return Saturation(s[0], use_default=True)
            else:
                return Saturation(use_default=True)
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "data" ("key" TEXT UNIQUE, "value");')
            await db.execute(f'INSERT OR REPLACE INTO "data" VALUES ("saturation", ?);', [self.level])
            await db.commit()
        finally:
            if close: await db.close()


class Currency:

    def __init__(self, dollars: int = None, use_default: bool = False, **kwargs) -> None:
        self.dollars = dollars
        self.metadata = kwargs
        if use_default:
            if not self.dollars: self.dollars = conf['Currency']['dollars']
            if 'metadata' in conf['Currency']: 
                d=dict(conf['Currency']['metadata'])
                d.update(self.metadata)
                self.metadata=d


    def __getitem__(self, n):
        if hasattr(self, n): return getattr(self, n)
        else: return self.metadata[n]

    def __repr__(self) -> str:
        return f'Currency: {self.dollars} dollars'

    @property
    def is_bankrupt(self) -> bool:
        return self.dollars < 0

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['data'])
            if await cursor.fetchone():
                cursor = await db.execute(f'SELECT "value" FROM "data" WHERE key=?;', ['currency'])
                s = await cursor.fetchone()
                return Currency(s[0], use_default=True)
            else:
                return Currency(use_default=True)
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "data" ("key" TEXT UNIQUE, "value");')
            await db.execute(f'INSERT OR REPLACE INTO "data" VALUES ("currency", ?);', [self.dollars])
            await db.commit()
        finally:
            if close: await db.close()


class Item:

    def __init__(self, category: str = None, name: str = None, amount: int = 0, stackable=True, *, use_default: bool = False, **kwargs) -> None:
        '''durability in metadata'''
        self.category = category
        self.name = name
        self.amount = amount
        self.stackable = stackable
        self.metadata = kwargs
        if use_default:
            if not self.category: self.category = default_items[self.name]['category']
            if not self.stackable: self.stackable = default_items[self.name]['stackable']
            if 'metadata' in default_items[self.name]: 
                d=dict(default_items[self.name]['metadata'])
                d.update(self.metadata)
                self.metadata=d

    def __getitem__(self, n):
        if hasattr(self, n): return getattr(self, n)
        else: return self.metadata[n]

    def __repr__(self) -> str:
        return f'Item: {self.name}[{self.amount}]'

    def add_amount(self, item):
        if self.name != item.name: raise TypeError('Different name')
        if not self.stackable: raise TypeError('Not stackable')
        self.amount = self.amount + item.amount


class Inventory:

    def __init__(self, *item: Item, **kwargs) -> None:
        self.items = list(item)
        self.metadata = kwargs

    def __getitem__(self, n):
        return self.get_items_by_name(n)

    def __iter__(self):
        yield from self.items

    def __repr__(self) -> str:
        return f'Inventory: {self.items}'

    def get_items_by_name(self, name: str):
        return [item for item in self if item.name == name]

    def get_items_by_category(self, category: str):
        return [item for item in self if item.category == category]

    @property
    def group_items_by_category(self) -> dict:
        L = dict()
        for item in self:
            category = item.category
            if category not in L: L.update({category: []})
            L[category].append(item)
        return {key: Inventory(*value) for key, value in L.items()}

    @property
    def get_all_category(self) -> set[str]:
        return {item.category for item in self}

    def add_items(self, *item: Item):
        for i in item:
            j = self.get_items_by_name(i.name)
            if len(j) > 0:
                if not j[0].stackable: self.items.append(i)
                else: j[0].add_amount(i)
            else: self.items.append(i)

    def remove_items(self, *item: Item):
        '''This will remove item regardless of amount, otherwise use add_items()'''
        for i in item:
            self.items.remove(i)

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['inventory'])
            if await cursor.fetchone():
                async with db.execute(f'SELECT * FROM "inventory"') as cur:
                    return Inventory(*[Item(row[0], row[1], row[2], **json.loads(row[3]), use_default=True) async for row in cur])
            else:
                return Inventory()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            await db.execute('DROP TABLE IF EXISTS "inventory"')
            await db.execute(f'CREATE TABLE "inventory" ("category" TEXT, "name" TEXT, "amount" INTEGAR, "metadata" TEXT);')
            for item in self:
                if item.amount<= 0: continue
                if 'durability' in item.metadata:
                    if item['durability']<=0: continue
                await db.execute(
                    f'INSERT INTO "inventory" VALUES (?,?,?,?);',
                    [item.category, item.name, item.amount, json.dumps(item.metadata, ensure_ascii=False)])
            await db.commit()
        finally:
            if close: await db.close()


class Ability:

    def __init__(self, name, experience: int = 0, use_default: bool = False, **kwargs) -> None:
        self.name = name
        self.experience = int(experience)
        self.metadata = kwargs
        if use_default:
            if not self.experience: self.x = conf['Ability'][name]

    def __getitem__(self, n):
        if hasattr(self, n): return getattr(self, n)
        else: return self.metadata[n]

    def __repr__(self) -> str:
        return f'Ability: {self.name} {self.level}({self.experience}/{self.upgrade_required})'

    @property
    def level(self) -> int:
        return math.ceil(0.64 * math.log(self.experience + 1))

    @property
    def upgrade_required(self) -> int:
        return math.ceil(math.exp(self.level / 0.64) - 1)

    def add_experience(self, n: int):
        self.experience = self.experience + int(n)


class AbilityTree:

    def __init__(self, *ability: Ability, **kwargs) -> None:
        self.abilities = list(ability)
        self.metadata = kwargs

    def __iter__(self):
        yield from self.abilities

    def __repr__(self) -> str:
        return f'Ability tree: {", ".join([i.name for i in self])}'

    def __getitem__(self, name: str):
        return self.get_ability_by_name(name)

    def add_ability(self, ability: Ability):
        self.abilities.append(ability)

    def get_ability_by_name(self, name: str) -> Ability:
        for i in self:
            if i.name == name: return i
        else:
            a = Ability(name, use_default=True)
            self.add_ability(a)
            return a

    async def read_sql(id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            cursor = await db.execute(f'SELECT "name" FROM "sqlite_master" WHERE type="table" AND name=?;', ['ability'])
            if await cursor.fetchone():
                async with db.execute(f'SELECT * FROM "ability"') as cur:
                    return AbilityTree(*[Ability(row[0], row[1], use_default=True) async for row in cur])
            else:
                return AbilityTree()
        finally:
            if close: await db.close()

    async def write_sql(self, id: int, db: aiosqlite.Connection = None, close=True):
        try:
            if db is None: db = await aiosqlite.connect(os.path.join(path, f'data/{id}.db'))
            await db.execute(f'CREATE TABLE IF NOT EXISTS "ability" ("key" TEXT UNIQUE, "value");')
            for a in self:
                await db.execute(f'INSERT OR REPLACE INTO "ability" VALUES (?,?);', [a.name, a.experience])
            await db.commit()
        finally:
            if close: await db.close()


class User:

    def __init__(self,
                 id: int,
                 name: str = None,
                 position: Position = Position(),
                 saturation=Saturation(),
                 currency=Currency(),
                 inventory=Inventory(),
                 abilitytree=AbilityTree(),
                 **kwargs) -> None:
        self.id = id
        self.name = name
        self.position = position
        self.saturation = saturation
        self.currency = currency
        self.inventory = inventory
        self.abilitytree = abilitytree
        self.metadata = kwargs

    def __repr__(self) -> str:
        return f'User: {self.name or self.id}'

    def __getitem__(self, n):
        return self.metadata[n]

    def do_activity(self, activity_name: str, tool_name: str = None, craft_item: str = None,craft_times:int=1, food_name:str=None, food_amount:int=None, *args, **kwargs):
        '''
        Gather: 
        Mine: tool_name
        Craft: craft_item, craft_times
        Eat: food_name, food_amount
        '''
        from .activity import Craft, Gather, Mine, Eat
        ability = self.abilitytree.get_ability_by_name(activity_name)
        if activity_name == 'Gather':
            if self.saturation.level - conf['Activity'][activity_name]['hungry'] < min(self.saturation.range): raise RPG_exception('沒體力了')
            res = []
            for activity in Gather.get_possible_types(ability):
                res.extend(activity.do(ability, self.position))
            self.inventory.add_items(*res)
            ability.add_experience(1)
            self.saturation.do_activity(activity)
            return res
        elif activity_name == 'Mine':
            if self.saturation.level - conf['Activity'][activity_name]['hungry'] < min(self.saturation.range): raise RPG_exception('沒體力了')
            tools = self.inventory.get_items_by_name(tool_name)
            if len(tools)==0: raise RPG_exception('沒有這個工具')
            tool=tools[0]
            res = []
            for activity in Mine.get_possible_types(self.position, tool):
                res.extend(activity.do(self.position, tool))
            self.inventory.add_items(*res)
            ability.add_experience(1)
            self.saturation.do_activity(activity)
            return res
        elif activity_name == 'Craft':
            if self.saturation.level - conf['Activity'][activity_name]['hungry'] < min(self.saturation.range): raise RPG_exception('沒體力了')
            for craft in Craft.get_possible_types(self.inventory):
                if craft.name == craft_item:
                    res, used = craft.do(self.inventory, craft_times)
                    break
                else:
                    raise RPG_exception('未知的合成')
            self.inventory.add_items(res, *used)
            ability.add_experience(1)
            self.saturation.do_activity(craft)
            return res, used
        # elif activity_name == 'Smelt': return Smelt(*args, **kwargs)
        # elif activity_name == 'Farm': return Farm(*args, **kwargs)
        # elif activity_name == 'Feed': return Feed(*args, **kwargs)
        elif activity_name == 'Eat': 
            for food in Eat.get_possible_types(self.inventory):
                if food.name==food_name:
                    s, eaten=food.do(self.inventory)
                    if s+self.saturation.level > max(self.saturation.range): raise RPG_exception('你太飽了')
                    break
            else: 
                raise RPG_exception('沒有這個食物')
            self.inventory.add_items(eaten)
            self.saturation.add_saturation(s)
            return s, eaten
        else:
            raise ValueError('Unknown activity')


    async def read_sql(id: int, name: str = None):
        async with aiosqlite.connect(os.path.join(path, f'data/{id}.db')) as db:
            p = await Position.read_sql(id, db, close=False)
            s = await Saturation.read_sql(id, db, close=False)
            c = await Currency.read_sql(id, db, close=False)
            i = await Inventory.read_sql(id, db, close=False)
            a = await AbilityTree.read_sql(id, db, close=False)
            return User(id, name, p, s, c, i, a)

    async def write_sql(self):
        async with aiosqlite.connect(os.path.join(path, f'data/{self.id}.db')) as db:
            if self.position: await self.position.write_sql(self.id, db, close=False)
            if self.saturation: await self.saturation.write_sql(self.id, db, close=False)
            if self.currency: await self.currency.write_sql(self.id, db, close=False)
            if self.inventory: await self.inventory.write_sql(self.id, db, close=False)
            if self.abilitytree: await self.abilitytree.write_sql(self.id, db, close=False)
