import logging
import os
import time
from collections import defaultdict

import discord
import requests
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.ui import Select, View

import yandex_music_api
from settings import discord_settings
from yandex_music_api import get_tracks_info, download_track

import asyncio

logging.basicConfig(
    filename='events.log',
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

bot = commands.Bot(command_prefix=discord_settings['command_prefix'],
                   intents=discord.Intents.all())

queue = defaultdict(list)
to_chose = defaultdict(list)

@bot.event
async def on_ready():
    print("Бот готов к работе.")
    while True:
        await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name=f'!bhelp',
                                                                                          type=discord.ActivityType.listening))  # Идёт инфа о команде помощи (префикс изменить)
        await asyncio.sleep(15)


@bot.command()
async def bhelp(ctx):
    embed = discord.Embed(color=0xff9900, title="Информация о командах")
    embed.add_field(name=f"`!bhelp` : ", value="**Вызовет это меню**", inline=False)
    embed.add_field(name=f"`!p <YourMusic>` или `!play <YourMusic>` : ",
                    value="**Выведет 10 найденных треков на выбор**", inline=False)
    embed.add_field(name=f"`!pb <YourMusic>` или `!playbest <YourMusic>` : ",
                    value="**Сразу добавит первый найденный трек в очередь**", inline=False)
    embed.add_field(name=f"`!playlist` : ", value="**Выведет информацию об очереди**", inline=False)
    embed.add_field(name=f"`!pause` : ", value="**Поставит проигрывание музыки на паузу**", inline=False)
    embed.add_field(name=f"`!resume` : ", value="**Возобновит проигрывание музыки**", inline=False)
    embed.add_field(name=f"`!skip` : ", value="**Пропустить текущий трек**", inline=False)
    embed.add_field(name=f"`!join` : ", value="**Бот подключится к вашему голосовому каналу**", inline=False)
    embed.add_field(name=f"`!leave` : ", value="**Бот покинет голосовой канал**", inline=False)
    embed.add_field(name=f"`!hello` : ", value="**Поприветствовать бота**", inline=False)
    embed.add_field(name=f"`!randomimage` : ", value="**Покажет случайную картинку**", inline=False)
    await ctx.send(ctx.message.author.mention, embed=embed, reference=ctx.message)

def mls_to_sm(x):
    return f'{x // 60 // 1000}:{str(x // 1000 - x // 60 // 1000 * 60).rjust(2, "0")}'


async def play_queue(ctx: discord.ext.commands.context.Context):
    print('play_queue func started')
    channel_id = ctx.channel.id
    voice = ctx.voice_client

    while queue[channel_id]:
        if len(queue[channel_id]) >= 3:
            yandex_music_api.download_track(queue[channel_id][2]['id'], path=str(channel_id) + '/')

        source = FFmpegPCMAudio(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3', executable=discord_settings[
            'ffmpeg_path'])

        voice.play(source)
        print('Started playing...')
        await asyncio.sleep(queue[channel_id][0]["duration"] / 1000 + 0.1)
        print('Stopped playing...')

        if len(queue[channel_id]) >= 2:
            if queue[channel_id][0]["id"] != queue[channel_id][1]["id"]:
                os.remove(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3')
                print('File deleted...')
        else:
            os.remove(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3')
            print('File deleted...')
        del queue[channel_id][0]


@bot.command()
async def playlist(ctx):  # Информация об очереди
    embed = discord.Embed(color=0xff9900, title='Очередь из треков')
    channel_id = ctx.channel.id

    embed = discord.Embed(color=0xff9900, title='Очередь из треков')

    if len(queue[channel_id]) > 1:
        to_print = ''
        now_playing = ''
        for n, track in enumerate(queue[channel_id]):
            if n == 0:
                now_playing = f"**{track['title']} - {track['artists']}** `Длительность: {mls_to_sm(track['duration'])}`"
            else:
                to_print += f"**{n}**: **{track['title']} - {track['artists']}** `Длительность: {mls_to_sm(track['duration'])}`\n"
        embed.add_field(name='Сейчас играет', value=f"{now_playing}", inline=False)
        embed.add_field(name='В очереди', value=f"{to_print}", inline=False)

    elif len(queue[channel_id]) == 1:
        now_playing = f"**{queue[channel_id][0]['title']} - {queue[channel_id][0]['artists']}** `Длительность: {mls_to_sm(queue[channel_id][0]['duration'])}`"
        embed.add_field(name='Сейчас играет', value=f"{now_playing}", inline=False)
    else:
        embed = discord.Embed(color=0xff9900, title='Я ничего не играю',
                              description='**В данный момент очередь пуста!**')

    embed.set_footer(**discord_settings['embed_footer'])
    await ctx.send(ctx.message.author.mention, embed=embed, reference=ctx.message)


@bot.command()
async def hello(ctx):
    print(type(ctx))
    author = ctx.message.author

    await ctx.send(f'Привет, {author.mention}!', reference=ctx.message)


@bot.command()
async def randomimage(ctx: discord.ext.commands.context.Context):
    response = requests.get(f'https://picsum.photos/1024')
    embed = discord.Embed(color=0xff9900, title='Random Image')
    embed.set_footer(**discord_settings['embed_footer'])
    embed.set_image(url=response.url)
    await ctx.send(ctx.message.author.mention, embed=embed, reference=ctx.message)


@bot.command()
async def pause(ctx):
    if not ctx.voice_client.is_paused():
        ctx.voice_client.pause()
        await ctx.send(ctx.message.author.mention + ' **приостановил воспроизведение музыки.**', reference=ctx.message)


@bot.command()
async def skip(ctx: discord.ext.commands.context.Context):
    channel_id = ctx.channel.id

    if not ctx.voice_client:
        embed = discord.Embed(color=0xff9900, title='**В данный момент очередь пуста!**')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)
        return

    ctx.voice_client.stop()
    if queue[channel_id]:

        embed = discord.Embed(color=0xff9900, title='**Вы успешно пропустили трек**')
        embed.add_field(value=f'**{queue[channel_id][1]["title"]}** - {queue[channel_id][1]["artists"]}',
                        name=f"**Сейчас играет:**",
                        inline=False)
        embed.set_image(url=queue[channel_id][1]['image_url'])
        embed.set_footer(**discord_settings['embed_footer'])

        await ctx.send(ctx.author.mention, embed=embed, reference=ctx.message)

        del queue[channel_id][0]

        await play_queue(ctx)

    else:
        embed = discord.Embed(color=0xff9900, title='**Вы успешно пропустили трек!**',
                              description='В данный момент очередь пуста')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(ctx.author.mention, embed=embed, reference=ctx.message)


@bot.command()
async def s(ctx):
    await skip(ctx)


@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send(ctx.message.author.mention + ' **продолжил воспроизведение музыки.**', reference=ctx.message)


@bot.command()
async def play(ctx, *, name_of_song):
    channel_id = ctx.channel.id

    if not ctx.message.author.voice:
        await ctx.send(ctx.message.author.mention +
                       '\n**Я не могу включить Вам песенку, Вы же не в чате**', reference=ctx.message)
        return

    tracks_info = get_tracks_info(name_of_song)
    message_1 = await ctx.send('***Ищу вашу песенку в Яндекс Музыке...***')

    if not tracks_info:
        await ctx.send(f'{ctx.message.author.mention} К сожалению, я не ничего не нашёл', reference=ctx.message)
        return

    to_say = ''
    embed = discord.Embed(color=0xff9900, title='**Вот что я нашёл!**')
    a = list()
    for i, track in enumerate(tracks_info, 1):
        duration = (lambda x: f'{x // 60 // 1000}:{str(x // 1000 - x // 60 // 1000 * 60).rjust(2, "0")}')(
            track["duration"])
        a.append(track)
        artists = track['artists']

        to_say += f'**{i}: {track["title"]}** - {artists}  (`Длительность: {duration}`)\n'

    to_chose[channel_id] = a.copy()
    embed.add_field(name="", value=f"{to_say}", inline=False)
    embed.set_footer(**discord_settings['embed_footer'])

    selectmenu = Select(options=[
        discord.SelectOption(label=f'{i}: {track["title"][:50]} - {track["artists"][:40]}') for i, track in
        enumerate(tracks_info, 1)
    ])

    view = View()
    view.add_item(selectmenu)

    async def my_callback(interaction: discord.Interaction):
        await message.delete()
        await message_1.delete()
        await c(ctx, int(selectmenu.values[0][0]))

    selectmenu.callback = my_callback

    message = await ctx.send(ctx.message.author.mention, embed=embed, view=view, reference=ctx.message)


@bot.command()
async def p(ctx, *, name_of_song):
    await play(ctx, name_of_song=name_of_song)


@bot.command()
async def playbest(ctx, *, name_of_song):
    channel_id = ctx.channel.id

    if not ctx.message.author.voice:
        await ctx.send(ctx.message.author.mention +
                       '\n**Я не могу включить Вам песенку, Вы же не в чате**', reference=ctx.message)
        return

    tracks_info = get_tracks_info(name_of_song, count=1)
    if not tracks_info:
        await ctx.send(f'{ctx.message.author.mention} К сожалению, я не ничего не нашёл', reference=ctx.message)
        return

    to_chose[channel_id] = [tracks_info[0]]
    await c(ctx, 1)


@bot.command()
async def pb(ctx, *, name_of_song):
    await playbest(ctx, name_of_song=name_of_song)


@bot.command()
async def join(ctx):
    if not ctx.voice_client:
        await ctx.message.author.voice.channel.connect()
        time.sleep(1)


async def c(ctx: discord.ext.commands.context.Context, num: int):
    print('c func started')
    await join(ctx)

    channel_id = ctx.channel.id

    num = num - 1

    queue[channel_id].append(to_chose[channel_id][num])

    embed = discord.Embed(color=0xff9900,
                          title=f'**{to_chose[channel_id][num]["title"]}** - {to_chose[channel_id][num]["artists"]}')
    embed.set_image(url=to_chose[channel_id][num]['image_url'])
    embed.set_footer(**discord_settings['embed_footer'])

    await ctx.send(
        f'{ctx.message.author.mention} добавил(а) `{to_chose[channel_id][num]["title"]} - {to_chose[channel_id][num]["artists"]}` в очередь',
        embed=embed, reference=ctx.message)

    if len(queue[channel_id]) <= 2:
        if not os.path.exists(str(channel_id)):
            os.mkdir(str(channel_id))

        download_track(queue[channel_id][len(queue[channel_id]) - 1]['id'], path=str(channel_id) + '/')

    try:
        await play_queue(ctx)
    except Exception:
        pass


@bot.command()
async def leave(ctx):  # Ливнуть из войса
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send(f'{ctx.message.author.mention} Пока-пока!', reference=ctx.message)
    else:
        await ctx.send('Я не подключен ни к одному из голосовых каналов', reference=ctx.message)


bot.run(discord_settings['token'])
