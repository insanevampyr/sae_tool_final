import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
from PIL import Image
from io import BytesIO
from supabase import create_client, Client
import os

# --- CONFIG ---
url = "https://xxyfipfbnusrowhbtwkb.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4eWZpcGZibnVzcm93aGJ0d2tiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcyNjI4MTMsImV4cCI6MjA2MjgzODgxM30.7a1UswYWolt82zAiRNzp3RAJ3OqW0GHYgWXvjoCES5I"
supabase: Client = create_client(url, key)
st.set_page_config(page_title="MEGA Client Manager", layout="centered")
MAX_MB = 5
MAX_BYTES = MAX_MB * 1024 * 1024

def crop_center_square(image_file):
    img = Image.open(image_file)
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) / 2
    top = (height - min_dim) / 2
    right = (width + min_dim) / 2
    bottom = (height + min_dim) / 2
    return img.crop((left, top, right, bottom))

def upload_image(bucket, file_obj, content_type):
    path = f"{bucket}/{uuid.uuid4().hex}.jpg"
    supabase.storage.from_(bucket).upload(path, file_obj, {"content-type": content_type})
    return f"https://xxyfipfbnusrowhbtwkb.supabase.co/storage/v1/object/public/{path}", path

# --- HEADER ---
logo_path = "MEGA_logo.jpg"  # Ensure this is in your working directory!
# Centering logo + headers using columns for best Streamlit appearance
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(logo_path, use_container_width=True)
    st.markdown(
        "<div style='text-align: center; font-size:2.2em; font-weight: bold; margin-bottom:0;'>MEGA Client Manager</div>",
        unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align: center; color: #888; font-size:1.2em; margin-top:0;'>Showcase June 2025</div>",
        unsafe_allow_html=True)
st.markdown("---")

# --- DATA ---
@st.cache_data(ttl=60)
def fetch_clients():
    res = supabase.table("clients").select("*").execute()
    return pd.DataFrame(res.data or [])

df = fetch_clients()
if "id" in df.columns:
    df = df.drop(columns=["id"])

selected_row = {}
with st.expander("🔍 Find Client"):
    col1, col2 = st.columns(2)
    search_name = col1.text_input("Search by Name").strip().lower()
    search_legal = col2.text_input("Search by Legal Name").strip().lower()

    df["display"] = df.apply(
        lambda x: f'{x["name"]} — {x["legal_name"]}' if pd.notna(x["legal_name"]) else x["name"], axis=1
    )
    selected_combo = st.selectbox("🔽 Or Select from Full List", df["display"].sort_values())

    if selected_combo:
        base_name = selected_combo.split(" — ")[0]
        selected_df = df[df["name"] == base_name]
    elif search_name:
        selected_df = df[df["name"].str.lower().str.contains(search_name)]
    elif search_legal:
        selected_df = df[df["legal_name"].str.lower().str.contains(search_legal)]
    else:
        selected_df = pd.DataFrame()

    if not selected_df.empty:
        selected_row = selected_df.iloc[0].to_dict()

with st.expander("➕ Add or Edit Client"):
    mode = st.radio("Mode", ["Add New", "Edit Selected"], horizontal=True)

    if mode == "Add New":
        selected_row = {}

    if mode == "Add New" or (mode == "Edit Selected" and selected_row):
        with st.form("client_form", clear_on_submit=(mode == "Add New")):
            cols1, cols2 = st.columns(2)

            name = cols1.text_input("Name", selected_row.get("name", ""))
            legal_name = cols2.text_input("Legal Name", selected_row.get("legal_name", ""))
            badge_name = cols1.text_input("Badge Name", selected_row.get("badge_name", ""))
            bio = cols2.text_input("Bio", selected_row.get("bio", ""))
            dob = cols1.text_input("Date of Birth", selected_row.get("dob", ""))
            gender = cols2.text_input("Gender", selected_row.get("gender", ""))
            phone = cols1.text_input("Phone", selected_row.get("phone", ""))
            email = cols2.text_input("Email", selected_row.get("email", ""))
            company = cols1.text_input("Company", selected_row.get("company", ""))
            address = cols2.text_input("Address", selected_row.get("address", ""))
            city = cols1.text_input("City", selected_row.get("city", ""))
            state = cols2.text_input("State", selected_row.get("state", ""))
            zip_code = cols1.text_input("Zip", selected_row.get("zip", ""))
            emergency = cols2.text_input("Emergency Contact", selected_row.get("emergency_contact", ""))
            emergency_phone = cols1.text_input("Emergency Phone", selected_row.get("emergency_contact_phone", ""))
            airport = cols2.text_input("Airport Code", selected_row.get("airport_code", ""))
            arrival_date = cols1.text_input("Arrival Date", selected_row.get("arrival_date", ""))
            arrival_time = cols2.text_input("Arrival Time", selected_row.get("arrival_time", ""))
            # ---- NEW DEPARTURE FIELDS ----
            departure_date = cols1.text_input("Departure Date", selected_row.get("departure_date", ""))
            departure_time = cols2.text_input("Departure Time", selected_row.get("departure_time", ""))

            old_logo_url = selected_row.get("logo_url", "")
            old_photo_url = selected_row.get("photo_url", "")

            logo_file = st.file_uploader("📎 Upload Company Logo (Max 5MB, JPG/PNG)", type=["jpg", "jpeg", "png"])
            logo_url = old_logo_url
            if logo_file:
                if logo_file.size > MAX_BYTES:
                    st.error("Logo file too large (5MB max)")
                else:
                    cropped = crop_center_square(logo_file)
                    buffer = BytesIO()
                    cropped.save(buffer, format="JPEG")
                    buffer.seek(0)
                    logo_url, _ = upload_image("logos", buffer, "image/jpeg")
                    st.success("✅ Logo uploaded!")
            if logo_url:
                st.image(logo_url, caption="Logo", width=150)

            photo_file = st.file_uploader("📷 Upload Headshot (Max 5MB, JPG/PNG)", type=["jpg", "jpeg", "png"])
            photo_url = old_photo_url
            if photo_file:
                if photo_file.size > MAX_BYTES:
                    st.error("Photo file too large (5MB max)")
                else:
                    cropped = crop_center_square(photo_file)
                    buffer = BytesIO()
                    cropped.save(buffer, format="JPEG")
                    buffer.seek(0)
                    photo_url, _ = upload_image("headshots", buffer, "image/jpeg")
                    st.success("✅ Headshot uploaded!")
            if photo_url:
                st.image(photo_url, caption="Headshot", width=150)

            submitted = st.form_submit_button("💾 Save Client")
            if submitted:
                data = {
                    "name": name, "legal_name": legal_name, "badge_name": badge_name, "bio": bio, "dob": dob,
                    "gender": gender, "phone": phone, "email": email, "company": company, "logo_url": logo_url,
                    "address": address, "city": city, "state": state, "zip": zip_code,
                    "emergency_contact": emergency, "emergency_contact_phone": emergency_phone,
                    "airport_code": airport, "arrival_date": arrival_date, "arrival_time": arrival_time,
                    "departure_date": departure_date, "departure_time": departure_time,
                    "photo_url": photo_url, "last_update": datetime.utcnow().isoformat()
                }
                if mode == "Add New":
                    supabase.table("clients").insert(data).execute()
                    st.success("✅ New client added.")
                else:
                    supabase.table("clients").update(data).eq("name", selected_row["name"]).execute()
                    if logo_file and old_logo_url:
                        supabase.storage.from_("logos").remove(old_logo_url.split("/")[-1])
                    if photo_file and old_photo_url:
                        supabase.storage.from_("headshots").remove(old_photo_url.split("/")[-1])
                    st.success("✅ Client updated.")

                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("⚠️ Select a client before editing.")

# --- DELETE CLIENT ---
with st.expander("🗑 Delete Client"):
    delete_name = st.selectbox("Choose Client to Delete", df["name"].dropna().unique())
    if st.button("❌ Confirm Delete"):
        row = df[df["name"] == delete_name].iloc[0]
        if row.get("photo_url"):
            supabase.storage.from_("headshots").remove(row["photo_url"].split("/")[-1])
        if row.get("logo_url"):
            supabase.storage.from_("logos").remove(row["logo_url"].split("/")[-1])
        supabase.table("clients").delete().eq("name", delete_name).execute()
        st.success(f"✅ Deleted {delete_name}")
        st.cache_data.clear()
        st.rerun()

# --- EXPORT CLIENTS ---
st.subheader("⬇️ Export Clients")
if not df.empty:
    csv = df.drop(columns=["id"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="clients.csv", mime="text/csv")
else:
    st.warning("Nothing to export.")
