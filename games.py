import random, math


def chance():
    n = random.random() * 91 + 5
    return f'{n:.0f}%'


def fortune():
    L = ["大吉", "吉", "小吉", "尚可", "小兇", "兇", "大凶"]
    n = random.random()
    if (0 <= n < 0.05): return L[0]
    elif (0.05 <= n < 0.1): return L[6]
    elif (0.1 <= n < 0.2): return L[1]
    elif (0.2 <= n < 0.3): return L[5]
    elif (0.3 <= n < 0.5): return L[2]
    elif (0.5 <= n < 0.7): return L[4]
    else: return L[3]


def pick(items):
    return items[math.floor(random.random() * len(items))]
