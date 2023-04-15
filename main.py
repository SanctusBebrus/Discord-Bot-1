import discord
from discord import FFmpegPCMAudio
import requests
import logging
from discord.ext import commands
from settings import discord_settings
from yandex_music_api import get_tracks_info, download_track
import random

logging.basicConfig(
    filename='events.log',
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

bot = commands.Bot(command_prefix=discord_settings['command_prefix'],
                   intents=discord.Intents.all())

queue = list()
to_chose = list()
voice = discord.VoiceClient


def after(error):
    if queue:
        source = FFmpegPCMAudio(f'{queue[0]["id"]}.mp3', executable=discord_settings[
            'ffmpeg_path'])

        voice.play(source, after=after)
        del queue[0]


@bot.command()
async def hello(ctx):  # Поприветствовать пользователя
    author = ctx.message.author
    await ctx.send(f'Привет, {author.mention}!')


@bot.command()
async def randomimage(ctx: discord.ext.commands.context.Context):
    print(type(ctx))
    response = requests.get(f'https://picsum.photos/1024')
    embed = discord.Embed(color=0xff9900, title='Random Image')
    embed.set_footer(text='Yandex Music Bot', icon_url=discord_settings['bot_icon'])
    embed.set_image(url=response.url)
    await ctx.send(ctx.message.author.mention, embed=embed)


@bot.command()
async def play(ctx, *, name_of_song):
    tracks_info = get_tracks_info(name_of_song)
    await ctx.send('***Ищу вашу песенку в Яндекс Музыке...***')

    if not tracks_info:
        await ctx.send(f'{ctx.message.author.mention} К сожалению, я не ничего не нашёл')
        return

    to_say = ''
    embed = discord.Embed(color=0xff9900, title='**Вот что я нашёл!**')
    for i, track in enumerate(tracks_info, 1):
        to_chose.append(track)
        to_say += f'**{i}:** {track["title"]} - {", ".join(track["artists"])}\t`Длительность: {track["duration"]}`\n'
    embed.add_field(name="", value=f"{to_say}", inline=False)
    embed.set_footer(text='Yandex Music Bot', icon_url=discord_settings['bot_icon'])
    await ctx.send(ctx.message.author.mention, embed=embed)


@bot.command()
async def join(ctx):
    global voice
    if ctx.author.voice:
        channel = ctx.message.author.voice.channel
        voice = await channel.connect()
        if not bot.voice_clients:
            await channel.connect()
        elif bot.voice_clients[0].channel == ctx.message.author.voice.channel:
            pass
        else:
            await channel.connect()


@bot.command()
async def c(ctx, num: int):
    global voice
    if num < 1 or num > 10:
        await ctx.send('Можно выбрать только от 1 до 10')
        return

    num = num - 1

    queue.append(to_chose[num])
    download_track(to_chose[num]['id'])

    await ctx.send(
        f'{ctx.message.author.mention} добавил(а) `{to_chose[0]["title"]} - {", ".join(to_chose[0]["artists"])}` в очередь')

    download_track(queue[0]['id'])
    to_chose.clear()

    if len(queue) == 1:
        if not bot.voice_clients:
            await ctx.message.author.voice.channel.connect()

        voice = ctx.message.guild.voice_client
        source = FFmpegPCMAudio(f'{queue[0]["id"]}.mp3', executable=discord_settings[
            'ffmpeg_path'])

        voice.play(source, after=after)
        print(1)
        del queue[0]


@bot.command()
async def leave(ctx):  # Ливнуть из войса
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send(f'{ctx.message.author.mention} Пока-пока!')
    else:
        await ctx.send('Я не подключен ни к одному из голосовых каналов')


bot.run(discord_settings['token'])
