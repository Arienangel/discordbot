import datetime

import discord
import discord.ui

from .user import *
from .activity import *


class RPG_dropdown(discord.ui.View):
    options = [
        discord.SelectOption(label='位置資訊', description='Position, ores, weather'),
        discord.SelectOption(label='營養資訊', description='Saturation level, balance, eat'),
        discord.SelectOption(label='物品及金錢', description='Inventory, currency, trade'),
        discord.SelectOption(label='工作', description='Gathering, mining, farming, crafting'),
        discord.SelectOption(label='專精', description='Ability level'),
    ]

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(custom_id='RPG_dropdown', placeholder='選擇', min_values=1, max_values=1, options=options)
    async def dropdown(self, interaction: discord.Interaction, select: discord.ui.Select):
        u = await User.read_sql(interaction.user.id)
        s = select.values[0]
        embed = discord.Embed(title=s, timestamp=datetime.datetime.now())
        if s == '位置資訊':
            p = u.position
            embed.add_field(name='位置', value=f'({p.x}, {p.y}, {p.z})')
            embed.add_field(name='此高度可取得礦物', value=', '.join(list(map(lambda x: x.name, Mine.get_possible_types(u.position)))), inline=False)
            #embed.add_field(name='氣候', value='')
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '營養資訊':
            s = u.saturation
            embed.description='使用方式: `/rpgeat 食物 數量`'
            embed.add_field(name='飽食度', value=f'{s.level}/{max(s.range)}')
            embed.add_field(name='可用食物', value=', '.join([f'{food.name}' for food in Eat.get_possible_types(u.inventory)]))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '物品及金錢':
            c = u.currency
            embed.add_field(name='金錢', value=f'${c.dollars}')
            i=u.inventory
            if len(i.items)==0:
                embed.add_field(name='物品', value='你現在什麼都沒有，先去撿一些木棒跟碎石做把鎬子，順便收集一些食物')
            else:
                L = []
                for x in i:
                    if 'durability' in x.metadata: L.append(f'{x.name}[{x["durability"]}]: {x.amount}')
                    else: L.append(f'{x.name}: {x.amount}')
                embed.add_field(name='物品', value='\n'.join(L))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '工作':
            embed.description = '\n'.join([
                '合成: 製作物品',
                '採集: 取得木棒、碎石、種子、野生動物',
                '挖礦: 取得礦物資源',
                '種田: 取得農作物及食物',
                '畜牧: 取得肉類及副產品',
            ])
            await interaction.response.send_message(embed=embed, view=Work_dropdown(), ephemeral=True)
        elif s == '專精':
            craft = u.abilitytree.get_ability_by_name('Craft')
            gather = u.abilitytree.get_ability_by_name('Gather')
            mine = u.abilitytree.get_ability_by_name('Mine')
            farm = u.abilitytree.get_ability_by_name('Farm')
            feed = u.abilitytree.get_ability_by_name('Feed')
            embed.description = '\n'.join([
                f'合成:  {craft.level}[{craft.experience}/{craft.upgrade_required}]',
                f'採集: {gather.level}[{gather.experience}/{gather.upgrade_required}]', f'挖礦:  {mine.level}[{mine.experience}/{mine.upgrade_required}]',
                f'種田:  {farm.level}[{farm.experience}/{farm.upgrade_required}]', f'畜牧:  {feed.level}[{feed.experience}/{feed.upgrade_required}]'
            ])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise TypeError('Unknown selection')


class Work_dropdown(discord.ui.View):
    options = [
        discord.SelectOption(label='合成'),
        discord.SelectOption(label='挖礦'),
        discord.SelectOption(label='採集'),
        discord.SelectOption(label='種田'),
        discord.SelectOption(label='畜牧'),
    ]

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(custom_id='Work_dropdown', placeholder='選擇', min_values=1, max_values=1, options=options)
    async def dropdown(self, interaction: discord.Interaction, select: discord.ui.Select):
        u = await User.read_sql(interaction.user.id)
        s = select.values[0]
        embed = discord.Embed(title=s, timestamp=datetime.datetime.now())
        if s == '合成':
            embed.description = '使用方式: `/rpgcraft 合成的物品 合成次數`，使用`/rpgrecipe`顯示合成方式'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '挖礦':
            embed.description = '使用方式: `/rpgmine 工具名稱(稿子)`\n你的稿子等級會決定能取得的礦物種類，等級越高能挖起越硬的礦物\n礦物分布會受到高度(z)影響，你可以在*位置資訊*中查看，使用`/rpggoto`移動位置'
            embed.add_field(name='你的工具',
                            value='\n'.join([f'{x.name}[{x["durability"]}]' for x in u.inventory.get_items_by_category('Pickaxe')]),
                            inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '採集':
            embed.description = '使用方式: `/rpggather`\n收集必要的資源，專精等級越高有機會得到稀有物品'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '種田':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '畜牧':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise TypeError('Unknown selection')
