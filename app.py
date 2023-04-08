import discord
from discord import app_commands
from discord.ext import tasks
from typing import Union
import datetime
import json
import sqlite3
import games, chatgpt


def load_config():
    with open('config/app.json', encoding='utf-8') as f:
        global conf
        conf = json.load(f)


load_config()
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_message(message: discord.Message):
    try:
        if message.author == client.user:
            return
        if message.content.startswith('$help'):
            pass
        if message.channel.id in conf['chatgpt']['channel']:
            if not message.content.startswith('##'):
                if len(message.content) > 0:
                    gpt = chatgpt.gpt35(message.content)
                    embed = discord.Embed(description=f'```{gpt.choices[0].message.content}```')
                    embed.set_author(name=gpt.model, icon_url=conf['chatgpt']['icon'])
                    embed.set_footer(text=f'id: {gpt.id}, tokens: {gpt.usage.total_tokens}')
                    await message.reply(embed=embed)
    finally:
        user = str(message.author)
        if message.guild: guild = message.guild.name
        else: return
        channel = message.channel.name
        time = (message.created_at + datetime.timedelta(hours=8)).strftime('%Y%m%d-%H%M%S')
        content = message.content
        with sqlite3.connect(f'data/{guild}.db') as con:
            cur = con.cursor()
            cur.execute(f'CREATE TABLE IF NOT EXISTS `{channel}` (time, user, content);')
            cur.execute(f'INSERT INTO `{channel}` VALUES (?,?,?);', [time, user, content])


@tree.command(name='help', description='Show help message')
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(conf['command']['help']['help_message'])


@tree.command(name='chance', description='算機率')
async def chance(interaction: discord.Interaction, ask: str = None):
    """
    Args:
        ask (str, optional): 事項
    """
    await interaction.response.send_message(f'{ask if ask else "機率"}: {games.chance()}')


@tree.command(name='fortune', description='你的運勢')
async def fortune(interaction: discord.Interaction, ask: str = None):
    """
    Args:
        ask (str, optional): 事項
    """
    await interaction.response.send_message(f'{ask if ask else "運勢"}: {games.fortune()}')


@tree.command(name='pick', description='多選一')
async def pick(interaction: discord.Interaction,
               a: str,
               b: str,
               c: str = None,
               d: str = None,
               e: str = None,
               f: str = None,
               g: str = None,
               h: str = None,
               i: str = None,
               j: str = None):
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
async def copy(interaction: discord.Interaction,
               message_id: str,
               channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread],
               notify: bool = True,
               origin: bool = True,
               copier: bool = False,
               title: str = None):
    """
    Args:
        message_id (str): 訊息ID
        channel (Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]): 頻道或討論串
        notify (bool, Optional): 顯示複製通知 (預設: True)
        origin (bool, Optional): 顯示原始訊息 (預設: True)
        copier (bool, Optional): 顯示複製者 (預設: False)
        title (str, Optional): 論壇頻道新增貼文的標題

    """
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.response.send_message("找不到此訊息", ephemeral=True)
        return
    if message.guild == channel.guild:
        try:
            embed = discord.Embed(description=message.content)
            embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
            if origin: embed.add_field(name='Copy from', value=message.jump_url, inline=False)
            if copier: embed.add_field(name='Copy by', value=interaction.user.mention, inline=False)
            if type(channel) is discord.ForumChannel:
                if not title:
                    await interaction.response.send_message(f"論壇頻道須輸入標題", ephemeral=True)
                    return
                else:
                    _, result = await channel.create_thread(name=title, embed=embed)
                    await interaction.response.send_message(f"複製訊息到: {result.jump_url}", ephemeral=(not notify))
            else:
                result = await channel.send(embed=embed)
                await interaction.response.send_message(f"複製訊息到: {result.jump_url}", ephemeral=(not notify))
        except:
            await interaction.response.send_message(f"無法傳送", ephemeral=True)
    else:
        await interaction.response.send_message("不在同一個伺服器", ephemeral=True)


@tree.command(name='anonymous', description='匿名傳送訊息')
async def anonymous(interaction: discord.Interaction,
                    channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread],
                    content: str,
                    title: str = None):
    """
    Args:
        channel (Union[discord.TextChannel,discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]): 頻道或討論串
        content (str): 內容
        title (str, Optional): 論壇頻道新增貼文的標題
    """
    try:
        embed = discord.Embed(description=content)
        embed.set_author(name='Anonymous', icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
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


@tree.command(name='reload', description='Reload bot config file')
async def reload(interaction: discord.Interaction):
    if interaction.user.id in conf['command']['reload']['permission']:
        load_config()
        await interaction.response.send_message("Finish", ephemeral=True)
    else:
        await interaction.response.send_message("Permission denied", ephemeral=True)


@tasks.loop(time=datetime.time(hour=13, minute=0, second=0))
async def goodnight():
    for channel_id in conf['goodnight']['channel']:
        try:
            channel = client.get_channel(channel_id)
            await channel.send('@everyone 晚上9點了該吃藥了')
        except:
            pass


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync()
    if not goodnight.is_running():
        goodnight.start()


if __name__ == '__main__':
    client.run(conf['TOKEN'])
