import datetime
import json

import aiosqlite

from RPG import item


class Position:

    def __init__(self, x: int = 0, y: int = 0, z: int = 64) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self) -> str:
        return f'Position: ({self.x}, {self.y}, {self.z})'

    @property
    def coordinate(self) -> tuple[int]:
        return (self.x, self.y, self.z)

    def move(self, x: int = 0, y: int = 0, z: int = 0):
        self.x = self.x + x
        self.y = self.y + y
        self.z = self.z + z

    def goto(self, x: int = 0, y: int = 0, z: int = 0):
        self.x = x
        self.y = y
        self.z = z

    def distance(self, position):
        return ((self.x - position.x)**2 + (self.y - position.y)**2 + (self.z - position.z)**2)**0.5

    async def get_possible_oregen_type(self) -> list[item.Ore]:
        async with aiosqlite.connect(f'config/RPG/item.db') as db:
            cursor = await db.execute(f'SELECT * FROM Ore WHERE zmin<? AND zmax>?', [self.z, self.z])
            ores= [
                item.Ore(ore[0], 0, ore[1],
                         item.Ore(ore[0]) if ore[2] == 'self' else item.Item(ore[2]), ore[3], ore[4], ore[5], ore[6])
                for ore in await cursor.fetchall()
            ]
            return sorted(ores, key=lambda x: x.name)

    async def read_sql(id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            cursor = await db.execute(f'SELECT name FROM sqlite_master WHERE type="table" AND name=?;', ['position'])
            if await cursor.fetchone():
                cursor = await db.execute(f'SELECT x, y, z FROM position ORDER BY t DESC LIMIT 1;', )
                x, y, z = await cursor.fetchone()
                return Position(x, y, z)
            else:
                return Position()

    async def write_sql(self, id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            await db.execute(f'CREATE TABLE IF NOT EXISTS "position" ("t" INTEGER UNIQUE, "x" INTEGER, "y" INTEGER, "z" INTEGER);')
            await db.execute(f'INSERT INTO "position" VALUES (?,?,?,?);', [round(datetime.datetime.now().timestamp()), self.x, self.y, self.z])
            await db.commit()


class Saturation:

    def __init__(self, level: float = 10, max: float = 10, min: float = 0) -> None:
        self.max = max
        self.min = min
        self.level = level

    def __repr__(self) -> str:
        return f'Saturation: {self.level}'

    @property
    def is_hunger(self) -> bool:
        return self.level < self.min

    @property
    def is_oversaturated(self) -> bool:
        return self.level > self.max

    def change(self, amount: float = 0):
        self.level = self.level + amount

    async def read_sql(id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            cursor = await db.execute(f'SELECT name FROM sqlite_master WHERE type="table" AND name=?;', ['saturation'])
            if await cursor.fetchone():
                cursor = await db.execute(f'SELECT level FROM saturation ORDER BY t DESC LIMIT 1;', )
                level, *_ = await cursor.fetchone()
                return Saturation(level)
            else:
                return Saturation()

    async def write_sql(self, id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            await db.execute(f'CREATE TABLE IF NOT EXISTS "saturation" ("t" INTEGER UNIQUE, "level" REAL);')
            await db.execute(f'INSERT INTO "saturation" VALUES (?,?);', [round(datetime.datetime.now().timestamp()), self.level])
            await db.commit()


class Currency:

    def __init__(self, dollars: int = 0) -> None:
        self.dollars = dollars

    def __repr__(self) -> str:
        return f'Currency: {self.dollars} dollars'

    @property
    def is_bankrupt(self) -> bool:
        return self.dollars < 0

    async def read_sql(id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            cursor = await db.execute(f'SELECT name FROM sqlite_master WHERE type="table" AND name=?;', ['currency'])
            if await cursor.fetchone():
                cursor = await db.execute(f'SELECT dollars FROM currency ORDER BY t DESC LIMIT 1;', )
                dollars, *_ = await cursor.fetchone()
                return Currency(dollars)
            else:
                return Currency()

    async def write_sql(self, id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            await db.execute(f'CREATE TABLE IF NOT EXISTS "currency" ("t" INTEGER UNIQUE, "dollars" INT);')
            await db.execute(f'INSERT INTO "currency" VALUES (?,?);', [round(datetime.datetime.now().timestamp()), self.dollars])
            await db.commit()


class Inventory:

    def __init__(self, items: list[item.Item] = []) -> None:
        self.items = items

    def __repr__(self) -> str:
        return f'Inventory: {self.items}'

    def __getitem__(self, n):
        return self.items[n]

    def __iter__(self):
        yield from sorted(self.items, key=lambda x: (x.type, x.amount, x.name))

    def get_item_by_name(self, name: str) -> item.Item:
        for i in self.items:
            if i.name == name:
                return i
        else:
            return None
        
    def get_items_by_type(self, type: str) -> list[item.Item]:
        L=[]
        for i in self.items:
            if i.type == type:
                L.append(i)
        return sorted(L, key=lambda x: (x.name, x.durability))

    def add_items(self, *item: item.Item):
        for i in item:
            j = self.get_item_by_name(i.name)
            if j:
                j.stack(i)
            else:
                self.items.append(i)

    def remove_items(self, items: list[item.Item]):
        for item in items:
            self.items.remove(item)

    async def read_sql(id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db1, aiosqlite.connect(f'config/RPG/item.db') as db2:
            cur1 = await db1.execute(f'SELECT name FROM sqlite_master WHERE type="table" AND name=?;', ['inventory'])
            if await cur1.fetchone():
                L = []
                async with db1.execute(f'SELECT * FROM inventory;') as cur1:
                    async for name, type, amount, metadata in cur1:
                        if metadata:
                            metadata = json.loads(metadata)
                        if type == 'Item':
                            L.append(item.Item(name, amount))
                        elif type == 'Block':
                            cur2 = await db2.execute('SELECT * FROM Block WHERE name=?;', [name])
                            _, level, drop = await cur2.fetchone()
                            L.append(item.Block(name, amount, level, drop))
                        elif type == 'Tool':
                            cur2 = await db2.execute('SELECT * FROM Tool WHERE name=?;', [name])
                            _, level, _ = await cur2.fetchone()
                            L.append(item.Tool(name, amount, level, **metadata))
                        elif type == 'Ore':
                            cur2 = await db2.execute('SELECT * FROM Ore WHERE name=?;', [name])
                            _, level, drop, size, chance, zmin, zmax = await cur2.fetchone()
                            L.append(item.Ore(name, amount, level, drop, size, chance, zmin, zmax))
                        elif type == 'Food':
                            cur2 = await db2.execute('SELECT * FROM Food WHERE name=?;', [name])
                            _, saturation = await cur2.fetchone()
                            L.append(item.Food(name, amount, saturation))
                        else:
                            raise Exception('Unknown item type')
                return Inventory(L)
            else:
                return Inventory()

    async def write_sql(self, id: int):
        async with aiosqlite.connect(f'data/RPG/{id}.db') as db:
            await db.execute('DROP TABLE IF EXISTS `inventory`')
            await db.execute(f'CREATE TABLE "inventory" ("name" TEXT UNIQUE, "type", "amount" INTEGAR, "metadata" TEXT);')
            for item in self.items:
                if item.type == 'Item':
                    await db.execute(f'INSERT INTO "inventory" VALUES (?,?,?,?);', [item.name, item.type, item.amount, None])
                elif item.type == 'Block':
                    await db.execute(f'INSERT INTO "inventory" VALUES (?,?,?,?);', [item.name, item.type, item.amount, None])
                elif item.type == 'Tool':
                    await db.execute(
                        f'INSERT INTO "inventory" VALUES (?,?,?,?);',
                        [item.name, item.type, item.amount, json.dumps({"durability": item.durability})])
                elif item.type == 'Ore':
                    await db.execute(f'INSERT INTO "inventory" VALUES (?,?,?,?);', [item.name, item.type, item.amount, None])
                elif item.type == 'Food':
                    await db.execute(f'INSERT INTO "inventory" VALUES (?,?,?,?);', [item.name, item.type, item.amount, None])
                else:
                    raise Exception('Unknown item type')
            await db.commit()


class User:

    def __init__(self,
                 id: int,
                 name: str = None,
                 position: Position = Position(),
                 saturation=Saturation(),
                 currency=Currency(),
                 inventory=Inventory()) -> None:
        self.id = id
        self.name = name
        self.position = position
        self.saturation = saturation
        self.currency = currency
        self.inventory = inventory

    def __repr__(self) -> str:
        return f'User: {self.name or self.id}'

    async def read_sql(id: int, name: str = None):
        p = await Position.read_sql(id)
        s = await Saturation.read_sql(id)
        c = await Currency.read_sql(id)
        i = await Inventory.read_sql(id)
        return User(id, name, p, s, c, i)

    async def write_sql(self):
        await self.position.write_sql(self.id)
        await self.saturation.write_sql(self.id)
        await self.currency.write_sql(self.id)
        await self.inventory.write_sql(self.id)