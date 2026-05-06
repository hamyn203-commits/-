"""
Clean Dashboard tab for Makhzan El-Nada.

This file intentionally keeps the dashboard simple: short Arabic labels,
separate icon labels, no mixed icon/text strings, and no background timers.
"""

import customtkinter as ctk
from datetime import datetime, timedelta
from api_client import APIClient
from rtl_utils import rtl


BG = "#1e1e1e"
CARD = "#262b33"
CARD_DARK = "#1f242c"
GREEN = "#43a85b"
BLUE = "#2196F3"
ORANGE = "#d28a2d"
RED = "#d05b52"
CYAN = "#00BCD4"
PURPLE = "#9C27B0"
GRAY = "#9e9e9e"
WHITE = "#ffffff"


class DashboardTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, navigation_callback=None):
        super().__init__(master)

        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.navigation_callback = navigation_callback

        self.products = []
        self.pharmacies = []
        self.orders = []

        self.configure(fg_color=BG)
        self.create_ui()
        self.load_dashboard_data()

    def ar(self, text):
        text = "" if text is None else str(text)
        shaped = rtl(text)
        if shaped != text:
            return shaped
        if not any("\u0600" <= char <= "\u06ff" for char in text):
            return text
        parts = text.split(" ")
        if len(parts) <= 1:
            return text
        return " ".join(reversed(parts))

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(self.ar(message))
            except Exception:
                pass

    def check_server_health(self):
        try:
            if hasattr(self.api_client, "health_check"):
                return self.api_client.health_check()
            return True
        except Exception:
            return False

    def clear_dynamic_content(self):
        for widget in list(self.dynamic_frame.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass

    def format_money(self, value):
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "0.00"

    def safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def parse_date(self, date_value):
        if not date_value:
            return None
        try:
            if isinstance(date_value, datetime):
                return date_value.date()
            if isinstance(date_value, str):
                clean_date = date_value.strip().split(" ")[0].split("T")[0]
                return datetime.strptime(clean_date, "%Y-%m-%d").date()
        except Exception:
            return None
        return None

    def is_expired(self, expiry_date):
        parsed_date = self.parse_date(expiry_date)
        return bool(parsed_date and parsed_date < datetime.now().date())

    def is_expiring_soon(self, expiry_date):
        parsed_date = self.parse_date(expiry_date)
        if not parsed_date:
            return False
        today = datetime.now().date()
        return today <= parsed_date <= today + timedelta(days=30)

    def translate_status(self, status):
        status_map = {
            "pending": self.ar("جديد"),
            "approved": self.ar("معتمد"),
            "rejected": self.ar("مرفوض"),
        }
        return status_map.get(str(status).lower(), str(status or "-"))

    def get_order_total(self, order):
        total = order.get("total", order.get("total_amount", order.get("total_price", 0)))
        return self.safe_float(total)

    def get_order_date(self, order):
        date_value = order.get("order_date", order.get("created_at", order.get("date", "-")))
        if isinstance(date_value, str) and len(date_value) >= 16:
            return date_value[:16].replace("T", " ")
        if hasattr(date_value, "strftime"):
            return date_value.strftime("%Y-%m-%d %H:%M")
        return date_value or "-"

    def get_pharmacy_name(self, order):
        pharmacy_name = (
            order.get("pharmacy_name")
            or order.get("customer_name")
            or order.get("client_name")
            or "-"
        )
        if pharmacy_name == "-" and isinstance(order.get("pharmacy"), dict):
            pharmacy_name = order["pharmacy"].get("name", "-")
        return pharmacy_name

    def navigate_to(self, tab_name):
        if self.navigation_callback:
            self.navigation_callback(tab_name)

    def navigate_to_product_filter(self, filter_name):
        if self.navigation_callback:
            self.navigation_callback("products", filter_name)

    def bind_click_recursive(self, widget, command):
        widget.bind("<Button-1>", lambda _event: command())
        try:
            widget.configure(cursor="hand2")
        except Exception:
            pass
        for child in widget.winfo_children():
            self.bind_click_recursive(child, command)

    def create_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=BG)
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        self.scroll.grid_columnconfigure(0, weight=1)

        self.create_header()

        self.dynamic_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.dynamic_frame.grid(row=1, column=0, sticky="ew")
        self.dynamic_frame.grid_columnconfigure(0, weight=1)

    def create_header(self):
        header = ctk.CTkFrame(self.scroll, fg_color="#272d36", corner_radius=16, border_width=1, border_color="#313a46")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)
        header.configure(height=156)

        ctk.CTkFrame(header, fg_color="#313846", height=6, corner_radius=16).pack(fill="x", padx=14, pady=(10, 0))

        title_area = ctk.CTkFrame(header, fg_color="transparent")
        title_area.grid(row=0, column=0, sticky="nsew", padx=36, pady=28)
        title_area.grid_columnconfigure(0, weight=1)

        text_area = ctk.CTkFrame(title_area, fg_color="transparent")
        text_area.grid(row=0, column=0, sticky="e", padx=(0, 28))

        ctk.CTkLabel(
            text_area,
            text=self.ar("مرحبًا بك في"),
            font=ctk.CTkFont(size=14),
            text_color=GRAY,
            anchor="e",
            justify="right",
        ).pack(anchor="e")

        ctk.CTkLabel(
            text_area,
            text=self.ar("مخزن الندا"),
            font=ctk.CTkFont(size=34, weight="bold"),
            text_color=GREEN,
            anchor="e",
            justify="right",
        ).pack(anchor="e")

        ctk.CTkLabel(
            text_area,
            text=self.ar("لوحة تحكم إدارة المخزن"),
            font=ctk.CTkFont(size=15),
            text_color=GRAY,
            anchor="e",
            justify="right",
        ).pack(anchor="e", pady=(5, 0))

        controls_area = ctk.CTkFrame(title_area, fg_color="transparent")
        controls_area.grid(row=0, column=1, sticky="e")

        buttons_row = ctk.CTkFrame(controls_area, fg_color="transparent")
        buttons_row.pack(anchor="e", pady=(6, 18))

        ctk.CTkButton(
            buttons_row,
            text=self.ar("تحديث"),
            command=self.refresh_dashboard,
            height=38,
            width=110,
            corner_radius=14,
            fg_color="#b57a2f",
            hover_color="#a56d28",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right", padx=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text=self.ar("تصدير التقرير"),
            command=lambda: self.update_status("استخدم شاشة التقارير للتصدير"),
            height=38,
            width=140,
            corner_radius=14,
            fg_color="#3f8d56",
            hover_color="#377c4b",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right", padx=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text=self.ar("تحديث تلقائي"),
            command=lambda: self.update_status("التحديث التلقائي غير مفعل"),
            height=38,
            width=140,
            corner_radius=14,
            fg_color=BLUE,
            hover_color="#1976D2",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="right")

        time_row = ctk.CTkFrame(controls_area, fg_color="transparent")
        time_row.pack(anchor="center")

        self.last_update_value = ctk.CTkLabel(
            time_row,
            text="--:--:--",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=WHITE,
        )
        self.last_update_value.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            time_row,
            text=self.ar("آخر تحديث"),
            font=ctk.CTkFont(size=12),
            text_color=GRAY,
            anchor="e",
            justify="right",
        ).pack(side="left")

    def create_stat_card(self, parent, icon, title, value, subtitle, color, tab_name=None):
        card = ctk.CTkFrame(parent, fg_color="#2a313c", corner_radius=16, border_width=1, border_color="#394252", height=162)
        card.grid_propagate(False)
        ctk.CTkFrame(card, fg_color=color, height=6, corner_radius=16).pack(fill="x", padx=10, pady=(10, 0))

        if tab_name:
            card.bind("<Button-1>", lambda _event: self.navigate_to(tab_name))

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=14)
        if tab_name:
            content.bind("<Button-1>", lambda _event: self.navigate_to(tab_name))

        top = ctk.CTkFrame(content, fg_color="transparent")
        top.pack(fill="x")

        icon_label = ctk.CTkLabel(top, text=icon, font=ctk.CTkFont(size=32), text_color=color)
        icon_label.pack(side="right")

        title_label = ctk.CTkLabel(
            top,
            text=self.ar(title),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=WHITE,
            anchor="e",
            justify="right",
        )
        title_label.pack(side="right", padx=(0, 10))

        value_label = ctk.CTkLabel(
            content,
            text=str(value),
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=WHITE,
            anchor="e",
        )
        value_label.pack(anchor="e", pady=(14, 4))

        subtitle_label = ctk.CTkLabel(
            content,
            text=self.ar(subtitle),
            font=ctk.CTkFont(size=12),
            text_color=WHITE,
            anchor="e",
            justify="right",
        )
        subtitle_label.pack(anchor="e")

        for child in (icon_label, title_label, value_label, subtitle_label):
            if tab_name:
                child.bind("<Button-1>", lambda _event: self.navigate_to(tab_name))

        return card

    def create_small_stat_card(self, parent, title, value, subtitle, color, column, product_filter=None):
        card = ctk.CTkFrame(parent, fg_color="#252c36", corner_radius=16, border_width=1, border_color="#323c4a", height=152)
        card.grid(row=0, column=column, sticky="ew", padx=8)
        card.grid_propagate(False)

        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=14, pady=(12, 18))

        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=WHITE,
            anchor="e",
            justify="right",
        ).pack(anchor="e", padx=14)

        display_color = color if str(value) != "0" else "#6f7a89"
        ctk.CTkLabel(
            card,
            text=str(value),
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=display_color,
            anchor="e",
        ).pack(anchor="e", padx=14, pady=(12, 2))

        ctk.CTkLabel(
            card,
            text=self.ar(subtitle),
            font=ctk.CTkFont(size=11),
            text_color=GRAY,
            anchor="e",
            justify="right",
        ).pack(anchor="e", padx=14)

        if product_filter:
            self.bind_click_recursive(card, lambda: self.navigate_to_product_filter(product_filter))

        return card

    def create_section_card(self, title, color, parent=None, row=None, column=None):
        parent = parent or self.dynamic_frame
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16, border_width=1, border_color="#323a46")
        if row is None:
            card.pack(fill="x", pady=12)
        else:
            card.grid(row=row, column=column, sticky="nsew", padx=10, pady=12)
            parent.grid_rowconfigure(row, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=self.ar(title),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=color,
            anchor="e",
            justify="right",
        ).pack(side="right")

        ctk.CTkFrame(card, height=2, fg_color=CARD_DARK).pack(fill="x", padx=18, pady=(0, 10))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(0, 16))
        return body

    def create_simple_row(self, parent, cells, color=WHITE):
        row = ctk.CTkFrame(parent, fg_color=CARD_DARK, corner_radius=8)
        row.pack(fill="x", pady=4)

        for cell in cells:
            ctk.CTkLabel(
                row,
                text=self.ar(cell),
                font=ctk.CTkFont(size=12),
                text_color=color,
                anchor="e",
                justify="right",
            ).pack(side="right", fill="x", expand=True, padx=10, pady=9)

        return row

    def create_empty_row(self, parent, text):
        row = ctk.CTkFrame(parent, fg_color="#263a2c", corner_radius=8)
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(
            row,
            text=self.ar(text),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=GREEN,
            anchor="e",
            justify="right",
        ).pack(anchor="e", padx=12, pady=10)

    def load_dashboard_data(self):
        self.clear_dynamic_content()

        if not self.check_server_health():
            self.show_offline_state()
            return

        try:
            self.products = self.api_client.get_products() or []
            self.pharmacies = self.api_client.get_pharmacies() or []
            self.orders = self.api_client.get_orders() or []
            self.render_dashboard()
            self.last_update_value.configure(text=datetime.now().strftime("%H:%M:%S"))
            self.update_status("تم تحديث لوحة التحكم")
        except Exception as exc:
            self.show_error_state(str(exc))

    def render_dashboard(self):
        total_products = len(self.products)
        total_pharmacies = len(self.pharmacies)
        pending_orders = sum(1 for order in self.orders if order.get("status") == "pending")
        total_debt = sum(self.safe_float(pharmacy.get("balance", 0)) for pharmacy in self.pharmacies)

        out_of_stock = sum(1 for product in self.products if self.safe_int(product.get("quantity", 0)) == 0)
        low_stock = sum(1 for product in self.products if 1 <= self.safe_int(product.get("quantity", 0)) <= 5)
        expired = sum(1 for product in self.products if self.is_expired(product.get("expiry_date")))
        expiring = sum(1 for product in self.products if self.is_expiring_soon(product.get("expiry_date")))

        stats = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        stats.pack(fill="x", padx=10, pady=(0, 30))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        cards = [
            self.create_stat_card(stats, "📦", "المنتجات", total_products, "إجمالي الأصناف", GREEN, "products"),
            self.create_stat_card(stats, "🏥", "الصيدليات", total_pharmacies, "عملاء مسجلون", BLUE, "pharmacies"),
            self.create_stat_card(stats, "📋", "الطلبات الجديدة", pending_orders, "قيد الانتظار", ORANGE, "orders"),
            self.create_stat_card(stats, "💰", "المديونيات", self.format_money(total_debt), "أرصدة مستحقة", RED, "payments"),
        ]

        for column, card in enumerate(cards):
            card.grid(row=0, column=column, sticky="ew", padx=10)

        risks = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        risks.pack(fill="x", padx=10, pady=(0, 30))
        risks.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.create_small_stat_card(risks, "نافد", out_of_stock, "لا توجد كمية", RED, 0, "out_of_stock")
        self.create_small_stat_card(risks, "مخزون منخفض", low_stock, "من 1 إلى 5", ORANGE, 1, "low_stock")
        self.create_small_stat_card(risks, "منتهي الصلاحية", expired, "انتهى التاريخ", PURPLE, 2, "expired")
        self.create_small_stat_card(risks, "قرب الانتهاء", expiring, "خلال 30 يوم", CYAN, 3, "expiring_soon")

        grid = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
        grid.pack(fill="x", padx=10)
        grid.grid_columnconfigure((0, 1), weight=1)

        self.render_alerts_preview(grid, 0, 0)
        self.render_recent_orders_preview(grid, 0, 1)
        self.render_debts_preview(grid, 1, 0)

    def render_alerts_preview(self, parent=None, row=None, column=None):
        body = self.create_section_card("تنبيهات المخزون", ORANGE, parent, row, column)
        alerts = []

        for product in self.products:
            quantity = self.safe_int(product.get("quantity", 0))
            name = product.get("name", "منتج")
            if quantity == 0:
                alerts.append([name, "نافد", "0"])
            elif 1 <= quantity <= 5:
                alerts.append([name, "مخزون منخفض", str(quantity)])

        if not alerts:
            self.create_empty_row(body, "لا توجد تنبيهات")
            return

        for item in alerts[:5]:
            self.create_simple_row(body, item, WHITE)

    def render_recent_orders_preview(self, parent=None, row=None, column=None):
        body = self.create_section_card("آخر الطلبات", BLUE, parent, row, column)
        recent_orders = sorted(self.orders, key=lambda order: order.get("id", 0), reverse=True)[:5]

        if not recent_orders:
            self.create_empty_row(body, "لا توجد طلبات")
            return

        for order in recent_orders:
            order_number = order.get("order_number", order.get("id", "-"))
            pharmacy = self.get_pharmacy_name(order)
            total = self.format_money(self.get_order_total(order))
            status = self.translate_status(order.get("status"))
            self.create_simple_row(body, [str(order_number), pharmacy, total, status], WHITE)

    def render_debts_preview(self, parent=None, row=None, column=None):
        body = self.create_section_card("أعلى المديونيات", RED, parent, row, column)
        debt_pharmacies = sorted(
            [pharmacy for pharmacy in self.pharmacies if self.safe_float(pharmacy.get("balance", 0)) > 0],
            key=lambda pharmacy: self.safe_float(pharmacy.get("balance", 0)),
            reverse=True,
        )[:5]

        if not debt_pharmacies:
            self.create_empty_row(body, "لا توجد مديونيات")
            return

        for pharmacy in debt_pharmacies:
            name = pharmacy.get("name", "صيدلية")
            balance = self.format_money(pharmacy.get("balance", 0))
            self.create_simple_row(body, [name, balance], WHITE)

    def refresh_dashboard(self):
        self.update_status("جاري تحديث لوحة التحكم")
        self.load_dashboard_data()

    def show_offline_state(self):
        self.update_status("السيرفر غير متصل")
        body = self.create_section_card("السيرفر غير متصل", RED)
        self.create_simple_row(body, ["شغّل السيرفر أولًا"], RED)

    def show_error_state(self, message):
        self.update_status("خطأ في تحميل لوحة التحكم")
        body = self.create_section_card("حدث خطأ", RED)
        self.create_simple_row(body, [message], RED)
