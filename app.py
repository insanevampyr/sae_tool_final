import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# Supabase credentials
url = "https://xxyfipfbnusrowhbtwkb.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4eWZpcGZibnVzcm93aGJ0d2tiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcyNjI4MTMsImV4cCI6MjA2MjgzODgxM30.7a1UswYWolt82zAiRNzp3RAJ3OqW0GHYgWXvjoCES5I"
supabase: Client = create_client(url, key)

st.set_page_config(page_title="MEGA Client Manager", layout="centered")

st.markdown(
    """
    <style>
    .stButton > button {
        background-color: #444; color: white; border-radius: 6px; padding: 0.4em 1em;
    }
    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #2b2b2b; color: #f0f0f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌟 MEGA Client Manager")

@st.cache_data(ttl=60)
def fetch_clients():
    res = supabase.table("clients").select("*").execute()
    return pd.DataFrame(res.data or [])

df = fetch_clients()

# Hide ID column
if "id" in df.columns:
    df = df.drop(columns=["id"])

# Search or select
selected_row = {}
with st.expander("🔍 Find Client"):
    col1, col2 = st.columns(2)
    search_name = col1.text_input("Search by Name").strip().lower()
    search_legal = col2.text_input("Search by Legal Name").strip().lower()

    combined_options = df.copy()
    combined_options["display"] = combined_options.apply(
        lambda x: f'{x["name"]} — {x["legal_name"]}' if pd.notna(x["legal_name"]) else x["name"], axis=1
    )
    selected_combo = st.selectbox("🔽 Or Select from Full List", combined_options["display"].sort_values())

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

# Add/Edit form
with st.expander("➕ Add or Edit Client"):
    mode = st.radio("Mode", ["Add New", "Edit Selected"], horizontal=True)

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
            logo_url = st.text_input("Company Logo URL", selected_row.get("logo_url", ""))
            photo_url = st.text_input("Headshot Photo URL", selected_row.get("photo_url", ""))

            if logo_url:
                st.image(logo_url, caption="Company Logo", width=150)
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
                    "photo_url": photo_url, "last_update": datetime.utcnow().isoformat()
                }

                if mode == "Add New":
                    supabase.table("clients").insert(data).execute()
                    st.success("✅ New client added.")
                elif mode == "Edit Selected":
                    supabase.table("clients").update(data).eq("name", selected_row["name"]).execute()
                    st.success("✅ Client updated.")

                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("⚠️ To edit, first select a client using the dropdown or search above.")

# Delete
with st.expander("🗑 Delete Client"):
    delete_name = st.selectbox("Choose Client to Delete", df["name"].dropna().unique())
    if st.button("❌ Confirm Delete"):
        supabase.table("clients").delete().eq("name", delete_name).execute()
        st.success(f"✅ Deleted {delete_name}")
        st.cache_data.clear()
        st.rerun()

# Export
st.subheader("⬇️ Export Clients")
if not df.empty:
    export_df = df.drop(columns=["id"], errors="ignore")
    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="clients.csv", mime="text/csv")
else:
    st.warning("Nothing to export.")
