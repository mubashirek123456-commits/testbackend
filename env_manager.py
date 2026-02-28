import os
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("F_HOST")
G_CREDENTIALS = os.getenv("G_API_CRED")
SHEET_ID = os.getenv("G_SHEET_ID")