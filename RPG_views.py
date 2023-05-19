import datetime

import discord
import discord.ui

from RPG import *


class RPG_dropdown(discord.ui.View):
    options = [
        discord.SelectOption(label='位置資訊', description='Position, weather'),
        discord.SelectOption(label='健康資訊', description='Saturation level, balance, eat'),
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
            #embed.add_field(name='氣候', value='')
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '健康資訊':
            s = u.health
            embed.description = '使用方式: `/rpgeat 食物 數量`'
            embed.add_field(name='生命值', value=f'{s.health}/{max(s.health_range)}')
            embed.add_field(name='飽食度', value=f'{s.saturation}/{max(s.saturation_range)}')
            embed.add_field(name='營養均衡', value=f'{round(s.nutrient_balance, 2)}/1.0')
            embed.add_field(name='營養值', value='\n'.join([f'{key}: {value} [{round(s.nutrient_level(key), 2)}/1.0]' for key, value in s.nutrient.items()]))
            g = u.inventory.group_items_by_category
            if 'food' in g:
                embed.add_field(name='可用食物', value=', '.join([f'{food.display_name}' for food in u.inventory.group_items_by_category['food']]))
            else:
                embed.add_field(name='可用食物', value='你現在什麼都沒有，先去撿一些木棒跟碎石做把鎬子，順便收集一些食物')
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '物品及金錢':
            c = u.finance
            embed.add_field(name='金錢', value=f'存款: ${c.deposit}\n債務: ${c.debt}')
            i = u.inventory
            if len(i.items) == 0:
                embed.add_field(name='物品', value='你現在什麼都沒有，先去撿一些木棒跟碎石做把鎬子，順便收集一些食物')
            else:
                for category, i in u.inventory.group_items_by_category.items():
                    L=[]
                    for x in i:
                        if 'pending' in x.tag: L.append(f'{x.display_name}[使用中]: {x.amount}')
                        elif 'durability' in x.tag: L.append(f'{x.display_name}[{x.tag["durability"]}]: {x.amount}')
                        else: L.append(f'{x.display_name}: {x.amount}')
                    embed.add_field(name=category, value='\n'.join(L))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '工作':
            embed.description = '\n'.join([
                '採集: 取得木棒、碎石、種子、野生動物',
                '挖礦: 取得礦物資源',
                '合成: 製作物品',
                '燒製: 利用熔爐燒製物品',
                '種田: 取得農作物及食物',
                '畜牧: 取得肉類及副產品',
                '捕魚: 取得海鮮及副產品',
            ])
            await interaction.response.send_message(embed=embed, view=Work_dropdown(), ephemeral=True)
        elif s == '專精':
            a = u.abilitytree
            gather = a['Gather']
            mine = a['Mine']
            craft = a['Craft']
            smelt = a['Smelt']
            farm = a['Farm']
            feed = a['Feed']
            fish = a['Fish']
            embed.description = '\n'.join([
                f'採集: {gather.level} [{gather.experience}/{gather.upgrade_required}]', f'挖礦:  {mine.level} [{mine.experience}/{mine.upgrade_required}]', f'合成:  {craft.level} [{craft.experience}/{craft.upgrade_required}]', f'燒製:  {smelt.level} [{smelt.experience}/{smelt.upgrade_required}]',
                f'種田:  {farm.level} [{farm.experience}/{farm.upgrade_required}]', f'畜牧:  {feed.level} [{feed.experience}/{feed.upgrade_required}]', f'捕魚:  {fish.level} [{fish.experience}/{fish.upgrade_required}]'
            ])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise TypeError('Unknown selection')


class Work_dropdown(discord.ui.View):
    options = [
        discord.SelectOption(label='採集'),
        discord.SelectOption(label='挖礦'),
        discord.SelectOption(label='合成'),
        discord.SelectOption(label='燒製'),
        discord.SelectOption(label='種田'),
        discord.SelectOption(label='畜牧'),
        discord.SelectOption(label='捕魚'),
    ]

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(custom_id='Work_dropdown', placeholder='選擇', min_values=1, max_values=1, options=options)
    async def dropdown(self, interaction: discord.Interaction, select: discord.ui.Select):
        u = await User.read_sql(interaction.user.id)
        s = select.values[0]
        embed = discord.Embed(title=s, timestamp=datetime.datetime.now())
        if s == '採集':
            embed.description = '使用方式: `/rpggather`\n收集必要的資源，專精等級越高有機會得到稀有物品\n你需要在地表'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '挖礦':
            embed.description = '使用方式: `/rpgmine 工具名稱(稿子)`\n你的稿子等級會決定能取得的礦物種類，等級越高能挖起越硬的礦物\n礦物分布會受到高度(z)影響，你可以在*位置資訊*中查看，使用`/rpggoto`移動位置'
            ore = u.get_possible_ore
            if ore:
                embed.add_field(name='在此高度及工具可取得的礦物', value=', '.join(list(map(lambda x: x.display_name, ore))), inline=False)
            else:
                embed.add_field(name='在此高度及工具可取得的礦物', value='你還挖不到什麼礦', inline=False)
            t = u.inventory.group_items_by_category
            if 'tool:pickaxe' in t:
                embed.add_field(name='你的工具', value='\n'.join([f'{x.display_name}[{x.tag["durability"]}]' for x in t['tool:pickaxe']]), inline=False)
            else:
                embed.add_field(name='你的工具', value='你還沒有鎬子，快去合成一把', inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '合成':
            embed.description = '使用方式: `/rpgcraft 合成的物品 合成次數`，使用`/rpgrecipe`顯示合成方式'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '燒製':
            embed.description = '使用方式: `/rpgsmelt 合成的物品 合成次數 燃料 燃料數量 熔爐`，使用`/rpgrecipe`顯示合成方式'
            f=u.get_possible_fuel
            if len(f):
                embed.add_field(name='燃料 (溫度, 燃燒時間)', value='\n'.join([f'{list(x.keys())[0].display_name}:  {list(x.values())[0]["temperature"]}°C, {list(x.values())[0]["duration"]}s' for x in f]), inline=False)
            else: 
                embed.add_field(name='燃料 (溫度, 燃燒時間)', value='你還沒有燃料，去地下挖一些煤炭回來', inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '種田':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '畜牧':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '捕魚':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise TypeError('Unknown selection')
