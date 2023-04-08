import discord
from discord import app_commands
from discord.ext import tasks
from typing import Union
import datetime
import yaml
import sqlite3
import games, chatgpt


def load_config():
    with open('config.yaml', encoding='utf-8') as f:
        global conf
        conf = yaml.load(f, yaml.SafeLoader)['app']


load_config()
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_message(message: discord.Message):
    try:
        if message.author == client.user: return # prevent loop
        if message.is_system(): return # ignore system messages
        if isinstance(message.channel, discord.DMChannel): # forward private messages
            for user_id in conf['DM']['forward']:
                try: 
                    user = await client.fetch_user(user_id)
                    embed = discord.Embed(description=message.content)
                    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url if message.author.display_avatar else None)
                    for attachment in message.attachments:
                        embed.add_field(name=attachment.content_type, value=attachment.url, inline=False)
                    await user.send(embed=embed)
                except: continue
        if message.channel.id in conf['chatgpt']['channel']: # chatgpt chatbot
            if not message.content.startswith('##'): # ignore messages start with ##
                if len(message.content) > 0: # ignore sticker or embed messages
                    gpt = await chatgpt.gpt35(message.content)
                    embed = discord.Embed(description=f'{gpt.choices[0].message.content}')
                    embed.set_author(name=gpt.model, icon_url=conf['chatgpt']['icon'])
                    embed.set_footer(text=f'tokens: {gpt.usage.total_tokens}, id: {gpt.id}')
                    await message.reply(embed=embed)
    finally: # record message to sql
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
    await interaction.response.send_message(conf['command']['help']['message'], ephemeral=True)


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
               copier: bool = True,
               title: str = None):
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


@tree.command(name='anonymous', description='匿名傳送訊息')
async def anonymous(interaction: discord.Interaction,
                    content: str,
                    title: str = None,
                    channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread] = None):
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


@tree.command(name='reload', description='Reload bot config file')
async def reload(interaction: discord.Interaction):
    if interaction.user.id in conf['command']['reload']['permission']:
        load_config()
        await interaction.response.send_message("Finish", ephemeral=True)
    else:
        await interaction.response.send_message("Permission denied", ephemeral=True)


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
    print(f'We have logged in as {client.user}')
    await tree.sync()
    if not goodnight.is_running():
        goodnight.start()


def check_send_permission(user: discord.User, channel: Union[discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread])->bool:
    if isinstance(channel, discord.Thread) and channel.permissions_for(user).send_messages_in_threads is False: return False
    elif isinstance(channel, discord.ForumChannel) and channel.permissions_for(user).create_public_threads is False: return False
    elif isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)) and channel.permissions_for(user).send_messages is False: return False
    else: return True

if __name__ == '__main__':
    client.run(conf['bot']['token'])
