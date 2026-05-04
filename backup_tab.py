import os
import shutil
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk
from rtl_utils import rtl


class BackupTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None):
        super().__init__(master)

        self.api_client = api_client
        self.status_callback = status_callback
        self.database_path = "pharmacy.db"
        self.backup_folder = "backups"

        self.configure(fg_color="#1e1e1e")
        self.create_ui()
        self.refresh_database_info()
        self.refresh_backups_list()

    def ar(self, text):
        return rtl("" if text is None else str(text))

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception:
                pass

    def format_file_size(self, size_bytes):
        try:
            size_bytes = float(size_bytes)
        except (TypeError, ValueError):
            return "-"

        if size_bytes < 1024:
            return f"{int(size_bytes)} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        if size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def format_timestamp(self, timestamp):
        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "-"

    def get_file_info(self, path):
        if not os.path.exists(path):
            return {
                "exists": False,
                "status": "غير موجودة",
                "size": "-",
                "modified": "-"
            }

        try:
            return {
                "exists": True,
                "status": "موجودة",
                "size": self.format_file_size(os.path.getsize(path)),
                "modified": self.format_timestamp(os.path.getmtime(path))
            }
        except OSError:
            return {
                "exists": True,
                "status": "موجودة",
                "size": "-",
                "modified": "-"
            }

    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=14, border_width=1, border_color="#3a3a3a")
        header.pack(fill="x", padx=24, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self.ar("النسخ الاحتياطي"),
            font=("Arial", 32, "bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 4))

        ctk.CTkLabel(
            header,
            text=self.ar("احفظ نسخة آمنة من بيانات مخزن الندا وتابع حالة الحماية من مكان واحد"),
            font=("Arial", 15),
            text_color="#9e9e9e",
            anchor="e",
            justify="right"
        ).grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 18))

        self.content = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.create_overview_card()
        self.create_database_card()
        self.create_controls_card()
        self.create_backup_history_card()

    def create_card(self, title):
        card = ctk.CTkFrame(self.content, fg_color="#2d2d2d", corner_radius=12, border_width=1, border_color="#3a3a3a")
        card.pack(fill="x", padx=18, pady=10)

        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=("Arial", 18, "bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=20, pady=(18, 10))

        return card

    def create_overview_card(self):
        card = self.create_card("ملخص الحماية")
        self.overview_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.overview_frame.pack(fill="x", padx=16, pady=(0, 18))
        self.overview_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

    def create_metric_card(self, parent, title, value, subtitle, color, column):
        box = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
        box.grid(row=0, column=column, sticky="ew", padx=6, pady=4)
        ctk.CTkFrame(box, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(box, text=self.ar(title), font=("Arial", 12, "bold"), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", padx=12)
        ctk.CTkLabel(box, text=self.ar(value), font=("Arial", 18, "bold"), text_color=color, anchor="e", justify="right").pack(fill="x", padx=12, pady=(5, 0))
        ctk.CTkLabel(box, text=self.ar(subtitle), font=("Arial", 11), text_color="#9e9e9e", anchor="e", justify="right").pack(fill="x", padx=12, pady=(4, 12))

    def add_info_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            row,
            text=self.ar(label),
            width=180,
            font=("Arial", 14, "bold"),
            text_color="#dcdcdc",
            anchor="e",
            justify="right"
        ).pack(side="right")

        ctk.CTkLabel(
            row,
            text=self.ar(value),
            font=("Arial", 14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).pack(side="right", fill="x", expand=True, padx=(0, 16))

    def create_database_card(self):
        card = self.create_card("حالة قاعدة البيانات")
        self.database_info_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.database_info_frame.pack(fill="x", pady=(0, 18))

    def create_controls_card(self):
        card = self.create_card("أزرار التحكم")
        buttons_frame = ctk.CTkFrame(card, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(4, 20))

        ctk.CTkButton(
            buttons_frame,
            text="إنشاء نسخة احتياطية الآن",
            height=42,
            width=220,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=("Arial", 14, "bold"),
            command=self.create_backup
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            buttons_frame,
            text="تحديث القائمة",
            height=42,
            width=150,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=("Arial", 14, "bold"),
            command=self.refresh_all
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            buttons_frame,
            text="فتح مجلد النسخ",
            height=42,
            width=170,
            fg_color="#455A64",
            hover_color="#546E7A",
            font=("Arial", 14, "bold"),
            command=self.open_backup_folder
        ).pack(side="right")

    def create_backup_history_card(self):
        card = self.create_card("سجل النسخ الاحتياطية")
        self.backup_list_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.backup_list_frame.pack(fill="x", padx=20, pady=(0, 18))

    def refresh_all(self):
        self.refresh_database_info()
        self.refresh_backups_list()
        self.refresh_overview()
        self.update_status("تم تحديث قائمة النسخ الاحتياطية")

    def refresh_database_info(self):
        for widget in self.database_info_frame.winfo_children():
            widget.destroy()

        info = self.get_file_info(self.database_path)
        self.add_info_row(self.database_info_frame, "اسم قاعدة البيانات:", self.database_path)
        self.add_info_row(self.database_info_frame, "الحالة:", info["status"])
        self.add_info_row(self.database_info_frame, "حجم الملف:", info["size"])
        self.add_info_row(self.database_info_frame, "آخر تعديل:", info["modified"])
        self.refresh_overview()

    def refresh_overview(self):
        if not hasattr(self, "overview_frame"):
            return
        for widget in self.overview_frame.winfo_children():
            widget.destroy()
        db_info = self.get_file_info(self.database_path)
        backups = self.get_backup_files()
        total_size = 0
        for backup in backups:
            try:
                total_size += os.path.getsize(backup["path"])
            except OSError:
                pass
        last_backup = backups[0]["modified"] if backups else "لا توجد"
        protection = "محمي" if db_info["exists"] and backups else ("يحتاج نسخة" if db_info["exists"] else "قاعدة غير موجودة")
        protection_color = "#4CAF50" if protection == "محمي" else "#FF9800"
        self.create_metric_card(self.overview_frame, "حالة الحماية", protection, "حسب وجود قاعدة ونسخ", protection_color, 0)
        self.create_metric_card(self.overview_frame, "عدد النسخ", str(len(backups)), "آخر 12 نسخة ظاهرة", "#2196F3", 1)
        self.create_metric_card(self.overview_frame, "آخر نسخة", last_backup, "تاريخ آخر حماية", "#9C27B0", 2)
        self.create_metric_card(self.overview_frame, "حجم النسخ", self.format_file_size(total_size), "إجمالي مجلد backups", "#00BCD4", 3)

    def clear_backup_list(self):
        for widget in self.backup_list_frame.winfo_children():
            widget.destroy()

    def get_backup_files(self):
        if not os.path.isdir(self.backup_folder):
            return []

        backups = []
        try:
            for file_name in os.listdir(self.backup_folder):
                file_path = os.path.join(self.backup_folder, file_name)
                if os.path.isfile(file_path) and file_name.lower().endswith(".db"):
                    backups.append({
                        "name": file_name,
                        "path": file_path,
                        "size": self.format_file_size(os.path.getsize(file_path)),
                        "modified_raw": os.path.getmtime(file_path),
                        "modified": self.format_timestamp(os.path.getmtime(file_path))
                    })
        except OSError:
            return []

        return sorted(backups, key=lambda item: item["modified_raw"], reverse=True)

    def refresh_backups_list(self):
        self.clear_backup_list()

        backups = self.get_backup_files()
        if not backups:
            self.show_empty_state()
            self.refresh_overview()
            return

        for backup in backups[:12]:
            self.create_backup_row(backup)
        self.refresh_overview()

    def show_empty_state(self):
        empty_frame = ctk.CTkFrame(self.backup_list_frame, fg_color="#3a3a3a", corner_radius=8)
        empty_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            empty_frame,
            text=self.ar("لا توجد نسخ احتياطية حتى الآن"),
            font=("Arial", 14),
            text_color="#9e9e9e",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=14, pady=14)

    def create_backup_row(self, backup):
        row = ctk.CTkFrame(self.backup_list_frame, fg_color="#3a3a3a", corner_radius=8)
        row.pack(fill="x", pady=5)
        row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            row,
            text=backup["name"],
            font=("Arial", 13, "bold"),
            text_color="white",
            anchor="e",
            justify="right"
        ).grid(row=0, column=1, sticky="e", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            row,
            text=self.ar(f'الحجم: {backup["size"]} | آخر تعديل: {backup["modified"]}'),
            font=("Arial", 12),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).grid(row=1, column=1, sticky="e", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            row,
            text=self.ar("جاهزة للاستعادة اليدوية"),
            font=("Arial", 11, "bold"),
            text_color="#4CAF50",
            fg_color="#253a28",
            corner_radius=8,
            width=140,
        ).grid(row=0, column=0, rowspan=2, padx=12, pady=10, sticky="w")

    def create_backup(self):
        if not os.path.exists(self.database_path):
            self.refresh_database_info()
            self.update_status("فشل إنشاء النسخة الاحتياطية")
            messagebox.showerror(
                "فشل إنشاء النسخة الاحتياطية",
                "ملف قاعدة البيانات pharmacy.db غير موجود."
            )
            return

        try:
            os.makedirs(self.backup_folder, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_folder, backup_name)
            shutil.copy2(self.database_path, backup_path)
        except Exception as exc:
            self.update_status("فشل إنشاء النسخة الاحتياطية")
            messagebox.showerror(
                "فشل إنشاء النسخة الاحتياطية",
                f"تعذر إنشاء النسخة الاحتياطية.\n{exc}"
            )
            return

        self.refresh_database_info()
        self.refresh_backups_list()
        self.update_status("تم إنشاء النسخة الاحتياطية بنجاح")
        messagebox.showinfo("نجاح", "تم إنشاء النسخة الاحتياطية بنجاح")

    def open_backup_folder(self):
        try:
            os.makedirs(self.backup_folder, exist_ok=True)
            os.startfile(self.backup_folder)
            self.update_status("تم فتح مجلد النسخ الاحتياطية")
        except Exception as exc:
            self.update_status("فشل فتح مجلد النسخ الاحتياطية")
            messagebox.showerror("خطأ", f"فشل فتح مجلد النسخ الاحتياطية.\n{exc}")
