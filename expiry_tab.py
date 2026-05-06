import csv
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox

import customtkinter as ctk

from api_client import APIClient
from rtl_utils import rtl


BG = "#0A0E1A"
SURFACE = "#141821"
CARD = "#1A1F2E"
CARD_DARK = "#111827"
BORDER = "#2A3348"
GREEN = "#10B981"
GREEN_HOVER = "#059669"
BLUE = "#3B82F6"
BLUE_HOVER = "#2563EB"
ORANGE = "#F59E0B"
RED = "#EF4444"
PURPLE = "#8B5CF6"
CYAN = "#06B6D4"
GRAY = "#64748B"
TEXT = "#FFFFFF"
MUTED = "#B8C5E0"
DIM = "#7A8BA0"


class ExpiryTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, navigation_callback=None):
        super().__init__(master, fg_color=BG)
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.navigation_callback = navigation_callback
        self.products = []
        self.visible_products = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
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

    def safe_int(self, value):
        try:
            return int(value or 0)
        except Exception:
            return 0

    def parse_date(self, value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        clean = str(value).strip().split("T")[0].split(" ")[0]
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(clean, fmt).date()
            except Exception:
                pass
        return None

    def classify_product(self, product):
        expiry = self.parse_date(product.get("expiry_date"))
        today = datetime.now().date()
        if not expiry:
            return "no_date", "بدون تاريخ", GRAY, None
        days_left = (expiry - today).days
        if days_left < 0:
            return "expired", "منتهي", RED, days_left
        if days_left <= 7:
            return "critical", "حرج جدًا", RED, days_left
        if days_left <= 30:
            return "soon", "قرب الانتهاء", ORANGE, days_left
        return "safe", "صالح", GREEN, days_left

    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self.ar("متابعة الصلاحية"),
            font=("Arial", 30, "bold"),
            text_color=GREEN,
            anchor="e",
            justify="right",
        ).grid(row=0, column=0, sticky="e")
        ctk.CTkLabel(
            header,
            text=self.ar("راقب المنتجات المنتهية وقريبة الانتهاء واتخذ قرارك بسرعة"),
            font=("Arial", 13),
            text_color=MUTED,
            anchor="e",
            justify="right",
        ).grid(row=1, column=0, sticky="e", pady=(4, 0))

        ctk.CTkButton(
            header,
            text=self.ar("تصدير CSV"),
            width=120,
            height=40,
            corner_radius=10,
            fg_color=PURPLE,
            hover_color=PURPLE,
            command=self.export_csv,
        ).grid(row=0, column=1, rowspan=2, padx=(16, 0), sticky="e")
        ctk.CTkButton(
            header,
            text=self.ar("تحديث"),
            width=105,
            height=40,
            corner_radius=10,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            command=self.refresh_data,
        ).grid(row=0, column=2, rowspan=2, padx=(8, 0), sticky="e")

        controls = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=14, border_width=1, border_color=BORDER)
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        controls.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            controls,
            height=38,
            placeholder_text=self.ar("بحث باسم المنتج أو الشركة أو التصنيف..."),
            fg_color=CARD_DARK,
            border_color=BORDER,
            justify="right",
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.search_entry.bind("<KeyRelease>", lambda _event: self.render())

        self.status_filter = ctk.CTkOptionMenu(
            controls,
            values=[
                self.ar("كل المنتجات"),
                self.ar("منتهي"),
                self.ar("حرج خلال 7 أيام"),
                self.ar("قرب الانتهاء خلال 30 يوم"),
                self.ar("صالح"),
                self.ar("بدون تاريخ"),
            ],
            width=190,
            height=38,
            fg_color=CARD,
            button_color=BORDER,
            command=lambda _value: self.render(),
        )
        self.status_filter.set(self.ar("كل المنتجات"))
        self.status_filter.grid(row=0, column=1, padx=8, pady=12)

        ctk.CTkButton(
            controls,
            text=self.ar("فتح المنتجات القريبة"),
            width=150,
            height=38,
            fg_color=ORANGE,
            hover_color=ORANGE,
            command=lambda: self.open_products_filter("expiring_soon"),
        ).grid(row=0, column=2, padx=(8, 12), pady=12)

        self.summary = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        self.summary.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        for col in range(5):
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
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def refresh_data(self):
        try:
            self.products = self.api_client.get_products()
        except Exception:
            self.products = []
        self.render()
        self.update_status("تم تحديث متابعة الصلاحية")

    def clear(self):
        for widget in self.summary.winfo_children():
            widget.destroy()
        for widget in self.list_frame.winfo_children():
            widget.destroy()

    def filter_key(self):
        selected = self.status_filter.get()
        mapping = {
            self.ar("منتهي"): "expired",
            self.ar("حرج خلال 7 أيام"): "critical",
            self.ar("قرب الانتهاء خلال 30 يوم"): "soon",
            self.ar("صالح"): "safe",
            self.ar("بدون تاريخ"): "no_date",
        }
        return mapping.get(selected)

    def render(self):
        self.clear()
        search = (self.search_entry.get() or "").strip().lower()
        wanted = self.filter_key()

        enriched = []
        counts = {"expired": 0, "critical": 0, "soon": 0, "safe": 0, "no_date": 0}
        for product in self.products:
            key, label, color, days_left = self.classify_product(product)
            counts[key] = counts.get(key, 0) + 1
            haystack = " ".join([
                str(product.get("name", "")),
                str(product.get("category_name") or product.get("category") or ""),
                str(product.get("company", "")),
            ]).lower()
            if wanted and key != wanted:
                continue
            if search and search not in haystack:
                continue
            enriched.append((product, key, label, color, days_left))

        self.visible_products = [item[0] for item in enriched]
        self.summary_card(0, "منتهي", counts["expired"], "يحتاج إجراء", RED)
        self.summary_card(1, "حرج", counts["critical"], "خلال 7 أيام", RED)
        self.summary_card(2, "قرب الانتهاء", counts["soon"], "خلال 30 يوم", ORANGE)
        self.summary_card(3, "صالح", counts["safe"], "مخزون آمن", GREEN)
        self.summary_card(4, "بدون تاريخ", counts["no_date"], "يراجع يدويًا", GRAY)

        if not enriched:
            self.show_empty()
            return

        for index, item in enumerate(enriched):
            self.create_product_row(index, *item)

    def summary_card(self, col, title, value, subtitle, color):
        card = ctk.CTkFrame(self.summary, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        card.grid(row=0, column=col, sticky="ew", padx=8, pady=12)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))
        ctk.CTkLabel(card, text=self.ar(title), font=("Arial", 12, "bold"), text_color=TEXT, anchor="e").grid(row=1, column=0, sticky="e", padx=12)
        ctk.CTkLabel(card, text=str(value), font=("Arial", 24, "bold"), text_color=color, anchor="e").grid(row=2, column=0, sticky="e", padx=12, pady=(6, 0))
        ctk.CTkLabel(card, text=self.ar(subtitle), font=("Arial", 10), text_color=MUTED, anchor="e").grid(row=3, column=0, sticky="e", padx=12, pady=(2, 12))

    def show_empty(self):
        empty = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        empty.grid(row=0, column=0, sticky="ew", padx=12, pady=14)
        ctk.CTkLabel(empty, text=self.ar("لا توجد منتجات مطابقة"), font=("Arial", 18, "bold"), text_color=MUTED).pack(pady=(28, 6))
        ctk.CTkLabel(empty, text=self.ar("غيّر الفلتر أو حدّث البيانات"), font=("Arial", 12), text_color=DIM).pack(pady=(0, 28))

    def create_product_row(self, index, product, key, label, color, days_left):
        row = ctk.CTkFrame(self.list_frame, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        row.grid(row=index, column=0, sticky="ew", padx=12, pady=8)
        row.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text=self.ar(product.get("name", "-")), font=("Arial", 17, "bold"), text_color=TEXT, anchor="e").grid(row=0, column=0, sticky="e")
        ctk.CTkLabel(
            top,
            text=self.ar(label),
            font=("Arial", 12, "bold"),
            text_color="#ffffff",
            fg_color=color,
            corner_radius=10,
            width=120,
            height=28,
        ).grid(row=0, column=1, sticky="e", padx=(10, 0))

        details = ctk.CTkFrame(row, fg_color="transparent")
        details.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        for col in range(5):
            details.grid_columnconfigure(col, weight=1)

        expiry = self.parse_date(product.get("expiry_date"))
        expiry_text = expiry.strftime("%Y-%m-%d") if expiry else "غير محدد"
        days_text = "غير محدد" if days_left is None else ("منتهي منذ " + str(abs(days_left)) + " يوم" if days_left < 0 else str(days_left) + " يوم")
        self.info_box(details, 0, "الصلاحية", expiry_text, color)
        self.info_box(details, 1, "المتبقي", days_text, color)
        self.info_box(details, 2, "الكمية", self.safe_int(product.get("quantity")), CYAN)
        self.info_box(details, 3, "التصنيف", product.get("category_name") or product.get("category") or "عام", BLUE)
        self.info_box(details, 4, "الشركة", product.get("company") or "غير محدد", PURPLE)

    def info_box(self, parent, col, label, value, color):
        box = ctk.CTkFrame(parent, fg_color=CARD_DARK, corner_radius=10)
        box.grid(row=0, column=col, sticky="ew", padx=5, pady=4)
        ctk.CTkLabel(box, text=self.ar(label), font=("Arial", 11), text_color=DIM, anchor="e").pack(anchor="e", padx=10, pady=(8, 2))
        ctk.CTkLabel(box, text=self.ar(value), font=("Arial", 13, "bold"), text_color=color, anchor="e").pack(anchor="e", padx=10, pady=(0, 8))

    def open_products_filter(self, product_filter):
        if self.navigation_callback:
            try:
                self.navigation_callback("products", product_filter=product_filter)
                return
            except Exception:
                pass
        messagebox.showinfo("المنتجات", "افتح شاشة المنتجات واستخدم فلاتر المخزون والصلاحية")

    def export_csv(self):
        if not self.visible_products:
            messagebox.showwarning("تصدير", "لا توجد بيانات للتصدير")
            return
        path = filedialog.asksaveasfilename(
            title="حفظ تقرير الصلاحية",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(["اسم المنتج", "التصنيف", "الشركة", "الكمية", "تاريخ الصلاحية", "الحالة", "الأيام المتبقية"])
                for product in self.visible_products:
                    key, label, _color, days_left = self.classify_product(product)
                    writer.writerow([
                        product.get("name", ""),
                        product.get("category_name") or product.get("category") or "",
                        product.get("company", ""),
                        product.get("quantity", 0),
                        product.get("expiry_date", ""),
                        label,
                        "" if days_left is None else days_left,
                    ])
            messagebox.showinfo("تصدير", "تم تصدير تقرير الصلاحية بنجاح")
        except Exception as exc:
            messagebox.showerror("تصدير", f"فشل التصدير: {exc}")
