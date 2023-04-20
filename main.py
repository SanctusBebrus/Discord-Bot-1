import asyncio
import logging
import os
import shutil
from collections import defaultdict

import discord
import requests
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.ui import Select, View

from settings import discord_settings
from yandex_music_api import get_tracks_info, get_track_info, get_albums_info, download_track, get_chart_tracks_info, \
    client

logging.basicConfig(
    filename='events.log',
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

bot = commands.Bot(command_prefix=discord_settings['command_prefix'],
                   intents=discord.Intents.all())


class QueueList(list):
    def append(self, __object, ctx) -> None:
        super().append(__object)
        on_queue_append(ctx)


queue = defaultdict(QueueList)
to_chose = defaultdict(list)


@bot.event
async def on_ready():
    print("Бот готов к работе.")
    await bot.change_presence(status=discord.Status.online,
                              activity=discord.Activity(name=f'{discord_settings["command_prefix"]}bhelp',
                                                        type=discord.ActivityType.listening))  # Идёт инфа о команде помощи (префикс изменить)


@bot.command()
async def bhelp(ctx):
    embed = discord.Embed(color=0xff9900, title="Информация о командах")
    embed.add_field(name=f"`{discord_settings['command_prefix']}bhelp` : ", value="**Вызовет это меню**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}play <YourMusic>` : ",
                    value="**Выведет 10 найденных треков на выбор**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}playbest <YourMusic>` : ",
                    value="**Сразу добавит первый найденный трек в очередь**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}playlist` : ",
                    value="**Выведет информацию об очереди**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}pause` : ",
                    value="**Поставит проигрывание музыки на паузу**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}resume` : ", value="**Возобновит проигрывание музыки**",
                    inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}skip` : ", value="**Пропустить текущий трек**",
                    inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}join` : ",
                    value="**Бот подключится к вашему голосовому каналу**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}leave` : ", value="**Бот покинет голосовой канал**",
                    inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}hello` : ", value="**Поприветствовать бота**",
                    inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}randomimage` : ",
                    value="**Покажет случайную картинку**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}playalbum <AlbumName>` : ",
                    value="**Поставит в очередь целый плейлист**", inline=False)
    embed.add_field(name=f"`{discord_settings['command_prefix']}playchart` : ",
                    value="**Бот перейдет в режим чартов и начнет проигрывание самых популярных треков на Яндекс Музыке**",
                    inline=False)
    await ctx.send(ctx.message.author.mention, embed=embed, reference=ctx.message)


def on_queue_append(ctx):
    if len(queue[ctx.channel.id]) <= 2:
        track = queue[ctx.channel.id][-1]
        download_track(track['id'], path=str(ctx.channel.id) + '/')


def mls_to_sm(x):
    return f'{x // 60 // 1000}:{str(x // 1000 - x // 60 // 1000 * 60).rjust(2, "0")}'


async def is_user_in_voicechat(ctx):
    if not ctx.message.author.voice:
        embed = discord.Embed(color=0xff9900, title='**Я не могу включить Вам песенку, Вы же не в чате**')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)
        return

    return True if ctx.message.author.voice else False


async def play_queue(ctx: discord.ext.commands.context.Context):
    print('play_queue func started')
    channel_id = ctx.channel.id
    voice = ctx.voice_client

    while queue[channel_id]:
        source = FFmpegPCMAudio(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3', executable=discord_settings[
            'ffmpeg_path'])

        voice.play(source)
        print('Started playing...')

        if len(queue[channel_id]) >= 3:
            download_track(queue[channel_id][2]['id'], path=str(channel_id) + '/')

        await asyncio.sleep(queue[channel_id][0]["duration"] / 1000 + 1)
        print('Stopped playing...')

        if not queue[channel_id]:
            return

        if len(queue[channel_id]) >= 2:
            if queue[channel_id][0]["id"] != queue[channel_id][1]["id"]:
                os.remove(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3')
                print('File deleted...')
        else:
            os.remove(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3')
            print('File deleted...')

        del queue[channel_id][0]


@bot.command()
async def playlist(ctx):
    channel_id = ctx.channel.id

    embed = discord.Embed(color=0xff9900, title='Ваш плейлист:')

    if len(queue[channel_id]) > 1:
        to_print = ''
        now_playing = ''
        for n, track in enumerate(queue[channel_id][:11]):
            if n == 0:
                now_playing = f"**{track['title']} - {track['artists']}** `Длительность: {mls_to_sm(track['duration'])}`"
            else:
                to_print += f"**{n}**: **{track['title']} - {track['artists']}** (`Длительность: {mls_to_sm(track['duration'])}`)\n"
        embed.add_field(name='Сейчас играет', value=f"{now_playing}", inline=False)
        embed.add_field(name='В очереди', value=f"{to_print}", inline=False)

        if len(queue[channel_id]) > 10:
            embed.add_field(name='\n', value='', inline=False)
            embed.add_field(name='**Всего треков в очереди:**', value=str(len(queue[channel_id])), inline=False)

    elif len(queue[channel_id]) == 1:
        now_playing = f"**{queue[channel_id][0]['title']} - {queue[channel_id][0]['artists']}** (`Длительность: {mls_to_sm(queue[channel_id][0]['duration'])}`)"
        embed.add_field(name='Сейчас играет', value=f"{now_playing}", inline=False)
    else:
        embed = discord.Embed(color=0xff9900, title='Я ничего не играю',
                              description='**В данный момент очередь пуста!**')

    embed.set_footer(**discord_settings['embed_footer'])
    await ctx.send(embed=embed, reference=ctx.message)


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
    await ctx.send(embed=embed, reference=ctx.message)


@bot.command()
async def pause(ctx):
    if not ctx.voice_client.is_paused():
        ctx.voice_client.pause()

        embed = discord.Embed(color=0xff9900, title='**Вы приостановили воспроизведение музыки.**')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)


@bot.command()
async def skip(ctx: discord.ext.commands.context.Context):
    channel_id = ctx.channel.id

    if not ctx.voice_client:
        embed = discord.Embed(color=0xff9900, title='**В данный момент очередь пуста!**')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)
        return

    ctx.voice_client.stop()
    await asyncio.sleep(0.1)
    if queue[channel_id]:
        if len(queue[channel_id]) > 1:

            if len(queue[channel_id]) >= 2:
                if queue[channel_id][0]["id"] != queue[channel_id][1]["id"]:
                    os.remove(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3')
                    print('File deleted...')
            else:
                os.remove(f'{channel_id}/{queue[channel_id][0]["id"]}.mp3')
                print('File deleted...')

            embed = discord.Embed(color=0xff9900, title='**Вы успешно пропустили трек!**')
            embed.add_field(value=f'**{queue[channel_id][1]["title"]}** - {queue[channel_id][1]["artists"]}',
                            name=f"**Сейчас играет:**",
                            inline=False)
            embed.set_image(url=queue[channel_id][1]['image_url'])
            embed.set_footer(**discord_settings['embed_footer'])

            await ctx.send(embed=embed, reference=ctx.message)

        elif len(queue[channel_id]) == 1:
            embed = discord.Embed(color=0xff9900, title='**Вы успешно пропустили трек**')
            embed.add_field(name=f'В данный момент очередь пуста', value='', inline=False)

            await ctx.send(embed=embed, reference=ctx.message)

        del queue[channel_id][0]
        await play_queue(ctx)
    else:
        embed = discord.Embed(color=0xff9900, title='**В данный момент очередь пуста**')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)


@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        embed = discord.Embed(color=0xff9900, title=' **Вы продолжили воспроизведение музыки.** ')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)


@bot.command()
async def play(ctx, *, name_of_song):
    await join(ctx)

    if not await is_user_in_voicechat(ctx):
        return

    channel_id = ctx.channel.id

    tracks_info = get_tracks_info(name_of_song)
    message_1 = await ctx.send(' ***Ищу вашу песенку в Яндекс Музыке... ***')

    if not tracks_info:
        embed = discord.Embed(color=0xff9900, title=' **К сожалению, я не ничего не нашёл** ')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(f'К сожалению, я не ничего не нашёл', reference=ctx.message)

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
        if interaction.user.id != ctx.author.id:
            await ctx.send(f'{interaction.user.mention}, я не тебя спрашивал!')
            return

        await message.delete()
        await message_1.delete()
        await c(ctx, int(selectmenu.values[0][0]))

    selectmenu.callback = my_callback

    message = await ctx.send(embed=embed, view=view, reference=ctx.message)


@bot.command()
async def playalbum(ctx, *, name_of_album):
    await join(ctx)

    if not await is_user_in_voicechat(ctx):
        return

    channel_id = ctx.channel.id

    albums_info = get_albums_info(name_of_album)
    message_1 = await ctx.send('***Ищу ваш альбом в Яндекс Музыке...***')

    if not albums_info:
        await ctx.send(f' **К сожалению, я не ничего не нашёл** ', reference=ctx.message)
        return

    to_say = ''
    embed = discord.Embed(color=0xff9900, title='**Я нашел немного альбомов!**')
    for i, album in enumerate(albums_info, 1):
        artists = album['artists']
        to_say += f'**{i}: {album["title"]}** - {artists}  (Треков: {album["track_count"]})\n'

    embed.add_field(name="", value=f"{to_say}", inline=False)
    embed.set_footer(**discord_settings['embed_footer'])

    selectmenu = Select(options=[
        discord.SelectOption(label=f'{i}: {album["title"][:50]} - {album["artists"][:40]}') for i, album in
        enumerate(albums_info, 1)
    ])

    view = View()
    view.add_item(selectmenu)

    async def my_callback(interaction: discord.Interaction):
        if interaction.user.id != ctx.author.id:
            await ctx.send(f'{interaction.user.mention}, я не тебя спрашивал!')
            return

        must_load = False
        if len(queue[channel_id]) <= 1:
            must_load = True

        await message.delete()
        await message_1.delete()

        if must_load:
            embed = discord.Embed(color=0xff9900)
            embed.set_image(url=discord_settings['loading_gif_url'])
            loading_message = await ctx.send('**Ищем чарты в Яндекс Музыке для вас...**', embed=embed)

        chosed_album = albums_info[int(selectmenu.values[0][0]) - 1]

        tracks = client.albums_with_tracks(chosed_album['id']).volumes[0]
        for track in tracks:
            queue[channel_id].append(get_track_info(track), ctx=ctx)

        if must_load:
            await loading_message.delete()

        embed = discord.Embed(color=0xff9900,
                              title=f'**Вы успешно добавили альбом "{chosed_album["title"]}" в очередь!**',
                              description=f'**{len(tracks)} треков уже ждут вас**')
        embed.set_image(url=chosed_album['image_url'])
        embed.set_footer(**discord_settings['embed_footer'])

        await ctx.send(embed=embed, reference=ctx.message)
        try:
            await play_queue(ctx)
        except Exception:
            pass

    selectmenu.callback = my_callback

    message = await ctx.send(embed=embed, view=view, reference=ctx.message)


@bot.command()
async def playchart(ctx):
    await join(ctx)

    if not await is_user_in_voicechat(ctx):
        return

    embed = discord.Embed(color=0xff9900)
    embed.set_image(url=discord_settings['loading_gif_url'])
    message = await ctx.send(' **Ищем чарты в Яндекс Музыке для вас...** ', embed=embed, reference=ctx.message)

    await clear(ctx)

    for track in get_chart_tracks_info():
        queue[ctx.channel.id].append(track, ctx=ctx)

    embed = discord.Embed(color=0xff9900, title='**Теперь я в режиме чартов!**',
                          description=f'**Кстати, сейчас в очереди {len(queue[ctx.channel.id])} треков.**')

    track = queue[ctx.channel.id][0]
    now_playing = f"**{track['title']} - {track['artists']}** (`Длительность: {mls_to_sm(track['duration'])}`)"
    embed.add_field(name='Первый из них', value=now_playing, inline=False)
    embed.set_image(url=track['image_url'])
    embed.set_footer(**discord_settings['embed_footer'])
    await message.delete()
    await ctx.send(embed=embed, reference=ctx.message)

    await play_queue(ctx)


@bot.command()
async def playbest(ctx, *, name_of_song):
    await join(ctx)
    if not await is_user_in_voicechat(ctx):
        return

    channel_id = ctx.channel.id

    tracks_info = get_tracks_info(name_of_song, count=1)

    embed = discord.Embed(color=0xff9900, title=' **К сожалению, я не ничего не нашёл** ')
    embed.set_footer(**discord_settings['embed_footer'])
    if not tracks_info:
        await ctx.send(embed=embed, reference=ctx.message)
        return

    to_chose[channel_id] = [tracks_info[0]]
    await c(ctx, 1)


@bot.command()
async def join(ctx):
    if not await is_user_in_voicechat(ctx):
        return

    if not ctx.voice_client:
        await ctx.message.author.voice.channel.connect()


async def c(ctx: discord.ext.commands.context.Context, num: int):
    channel_id = ctx.channel.id

    num = num - 1

    queue[channel_id].append(to_chose[channel_id][num], ctx=ctx)

    embed = discord.Embed(color=0xff9900,
                          title=f'**{to_chose[channel_id][num]["title"]}** - {to_chose[channel_id][num]["artists"]}')
    embed.set_image(url=to_chose[channel_id][num]['image_url'])
    embed.set_footer(**discord_settings['embed_footer'])

    await ctx.send(
        f'{ctx.message.author.mention} добавил(а) `{to_chose[channel_id][num]["title"]} - {to_chose[channel_id][num]["artists"]}` в очередь',
        embed=embed, reference=ctx.message)

    try:
        await play_queue(ctx)
    except Exception:
        pass


@bot.command()
async def clear(ctx):
    ctx.voice_client.stop()
    await asyncio.sleep(0.1)
    shutil.rmtree(str(ctx.channel.id), ignore_errors=True)
    queue[ctx.channel.id].clear()


@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await clear(ctx)
        await ctx.send(f'{ctx.message.author.mention}, пока-пока!', reference=ctx.message)
        await ctx.guild.voice_client.disconnect()

    else:
        embed = discord.Embed(color=0xff9900, title=' **Я не подключен ни к одному из голосовых каналов** ')
        embed.set_footer(**discord_settings['embed_footer'])
        await ctx.send(embed=embed, reference=ctx.message)


bot.run(discord_settings['token'])
