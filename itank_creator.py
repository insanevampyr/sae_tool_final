import streamlit as st
import json
from fpdf import FPDF

st.set_page_config(page_title="ITank Prime Character Creator")

st.title("ITank Prime Character Creator")

# --- Constants ---
races = {
    "Human": {"type": "Both", "modifiers": {}},
    "Elf": {"type": "Both", "modifiers": {"STR": -1, "END": -2, "SPD": 1, "DEX": 1, "WIS": 1, "INT": 2, "APP": 2}},
    "Dwarf": {"type": "Ability", "modifiers": {"STR": 3, "END": 2, "SPD": -1, "DEX": -1, "WIS": -3, "INT": 1, "APP": -2}},
    "Demon": {"type": "Both", "modifiers": {"STR": 3, "END": 3, "SPD": -2, "DEX": -2, "WIS": 2, "INT": 1, "MAN": 2, "APP": -3}},
    "Angel": {"type": "Both", "modifiers": {"STR": 1, "END": -2, "SPD": 1, "DEX": 1, "WIS": 3, "INT": 2, "WIT": -3, "APP": 2}},
    "Fairy": {"type": "Mana", "modifiers": {"STR": -2, "END": -2, "SPD": 2, "DEX": 2, "WIS": 2, "WIT": 2, "LUK": 4, "APP": 1, "SR": 3}},
    "Gargoyle": {"type": "Ability", "modifiers": {"STR": 3, "END": 2, "SPD": 2, "DEX": 3, "WIS": -2, "INT": -2, "WIT": 1, "APP": -2}},
    "Drakkin": {"type": "Mana", "modifiers": {"STR": 4, "END": 3, "SPD": 0, "DEX": -5, "WIS": 4, "INT": 3, "WIT": -2, "MAN": 3}}
}

classes = {
    "Fighter": {"type": "Both", "modifiers": {"STR": 2, "END": 2, "SPD": 1, "DEX": 1, "WIS": -2, "INT": -2, "WIT": 1}, "HSF": "Combat", "EXP": 1},
    "Mage": {"type": "Mana", "modifiers": {"STR": -2, "END": -1, "WIS": 3, "INT": 2, "SR": 1}, "HSF": "Choose from Lava, Fire, Ice, etc.", "EXP": 4},
    "Rogue": {"type": "Both", "modifiers": {"STR": -1, "END": -2, "SPD": 2, "DEX": 2, "WIS": -3, "INT": 3, "WIT": 1, "LUK": 1}, "HSF": "Larceny", "EXP": 2},
    "Cleric": {"type": "Ability", "modifiers": {"STR": 2, "END": 1, "SPD": -1, "DEX": -1, "WIS": 4, "INT": -1, "WIT": -1}, "HSF": "Cleric", "EXP": 2},
    "Sorcerer": {"type": "Mana", "modifiers": {"STR": -2, "END": -2, "SPD": -1, "DEX": -1, "WIS": 3, "INT": 1, "WIT": 3, "LUK": 1, "SR": 1}, "HSF": "Any Elemental Field", "EXP": 3}
}

religions = {
    "None": "",
    "Watera": "Water",
    "Void": "Void",
    "Fire Elemental": "Fire",
    "God": "Light"
}

skills = ["Alertness", "Stealth", "Alchemy", "Persuasion", "Throw", "Leap"]
spells = ["Fireball", "Heal", "Shadow Cloak", "Lightning Bolt"]
drawbacks = ["Greedy", "Coward", "Hot-headed", "Arrogant"]
fears = ["Darkness", "Heights", "Drowning", "Fire"]

base_attrs = ["STR", "END", "SPD", "DEX", "WIS", "INT", "WIT", "MAN", "LUK", "APP", "SR"]

# --- User Selections ---
char_name = st.text_input("Character Name")
sheet_type = st.radio("Select Character Sheet Type", ["Mana", "Ability"])

valid_races = [r for r in races if races[r]['type'] == sheet_type or races[r]['type'] == "Both"]
valid_classes = [c for c in classes if classes[c]['type'] == sheet_type or classes[c]['type'] == "Both"]

selected_race = st.selectbox("Select Race", ["None"] + valid_races)
selected_class1 = st.selectbox("Select Primary Class", ["None"] + valid_classes)
selected_class2 = st.selectbox("Select Secondary Class (Optional)", ["None"] + valid_classes)

selected_religion = st.selectbox("Select Religion (adds a bonus HSF)", list(religions.keys()))
selected_skills = st.multiselect("Choose up to 3 Skills", skills, max_selections=3)
selected_spells = st.multiselect("Choose up to 2 Starting Spells", spells, max_selections=2)
selected_drawbacks = st.multiselect("Select Drawbacks (Max 2)", drawbacks, max_selections=2)
selected_fears = st.multiselect("Select Fears (Max 2)", fears, max_selections=2)

# --- Attribute Calculation ---
attrs = dict.fromkeys(base_attrs, 0)

if selected_race != "None":
    for attr, val in races[selected_race]["modifiers"].items():
        attrs[attr] = attrs.get(attr, 0) + val
if selected_class1 != "None":
    for attr, val in classes[selected_class1]["modifiers"].items():
        attrs[attr] = attrs.get(attr, 0) + val
if selected_class2 != "None":
    for attr, val in classes[selected_class2]["modifiers"].items():
        attrs[attr] = attrs.get(attr, 0) + val

# --- Display Results ---
st.subheader("Final Attributes")
for attr in base_attrs:
    st.write(f"{attr}: {attrs[attr]}")

# --- Derived Info ---
hsf = []
exp_type = []
if selected_class1 != "None":
    hsf.append(classes[selected_class1]["HSF"])
    exp_type.append(classes[selected_class1]["EXP"])
if selected_class2 != "None":
    hsf.append(classes[selected_class2]["HSF"])
    exp_type.append(classes[selected_class2]["EXP"])

hsf.append(religions[selected_religion])
exp_sum = sum(exp_type)
exp_type_str = f"EXP Type: {exp_sum}"

st.write(f"Home Special Fields: {', '.join(hsf)}")
st.write(exp_type_str)

# --- PDF Save ---
def save_character_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Character: {char_name}", ln=1)
    pdf.cell(200, 10, txt=f"Race: {selected_race} | Class: {selected_class1} {selected_class2 if selected_class2 != 'None' else ''}", ln=1)
    pdf.cell(200, 10, txt=f"Character Sheet Type: {sheet_type}", ln=1)
    pdf.cell(200, 10, txt=f"Religion: {selected_religion}", ln=1)
    pdf.cell(200, 10, txt=f"HSF: {', '.join(hsf)}", ln=1)
    pdf.cell(200, 10, txt=exp_type_str, ln=1)
    pdf.cell(200, 10, txt="Attributes:", ln=1)
    for attr in base_attrs:
        pdf.cell(200, 10, txt=f"{attr}: {attrs[attr]}", ln=1)
    pdf.cell(200, 10, txt=f"Skills: {', '.join(selected_skills)}", ln=1)
    pdf.cell(200, 10, txt=f"Spells: {', '.join(selected_spells)}", ln=1)
    pdf.cell(200, 10, txt=f"Drawbacks: {', '.join(selected_drawbacks)}", ln=1)
    pdf.cell(200, 10, txt=f"Fears: {', '.join(selected_fears)}", ln=1)
    pdf.output("itank_character.pdf")
    with open("itank_character.pdf", "rb") as f:
        st.download_button("Download Character PDF", data=f, file_name="itank_character.pdf")

if st.button("Save Character"):
    save_character_pdf()
