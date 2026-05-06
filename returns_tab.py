import csv
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from api_client import APIClient
from rtl_utils import rtl


class ReturnsTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None):
        super().__init__(master)
        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback

        self.configure(fg_color="#1e1e1e")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.pharmacy_dict = {}
        self.orders_cache = []
        self.order_dict = {}

        self.is_saving = False

        self.create_ui()
        self.load_initial_data()

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
            return f"{float(value):,.2f}"
        except Exception:
            return "0.00"

    def format_dt(self, value):
        if not value:
            return "-"
        if isinstance(value, str):
            return value.replace("T", " ").split(".")[0][:16]
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)

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
            text=self.ar("المرتجعات"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right",
        ).pack(anchor="e")

        ctk.CTkLabel(
            title_area,
            text=self.ar("تسجيل مرتجع (خصم من المديونية) مع سجل كامل قابل للتصدير"),
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        ).pack(anchor="e", pady=(4, 0))

        self.input_frame = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=12)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.input_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        ctk.CTkLabel(
            self.input_frame,
            text=self.ar("تسجيل مرتجع"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4CAF50",
        ).grid(row=0, column=0, columnspan=6, pady=(16, 6))

        self.summary_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=10, pady=(0, 10))
        self.summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.balance_var = ctk.StringVar(value="—")
        self.returns_count_var = ctk.StringVar(value="—")
        self.returns_total_var = ctk.StringVar(value="—")
        self.balance_after_var = ctk.StringVar(value="—")

        self.create_summary_card(self.summary_frame, "المديونية الحالية", self.balance_var, "#FF9800", 0)
        self.create_summary_card(self.summary_frame, "عدد المرتجعات", self.returns_count_var, "#2196F3", 1)
        self.create_summary_card(self.summary_frame, "إجمالي المرتجعات", self.returns_total_var, "#9C27B0", 2)
        self.create_summary_card(self.summary_frame, "الرصيد بعد المرتجع", self.balance_after_var, "#4CAF50", 3)

        ctk.CTkLabel(self.input_frame, text=self.ar("الصيدلية:"), font=ctk.CTkFont(size=14), text_color="white").grid(row=2, column=5, padx=5, pady=10, sticky="e")
        self.pharmacy_var = ctk.StringVar(value="")
        self.pharmacy_menu = ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.pharmacy_var,
            values=["جاري التحميل..."],
            command=self.on_pharmacy_select,
            font=ctk.CTkFont(size=13),
            width=260,
        )
        self.pharmacy_menu.grid(row=2, column=4, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.input_frame, text=self.ar("الطلب (اختياري):"), font=ctk.CTkFont(size=14), text_color="white").grid(row=2, column=3, padx=5, pady=10, sticky="e")
        self.order_var = ctk.StringVar(value="بدون طلب محدد")
        self.order_menu = ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.order_var,
            values=["بدون طلب محدد"],
            command=lambda _v: self.update_balance_preview(),
            font=ctk.CTkFont(size=13),
            width=260,
        )
        self.order_menu.grid(row=2, column=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.input_frame, text=self.ar("قيمة المرتجع:"), font=ctk.CTkFont(size=14), text_color="white").grid(row=2, column=1, padx=5, pady=10, sticky="e")
        self.amount_entry = ctk.CTkEntry(self.input_frame, placeholder_text="أدخل قيمة المرتجع...", justify="right", font=ctk.CTkFont(size=13), width=200)
        self.amount_entry.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.amount_entry.bind("<KeyRelease>", lambda _e: self.update_balance_preview())

        ctk.CTkLabel(self.input_frame, text=self.ar("ملاحظات:"), font=ctk.CTkFont(size=14), text_color="white").grid(row=3, column=5, padx=5, pady=10, sticky="e")
        self.notes_entry = ctk.CTkEntry(self.input_frame, placeholder_text="سبب المرتجع أو التفاصيل...", justify="right", font=ctk.CTkFont(size=13))
        self.notes_entry.grid(row=3, column=0, columnspan=5, padx=10, pady=10, sticky="ew")

        self.save_btn = ctk.CTkButton(
            self.input_frame,
            text=self.ar("💾 حفظ المرتجع"),
            command=self.save_return,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
        )
        self.save_btn.grid(row=4, column=0, columnspan=6, pady=(8, 16))

        self.table_frame = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=12)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(2, weight=1)

        top_bar = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text=self.ar("سجل المرتجعات"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2196F3",
            anchor="e",
            justify="right",
        ).pack(side="right")

        ctk.CTkButton(
            top_bar,
            text=self.ar("تصدير CSV"),
            height=36,
            width=120,
            fg_color="#607D8B",
            hover_color="#455A64",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.export_returns_csv,
        ).pack(side="left")

        self.search_entry = ctk.CTkEntry(top_bar, width=260, height=36, placeholder_text="بحث في السجل...", justify="right")
        self.search_entry.pack(side="left", padx=(10, 10))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.apply_search_filter())

        self.state_label = ctk.CTkLabel(
            self.table_frame,
            text=self.ar("اختر صيدلية لعرض سجل المرتجعات."),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        )
        self.state_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        tree_wrap = ctk.CTkFrame(self.table_frame, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
        tree_wrap.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        tree_wrap.grid_columnconfigure(0, weight=1)
        tree_wrap.grid_rowconfigure(0, weight=1)

        columns = ("id", "order", "amount", "date", "before", "after", "notes")
        self.tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", height=14)

        style = ttk.Style()
        try:
            style.theme_use("default")
        except Exception:
            pass
        style.configure("Treeview", background="#2d2d2d", foreground="white", fieldbackground="#2d2d2d", rowheight=30)
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#4CAF50", font=("Arial", 11, "bold"))
        style.map("Treeview", background=[("selected", "#2196F3")])

        self.tree.heading("id", text="رقم")
        self.tree.heading("order", text="الطلب")
        self.tree.heading("amount", text="قيمة المرتجع")
        self.tree.heading("date", text="التاريخ")
        self.tree.heading("before", text="قبل")
        self.tree.heading("after", text="بعد")
        self.tree.heading("notes", text="ملاحظات")

        self.tree.column("id", width=70, anchor="center")
        self.tree.column("order", width=90, anchor="center")
        self.tree.column("amount", width=120, anchor="center")
        self.tree.column("date", width=150, anchor="center")
        self.tree.column("before", width=110, anchor="center")
        self.tree.column("after", width=110, anchor="center")
        self.tree.column("notes", width=420, anchor="e")

        scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)

        self.filtered_rows = []

    def create_summary_card(self, parent, title, variable, color, column):
        card = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
        card.grid(row=0, column=column, sticky="ew", padx=6, pady=6)
        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(card, text=self.ar(title), font=ctk.CTkFont(size=12, weight="bold"), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", padx=10)
        ctk.CTkLabel(card, textvariable=variable, font=ctk.CTkFont(size=16, weight="bold"), text_color=color, anchor="e", justify="right").pack(fill="x", padx=10, pady=(4, 10))

    def load_initial_data(self):
        try:
            self.update_status("جاري تحميل بيانات المرتجعات...")
            pharmacies = self.api_client.get_pharmacies() or []
            self.pharmacy_dict = {p.get("name", f"صيدلية {p.get('id')}"): p for p in pharmacies}
            options = ["اختر الصيدلية..."] + list(self.pharmacy_dict.keys())
            self.pharmacy_menu.configure(values=options)
            self.pharmacy_var.set(options[0])
            self.orders_cache = self.api_client.get_orders() if hasattr(self.api_client, "get_orders") else []
            self.update_status("تم تحميل بيانات المرتجعات")
        except Exception as exc:
            self.update_status("تعذر تحميل بيانات المرتجعات")
            messagebox.showerror("المرتجعات", f"تعذر تحميل البيانات:\n{exc}")

    def get_selected_pharmacy(self):
        name = self.pharmacy_var.get()
        if not name or name == "اختر الصيدلية...":
            return None
        return self.pharmacy_dict.get(name)

    def update_order_menu_for_pharmacy(self, pharmacy_id):
        self.order_dict = {}
        options = ["بدون طلب محدد"]
        for order in self.orders_cache or []:
            if order.get("pharmacy_id") != pharmacy_id:
                continue
            label = f"طلب #{order.get('id')} - {order.get('order_number', '')}"
            self.order_dict[label] = order
            options.append(label)
        self.order_menu.configure(values=options)
        self.order_var.set(options[0])

    def on_pharmacy_select(self, _value=None):
        pharmacy = self.get_selected_pharmacy()
        if not pharmacy:
            self.balance_var.set("—")
            self.returns_count_var.set("—")
            self.returns_total_var.set("—")
            self.balance_after_var.set("—")
            self.state_label.configure(text=self.ar("اختر صيدلية لعرض سجل المرتجعات."))
            self.clear_table()
            return

        balance = self.safe_float(pharmacy.get("balance", 0.0))
        self.balance_var.set(f"{self.money(balance)}")
        self.update_order_menu_for_pharmacy(pharmacy.get("id"))
        self.refresh_returns_table(pharmacy.get("id"))
        self.update_balance_preview()

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def refresh_returns_table(self, pharmacy_id):
        self.clear_table()
        self.filtered_rows = []
        try:
            rows = self.api_client.get_pharmacy_returns(pharmacy_id, limit=500)
            if not rows:
                self.state_label.configure(text=self.ar("لا توجد مرتجعات لهذه الصيدلية حتى الآن."))
                self.returns_count_var.set("0")
                self.returns_total_var.set("0.00")
                return

            total = 0.0
            for r in rows:
                total += self.safe_float(r.get("amount", 0.0))
                order_id = r.get("order_id") or "-"
                values = (
                    r.get("id", "-"),
                    order_id,
                    self.money(r.get("amount", 0.0)),
                    self.format_dt(r.get("created_at")),
                    self.money(r.get("balance_before", 0.0)),
                    self.money(r.get("balance_after", 0.0)),
                    r.get("notes", "") or "",
                )
                self.filtered_rows.append(values)

            self.returns_count_var.set(str(len(rows)))
            self.returns_total_var.set(self.money(total))
            self.state_label.configure(text=self.ar(f"آخر {len(rows)} مرتجع — يمكنك البحث أو التصدير."))
            self.apply_search_filter()
        except Exception as exc:
            self.state_label.configure(text=self.ar("تعذر تحميل سجل المرتجعات."))
            self.update_status("فشل تحميل سجل المرتجعات")
            messagebox.showerror("المرتجعات", f"تعذر تحميل السجل:\n{exc}")

    def apply_search_filter(self):
        query = (self.search_entry.get() or "").strip().lower()
        self.clear_table()
        if not query:
            for values in self.filtered_rows:
                self.tree.insert("", "end", values=values)
            return
        for values in self.filtered_rows:
            hay = " ".join(str(v) for v in values).lower()
            if query in hay:
                self.tree.insert("", "end", values=values)

    def update_balance_preview(self):
        pharmacy = self.get_selected_pharmacy()
        if not pharmacy:
            return
        current = self.safe_float(pharmacy.get("balance", 0.0))
        amount = self.safe_float((self.amount_entry.get() or "").strip())
        after = max(current - max(amount, 0.0), 0.0)
        self.balance_after_var.set(self.money(after))

    def get_selected_order_id(self):
        label = self.order_var.get()
        if not label or label == "بدون طلب محدد":
            return None
        order = self.order_dict.get(label)
        return order.get("id") if order else None

    def save_return(self):
        if self.is_saving:
            return
        pharmacy = self.get_selected_pharmacy()
        if not pharmacy:
            messagebox.showwarning("المرتجعات", "اختر صيدلية أولاً")
            return

        amount_text = (self.amount_entry.get() or "").strip()
        if not amount_text:
            messagebox.showwarning("المرتجعات", "أدخل قيمة المرتجع")
            return
        amount = self.safe_float(amount_text)
        if amount <= 0:
            messagebox.showwarning("المرتجعات", "قيمة المرتجع يجب أن تكون أكبر من صفر")
            return

        current_balance = self.safe_float(pharmacy.get("balance", 0.0))
        if current_balance <= 0:
            messagebox.showwarning("المرتجعات", "لا توجد مديونية حالية على هذه الصيدلية")
            return
        if amount > current_balance:
            messagebox.showerror("المرتجعات", f"قيمة المرتجع أكبر من المديونية الحالية ({self.money(current_balance)})")
            return

        notes = (self.notes_entry.get() or "").strip()
        order_id = self.get_selected_order_id()

        try:
            self.is_saving = True
            self.save_btn.configure(state="disabled", text=self.ar("جاري الحفظ..."))
            self.update_status("جاري تسجيل المرتجع...")
            result = self.api_client.add_return(pharmacy.get("id"), amount, order_id=order_id, notes=notes)
            if not result:
                messagebox.showerror("المرتجعات", "فشل تسجيل المرتجع. تأكد من اتصال السيرفر.")
                self.update_status("فشل تسجيل المرتجع")
                return

            new_balance = self.safe_float(result.get("balance_after", current_balance - amount))
            pharmacy["balance"] = new_balance
            self.balance_var.set(self.money(new_balance))
            self.amount_entry.delete(0, "end")
            self.notes_entry.delete(0, "end")
            self.order_var.set("بدون طلب محدد")
            self.update_balance_preview()
            self.refresh_returns_table(pharmacy.get("id"))
            self.update_status("تم تسجيل المرتجع بنجاح")
            messagebox.showinfo("المرتجعات", f"تم تسجيل المرتجع بنجاح\nالرصيد الجديد: {self.money(new_balance)}")
        except Exception as exc:
            self.update_status("فشل تسجيل المرتجع")
            messagebox.showerror("المرتجعات", f"حدث خطأ أثناء الحفظ:\n{exc}")
        finally:
            self.is_saving = False
            self.save_btn.configure(state="normal", text=self.ar("💾 حفظ المرتجع"))

    def export_returns_csv(self):
        pharmacy = self.get_selected_pharmacy()
        if not pharmacy:
            messagebox.showwarning("تصدير", "اختر صيدلية أولاً")
            return
        if not self.filtered_rows:
            messagebox.showwarning("تصدير", "لا توجد بيانات لتصديرها")
            return
        pharmacy_name = (pharmacy.get("name") or "pharmacy").replace(" ", "_")
        suffix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"مرتجعات_{pharmacy_name}_{suffix}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="حفظ ملف المرتجعات",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["رقم", "الطلب", "قيمة المرتجع", "التاريخ", "قبل", "بعد", "ملاحظات"])
                for row in self.filtered_rows:
                    writer.writerow(row)
            self.update_status(f"تم تصدير المرتجعات: {file_path}")
            messagebox.showinfo("تصدير", "تم تصدير المرتجعات بنجاح")
        except Exception as exc:
            messagebox.showerror("تصدير", f"فشل التصدير:\n{exc}")

