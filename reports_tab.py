import csv
import os
import json
import smtplib
import tempfile
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox
from email.message import EmailMessage

import customtkinter as ctk

from api_client import APIClient
from rtl_utils import rtl


class ReportsTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, navigation_callback=None):
        super().__init__(master)

        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.navigation_callback = navigation_callback

        self.products = []
        self.orders = []
        self.pharmacies = []

        self.current_report_name = "تقرير المنتجات"
        self.current_headers = []
        self.current_rows = []

        self.configure(fg_color="#1e1e1e")
        self.create_ui()
        self.load_data()

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

    def clear_content(self):
        for widget in list(self.content_frame.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass

    def clear_report_table(self):
        for widget in list(self.table_frame.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass

    def format_money(self, value):
        try:
            return f"{float(value):,.2f} جنيه"
        except (TypeError, ValueError):
            return "0.00 جنيه"

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
            "pending": "جديد",
            "approved": "تم الاعتماد",
            "rejected": "مرفوض",
            "reviewed": "تمت المراجعة",
            "in_store": "في المخزن",
            "with_driver": "مع المندوب",
            "on_the_way": "في الطريق إليك",
            "delivered": "تم التسليم",
            "postponed": "مؤجل",
            "cancelled": "ملغي",
            "completed": "تم التسليم",
        }
        return status_map.get(str(status).lower(), status or "-")

    def translate_payment_status(self, status):
        status_map = {
            "unpaid": "لم يدفع",
            "cash": "دفع كاش",
            "partial": "دفع جزء",
            "full": "دفع كامل",
            "deferred": "أجل",
            "collect_on_delivery": "تحصيل عند الاستلام",
        }
        return status_map.get(str(status or "unpaid").lower(), status or "لم يدفع")

    def is_sales_order(self, order):
        return str(order.get("status", "")).lower() in {
            "approved", "reviewed", "completed", "delivered", "in_store", "with_driver", "on_the_way"
        }

    def get_order_items(self, order):
        items = order.get("items", order.get("order_items", []))
        return items if isinstance(items, list) else []

    def get_item_name(self, item):
        if not isinstance(item, dict):
            return "-"
        if item.get("product_name") or item.get("name"):
            return item.get("product_name") or item.get("name")
        product = item.get("product")
        if isinstance(product, dict):
            return product.get("name", "-")
        return "-"

    def get_item_quantity(self, item):
        return self.safe_int(item.get("quantity", 0)) if isinstance(item, dict) else 0

    def get_item_price(self, item):
        if not isinstance(item, dict):
            return 0.0
        return self.safe_float(item.get("price", item.get("unit_price", 0)))

    def get_item_total(self, item):
        if not isinstance(item, dict):
            return 0.0
        total = item.get("total", item.get("total_price"))
        if total is not None:
            return self.safe_float(total)
        return self.get_item_quantity(item) * self.get_item_price(item)

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

    def get_product_price(self, product):
        price = product.get("price")
        if price is not None:
            return self.safe_float(price)
        return self.safe_float(product.get("unit_price", 0))

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
            text="📊",
            font=ctk.CTkFont(size=30),
            text_color="#4CAF50"
        ).pack(side="right", padx=(10, 0))

        title_area = ctk.CTkFrame(header_content, fg_color="transparent")
        title_area.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            title_area,
            text=self.ar("التقارير"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).pack(anchor="e")

        ctk.CTkLabel(
            title_area,
            text=self.ar("راجع أداء المخزن والطلبات والمديونيات من مكان واحد"),
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).pack(anchor="e", pady=(4, 0))

        ctk.CTkButton(
            header_content,
            text=self.ar("تحديث البيانات"),
            height=38,
            width=150,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.refresh_data
        ).pack(side="left")

        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)

    def create_summary_card(self, parent, title, value, subtitle, color, column, target=None, product_filter=None):
        card = ctk.CTkFrame(parent, fg_color="#2d2d2d", corner_radius=12, height=150, border_width=1, border_color="#3a3a3a")
        card.grid(row=0, column=column, sticky="ew", padx=6, pady=6)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        accent = ctk.CTkFrame(card, fg_color=color, width=5, corner_radius=5)
        accent.grid(row=0, column=1, rowspan=3, sticky="ns", padx=(0, 8), pady=14)

        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
            anchor="e",
            justify="right"
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 0))

        ctk.CTkLabel(
            card,
            text=str(value),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=color,
            anchor="e"
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 0))

        ctk.CTkLabel(
            card,
            text=self.ar(subtitle),
            font=ctk.CTkFont(size=12),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 16))

        if target:
            self.make_clickable(card, lambda _event=None: self.navigate(target, product_filter=product_filter))
            card.configure(cursor="hand2")

    def make_clickable(self, widget, callback):
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            child.bind("<Button-1>", callback)
            try:
                child.configure(cursor="hand2")
            except Exception:
                pass

    def navigate(self, tab_name, product_filter=None):
        if not self.navigation_callback:
            return
        try:
            self.navigation_callback(tab_name, product_filter=product_filter)
        except TypeError:
            self.navigation_callback(tab_name)

    def create_report_selector(self):
        selector_card = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        selector_card.pack(fill="x", pady=10)
        selector_card.grid_columnconfigure(0, weight=1)

        row = ctk.CTkFrame(selector_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=16)

        ctk.CTkButton(
            row,
            text=self.ar("تصدير التقرير"),
            height=38,
            width=140,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.export_current_report
        ).pack(side="left")
        
        ctk.CTkButton(
            row,
            text=self.ar("إرسال التقرير"),
            height=38,
            width=130,
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.show_send_report_dialog
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            row,
            text=self.ar("تصدير PDF"),
            height=38,
            width=120,
            fg_color="#607D8B",
            hover_color="#455A64",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.export_current_report_pdf
        ).pack(side="left", padx=(8, 0))

        self.report_menu = ctk.CTkOptionMenu(
            row,
            values=[
                "تقرير المنتجات",
                "تقرير المخزون",
                "تقرير الطلبات",
                "تقرير مبيعات مفصل",
                "تقرير المديونيات",
                "تقرير الصلاحية",
                "تقرير أفضل الصيدليات",
                "تقرير أفضل المنتجات",
                "تقرير المبيعات حسب الحالة",
                "أكثر المنتجات مبيعاً",
                "الرسم البياني للمبيعات",
            ],
            command=self.show_report,
            width=210,
            height=38,
            fg_color="#1e1e1e",
            button_color="#2196F3",
            button_hover_color="#1976D2",
            font=ctk.CTkFont(size=13)
        )
        self.report_menu.set(self.current_report_name)
        self.report_menu.pack(side="right")

        ctk.CTkLabel(
            row,
            text=self.ar("اختر نوع التقرير:"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#dcdcdc",
            anchor="e",
            justify="right"
        ).pack(side="right", padx=(0, 12))

    def load_data(self):
        self.clear_content()

        if not self.check_server_health():
            self.show_offline_state()
            return

        try:
            self.products = self.api_client.get_products() or []
            self.orders = self.api_client.get_orders() or []
            self.pharmacies = self.api_client.get_pharmacies() or []
        except Exception as exc:
            self.update_status(f"فشل تحميل بيانات التقارير: {exc}")
            self.show_offline_state()
            return

        self.render_dashboard()
        self.show_report(self.current_report_name)
        self.update_status("تم تحديث بيانات التقارير بنجاح")

    def refresh_data(self):
        self.update_status("جاري تحديث بيانات التقارير...")
        self.load_data()

    def render_dashboard(self):
        total_debt = sum(self.safe_float(pharmacy.get("balance", 0)) for pharmacy in self.pharmacies)
        pending_orders = sum(1 for order in self.orders if str(order.get("status", "")).lower() == "pending")
        out_of_stock = sum(1 for product in self.products if self.safe_int(product.get("quantity", 0)) == 0)

        self.create_section_title("الملخص العام")
        summary = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        summary.pack(fill="x", pady=(0, 10))
        summary.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_summary_card(summary, "إجمالي المنتجات", len(self.products), "كل الأصناف المسجلة", "#4CAF50", 0, "products")
        self.create_summary_card(summary, "إجمالي الصيدليات", len(self.pharmacies), "عملاء مسجلون", "#2196F3", 1, "pharmacies")
        self.create_summary_card(summary, "إجمالي الطلبات", len(self.orders), "كل الطلبات", "#FF9800", 2, "orders")

        summary2 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        summary2.pack(fill="x", pady=(0, 10))
        summary2.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_summary_card(summary2, "إجمالي المديونيات", self.format_money(total_debt), "أرصدة مستحقة", "#f44336", 0, "payments")
        self.create_summary_card(summary2, "الطلبات الجديدة", pending_orders, "قيد الانتظار", "#9C27B0", 1, "orders")
        self.create_summary_card(summary2, "المنتجات النافدة", out_of_stock, "تحتاج توريد", "#607D8B", 2, "products", "out_of_stock")

        self.render_analytics_section()
        self.create_section_title("التقارير المفصلة")
        self.create_report_selector()

        table_card = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        table_card.pack(fill="both", expand=True, pady=10)

        self.table_title = ctk.CTkLabel(
            table_card,
            text=self.current_report_name,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        )
        self.table_title.pack(anchor="e", padx=16, pady=(16, 8))

        self.table_frame = ctk.CTkScrollableFrame(table_card, fg_color="transparent", height=360)
        self.table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def create_section_title(self, title):
        ctk.CTkLabel(
            self.content_frame,
            text=self.ar(title),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff",
            anchor="e",
            justify="right"
        ).pack(anchor="e", fill="x", pady=(10, 6))

    def calculate_analytics(self):
        pharmacy_orders = {}
        pharmacy_values = {}
        product_quantity = {}
        product_values = {}
        status_counts = {}
        payment_counts = {}
        unpaid_total = 0.0
        paid_total = 0.0
        low_stock = 0
        expired = 0
        expiring_soon = 0

        for order in self.orders:
            pharmacy = self.get_pharmacy_name(order)
            total = self.get_order_total(order)
            pharmacy_orders[pharmacy] = pharmacy_orders.get(pharmacy, 0) + 1
            pharmacy_values[pharmacy] = pharmacy_values.get(pharmacy, 0.0) + total
            status_text = self.translate_status(order.get("status", "-"))
            status_counts[status_text] = status_counts.get(status_text, 0) + 1
            payment_text = self.translate_payment_status(order.get("payment_status", "unpaid"))
            payment_counts[payment_text] = payment_counts.get(payment_text, 0) + 1
            paid_total += self.safe_float(order.get("amount_paid", 0))
            remaining = order.get("remaining_amount")
            if remaining is None:
                remaining = max(total - self.safe_float(order.get("amount_paid", 0)), 0.0)
            unpaid_total += self.safe_float(remaining)
            for item in self.get_order_items(order):
                name = self.get_item_name(item)
                quantity = self.get_item_quantity(item)
                value = self.get_item_total(item)
                product_quantity[name] = product_quantity.get(name, 0) + quantity
                product_values[name] = product_values.get(name, 0.0) + value

        for product in self.products:
            quantity = self.safe_int(product.get("quantity", 0))
            if quantity == 0:
                pass
            elif quantity <= 5:
                low_stock += 1
            if self.is_expired(product.get("expiry_date")):
                expired += 1
            elif self.is_expiring_soon(product.get("expiry_date")):
                expiring_soon += 1

        return {
            "top_pharmacy_orders": max(pharmacy_orders.items(), key=lambda x: x[1], default=("-", 0)),
            "top_pharmacy_value": max(pharmacy_values.items(), key=lambda x: x[1], default=("-", 0.0)),
            "top_product_quantity": max(product_quantity.items(), key=lambda x: x[1], default=("-", 0)),
            "top_product_value": max(product_values.items(), key=lambda x: x[1], default=("-", 0.0)),
            "pharmacy_orders": pharmacy_orders,
            "pharmacy_values": pharmacy_values,
            "product_quantity": product_quantity,
            "product_values": product_values,
            "status_counts": status_counts,
            "payment_counts": payment_counts,
            "paid_total": paid_total,
            "unpaid_total": unpaid_total,
            "low_stock": low_stock,
            "expired": expired,
            "expiring_soon": expiring_soon,
            "least_moving_product": min(product_quantity.items(), key=lambda x: x[1], default=("-", 0)),
        }

    def render_analytics_section(self):
        self.create_section_title("التحليلات")
        analytics = self.calculate_analytics()
        wrap = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        wrap.pack(fill="x", pady=(0, 10))
        wrap.grid_columnconfigure((0, 1, 2, 3), weight=1)

        cards = [
            ("أعلى صيدلية بالطلبات", analytics["top_pharmacy_orders"][0], f"{analytics['top_pharmacy_orders'][1]} طلب", "#2196F3"),
            ("أعلى صيدلية بالقيمة", analytics["top_pharmacy_value"][0], self.format_money(analytics["top_pharmacy_value"][1]), "#4CAF50"),
            ("أعلى منتج بالكمية", analytics["top_product_quantity"][0], f"{analytics['top_product_quantity'][1]} وحدة", "#FF9800"),
            ("أعلى منتج بالقيمة", analytics["top_product_value"][0], self.format_money(analytics["top_product_value"][1]), "#9C27B0"),
        ]

        for col, (title, value, subtitle, color) in enumerate(cards):
            card = ctk.CTkFrame(wrap, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
            card.grid(row=0, column=col, sticky="ew", padx=8, pady=(12, 8))
            ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 6))
            ctk.CTkLabel(card, text=self.ar(title), font=ctk.CTkFont(size=12, weight="bold"), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", padx=12)
            ctk.CTkLabel(card, text=self.ar(value), font=ctk.CTkFont(size=15, weight="bold"), text_color="#ffffff", anchor="e", justify="right", wraplength=180).pack(fill="x", padx=12, pady=(5, 0))
            ctk.CTkLabel(card, text=self.ar(subtitle), font=ctk.CTkFont(size=12), text_color=color, anchor="e", justify="right").pack(fill="x", padx=12, pady=(4, 12))

        deep = ctk.CTkFrame(wrap, fg_color="transparent")
        deep.grid(row=1, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 12))
        deep.grid_columnconfigure((0, 1, 2), weight=1)

        self.create_analysis_panel(
            deep,
            "تحليل السداد",
            [
                ("إجمالي المدفوع", self.format_money(analytics["paid_total"])),
                ("إجمالي المتبقي", self.format_money(analytics["unpaid_total"])),
                ("حالات الدفع", " | ".join(f"{k}: {v}" for k, v in analytics["payment_counts"].items()) or "-"),
            ],
            "#4CAF50",
            0,
        )
        self.create_analysis_panel(
            deep,
            "تحليل الطلبات",
            [
                ("حالات الطلبات", " | ".join(f"{k}: {v}" for k, v in analytics["status_counts"].items()) or "-"),
                ("أقل منتج حركة", f"{analytics['least_moving_product'][0]} ({analytics['least_moving_product'][1]})"),
                ("عدد الطلبات", len(self.orders)),
            ],
            "#2196F3",
            1,
        )
        self.create_analysis_panel(
            deep,
            "مؤشرات المخزون",
            [
                ("مخزون منخفض", analytics["low_stock"]),
                ("منتهي الصلاحية", analytics["expired"]),
                ("قرب انتهاء الصلاحية", analytics["expiring_soon"]),
            ],
            "#FF9800",
            2,
        )

    def create_analysis_panel(self, parent, title, rows, color, column):
        panel = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
        panel.grid(row=0, column=column, sticky="nsew", padx=6, pady=4)
        ctk.CTkFrame(panel, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 8))
        ctk.CTkLabel(panel, text=self.ar(title), font=ctk.CTkFont(size=14, weight="bold"), text_color=color, anchor="e", justify="right").pack(fill="x", padx=12)
        for label, value in rows:
            ctk.CTkLabel(
                panel,
                text=self.ar(f"{label}: {value}"),
                font=ctk.CTkFont(size=12),
                text_color="#dcdcdc",
                anchor="e",
                justify="right",
                wraplength=260,
            ).pack(fill="x", padx=12, pady=(5, 0))
        ctk.CTkLabel(panel, text="", height=6).pack()

    def show_report(self, report_name):
        self.current_report_name = report_name

        builders = {
            "تقرير المنتجات": self.build_products_report,
            "تقرير المخزون": self.build_stock_report,
            "تقرير الطلبات": self.build_orders_report,
            "تقرير مبيعات مفصل": self.build_detailed_sales_report,
            "تقرير المديونيات": self.build_debts_report,
            "تقرير الصلاحية": self.build_expiry_report,
            "تقرير أفضل الصيدليات": self.build_top_pharmacies_report,
            "تقرير أفضل المنتجات": self.build_best_products_report,
            "تقرير المبيعات حسب الحالة": self.build_sales_by_status_report,
            "أكثر المنتجات مبيعاً": self.build_top_products_report,
            "الرسم البياني للمبيعات": self.build_monthly_sales_report,
        }

        builder = builders.get(report_name, self.build_products_report)
        headers, rows = builder()
        self.current_headers = headers
        self.current_rows = rows

        if hasattr(self, "table_title"):
            self.table_title.configure(text=report_name)
        if report_name == "تقرير مبيعات مفصل":
            self.clear_report_table()
            self.render_sales_summary(rows)
            self.render_table(headers, rows, clear=False)
        else:
            self.render_table(headers, rows)
        if report_name == "الرسم البياني للمبيعات":
            self.render_sales_chart(rows)
        elif report_name == "أكثر المنتجات مبيعاً":
            self.render_top_products_chart(rows)

    def build_products_report(self):
        headers = ["ID", "اسم المنتج", "الكمية", "السعر", "التصنيف", "الشركة", "تاريخ الصلاحية"]
        rows = []
        for product in self.products:
            rows.append([
                product.get("id", "-"),
                product.get("name", "-"),
                self.safe_int(product.get("quantity", 0)),
                self.format_money(self.get_product_price(product)),
                product.get("category", "-") or "-",
                product.get("company", "-") or "-",
                product.get("expiry_date", "-") or "-",
            ])
        return headers, rows

    def build_stock_report(self):
        headers = ["اسم المنتج", "الكمية", "حالة المخزون"]
        rows = []
        for product in self.products:
            quantity = self.safe_int(product.get("quantity", 0))
            if quantity == 0:
                status = "نافد"
            elif 1 <= quantity <= 5:
                status = "منخفض"
            else:
                status = "جيد"
            rows.append([product.get("name", "-"), quantity, status])
        return headers, rows

    def build_orders_report(self):
        headers = ["رقم الطلب", "الصيدلية", "الإجمالي", "حالة الطلب", "حالة الدفع", "التاريخ"]
        rows = []
        for order in self.orders:
            rows.append([
                order.get("order_number", order.get("id", "-")),
                self.get_pharmacy_name(order),
                self.format_money(self.get_order_total(order)),
                self.translate_status(order.get("status", "-")),
                self.translate_payment_status(order.get("payment_status", "unpaid")),
                self.get_order_date(order),
            ])
        return headers, rows

    def build_detailed_sales_report(self):
        headers = ["رقم الطلب", "الصيدلية", "عدد المنتجات", "إجمالي الطلب", "حالة الطلب", "التاريخ", "أبرز منتج", "طريقة الدفع", "حالة الدفع"]
        rows = []
        for order in self.orders:
            items = self.get_order_items(order)
            top_item = "-"
            if items:
                top_item_obj = max(items, key=lambda item: self.get_item_total(item), default={})
                top_item = self.get_item_name(top_item_obj)
            rows.append([
                order.get("order_number", order.get("id", "-")),
                self.get_pharmacy_name(order),
                sum(self.get_item_quantity(item) for item in items),
                self.format_money(self.get_order_total(order)),
                self.translate_status(order.get("status", "-")),
                self.get_order_date(order),
                top_item,
                self.translate_payment_status(order.get("payment_type", "")) if order.get("payment_type") else "-",
                self.translate_payment_status(order.get("payment_status", "unpaid")),
            ])
        return headers, rows

    def build_debts_report(self):
        headers = ["اسم الصيدلية", "الهاتف", "الرصيد"]
        debt_pharmacies = sorted(
            [pharmacy for pharmacy in self.pharmacies if self.safe_float(pharmacy.get("balance", 0)) > 0],
            key=lambda pharmacy: self.safe_float(pharmacy.get("balance", 0)),
            reverse=True
        )
        rows = []
        for pharmacy in debt_pharmacies:
            rows.append([
                pharmacy.get("name", "-"),
                pharmacy.get("phone", "-") or "-",
                self.format_money(pharmacy.get("balance", 0)),
            ])
        return headers, rows

    def build_expiry_report(self):
        headers = ["اسم المنتج", "تاريخ الصلاحية", "حالة الصلاحية"]
        rows = []
        for product in self.products:
            expiry_date = product.get("expiry_date")
            parsed_date = self.parse_date(expiry_date)
            if not parsed_date:
                status = "غير محدد"
                display_date = expiry_date or "-"
            elif self.is_expired(expiry_date):
                status = "منتهي الصلاحية"
                display_date = str(parsed_date)
            elif self.is_expiring_soon(expiry_date):
                status = "قرب انتهاء الصلاحية"
                display_date = str(parsed_date)
            else:
                status = "صالحة"
                display_date = str(parsed_date)
            rows.append([product.get("name", "-"), display_date, status])
        return headers, rows

    def build_top_products_report(self):
        headers = ["اسم المنتج", "عدد الطلبات", "إجمالي الكمية", "إجمالي المبيعات"]
        stats = {}
        for order in self.orders:
            if not self.is_sales_order(order):
                continue
            seen_products = set()
            for item in order.get("items", order.get("order_items", [])):
                name = item.get("product_name") or item.get("name") or "-"
                quantity = self.safe_int(item.get("quantity", 0))
                price = self.safe_float(item.get("price", item.get("unit_price", 0)))
                if name not in stats:
                    stats[name] = {"orders": 0, "quantity": 0, "sales": 0.0}
                if name not in seen_products:
                    stats[name]["orders"] += 1
                    seen_products.add(name)
                stats[name]["quantity"] += quantity
                stats[name]["sales"] += quantity * price
        rows = []
        for name, data in sorted(stats.items(), key=lambda item: item[1]["quantity"], reverse=True):
            rows.append([name, data["orders"], data["quantity"], self.format_money(data["sales"])])
        return headers, rows

    def build_top_pharmacies_report(self):
        headers = ["الصيدلية", "عدد الطلبات", "إجمالي الشراء"]
        analytics = self.calculate_analytics()
        rows = []
        for name, count in sorted(analytics["pharmacy_orders"].items(), key=lambda item: item[1], reverse=True):
            rows.append([name, count, self.format_money(analytics["pharmacy_values"].get(name, 0.0))])
        return headers, rows

    def build_best_products_report(self):
        headers = ["المنتج", "إجمالي الكمية", "إجمالي القيمة"]
        analytics = self.calculate_analytics()
        rows = []
        for name, quantity in sorted(analytics["product_quantity"].items(), key=lambda item: item[1], reverse=True):
            rows.append([name, quantity, self.format_money(analytics["product_values"].get(name, 0.0))])
        return headers, rows

    def build_sales_by_status_report(self):
        headers = ["الحالة", "عدد الطلبات", "إجمالي القيمة"]
        stats = {}
        for order in self.orders:
            status = self.translate_status(order.get("status", "-"))
            if status not in stats:
                stats[status] = {"count": 0, "value": 0.0}
            stats[status]["count"] += 1
            stats[status]["value"] += self.get_order_total(order)
        rows = [[status, data["count"], self.format_money(data["value"])] for status, data in stats.items()]
        return headers, rows

    def build_monthly_sales_report(self):
        headers = ["الشهر", "إجمالي المبيعات", "عدد الطلبات"]
        monthly = {}
        for order in self.orders:
            if not self.is_sales_order(order):
                continue
            date_value = self.get_order_date(order)
            month = str(date_value)[:7] if date_value and date_value != "-" else "غير محدد"
            if month not in monthly:
                monthly[month] = {"sales": 0.0, "orders": 0}
            monthly[month]["sales"] += self.get_order_total(order)
            monthly[month]["orders"] += 1
        rows = []
        for month in sorted(monthly.keys()):
            rows.append([month, self.format_money(monthly[month]["sales"]), monthly[month]["orders"]])
        return headers, rows

    def render_sales_chart(self, rows):
        self.render_simple_bar_chart(rows, title_index=0, value_index=1, title="المبيعات الشهرية")

    def render_top_products_chart(self, rows):
        self.render_simple_bar_chart(rows[:5], title_index=0, value_index=2, title="أفضل 5 منتجات")

    def render_sales_summary(self, rows):
        if not rows:
            return
        totals = [self.get_order_total(order) for order in self.orders]
        total_sales = sum(totals)
        average = total_sales / len(totals) if totals else 0.0
        max_order = max(totals) if totals else 0.0
        min_order = min(totals) if totals else 0.0
        pending = sum(1 for order in self.orders if str(order.get("status", "")).lower() == "pending")
        completed = sum(1 for order in self.orders if str(order.get("status", "")).lower() in {"approved", "reviewed", "completed", "delivered"})

        summary = ctk.CTkFrame(self.table_frame, fg_color="#1f1f1f", corner_radius=10)
        summary.pack(fill="x", padx=8, pady=(8, 10))
        summary.grid_columnconfigure((0, 1, 2), weight=1)
        items = [
            ("عدد الطلبات", len(self.orders)),
            ("إجمالي المبيعات", self.format_money(total_sales)),
            ("متوسط الطلب", self.format_money(average)),
            ("أعلى طلب", self.format_money(max_order)),
            ("أقل طلب", self.format_money(min_order)),
            ("طلبات جديدة", pending),
            ("طلبات مكتملة", completed),
        ]
        for index, (label, value) in enumerate(items):
            ctk.CTkLabel(
                summary,
                text=self.ar(f"{label}: {value}"),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#dcdcdc",
                anchor="e",
                justify="right"
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=10, pady=6)

    def render_simple_bar_chart(self, rows, title_index, value_index, title):
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception:
            return
        if not rows:
            return
        chart_frame = ctk.CTkFrame(self.table_frame, fg_color="#1f1f1f", corner_radius=8)
        chart_frame.pack(fill="x", padx=8, pady=8)
        labels = [str(row[title_index]) for row in rows]
        values = []
        for row in rows:
            raw = str(row[value_index]).replace("جنيه", "").replace(",", "").strip()
            values.append(self.safe_float(raw))
        figure, ax = plt.subplots(figsize=(7, 3))
        ax.bar(labels, values, color="#4CAF50")
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
        figure.tight_layout()
        canvas = FigureCanvasTkAgg(figure, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=10)

    def render_table(self, headers, rows, clear=True):
        if clear:
            self.clear_report_table()

        if not rows:
            empty = ctk.CTkFrame(self.table_frame, fg_color="#263a2c", corner_radius=8)
            empty.pack(fill="x", pady=5)
            ctk.CTkLabel(
                empty,
                text="لا توجد بيانات في هذا التقرير",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#4CAF50",
                anchor="e",
                justify="right"
            ).pack(anchor="e", padx=14, pady=14)
            return

        header_row = ctk.CTkFrame(self.table_frame, fg_color="#1f1f1f", corner_radius=8)
        header_row.pack(fill="x", pady=(0, 5))

        for header in reversed(headers):
            ctk.CTkLabel(
                header_row,
                text=str(header),
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#4CAF50",
                width=140,
                anchor="e",
                justify="right"
            ).pack(side="right", padx=4, pady=8)

        for index, row_data in enumerate(rows):
            bg_color = "#333333" if index % 2 == 0 else "#3a3a3a"
            row = ctk.CTkFrame(self.table_frame, fg_color=bg_color, corner_radius=8)
            row.pack(fill="x", pady=3)

            for value in reversed(row_data):
                ctk.CTkLabel(
                    row,
                    text=str(value),
                    font=ctk.CTkFont(size=12),
                    text_color="white",
                    width=140,
                    anchor="e",
                    justify="right"
                ).pack(side="right", padx=4, pady=8)

    def export_current_report(self):
        if not self.current_rows:
            messagebox.showwarning("لا توجد بيانات", "لا توجد بيانات في التقرير الحالي للتصدير")
            return

        safe_name = self.current_report_name.replace(" ", "_")
        default_name = f"{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="حفظ التقرير"
        )

        if not file_path:
            return

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
            with open(file_path, "w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(self.current_headers)
                writer.writerows(self.current_rows)
        except Exception as exc:
            self.update_status("فشل تصدير التقرير")
            messagebox.showerror("خطأ", f"فشل تصدير التقرير:\n{exc}")
            return

        self.update_status(f"تم تصدير التقرير: {file_path}")
        messagebox.showinfo("نجاح", "تم تصدير التقرير بنجاح")

    def export_current_report_pdf(self):
        if not self.current_rows:
            messagebox.showwarning("لا توجد بيانات", "لا توجد بيانات في التقرير الحالي للتصدير")
            return
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
        except Exception:
            messagebox.showerror("PDF", "تصدير PDF يحتاج تثبيت reportlab")
            return
        safe_name = self.current_report_name.replace(" ", "_")
        default_name = f"{safe_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="حفظ التقرير PDF"
        )
        if not file_path:
            return
        try:
            styles = getSampleStyleSheet()
            story = [
                Paragraph("Pharmacy Management System", styles["Title"]),
                Paragraph(str(self.current_report_name), styles["Heading2"]),
                Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles["Normal"]),
                Spacer(1, 12),
            ]
            data = [list(self.current_headers)] + [list(row) for row in self.current_rows]
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d2d2d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))
            story.append(table)
            SimpleDocTemplate(file_path, pagesize=landscape(A4)).build(story)
            self.update_status(f"تم تصدير PDF: {file_path}")
            messagebox.showinfo("PDF", "تم تصدير التقرير PDF بنجاح")
        except Exception as exc:
            messagebox.showerror("PDF", f"فشل تصدير PDF:\n{exc}")

    def show_send_report_dialog(self):
        if not self.current_rows:
            messagebox.showwarning("لا توجد بيانات", "لا توجد بيانات في التقرير الحالي للإرسال")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("إرسال التقرير")
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frame, text="البريد الإلكتروني للمستلم", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(18, 8))
        email_entry = ctk.CTkEntry(frame, width=300, placeholder_text="example@email.com")
        email_entry.pack(pady=8)
        ctk.CTkButton(
            frame,
            text="إرسال",
            width=120,
            command=lambda: [self.send_current_report(email_entry.get().strip()), dialog.destroy()]
        ).pack(pady=16)

    def send_current_report(self, recipient):
        if not recipient:
            messagebox.showwarning("بيانات ناقصة", "أدخل بريد المستلم")
            return
        try:
            with open("app_settings.json", "r", encoding="utf-8") as file:
                settings = json.load(file)
        except Exception:
            settings = {}
        smtp_server = settings.get("smtp_server")
        smtp_port = int(settings.get("smtp_port", 587) or 587)
        smtp_email = settings.get("smtp_email")
        smtp_password = settings.get("smtp_password")
        if not smtp_server or not smtp_email or not smtp_password:
            messagebox.showerror("إعدادات ناقصة", "أكمل إعدادات SMTP من شاشة الإعدادات أولاً")
            return
        try:
            temp_path = os.path.join(tempfile.gettempdir(), f"{self.current_report_name}.csv")
            with open(temp_path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(self.current_headers)
                writer.writerows(self.current_rows)
            msg = EmailMessage()
            msg["Subject"] = self.current_report_name
            msg["From"] = smtp_email
            msg["To"] = recipient
            msg.set_content("مرفق التقرير المطلوب من نظام مخزن الندا.")
            with open(temp_path, "rb") as file:
                msg.add_attachment(file.read(), maintype="text", subtype="csv", filename=os.path.basename(temp_path))
            with smtplib.SMTP(smtp_server, smtp_port) as smtp:
                smtp.starttls()
                smtp.login(smtp_email, smtp_password)
                smtp.send_message(msg)
            messagebox.showinfo("تم الإرسال", "تم إرسال التقرير بنجاح")
            self.update_status("تم إرسال التقرير")
        except Exception as exc:
            messagebox.showerror("فشل الإرسال", f"فشل إرسال التقرير:\n{exc}")

    def show_offline_state(self):
        self.clear_content()
        self.update_status("السيرفر غير متصل")

        card = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card,
            text="السيرفر غير متصل",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f44336",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=22, pady=(24, 8))

        ctk.CTkLabel(
            card,
            text="شغّل السيرفر بالأمر:\npython -m uvicorn main:app --reload",
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=22, pady=(0, 24))
