import asyncio
import logging
import io
import os
import textwrap

import discord
import requests

from discord import Message, Intents
from discord.ext import commands
from dotenv import load_dotenv
from imgbb import imgbb
from PIL import Image, ImageFont, ImageDraw

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

load_dotenv()

bot = commands.Bot(intents=Intents.default(), command_prefix=".")

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    print(bot.get_all_channels())
    print(os.getenv("GREET_CHANNEL_ID"))
    channel = bot.get_channel(id=int(os.getenv("GREET_CHANNEL_ID")))
    await channel.send("Hello!")


def meme_creator(im: Image, top, bottom):   
    width, height = im.size
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype("IMPACT.TTF", 20)
    wrap_top = textwrap.wrap(text=top, width=30)
    wrap_top = "\n".join(wrap_top)
    wrap_bottom = textwrap.wrap(text=bottom, width=30)
    wrap_bottom = "\n".join(wrap_bottom)
    stroke_width = 3
    text_tw, _ = draw.textsize(text=wrap_top, font=font, stroke_width=stroke_width)
    text_bw, text_bh = draw.textsize(text=wrap_bottom, font=font, stroke_width=stroke_width)
    draw.multiline_text(((width - text_tw)/2, 10), text=wrap_top, font=font, fill=(255,255,255), align="center", stroke_width=stroke_width, stroke_fill=(0,0,0))
    draw.multiline_text(((width - text_bw)/2, height - text_bh - 10), text=wrap_bottom, font=font, fill=(255,255,255), align="center", stroke_width=stroke_width, stroke_fill=(0,0,0))
    im.save("meme.jpg")


@bot.command()
async def meme(ctx: commands.Context, top: str, bottom: str = ""):
    message: Message = ctx.message

    attachment = message.attachments[0] if len(message.attachments) else None
    
    if not attachment or not attachment.content_type.startswith("image"):
        raise commands.CommandError("Нужно изображение")
    
    image_data = await attachment.read()
    im = Image.open(io.BytesIO(image_data))
    meme_creator(im, top, bottom)
    
    url_viewer = imgbb("meme.jpg")

    file = discord.File(fp="meme.jpg")
    await ctx.send(url_viewer, file=file)

@meme.error
async def meme_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Укажите текст")
    elif isinstance(error, commands.CommandError):
        await ctx.send(error)

@bot.command()
async def products(ctx: commands.Context):
    r = requests.get(os.getenv("REVIEWMANIA_API_URL") + '/products')
    await ctx.reply(r.json())

def categories():
    r = requests.get(os.getenv("REVIEWMANIA_API_URL") + '/categories')
    return r.json()

@bot.command()
async def add_product(ctx:commands.Context):
    embed = discord.Embed(title='Введите номер категории')
    for category in categories():
        embed.add_field(name = category['id'], value= category['name'], inline = True)
    await ctx.send(embed=embed)
    
    def check(m):
        return m.content.isdigit() and m.channel == ctx.channel and m.author == ctx.author
    try:
        message: Message = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        return await ctx.send(embed=discord.Embed(description=f"{ctx.author.mention} Время вышло!"))
    category_id = message.content

    embed = discord.Embed(title='Введите название продукта')
    await ctx.send(embed=embed)

    def check(m):
        return len(m.content) <= 100 and m.channel == ctx.channel and m.author == ctx.author
    try:
        message: Message = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        return await ctx.send(embed=discord.Embed(description=f"{ctx.author.mention} Время вышло!"))
    title = message.content

    embed = discord.Embed(title='Введите описание продукта')
    await ctx.send(embed=embed)

    def check(m):
        return m.channel == ctx.channel and m.author == ctx.author
    try:
        message: Message = await bot.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        return await ctx.send(embed=discord.Embed(description=f"{ctx.author.mention} Время вышло!"))
    description = message.content
    
    await ctx.send(f"{category_id} {title} {description}")
    headers = {'Authorization': f'Token {os.getenv("REVIEWMANIA_TOKEN")}'}
    data = {
        'category': category_id,
        'title': title,
        'description': description,
    }
    r = requests.post(os.getenv("REVIEWMANIA_API_URL") + '/products/', data=data, headers=headers)
    if r.ok:
        product_id = r.json()['id']
        link = os.getenv('REVIEWMANIA_ROOT') + f'/product/{product_id}'
        await ctx.send(f"Продукт успешно добавлен {link}")

@bot.command()
async def show_products(ctx:commands.Context):
    r = requests.get(os.getenv("REVIEWMANIA_API_URL") + '/products')
    collage = Image.new(mode="RGBA", size=(1000,200), color= 123)
    collage.save("test.png")
    
    number = 0

    for product in r.json():
        url = product['main_photo']
        if not url:
            continue
        response = requests.get(url=url)
        photo_bytes = io.BytesIO(response.content)
        photo = Image.open(photo_bytes)
        photo_ratio = photo.size[0] / float(photo.size[1])
        if photo_ratio < 1: #vertical photo
            photo = photo.resize((200, int(200 * photo.size[1] / photo.size[0])), Image.ANTIALIAS)
            box = (0, int((photo.size[1] - 200) / 2), photo.size[0], int((photo.size[1] + 200) / 2))
            photo = photo.crop(box)
        elif photo_ratio > 1: #horizontal photo
            photo = photo.resize((int(200 * photo.size[0] / photo.size[1]), 200), Image.ANTIALIAS)
            box = (int((photo.size[0] - 200) / 2), 0, int((photo.size[0] + 200) / 2), photo.size[1])
            photo = photo.crop(box)
        else:
            photo = photo.resize((200, 200))
        collage.paste(photo, box=(number*200, 0))
        number += 1

    collage.save("test2.png")
    last_image = discord.File(fp='test2.png', filename='products.png')
    await ctx.send(file = last_image)



bot.run(os.getenv("TOKEN"))
