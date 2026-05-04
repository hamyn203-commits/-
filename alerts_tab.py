import customtkinter as ctk
from datetime import datetime, timedelta

from api_client import APIClient
from rtl_utils import rtl


class AlertsTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None):
        super().__init__(master)

        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback

        self.products = []
        self.orders = []
        self.pharmacies = []

        self.stock_alerts = []
        self.expiry_alerts = []
        self.pending_orders = []
        self.debt_pharmacies = []

        self.configure(fg_color="#1e1e1e")
        self.create_ui()
        self.load_alerts()

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

    def priority_score(self, alert):
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(alert.get("severity"), 4)

    def severity_label(self, severity):
        return {
            "critical": "حرج",
            "high": "عالي",
            "medium": "متوسط",
            "low": "منخفض",
        }.get(severity, "تنبيه")

    def severity_color(self, severity):
        return {
            "critical": "#f44336",
            "high": "#FF9800",
            "medium": "#2196F3",
            "low": "#9C27B0",
        }.get(severity, "#607D8B")

    def create_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))
        header.grid_columnconfigure(0, weight=1)

        title_area = ctk.CTkFrame(header, fg_color="transparent")
        title_area.grid(row=0, column=0, sticky="ew", padx=22, pady=18)

        ctk.CTkLabel(
            title_area,
            text="🔔",
            font=ctk.CTkFont(size=30),
            text_color="#4CAF50"
        ).pack(side="right", padx=(10, 0))

        text_area = ctk.CTkFrame(title_area, fg_color="transparent")
        text_area.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            text_area,
            text=self.ar("التنبيهات"),
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).pack(anchor="e")

        ctk.CTkLabel(
            text_area,
            text=self.ar("تابع المخزون والصلاحية والطلبات والمديونيات من مكان واحد"),
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).pack(anchor="e", pady=(4, 0))

        ctk.CTkButton(
            title_area,
            text=self.ar("تحديث التنبيهات"),
            height=38,
            width=160,
            fg_color="#2196F3",
            hover_color="#1976D2",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.refresh_alerts
        ).pack(side="left")

        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="#1e1e1e")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content_frame.grid_columnconfigure(0, weight=1)

    def create_summary_card(self, parent, title, value, subtitle, color, column):
        card = ctk.CTkFrame(parent, fg_color="#2d2d2d", corner_radius=12, height=128, border_width=1, border_color="#3a3a3a")
        card.grid(row=0, column=column, sticky="ew", padx=6, pady=6)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(card, fg_color=color, width=5, corner_radius=5).grid(row=0, column=1, rowspan=3, sticky="ns", padx=(0, 8), pady=12)

        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff",
            anchor="e",
            justify="right"
        ).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 0))

        ctk.CTkLabel(
            card,
            text=str(value),
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=color,
            anchor="e"
        ).grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 0))

        ctk.CTkLabel(
            card,
            text=self.ar(subtitle),
            font=ctk.CTkFont(size=11),
            text_color="#bdbdbd",
            anchor="e",
            justify="right"
        ).grid(row=2, column=0, sticky="ew", padx=16, pady=(2, 12))

    def create_section_card(self, title, color, subtitle=None):
        card = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12)
        card.pack(fill="x", pady=10)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=self.ar(title),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=color,
            anchor="e",
            justify="right"
        ).pack(side="right")

        if subtitle:
            ctk.CTkLabel(
                header,
                text=self.ar(subtitle),
                font=ctk.CTkFont(size=12),
                text_color="#bdbdbd",
                anchor="e",
                justify="right"
            ).pack(side="right", padx=(0, 12))

        line = ctk.CTkFrame(card, height=2, fg_color="#3d3d3d")
        line.pack(fill="x", padx=16, pady=(0, 8))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(0, 16))
        return body

    def create_alert_row(self, parent, title, details, color, severity="medium", action_text=None, meta=None):
        row = ctk.CTkFrame(parent, fg_color="#333333", corner_radius=10, border_width=1, border_color="#3d3d3d")
        row.pack(fill="x", pady=5)
        row.grid_columnconfigure(0, weight=1)

        marker = ctk.CTkFrame(row, fg_color=color, width=5, corner_radius=3)
        marker.grid(row=0, column=3, rowspan=2, sticky="ns", padx=(0, 10), pady=8)

        badge = ctk.CTkLabel(
            row,
            text=self.ar(self.severity_label(severity)),
            width=70,
            height=26,
            fg_color=self.severity_color(severity),
            text_color="white",
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        badge.grid(row=0, column=2, padx=8, pady=(10, 4), sticky="e")

        text_box = ctk.CTkFrame(row, fg_color="transparent")
        text_box.grid(row=0, column=0, rowspan=2, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(
            text_box,
            text=self.ar(title),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            anchor="e",
            justify="right"
        ).pack(anchor="e", fill="x")

        ctk.CTkLabel(
            text_box,
            text=self.ar(details),
            font=ctk.CTkFont(size=12),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
            wraplength=620,
        ).pack(anchor="e", fill="x", pady=(3, 0))

        if meta:
            ctk.CTkLabel(
                text_box,
                text=self.ar(meta),
                font=ctk.CTkFont(size=11),
                text_color="#8fa3b7",
                anchor="e",
                justify="right",
            ).pack(anchor="e", fill="x", pady=(3, 0))

        if action_text:
            ctk.CTkLabel(
                row,
                text=self.ar(action_text),
                width=110,
                height=28,
                fg_color="#252525",
                text_color=color,
                corner_radius=8,
                font=ctk.CTkFont(size=11, weight="bold"),
            ).grid(row=1, column=2, padx=8, pady=(0, 10), sticky="e")

    def create_empty_message(self, parent):
        empty = ctk.CTkFrame(parent, fg_color="#263a2c", corner_radius=8)
        empty.pack(fill="x", pady=5)
        ctk.CTkLabel(
            empty,
            text="لا توجد تنبيهات",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=14, pady=12)

    def load_alerts(self):
        self.clear_content()

        if not self.check_server_health():
            self.show_offline_state()
            return

        try:
            self.products = self.api_client.get_products() or []
            self.orders = self.api_client.get_orders() or []
            self.pharmacies = self.api_client.get_pharmacies() or []
        except Exception as exc:
            self.update_status(f"فشل تحميل التنبيهات: {exc}")
            self.show_offline_state()
            return

        self.build_alert_data()
        self.render_alerts()
        self.update_status("تم تحديث التنبيهات بنجاح")

    def build_alert_data(self):
        self.stock_alerts = []
        self.expiry_alerts = []

        for product in self.products:
            name = product.get("name", "منتج غير معروف")
            quantity = self.safe_int(product.get("quantity", 0))
            category = product.get("category_name") or product.get("category") or "بدون تصنيف"

            if quantity == 0:
                self.stock_alerts.append({
                    "title": name,
                    "details": "الكمية: 0 | المنتج نافد",
                    "color": "#f44336",
                    "severity": "critical",
                    "action": "توريد عاجل",
                    "meta": f"التصنيف: {category}"
                })
            elif 1 <= quantity <= 5:
                self.stock_alerts.append({
                    "title": name,
                    "details": f"الكمية: {quantity} | المنتج منخفض",
                    "color": "#FF9800",
                    "severity": "high",
                    "action": "راجع المخزون",
                    "meta": f"التصنيف: {category}"
                })

            expiry_date = product.get("expiry_date")
            parsed_date = self.parse_date(expiry_date)
            if not parsed_date:
                continue

            if self.is_expired(expiry_date):
                self.expiry_alerts.append({
                    "title": name,
                    "details": f"تاريخ الصلاحية: {parsed_date} | منتهي الصلاحية",
                    "color": "#f44336",
                    "severity": "critical",
                    "action": "إيقاف بيع",
                    "meta": f"منتهي منذ {(datetime.now().date() - parsed_date).days} يوم"
                })
            elif self.is_expiring_soon(expiry_date):
                days_left = (parsed_date - datetime.now().date()).days
                self.expiry_alerts.append({
                    "title": name,
                    "details": f"تاريخ الصلاحية: {parsed_date} | قرب انتهاء الصلاحية",
                    "color": "#FF9800",
                    "severity": "high" if days_left <= 7 else "medium",
                    "action": "تصريف قريب",
                    "meta": f"متبقي {days_left} يوم"
                })

        self.pending_orders = [
            order for order in self.orders
            if str(order.get("status", "")).lower() == "pending"
        ]

        self.debt_pharmacies = sorted(
            [pharmacy for pharmacy in self.pharmacies if self.safe_float(pharmacy.get("balance", 0)) > 0],
            key=lambda pharmacy: self.safe_float(pharmacy.get("balance", 0)),
            reverse=True
        )

        self.stock_alerts.sort(key=self.priority_score)
        self.expiry_alerts.sort(key=self.priority_score)

    def render_alerts(self):
        critical_count = sum(1 for alert in self.stock_alerts + self.expiry_alerts if alert.get("severity") == "critical")
        high_count = sum(1 for alert in self.stock_alerts + self.expiry_alerts if alert.get("severity") == "high")
        total_alerts = len(self.stock_alerts) + len(self.expiry_alerts) + len(self.pending_orders) + len(self.debt_pharmacies)

        self.create_operational_overview(total_alerts, critical_count, high_count)

        summary = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        summary.pack(fill="x", pady=(0, 10))
        summary.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.create_summary_card(summary, "تنبيهات المخزون", len(self.stock_alerts), "نافد أو منخفض", "#f44336", 0)
        self.create_summary_card(summary, "تنبيهات الصلاحية", len(self.expiry_alerts), "منتهي أو قريب", "#FF9800", 1)
        self.create_summary_card(summary, "الطلبات الجديدة", len(self.pending_orders), "قيد الانتظار", "#2196F3", 2)
        self.create_summary_card(summary, "صيدليات عليها مديونية", len(self.debt_pharmacies), "أرصدة مستحقة", "#9C27B0", 3)

        urgent_alerts = sorted(self.stock_alerts + self.expiry_alerts, key=self.priority_score)[:6]
        urgent_body = self.create_section_card("الأهم الآن", "#f44336", "أعلى التنبيهات التي تحتاج قرار سريع")
        if urgent_alerts:
            for alert in urgent_alerts:
                self.create_alert_row(urgent_body, alert["title"], alert["details"], alert["color"], alert.get("severity"), alert.get("action"), alert.get("meta"))
        else:
            self.create_empty_message(urgent_body)

        stock_body = self.create_section_card("المخزون", "#FF9800", "المنتجات النافدة أو منخفضة الكمية")
        if self.stock_alerts:
            for alert in self.stock_alerts:
                self.create_alert_row(stock_body, alert["title"], alert["details"], alert["color"], alert.get("severity"), alert.get("action"), alert.get("meta"))
        else:
            self.create_empty_message(stock_body)

        expiry_body = self.create_section_card("الصلاحية", "#f44336", "منتجات منتهية أو قريبة الانتهاء خلال 30 يوم")
        if self.expiry_alerts:
            for alert in self.expiry_alerts:
                self.create_alert_row(expiry_body, alert["title"], alert["details"], alert["color"], alert.get("severity"), alert.get("action"), alert.get("meta"))
        else:
            self.create_empty_message(expiry_body)

        orders_body = self.create_section_card("الطلبات الجديدة", "#2196F3", "طلبات تحتاج متابعة واعتماد")
        if self.pending_orders:
            for order in self.pending_orders:
                order_number = order.get("order_number", order.get("id", "-"))
                pharmacy = self.get_pharmacy_name(order)
                total = self.format_money(self.get_order_total(order))
                date_value = self.get_order_date(order)
                self.create_alert_row(
                    orders_body,
                    f"طلب رقم: {order_number}",
                    f"الصيدلية: {pharmacy} | الإجمالي: {total} | التاريخ: {date_value}",
                    "#2196F3",
                    "medium",
                    "مراجعة الطلب",
                    "حالة الطلب: جديد"
                )
        else:
            self.create_empty_message(orders_body)

        debts_body = self.create_section_card("المديونيات", "#9C27B0", "صيدليات عليها أرصدة مستحقة")
        if self.debt_pharmacies:
            for pharmacy in self.debt_pharmacies:
                name = pharmacy.get("name", "صيدلية غير معروفة")
                phone = pharmacy.get("phone") or "-"
                balance = self.format_money(pharmacy.get("balance", 0))
                self.create_alert_row(
                    debts_body,
                    name,
                    f"الهاتف: {phone} | الرصيد: {balance}",
                    "#9C27B0",
                    "high" if self.safe_float(pharmacy.get("balance", 0)) >= 1000 else "medium",
                    "متابعة تحصيل",
                    "ترتيب حسب أعلى رصيد"
                )
        else:
            self.create_empty_message(debts_body)

    def create_operational_overview(self, total_alerts, critical_count, high_count):
        panel = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=12, border_width=1, border_color="#3a3a3a")
        panel.pack(fill="x", pady=(0, 10))
        panel.grid_columnconfigure((0, 1, 2), weight=1)

        status_text = "مستقر" if critical_count == 0 and high_count == 0 else ("يحتاج تدخل عاجل" if critical_count else "يحتاج متابعة")
        status_color = "#4CAF50" if status_text == "مستقر" else ("#f44336" if critical_count else "#FF9800")
        items = [
            ("حالة النظام", status_text, status_color),
            ("تنبيهات حرجة", critical_count, "#f44336"),
            ("إجمالي التنبيهات", total_alerts, "#2196F3"),
        ]
        for col, (title, value, color) in enumerate(items):
            box = ctk.CTkFrame(panel, fg_color="#252525", corner_radius=10)
            box.grid(row=0, column=col, sticky="ew", padx=8, pady=12)
            ctk.CTkLabel(box, text=self.ar(title), font=ctk.CTkFont(size=12, weight="bold"), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", padx=12, pady=(10, 0))
            ctk.CTkLabel(box, text=self.ar(value), font=ctk.CTkFont(size=18, weight="bold"), text_color=color, anchor="e", justify="right").pack(fill="x", padx=12, pady=(6, 12))

    def refresh_alerts(self):
        self.update_status("جاري تحديث التنبيهات...")
        self.load_alerts()

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
