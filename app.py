import datetime
import re
from typing import Union

import aiosqlite
import discord
import yaml
from discord import app_commands, ui
from discord.ext import tasks

import chatgpt
import games
from RPG import *
from RPG_views import *


def load_config():
    with open('config/app.yaml', encoding='utf-8') as f:
        global conf
        conf = yaml.load(f, yaml.SafeLoader)['app']


load_config()
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_message(message: discord.Message):

    # forward private messages
    async def forward_private():
        embed = discord.Embed(description=message.content)
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
        embed.title = 'Private message'
        for attachment in message.attachments:
            embed.add_field(name=attachment.content_type, value=attachment.url, inline=False)
        for channel_id in conf['DM']['forward']:
            try:
                channel = await client.fetch_channel(channel_id)
                await channel.send(embed=embed)
            except:
                continue

    # chatgpt chatbot
    async def chatbot():
        wait = await message.reply('Waiting for reply...', allowed_mentions=discord.AllowedMentions.none())
        try:
            gpt, temp = await chatgpt.gpt35(message.content, conf['chatgpt']['temperature'])
            embed = discord.Embed(description=f'{gpt.choices[0].message.content}')
            embed.set_author(name=gpt.model, icon_url=conf['chatgpt']['icon'])
            embed.set_footer(text=f'temp: {round(temp, 2):.2f}, tokens: {gpt.usage.total_tokens}, id: {gpt.id}')
            await wait.edit(content=None, embed=embed)
        except:
            await wait.edit(content='Something went wrong')

    # record message to sql
    async def record_message():
        async with aiosqlite.connect(f'data/messages/{message.guild.id if message.guild else "private"}.db') as db:
            await db.execute(f'CREATE TABLE IF NOT EXISTS `{message.channel.id}` (id, time, user, content, attachment);')
            await db.execute(f'INSERT INTO `{message.channel.id}` VALUES (?,?,?,?,?);', [message.id, round(message.created_at.timestamp()), message.author.id, message.content, '\n'.join([attachment.url for attachment in message.attachments]) if message.attachments else None])
            await db.commit()

    await record_message()
    if message.author == client.user: return  # prevent loop
    if message.author.bot: return  # ignore bot messages
    if message.is_system(): return  # ignore system messages
    if isinstance(message.channel, discord.DMChannel): await forward_private()
    if message.channel.id in conf['chatgpt']['channel']:  # chatbot channel
        if not message.content.startswith('##'):  # ignore messages start with ##
            if not re.match('^<a{0,1}:.*?:\d+>', message.content):  # ignore messages start with emoji
                if len(message.content) > 0:  # ignore sticker or embed messages
                    await chatbot()


@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    if not payload.guild_id: return  ## private message
    if payload.channel_id in conf['on_message_delete']['ignore']: return  # blacklist channel
    try:
        if payload.guild_id in conf['on_message_delete']:
            async with aiosqlite.connect(f'data/{payload.guild_id}.db') as db:
                async with db.execute(f'SELECT * FROM `{payload.channel_id}` WHERE id=?;', [payload.message_id]) as cur:
                    async for row in cur:
                        user = await client.fetch_user(int(row[2]))
                        if user.bot: return  # ignore bot messages
                        text = f'**Message sent at <t:{row[1]}> by <@{row[2]}> Deleted in <#{payload.channel_id}>**'
                        if row[3]: text = text + '\n' + row[3]
                        if row[4]: text = text + '\n**Attachment**\n' + row[4]
                        embed = discord.Embed(description=text, color=discord.Colour.red(), timestamp=datetime.datetime.now())
                        embed.set_author(name=str(user), icon_url=user.display_avatar.url if user.display_avatar else None)
                        embed.set_footer(text=f'Message ID: {payload.message_id}')
                        for channel_id in conf['on_message_delete'][payload.guild_id]:
                            channel = await client.fetch_channel(int(channel_id))
                            await channel.send(embed=embed)
    except Exception as E:
        pass


@client.event
async def on_guild_emojis_update(guild: discord.Guild, before: list[discord.Emoji], after: list[discord.Emoji]):
    if guild.id in conf['on_guild_emojis_update']:
        for emoji in set(before).symmetric_difference(set(after)):
            if len(before) > len(after):
                embed = discord.Embed(description='Emoji Deleted', color=discord.Colour.red(), timestamp=datetime.datetime.now())
            elif len(before) < len(after):
                embed = discord.Embed(description='Emoji Created', color=discord.Colour.red(), timestamp=datetime.datetime.now())
            embed.set_author(name=f'{str(guild)}', icon_url=guild.icon.url if guild.icon else None)
            embed.set_image(url=emoji.url)
            for channel_id in conf['on_guild_emojis_update'][guild.id]:
                channel = await client.fetch_channel(int(channel_id))
                await channel.send(embed=embed)


@client.event
async def on_guild_stickers_update(guild: discord.Guild, before: list[discord.GuildSticker], after: list[discord.GuildSticker]):
    if guild.id in conf['on_guild_stickers_update']:
        for sticker in set(before).symmetric_difference(set(after)):
            if len(before) > len(after):
                embed = discord.Embed(description='Sticker Deleted', color=discord.Colour.red(), timestamp=datetime.datetime.now())
            elif len(before) < len(after):
                embed = discord.Embed(description='Sticker Created', color=discord.Colour.red(), timestamp=datetime.datetime.now())
            embed.set_author(name=f'{str(guild)}', icon_url=guild.icon.url if guild.icon else None)
            embed.set_image(url=sticker.url)
            for channel_id in conf['on_guild_stickers_update'][guild.id]:
                channel = await client.fetch_channel(int(channel_id))
                await channel.send(embed=embed)


@tree.command(name='help', description='Show help message')
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(conf['command']['help']['message'], ephemeral=True)


@tree.command(name='chance', description='算機率')
async def chance(interaction: discord.Interaction, ask: str = None):
    """
    Args:
        ask (str, optional): 事項
    """
    await interaction.response.send_message(f'{ask if ask else "機率"}: {round(games.chance(), 2):.0%}')


@tree.command(name='fortune', description='你的運勢')
async def fortune(interaction: discord.Interaction, ask: str = None):
    """
    Args:
        ask (str, optional): 事項
    """
    await interaction.response.send_message(f'{ask if ask else "運勢"}: {games.fortune()}')


@tree.command(name='pick', description='多選一')
async def pick(interaction: discord.Interaction, a: str, b: str, c: str = None, d: str = None, e: str = None, f: str = None, g: str = None, h: str = None, i: str = None, j: str = None):
    """
    Args:
        a (str): 事項1
        b (str): 事項2
        c (str, optional): 事項3
        d (str, optional): 事項4
        e (str, optional): 事項5
        f (str, optional): 事項6
        g (str, optional): 事項7
        h (str, optional): 事項8
        i (str, optional): 事項9
        j (str, optional): 事項10
    """
    S = {a, b, c, d, e, f, g, h, i, j}
    S.discard(None)
    await interaction.response.send_message(f'選擇: {games.pick(list(S))}')


@tree.command(name='cp', description='複製訊息到其他頻道')
async def copy(interaction: discord.Interaction, message_id: str, channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread], notify: bool = True, origin: bool = True, copier: bool = True, title: str = None):
    """
    Args:
        message_id (str): 訊息ID
        channel (Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]): 頻道或討論串
        notify (bool, Optional): 顯示複製通知 (預設: True)
        origin (bool, Optional): 顯示原始訊息 (預設: True)
        copier (bool, Optional): 顯示複製者 (預設: True)
        title (str, Optional): 論壇頻道新增貼文的標題，或是在一般訊息上新增標題

    """
    if not check_send_permission(interaction.user, channel):
        await interaction.response.send_message("你沒有在此頻道發送訊息的權限", ephemeral=True)
        return
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.response.send_message("找不到此訊息", ephemeral=True)
        return
    if message.guild == channel.guild:
        try:
            embed = discord.Embed(description=message.content)
            embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
            for attachment in message.attachments:
                embed.add_field(name=attachment.content_type, value=attachment.url, inline=False)
            if (origin or copier):
                field = ''
                if origin: field = f'{field}from {message.jump_url} '
                if copier: field = f'{field}by {interaction.user.mention} '
                embed.add_field(name='Message copied', value=field, inline=False)
            if type(channel) is discord.ForumChannel:
                if not title:
                    await interaction.response.send_message(f"論壇頻道須輸入標題", ephemeral=True)
                    return
                else:
                    _, result = await channel.create_thread(name=title, embed=embed)
                    await interaction.response.send_message(f"複製{message.jump_url}到{result.jump_url}", ephemeral=(not notify))
            else:
                if title: embed.title = title
                result = await channel.send(embed=embed)
                await interaction.response.send_message(f"複製{message.jump_url}到{result.jump_url}", ephemeral=(not notify))
        except:
            await interaction.response.send_message(f"無法傳送", ephemeral=True)
    else:
        await interaction.response.send_message("不在同一個伺服器", ephemeral=True)


@tree.command(name='qpoll', description='Quick poll')
async def qpoll(interaction: discord.Interaction, title: str = None, content: str = None):
    """
    Args:
        content (str, Optional): 內容
        title (str, Optional): 標題
    """
    embed = discord.Embed(title=title if title else '投票', description=content, timestamp=datetime.datetime.now())
    embed.add_field(name='⭕', value='')
    embed.add_field(name='❌', value='')
    embed.add_field(name='❓', value='')
    button = qpoll_button()
    await interaction.response.send_message(embed=embed, view=button)


class qpoll_button(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def edit(self, id, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        users = embed.fields[id].value.split(' ')
        user = f'<@{interaction.user.id}>'
        if user not in users:
            button.label = str(int(button.label) + 1)
            users.append(user)
        else:
            button.label = str(int(button.label) - 1)
            users.remove(user)
        embed.set_field_at(id, name=embed.fields[id].name, value=' '.join(users))
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='0', custom_id='qpoll:o', emoji='⭕')
    async def T(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.edit(0, interaction, button)

    @discord.ui.button(label='0', custom_id='qpoll:x', emoji='❌')
    async def F(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.edit(1, interaction, button)

    @discord.ui.button(label='0', custom_id='qpoll:q', emoji='❓')
    async def Q(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.edit(2, interaction, button)


@tree.command(name='anonymous', description='匿名傳送訊息')
@app_commands.checks.cooldown(3, 60)
async def anonymous(interaction: discord.Interaction, content: str, title: str = None, channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread] = None):
    """
    Args:
        content (str): 內容
        title (str, Optional): 論壇頻道新增貼文的標題，或是在一般訊息上新增標題
        channel (Union[discord.TextChannel,discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread], Optional): 頻道或討論串
    """
    if not check_send_permission(interaction.user, channel):
        await interaction.response.send_message("你沒有在此頻道發送訊息的權限", ephemeral=True)
        return
    try:
        embed = discord.Embed(description=content)
        embed.set_author(name='Anonymous', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        if not channel: channel = interaction.channel
        if type(channel) is discord.ForumChannel:
            if not title:
                await interaction.response.send_message(f"論壇頻道須輸入標題", ephemeral=True)
                return
            else:
                _, message = await channel.create_thread(name=title, embed=embed)
                await interaction.response.send_message(f"已傳送: {message.jump_url}", ephemeral=True)
        else:
            if title: embed.title = title
            message = await channel.send(embed=embed)
            await interaction.response.send_message(f"已傳送: {message.jump_url}", ephemeral=True)
    except:
        await interaction.response.send_message(f"傳送失敗", ephemeral=True)


@tree.command(name='report', description='Report issues')
@app_commands.checks.cooldown(1, 60)
async def report(interaction: discord.Interaction, content: str):
    """
    Args:
        content (str): 內容
    """
    embed = discord.Embed(description=content)
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None)
    embed.title = 'Report message'
    for channel_id in conf['command']['report']['forward']:
        try:
            channel = await client.fetch_channel(channel_id)
            await channel.send(embed=embed)
        except:
            continue
    await interaction.response.send_message(f"Finish", ephemeral=True)


@tree.command(name='reload', description='Reload bot config file')
async def reload(interaction: discord.Interaction):
    if interaction.user.id in conf['command']['reload']['permission']:
        load_config()
        await interaction.response.send_message("Finish", ephemeral=True)
    else:
        await interaction.response.send_message("Permission denied", ephemeral=True)


@tree.command(description='開始遊戲，顯示RPG資訊')
async def rpginfo(interaction: discord.Interaction):
    embed = discord.Embed(title='RPG資訊', timestamp=datetime.datetime.now())
    embed.description = f'使用方式\n```位置: 顯示目前座標及此高度可挖到的礦物\n健康: 工作會消耗飽食度，吃東西可回復飽食度\n物品: 顯示目前擁有的物品\n工作: 採集、挖礦、合成\n專精: 持續工作會提升專精等級```\n'
    embed.add_field(name='玩家', value=f'{interaction.user.mention}')
    embed.add_field(name='現在時間', value=f'<t:{round(datetime.datetime.now().timestamp())}>')
    await interaction.response.send_message(embed=embed, view=RPG_dropdown(), ephemeral=True)


@app_commands.checks.cooldown(1, 0)
@tree.command(description='吃東西')
async def rpgeat(interaction: discord.Interaction, food: str, amount: int = 1):
    """
    Args:
        food (str): 食物
        amount (int, Optional): 數量
    """
    u = await User.read_sql(interaction.user.id)
    s, eaten = u.do_activity('Eat', to_use=u.inventory[food], times=amount)
    embed = discord.Embed(title='吃東西', timestamp=datetime.datetime.now())
    embed.description = f'回復`{round(s, 1)}`飽食度\n目前飽食度: {u.health.saturation}/{max(u.health.saturation_range)}\n消耗食物: {eaten.display_name}\*{-eaten.amount}'
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await u.write_sql()


@rpgeat.autocomplete('food')
async def rpgeat_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    u = await User.read_sql(interaction.user.id)
    return [app_commands.Choice(name=i.display_name, value=i.uid) for i in u.inventory.group_items_by_category['food']]


@app_commands.checks.cooldown(1, 0)
@tree.command(description='合成')
async def rpgcraft(interaction: discord.Interaction, item: str, times: int = 1):
    """
    Args:
        item (str): 合成的物品
        times (int, Optional): 合成次數
    """
    u = await User.read_sql(interaction.user.id)
    res, used = u.do_activity('Craft', to_craft=Item.get_default(item), times=times)
    embed = discord.Embed(title='合成結果', timestamp=datetime.datetime.now())
    embed.description = f'合成\n```{res.display_name}: {res.amount}```\n消耗\n```' + '\n'.join([f'{x.display_name}: {-x.amount}' for x in used]) + '```'
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await u.write_sql()


@rpgcraft.autocomplete('item')
async def rpgcraft_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    u = await User.read_sql(interaction.user.id)
    return [app_commands.Choice(name=i.display_name, value=i.id) for i in u.get_possible_craft]


@app_commands.checks.cooldown(1, 0)
@tree.command(description='燒製')
async def rpgsmelt(interaction: discord.Interaction, furnace: str, fuel: str, fuel_amount: int, item: str, times: int = 1):
    """
    Args:
        furnace (str): 熔爐
        fuel (str): 燃料
        fuel_amount (int): 燃料數量
        item (str): 合成的物品
        times (int, Optional): 合成次數
    """
    u = await User.read_sql(interaction.user.id)
    res, used, fur = u.do_activity('Smelt', to_craft=Item.get_default(item), times=times, fuel=Item.get_default(fuel, fuel_amount), furnace=u.inventory[furnace])
    embed = discord.Embed(title='燒製中', timestamp=datetime.datetime.now())
    embed.add_field(name='燒製', value=f'{res.display_name}: {res.amount}')
    embed.add_field(name='消耗', value='\n'.join([f'{x.display_name}: {-x.amount}' for x in used]))
    embed.add_field(name='熔爐', value=f'{fur.display_name}[{fur.tag["durability"]}]')
    embed.add_field(name='完成時間', value=f'<t:{fur.tag["pending"]}:R>')
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await u.write_sql()


@rpgsmelt.autocomplete('furnace')
async def rpgsmelt_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    u = await User.read_sql(interaction.user.id)
    return [app_commands.Choice(name=i.display_name, value=i.uid) for i in u.inventory.group_items_by_category['structure:furnace'] if 'pending' not in i.tag]


@rpgsmelt.autocomplete('fuel')
async def rpgsmelt_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    u = await User.read_sql(interaction.user.id)
    return [app_commands.Choice(name=i.display_name, value=i.id) for i in u.inventory.group_items_by_category['ore:fuel']]


@rpgsmelt.autocomplete('item')
async def rpgsmelt_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    u = await User.read_sql(interaction.user.id)
    return [app_commands.Choice(name=i.display_name, value=i.id) for i in u.get_possible_smelt]


@app_commands.checks.cooldown(1, 0)
@tree.command(description='合成方式')
async def rpgrecipe(interaction: discord.Interaction, item: str):
    """
    Args:
        item (str): 合成的物品
    """
    key, values = list(User.get_recipe(item).items())[0]
    text = f'{key.display_name}\*`{key.amount}`=' + '+'.join([f'{x.display_name}\*`{x.amount}`' for x in values['recipe']])
    embed = discord.Embed(title='合成方式', description=text, timestamp=datetime.datetime.now())
    if 'temperature' in values:
        embed.add_field(name='溫度', value=f"{values['temperature']}°C")
        embed.add_field(name='時間', value=f"{values['duration']}s")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@rpgrecipe.autocomplete('item')
async def rpgrecipe_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=list(i.keys())[0].display_name, value=list(i.keys())[0].id) for i in User.get_recipe() if current in list(i.keys())[0].display_name][:25]


@app_commands.checks.cooldown(1, 0)
@tree.command(description='採集')
async def rpggather(interaction: discord.Interaction):
    u = await User.read_sql(interaction.user.id)
    res = u.do_activity('Gather')
    embed = discord.Embed(title='採集結果', timestamp=datetime.datetime.now())
    if res:
        embed.description = '你採到了\n```' + '\n'.join([f'{x.display_name}: {x.amount}' for x in res]) + '```'
    else:
        embed.description = '你沒有採到任何東西，空手而歸'
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await u.write_sql()


@app_commands.checks.cooldown(1, 0)
@tree.command(description='挖礦')
async def rpgmine(interaction: discord.Interaction, tool: str):
    """
    Args:
        tool (str): 工具名稱
    """
    u = await User.read_sql(interaction.user.id)
    tool = u.inventory[tool]
    res = u.do_activity('Mine', tool=tool)
    embed = discord.Embed(title='挖礦結果', timestamp=datetime.datetime.now())
    if res:
        embed.description = '你挖到了\n```' + '\n'.join([f'{x.display_name}: {x.amount}' for x in res]) + '```'
    else:
        embed.description = '你沒有挖到任何東西，空手而歸'
    embed.add_field(name='工具', value=f'```{tool.display_name}[{tool.tag["durability"]}]```')
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await u.write_sql()


@rpgmine.autocomplete('tool')
async def rpgmine_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    u = await User.read_sql(interaction.user.id)
    return [app_commands.Choice(name=i.display_name, value=i.uid) for i in u.inventory.group_items_by_category['tool:pickaxe']]


@tree.command(description='移動位置')
async def rpggoto(interaction: discord.Interaction, z: int = 64, x: int = 0, y: int = 0):
    """
    Args:
        z (int, optional): 高度 (0~64地表)
        x (int, optional): 東西向
        y (int, optional): 南北向
    """
    u = await User.read_sql(interaction.user.id)
    u.position.goto(x, y, z)
    embed = discord.Embed(title='移動位置到', description=str(u.position.coordinate), timestamp=datetime.datetime.now())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await u.write_sql()


@tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.errors.AppCommandError):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f'Time out. Retry after {round(error.retry_after)}s', ephemeral=True)
    if isinstance(error.original, RPG_exception):
        await interaction.response.send_message(f'{error.original}', ephemeral=True)
    else:
        await interaction.response.send_message(f'Something went wrong', ephemeral=True)


@tasks.loop(time=datetime.time(hour=13, minute=0, second=0))
async def goodnight():
    for channel_id in conf['event']['goodnight']['channel']:
        try:
            channel = client.get_channel(channel_id)
            await channel.send(conf['event']['goodnight']['message'])
        except:
            continue


@client.event
async def on_ready():
    client.add_view(qpoll_button())
    client.add_view(RPG_dropdown())
    client.add_view(Work_dropdown())
    await tree.sync()
    if not goodnight.is_running():
        goodnight.start()


def check_send_permission(user: discord.User, channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]) -> bool:
    if isinstance(channel, discord.Thread) and channel.permissions_for(user).send_messages_in_threads is False: return False
    elif isinstance(channel, discord.ForumChannel) and channel.permissions_for(user).create_public_threads is False: return False
    elif isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)) and channel.permissions_for(user).send_messages is False:
        return False
    else:
        return True


if __name__ == '__main__':
    client.run(conf['bot']['token'])
