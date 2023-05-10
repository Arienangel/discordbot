class Item:

    def __init__(self, name: str, amount: int = 0, stackable: bool = True) -> None:
        self.type='Item'
        self.name = name
        self.amount = amount
        self.stackable = stackable
    def __repr__(self) -> str:
        return f'({self.name}: {self.amount})'

    def stack(self, item):
        if not self.stackable: raise Exception('Not stackable')
        if type(self) is not type(item): raise Exception('Different type')
        if self.name != item.name: raise Exception('Different name')
        self.amount = self.amount + item.amount


class Block(Item):

    def __init__(self, name: str, amount: int = 0, level: int = 0, drop: Item = True) -> None:
        super().__init__(name, amount, stackable=True)
        self.type='Block'
        self.level = level
        self.drop = self


class Ore(Block):

    def __init__(self,
                 name: str,
                 amount: int = 0,
                 level: int = 0,
                 drop: Item | bool = True,
                 size: int = 0,
                 chance: int = 0,
                 zmin: int = 0,
                 zmax: int = 0) -> None:
        super().__init__(name, amount, level, drop)
        self.type='Ore'
        self.size = size
        self.chance = chance
        self.zmin = zmin
        self.zmax = zmax

    async def read_sql(self):
        pass


class Tool(Item):

    def __init__(self, name: str, amount: int = 0, level: int = 0, durability: int = 100) -> None:
        super().__init__(name, amount, stackable=False)
        self.type='Tool'
        self.level = level
        self.durability = durability
    def __repr__(self) -> str:
        return f'({self.name}({self.durability}): {self.amount})'


class Food(Item):

    def __init__(self, name: str, amount: int = 0, saturation: float = 0) -> None:
        super().__init__(name, amount, stackable=True)
        self.type='Food'
        self.saturation = saturation
