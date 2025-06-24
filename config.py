import os
from dotenv import load_dotenv

load_dotenv()

env_vars = {
    "API_ID": os.getenv("API_ID"),
    "API_HASH": os.getenv("API_HASH"),
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "DATABASE_URL_PRIMARY": os.getenv("DATABASE_URL_PRIMARY", ""),
    "CACHE_CHANNEL": os.getenv("CACHE_CHANNEL", ""),
    "CHANNEL": os.getenv("CHANNEL", ""),
    "FNAME": os.getenv("FNAME", ""),
    "THUMB": os.getenv("THUMB", "")
}
dbname = env_vars.get('DATABASE_URL_PRIMARY') or env_vars.get('DATABASE_URL') or 'sqlite:///test.db'
