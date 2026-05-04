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
RED = "#EF4444"
RED_HOVER = "#DC2626"
TEXT = "#FFFFFF"
MUTED = "#B8C5E0"
DIM = "#7A8BA0"


class SuppliersTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, role="admin"):
        super().__init__(master, fg_color=BG)
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.role = role or "admin"
        self.suppliers = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.create_ui()
        self.load_suppliers()

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

    def can_manage(self):
        return self.role == "admin"

    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self.ar("الموردين"),
            font=("Arial", 30, "bold"),
            text_color=GREEN,
            anchor="e",
            justify="right",
        ).grid(row=0, column=0, sticky="e")
        ctk.CTkLabel(
            header,
            text=self.ar("إدارة الموردين، أرصدة التوريد، وسجل التعاملات"),
            font=("Arial", 13),
            text_color=MUTED,
            anchor="e",
            justify="right",
        ).grid(row=1, column=0, sticky="e", pady=(4, 0))

        ctk.CTkButton(
            header,
            text=self.ar("إضافة مورد"),
            width=150,
            height=40,
            corner_radius=10,
            fg_color=GREEN,
            hover_color=GREEN_HOVER,
            font=("Arial", 13, "bold"),
            command=self.open_supplier_dialog,
            state="normal" if self.can_manage() else "disabled",
        ).grid(row=0, column=1, rowspan=2, padx=(16, 0), sticky="e")

        self.summary = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        self.summary.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 10))
        for col in range(3):
            self.summary.grid_columnconfigure(col, weight=1)

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=SURFACE,
            corner_radius=18,
            border_width=1,
            border_color=BORDER,
            scrollbar_button_color=BLUE,
            scrollbar_button_hover_color=BLUE_HOVER,
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def clear(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        for widget in self.summary.winfo_children():
            widget.destroy()

    def load_suppliers(self):
        self.clear()
        try:
            self.suppliers = self.api_client.get_suppliers()
        except Exception:
            self.suppliers = []

        total_balance = sum(float(item.get("balance") or 0) for item in self.suppliers)
        active_count = sum(1 for item in self.suppliers if int(item.get("purchases_count") or 0) > 0)
        self.create_summary_card(0, "إجمالي الموردين", len(self.suppliers), "مورد مسجل", BLUE)
        self.create_summary_card(1, "أرصدة مستحقة", self.money(total_balance), "جنيه", RED if total_balance > 0 else GREEN)
        self.create_summary_card(2, "موردين نشطين", active_count, "لهم فواتير", GREEN)

        if not self.suppliers:
            self.show_empty()
            return

        for index, supplier in enumerate(self.suppliers):
            self.create_supplier_row(index, supplier)
        self.update_status(f"تم تحميل {len(self.suppliers)} مورد")

    def create_summary_card(self, col, title, value, hint, color):
        card = ctk.CTkFrame(self.summary, fg_color=CARD, corner_radius=14)
        card.grid(row=0, column=col, sticky="ew", padx=10, pady=10)
        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=10).pack(fill="x", padx=12, pady=(10, 8))
        ctk.CTkLabel(card, text=self.ar(title), font=("Arial", 13, "bold"), text_color=MUTED, anchor="e").pack(fill="x", padx=14)
        ctk.CTkLabel(card, text=str(value), font=("Arial", 24, "bold"), text_color=color).pack(fill="x", padx=14, pady=(4, 0))
        ctk.CTkLabel(card, text=self.ar(hint), font=("Arial", 11), text_color=DIM, anchor="e").pack(fill="x", padx=14, pady=(0, 12))

    def show_empty(self):
        box = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=16)
        box.grid(row=0, column=0, sticky="ew", padx=14, pady=24)
        ctk.CTkLabel(box, text=self.ar("لا توجد موردين حتى الآن"), font=("Arial", 18, "bold"), text_color=MUTED).pack(pady=(28, 8))
        ctk.CTkLabel(box, text=self.ar("ابدأ بإضافة أول مورد لتسجيل فواتير التوريد لاحقًا"), font=("Arial", 12), text_color=DIM).pack(pady=(0, 28))

    def create_supplier_row(self, row, supplier):
        card = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, sticky="ew", padx=12, pady=8)
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text=self.ar(supplier.get("name", "")), font=("Arial", 18, "bold"), text_color=TEXT, anchor="e").grid(row=0, column=0, sticky="e")
        ctk.CTkLabel(top, text=self.ar(supplier.get("company") or "بدون شركة"), font=("Arial", 12), text_color=MUTED, anchor="e").grid(row=1, column=0, sticky="e")

        balance = float(supplier.get("balance") or 0)
        badge_color = RED if balance > 0 else GREEN
        ctk.CTkLabel(top, text=self.money(balance), font=("Arial", 18, "bold"), text_color=badge_color).grid(row=0, column=1, padx=(18, 0), sticky="e")
        ctk.CTkLabel(top, text=self.ar("الرصيد"), font=("Arial", 11), text_color=DIM).grid(row=1, column=1, padx=(18, 0), sticky="e")

        meta = ctk.CTkFrame(card, fg_color="#20283A", corner_radius=12)
        meta.grid(row=1, column=0, sticky="ew", padx=14, pady=8)
        for col in range(3):
            meta.grid_columnconfigure(col, weight=1)
        self.meta_label(meta, 0, "الهاتف", supplier.get("phone") or "-")
        self.meta_label(meta, 1, "العنوان", supplier.get("address") or "-")
        self.meta_label(meta, 2, "الفواتير", supplier.get("purchases_count") or 0)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 12))
        ctk.CTkButton(actions, text=self.ar("تعديل"), width=90, height=32, fg_color=BLUE, hover_color=BLUE_HOVER, command=lambda: self.open_supplier_dialog(supplier), state="normal" if self.can_manage() else "disabled").pack(side="right", padx=4)
        ctk.CTkButton(actions, text=self.ar("حذف"), width=90, height=32, fg_color=RED, hover_color=RED_HOVER, command=lambda: self.delete_supplier(supplier), state="normal" if self.can_manage() else "disabled").pack(side="right", padx=4)

    def meta_label(self, parent, col, title, value):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(box, text=self.ar(title), font=("Arial", 11), text_color=DIM, anchor="e").pack(fill="x")
        ctk.CTkLabel(box, text=self.ar(value), font=("Arial", 13, "bold"), text_color=MUTED, anchor="e").pack(fill="x")

    def open_supplier_dialog(self, supplier=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("مورد")
        dialog.geometry("480x620")
        dialog.minsize(440, 520)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=BG)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        form = ctk.CTkScrollableFrame(
            dialog,
            fg_color=BG,
            scrollbar_button_color=BLUE,
            scrollbar_button_hover_color=BLUE_HOVER,
        )
        form.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 0))

        footer = ctk.CTkFrame(dialog, fg_color=SURFACE, corner_radius=0)
        footer.grid(row=1, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        fields = {}
        values = supplier or {}
        for label, key in [
            ("اسم المورد", "name"),
            ("الهاتف", "phone"),
            ("العنوان", "address"),
            ("الشركة", "company"),
            ("الرصيد الافتتاحي", "balance"),
            ("ملاحظات", "notes"),
        ]:
            ctk.CTkLabel(form, text=self.ar(label), text_color=MUTED, anchor="e", font=("Arial", 12, "bold")).pack(fill="x", padx=24, pady=(12, 4))
            entry = ctk.CTkEntry(form, height=38, justify="right")
            entry.pack(fill="x", padx=24)
            entry.insert(0, str(values.get(key, "")))
            fields[key] = entry

        def save():
            try:
                name = fields["name"].get().strip()
                if not name:
                    messagebox.showerror("خطأ", "اسم المورد مطلوب")
                    return
                balance = float(fields["balance"].get() or 0)
                if supplier:
                    result = self.api_client.update_supplier(supplier["id"], name, fields["phone"].get(), fields["address"].get(), fields["company"].get(), balance, fields["notes"].get())
                else:
                    result = self.api_client.create_supplier(name, fields["phone"].get(), fields["address"].get(), fields["company"].get(), balance, fields["notes"].get())
                if result:
                    messagebox.showinfo("تم", "تم حفظ بيانات المورد بنجاح")
                    dialog.destroy()
                    self.load_suppliers()
                else:
                    messagebox.showerror("خطأ", "تعذر حفظ المورد")
            except ValueError:
                messagebox.showerror("خطأ", "الرصيد يجب أن يكون رقمًا")
            except Exception as exc:
                messagebox.showerror("خطأ", f"تعذر حفظ المورد: {exc}")

        ctk.CTkButton(
            footer,
            text=self.ar("حفظ"),
            height=42,
            fg_color=GREEN,
            hover_color=GREEN_HOVER,
            font=("Arial", 14, "bold"),
            command=save
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=14)

    def delete_supplier(self, supplier):
        if not messagebox.askyesno("تأكيد", f"هل تريد حذف المورد {supplier.get('name')}؟"):
            return
        if self.api_client.delete_supplier(supplier.get("id")):
            messagebox.showinfo("تم", "تم حذف المورد")
            self.load_suppliers()
        else:
            messagebox.showerror("خطأ", "لا يمكن حذف مورد مرتبط بفواتير مشتريات")
