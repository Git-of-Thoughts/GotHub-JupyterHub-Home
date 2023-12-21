import os

from dotenv import load_dotenv

if "GOTHUB_API_KEY" not in os.environ:
    load_dotenv()
