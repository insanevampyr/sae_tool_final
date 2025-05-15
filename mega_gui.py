import tkinter as tk
from tkinter import messagebox, ttk, Toplevel, filedialog
import pandas as pd
import os
import subprocess
import sys
from datetime import datetime

CSV_FILE = "clients.csv"
REQUIRED_FIELDS = ["Name", "Legal Name", "Email"]  # Add more if needed

class MegaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MEGA Client Manager")
        self.root.configure(bg="#1e1e1e")
        self.root.resizable(False, False)

        self.font_style = ("Helvetica", 10)
        self.bg_color = "#1e1e1e"
        self.fg_color = "#f0f0f0"
        self.entry_bg = "#2b2b2b"

        self.status_var = tk.StringVar(value="")
        self.run_sync_and_set_status()

        self.fields = {
            "Name": tk.StringVar(),
            "Legal Name": tk.StringVar(),
            "Badge Name": tk.StringVar(),
            "Bio": tk.StringVar(),
            "Date of Birth": tk.StringVar(),
            "Gender": tk.StringVar(),
            "Contact Phone": tk.StringVar(),
            "Email": tk.StringVar(),
            "Company": tk.StringVar(),
            "Address": tk.StringVar(),
            "City": tk.StringVar(),
            "State": tk.StringVar(),
            "Zip": tk.StringVar(),
            "Emergency Contact": tk.StringVar(),
            "Emergency Contact Phone": tk.StringVar(),
            "Airport Code": tk.StringVar(),
            "Arrival Date": tk.StringVar(),
            "Arrival Time": tk.StringVar()
        }

        self.entry_widgets = {}

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("TButton", background=self.entry_bg, foreground=self.fg_color)
        style.map("TButton", background=[("active", "#444")])

        # Dropdown
        self.client_names = self.get_client_names()
        self.selected_name = tk.StringVar()

        tk.Label(root, text="Select Client:", font=self.font_style,
                 bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, pady=4, sticky="e")
        self.name_dropdown = ttk.Combobox(root, textvariable=self.selected_name,
                                          values=self.client_names, width=45)
        self.name_dropdown.grid(row=0, column=1, pady=4)
        self.name_dropdown.bind("<<ComboboxSelected>>", self.fill_from_dropdown)

        tk.Button(root, text="Add New", command=self.clear_fields).grid(row=0, column=2, padx=5)
        tk.Button(root, text="Save Client", command=self.save_client).grid(row=0, column=3, padx=5)
        tk.Button(root, text="Delete Client", command=self.delete_client).grid(row=1, column=3, padx=5)

        # Entry fields
        row = 1
        for label, var in self.fields.items():
            tk.Label(root, text=label + ":", font=self.font_style,
                     bg=self.bg_color, fg=self.fg_color).grid(row=row + 1, column=0, sticky="e", pady=2)
            entry = tk.Entry(root, textvariable=var, width=50,
                             font=self.font_style, bg=self.entry_bg, fg=self.fg_color,
                             insertbackground=self.fg_color)
            entry.grid(row=row + 1, column=1, columnspan=3, pady=2, sticky="w")
            self.entry_widgets[label] = entry
            row += 1

        # Bottom buttons
        tk.Button(root, text="View All Clients", command=self.show_all_clients).grid(row=row + 1, column=0, pady=10)
        tk.Button(root, text="Export Clients", command=self.export_clients).grid(row=row + 1, column=1, pady=10)

        self.status_label = tk.Label(root, textvariable=self.status_var, fg="lightgreen",
                                     bg=self.bg_color, font=self.font_style)
        self.status_label.grid(row=row + 2, column=0, columnspan=4, pady=(5, 10))

        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        self.root.geometry(f"{width}x{height}")

    def run_sync_and_set_status(self):
        try:
            subprocess.run([sys.executable, "sync_form_to_csv.py"], check=True, capture_output=True, text=True)
            self.status_var.set("✅ Sync successful.")
        except subprocess.CalledProcessError as e:
            self.status_var.set(f"❌ Sync failed: {e.stderr.strip() or str(e)}")
        except Exception as e:
            self.status_var.set(f"❌ Sync error: {str(e)}")

        self.root.after(10000, lambda: self.status_var.set(""))

    def get_client_names(self):
        if not os.path.exists(CSV_FILE):
            return []
        df = pd.read_csv(CSV_FILE)
        return sorted(df["Name"].dropna().unique().tolist())

    def fill_from_dropdown(self, event):
        self.fields["Name"].set(self.selected_name.get())
        self.load_client()

    def load_client(self):
        if not os.path.exists(CSV_FILE):
            return
        df = pd.read_csv(CSV_FILE)
        name = self.fields["Name"].get()
        match = df[df["Name"].str.lower() == name.lower()]
        if not match.empty:
            row = match.iloc[0]
            for key in self.fields:
                self.fields[key].set(row.get(key, ""))

    def clear_fields(self):
        for var in self.fields.values():
            var.set("")
        self.selected_name.set("")
        self.reset_entry_colors()

    def reset_entry_colors(self):
        for entry in self.entry_widgets.values():
            entry.config(bg=self.entry_bg)

    def validate_required_fields(self):
        self.reset_entry_colors()
        missing = []
        for field in REQUIRED_FIELDS:
            value = self.fields[field].get().strip()
            if not value:
                self.entry_widgets[field].config(bg="#8B0000")  # red background
                missing.append(field)
        return missing

    def save_client(self):
        missing = self.validate_required_fields()
        if missing:
            messagebox.showerror("Missing Info", f"Required fields missing: {', '.join(missing)}")
            return

        confirm = messagebox.askyesno("Confirm Save", "Are you sure you want to save this client?")
        if not confirm:
            return

        new_data = {k: v.get() for k, v in self.fields.items()}
        new_data["LastUpdate"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            if "Timestamp" in df.columns:
                df = df.rename(columns={"Timestamp": "LastUpdate"})
            df = df[df["Name"].str.lower() != new_data["Name"].lower()]
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])

        df.to_csv(CSV_FILE, index=False)
        messagebox.showinfo("Saved", "Client data saved!")

        self.client_names = self.get_client_names()
        self.name_dropdown["values"] = self.client_names
        self.clear_fields()

    def delete_client(self):
        name = self.fields["Name"].get()
        if not name:
            messagebox.showwarning("No Client Selected", "Please select a client to delete.")
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete {name}?")
        if not confirm:
            return

        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            df = df[df["Name"].str.lower() != name.lower()]
            df.to_csv(CSV_FILE, index=False)
            messagebox.showinfo("Deleted", f"{name} has been deleted.")

        self.client_names = self.get_client_names()
        self.name_dropdown["values"] = self.client_names
        self.clear_fields()

    def show_all_clients(self):
        if not os.path.exists(CSV_FILE):
            messagebox.showerror("Error", "clients.csv not found.")
            return

        df = pd.read_csv(CSV_FILE)
        win = Toplevel(self.root)
        win.title("All Clients — MEGA")
        win.configure(bg=self.bg_color)

        frame = tk.Frame(win, bg=self.bg_color)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame)
        tree["columns"] = list(df.columns)
        tree["show"] = "headings"
        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=150)

        for _, row in df.iterrows():
            tree.insert("", "end", values=list(row))

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

    def export_clients(self):
        if not os.path.exists(CSV_FILE):
            messagebox.showerror("Error", "clients.csv not found.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
        if not file_path:
            return

        df = pd.read_csv(CSV_FILE)
        try:
            if file_path.endswith(".xlsx"):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            messagebox.showinfo("Exported", f"Client list saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

# Launch app
if __name__ == "__main__":
    root = tk.Tk()
    app = MegaApp(root)
    root.mainloop()
