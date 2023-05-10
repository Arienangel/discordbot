import datetime

import discord
import discord.ui

from RPG import item
from RPG import user


class RPG_dropdown(discord.ui.View):
    options = [
        discord.SelectOption(label='位置資訊', description='Position, ores, weather'),
        discord.SelectOption(label='營養資訊', description='Saturation level, balance, eat'),
        discord.SelectOption(label='物品及金錢', description='Inventory, currency, trade'),
        discord.SelectOption(label='工作', description='Gathering, mining, farming, crafting'),
        discord.SelectOption(label='專精', description=''),
    ]

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(custom_id='RPG_dropdown', placeholder='選擇', min_values=1, max_values=1, options=options)
    async def dropdown(self, interaction: discord.Interaction, select: discord.ui.Select):
        u = await user.User.read_sql(interaction.user.id)
        s = select.values[0]
        embed = discord.Embed(title=s, timestamp=datetime.datetime.now())
        if s == '位置資訊':
            p = u.position
            embed.add_field(name='位置', value=f'({p.x}, {p.y}, {p.z})')
            embed.add_field(name='可取得礦物', value=', '.join(list(map(lambda x: x.name, await p.get_possible_oregen_type() ))), inline=False)
            #embed.add_field(name='氣候', value='')
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '營養資訊':
            s = u.saturation
            embed.add_field(name='飽食度', value=f'{s.level} ({s.min}~{s.max})')
            #embed.add_field(name='可用食物', value=', '.join([ore.name for ore in await p.get_possible_oregen_type()]))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '物品及金錢':
            c = u.currency
            embed.add_field(name='金錢', value=f'${c.dollars}')
            embed.add_field(name='物品',
                            value='\n'.join(
                                [f'{x.name}[{x.durability}]: {x.amount}' if isinstance(x, item.Tool) else f'{x.name}: {x.amount}' for x in u.inventory]))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '工作':
            embed.description = '\n'.join([
                '合成: 製作物品',
                '挖礦: 取得礦物資源',
                '採集: 取得木棒、碎石、種子、野生動物',
                '種田: 取得農作物及食物',
                '畜牧: 取得肉類及副產品',
            ])
            await interaction.response.send_message(embed=embed, view=Work_dropdown(), ephemeral=True)
        elif s == '專精':
            embed.description = '\n'.join(['採集', '挖礦', '種田', '畜牧', '合成'])
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise Exception('Unknown selection')


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
        u = await user.User.read_sql(interaction.user.id)
        s = select.values[0]
        embed = discord.Embed(title=s, timestamp=datetime.datetime.now())
        if s == '合成':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '挖礦':
            embed.description = '使用方式: `/rpg_mine 工具名稱(稿子)`\n你的稿子等級會決定能取得的礦物種類，等級越高能挖起越硬的礦物\n礦物分布會受到高度(z)影響，你可以在*位置資訊*中查看，使用`/goto`移動位置'
            embed.add_field(name='你的工具', value='\n'.join([f'{x.name}[{x.durability}]' for x in u.inventory.get_items_by_type('Tool')]), inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '採集':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '種田':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif s == '畜牧':
            embed.description = '未完成的內容'
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            raise Exception('Unknown selection')
