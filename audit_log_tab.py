import csv
import os
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from api_client import APIClient
from rtl_utils import rtl


class AuditLogTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None):
        super().__init__(master)

        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback

        self.logs = []
        self.current_offset = 0
        self.limit = 100

        self.configure(fg_color="#1e1e1e")
        self.create_ui()
        self.load_logs()

    def ar(self, text):
        return rtl("" if text is None else str(text))

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception:
                pass

    def check_server_health(self):
        try:
            if hasattr(self.api_client, "health_check"):
                return self.api_client.health_check()
            return True
        except Exception:
            return False

    def clear_log_table(self):
        for widget in list(self.table_frame.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass

    def format_datetime(self, dt_value):
        if not dt_value:
            return "-"
        try:
            if isinstance(dt_value, datetime):
                return dt_value.strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(dt_value, str):
                clean = dt_value.strip().split("T")[0].split(" ")[0]
                if "T" in dt_value:
                    time_part = dt_value.split("T")[1].split(".")[0]
                    return f"{clean} {time_part}"
                return clean
        except Exception:
            pass
        return str(dt_value)

    def create_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.grid(row=0, column=0, sticky="ew", padx=22, pady=18)

        ctk.CTkLabel(
            header_content,
            text="📋",
            font=ctk.CTkFont(size=30),
            text_color="#4CAF50"
        ).pack(side="right", padx=(10, 0))

        title_area = ctk.CTkFrame(header_content, fg_color="transparent")
        title_area.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            title_area,
            text=self.ar("سجل العمليات"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).pack(anchor="e")

        ctk.CTkLabel(
            title_area,
            text=self.ar("تتبع جميع العمليات والأنشطة في النظام"),
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).pack(anchor="e", pady=(4, 0))

        ctk.CTkButton(
            header_content,
            text=self.ar("تحديث"),
            height=38,
            width=120,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.refresh_logs
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            header_content,
            text=self.ar("تصدير CSV"),
            height=38,
            width=120,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.export_to_csv
        ).pack(side="left", padx=(8, 0))

        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.create_filter_section()

        table_card = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        table_card.pack(fill="both", expand=True, pady=10)

        pagination_row = ctk.CTkFrame(table_card, fg_color="transparent")
        pagination_row.pack(fill="x", padx=16, pady=(12, 8))

        self.prev_btn = ctk.CTkButton(
            pagination_row,
            text=self.ar("السابق"),
            height=32,
            width=100,
            fg_color="#607D8B",
            hover_color="#455A64",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.load_prev_page
        )
        self.prev_btn.pack(side="left")

        self.page_label = ctk.CTkLabel(
            pagination_row,
            text=self.ar("الصفحة 1"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#bdbdbd"
        )
        self.page_label.pack(side="left", padx=16)

        self.next_btn = ctk.CTkButton(
            pagination_row,
            text=self.ar("التالي"),
            height=32,
            width=100,
            fg_color="#607D8B",
            hover_color="#455A64",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.load_next_page
        )
        self.next_btn.pack(side="left")

        self.table_frame = ctk.CTkScrollableFrame(table_card, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def create_filter_section(self):
        filter_card = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        filter_card.pack(fill="x", pady=10)
        filter_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            filter_card,
            text=self.ar("تصفية وعرض:"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        ).grid(row=0, column=3, sticky="e", padx=16, pady=(16, 8))

        row1 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row1.grid(row=1, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 8))

        self.search_entry = ctk.CTkEntry(
            row1,
            placeholder_text=self.ar("بحث في السجلات..."),
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.search_entry.pack(side="right", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda e: self.apply_filters())

        ctk.CTkButton(
            row1,
            text=self.ar("بحث"),
            height=38,
            width=100,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.apply_filters
        ).pack(side="right", padx=(8, 0))

        row2 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row2.grid(row=2, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 8))

        self.username_filter = ctk.CTkEntry(
            row2,
            placeholder_text=self.ar("اسم المستخدم"),
            height=38,
            width=180,
            font=ctk.CTkFont(size=13)
        )
        self.username_filter.pack(side="right", padx=4)

        self.action_filter = ctk.CTkEntry(
            row2,
            placeholder_text=self.ar("العملية"),
            height=38,
            width=150,
            font=ctk.CTkFont(size=13)
        )
        self.action_filter.pack(side="right", padx=4)

        self.entity_filter = ctk.CTkEntry(
            row2,
            placeholder_text=self.ar("الكيان"),
            height=38,
            width=150,
            font=ctk.CTkFont(size=13)
        )
        self.entity_filter.pack(side="right", padx=4)

        row3 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row3.grid(row=3, column=0, columnspan=4, sticky="ew", padx=16, pady=(0, 16))

        self.date_from_filter = ctk.CTkEntry(
            row3,
            placeholder_text=self.ar("من تاريخ (YYYY-MM-DD)"),
            height=38,
            width=200,
            font=ctk.CTkFont(size=13)
        )
        self.date_from_filter.pack(side="right", padx=4)

        self.date_to_filter = ctk.CTkEntry(
            row3,
            placeholder_text=self.ar("إلى تاريخ (YYYY-MM-DD)"),
            height=38,
            width=200,
            font=ctk.CTkFont(size=13)
        )
        self.date_to_filter.pack(side="right", padx=4)

        ctk.CTkButton(
            row3,
            text=self.ar("تطبيق الفلاتر"),
            height=38,
            width=140,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.apply_filters
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            row3,
            text=self.ar("مسح الفلاتر"),
            height=38,
            width=140,
            fg_color="#f44336",
            hover_color="#d32f2f",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.clear_filters
        ).pack(side="right", padx=(8, 0))

    def load_logs(self):
        self.update_status("جاري تحميل سجل العمليات...")
        if not self.check_server_health():
            self.show_offline_state()
            return

        try:
            self.logs = self.api_client.get_audit_logs(
                limit=self.limit,
                offset=self.current_offset,
                username=self.username_filter.get().strip() or None,
                action=self.action_filter.get().strip() or None,
                entity=self.entity_filter.get().strip() or None,
                date_from=self.date_from_filter.get().strip() or None,
                date_to=self.date_to_filter.get().strip() or None,
                search=self.search_entry.get().strip() or None
            ) or []
            self.render_log_table()
            self.update_pagination_buttons()
            self.update_status("تم تحميل سجل العمليات بنجاح")
        except Exception as exc:
            self.update_status(f"فشل تحميل سجل العمليات: {exc}")
            self.show_offline_state()

    def refresh_logs(self):
        self.current_offset = 0
        self.load_logs()

    def apply_filters(self):
        self.current_offset = 0
        self.load_logs()

    def clear_filters(self):
        self.search_entry.delete(0, "end")
        self.username_filter.delete(0, "end")
        self.action_filter.delete(0, "end")
        self.entity_filter.delete(0, "end")
        self.date_from_filter.delete(0, "end")
        self.date_to_filter.delete(0, "end")
        self.apply_filters()

    def load_prev_page(self):
        if self.current_offset > 0:
            self.current_offset = max(0, self.current_offset - self.limit)
            self.load_logs()

    def load_next_page(self):
        if len(self.logs) == self.limit:
            self.current_offset += self.limit
            self.load_logs()

    def update_pagination_buttons(self):
        current_page = (self.current_offset // self.limit) + 1
        self.page_label.configure(text=self.ar(f"الصفحة {current_page}"))
        self.prev_btn.configure(state="normal" if self.current_offset > 0 else "disabled")
        self.next_btn.configure(state="normal" if len(self.logs) == self.limit else "disabled")

    def show_offline_state(self):
        self.clear_log_table()
        empty = ctk.CTkFrame(self.table_frame, fg_color="#263a2c", corner_radius=8)
        empty.pack(fill="x", pady=5)
        ctk.CTkLabel(
            empty,
            text=self.ar("تعذر الاتصال بالسيرفر أو لا توجد بيانات"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=14, pady=14)

    def render_log_table(self):
        self.clear_log_table()

        if not self.logs:
            empty = ctk.CTkFrame(self.table_frame, fg_color="#263a2c", corner_radius=8)
            empty.pack(fill="x", pady=5)
            ctk.CTkLabel(
                empty,
                text=self.ar("لا توجد سجلات لعرضها"),
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#4CAF50",
                anchor="e",
                justify="right"
            ).pack(anchor="e", padx=14, pady=14)
            return

        header_row = ctk.CTkFrame(self.table_frame, fg_color="#1f1f1f", corner_radius=8)
        header_row.pack(fill="x", pady=(0, 5))

        headers = [
            "التاريخ والوقت",
            "المستخدم",
            "العملية",
            "الكيان",
            "معرف الكيان",
            "التفاصيل"
        ]

        for header in reversed(headers):
            ctk.CTkLabel(
                header_row,
                text=str(header),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#4CAF50",
                width=160 if header in ["التاريخ والوقت", "التفاصيل"] else 120,
                anchor="e",
                justify="right"
            ).pack(side="right", padx=4, pady=8)

        for index, log in enumerate(self.logs):
            bg_color = "#333333" if index % 2 == 0 else "#3a3a3a"
            row = ctk.CTkFrame(self.table_frame, fg_color=bg_color, corner_radius=8)
            row.pack(fill="x", pady=3)

            row_data = [
                self.format_datetime(log.get("created_at", "-")),
                log.get("username", "-"),
                log.get("action", "-"),
                log.get("entity", "-"),
                log.get("entity_id", "-"),
                log.get("details", "-")
            ]

            for value in reversed(row_data):
                ctk.CTkLabel(
                    row,
                    text=str(value),
                    font=ctk.CTkFont(size=11),
                    text_color="white",
                    width=160 if row_data.index(value) in [0, 5] else 120,
                    anchor="e",
                    justify="right",
                    wraplength=300
                ).pack(side="right", padx=4, pady=6)

    def export_to_csv(self):
        if not self.logs:
            messagebox.showwarning("لا توجد بيانات", "لا توجد سجلات للتصدير")
            return

        default_name = f"audit_logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="حفظ سجل العمليات"
        )

        if not file_path:
            return

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
            headers = ["التاريخ والوقت", "المستخدم", "العملية", "الكيان", "معرف الكيان", "التفاصيل"]
            with open(file_path, "w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(headers)
                for log in self.logs:
                    row = [
                        self.format_datetime(log.get("created_at", "-")),
                        log.get("username", "-"),
                        log.get("action", "-"),
                        log.get("entity", "-"),
                        log.get("entity_id", "-"),
                        log.get("details", "-")
                    ]
                    writer.writerow(row)
            self.update_status(f"تم تصدير سجل العمليات: {file_path}")
            messagebox.showinfo("نجاح", "تم تصدير سجل العمليات بنجاح")
        except Exception as exc:
            self.update_status("فشل تصدير سجل العمليات")
            messagebox.showerror("خطأ", f"فشل تصدير سجل العمليات:\n{exc}")
