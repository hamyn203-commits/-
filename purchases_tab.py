import customtkinter as ctk
from tkinter import messagebox
from api_client import APIClient
from rtl_utils import rtl


BG = "#0A0E1A"
SURFACE = "#141821"
CARD = "#1A1F2E"
BORDER = "#2A3348"
GREEN = "#10B981"
GREEN_HOVER = "#059669"
BLUE = "#3B82F6"
BLUE_HOVER = "#2563EB"
ORANGE = "#F59E0B"
RED = "#EF4444"
TEXT = "#FFFFFF"
MUTED = "#B8C5E0"
DIM = "#7A8BA0"


class PurchasesTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, role="admin"):
        super().__init__(master, fg_color=BG)
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.role = role or "admin"
        self.suppliers = []
        self.products = []
        self.purchases = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.create_ui()
        self.refresh_data()

    def ar(self, text):
        return rtl("" if text is None else str(text))

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception:
                pass

    def money(self, value):
        try:
            return f"{float(value or 0):,.2f}"
        except Exception:
            return "0.00"

    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=self.ar("المشتريات والتوريد"), font=("Arial", 30, "bold"), text_color=GREEN, anchor="e").grid(row=0, column=0, sticky="e")
        ctk.CTkLabel(header, text=self.ar("سجل فواتير الموردين وزيادة المخزون تلقائيًا"), font=("Arial", 13), text_color=MUTED, anchor="e").grid(row=1, column=0, sticky="e", pady=(4, 0))
        ctk.CTkButton(header, text=self.ar("فاتورة توريد جديدة"), width=170, height=40, corner_radius=10, fg_color=GREEN, hover_color=GREEN_HOVER, font=("Arial", 13, "bold"), command=self.open_purchase_dialog).grid(row=0, column=1, rowspan=2, padx=(16, 0), sticky="e")
        ctk.CTkButton(header, text=self.ar("تحديث"), width=100, height=40, corner_radius=10, fg_color=BLUE, hover_color=BLUE_HOVER, command=self.refresh_data).grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="e")

        self.summary = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        self.summary.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 10))
        for col in range(4):
            self.summary.grid_columnconfigure(col, weight=1)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=18, border_width=1, border_color=BORDER, scrollbar_button_color=BLUE, scrollbar_button_hover_color=BLUE_HOVER)
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def clear(self):
        for widget in self.summary.winfo_children():
            widget.destroy()
        for widget in self.list_frame.winfo_children():
            widget.destroy()

    def refresh_data(self):
        self.clear()
        try:
            self.suppliers = self.api_client.get_suppliers()
            self.products = self.api_client.get_products()
            self.purchases = self.api_client.get_purchases()
        except Exception:
            self.suppliers, self.products, self.purchases = [], [], []

        total = sum(float(item.get("total_amount") or 0) for item in self.purchases)
        paid = sum(float(item.get("amount_paid") or 0) for item in self.purchases)
        remaining = sum(float(item.get("remaining_amount") or 0) for item in self.purchases)
        self.summary_card(0, "عدد الفواتير", len(self.purchases), "فاتورة توريد", BLUE)
        self.summary_card(1, "إجمالي التوريد", self.money(total), "جنيه", GREEN)
        self.summary_card(2, "المدفوع", self.money(paid), "جنيه", ORANGE)
        self.summary_card(3, "المتبقي", self.money(remaining), "جنيه", RED if remaining > 0 else GREEN)

        if not self.purchases:
            self.show_empty()
            return

        for index, purchase in enumerate(self.purchases):
            self.create_purchase_row(index, purchase)
        self.update_status(f"تم تحميل {len(self.purchases)} فاتورة مشتريات")

    def summary_card(self, col, title, value, hint, color):
        card = ctk.CTkFrame(self.summary, fg_color=CARD, corner_radius=14)
        card.grid(row=0, column=col, sticky="ew", padx=8, pady=10)
        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=10).pack(fill="x", padx=12, pady=(10, 8))
        ctk.CTkLabel(card, text=self.ar(title), font=("Arial", 12, "bold"), text_color=MUTED, anchor="e").pack(fill="x", padx=14)
        ctk.CTkLabel(card, text=str(value), font=("Arial", 22, "bold"), text_color=color).pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(card, text=self.ar(hint), font=("Arial", 11), text_color=DIM, anchor="e").pack(fill="x", padx=14, pady=(0, 12))

    def show_empty(self):
        box = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=16)
        box.grid(row=0, column=0, sticky="ew", padx=14, pady=24)
        ctk.CTkLabel(box, text=self.ar("لا توجد فواتير مشتريات حتى الآن"), font=("Arial", 18, "bold"), text_color=MUTED).pack(pady=(28, 8))
        ctk.CTkLabel(box, text=self.ar("أنشئ فاتورة توريد لتحديث المخزون وربطها بالمورد"), font=("Arial", 12), text_color=DIM).pack(pady=(0, 28))

    def create_purchase_row(self, row, purchase):
        card = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=purchase.get("invoice_number", ""), font=("Arial", 18, "bold"), text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text=self.ar(purchase.get("supplier_name", "")), font=("Arial", 14, "bold"), text_color=GREEN, anchor="e").grid(row=0, column=1, sticky="e")

        status, color = self.status_text(purchase.get("status"))
        ctk.CTkLabel(top, text=self.ar(status), font=("Arial", 12, "bold"), text_color=color).grid(row=1, column=1, sticky="e", pady=(3, 0))

        meta = ctk.CTkFrame(card, fg_color="#20283A", corner_radius=12)
        meta.grid(row=1, column=0, sticky="ew", padx=14, pady=8)
        for col in range(4):
            meta.grid_columnconfigure(col, weight=1)
        self.meta(meta, 0, "الإجمالي", self.money(purchase.get("total_amount")))
        self.meta(meta, 1, "المدفوع", self.money(purchase.get("amount_paid")))
        self.meta(meta, 2, "المتبقي", self.money(purchase.get("remaining_amount")))
        self.meta(meta, 3, "عدد الأصناف", len(purchase.get("items") or []))

        items_text = " | ".join(f"{item.get('product_name')} x {item.get('quantity')}" for item in (purchase.get("items") or [])[:4])
        ctk.CTkLabel(card, text=self.ar(items_text or "بدون أصناف"), font=("Arial", 12), text_color=MUTED, anchor="e", justify="right").grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

    def meta(self, parent, col, title, value):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="ew", padx=8, pady=8)
        ctk.CTkLabel(box, text=self.ar(title), font=("Arial", 11), text_color=DIM, anchor="e").pack(fill="x")
        ctk.CTkLabel(box, text=self.ar(value), font=("Arial", 13, "bold"), text_color=MUTED, anchor="e").pack(fill="x")

    def status_text(self, status):
        mapping = {
            "paid": ("مدفوع", GREEN),
            "partial": ("مدفوع جزئي", ORANGE),
            "unpaid": ("غير مدفوع", RED),
        }
        return mapping.get(str(status or "").lower(), ("غير محدد", DIM))

    def product_options(self):
        return [f"{p.get('id')} - {p.get('name')}" for p in self.products]

    def supplier_options(self):
        return [f"{s.get('id')} - {s.get('name')}" for s in self.suppliers]

    def parse_id(self, value):
        try:
            return int(str(value).split(" - ")[0])
        except Exception:
            return None

    def open_purchase_dialog(self):
        if not self.suppliers:
            messagebox.showwarning("تنبيه", "أضف موردًا أولًا قبل تسجيل المشتريات")
            return
        if not self.products:
            messagebox.showwarning("تنبيه", "أضف منتجات أولًا قبل تسجيل المشتريات")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("فاتورة توريد")
        dialog.geometry("760x650")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=BG)
        dialog.grid_columnconfigure(0, weight=1)

        form = ctk.CTkScrollableFrame(dialog, fg_color=SURFACE, corner_radius=16)
        form.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text=self.ar("فاتورة توريد جديدة"), font=("Arial", 24, "bold"), text_color=GREEN, anchor="e").grid(row=0, column=0, sticky="e", padx=14, pady=(14, 12))

        supplier_var = ctk.StringVar(value=self.supplier_options()[0])
        self.field_label(form, "المورد", 1)
        ctk.CTkOptionMenu(form, values=self.supplier_options(), variable=supplier_var, height=38).grid(row=2, column=0, sticky="ew", padx=14)

        invoice_entry = self.entry(form, "رقم الفاتورة اختياري", 3)
        paid_entry = self.entry(form, "المدفوع الآن", 5)
        paid_entry.insert(0, "0")
        notes_entry = self.entry(form, "ملاحظات", 7)

        items_frame = ctk.CTkFrame(form, fg_color=CARD, corner_radius=14)
        items_frame.grid(row=9, column=0, sticky="ew", padx=14, pady=(16, 10))
        items_frame.grid_columnconfigure(0, weight=1)
        item_rows = []

        def add_item_row():
            row_frame = ctk.CTkFrame(items_frame, fg_color="#20283A", corner_radius=12)
            row_frame.pack(fill="x", padx=10, pady=8)
            product_var = ctk.StringVar(value=self.product_options()[0])
            ctk.CTkOptionMenu(row_frame, values=self.product_options(), variable=product_var, width=300, height=34).pack(side="right", padx=6, pady=8)
            qty = ctk.CTkEntry(row_frame, width=90, height=34, placeholder_text="الكمية", justify="center")
            qty.pack(side="right", padx=6, pady=8)
            cost = ctk.CTkEntry(row_frame, width=110, height=34, placeholder_text="سعر الشراء", justify="center")
            cost.pack(side="right", padx=6, pady=8)
            ctk.CTkButton(row_frame, text=self.ar("حذف"), width=70, height=32, fg_color=RED, hover_color="#DC2626", command=lambda: remove_item(row_frame)).pack(side="left", padx=6, pady=8)
            item_rows.append((row_frame, product_var, qty, cost))

        def remove_item(row_frame):
            for row in list(item_rows):
                if row[0] == row_frame:
                    item_rows.remove(row)
                    break
            row_frame.destroy()

        ctk.CTkButton(form, text=self.ar("إضافة صنف للفاتورة"), height=38, fg_color=BLUE, hover_color=BLUE_HOVER, command=add_item_row).grid(row=10, column=0, sticky="ew", padx=14, pady=(4, 12))
        add_item_row()

        def save():
            try:
                items = []
                for _, product_var, qty_entry, cost_entry in item_rows:
                    product_id = self.parse_id(product_var.get())
                    quantity = int(qty_entry.get() or 0)
                    unit_cost = float(cost_entry.get() or 0)
                    if not product_id or quantity <= 0:
                        messagebox.showerror("خطأ", "راجع المنتج والكمية في كل صف")
                        return
                    items.append({"product_id": product_id, "quantity": quantity, "unit_cost": unit_cost})
                if not items:
                    messagebox.showerror("خطأ", "أضف صنفًا واحدًا على الأقل")
                    return
                result = self.api_client.create_purchase(
                    supplier_id=self.parse_id(supplier_var.get()),
                    items=items,
                    invoice_number=invoice_entry.get().strip(),
                    amount_paid=float(paid_entry.get() or 0),
                    notes=notes_entry.get().strip(),
                )
                if result:
                    messagebox.showinfo("تم", "تم تسجيل فاتورة التوريد وتحديث المخزون")
                    dialog.destroy()
                    self.refresh_data()
                else:
                    messagebox.showerror("خطأ", "تعذر تسجيل فاتورة التوريد")
            except ValueError:
                messagebox.showerror("خطأ", "راجع الأرقام المدخلة")
            except Exception as exc:
                messagebox.showerror("خطأ", f"تعذر تسجيل الفاتورة: {exc}")

        ctk.CTkButton(form, text=self.ar("حفظ فاتورة التوريد"), height=44, fg_color=GREEN, hover_color=GREEN_HOVER, font=("Arial", 14, "bold"), command=save).grid(row=11, column=0, sticky="ew", padx=14, pady=(6, 18))

    def field_label(self, parent, text, row):
        ctk.CTkLabel(parent, text=self.ar(text), font=("Arial", 12, "bold"), text_color=MUTED, anchor="e").grid(row=row, column=0, sticky="e", padx=14, pady=(8, 4))

    def entry(self, parent, label, row):
        self.field_label(parent, label, row)
        entry = ctk.CTkEntry(parent, height=38, justify="right")
        entry.grid(row=row + 1, column=0, sticky="ew", padx=14)
        return entry
