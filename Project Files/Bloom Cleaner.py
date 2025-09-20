import os
import datetime
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog

class DataCleaner:
    def __init__(self, root):
        self.root = root
        self.lang = "fa"
        self.root.title("بلوم کلینر" if self.lang=="fa" else "Bloom Cleaner")
        self.root.geometry("800x500")
        self.root.resizable(False, False)
        self.root.configure(bg="#ffffff")

        self.df = None
        self.filename = None
        self.history = []
        self.redo_stack = []

        self.logs = []

        self.base_font = self._select_font()
        self._setup_style()
        self._build_ui()
        self._build_menus()
        self._bind_shortcuts()
        self._update_status()

    def _select_font(self):
        import tkinter.font as tkfont
        fams = set(tkfont.families())
        for pref in ("Vazirmatn","Vazir","Tahoma","DejaVu Sans"):
            if pref in fams: return (pref,10)
        return ("TkDefaultFont",10)

    def _setup_style(self):
        style = ttk.Style()
        try: style.theme_use("clam")
        except: pass
        style.configure("TFrame", background="#ffffff")
        style.configure("TLabel", background="#ffffff", font=self.base_font)
        style.configure("TButton", padding=4, font=self.base_font)
        style.configure("Treeview", font=self.base_font)

    def _build_menus(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="باز کردن" if self.lang=="fa" else "Open", command=self.open_file)
        file_menu.add_command(label="ذخیره" if self.lang=="fa" else "Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="خروج" if self.lang=="fa" else "Exit", command=self.root.quit)
        menubar.add_cascade(label="فایل" if self.lang=="fa" else "File", menu=file_menu)

        hist_menu = tk.Menu(menubar, tearoff=0)
        hist_menu.add_command(label="↶ بازگشت" if self.lang=="fa" else "↶ Undo", command=self.undo_action)
        hist_menu.add_command(label="↷ جلو" if self.lang=="fa" else "↷ Redo", command=self.redo_action)
        hist_menu.add_command(label="ذخیره لاگ" if self.lang=="fa" else "Save Logs", command=self.save_logs)
        hist_menu.add_command(label="پاکسازی لاگ" if self.lang=="fa" else "Clear Logs", command=self.clear_logs)
        menubar.add_cascade(label="تاریخچه" if self.lang=="fa" else "History", menu=hist_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="English" if self.lang=="fa" else "فارسی", command=self.toggle_language)
        menubar.add_cascade(label="نمایش" if self.lang=="fa" else "View", menu=view_menu)
        self.root.config(menu=menubar)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label="درباره ما" if self.lang=="fa" else "About Us", command=self.show_about)
        menubar.add_cascade(label="درباره" if self.lang=="fa" else "About", menu=about_menu)

    def _build_ui(self):
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True, padx=6, pady=6)

        self.toolbar = ttk.Frame(self.frame)
        self.toolbar.pack(fill="x", pady=6)
        
        self._update_toolbar_texts()

        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill="both", expand=True, pady=4)
        
        self.tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        self.tree_scroll_y.pack(side="right", fill="y")
        
        self.tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")
        self.tree_scroll_x.pack(side="bottom", fill="x")
        
        self.tree = ttk.Treeview(
            table_frame, 
            yscrollcommand=self.tree_scroll_y.set, 
            xscrollcommand=self.tree_scroll_x.set, 
            show="headings"
        )
        self.tree.pack(fill="both", expand=True)
        
        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree_scroll_x.config(command=self.tree.xview)

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", padx=6, pady=(0,4))

        self.log_frame = ttk.LabelFrame(self.frame, text="لاگ‌ها" if self.lang=="fa" else "Logs")
        self.log_frame.pack(fill="both", expand=True, pady=4)
        self.log_text = tk.Text(self.log_frame, wrap="word", font=self.base_font, state="disabled", height=8)
        self.log_text.pack(fill="both", expand=True)

    def _update_toolbar_texts(self):
        for widget in self.toolbar.winfo_children():
            widget.destroy()
        
        self.btn_dropna = ttk.Button(self.toolbar, text="حذف سطرهای خالی" if self.lang=="fa" else "Drop empty rows", command=self.remove_empty_rows)
        self.btn_dropna.pack(side="left", padx=4)
        self.btn_dups = ttk.Button(self.toolbar, text="حذف سطرهای تکراری" if self.lang=="fa" else "Drop duplicate rows", command=self.remove_duplicate_rows)
        self.btn_dups.pack(side="left", padx=4)
        
        ttk.Label(self.toolbar, text="ستون:" if self.lang=="fa" else "Column:").pack(side="left", padx=(8,0))
        self.column_var = tk.StringVar()
        self.col_combo = ttk.Combobox(self.toolbar, textvariable=self.column_var, state="readonly", width=15)
        self.col_combo.pack(side="left", padx=4)
        
        ttk.Label(self.toolbar, text="نام جدید:" if self.lang=="fa" else "New name:").pack(side="left", padx=(8,0))
        self.new_name_var = tk.StringVar()
        self.new_name_entry = ttk.Entry(self.toolbar, textvariable=self.new_name_var, width=12)
        self.new_name_entry.pack(side="left", padx=4)
        placeholder = "نام جدید را وارد کنید" if self.lang=="fa" else "Enter new name"
        self.new_name_entry.delete(0, "end")
        self.new_name_entry.insert(0, placeholder)
        self.new_name_entry.bind("<FocusIn>", self._clear_placeholder)
        
        self.btn_rename = ttk.Button(self.toolbar, text="تغییر نام" if self.lang=="fa" else "Rename", command=self.rename_column)
        self.btn_rename.pack(side="left", padx=4)
        self.btn_delcol = ttk.Button(self.toolbar, text="حذف ستون" if self.lang=="fa" else "Delete", command=self.delete_column)
        self.btn_delcol.pack(side="left", padx=4)

    def _clear_placeholder(self, event):
        placeholder_fa = "نام جدید را وارد کنید"
        placeholder_en = "Enter new name"
        current_text = self.new_name_entry.get()
        if current_text in (placeholder_fa, placeholder_en):
            self.new_name_entry.delete(0, "end")

    def _bind_shortcuts(self):
        self.root.bind_all("<Control-o>", lambda e: self.open_file())
        self.root.bind_all("<Control-s>", lambda e: self.save_file())
        self.root.bind_all("<Control-z>", lambda e: self.undo_action())
        self.root.bind_all("<Control-y>", lambda e: self.redo_action())

    def _update_status(self):
        if self.df is not None:
            self.status_var.set(f"تعداد سطرها: {len(self.df)} | تعداد ستون‌ها: {len(self.df.columns)}" if self.lang=="fa" else f"Rows: {len(self.df)} | Columns: {len(self.df.columns)}")
        else:
            self.status_var.set("آماده — لطفا فایل را باز کنید" if self.lang=="fa" else "Ready — please open a file")

    def open_file(self):
        title = "باز کردن" if self.lang=="fa" else "Open"
        ftypes = (("Excel files","*.xlsx *.xls"),("CSV files","*.csv"),("All files","*.*"))
        fname = filedialog.askopenfilename(title=title, filetypes=ftypes)
        if not fname: return
        try:
            if fname.lower().endswith(".csv"):
                self.df = pd.read_csv(fname, encoding="utf-8")
            else:
                self.df = pd.read_excel(fname)
            self.filename = fname
            self.history.clear()
            self.redo_stack.clear()
            self._refresh_table()
            self._update_columns()
            self.log(f"فایل بارگذاری شد: {os.path.basename(fname)}" if self.lang=="fa" else f"File opened: {os.path.basename(fname)}")
        except Exception as e:
            self.log(f"ERROR: {e}")

    def save_file(self):
        if self.df is None:
            self.log("ابتدا یک فایل باز کنید" if self.lang=="fa" else "Please open a file first")
            return
        title = "ذخیره" if self.lang=="fa" else "Save"
        ftypes = (("Excel files","*.xlsx"),("CSV files","*.csv"))
        fname = filedialog.asksaveasfilename(title=title, filetypes=ftypes, defaultextension=".xlsx")
        if not fname: return
        try:
            if fname.lower().endswith(".csv"):
                self.df.to_csv(fname, index=False, encoding="utf-8-sig")
            else:
                self.df.to_excel(fname, index=False)
            self.log(f"فایل ذخیره شد: {os.path.basename(fname)}" if self.lang=="fa" else f"File saved: {os.path.basename(fname)}")
        except Exception as e:
            self.log(f"ERROR: {e}")

    def log(self, msg):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.logs.append(entry)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", entry+"\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self._update_status()

    def save_logs(self):
        title = "ذخیره لاگ‌ها" if self.lang=="fa" else "Save Logs"
        fn = filedialog.asksaveasfilename(title=title, defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if not fn: return
        with open(fn,"w", encoding="utf-8") as f:
            f.write("\n".join(self.logs))
        self.log("لاگ‌ها ذخیره شدند" if self.lang=="fa" else "Logs saved")

    def clear_logs(self):
        self.logs.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0","end")
        self.log_text.configure(state="disabled")
        self.log("لاگ‌ها پاک شدند" if self.lang=="fa" else "Logs cleared")

    def _refresh_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        if self.df is None:
            self.tree["columns"] = []
            return
        cols = list(self.df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100, minwidth=50, stretch=False)
        for _, row in self.df.head(1000).iterrows():
            self.tree.insert("", "end", values=list(row))
        self._update_status()

    def _update_columns(self):
        if self.df is not None:
            cols = list(self.df.columns)
            self.col_combo['values'] = cols
            if cols: 
                self.column_var.set(cols[0])
        else:
            self.col_combo['values'] = []
            self.column_var.set("")

    def remove_empty_rows(self):
        if self.df is None:
            self.log("ابتدا یک فایل باز کنید" if self.lang=="fa" else "Please open a file first")
            return
        self._push_history()
        removed = len(self.df) - len(self.df.dropna())
        self.df = self.df.dropna()
        self._refresh_table()
        self.log(f"حذف سطرهای خالی — تعداد حذف شده: {removed}" if self.lang=="fa" else f"Dropped empty rows — Removed: {removed}")

    def remove_duplicate_rows(self):
        if self.df is None:
            self.log("ابتدا یک فایل باز کنید" if self.lang=="fa" else "Please open a file first")
            return
        self._push_history()
        removed = len(self.df) - len(self.df.drop_duplicates())
        self.df = self.df.drop_duplicates()
        self._refresh_table()
        self.log(f"حذف سطرهای تکراری — تعداد حذف شده: {removed}" if self.lang=="fa" else f"Dropped duplicate rows — Removed: {removed}")

    def rename_column(self):
        if self.df is None:
            self.log("ابتدا یک فایل باز کنید" if self.lang=="fa" else "Please open a file first")
            return
        old = self.column_var.get()
        new = self.new_name_var.get().strip()
        if not old or not new:
            self.log("لطفاً ستون و نام جدید را وارد کنید" if self.lang=="fa" else "Enter column and new name")
            return
        self._push_history()
        self.df.rename(columns={old:new}, inplace=True)
        self._refresh_table()
        self._update_columns()
        self.log(f"تغییر نام ستون: {old} -> {new}" if self.lang=="fa" else f"Renamed column: {old} -> {new}")
        self.new_name_var.set("")

    def delete_column(self):
        if self.df is None:
            self.log("ابتدا یک فایل باز کنید" if self.lang=="fa" else "Please open a file first")
            return
        col = self.column_var.get()
        if not col:
            self.log("لطفاً یک ستون انتخاب کنید" if self.lang=="fa" else "Select a column")
            return
        self._push_history()
        self.df.drop(columns=[col], inplace=True)
        self._refresh_table()
        self._update_columns()
        self.log(f"حذف ستون: {col}" if self.lang=="fa" else f"Deleted column: {col}")

    def _push_history(self):
        if self.df is not None:
            self.history.append(self.df.copy())
            if len(self.history) > 20: 
                self.history.pop(0)
            self.redo_stack.clear()

    def undo_action(self):
        if not self.history:
            self.log("بازگردانی — عملی برای بازگشت نیست" if self.lang=="fa" else "Undo — nothing to undo")
            return
        self.redo_stack.append(self.df.copy())
        self.df = self.history.pop()
        self._refresh_table()
        self._update_columns()
        self.log("بازگردانی" if self.lang=="fa" else "Undo")

    def redo_action(self):
        if not self.redo_stack:
            self.log("جلو — عملی برای جلو نیست" if self.lang=="fa" else "Redo — nothing to redo")
            return
        self.history.append(self.df.copy())
        self.df = self.redo_stack.pop()
        self._refresh_table()
        self._update_columns()
        self.log("جلو" if self.lang=="fa" else "Redo")

    def toggle_language(self):
        self.lang = "en" if self.lang == "fa" else "fa"

        self._build_menus()
        self._update_toolbar_texts()
        self.log_frame.config(text="لاگ‌ها" if self.lang=="fa" else "Logs")
        self._refresh_table()
        self._update_columns()
        self._update_status()
        self.log(f"Language switched to {self.lang}")
        self.root.title("بلوم کلینر" if self.lang=="fa" else "Bloom Cleaner")

    def open_link(self, url):
        import webbrowser
        webbrowser.open(url)

    def show_about(self):
        about_text = {
            "fa": [
                "این یک برنامه اوپن سورس رایگان برای",
                "تسریع فرآیند پاکسازی داده ها است",
                "",
                "توسعه داده شده توسط دیتا بلوم",
                "linktr.ee/Data_Bloom",
                "\"پاکسازی داده فقط حذف سطر خالی نیست\"",
            ],
            "en": [
                "This is a free open-source program for",
                "accelerating the data cleaning process",
                "",
                "Developed by Data Bloom",
                "linktr.ee/Data_Bloom",
                "\"Data cleaning is not just about removing empty rows\"",
            ]
        }
        
        about_window = tk.Toplevel(self.root)
        about_window.title("درباره ما" if self.lang=="fa" else "About Us")
        about_window.geometry("400x250")
        about_window.resizable(False, False)
        about_window.configure(bg="#f8f9fa")
        
        title_label = tk.Label(about_window, 
                            text="Data Bloom" if self.lang=="en" else "دیتا بلوم",
                            font=(self.base_font[0], 16, "bold"),
                            bg="#f8f9fa",
                            fg="#2c3e50")
        title_label.pack(pady=20)
        
        for line in about_text[self.lang]:
            if "linktr.ee/Data_Bloom" in line:
                link_label = tk.Label(about_window,
                                    text=line,
                                    font=(self.base_font[0], 10),
                                    bg="#f8f9fa",
                                    fg="#3498db",
                                    cursor="hand2")
                link_label.pack(pady=2)
                link_label.bind("<Button-1>", lambda e: self.open_link("linktr.ee/Data_Bloom"))
            else:
                label = tk.Label(about_window,
                            text=line,
                            font=(self.base_font[0], 10),
                            bg="#f8f9fa",
                            fg="#34495e")
                label.pack(pady=2)
        
        about_window.transient(self.root)
        about_window.grab_set()
        about_window.focus_set()

def main():
    root = tk.Tk()
    app = DataCleaner(root)
    root.mainloop()

if __name__ == "__main__":
    main()