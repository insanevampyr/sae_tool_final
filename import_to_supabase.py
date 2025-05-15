import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# Supabase credentials
url = "https://xxyfipfbnusrowhbtwkb.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4eWZpcGZibnVzcm93aGJ0d2tiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcyNjI4MTMsImV4cCI6MjA2MjgzODgxM30.7a1UswYWolt82zAiRNzp3RAJ3OqW0GHYgWXvjoCES5I"  # Keep using your actual anon key

supabase: Client = create_client(url, key)

# Load and clean the CSV
df = pd.read_csv("clients.csv")

# Rename columns from form to match Supabase schema
df = df.rename(columns={
    "Name": "name",
    "Legal Name as it appears on ID": "legal_name",
    "Badge Name Preference": "badge_name",
    "Bio": "bio",
    "Date of Birth": "dob",
    "Gender": "gender",
    "Contact Phone": "phone",
    "Email": "email",
    "Company": "company",
    "Company Logo Upload": "logo_url",
    "Address": "address",
    "City": "city",
    "State": "state",
    "Zip": "zip",
    "Emergency Contact": "emergency_contact",
    "Emergency Contact Phone": "emergency_contact_phone",
    "Airport Code": "airport_code",
    "Arrival Date": "arrival_date",
    "Arrival Time": "arrival_time",
    "Upload 1 supported file. Max 10 MB.": "photo_url"
})

# Add last_update
df["last_update"] = datetime.utcnow().isoformat()

# Filter valid columns
columns = [
    "name", "legal_name", "badge_name", "bio", "dob", "gender",
    "phone", "email", "company", "logo_url",
    "address", "city", "state", "zip",
    "emergency_contact", "emergency_contact_phone",
    "airport_code", "arrival_date", "arrival_time",
    "photo_url", "last_update"
]
df = df[[col for col in columns if col in df.columns]]

# Upsert into Supabase using "name" as conflict key
for _, row in df.iterrows():
    data = row.dropna().to_dict()
    try:
        supabase.table("clients").upsert(data, on_conflict="name").execute()
        print(f"✅ Synced: {data.get('name', '[No Name]')}")
    except Exception as e:
        print(f"⚠️ Error syncing {data.get('name', '[No Name]')}: {e}")

print("✅ All clients processed with upsert protection.")
