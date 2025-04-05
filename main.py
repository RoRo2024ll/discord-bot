import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import os
import json

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

app = Flask(__name__)

DATA_FILE = "data.json"
data = {}

# 데이터 불러오기
def load_data():
    global data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

# 데이터 저장하기
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 웹 서버로 UptimeRobot ping 유지하기
@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

@bot.event
async def on_ready():
    load_data()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await tree.sync()

# 슬래시 명령어: 채널 지정
@tree.command(name="채널지정")
@app_commands.describe(채널="인증 메시지를 보낼 채널")
async def set_channel(interaction: discord.Interaction, 채널: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    data.setdefault(guild_id, {})["channel_id"] = 채널.id
    save_data()
    await interaction.response.send_message(f"채널이 {채널.mention}(으)로 설정되었습니다.", ephemeral=True)

# 메시지 작성
@tree.command(name="메시지작성")
@app_commands.describe(내용="인증 메시지에 들어갈 내용")
async def set_message(interaction: discord.Interaction, 내용: str):
    guild_id = str(interaction.guild.id)
    data.setdefault(guild_id, {})["message"] = 내용
    save_data()
    await interaction.response.send_message("메시지 내용이 설정되었습니다.", ephemeral=True)

# 버튼 텍스트 설정
@tree.command(name="버튼텍스트")
@app_commands.describe(텍스트="버튼에 표시될 텍스트")
async def set_button_text(interaction: discord.Interaction, 텍스트: str):
    guild_id = str(interaction.guild.id)
    data.setdefault(guild_id, {})["button_text"] = 텍스트
    save_data()
    await interaction.response.send_message("버튼 텍스트가 설정되었습니다.", ephemeral=True)

# 버튼 색상 설정
@tree.command(name="버튼색상")
@app_commands.describe(색상="primary / secondary / success / danger")
async def set_button_color(interaction: discord.Interaction, 색상: str):
    if 색상 not in ["primary", "secondary", "success", "danger"]:
        await interaction.response.send_message("잘못된 색상입니다. (primary, secondary, success, danger 중 하나)", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)
    data.setdefault(guild_id, {})["button_color"] = 색상
    save_data()
    await interaction.response.send_message("버튼 색상이 설정되었습니다.", ephemeral=True)

# 역할 지정
@tree.command(name="버튼역할")
@app_commands.describe(역할="버튼 클릭 시 부여할 역할")
async def set_button_role(interaction: discord.Interaction, 역할: discord.Role):
    guild_id = str(interaction.guild.id)
    data.setdefault(guild_id, {})["role_id"] = 역할.id
    save_data()
    await interaction.response.send_message(f"버튼 역할이 {역할.mention}(으)로 설정되었습니다.", ephemeral=True)

# 인증 메시지 전송
@tree.command(name="메시지보내기")
async def send_auth_message(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    guild_data = data.get(guild_id)
    if not guild_data:
        await interaction.response.send_message("먼저 설정을 완료해주세요.", ephemeral=True)
        return

    channel_id = guild_data.get("channel_id")
    message_text = guild_data.get("message")
    button_text = guild_data.get("button_text")
    button_color = guild_data.get("button_color", "primary")

    if not all([channel_id, message_text, button_text]):
        await interaction.response.send_message("설정이 완전히 완료되지 않았습니다.", ephemeral=True)
        return

    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        await interaction.response.send_message("지정한 채널을 찾을 수 없습니다.", ephemeral=True)
        return

    class RoleButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            style = {
                "primary": discord.ButtonStyle.primary,
                "secondary": discord.ButtonStyle.secondary,
                "success": discord.ButtonStyle.success,
                "danger": discord.ButtonStyle.danger
            }.get(button_color, discord.ButtonStyle.primary)

            self.add_item(discord.ui.Button(label=button_text, style=style, custom_id="auth_button"))

    await channel.send(content=message_text, view=RoleButton())
    await interaction.response.send_message("인증 메시지가 전송되었습니다.", ephemeral=True)

# 버튼 클릭 이벤트 처리
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and interaction.data.get("custom_id") == "auth_button":
        guild_id = str(interaction.guild.id)
        role_id = data.get(guild_id, {}).get("role_id")
        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("역할이 부여되었습니다!", ephemeral=True)
                return
        await interaction.response.send_message("설정된 역할이 없습니다.", ephemeral=True)

# Render에서 Flask 실행용 스레드 시작
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(os.environ["DISCORD_TOKEN"])
