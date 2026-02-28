import gspread
import json
from google.oauth2.service_account import Credentials
from env_manager import SHEET_ID, G_CREDENTIALS

scope = ["https://www.googleapis.com/auth/spreadsheets"]

creds_dict = json.loads(G_CREDENTIALS)

# Fix private_key newline issue (important)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=scope
)

client = gspread.authorize(creds)

spreadsheet = client.open_by_key(SHEET_ID)