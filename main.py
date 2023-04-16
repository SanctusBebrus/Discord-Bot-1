import discord
from discord import FFmpegPCMAudio
from discord.ui import Select, View
import requests
import logging
from discord.ext import commands
from settings import discord_settings
from yandex_music_api import get_tracks_info, download_track

logging.basicConfig(
    filename='events.log',
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

bot = commands.Bot(command_prefix=discord_settings['command_prefix'],
                   intents=discord.Intents.all())

queue = list()
to_chose = list()
voice = discord.VoiceClient
last_song = dict()


def after(error):
    print(error, type(error))
    global last_song
    if queue:
        source = FFmpegPCMAudio(f'{queue[0]["id"]}.mp3', executable=discord_settings[
            'ffmpeg_path'])

        voice.play(source, after=after)
        last_song = queue[0]
        del queue[0]


@bot.command()
async def playlist(ctx):  # Информация об очереди
    embed = discord.Embed(color=0xff9900, title='Очередь из треков')

    if len(queue) > 1:
        to_print = ''
        now_playing = ''
        for n, track in enumerate([last_song] + queue):
            if n == 0:
                now_playing = f"**{queue[0]['title']} - {queue[0]['artists']}** `Длительность: {queue[0]['duration']}`"
            else:
                to_print += f"**{n}**: **{track['title']} - {track['artists']}** `Длительность: {track['duration']}`\n"
        embed.add_field(name='Сейчас играет', value=f"{now_playing}", inline=False)
        embed.add_field(name='В очереди', value=f"{to_print}", inline=False)

    elif len(queue) == 1:
        now_playing = f"**{queue[0]['title']} - {queue[0]['artists']}** `Длительность: {queue[0]['duration']}`"
        embed.add_field(name='Сейчас играет', value=f"{now_playing}", inline=False)
    else:
        embed.add_field(name='Сейчас играет', value="**В данный момент очередь пуста!**", inline=False)
    embed.set_footer(**discord_settings['embed_footer'])
    await ctx.send(ctx.message.author.mention, embed=embed)


@bot.command()
async def hello(ctx):
    print(type(ctx))
    author = ctx.message.author

    await ctx.send(f'Привет, {author.mention}!')


@bot.command()
async def randomimage(ctx: discord.ext.commands.context.Context):
    print(type(ctx))
    response = requests.get(f'https://picsum.photos/1024')
    embed = discord.Embed(color=0xff9900, title='Random Image')
    embed.set_footer(**discord_settings['embed_footer'])
    embed.set_image(url=response.url)
    await ctx.send(ctx.message.author.mention, embed=embed)


@bot.command()
async def pause(ctx):
    if not ctx.voice_client.is_paused():
        ctx.voice_client.pause()
        await ctx.send(ctx.message.author.mention + ' **приостановил воспроизведение музыки.**')


@bot.command()
async def skip(ctx: discord.ext.commands.context.Context):
    if not ctx.voice_client:
        embed = discord.Embed(color=0xff9900, title='**В данный момент очередь пуста!**')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed)
        return

    ctx.voice_client.stop()
    if queue:
        print(queue)

        embed = discord.Embed(color=0xff9900, title='**Вы успешно пропустили трек**')
        embed.add_field(value=f'**{queue[0]["title"]}** - {queue[0]["artists"]}', name=f"**Сейчас играет:**",
                        inline=False)
        embed.set_image(url=queue[0]['image_url'])
        embed.set_footer(**discord_settings['embed_footer'])

        await ctx.send(ctx.author.mention, embed=embed)

        after(None)
        print(123)
    else:
        embed = discord.Embed(color=0xff9900, title='**Вы успешно пропустили трек!**',
                              description='В данный момент очередь пуста')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(ctx.author.mention, embed=embed)


@bot.command()
async def s(ctx):
    await skip(ctx)


@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send(ctx.message.author.mention + ' **продолжил воспроизведение музыки.**')


@bot.command()
async def play(ctx, *, name_of_song):
    if not ctx.message.author.voice:
        await ctx.send(ctx.message.author.mention +
                       '\n**Я не могу включить Вам песенку, Вы же не в чате**')
        return

    tracks_info = get_tracks_info(name_of_song)
    message_1 = await ctx.send('***Ищу вашу песенку в Яндекс Музыке...***')

    if not tracks_info:
        await ctx.send(f'{ctx.message.author.mention} К сожалению, я не ничего не нашёл')
        return

    to_say = ''
    embed = discord.Embed(color=0xff9900, title='**Вот что я нашёл!**')
    for i, track in enumerate(tracks_info, 1):
        to_chose.append(track)
        artists = track['artists'].split(', ')

        to_say += f'**{i}: {track["title"]}** - {artists}  (`Длительность: {track["duration"]}`)\n'

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

    message = await ctx.send(ctx.message.author.mention, embed=embed, view=view)


@bot.command()
async def p(ctx, *, name_of_song):
    await play(ctx, name_of_song=name_of_song)


@bot.command()
async def playbest(ctx, *, name_of_song):
    if not ctx.message.author.voice:
        await ctx.send(ctx.message.author.mention +
                       '\n**Я не могу включить Вам песенку, Вы же не в чате**')
        return

    tracks_info = get_tracks_info(name_of_song, count=1)
    if not tracks_info:
        await ctx.send(f'{ctx.message.author.mention} К сожалению, я не ничего не нашёл')
        return

    to_chose.append(tracks_info[0])
    await c(ctx, 1)


@bot.command()
async def pb(ctx, *, name_of_song):
    await playbest(ctx, name_of_song=name_of_song)


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


async def c(ctx: discord.ext.commands.context.Context, num: int):
    global voice

    num = num - 1

    queue.append(to_chose[num])

    embed = discord.Embed(color=0xff9900, title=f'**{to_chose[num]["title"]}** - {to_chose[num]["artists"]}')
    embed.set_image(url=to_chose[num]['image_url'])
    embed.set_footer(**discord_settings['embed_footer'])

    await ctx.send(
        f'{ctx.message.author.mention} добавил(а) `{to_chose[num]["title"]} - {to_chose[num]["artists"]}` в очередь',
        embed=embed)

    download_track(queue[0]['id'])
    to_chose.clear()

    try:
        await ctx.message.author.voice.channel.connect()
    except Exception:
        pass

    if len(queue) == 1:
        voice = ctx.message.guild.voice_client
        after(None)


@bot.command()
async def leave(ctx):  # Ливнуть из войса
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        await ctx.send(f'{ctx.message.author.mention} Пока-пока!')
    else:
        await ctx.send('Я не подключен ни к одному из голосовых каналов')


bot.run(discord_settings['token'])
