import datetime
import re
from typing import Union

import aiosqlite
import aiohttp
import discord
import urllib.parse
import numpy as np
import yaml
from discord import app_commands, ui
from discord.ext import tasks
from pyquery import PyQuery as pq

import chatgpt

with open('config/app.yaml', encoding='utf-8') as f:
    conf = yaml.load(f, yaml.SafeLoader)['app']

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
        if not message.content.startswith('//'):  # ignore messages start with //
            if not re.match('^<a{0,1}:.*?:\d+>', message.content):  # ignore messages start with emoji
                if len(message.content) > 0:  # ignore sticker or embed messages
                    await chatbot()


@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    if not payload.guild_id: return  ## private message
    if payload.channel_id in conf['on_message_delete']['ignore']: return  # blacklist channel
    try:
        if payload.guild_id in conf['on_message_delete']:
            async with aiosqlite.connect(f'data/messages/{payload.guild_id}.db') as db:
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


@tree.command(name='help', description='顯示說明')
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(conf['command']['help']['message'], ephemeral=True)


@tree.command(name='chance', description='算機率')
async def chance(interaction: discord.Interaction, ask: str = None):
    """
    Args:
        ask (str, optional): 事項
    """
    start, end = sorted(conf['command']['chance'])
    res = np.random.randint(low=start * 100, high=end * 100)
    await interaction.response.send_message(f'{ask if ask else "機率"}: {res}%')


@tree.command(name='dice', description='擲骰子')
async def dice(interaction: discord.Interaction, n: int = 6):
    """
    Args:
        n (int, optional): 最大數字
    """
    await interaction.response.send_message(f'{np.random.randint(1, n)}')


@tree.command(name='fortune', description='你的運勢')
async def fortune(interaction: discord.Interaction, ask: str = None):
    """
    Args:
        ask (str, optional): 事項
    """
    res = np.random.choice(conf['command']['fortune']['key'], p=conf['command']['fortune']['ratio'])
    await interaction.response.send_message(f'{ask if ask else "運勢"}: {res}')


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
    await interaction.response.send_message(f'選擇: {np.random.choice(list(S))}')

@tree.command(name='fbid', description='FB網址轉換')
async def fbid(interaction: discord.Interaction, url: str):
    """
    Args:
        url (str): 網址
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://www.facebook.com/plugins/post.php?href={urllib.parse.quote_plus(url)}') as response:
            s=pq(await response.text())
            url=s('a._39g5').attr('href')
            if not url:
                url=s('a._2q21').attr('href')
            if url:
                if 'permalink.php?story_fbid=' in url:
                    post, page=re.search(r'/permalink.php\?story_fbid=(\d+)&id=(\d+)', url).group(1,2)
                    await interaction.response.send_message(f"https://www.facebook.com/{page}/posts/{post}", ephemeral=True)
                else:
                    await interaction.response.send_message(f"https://www.facebook.com{url.split('?')[0]}", ephemeral=True)
            else:
                await interaction.response.send_message('Not found', ephemeral=True)

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


@tree.command(name='poll', description='投票:⭕/❌/❓')
async def poll(interaction: discord.Interaction, title: str = None, content: str = None):
    """
    Args:
        content (str, Optional): 內容
        title (str, Optional): 標題
    """
    embed = discord.Embed(title=title if title else '投票', description=content, timestamp=datetime.datetime.now())
    embed.add_field(name='⭕', value='')
    embed.add_field(name='❌', value='')
    embed.add_field(name='❓', value='')
    button = poll_button()
    await interaction.response.send_message(embed=embed, view=button)


class poll_button(discord.ui.View):

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

    @discord.ui.button(label='0', custom_id='poll:o', emoji='⭕')
    async def T(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.edit(0, interaction, button)

    @discord.ui.button(label='0', custom_id='poll:x', emoji='❌')
    async def F(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.edit(1, interaction, button)

    @discord.ui.button(label='0', custom_id='poll:q', emoji='❓')
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


@tree.command(name='report', description='回報錯誤')
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


@tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.errors.AppCommandError):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f'Time out. Retry after {round(error.retry_after)}s', ephemeral=True)
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
    client.add_view(poll_button())
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
