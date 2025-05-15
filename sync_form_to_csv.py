# file: sync_form_to_csv.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime

# Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Open the sheet by its unique key
sheet = client.open_by_key("1lrgVd6-nq9OkTiDo8v2wLrJYcLGgJwJLIDIKXZ_njc0").sheet1



# Pull data
records = sheet.get_all_records()
df = pd.DataFrame(records)

# Optional: add timestamp column
df['Synced At'] = datetime.datetime.now()

# Group or sort if needed (we’ll adjust based on your form structure)
df.to_csv("clients.csv", index=False)
print("Google Form responses synced to clients.csv")
