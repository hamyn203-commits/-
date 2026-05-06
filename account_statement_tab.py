import csv
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from api_client import APIClient
from rtl_utils import rtl


class AccountStatementTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None):
        super().__init__(master)
        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback

        self.configure(fg_color="#1e1e1e")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.pharmacies = []
        self.pharmacy_dict = {}
        self.statement = None

        self.create_ui()
        self.load_pharmacies()

    def ar(self, text):
        return rtl("" if text is None else str(text))

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception:
                pass

    def safe_float(self, value):
        try:
            return float(value)
        except Exception:
            return 0.0

    def money(self, value):
        try:
            return f"{float(value):,.2f} جنيه"
        except Exception:
            return "0.00 جنيه"

    def parse_date_input(self, value):
        value = (value or "").strip()
        if not value:
            return None
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except Exception:
            return "__invalid__"

    def translate_movement_type(self, movement_type):
        return {
            "order": "مبيعات / طلب",
            "payment": "تحصيل",
            "return": "مرتجع",
            "adjustment": "تسوية",
        }.get(str(movement_type or "").lower(), "حركة")

    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.grid(row=0, column=0, sticky="ew", padx=22, pady=18)
        header_content.grid_columnconfigure(0, weight=1)

        title_area = ctk.CTkFrame(header_content, fg_color="transparent")
        title_area.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            title_area,
            text=self.ar("كشف حساب الصيدليات"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right",
        ).pack(anchor="e")

        ctk.CTkLabel(
            title_area,
            text=self.ar("دفتر حركة مالي (مدين/دائن) مع رصيد جاري لكل صيدلية"),
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        ).pack(anchor="e", pady=(4, 0))

        filters_card = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=12)
        filters_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        filters_card.grid_columnconfigure(0, weight=1)
        filters_card.grid_rowconfigure(3, weight=1)

        controls = ctk.CTkFrame(filters_card, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))

        self.pharmacy_var = ctk.StringVar(value="")
        self.pharmacy_menu = ctk.CTkOptionMenu(
            controls,
            variable=self.pharmacy_var,
            values=["اختر الصيدلية..."],
            command=lambda _v: self.refresh_statement(auto=True),
            width=320,
            height=38,
            fg_color="#1e1e1e",
            button_color="#2196F3",
            button_hover_color="#1976D2",
            font=ctk.CTkFont(size=13),
        )
        self.pharmacy_menu.pack(side="right", padx=(0, 10))

        ctk.CTkLabel(
            controls,
            text=self.ar("الصيدلية:"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#dcdcdc",
        ).pack(side="right", padx=(0, 10))

        self.date_from_entry = ctk.CTkEntry(controls, width=140, height=38, placeholder_text="من YYYY-MM-DD", justify="right")
        self.date_from_entry.pack(side="right", padx=(0, 8))
        self.date_to_entry = ctk.CTkEntry(controls, width=140, height=38, placeholder_text="إلى YYYY-MM-DD", justify="right")
        self.date_to_entry.pack(side="right", padx=(0, 10))

        ctk.CTkButton(
            controls,
            text=self.ar("تحديث"),
            height=38,
            width=120,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.refresh_statement,
        ).pack(side="left")

        ctk.CTkButton(
            controls,
            text=self.ar("تصدير CSV"),
            height=38,
            width=130,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.export_csv,
        ).pack(side="left", padx=(8, 0))

        self.summary_frame = ctk.CTkFrame(filters_card, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.summary_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.current_balance_var = ctk.StringVar(value="—")
        self.total_orders_var = ctk.StringVar(value="—")
        self.total_payments_var = ctk.StringVar(value="—")
        self.total_returns_var = ctk.StringVar(value="—")
        self.net_movement_var = ctk.StringVar(value="—")

        self.create_summary_card(self.summary_frame, "الرصيد الحالي", self.current_balance_var, "#4CAF50", 0)
        self.create_summary_card(self.summary_frame, "إجمالي الطلبات (مدين)", self.total_orders_var, "#FF9800", 1)
        self.create_summary_card(self.summary_frame, "إجمالي التحصيلات (دائن)", self.total_payments_var, "#2196F3", 2)
        self.create_summary_card(self.summary_frame, "إجمالي المرتجعات", self.total_returns_var, "#9C27B0", 3)
        self.create_summary_card(self.summary_frame, "صافي الحركة", self.net_movement_var, "#f44336", 4)

        self.state_frame = ctk.CTkFrame(filters_card, fg_color="#1f1f1f", corner_radius=10)
        self.state_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.state_label = ctk.CTkLabel(
            self.state_frame,
            text=self.ar("اختر صيدلية لعرض كشف الحساب."),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        )
        self.state_label.pack(fill="x", padx=14, pady=12)

        table_card = ctk.CTkFrame(filters_card, fg_color="#252525", corner_radius=12, border_width=1, border_color="#3a3a3a")
        table_card.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            table_card,
            text=self.ar("دفتر الحركة"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))

        tree_frame = ctk.CTkFrame(table_card, fg_color="#2d2d2d", corner_radius=8)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        columns = ("date", "type", "ref", "desc", "debit", "credit", "balance")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=16)

        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure("Treeview", background="#2d2d2d", foreground="white", fieldbackground="#2d2d2d", rowheight=30)
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#4CAF50", font=("Arial", 11, "bold"))
        style.map("Treeview", background=[("selected", "#2196F3")])

        self.tree.heading("date", text="التاريخ")
        self.tree.heading("type", text="النوع")
        self.tree.heading("ref", text="المرجع")
        self.tree.heading("desc", text="البيان")
        self.tree.heading("debit", text="مدين")
        self.tree.heading("credit", text="دائن")
        self.tree.heading("balance", text="الرصيد")

        self.tree.column("date", width=150, anchor="center")
        self.tree.column("type", width=140, anchor="center")
        self.tree.column("ref", width=140, anchor="center")
        self.tree.column("desc", width=420, anchor="e")
        self.tree.column("debit", width=110, anchor="center")
        self.tree.column("credit", width=110, anchor="center")
        self.tree.column("balance", width=120, anchor="center")

        self.tree.tag_configure("debit", foreground="#FF9800")
        self.tree.tag_configure("credit", foreground="#2196F3")
        self.tree.tag_configure("opening", foreground="#bdbdbd")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)

    def create_summary_card(self, parent, title, variable, color, column):
        card = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
        card.grid(row=0, column=column, sticky="ew", padx=6, pady=6)
        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(card, text=self.ar(title), font=ctk.CTkFont(size=12, weight="bold"), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", padx=10)
        ctk.CTkLabel(card, textvariable=variable, font=ctk.CTkFont(size=16, weight="bold"), text_color=color, anchor="e", justify="right").pack(fill="x", padx=10, pady=(4, 10))

    def load_pharmacies(self):
        try:
            self.update_status("جاري تحميل الصيدليات لكشف الحساب...")
            self.pharmacies = self.api_client.get_pharmacies() or []
            self.pharmacy_dict = {p.get("name", f"صيدلية {p.get('id')}"): p for p in self.pharmacies}
            options = ["اختر الصيدلية..."] + list(self.pharmacy_dict.keys())
            self.pharmacy_menu.configure(values=options)
            self.pharmacy_var.set(options[0])
            self.update_status(f"تم تحميل {len(self.pharmacies)} صيدلية")
        except Exception as exc:
            self.update_status("تعذر تحميل الصيدليات")
            messagebox.showerror("كشف الحساب", f"تعذر تحميل الصيدليات:\n{exc}")

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def set_empty_state(self, message):
        self.state_label.configure(text=self.ar(message))
        self.clear_table()
        self.current_balance_var.set("—")
        self.total_orders_var.set("—")
        self.total_payments_var.set("—")
        self.total_returns_var.set("—")
        self.net_movement_var.set("—")

    def refresh_statement(self, auto=False):
        name = self.pharmacy_var.get()
        if not name or name == "اختر الصيدلية...":
            if not auto:
                self.set_empty_state("اختر صيدلية لعرض كشف الحساب.")
            return
        pharmacy = self.pharmacy_dict.get(name)
        if not pharmacy:
            self.set_empty_state("تعذر تحديد الصيدلية المختارة.")
            return

        date_from = self.parse_date_input(self.date_from_entry.get())
        date_to = self.parse_date_input(self.date_to_entry.get())
        if date_from == "__invalid__" or date_to == "__invalid__":
            messagebox.showwarning("التاريخ", "صيغة التاريخ يجب أن تكون YYYY-MM-DD")
            return

        try:
            self.update_status("جاري تحميل كشف الحساب...")
            result = self.api_client.get_pharmacy_account_statement(pharmacy.get("id"), date_from=date_from, date_to=date_to)
            if not result:
                self.set_empty_state("تعذر تحميل كشف الحساب. تأكد من اتصال السيرفر.")
                self.update_status("فشل تحميل كشف الحساب")
                return
            self.statement = result
            self.render_statement()
            self.update_status("تم تحميل كشف الحساب")
        except Exception as exc:
            self.set_empty_state("حدث خطأ أثناء تحميل كشف الحساب.")
            self.update_status("فشل تحميل كشف الحساب")
            messagebox.showerror("كشف الحساب", f"فشل تحميل كشف الحساب:\n{exc}")

    def render_statement(self):
        stmt = self.statement or {}
        entries = stmt.get("entries") or []
        totals = stmt.get("totals") or {}
        opening = self.safe_float(stmt.get("opening_balance", 0.0))
        current_balance = self.safe_float(stmt.get("current_balance", 0.0))

        self.current_balance_var.set(self.money(current_balance))
        self.total_orders_var.set(self.money(totals.get("total_orders", 0.0)))
        self.total_payments_var.set(self.money(totals.get("total_payments", 0.0)))
        self.total_returns_var.set(self.money(totals.get("total_returns", 0.0)))
        self.net_movement_var.set(self.money(totals.get("net_movement", 0.0)))

        if not entries:
            self.set_empty_state("لا توجد حركات مالية ضمن الفترة المحددة.")
            return

        self.state_label.configure(text=self.ar(f"رصيد افتتاحي للفترة: {self.money(opening)}"))

        self.clear_table()
        self.tree.insert(
            "",
            "end",
            values=(
                "—",
                "رصيد افتتاحي",
                "—",
                "بداية الفترة",
                "",
                "",
                f"{opening:,.2f}",
            ),
            tags=("opening",),
        )

        for item in entries:
            raw_date = item.get("date")
            date_text = "-"
            try:
                if isinstance(raw_date, str):
                    date_text = raw_date.replace("T", " ").split(".")[0][:16]
                elif hasattr(raw_date, "strftime"):
                    date_text = raw_date.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_text = "-"

            debit = self.safe_float(item.get("debit"))
            credit = self.safe_float(item.get("credit"))
            balance = self.safe_float(item.get("running_balance"))
            movement_type = self.translate_movement_type(item.get("movement_type"))
            ref = item.get("reference", "")
            desc = item.get("description", "")

            tags = ()
            if debit > 0:
                tags = ("debit",)
            elif credit > 0:
                tags = ("credit",)

            self.tree.insert(
                "",
                "end",
                values=(
                    date_text,
                    movement_type,
                    ref,
                    desc,
                    f"{debit:,.2f}" if debit else "",
                    f"{credit:,.2f}" if credit else "",
                    f"{balance:,.2f}",
                ),
                tags=tags,
            )

    def export_csv(self):
        stmt = self.statement or {}
        entries = stmt.get("entries") or []
        if not entries:
            messagebox.showwarning("تصدير", "لا توجد بيانات لتصديرها")
            return

        pharmacy_name = (stmt.get("pharmacy_name") or "pharmacy").replace(" ", "_")
        df = stmt.get("date_from") or ""
        dt = stmt.get("date_to") or ""
        suffix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"كشف_حساب_{pharmacy_name}_{df}_{dt}_{suffix}.csv".replace("__", "_").replace("..", ".")

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="حفظ كشف الحساب",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(["التاريخ", "النوع", "المرجع", "البيان", "مدين", "دائن", "الرصيد"])
                writer.writerow(["—", "رصيد افتتاحي", "—", "بداية الفترة", "", "", stmt.get("opening_balance", 0.0)])
                for item in entries:
                    raw_date = item.get("date")
                    date_text = raw_date
                    if isinstance(raw_date, str):
                        date_text = raw_date.replace("T", " ").split(".")[0][:16]
                    writer.writerow([
                        date_text,
                        self.translate_movement_type(item.get("movement_type")),
                        item.get("reference", ""),
                        item.get("description", ""),
                        item.get("debit", 0.0) or "",
                        item.get("credit", 0.0) or "",
                        item.get("running_balance", 0.0),
                    ])
            self.update_status(f"تم تصدير كشف الحساب: {file_path}")
            messagebox.showinfo("تصدير", "تم تصدير كشف الحساب بنجاح")
        except Exception as exc:
            messagebox.showerror("تصدير", f"فشل التصدير:\n{exc}")

