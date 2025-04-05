import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

print("TOKEN:", TOKEN)  # 배포 전에 꼭 지우기!!!
