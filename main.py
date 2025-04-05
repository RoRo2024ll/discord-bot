import discord
import json
import os
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# ────────── 환경변수 로드 ──────────
load_dotenv()
TOKEN = os.getenv("TOKEN")  # 환경 변수 이름 수정

# 디버깅용 출력
if TOKEN is None:
    print("❌ DISCORD TOKEN이 None입니다. 환경변수 설정을 확인하세요.")
else:
    print("✅ DISCORD TOKEN이 정상적으로 불러와졌습니다.")

SAVE_FILE = "settings.json"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

# ────────── Flask 웹서버 설정 (Render용) ──────────
app = Flask('')

@app.route('/')
def home():
    return "봇이 실행 중입니다!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ────────── 디스코드 봇 클래스 ──────────
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.channel_mapping = {}
        self.button_settings = {}
        self.message_ids = {}
        self.load_settings()

    async def on_ready(self):
        print(f"✅ {self.user} 로그인 완료!")
        await self.tree.sync()

    def load_settings(self):
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.channel_mapping = data.get("channel_mapping", {})
                self.button_settings = data.get("button_settings", {})
                self.message_ids = data.get("message_ids", {})

    def save_settings(self):
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "channel_mapping": self.channel_mapping,
                "button_settings": self.button_settings,
                "message_ids": self.message_ids
            }, f, ensure_ascii=False, indent=2)

bot = MyBot()

# ────────── 커맨드 구현 ──────────
@bot.tree.command(name="채널지정", description="메시지를 보낼 채널을 지정합니다.")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    bot.channel_mapping[str(interaction.guild.id)] = channel.id
    bot.save_settings()
    await interaction.response.send_message(f"✅ 메시지 채널이 {channel.mention} 으로 설정되었습니다!", ephemeral=True)

@bot.tree.command(name="메세지보내기", description="지정된 채널에 메시지를 보냅니다.")
async def send_message(interaction: discord.Interaction, message: str):
    guild_id = str(interaction.guild.id)
    if guild_id in bot.channel_mapping:
        channel = bot.get_channel(bot.channel_mapping[guild_id])
        if channel:
            sent = await channel.send(message)
            bot.message_ids[guild_id] = sent.id
            bot.save_settings()
            await interaction.response.send_message("✅ 메시지 전송 완료!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 채널을 찾을 수 없습니다.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 먼저 `/채널지정`을 해주세요.", ephemeral=True)

@bot.tree.command(name="버튼텍스트정하기", description="버튼의 텍스트를 설정합니다.")
async def set_button_text(interaction: discord.Interaction, text: str):
    guild_id = str(interaction.guild.id)
    if guild_id not in bot.button_settings:
        bot.button_settings[guild_id] = {}
    bot.button_settings[guild_id]["text"] = text
    bot.save_settings()
    await interaction.response.send_message(f"✅ 버튼 텍스트가 `{text}` 로 설정되었습니다!", ephemeral=True)

@bot.tree.command(name="버튼색깔지정", description="버튼의 색깔을 지정합니다.")
@discord.app_commands.choices(color=[
    discord.app_commands.Choice(name="빨강", value="red"),
    discord.app_commands.Choice(name="주황", value="blurple"),
    discord.app_commands.Choice(name="노랑", value="gray"),
    discord.app_commands.Choice(name="초록", value="green"),
    discord.app_commands.Choice(name="파랑", value="blurple")
])
async def set_button_color(interaction: discord.Interaction, color: discord.app_commands.Choice[str]):
    guild_id = str(interaction.guild.id)
    if guild_id not in bot.button_settings:
        bot.button_settings[guild_id] = {}
    bot.button_settings[guild_id]["color"] = color.value
    bot.save_settings()
    await interaction.response.send_message(f"✅ 버튼 색깔이 `{color.name}` 로 설정되었습니다!", ephemeral=True)

@bot.tree.command(name="버튼역할", description="버튼을 클릭하면 부여될 역할을 지정합니다.")
async def set_button_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = str(interaction.guild.id)
    if guild_id not in bot.button_settings:
        bot.button_settings[guild_id] = {}
    bot.button_settings[guild_id]["role"] = role.id
    bot.save_settings()
    await interaction.response.send_message(f"✅ 버튼 역할이 `{role.name}` 으로 설정되었습니다!", ephemeral=True)

@bot.tree.command(name="버튼보내기", description="설정한 버튼이 포함된 메시지를 전송합니다.")
async def send_button(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    settings = bot.button_settings.get(guild_id)
    channel_id = bot.channel_mapping.get(guild_id)
    message_id = bot.message_ids.get(guild_id)

    if not settings or not settings.get("text") or not settings.get("color") or not settings.get("role"):
        await interaction.response.send_message("❌ 버튼 설정을 먼저 완료해주세요.", ephemeral=True)
        return

    if not channel_id or not message_id:
        await interaction.response.send_message("❌ 먼저 `/메세지보내기` 명령어로 메시지를 전송해주세요.", ephemeral=True)
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message("❌ 채널을 찾을 수 없습니다.", ephemeral=True)
        return

    try:
        target_message = await channel.fetch_message(message_id)
    except:
        await interaction.response.send_message("❌ 메시지를 찾을 수 없습니다. 다시 `/메세지보내기`를 사용해주세요.", ephemeral=True)
        return

    role_id = settings["role"]
    button_style = discord.ButtonStyle.primary
    if settings["color"] == "red":
        button_style = discord.ButtonStyle.danger
    elif settings["color"] == "green":
        button_style = discord.ButtonStyle.success
    elif settings["color"] == "gray":
        button_style = discord.ButtonStyle.secondary
    else:
        button_style = discord.ButtonStyle.primary

    class RoleButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label=settings["text"], style=button_style)
        async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            role = interaction.guild.get_role(role_id)
            if not role:
                await interaction.response.send_message("❌ 역할을 찾을 수 없습니다.", ephemeral=True)
                return

            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"❌ `{role.name}` 역할이 제거되었습니다!", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ `{role.name}` 역할이 부여되었습니다!", ephemeral=True)

    await target_message.edit(view=RoleButton())
    await interaction.response.send_message("✅ 버튼이 성공적으로 메시지에 추가되었습니다!", ephemeral=True)

# ────────── 실행 ──────────
keep_alive()
bot.run(TOKEN)
