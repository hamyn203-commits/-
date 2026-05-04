import customtkinter as ctk
from tkinter import messagebox, filedialog
import json
import os
from rtl_utils import rtl


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, username="admin", role="admin"):
        super().__init__(master)

        self.api_client = api_client
        self.status_callback = status_callback
        self.username = username or "admin"
        self.role = role or "admin"
        self.settings_path = "app_settings.json"
        self.settings = self.load_settings()

        self.configure(fg_color="#1e1e1e")
        self.create_ui()

    def ar(self, text):
        return rtl("" if text is None else str(text))

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception:
                pass
    
    def load_settings(self):
        defaults = {
            "server_url": "http://127.0.0.1:8000",
            "whatsapp_order_notifications": False,
            "smtp_server": "",
            "smtp_port": "587",
            "smtp_email": "",
            "smtp_password": "",
            "auto_backup_enabled": True
        }
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r", encoding="utf-8") as file:
                    defaults.update(json.load(file))
        except Exception:
            pass
        return defaults
    
    def save_settings(self):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as file:
                json.dump(self.settings, file, ensure_ascii=False, indent=2)
            if self.api_client and self.settings.get("server_url"):
                self.api_client.set_base_url(self.settings["server_url"])
            self.update_status("تم حفظ الإعدادات")
            messagebox.showinfo("الإعدادات", "تم حفظ الإعدادات بنجاح")
        except Exception as exc:
            messagebox.showerror("الإعدادات", f"فشل حفظ الإعدادات:\n{exc}")

    def create_card(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color="#2d2d2d", corner_radius=12, border_width=1, border_color="#3a3a3a")
        card.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=("Arial", 18, "bold"),
            text_color="#4CAF50"
        ).pack(anchor="e", padx=20, pady=(18, 10))

        return card

    def add_info_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            row,
            text=self.ar(label),
            font=("Arial", 14, "bold"),
            text_color="#dcdcdc",
            width=150,
            anchor="e",
            justify="right"
        ).pack(side="right")

        ctk.CTkLabel(
            row,
            text=self.ar(value),
            font=("Arial", 14),
            text_color="gray",
            anchor="e",
            justify="right"
        ).pack(side="right", fill="x", expand=True, padx=(0, 14))

    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=14, border_width=1, border_color="#3a3a3a")
        header.pack(fill="x", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self.ar("الإعدادات"),
            font=("Arial", 28, "bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 4))

        ctk.CTkLabel(
            header,
            text=self.ar("إدارة الاتصال والمستخدمين والنسخ وإعدادات التشغيل اليومية"),
            font=("Arial", 14),
            text_color="#9e9e9e",
            anchor="e",
            justify="right"
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 18))

        content = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.create_overview_section(content)
        self.create_system_section(content)
        self.create_user_section(content)
        self.create_language_section(content)
        self.create_connection_section(content)
        self.create_notifications_section(content)
        self.create_email_section(content)
        if self.role == "admin":
            self.create_admin_tools_section(content)
            self.create_users_section(content)
        self.create_backup_section(content)

    def create_overview_section(self, parent):
        card = self.create_card(parent, "ملخص الإعدادات")
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 18))
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
        items = [
            ("السيرفر", self.settings.get("server_url", "http://127.0.0.1:8000"), "#2196F3"),
            ("المستخدم", self.username, "#4CAF50"),
            ("الدور", self.role, "#9C27B0"),
            ("النسخ التلقائي", "مفعل" if self.settings.get("auto_backup_enabled", True) else "متوقف", "#FF9800"),
        ]
        for col, (title, value, color) in enumerate(items):
            box = ctk.CTkFrame(grid, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
            box.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
            ctk.CTkFrame(box, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 6))
            ctk.CTkLabel(box, text=self.ar(title), font=("Arial", 12, "bold"), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", padx=12)
            ctk.CTkLabel(box, text=self.ar(value), font=("Arial", 13, "bold"), text_color=color, anchor="e", justify="right", wraplength=170).pack(fill="x", padx=12, pady=(5, 12))

    def create_system_section(self, parent):
        card = self.create_card(parent, "بيانات النظام")
        self.add_info_row(card, "اسم النظام:", "مخزن الندا")
        self.add_info_row(card, "نوع النظام:", "إدارة مخزن أدوية")
        self.add_info_row(card, "الإصدار:", "v1.0")
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def create_user_section(self, parent):
        card = self.create_card(parent, "المستخدم")
        self.add_info_row(card, "المستخدم الحالي:", self.username)
        self.add_info_row(card, "الدور:", "admin")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(12, 18))

        ctk.CTkButton(
            actions,
            text="تبديل المستخدم",
            width=150,
            height=38,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=("Arial", 13, "bold"),
            command=self.show_switch_user_message
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            actions,
            text="تسجيل الخروج",
            width=150,
            height=38,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            font=("Arial", 13, "bold"),
            command=self.show_logout_message
        ).pack(side="left")

    def create_language_section(self, parent):
        card = self.create_card(parent, "اللغة")
        self.add_info_row(card, "اللغة الحالية:", "العربية")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(8, 18))

        ctk.CTkLabel(
            row,
            text="اختيار اللغة:",
            font=("Arial", 14, "bold"),
            text_color="#dcdcdc",
            width=150,
            anchor="w"
        ).pack(side="left")

        language_menu = ctk.CTkOptionMenu(
            row,
            values=["العربية", "English"],
            width=160,
            fg_color="#1e1e1e",
            button_color="#4CAF50",
            button_hover_color="#45a049",
            command=self.show_language_message
        )
        language_menu.set("العربية")
        language_menu.pack(side="left")

    def create_connection_section(self, parent):
        card = self.create_card(parent, "الاتصال")
        self.add_info_row(card, "عنوان السيرفر الحالي:", self.settings.get("server_url", "http://127.0.0.1:8000"))
        input_row = ctk.CTkFrame(card, fg_color="transparent")
        input_row.pack(fill="x", padx=20, pady=(5, 10))
        self.server_url_entry = ctk.CTkEntry(input_row, width=420, justify="left", height=38)
        self.server_url_entry.insert(0, self.settings.get("server_url", "http://127.0.0.1:8000"))
        self.server_url_entry.pack(side="right", fill="x", expand=True)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(8, 18))
        ctk.CTkButton(
            actions,
            text="اختبار الاتصال",
            width=160,
            height=38,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=("Arial", 13, "bold"),
            command=self.test_connection
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            actions,
            text="حفظ عنوان السيرفر",
            width=160,
            height=38,
            fg_color="#2196F3",
            command=self.save_server_url
        ).pack(side="right")

    def create_notifications_section(self, parent):
        card = self.create_card(parent, "الإشعارات")
        enabled = bool(self.settings.get("whatsapp_order_notifications", False))
        self.whatsapp_notify_var = ctk.BooleanVar(value=enabled)
        ctk.CTkCheckBox(
            card,
            text="تشغيل إشعار واتساب عند اعتماد الطلب",
            variable=self.whatsapp_notify_var,
            command=self.save_notification_settings
        ).pack(anchor="e", padx=20, pady=(8, 18))

    def create_email_section(self, parent):
        card = self.create_card(parent, "إعدادات البريد الإلكتروني")
        self.smtp_entries = {}
        for key, label in [
            ("smtp_server", "SMTP Server"),
            ("smtp_port", "Port"),
            ("smtp_email", "Email"),
            ("smtp_password", "Password"),
        ]:
            ctk.CTkLabel(card, text=label, font=("Arial", 13, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
            entry = ctk.CTkEntry(card, width=320, show="*" if key == "smtp_password" else None)
            entry.insert(0, str(self.settings.get(key, "")))
            entry.pack(anchor="w", padx=20)
            self.smtp_entries[key] = entry
        ctk.CTkButton(card, text="حفظ إعدادات البريد", width=170, command=self.save_email_settings).pack(anchor="w", padx=20, pady=16)

    def create_admin_tools_section(self, parent):
        card = self.create_card(parent, "أدوات المدير")
        self.auto_backup_var = ctk.BooleanVar(value=bool(self.settings.get("auto_backup_enabled", True)))
        ctk.CTkCheckBox(
            card,
            text="تفعيل النسخ الاحتياطي التلقائي اليومي",
            variable=self.auto_backup_var,
            command=self.save_auto_backup_setting
        ).pack(anchor="w", padx=20, pady=(8, 12))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkButton(actions, text="تصدير البيانات JSON", width=150, fg_color="#2196F3", command=self.export_all_data).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="استيراد بيانات JSON", width=150, fg_color="#FF9800", command=self.import_all_data).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="تحديث سجل العمليات", width=150, fg_color="#4CAF50", command=self.refresh_audit_logs).pack(side="left", padx=8)

        self.audit_frame = ctk.CTkFrame(card, fg_color="#252525", corner_radius=8)
        self.audit_frame.pack(fill="x", padx=20, pady=(0, 18))
        self.refresh_audit_logs()

    def create_users_section(self, parent):
        card = self.create_card(parent, "إدارة المستخدمين")
        self.users_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.users_frame.pack(fill="x", padx=20, pady=(4, 8))
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=(4, 18))
        self.new_username_entry = ctk.CTkEntry(form, placeholder_text="اسم المستخدم", width=150)
        self.new_username_entry.pack(side="left", padx=4)
        self.new_password_entry = ctk.CTkEntry(form, placeholder_text="كلمة المرور", width=150, show="*")
        self.new_password_entry.pack(side="left", padx=4)
        self.new_role_var = ctk.StringVar(value="rep")
        ctk.CTkOptionMenu(form, values=["admin", "accountant", "rep"], variable=self.new_role_var, width=130).pack(side="left", padx=4)
        ctk.CTkButton(form, text="إضافة", width=90, command=self.add_user).pack(side="left", padx=4)
        self.refresh_users()

    def create_backup_section(self, parent):
        card = self.create_card(parent, "النسخ الاحتياطي")
        self.add_info_row(card, "مسار قاعدة البيانات:", "pharmacy.db")
        exists = os.path.exists("pharmacy.db")
        size = "-"
        if exists:
            try:
                size = f"{os.path.getsize('pharmacy.db') / 1024:.2f} KB"
            except OSError:
                size = "-"
        self.add_info_row(card, "حالة قاعدة البيانات:", "موجودة" if exists else "غير موجودة")
        self.add_info_row(card, "حجم قاعدة البيانات:", size)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(12, 18))
        ctk.CTkButton(
            actions,
            text="فتح شاشة النسخ الاحتياطي",
            width=220,
            height=38,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=("Arial", 13, "bold"),
            command=self.show_backup_message
        ).pack(side="right")

    def show_switch_user_message(self):
        messagebox.showinfo("تبديل المستخدم", "سيتم دعم تبديل المستخدم لاحقًا")

    def show_logout_message(self):
        if not messagebox.askyesno("تسجيل الخروج", "هل تريد تسجيل الخروج الآن؟"):
            return
        try:
            root = self.winfo_toplevel()
            root.destroy()
            from login_window import LoginWindow
            LoginWindow().run()
        except Exception as exc:
            messagebox.showerror("تسجيل الخروج", f"فشل تسجيل الخروج:\n{exc}")
        return
        messagebox.showinfo("تسجيل الخروج", "سيتم دعم تسجيل الخروج من الإعدادات لاحقًا")

    def show_language_message(self, _selected_language=None):
        selected = _selected_language or "العربية"
        self.settings["language"] = "en" if selected == "English" else "ar"
        self.save_settings()
        messagebox.showinfo("اللغة", "تم حفظ اللغة. أعد فتح البرنامج لتطبيقها بالكامل.")

    def save_server_url(self):
        self.settings["server_url"] = self.server_url_entry.get().strip() or "http://127.0.0.1:8000"
        self.save_settings()

    def save_notification_settings(self):
        self.settings["whatsapp_order_notifications"] = bool(self.whatsapp_notify_var.get())
        self.save_settings()

    def save_email_settings(self):
        for key, entry in self.smtp_entries.items():
            self.settings[key] = entry.get().strip()
        self.save_settings()

    def save_auto_backup_setting(self):
        self.settings["auto_backup_enabled"] = bool(self.auto_backup_var.get())
        self.save_settings()

    def refresh_audit_logs(self):
        if not hasattr(self, "audit_frame"):
            return
        for widget in self.audit_frame.winfo_children():
            widget.destroy()
        if not self.api_client or not hasattr(self.api_client, "get_audit_logs"):
            ctk.CTkLabel(self.audit_frame, text="سجل العمليات غير متاح").pack(anchor="w", padx=12, pady=10)
            return
        logs = self.api_client.get_audit_logs(8)
        if not logs:
            ctk.CTkLabel(self.audit_frame, text="لا توجد عمليات مسجلة بعد").pack(anchor="w", padx=12, pady=10)
            return
        for log in logs:
            text = f"{log.get('created_at', '')} | {log.get('username', 'system')} | {log.get('action', '')} | {log.get('entity', '')} #{log.get('entity_id', '')}"
            ctk.CTkLabel(self.audit_frame, text=text, anchor="w", text_color="#dcdcdc").pack(fill="x", padx=12, pady=3)

    def export_all_data(self):
        if not self.api_client or not hasattr(self.api_client, "export_data"):
            messagebox.showerror("تصدير البيانات", "تصدير البيانات غير متاح")
            return
        data = self.api_client.export_data()
        if not data:
            messagebox.showerror("تصدير البيانات", "فشل تصدير البيانات")
            return
        file_path = filedialog.asksaveasfilename(
            title="حفظ نسخة JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            messagebox.showinfo("تصدير البيانات", "تم تصدير البيانات بنجاح")
        except Exception as exc:
            messagebox.showerror("تصدير البيانات", f"فشل حفظ الملف:\n{exc}")

    def import_all_data(self):
        if not self.api_client or not hasattr(self.api_client, "import_data"):
            messagebox.showerror("استيراد البيانات", "استيراد البيانات غير متاح")
            return
        file_path = filedialog.askopenfilename(
            title="اختيار ملف JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return
        if not messagebox.askyesno("استيراد البيانات", "سيتم استيراد المنتجات والصيدليات غير الموجودة فقط. هل تريد المتابعة؟"):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            result = self.api_client.import_data(payload)
            if result:
                messagebox.showinfo("استيراد البيانات", "تم الاستيراد بنجاح")
                self.refresh_audit_logs()
            else:
                messagebox.showerror("استيراد البيانات", "فشل الاستيراد")
        except Exception as exc:
            messagebox.showerror("استيراد البيانات", f"فشل قراءة الملف:\n{exc}")

    def refresh_users(self):
        for widget in self.users_frame.winfo_children():
            widget.destroy()
        if not self.api_client or not hasattr(self.api_client, "get_users"):
            ctk.CTkLabel(self.users_frame, text="إدارة المستخدمين تحتاج اتصال API").pack(anchor="w")
            return
        users = self.api_client.get_users()
        if not users:
            ctk.CTkLabel(self.users_frame, text="لا يوجد مستخدمون").pack(anchor="w")
            return
        for user in users:
            row = ctk.CTkFrame(self.users_frame, fg_color="#333333", corner_radius=8)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=f"{user.get('username')} | {user.get('role')}", width=260, anchor="w").pack(side="left", padx=8, pady=6)
            ctk.CTkButton(
                row,
                text="حذف",
                width=70,
                fg_color="#c0392b",
                command=lambda uid=user.get("id"): self.delete_user(uid)
            ).pack(side="right", padx=8)

    def add_user(self):
        username = self.new_username_entry.get().strip()
        password = self.new_password_entry.get().strip()
        role = self.new_role_var.get()
        if not username or not password:
            messagebox.showwarning("بيانات ناقصة", "أدخل اسم المستخدم وكلمة المرور")
            return
        result = self.api_client.create_user(username, password, role) if self.api_client else None
        if result:
            self.new_username_entry.delete(0, "end")
            self.new_password_entry.delete(0, "end")
            self.refresh_users()
        else:
            messagebox.showerror("خطأ", "فشل إضافة المستخدم")

    def delete_user(self, user_id):
        if not messagebox.askyesno("تأكيد", "هل تريد حذف المستخدم؟"):
            return
        if self.api_client and self.api_client.delete_user(user_id):
            self.refresh_users()
        else:
            messagebox.showerror("خطأ", "فشل حذف المستخدم")

    def show_backup_message(self):
        messagebox.showinfo("النسخ الاحتياطي", "افتح تبويب النسخ الاحتياطي من القائمة الجانبية لإنشاء نسخة أو متابعة السجل.")

    def test_connection(self):
        try:
            is_connected = bool(
                self.api_client
                and hasattr(self.api_client, "health_check")
                and self.api_client.health_check()
            )
        except Exception:
            is_connected = False

        if is_connected:
            self.update_status("تم الاتصال بالسيرفر بنجاح")
            messagebox.showinfo("اختبار الاتصال", "الاتصال بالسيرفر ناجح")
        else:
            self.update_status("فشل الاتصال بالسيرفر")
            messagebox.showerror("اختبار الاتصال", "فشل الاتصال بالسيرفر")
