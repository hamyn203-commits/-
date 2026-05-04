"""
Orders Tab for Pharmacy Management System
Displays orders and allows creating new orders with cart management
"""

import customtkinter as ctk
from tkinter import messagebox, ttk
from api_client import APIClient
from datetime import datetime, timedelta
from tkinter import filedialog
import json
from rtl_utils import rtl


class OrdersTab(ctk.CTkFrame):
    """Orders management tab"""

    def __init__(self, master, api_client=None, status_callback=None, role="admin"):
        super().__init__(master)

        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.role = role or "admin"
        self.current_filter = "الكل"
        self.date_from = None
        self.date_to = None
        self.search_term = ""
        self.processing_orders = set()  # Track orders being processed

        # Master-detail state
        self.selected_order_id = None
        self.orders_by_id = {}
        self.order_cards = {}
        
        # Cache for products
        self.products_cache = []
        self.pharmacies_cache = []
        
        self.configure(fg_color="#1e1e1e")

        self.create_ui()
        self.load_orders()

    def can_manage_orders(self):
        return self.role == "admin"

    def show_permission_denied(self):
        self.show_warning("هذه العملية غير متاحة لهذا الدور")
    
    # ==========================================
    # Helper Methods
    # ==========================================

    def translate_status(self, status):
        """Translate status to Arabic"""
        status_map = {
            "pending": "جديد",
            "reviewed": "تمت المراجعة",
            "in_store": "في المخزن",
            "with_driver": "مع المندوب",
            "on_the_way": "في الطريق إليك",
            "delivered": "تم التسليم",
            "postponed": "مؤجل",
            "cancelled": "ملغي",
            "approved": "تمت المراجعة",
            "rejected": "ملغي",
            "completed": "تم التسليم"
        }
        return status_map.get(status, status)

    def ar(self, text):
        """Format short Arabic labels for CustomTkinter display."""
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

    def get_status_color(self, status):
        """Get color for status display"""
        color_map = {
            "pending": "#FFA500",
            "reviewed": "#2196F3",
            "in_store": "#5E35B1",
            "with_driver": "#00BCD4",
            "on_the_way": "#CDDC39",
            "delivered": "#4CAF50",
            "postponed": "#8D6E63",
            "cancelled": "#f44336",
            "approved": "#2196F3",
            "rejected": "#f44336",
            "completed": "#4CAF50"
        }
        return color_map.get(status, "white")
    
    def get_status_icon(self, status):
        """Get icon for status display"""
        icon_map = {
            "pending": "⏳",
            "reviewed": "📝",
            "in_store": "🏬",
            "with_driver": "🧾",
            "on_the_way": "🚚",
            "delivered": "✅",
            "postponed": "⏸",
            "cancelled": "❌",
            "approved": "📝",
            "rejected": "❌",
            "completed": "✅"
        }
        return icon_map.get(status, "📋")

    def normalize_status(self, status):
        legacy_map = {
            "approved": "reviewed",
            "rejected": "cancelled",
            "completed": "delivered",
        }
        status = (status or "pending").lower()
        return legacy_map.get(status, status)

    def ui_status(self, status):
        """
        Normalize backend/legacy status values into the UI states required by the master-detail screen.
        UI states: pending / approved / completed / rejected
        """
        status = (status or "pending").lower()
        ui_map = {
            "pending": "pending",
            "reviewed": "approved",
            "approved": "approved",
            "delivered": "completed",
            "completed": "completed",
            "cancelled": "rejected",
            "rejected": "rejected",
        }
        return ui_map.get(status, status)

    def get_delivery_note(self, order):
        return order.get("expected_delivery_note") or "الطلب في الطريق إليك، ومتوقع وصوله خلال 30 إلى 60 دقيقة"

    def translate_payment_status(self, status):
        status_map = {
            "unpaid": "لم يدفع",
            "cash": "دفع كاش",
            "partial": "دفع جزء",
            "full": "دفع كامل",
            "deferred": "أجل",
            "collect_on_delivery": "تحصيل عند الاستلام",
        }
        return status_map.get(status or "unpaid", status or "لم يدفع")

    def get_payment_status_color(self, status):
        color_map = {
            "unpaid": "#f44336",
            "cash": "#4CAF50",
            "partial": "#FF9800",
            "full": "#4CAF50",
            "deferred": "#8D6E63",
            "collect_on_delivery": "#00BCD4",
        }
        return color_map.get(status or "unpaid", "#bdbdbd")

    def get_order_payment_summary(self, order):
        payment_status = order.get("payment_status") or "unpaid"
        amount_paid = self.safe_float(order.get("amount_paid", 0))
        remaining = order.get("remaining_amount")
        if remaining is None:
            remaining = max(self.get_order_total(order) - amount_paid, 0.0)
        remaining = self.safe_float(remaining)
        return payment_status, amount_paid, remaining

    def get_order_total(self, order):
        """Get order total safely"""
        total = order.get("total", order.get("total_amount", order.get("total_price", 0)))
        try:
            return float(total)
        except (ValueError, TypeError):
            return 0.0

    def get_order_date(self, order):
        """Get order date safely"""
        date = order.get("order_date", order.get("created_at", order.get("date", "-")))
        if date and date != "-":
            if hasattr(date, 'strftime'):
                return date.strftime("%Y-%m-%d %H:%M")
            elif isinstance(date, str) and len(date) > 19:
                return date[:19]
        return date
    
    def format_date_display(self, date_str):
        """Format date for display"""
        if not date_str or date_str == "-":
            return "-"
        try:
            if len(date_str) >= 16:
                return date_str[:16]
            return date_str
        except:
            return date_str

    def get_pharmacy_name(self, order):
        """Get pharmacy name safely"""
        pharmacy_name = (
            order.get("pharmacy_name") or
            order.get("customer_name") or
            order.get("client_name") or
            "-"
        )
        if pharmacy_name == "-" and isinstance(order.get("pharmacy"), dict):
            pharmacy_name = order["pharmacy"].get("name", "-")
        return pharmacy_name

    def get_item_price(self, item):
        """Get item price safely"""
        price = item.get("price", item.get("unit_price", 0))
        try:
            return float(price)
        except (ValueError, TypeError):
            return 0.0

    def get_item_total(self, item):
        """Get item total safely"""
        total = item.get("total", item.get("total_price", 0))
        try:
            return float(total)
        except (ValueError, TypeError):
            return self.get_item_price(item) * item.get("quantity", 0)

    def get_item_name(self, item):
        """Get item name safely"""
        return (
            item.get("product_name") or
            item.get("name") or
            (item.get("product", {}).get("name") if isinstance(item.get("product"), dict) else None) or
            "-"
        )

    def get_item_product_name(self, item):
        """Alias for get_item_name"""
        return self.get_item_name(item)
    
    def get_items_count(self, order):
        """Get number of items in order"""
        items = order.get("items", order.get("order_items", []))
        return len(items)
    
    def calculate_order_stats(self, orders):
        """Calculate statistics for orders"""
        stats = {
            "total": len(orders),
            "pending": 0,
            "active": 0,
            "delivered": 0,
            "cancelled": 0,
            "total_value": 0.0
        }
        
        for order in orders:
            status = self.normalize_status(order.get("status", "pending"))
            if status == "pending":
                stats["pending"] += 1
            elif status == "delivered":
                stats["delivered"] += 1
            elif status == "cancelled":
                stats["cancelled"] += 1
            else:
                stats["active"] += 1
            
            total = self.get_order_total(order)
            stats["total_value"] += total
        
        return stats

    def show_error(self, message, title="خطأ"):
        """Show error message box"""
        messagebox.showerror(title, message)

    def show_info(self, message, title="معلومات"):
        """Show info message box"""
        messagebox.showinfo(title, message)

    def show_warning(self, message, title="تحذير"):
        """Show warning message box"""
        messagebox.showwarning(title, message)

    def update_status(self, message):
        """Update status bar safely"""
        if self.status_callback:
            try:
                self.status_callback(message)
            except:
                pass

    def check_server_health(self):
        """Check if server is reachable"""
        try:
            if hasattr(self.api_client, "health_check"):
                return self.api_client.health_check()
            return True
        except:
            return False

    def format_money(self, value):
        """Format money value with commas and 2 decimals"""
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return "0.00"
    
    def export_orders_to_json(self):
        """Export orders to JSON file"""
        if not hasattr(self, 'current_orders') or not self.current_orders:
            self.show_warning("لا توجد بيانات للتصدير")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="تصدير الطلبات"
            )
            
            if not file_path:
                return
            
            export_data = []
            for order in self.current_orders:
                export_data.append({
                    "id": order.get("id"),
                    "order_number": order.get("order_number"),
                    "pharmacy_name": self.get_pharmacy_name(order),
                    "total": self.get_order_total(order),
                    "status": order.get("status"),
                    "date": self.get_order_date(order),
                    "items_count": self.get_items_count(order)
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.update_status(f"✅ تم تصدير {len(export_data)} طلب بنجاح")
            self.show_info(f"تم تصدير {len(export_data)} طلب بنجاح")
            
        except Exception as e:
            self.show_error(f"فشل التصدير: {str(e)}")
    
    def print_order_invoice(self, order):
        """Show a professional invoice preview for an order."""
        try:
            order_id = order.get("id", "-")
            invoice_number = order.get("order_number", f"ORD-{order_id}")
            pharmacy_name = self.get_pharmacy_name(order)
            order_date = self.format_date_display(self.get_order_date(order))
            status = order.get("status", "pending")
            status_text = self.translate_status(status)
            status_color = self.get_status_color(status)
            total = self.get_order_total(order)
            items = order.get("items", order.get("order_items", []))

            dialog = ctk.CTkToplevel(self)
            dialog.title(f"فاتورة الطلب #{order_id}")
            dialog.geometry("920x700")
            dialog.minsize(850, 620)
            dialog.resizable(True, True)
            dialog.transient(self)
            dialog.grab_set()
            dialog.bind("<Escape>", lambda e: dialog.destroy())

            main_frame = ctk.CTkFrame(dialog, fg_color="#1e1e1e")
            main_frame.pack(fill="both", expand=True, padx=18, pady=18)

            header = ctk.CTkFrame(main_frame, fg_color="#2d2d2d", corner_radius=14)
            header.pack(fill="x", pady=(0, 14))

            title_frame = ctk.CTkFrame(header, fg_color="transparent")
            title_frame.pack(fill="x", padx=18, pady=(16, 8))

            ctk.CTkLabel(
                title_frame,
                text=self.ar("مخزن الندا"),
                font=ctk.CTkFont(size=22, weight="bold"),
                text_color="#4CAF50",
                anchor="e"
            ).pack(side="right")

            ctk.CTkLabel(
                title_frame,
                text=self.ar("فاتورة طلب"),
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color="white",
                anchor="w"
            ).pack(side="left")

            info_grid = ctk.CTkFrame(header, fg_color="transparent")
            info_grid.pack(fill="x", padx=18, pady=(0, 16))
            info_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

            self.create_invoice_info_card(info_grid, "رقم الفاتورة", str(invoice_number), "#2196F3", 0)
            self.create_invoice_info_card(info_grid, "الصيدلية", str(pharmacy_name), "#4CAF50", 1)
            self.create_invoice_info_card(info_grid, "التاريخ", str(order_date), "#FF9800", 2)
            self.create_invoice_info_card(info_grid, "الحالة", status_text, status_color, 3)

            items_frame = ctk.CTkScrollableFrame(main_frame, fg_color="#2d2d2d", corner_radius=12)
            items_frame.pack(fill="both", expand=True, pady=(0, 14))

            self.create_invoice_items_header(items_frame)

            if items:
                for index, item in enumerate(items, start=1):
                    self.create_invoice_item_row(items_frame, index, item)
            else:
                ctk.CTkLabel(
                    items_frame,
                    text=self.ar("لا توجد منتجات داخل هذا الطلب"),
                    font=ctk.CTkFont(size=14),
                    text_color="#9e9e9e"
                ).pack(pady=40)

            footer = ctk.CTkFrame(main_frame, fg_color="#2d2d2d", corner_radius=12)
            footer.pack(fill="x")

            total_box = ctk.CTkFrame(footer, fg_color="#1f1f1f", corner_radius=10)
            total_box.pack(side="right", padx=14, pady=12)

            ctk.CTkLabel(
                total_box,
                text=self.ar("الإجمالي"),
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#bdbdbd"
            ).pack(anchor="e", padx=16, pady=(10, 0))

            ctk.CTkLabel(
                total_box,
                text=f"{self.format_money(total)} جنيه",
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color="#4CAF50"
            ).pack(anchor="e", padx=16, pady=(2, 12))

            discount = self.safe_float(order.get("discount", 0))
            if discount > 0:
                discount_type = order.get("discount_type", "value")
                original_total = self.safe_float(order.get("total_amount", total))
                discount_text = f"{discount:.2f}%" if discount_type == "percent" else f"{self.format_money(discount)} جنيه"
                ctk.CTkLabel(
                    total_box,
                    text=self.ar(f"قبل الخصم: {self.format_money(original_total)} جنيه"),
                    font=ctk.CTkFont(size=12),
                    text_color="#bdbdbd"
                ).pack(anchor="e", padx=16, pady=(0, 2))
                ctk.CTkLabel(
                    total_box,
                    text=self.ar(f"الخصم: {discount_text}"),
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#FF9800"
                ).pack(anchor="e", padx=16, pady=(0, 10))

            buttons_frame = ctk.CTkFrame(footer, fg_color="transparent")
            buttons_frame.pack(side="left", padx=14, pady=16)

            ctk.CTkButton(
                buttons_frame,
                text=self.ar("نسخ ملخص الفاتورة"),
                width=160,
                height=36,
                fg_color="#2196F3",
                hover_color="#1976D2",
                command=lambda o=order: self.copy_invoice_summary(o)
            ).pack(side="left", padx=6)

            ctk.CTkButton(
                buttons_frame,
                text=self.ar("إغلاق"),
                width=100,
                height=36,
                fg_color="#555555",
                hover_color="#666666",
                command=dialog.destroy
            ).pack(side="left", padx=6)

            self.update_status(f"تم فتح فاتورة الطلب {order_id}")

        except Exception as e:
            self.show_error(f"حدث خطأ أثناء فتح الفاتورة:\n{str(e)}")
            self.update_status("خطأ في فتح فاتورة الطلب")

    def create_invoice_info_card(self, parent, title, value, color, column):
        """Create compact invoice metadata card."""
        card = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=10)
        card.grid(row=0, column=column, sticky="ew", padx=5)

        ctk.CTkFrame(card, fg_color=color, height=4).pack(fill="x", padx=10, pady=(10, 8))
        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#bdbdbd",
            anchor="e"
        ).pack(anchor="e", padx=12)
        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white",
            anchor="e"
        ).pack(anchor="e", padx=12, pady=(4, 12))

    def create_invoice_items_header(self, parent):
        """Create invoice products header."""
        header = ctk.CTkFrame(parent, fg_color="#1f1f1f", corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 4))

        headers = [
            ("#", 50),
            ("المنتج", 300),
            ("الكمية", 90),
            ("السعر", 140),
            ("الإجمالي", 150),
        ]

        for text, width in headers:
            ctk.CTkLabel(
                header,
                text=self.ar(text) if text != "#" else "#",
                width=width,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#4CAF50"
            ).pack(side="left", padx=4, pady=8)

    def create_invoice_item_row(self, parent, index, item):
        """Create one invoice product row."""
        quantity = item.get("quantity", 0)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 0

        price = self.get_item_price(item)
        total_price = self.get_item_total(item)

        row = ctk.CTkFrame(parent, fg_color="#333333", corner_radius=8)
        row.pack(fill="x", padx=8, pady=3)

        values = [
            (str(index), 50, "white"),
            (self.get_item_name(item), 300, "white"),
            (str(quantity), 90, "white"),
            (self.format_money(price), 140, "white"),
            (self.format_money(total_price), 150, "#4CAF50"),
        ]

        for text, width, color in values:
            ctk.CTkLabel(
                row,
                text=str(text),
                width=width,
                font=ctk.CTkFont(size=12),
                text_color=color,
                anchor="center"
            ).pack(side="left", padx=4, pady=8)

    def build_invoice_summary(self, order):
        """Build a plain text invoice summary for copying."""
        order_id = order.get("id", "-")
        invoice_number = order.get("order_number", f"ORD-{order_id}")
        pharmacy_name = self.get_pharmacy_name(order)
        order_date = self.format_date_display(self.get_order_date(order))
        status = self.translate_status(order.get("status", "pending"))
        total = self.get_order_total(order)
        items = order.get("items", order.get("order_items", []))

        lines = [
            "مخزن الندا",
            f"فاتورة طلب: {invoice_number}",
            f"الصيدلية: {pharmacy_name}",
            f"التاريخ: {order_date}",
            f"الحالة: {status}",
            "",
            "المنتجات:",
        ]

        if items:
            for index, item in enumerate(items, start=1):
                name = self.get_item_name(item)
                quantity = item.get("quantity", 0)
                price = self.get_item_price(item)
                item_total = self.get_item_total(item)
                lines.append(
                    f"{index}. {name} | الكمية: {quantity} | السعر: {self.format_money(price)} | الإجمالي: {self.format_money(item_total)}"
                )
        else:
            lines.append("لا توجد منتجات")

        lines.extend(["", f"الإجمالي: {self.format_money(total)} جنيه"])
        return "\n".join(lines)

    def copy_invoice_summary(self, order):
        """Copy invoice summary to clipboard."""
        try:
            text = self.build_invoice_summary(order)
            self.clipboard_clear()
            self.clipboard_append(text)
            self.show_info("تم نسخ ملخص الفاتورة")
            self.update_status("تم نسخ ملخص الفاتورة")
        except Exception as e:
            self.show_error(f"فشل نسخ الفاتورة:\n{str(e)}")

    def clear_table(self):
        """Clear orders list (left) and details (right) safely"""
        list_frame = getattr(self, "orders_list_frame", None)
        if list_frame is not None:
            for widget in list(list_frame.winfo_children()):
                try:
                    if widget and widget.winfo_exists():
                        widget.destroy()
                except Exception:
                    pass

        self.order_cards = {}
        self.orders_by_id = {}
        self.selected_order_id = None

        self._clear_right_panel()

    def _clear_right_panel(self):
        """Clear right details content safely"""
        for attr in ("pharmacy_info_frame", "items_container", "summary_frame", "actions_frame"):
            frame = getattr(self, attr, None)
            if frame is None:
                continue
            for widget in list(frame.winfo_children()):
                try:
                    if widget and widget.winfo_exists():
                        widget.destroy()
                except Exception:
                    pass

        header_label = getattr(self, "details_header_label", None)
        if header_label is not None:
            try:
                header_label.configure(text=self.ar("اختر طلباً من القائمة"))
            except Exception:
                pass

    # ==========================================
    # Main UI Creation
    # ==========================================

    def create_ui(self):
        """Create the user interface"""
        # Top frame for title and buttons
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=(20, 10))

        # Title
        self.title_label = ctk.CTkLabel(
            self.top_frame,
            text="الطلبات",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        self.title_label.pack(side="left")
        
        # Export button
        self.export_btn = ctk.CTkButton(
            self.top_frame,
            text="📄 تصدير",
            width=80,
            height=35,
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            command=self.export_orders_to_json
        )
        self.export_btn.pack(side="right", padx=(0, 10))
        
        self.create_order_btn = ctk.CTkButton(
            self.top_frame,
            text="+ إنشاء طلب",
            width=120,
            height=35,
            command=self.show_create_order_dialog
        )
        self.create_order_btn.pack(side="right", padx=(0, 10))
        if not self.can_manage_orders():
            self.create_order_btn.configure(state="disabled")

        # Stats Frame
        self.stats_frame = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=10)
        self.stats_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.stats_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Smart insights frame
        self.insights_frame = ctk.CTkFrame(self, fg_color="transparent", height=96)
        self.insights_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.insights_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.insights_frame.grid_rowconfigure(0, weight=1)
        self.insights_frame.grid_propagate(False)
        self.insights_frame.pack_propagate(False)
        
        # Filter Frame
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Filter by status
        status_filter_frame = ctk.CTkFrame(filter_frame, fg_color="#2d2d2d", corner_radius=8)
        status_filter_frame.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            status_filter_frame,
            text="الحالة:",
            font=ctk.CTkFont(size=13),
            text_color="white"
        ).pack(side="left", padx=(10, 5), pady=5)
        
        self.filter_var = ctk.StringVar(value="الكل")
        filter_options = [
            "الكل",
            "جديد",
            "تمت المراجعة",
            "في المخزن",
            "مع المندوب",
            "في الطريق إليك",
            "تم التسليم",
            "مؤجل",
            "ملغي",
        ]
        
        self.filter_menu = ctk.CTkOptionMenu(
            status_filter_frame,
            values=filter_options,
            variable=self.filter_var,
            width=150,
            command=self.on_filter_change
        )
        self.filter_menu.pack(side="left", padx=(0, 10), pady=5)
        
        # Date filter
        date_filter_frame = ctk.CTkFrame(filter_frame, fg_color="#2d2d2d", corner_radius=8)
        date_filter_frame.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            date_filter_frame,
            text="من تاريخ:",
            font=ctk.CTkFont(size=13),
            text_color="white"
        ).pack(side="left", padx=(10, 5), pady=5)
        
        self.date_from_entry = ctk.CTkEntry(
            date_filter_frame,
            placeholder_text="YYYY-MM-DD",
            width=100
        )
        self.date_from_entry.pack(side="left", padx=5, pady=5)
        
        ctk.CTkLabel(
            date_filter_frame,
            text="إلى تاريخ:",
            font=ctk.CTkFont(size=13),
            text_color="white"
        ).pack(side="left", padx=(10, 5), pady=5)
        
        self.date_to_entry = ctk.CTkEntry(
            date_filter_frame,
            placeholder_text="YYYY-MM-DD",
            width=100
        )
        self.date_to_entry.pack(side="left", padx=5, pady=5)
        
        self.apply_date_btn = ctk.CTkButton(
            date_filter_frame,
            text="تطبيق",
            width=60,
            height=30,
            command=self.apply_date_filter
        )
        self.apply_date_btn.pack(side="left", padx=5, pady=5)
        
        self.clear_date_btn = ctk.CTkButton(
            date_filter_frame,
            text="مسح",
            width=50,
            height=30,
            fg_color="#555555",
            command=self.clear_date_filter
        )
        self.clear_date_btn.pack(side="left", padx=5, pady=5)
        
        # Search box
        search_frame = ctk.CTkFrame(filter_frame, fg_color="#2d2d2d", corner_radius=8)
        search_frame.pack(side="right")
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 بحث برقم الطلب أو الصيدلية...",
            width=200
        )
        self.search_entry.pack(side="left", padx=10, pady=5)
        self.search_entry.bind("<Return>", lambda e: self.apply_search())
        
        self.search_btn = ctk.CTkButton(
            search_frame,
            text="بحث",
            width=60,
            height=30,
            command=self.apply_search
        )
        self.search_btn.pack(side="left", padx=(0, 10), pady=5)
        
        self.refresh_btn = ctk.CTkButton(
            search_frame,
            text="🔄 تحديث",
            width=80,
            height=30,
            command=self.load_orders
        )
        self.refresh_btn.pack(side="right", padx=10, pady=5)

        # Main master-detail layout
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)

        # Left: orders list
        self.left_frame = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=10, width=350)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.left_frame.grid_propagate(False)

        ctk.CTkLabel(
            self.left_frame,
            text=self.ar("قائمة الطلبات"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white",
            anchor="e",
            justify="right"
        ).pack(fill="x", padx=12, pady=(12, 6))

        self.orders_list_frame = ctk.CTkScrollableFrame(self.left_frame, fg_color="transparent", corner_radius=0)
        self.orders_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        # Right: selected order details
        self.right_frame = ctk.CTkFrame(self.content_frame, fg_color="#2d2d2d", corner_radius=10)
        self.right_frame.grid(row=0, column=1, sticky="nsew")
        self.right_frame.grid_rowconfigure(2, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        self.details_header_label = ctk.CTkLabel(
            header_row,
            text=self.ar("اختر طلباً من القائمة"),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white",
            anchor="e",
            justify="right"
        )
        self.details_header_label.pack(side="right")

        # Pharmacy info card
        self.pharmacy_info_frame = ctk.CTkFrame(self.right_frame, fg_color="#1f1f1f", corner_radius=12)
        self.pharmacy_info_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

        # Items table container (scrollable)
        self.items_container = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.items_container.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.items_container.grid_rowconfigure(1, weight=1)
        self.items_container.grid_columnconfigure(0, weight=1)

        self.items_scroll = ctk.CTkScrollableFrame(self.items_container, fg_color="#1f1f1f", corner_radius=12)
        self.items_scroll.grid(row=1, column=0, sticky="nsew")

        # Summary and actions
        bottom_row = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        bottom_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        bottom_row.grid_columnconfigure(0, weight=1)

        self.summary_frame = ctk.CTkFrame(bottom_row, fg_color="#1f1f1f", corner_radius=12)
        self.summary_frame.grid(row=0, column=0, sticky="ew")

        self.actions_frame = ctk.CTkFrame(bottom_row, fg_color="transparent")
        self.actions_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

    def create_stats_cards(self, stats):
        """Create statistics cards"""
        # Clear existing stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        # Total orders card
        self.create_stat_card(self.stats_frame, "إجمالي الطلبات", stats["total"], "طلب", "#2196F3", "📊", 0, 0)
        
        # Pending card
        self.create_stat_card(self.stats_frame, "قيد الانتظار", stats["pending"], "طلب", "#FF9800", "⏳", 0, 1)
        
        # Active cycle card
        self.create_stat_card(self.stats_frame, "قيد التنفيذ", stats["active"], "طلب", "#00BCD4", "🚚", 0, 2)
        
        # Delivered card
        self.create_stat_card(self.stats_frame, "تم التسليم", stats["delivered"], "طلب", "#4CAF50", "✅", 0, 3)
        
        # Total value card
        self.create_stat_card(self.stats_frame, "إجمالي القيمة", self.format_money(stats["total_value"]), "جنيه", "#9C27B0", "💰", 0, 4)
    
    def create_stat_card(self, parent, title, value, subtitle, color, icon, row, column):
        """Create a statistics card"""
        card = ctk.CTkFrame(parent, fg_color="#303030", corner_radius=10)
        card.grid(row=row, column=column, sticky="ew", padx=5, pady=5)

        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=10, pady=(10, 8))

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10)
        
        ctk.CTkLabel(
            top_row,
            text=icon,
            font=ctk.CTkFont(size=18),
            text_color=color
        ).pack(side="right")

        ctk.CTkLabel(
            top_row,
            text=self.ar(title),
            font=ctk.CTkFont(size=12),
            text_color="white",
            anchor="e",
            justify="right"
        ).pack(side="right", padx=(0, 8))
        
        ctk.CTkLabel(
            card,
            text=str(value),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        ).pack(anchor="e", padx=10, pady=(8, 0))
        
        ctk.CTkLabel(
            card,
            text=self.ar(subtitle),
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="e",
            justify="right"
        ).pack(anchor="e", padx=10, pady=(0, 10))

    def create_insights_panel(self, orders, stats):
        """Create a small smart summary for important order signals."""
        for widget in self.insights_frame.winfo_children():
            widget.destroy()

        pending_orders = [o for o in orders if o.get("status") == "pending"]
        largest_order = max(orders, key=self.get_order_total) if orders else None
        average_value = stats["total_value"] / stats["total"] if stats["total"] else 0

        oldest_pending = None
        if pending_orders:
            oldest_pending = sorted(pending_orders, key=lambda o: o.get("id", 0))[0]

        pending_text = "-"
        if oldest_pending:
            pending_text = f"#{oldest_pending.get('id', '-')}"

        largest_text = "-"
        if largest_order:
            largest_text = f"#{largest_order.get('id', '-')} | {self.format_money(self.get_order_total(largest_order))}"

        self.create_insight_card(
            self.insights_frame,
            self.ar("أقدم طلب جديد"),
            pending_text,
            self.ar("راجع الطلبات المعلقة أولًا"),
            "#FF9800",
            0
        )
        self.create_insight_card(
            self.insights_frame,
            self.ar("أكبر طلب"),
            largest_text,
            self.ar("أعلى قيمة في القائمة الحالية"),
            "#4CAF50",
            1
        )
        self.create_insight_card(
            self.insights_frame,
            self.ar("متوسط الطلب"),
            self.format_money(average_value),
            self.ar("متوسط قيمة الطلبات المعروضة"),
            "#00BCD4",
            2
        )

    def create_insight_card(self, parent, title, value, subtitle, color, column):
        """Create one insight card."""
        card = ctk.CTkFrame(parent, fg_color="#2d2d2d", corner_radius=8, height=78)
        card.grid(row=0, column=column, sticky="nsew", padx=5, pady=4)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(card, fg_color=color, width=4, corner_radius=4).grid(row=0, column=1, rowspan=3, sticky="ns", padx=(6, 0), pady=8)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=color,
            anchor="e",
            justify="right"
        ).grid(row=0, column=0, sticky="e", padx=10, pady=(7, 0))

        ctk.CTkLabel(
            card,
            text=str(value),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white",
            anchor="e"
        ).grid(row=1, column=0, sticky="e", padx=10, pady=(0, 0))

        ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=10),
            text_color="#9e9e9e",
            anchor="e",
            justify="right"
        ).grid(row=2, column=0, sticky="e", padx=10, pady=(0, 6))

    def on_filter_change(self, value):
        """Handle filter change"""
        self.current_filter = value
        self.load_orders()

    def apply_date_filter(self):
        """Apply date filter to orders"""
        date_from = self.date_from_entry.get().strip()
        date_to = self.date_to_entry.get().strip()
        
        if date_from:
            try:
                self.date_from = datetime.strptime(date_from, "%Y-%m-%d")
            except:
                self.show_error("صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD")
                return
        
        if date_to:
            try:
                self.date_to = datetime.strptime(date_to + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            except:
                self.show_error("صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD")
                return
        
        self.load_orders()
    
    def clear_date_filter(self):
        """Clear date filter"""
        self.date_from = None
        self.date_to = None
        self.date_from_entry.delete(0, "end")
        self.date_to_entry.delete(0, "end")
        self.load_orders()
    
    def apply_search(self):
        """Apply search filter"""
        self.search_term = self.search_entry.get().strip()
        self.load_orders()

    def load_orders(self):
        """Load orders from API"""
        prev_selected = getattr(self, "selected_order_id", None)
        self.clear_table()
        for widget in self.insights_frame.winfo_children():
            widget.destroy()

        if not self.check_server_health():
            self.update_status("⚠️ السيرفر غير متصل")
            self.show_empty_state(
                "⚠️ السيرفر غير متصل\n\n"
                "قم بتشغيل السيرفر باستخدام الأمر:\n"
                "python -m uvicorn main:app --reload"
            )
            return

        try:
            self.update_status("جاري تحميل الطلبات...")

            orders = self.api_client.get_orders()

            if not orders:
                self.show_empty_state("📋 لا توجد طلبات حاليًا\nاضغط على 'إنشاء طلب' لإضافة طلب جديد")
                self.update_status("لا توجد طلبات")
                return
            
            # Apply status filter
            if self.current_filter != "الكل":
                filter_map = {
                    "جديد": "pending",
                    "تمت المراجعة": "reviewed",
                    "في المخزن": "in_store",
                    "مع المندوب": "with_driver",
                    "في الطريق إليك": "on_the_way",
                    "تم التسليم": "delivered",
                    "مؤجل": "postponed",
                    "ملغي": "cancelled",
                }
                status_filter = filter_map.get(self.current_filter)
                if status_filter:
                    orders = [o for o in orders if self.normalize_status(o.get("status")) == status_filter]
            
            # Apply date filter
            if self.date_from or self.date_to:
                filtered = []
                for o in orders:
                    order_date = self.get_order_date(o)
                    if order_date and order_date != "-":
                        try:
                            date_str = order_date[:10]
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            if self.date_from and date_obj < self.date_from:
                                continue
                            if self.date_to and date_obj > self.date_to:
                                continue
                        except:
                            pass
                    filtered.append(o)
                orders = filtered
            
            # Apply search filter
            if self.search_term:
                search_lower = self.search_term.lower()
                filtered = []
                for o in orders:
                    order_id = str(o.get("id", ""))
                    pharmacy_name = self.get_pharmacy_name(o).lower()
                    if search_lower in order_id or search_lower in pharmacy_name:
                        filtered.append(o)
                orders = filtered
            
            # Store current orders for export
            self.current_orders = orders
            
            # Sort orders by id descending (newest first)
            orders.sort(key=lambda x: x.get("id", 0), reverse=True)

            # Build caches for master-detail selection
            self.orders_by_id = {}
            for o in orders:
                oid = o.get("id")
                if oid is not None:
                    self.orders_by_id[oid] = o
            
            # Calculate and display stats
            stats = self.calculate_order_stats(orders)
            self.create_stats_cards(stats)
            self.create_insights_panel(orders, stats)

            # Display orders as cards (left list)
            for order in orders:
                self._create_order_card(order)

            # Auto-select newest (or keep previous selection if still available)
            target_id = None
            if prev_selected is not None and prev_selected in self.orders_by_id:
                target_id = prev_selected
            elif orders:
                target_id = orders[0].get("id")

            if target_id is not None:
                self.select_order(target_id)

            self.update_status(f"✅ تم تحميل {len(orders)} طلب")

        except Exception as e:
            self.update_status("❌ خطأ في تحميل الطلبات")
            self.show_empty_state(f"⚠️ حدث خطأ أثناء تحميل الطلبات\n\n{str(e)}")

    def show_empty_state(self, message):
        """Show empty state message"""
        # Show it in left list area if available; otherwise fall back to self
        parent = getattr(self, "orders_list_frame", None) or self
        empty_label = ctk.CTkLabel(parent, text=message, font=ctk.CTkFont(size=16), text_color="gray", justify="center")
        empty_label.pack(pady=50, padx=20)
        self._clear_right_panel()

    # ==========================================
    # Master-Detail UI (Cards + Details Panel)
    # ==========================================

    def _create_order_card(self, order):
        """Create an order card in the left list."""
        order_id = order.get("id", "-")
        pharmacy_name = self.get_pharmacy_name(order)
        total = self.get_order_total(order)
        status_ui = self.ui_status(order.get("status", "pending"))
        status_ar = self.translate_status(status_ui)
        status_color = self.get_status_color(status_ui)
        date_text = self.format_date_display(self.get_order_date(order))

        card = ctk.CTkFrame(self.orders_list_frame, fg_color="#2d2d2d", corner_radius=12)
        card.pack(fill="x", padx=6, pady=6)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # Row 1 (RTL): pharmacy name + order number
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x")

        ctk.CTkLabel(
            row1,
            text=str(pharmacy_name),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white",
            anchor="e",
            justify="right"
        ).pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            row1,
            text=f"#{order_id}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#bdbdbd"
        ).pack(side="left", padx=(8, 0))

        # Row 2: total + date
        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x", pady=(6, 0))

        ctk.CTkLabel(
            row2,
            text=self.ar(f"الإجمالي: {self.format_money(total)} جنيه"),
            font=ctk.CTkFont(size=12),
            text_color="#cfcfcf",
            anchor="e",
            justify="right"
        ).pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            row2,
            text=self.ar(f"التاريخ: {date_text}"),
            font=ctk.CTkFont(size=12),
            text_color="#9e9e9e"
        ).pack(side="left")

        # Status line
        ctk.CTkLabel(
            inner,
            text=self.ar(status_ar),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=status_color,
            anchor="e",
            justify="right"
        ).pack(fill="x", pady=(8, 0))

        def on_click(_event=None, oid=order.get("id")):
            if oid is None:
                return
            self.select_order(oid)

        for w in (card, inner, row1, row2):
            try:
                w.bind("<Button-1>", on_click)
            except Exception:
                pass
        for label in inner.winfo_children():
            try:
                label.bind("<Button-1>", on_click)
            except Exception:
                pass
        for label in row1.winfo_children():
            try:
                label.bind("<Button-1>", on_click)
            except Exception:
                pass
        for label in row2.winfo_children():
            try:
                label.bind("<Button-1>", on_click)
            except Exception:
                pass

        oid = order.get("id")
        if oid is not None:
            self.order_cards[oid] = card

    def select_order(self, order_id):
        """Select an order and render its details on the right."""
        self.selected_order_id = order_id

        # Highlight selection
        for oid, card in list(self.order_cards.items()):
            try:
                card.configure(fg_color="#3a4a3a" if oid == order_id else "#2d2d2d")
            except Exception:
                pass

        self.show_order_details(order_id)

    def _extract_pharmacy_info(self, order):
        pharmacy = order.get("pharmacy") if isinstance(order.get("pharmacy"), dict) else {}
        name = (
            order.get("pharmacy_name")
            or pharmacy.get("name")
            or order.get("customer_name")
            or order.get("client_name")
            or "-"
        )
        phone = order.get("pharmacy_phone") or pharmacy.get("phone") or pharmacy.get("mobile") or "-"
        address = order.get("pharmacy_address") or pharmacy.get("address") or "-"
        balance = (
            order.get("pharmacy_balance")
            if order.get("pharmacy_balance") is not None
            else pharmacy.get("balance")
        )
        try:
            balance = float(balance)
        except Exception:
            balance = None
        return name, phone, address, balance

    def show_order_details(self, order_id):
        """Render order details in the right panel (master-detail)."""
        order = self.orders_by_id.get(order_id)
        if not order:
            self._clear_right_panel()
            return

        self._clear_right_panel()

        oid = order.get("id", order_id)
        status_ui = self.ui_status(order.get("status", "pending"))
        status_ar = self.translate_status(status_ui)
        status_color = self.get_status_color(status_ui)
        total = self.get_order_total(order)

        try:
            self.details_header_label.configure(
                text=self.ar(f"تفاصيل الطلب #{oid}"),
                text_color="white"
            )
        except Exception:
            pass

        # Pharmacy info card
        name, phone, address, balance = self._extract_pharmacy_info(order)
        info_inner = ctk.CTkFrame(self.pharmacy_info_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=14, pady=12)
        info_inner.grid_columnconfigure(0, weight=1)

        def info_line(label, value, row, color="white"):
            ctk.CTkLabel(
                info_inner,
                text=self.ar(f"{label}: {value}"),
                font=ctk.CTkFont(size=13),
                text_color=color,
                anchor="e",
                justify="right"
            ).grid(row=row, column=0, sticky="ew", pady=3)

        info_line("الصيدلية", name, 0, "#4CAF50")
        info_line("الهاتف", phone, 1, "white")
        info_line("العنوان", address, 2, "white")
        bal_text = "-" if balance is None else f"{self.format_money(balance)} جنيه"
        info_line("الرصيد الحالي", bal_text, 3, "#FF9800" if balance is not None and balance > 0 else "#bdbdbd")

        # Items table header
        header = ctk.CTkFrame(self.items_scroll, fg_color="#2a2a2a", corner_radius=10)
        header.pack(fill="x", padx=10, pady=(10, 6))

        cols = [
            (self.ar("المنتج"), 260),
            (self.ar("الكمية"), 90),
            (self.ar("السعر"), 120),
            (self.ar("الإجمالي"), 120),
        ]
        for text, width in cols:
            ctk.CTkLabel(
                header,
                text=text,
                width=width,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#4CAF50",
                anchor="center"
            ).pack(side="left", padx=6, pady=8)

        items = order.get("items", order.get("order_items", [])) or []
        if not items:
            ctk.CTkLabel(
                self.items_scroll,
                text=self.ar("لا توجد منتجات داخل هذا الطلب"),
                font=ctk.CTkFont(size=13),
                text_color="#9e9e9e"
            ).pack(pady=30)
        else:
            for item in items:
                name_i = self.get_item_name(item)
                qty = item.get("quantity", 0)
                try:
                    qty = int(qty)
                except Exception:
                    qty = 0
                price = self.get_item_price(item)
                row_total = self.get_item_total(item)

                row = ctk.CTkFrame(self.items_scroll, fg_color="#333333", corner_radius=10)
                row.pack(fill="x", padx=10, pady=5)

                ctk.CTkLabel(row, text=str(name_i), width=260, text_color="white", anchor="e", justify="right").pack(side="left", padx=6, pady=8)
                ctk.CTkLabel(row, text=str(qty), width=90, text_color="white").pack(side="left", padx=6, pady=8)
                ctk.CTkLabel(row, text=self.format_money(price), width=120, text_color="white").pack(side="left", padx=6, pady=8)
                ctk.CTkLabel(row, text=self.format_money(row_total), width=120, text_color="#4CAF50").pack(side="left", padx=6, pady=8)

        # Summary
        summary_inner = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        summary_inner.pack(fill="x", padx=14, pady=12)
        summary_inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            summary_inner,
            text=self.ar(f"الإجمالي الكلي: {self.format_money(total)} جنيه"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right"
        ).grid(row=0, column=0, sticky="ew", pady=2)

        status_badge = ctk.CTkFrame(summary_inner, fg_color="transparent")
        status_badge.grid(row=1, column=0, sticky="e", pady=(6, 0))
        ctk.CTkLabel(
            status_badge,
            text=self.ar(f"الحالة: {status_ar}"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=status_color,
            anchor="e",
            justify="right"
        ).pack(side="right")

        # Actions
        for widget in list(self.actions_frame.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass

        if self.can_manage_orders():
            # Required logic:
            # - pending: review(approve_order) + reject(reject_order)
            # - approved: deliver(complete_order)
            # - completed/rejected: no actions
            if status_ui == "pending":
                ctk.CTkButton(
                    self.actions_frame,
                    text=self.ar("مراجعة"),
                    width=140,
                    height=36,
                    fg_color="#4CAF50",
                    hover_color="#45a049",
                    command=lambda o=order: self.approve_order(o)
                ).pack(side="right", padx=6)

                ctk.CTkButton(
                    self.actions_frame,
                    text=self.ar("رفض"),
                    width=120,
                    height=36,
                    fg_color="#f44336",
                    hover_color="#d32f2f",
                    command=lambda o=order: self.reject_order(o)
                ).pack(side="right", padx=6)

            elif status_ui == "approved":
                ctk.CTkButton(
                    self.actions_frame,
                    text=self.ar("تسليم"),
                    width=140,
                    height=36,
                    fg_color="#9C27B0",
                    hover_color="#7B1FA2",
                    command=lambda oid=oid: self.complete_order(oid)
                ).pack(side="right", padx=6)

        # Always allow printing in details
        ctk.CTkButton(
            self.actions_frame,
            text=self.ar("طباعة"),
            width=120,
            height=36,
            fg_color="#607D8B",
            hover_color="#455A64",
            command=lambda o=order: self.print_order_invoice(o)
        ).pack(side="left", padx=6)

    def create_order_headers(self):
        """Create table headers"""
        header = ctk.CTkFrame(self.table_frame, fg_color="#1f1f1f", corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 4))

        headers = [
            {"text": "#", "width": 35, "col": 0},
            {"text": "طلب", "width": 55, "col": 1},
            {"text": "الصيدلية", "width": 125, "col": 2},
            {"text": "الإجمالي", "width": 90, "col": 3},
            {"text": "الحالة", "width": 95, "col": 4},
            {"text": "الإجراءات", "width": 275, "col": 5}
        ]

        for header_info in headers:
            ctk.CTkLabel(
                header,
                text=self.ar(header_info["text"]) if header_info["text"] != "#" else "#",
                width=header_info["width"],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#4CAF50"
            ).grid(row=0, column=header_info["col"], padx=4, pady=8)

    def create_order_row(self, order):
        """Create a row for an order"""
        row = ctk.CTkFrame(self.table_frame, fg_color="#3a3a3a", corner_radius=8)
        row.pack(fill="x", padx=8, pady=4)

        order_id = order.get("id", "-")
        order_number = order.get("order_number", f"ORD-{order_id}")
        total = self.get_order_total(order)
        status = self.normalize_status(order.get("status", "pending"))
        status_arabic = self.translate_status(status)
        status_color = self.get_status_color(status)
        pharmacy_name = self.get_pharmacy_name(order)
        payment_status, amount_paid, remaining = self.get_order_payment_summary(order)
        payment_text = self.translate_payment_status(payment_status)
        payment_color = self.get_payment_status_color(payment_status)
        
        # Serial number
        idx = len(self.table_frame.winfo_children()) - 1
        
        # Order serial
        ctk.CTkLabel(
            row,
            text=str(idx + 1),
            width=35,
            text_color="white"
        ).grid(row=0, column=0, padx=4, pady=8)
        
        # Order ID
        ctk.CTkLabel(
            row,
            text=str(order_id),
            width=55,
            text_color="white"
        ).grid(row=0, column=1, padx=4, pady=8)

        # Pharmacy Name
        ctk.CTkLabel(
            row,
            text=str(pharmacy_name),
            width=125,
            text_color="white",
            anchor="e",
            justify="right"
        ).grid(row=0, column=2, padx=4, pady=8)

        # Total
        ctk.CTkLabel(
            row,
            text=f"{self.format_money(total)}",
            width=90,
            text_color="white"
        ).grid(row=0, column=3, padx=4, pady=8)

        # Status
        ctk.CTkLabel(
            row,
            text=self.ar(status_arabic),
            width=95,
            text_color=status_color,
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=4, padx=4, pady=8)

        ctk.CTkLabel(
            row,
            text=self.ar(payment_text),
            text_color=payment_color,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="e",
            justify="right",
        ).grid(row=1, column=3, columnspan=2, padx=8, pady=(0, 4), sticky="ew")

        delivery_person = (order.get("delivery_person") or "").strip()
        notes = (order.get("notes") or "").strip()
        if delivery_person or notes or status == "on_the_way" or payment_status != "unpaid" or remaining > 0:
            meta_parts = []
            if delivery_person:
                meta_parts.append(f"المندوب: {delivery_person}")
            if notes:
                meta_parts.append(f"ملاحظات: {notes}")
            if status == "on_the_way":
                meta_parts.append(self.get_delivery_note(order))
            meta_parts.append(f"الدفع: {payment_text}")
            meta_parts.append(f"مدفوع: {self.format_money(amount_paid)}")
            meta_parts.append(f"متبقي: {self.format_money(remaining)}")
            ctk.CTkLabel(
                row,
                text=self.ar(" | ".join(meta_parts)),
                text_color="#bdbdbd",
                font=ctk.CTkFont(size=11),
                anchor="e",
                justify="right",
                wraplength=360,
            ).grid(row=1, column=2, columnspan=3, padx=8, pady=(0, 8), sticky="ew")

        # Actions Frame
        actions_frame = ctk.CTkFrame(row, fg_color="transparent", width=275, height=30)
        actions_frame.grid(row=0, column=5, padx=4, pady=8)
        actions_frame.grid_propagate(False)
        actions_frame.pack_propagate(False)

        # Status action buttons
        if not self.can_manage_orders():
            ctk.CTkLabel(
                actions_frame,
                text=self.ar("عرض فقط"),
                width=62,
                text_color="#9e9e9e",
                font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=2)
        elif status == "pending":
            approve_btn = ctk.CTkButton(
                actions_frame,
                text=self.ar("مراجعة"),
                width=92,
                height=28,
                fg_color="#2196F3",
                hover_color="#1976D2",
                command=lambda o=order: self.approve_order(o)
            )
            approve_btn.pack(side="left", padx=2)

            reject_btn = ctk.CTkButton(
                actions_frame,
                text=self.ar("إلغاء"),
                width=62,
                height=28,
                fg_color="#f44336",
                hover_color="#d32f2f",
                command=lambda o=order: self.reject_order(o)
            )
            reject_btn.pack(side="left", padx=2)
            
            edit_btn = ctk.CTkButton(
                actions_frame,
                text=self.ar("تعديل"),
                width=54,
                height=28,
                fg_color="#FF9800",
                hover_color="#F57C00",
                command=lambda o=order: self.show_create_order_dialog(o)
            )
            edit_btn.pack(side="left", padx=2)
        elif status == "reviewed":
            in_store_btn = ctk.CTkButton(
                actions_frame,
                text=self.ar("المخزن"),
                width=70,
                height=28,
                fg_color="#5E35B1",
                hover_color="#4527A0",
                command=lambda oid=order_id: self.change_order_status(oid, "in_store", "نقل الطلب إلى المخزن؟")
            )
            in_store_btn.pack(side="left", padx=2)
        elif status == "in_store":
            ctk.CTkButton(
                actions_frame,
                text=self.ar("مندوب"),
                width=62,
                height=28,
                fg_color="#00BCD4",
                hover_color="#0097A7",
                command=lambda oid=order_id: self.change_order_status(oid, "with_driver", "تسليم الطلب للمندوب؟")
            ).pack(side="left", padx=2)
        elif status == "with_driver":
            ctk.CTkButton(
                actions_frame,
                text=self.ar("في الطريق"),
                width=78,
                height=28,
                fg_color="#8BC34A",
                hover_color="#689F38",
                command=lambda oid=order_id: self.change_order_status(oid, "on_the_way", "تأكيد أن الطلب في الطريق؟")
            ).pack(side="left", padx=2)
        elif status == "on_the_way":
            ctk.CTkButton(
                actions_frame,
                text=self.ar("تسليم"),
                width=58,
                height=28,
                fg_color="#4CAF50",
                hover_color="#45a049",
                command=lambda oid=order_id: self.change_order_status(oid, "delivered", "تأكيد تسليم الطلب؟")
            ).pack(side="left", padx=2)
        elif status == "postponed":
            ctk.CTkButton(
                actions_frame,
                text=self.ar("استئناف"),
                width=70,
                height=28,
                fg_color="#2196F3",
                hover_color="#1976D2",
                command=lambda oid=order_id: self.change_order_status(oid, "reviewed", "استئناف الطلب؟")
            ).pack(side="left", padx=2)
        elif status == "delivered":
            ctk.CTkLabel(
                actions_frame,
                text=self.ar("مكتمل"),
                width=58,
                text_color="#4CAF50",
                font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=2)
        elif status == "cancelled":
            ctk.CTkLabel(
                actions_frame,
                text=self.ar("ملغي"),
                width=62,
                text_color="#f44336",
                font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=2)

        if self.can_manage_orders() and status in ("reviewed", "in_store", "with_driver", "on_the_way"):
            ctk.CTkButton(
                actions_frame,
                text=self.ar("تأجيل"),
                width=54,
                height=28,
                fg_color="#8D6E63",
                hover_color="#6D4C41",
                command=lambda oid=order_id: self.change_order_status(oid, "postponed", "تأجيل الطلب؟")
            ).pack(side="left", padx=2)

        # Details Button
        details_btn = ctk.CTkButton(
            actions_frame,
            text=self.ar("تفاصيل"),
            width=58,
            height=28,
            fg_color="#2196F3",
            hover_color="#0b7dda",
            command=lambda oid=order_id: self.select_order(oid) if hasattr(self, "select_order") else None
        )
        details_btn.pack(side="left", padx=2)
        
        # Print Button
        print_btn = ctk.CTkButton(
            actions_frame,
            text=self.ar("طباعة"),
            width=50,
            height=28,
            fg_color="#607D8B",
            hover_color="#455A64",
            command=lambda o=order: self.print_order_invoice(o)
        )
        print_btn.pack(side="left", padx=2)

    # ==========================================
    # Order Actions
    # ==========================================

    def approve_order(self, order):
        """Approve an order"""
        if not self.can_manage_orders():
            self.show_permission_denied()
            return
        order_id = order.get("id")
        if not order_id:
            self.show_error("لا يمكن تحديد رقم الطلب")
            return

        if order_id in self.processing_orders:
            return

        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return

        if not messagebox.askyesno("تأكيد", f"هل تريد تسجيل مراجعة الطلب رقم {order_id}؟"):
            return

        try:
            self.processing_orders.add(order_id)
            self.update_status(f"جاري تسجيل مراجعة الطلب {order_id}...")

            result = self.api_client.update_order_status(order_id, "reviewed")

            if result:
                self.show_info(f"✅ تمت مراجعة الطلب رقم {order_id}")
                self.load_orders()
                self.update_status(f"✅ تمت مراجعة الطلب {order_id}")
            else:
                self.show_error("فشل تسجيل مراجعة الطلب. قد تكون الكمية غير متوفرة.")
                self.update_status("❌ فشل تحديث حالة الطلب")

        except Exception as e:
            if "stock" in str(e).lower() or "quantity" in str(e).lower():
                self.show_error(f"لا توجد كمية كافية من المنتج في المخزون.\n\n{str(e)}")
            else:
                self.show_error(f"حدث خطأ أثناء تحديث حالة الطلب:\n{str(e)}")
            self.update_status("❌ خطأ في تحديث حالة الطلب")
        finally:
            self.processing_orders.discard(order_id)

    def reject_order(self, order):
        """Reject an order"""
        if not self.can_manage_orders():
            self.show_permission_denied()
            return
        order_id = order.get("id")
        if not order_id:
            self.show_error("لا يمكن تحديد رقم الطلب")
            return

        if order_id in self.processing_orders:
            return

        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return

        if not messagebox.askyesno("تأكيد", f"هل تريد إلغاء الطلب رقم {order_id}؟"):
            return

        try:
            self.processing_orders.add(order_id)
            self.update_status(f"جاري إلغاء الطلب {order_id}...")

            result = self.api_client.update_order_status(order_id, "cancelled")

            if result:
                self.show_info(f"✅ تم إلغاء الطلب رقم {order_id}")
                self.load_orders()
                self.update_status(f"✅ تم إلغاء الطلب {order_id}")
            else:
                self.show_error("فشل إلغاء الطلب. تأكد من اتصال السيرفر.")
                self.update_status("❌ فشل إلغاء الطلب")

        except Exception as e:
            self.show_error(f"حدث خطأ أثناء إلغاء الطلب:\n{str(e)}")
            self.update_status("❌ خطأ في إلغاء الطلب")
        finally:
            self.processing_orders.discard(order_id)

    def change_order_status(self, order_id, new_status, confirm_message):
        """Generic safe status transition for the new order workflow."""
        if not self.can_manage_orders():
            self.show_permission_denied()
            return
        if not order_id:
            self.show_error("لا يمكن تحديد رقم الطلب")
            return

        if order_id in self.processing_orders:
            return

        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return

        if not messagebox.askyesno("تأكيد", f"{confirm_message} رقم الطلب: {order_id}"):
            return

        try:
            self.processing_orders.add(order_id)
            target_text = self.translate_status(new_status)
            self.update_status(f"جاري تحديث الطلب {order_id} إلى {target_text}...")

            result = self.api_client.update_order_status(order_id, new_status)

            if result:
                self.show_info(f"✅ تم تحديث الطلب رقم {order_id} إلى {target_text}")
                self.load_orders()
                self.update_status(f"✅ تم تحديث الطلب {order_id}")
            else:
                self.show_error("فشل تحديث حالة الطلب. تأكد من اتصال السيرفر وحالة الطلب.")
                self.update_status("❌ فشل تحديث حالة الطلب")
        except Exception as e:
            self.show_error(f"حدث خطأ أثناء تحديث حالة الطلب:\n{str(e)}")
            self.update_status("❌ خطأ في تحديث حالة الطلب")
        finally:
            self.processing_orders.discard(order_id)

    def review_order(self, order_id):
        """Compatibility wrapper: move reviewed order to store stage."""
        self.change_order_status(order_id, "in_store", "نقل الطلب إلى المخزن؟")

    def complete_order(self, order_id):
        """Compatibility wrapper: mark an on-the-way order as delivered."""
        self.change_order_status(order_id, "delivered", "تأكيد تسليم الطلب؟")

    # ==========================================
    # Order Details Dialog
    # ==========================================

    def show_order_details_dialog(self, order):
        """Show order details in a new window (legacy dialog)."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"تفاصيل الطلب #{order.get('id', '-')}")
        dialog.geometry("850x700")
        dialog.minsize(800, 600)
        dialog.resizable(True, True)

        dialog.transient(self)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        main_frame = ctk.CTkFrame(dialog, fg_color="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title with order number
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            title_frame,
            text=f"تفاصيل الطلب #{order.get('id', '-')}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        ).pack(side="left")
        
        # Order status badge
        status = self.normalize_status(order.get("status", "pending"))
        status_arabic = self.translate_status(status)
        status_color = self.get_status_color(status)
        
        status_badge = ctk.CTkFrame(title_frame, fg_color=status_color, corner_radius=20)
        status_badge.pack(side="right", padx=10)
        
        ctk.CTkLabel(
            status_badge,
            text=status_arabic,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        ).pack(padx=15, pady=5)

        # Order Info Frame
        info_frame = ctk.CTkFrame(main_frame, fg_color="#2d2d2d", corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 20))
        
        # 2x2 grid for info
        info_frame.grid_columnconfigure((0, 1), weight=1)

        # Order Number
        order_number = order.get("order_number", "-")
        ctk.CTkLabel(
            info_frame,
            text=f"📋 رقم الطلب: {order_number}",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=0, column=0, padx=15, pady=10, sticky="w")

        # Pharmacy Name
        pharmacy_name = self.get_pharmacy_name(order)
        ctk.CTkLabel(
            info_frame,
            text=f"🏥 الصيدلية: {pharmacy_name}",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=0, column=1, padx=15, pady=10, sticky="w")

        # Date
        created_at = self.format_date_display(self.get_order_date(order))
        ctk.CTkLabel(
            info_frame,
            text=f"📅 التاريخ: {created_at}",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=1, column=0, padx=15, pady=10, sticky="w")

        # Total
        total = self.get_order_total(order)
        ctk.CTkLabel(
            info_frame,
            text=f"💰 الإجمالي: {self.format_money(total)} جنيه",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4CAF50"
        ).grid(row=1, column=1, padx=15, pady=10, sticky="w")

        payment_status, amount_paid, remaining = self.get_order_payment_summary(order)
        payment_text = self.translate_payment_status(payment_status)
        payment_color = self.get_payment_status_color(payment_status)
        ctk.CTkLabel(
            info_frame,
            text=f"حالة الدفع: {payment_text}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=payment_color
        ).grid(row=2, column=0, padx=15, pady=10, sticky="w")
        ctk.CTkLabel(
            info_frame,
            text=f"مدفوع: {self.format_money(amount_paid)} | متبقي: {self.format_money(remaining)} جنيه",
            font=ctk.CTkFont(size=14),
            text_color="#bdbdbd"
        ).grid(row=2, column=1, padx=15, pady=10, sticky="w")

        discount = self.safe_float(order.get("discount", 0))
        discount_type = order.get("discount_type", "value")
        if discount > 0:
            original_total = self.safe_float(order.get("total_amount", total))
            discount_text = f"{discount:.2f}%" if discount_type == "percent" else f"{self.format_money(discount)} جنيه"
            ctk.CTkLabel(
                info_frame,
                text=f"🏷️ الخصم: {discount_text}",
                font=ctk.CTkFont(size=14),
                text_color="#FF9800"
            ).grid(row=3, column=0, padx=15, pady=10, sticky="w")
            ctk.CTkLabel(
                info_frame,
                text=f"قبل الخصم: {self.format_money(original_total)} جنيه",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            ).grid(row=3, column=1, padx=15, pady=10, sticky="w")

        delivery_person = (order.get("delivery_person") or "").strip()
        notes = (order.get("notes") or "").strip()
        last_update = order.get("last_status_update") or "-"
        if hasattr(last_update, "strftime"):
            last_update = last_update.strftime("%Y-%m-%d %H:%M")
        elif isinstance(last_update, str) and len(last_update) > 16:
            last_update = last_update[:16]

        if delivery_person:
            ctk.CTkLabel(
                info_frame,
                text=f"🚚 المندوب: {delivery_person}",
                font=ctk.CTkFont(size=14),
                text_color="#00BCD4"
            ).grid(row=4, column=0, padx=15, pady=10, sticky="w")

        if last_update and last_update != "-":
            ctk.CTkLabel(
                info_frame,
                text=f"آخر تحديث: {last_update}",
                font=ctk.CTkFont(size=14),
                text_color="#bdbdbd"
            ).grid(row=4, column=1, padx=15, pady=10, sticky="w")

        if notes:
            ctk.CTkLabel(
                info_frame,
                text=f"ملاحظات: {notes}",
                font=ctk.CTkFont(size=14),
                text_color="#FF9800",
                wraplength=700,
                anchor="w",
                justify="right"
            ).grid(row=5, column=0, columnspan=2, padx=15, pady=10, sticky="ew")

        if status == "on_the_way":
            ctk.CTkLabel(
                info_frame,
                text=self.get_delivery_note(order),
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#CDDC39",
                wraplength=700,
                anchor="w",
                justify="right"
            ).grid(row=6, column=0, columnspan=2, padx=15, pady=10, sticky="ew")

        # Products Frame
        products_label = ctk.CTkLabel(
            main_frame,
            text="المنتجات",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        products_label.pack(anchor="w", pady=(0, 10))

        products_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="#2d2d2d",
            height=350
        )
        products_frame.pack(fill="both", expand=True, pady=(0, 20))

        items = order.get("items", order.get("order_items", []))

        if not items:
            ctk.CTkLabel(
                products_frame,
                text="لا توجد منتجات في هذا الطلب",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            ).pack(pady=30)
        else:
            # Header
            header = ctk.CTkFrame(products_frame, fg_color="#1f1f1f", corner_radius=8)
            header.pack(fill="x", padx=10, pady=(10, 5))

            ctk.CTkLabel(
                header,
                text="#",
                width=40,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=0, padx=8, pady=8)

            ctk.CTkLabel(
                header,
                text="المنتج",
                width=250,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=1, padx=8, pady=8)

            ctk.CTkLabel(
                header,
                text="الكمية",
                width=100,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=2, padx=8, pady=8)

            ctk.CTkLabel(
                header,
                text="السعر",
                width=120,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=3, padx=8, pady=8)

            ctk.CTkLabel(
                header,
                text="الإجمالي",
                width=120,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=4, padx=8, pady=8)

            for idx, item in enumerate(items, 1):
                row = ctk.CTkFrame(products_frame, fg_color="#3a3a3a", corner_radius=8)
                row.pack(fill="x", padx=10, pady=5)

                product_name = self.get_item_name(item)
                quantity = item.get("quantity", 0)
                price = self.get_item_price(item)
                total_price = self.get_item_total(item)

                ctk.CTkLabel(
                    row,
                    text=str(idx),
                    width=40,
                    text_color="white"
                ).grid(row=0, column=0, padx=8, pady=8)

                ctk.CTkLabel(
                    row,
                    text=product_name,
                    width=250,
                    text_color="white",
                    anchor="w"
                ).grid(row=0, column=1, padx=8, pady=8)

                ctk.CTkLabel(
                    row,
                    text=str(quantity),
                    width=100,
                    text_color="white"
                ).grid(row=0, column=2, padx=8, pady=8)

                ctk.CTkLabel(
                    row,
                    text=f"{self.format_money(price)}",
                    width=120,
                    text_color="white"
                ).grid(row=0, column=3, padx=8, pady=8)

                ctk.CTkLabel(
                    row,
                    text=f"{self.format_money(total_price)}",
                    width=120,
                    text_color="#4CAF50"
                ).grid(row=0, column=4, padx=8, pady=8)

        # Action buttons based on current status
        if self.can_manage_orders() and status in ("pending", "reviewed", "in_store", "with_driver", "on_the_way", "postponed"):
            buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            buttons_frame.pack(fill="x", pady=(0, 10))

        if self.can_manage_orders() and status == "pending":
            
            approve_btn = ctk.CTkButton(
                buttons_frame,
                text=self.ar("تمت المراجعة"),
                width=150,
                height=40,
                fg_color="#2196F3",
                hover_color="#1976D2",
                command=lambda: [self.approve_order(order), dialog.destroy()]
            )
            approve_btn.pack(side="right", padx=10)
            
            reject_btn = ctk.CTkButton(
                buttons_frame,
                text=self.ar("إلغاء"),
                width=150,
                height=40,
                fg_color="#f44336",
                hover_color="#d32f2f",
                command=lambda: [self.reject_order(order), dialog.destroy()]
            )
            reject_btn.pack(side="right", padx=10)
        elif self.can_manage_orders() and status == "reviewed":
            next_btn = ctk.CTkButton(
                buttons_frame,
                text=self.ar("في المخزن"),
                width=150,
                height=40,
                fg_color="#5E35B1",
                hover_color="#4527A0",
                command=lambda oid=order.get("id"): [self.change_order_status(oid, "in_store", "نقل الطلب إلى المخزن؟"), dialog.destroy()]
            )
            next_btn.pack(side="right", padx=10)
        elif self.can_manage_orders() and status == "in_store":
            ctk.CTkButton(
                buttons_frame,
                text=self.ar("مع المندوب"),
                width=150,
                height=40,
                fg_color="#00BCD4",
                hover_color="#0097A7",
                command=lambda oid=order.get("id"): [self.change_order_status(oid, "with_driver", "تسليم الطلب للمندوب؟"), dialog.destroy()]
            ).pack(side="right", padx=10)
        elif self.can_manage_orders() and status == "with_driver":
            ctk.CTkButton(
                buttons_frame,
                text=self.ar("في الطريق إليك"),
                width=150,
                height=40,
                fg_color="#8BC34A",
                hover_color="#689F38",
                command=lambda oid=order.get("id"): [self.change_order_status(oid, "on_the_way", "تأكيد أن الطلب في الطريق؟"), dialog.destroy()]
            ).pack(side="right", padx=10)
        elif self.can_manage_orders() and status == "on_the_way":
            ctk.CTkButton(
                buttons_frame,
                text=self.ar("تم التسليم"),
                width=150,
                height=40,
                fg_color="#4CAF50",
                hover_color="#45a049",
                command=lambda oid=order.get("id"): [self.change_order_status(oid, "delivered", "تأكيد تسليم الطلب؟"), dialog.destroy()]
            ).pack(side="right", padx=10)
        elif self.can_manage_orders() and status == "postponed":
            ctk.CTkButton(
                buttons_frame,
                text=self.ar("استئناف"),
                width=150,
                height=40,
                fg_color="#2196F3",
                hover_color="#1976D2",
                command=lambda oid=order.get("id"): [self.change_order_status(oid, "reviewed", "استئناف الطلب؟"), dialog.destroy()]
            ).pack(side="right", padx=10)

        if self.can_manage_orders() and status in ("reviewed", "in_store", "with_driver", "on_the_way"):
            ctk.CTkButton(
                buttons_frame,
                text=self.ar("تأجيل"),
                width=120,
                height=40,
                fg_color="#8D6E63",
                hover_color="#6D4C41",
                command=lambda oid=order.get("id"): [self.change_order_status(oid, "postponed", "تأجيل الطلب؟"), dialog.destroy()]
            ).pack(side="right", padx=10)
        
        # Print button
        print_btn = ctk.CTkButton(
            main_frame,
            text="🖨️ طباعة الفاتورة",
            width=120,
            height=35,
            fg_color="#607D8B",
            hover_color="#455A64",
            command=lambda: self.print_order_invoice(order)
        )
        print_btn.pack(side="left")

        close_btn = ctk.CTkButton(
            main_frame,
            text="إغلاق",
            width=120,
            height=35,
            command=dialog.destroy
        )
        close_btn.pack(side="right")

    # ==========================================
    # Create Order Dialog
    # ==========================================

    def show_create_order_dialog(self, existing_order=None):
        """Show dialog to create or edit a pending order."""
        if not self.can_manage_orders():
            self.show_permission_denied()
            return
        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return

        try:
            self.pharmacies_cache = self.api_client.get_pharmacies()
        except Exception as e:
            self.show_error(f"فشل تحميل الصيدليات:\n{e}")
            return

        try:
            self.products_cache = self.api_client.get_products()
        except Exception as e:
            self.show_error(f"فشل تحميل المنتجات:\n{e}")
            return

        if not self.pharmacies_cache:
            self.show_warning("لا توجد صيدليات", "لا يمكن إنشاء طلب جديد لأن قائمة الصيدليات فارغة.")
            return

        if not self.products_cache:
            self.show_warning("لا توجد منتجات", "لا يمكن إنشاء طلب جديد لأن قائمة المنتجات فارغة.")
            return

        dialog = ctk.CTkToplevel(self)
        is_edit_mode = bool(existing_order)
        dialog.title("تعديل طلب" if is_edit_mode else "إنشاء طلب")
        dialog.geometry("1000x800")
        dialog.minsize(900, 650)
        dialog.resizable(True, True)

        dialog.transient(self)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        cart = []
        if existing_order:
            for item in existing_order.get("items", existing_order.get("order_items", [])):
                cart.append({
                    "product_id": item.get("product_id"),
                    "name": self.get_item_name(item),
                    "quantity": int(item.get("quantity", 0) or 0),
                    "price": self.get_item_price(item)
                })
        order_saved = False

        main_frame = ctk.CTkFrame(dialog, fg_color="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="تعديل الطلب" if is_edit_mode else "إنشاء طلب جديد",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#4CAF50"
        )
        title_label.grid(row=0, column=0, pady=(0, 20), sticky="w")

        # Form Frame
        form_frame = ctk.CTkFrame(main_frame, fg_color="#2d2d2d", corner_radius=10)
        form_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        form_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        # Pharmacy Select
        ctk.CTkLabel(
            form_frame,
            text="الصيدلية",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        pharmacy_options = [f"{p.get('id')} - {p.get('name', 'بدون اسم')}" for p in self.pharmacies_cache]
        selected_pharmacy_option = pharmacy_options[0] if pharmacy_options else ""
        if existing_order:
            existing_pharmacy_id = str(existing_order.get("pharmacy_id", ""))
            for option in pharmacy_options:
                if option.startswith(f"{existing_pharmacy_id} -"):
                    selected_pharmacy_option = option
                    break
        pharmacy_var = ctk.StringVar(value=selected_pharmacy_option)

        pharmacy_menu = ctk.CTkOptionMenu(
            form_frame,
            values=pharmacy_options,
            variable=pharmacy_var,
            width=200
        )
        pharmacy_menu.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        # Product Select
        ctk.CTkLabel(
            form_frame,
            text="المنتج",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).grid(row=0, column=1, padx=15, pady=(15, 5), sticky="w")

        # Searchable product selection
        product_var = ctk.StringVar()
        product_search_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="ابحث عن منتج...",
            width=200
        )
        product_search_entry.grid(row=1, column=1, padx=15, pady=(0, 15), sticky="w")
        
        
        product_menu = ctk.CTkOptionMenu(
            form_frame,
            values=[f"{p.get('id')} - {p.get('name', 'بدون اسم')}" for p in self.products_cache[:20]],
            variable=product_var,
            width=200
        )
        product_menu.grid(row=1, column=2, padx=15, pady=(0, 15), sticky="w")
        
        def filter_products(*args):
            search = product_search_entry.get().strip().lower()
            filtered = []
            for p in self.products_cache:
                name = p.get('name', '').lower()
                if search in name:
                    filtered.append(f"{p.get('id')} - {p.get('name', 'بدون اسم')}")
            if filtered:
                product_menu.configure(values=filtered[:20])
                if filtered:
                    product_var.set(filtered[0])
        
        product_search_entry.bind("<KeyRelease>", filter_products)

        # Price
        ctk.CTkLabel(
            form_frame,
            text="السعر",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).grid(row=0, column=3, padx=15, pady=(15, 5), sticky="w")

        price_var = ctk.StringVar(value="0")
        price_entry = ctk.CTkEntry(
            form_frame,
            textvariable=price_var,
            width=120,
            state="readonly"
        )
        price_entry.grid(row=1, column=3, padx=15, pady=(0, 15), sticky="w")

        # Quantity
        ctk.CTkLabel(
            form_frame,
            text="الكمية",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).grid(row=2, column=0, padx=15, pady=(5, 5), sticky="w")

        quantity_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="الكمية",
            width=120
        )
        quantity_entry.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")

        add_to_cart_btn = ctk.CTkButton(
            form_frame,
            text="➕ إضافة للسلة",
            width=150,
            height=35
        )
        add_to_cart_btn.grid(row=3, column=1, padx=15, pady=(0, 15), sticky="w")
        
        # Edit quantity in cart later is handled in render_cart
        ctk.CTkLabel(
            form_frame,
            text="الخصم",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).grid(row=2, column=2, padx=15, pady=(5, 5), sticky="w")
        
        discount_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="0",
            width=100
        )
        discount_entry.insert(0, str(existing_order.get("discount", 0) if existing_order else 0))
        discount_entry.grid(row=3, column=2, padx=15, pady=(0, 15), sticky="w")
        
        discount_type_var = ctk.StringVar(value=existing_order.get("discount_type", "value") if existing_order else "value")
        discount_type_menu = ctk.CTkOptionMenu(
            form_frame,
            values=["value", "percent"],
            variable=discount_type_var,
            width=100
        )
        discount_type_menu.grid(row=3, column=3, padx=15, pady=(0, 15), sticky="w")
        discount_entry.bind("<KeyRelease>", lambda _event: update_total_label())
        discount_type_menu.configure(command=lambda _value: update_total_label())

        # Cart Header
        cart_title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        cart_title_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        cart_title_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cart_title_frame,
            text="السلة",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        ).pack(side="left")

        total_label = ctk.CTkLabel(
            cart_title_frame,
            text="الإجمالي: 0.00 جنيه",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4CAF50"
        )
        total_label.pack(side="right")

        # Cart Frame
        cart_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="#2d2d2d"
        )
        cart_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 15))
        cart_frame.grid_columnconfigure(0, weight=1)

        # Buttons Frame
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))

        def get_selected_product():
            val = product_var.get()
            if not val:
                return None
            try:
                selected_id = int(val.split(" - ")[0])
                for product in self.products_cache:
                    if product.get("id") == selected_id:
                        return product
                return None
            except:
                return None

        def get_selected_pharmacy_id():
            val = pharmacy_var.get()
            if not val:
                return None
            try:
                return int(val.split(" - ")[0])
            except:
                return None

        def get_product_price(product):
            if not product:
                return 0
            price = product.get("price") or product.get("unit_price") or 0
            try:
                return float(price)
            except:
                return 0

        def update_price(*args):
            product = get_selected_product()
            price = get_product_price(product)
            price_entry.configure(state="normal")
            price_var.set(str(price))
            price_entry.configure(state="readonly")

        def calculate_total():
            return sum(item["quantity"] * item["price"] for item in cart)
        
        def get_discount_value():
            try:
                return max(float(discount_entry.get().strip() or 0), 0)
            except ValueError:
                return 0
        
        def calculate_final_total():
            total = calculate_total()
            discount = get_discount_value()
            if discount_type_var.get() == "percent":
                discount_amount = total * min(discount, 100) / 100
            else:
                discount_amount = min(discount, total)
            return max(total - discount_amount, 0)

        def update_total_label():
            total = calculate_total()
            final_total = calculate_final_total()
            total_label.configure(text=f"الإجمالي: {self.format_money(total)} | بعد الخصم: {self.format_money(final_total)} جنيه")

        def render_cart():
            for widget in cart_frame.winfo_children():
                widget.destroy()

            if not cart:
                ctk.CTkLabel(
                    cart_frame,
                    text="🛒 السلة فارغة",
                    font=ctk.CTkFont(size=15),
                    text_color="gray"
                ).pack(pady=30)
                update_total_label()
                return

            # Header
            header = ctk.CTkFrame(cart_frame, fg_color="#1f1f1f", corner_radius=8)
            header.pack(fill="x", padx=10, pady=(10, 5))

            ctk.CTkLabel(
                header,
                text="المنتج",
                width=280,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=0, padx=5, pady=8)

            ctk.CTkLabel(
                header,
                text="الكمية",
                width=100,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=1, padx=5, pady=8)

            ctk.CTkLabel(
                header,
                text="السعر",
                width=120,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=2, padx=5, pady=8)

            ctk.CTkLabel(
                header,
                text="الإجمالي",
                width=130,
                font=ctk.CTkFont(weight="bold"),
                text_color="white"
            ).grid(row=0, column=3, padx=5, pady=8)

            ctk.CTkLabel(
                header,
                text="",
                width=160
            ).grid(row=0, column=4, padx=5, pady=8)

            for index, item in enumerate(cart):
                row = ctk.CTkFrame(cart_frame, fg_color="#3a3a3a", corner_radius=8)
                row.pack(fill="x", padx=10, pady=5)

                subtotal = item["quantity"] * item["price"]

                ctk.CTkLabel(
                    row,
                    text=item["name"][:35],
                    width=280,
                    text_color="white",
                    anchor="w"
                ).grid(row=0, column=0, padx=5, pady=8)

                # Quantity with +/- buttons
                qty_frame = ctk.CTkFrame(row, fg_color="transparent")
                qty_frame.grid(row=0, column=1, padx=5, pady=8)
                
                qty_label = ctk.CTkLabel(
                    qty_frame,
                    text=str(item["quantity"]),
                    width=40,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color="white"
                )
                qty_label.pack(side="left", padx=5)
                
                def dec_qty(i=index):
                    if cart[i]["quantity"] > 1:
                        cart[i]["quantity"] -= 1
                        render_cart()
                
                def inc_qty(i=index):
                    cart[i]["quantity"] += 1
                    render_cart()
                
                dec_btn = ctk.CTkButton(
                    qty_frame,
                    text="-",
                    width=30,
                    height=25,
                    command=dec_qty
                )
                dec_btn.pack(side="left")
                
                inc_btn = ctk.CTkButton(
                    qty_frame,
                    text="+",
                    width=30,
                    height=25,
                    command=inc_qty
                )
                inc_btn.pack(side="left")

                ctk.CTkLabel(
                    row,
                    text=f"{self.format_money(item['price'])}",
                    width=120,
                    text_color="white"
                ).grid(row=0, column=2, padx=5, pady=8)

                ctk.CTkLabel(
                    row,
                    text=f"{self.format_money(subtotal)}",
                    width=130,
                    text_color="#4CAF50"
                ).grid(row=0, column=3, padx=5, pady=8)

                delete_btn = ctk.CTkButton(
                    row,
                    text="🗑️ حذف",
                    width=70,
                    height=30,
                    fg_color="#f44336",
                    hover_color="#d32f2f",
                    command=lambda i=index: remove_from_cart(i)
                )
                delete_btn.grid(row=0, column=4, padx=5, pady=8)

            update_total_label()

        def add_to_cart():
            product = get_selected_product()
            if not product:
                self.show_error("اختر منتج صحيح.")
                return

            quantity_text = quantity_entry.get().strip()
            try:
                quantity = int(quantity_text)
                if quantity <= 0:
                    raise ValueError
            except:
                self.show_error("الكمية غير صحيحة. اكتب رقم أكبر من صفر.")
                return

            product_id = product.get("id")
            product_name = product.get("name", "منتج بدون اسم")
            price = get_product_price(product)

            if price <= 0:
                self.show_error("سعر المنتج غير صحيح.")
                return

            for item in cart:
                if item["product_id"] == product_id:
                    item["quantity"] += quantity
                    render_cart()
                    quantity_entry.delete(0, "end")
                    return

            cart.append({
                "product_id": product_id,
                "name": product_name,
                "quantity": quantity,
                "price": price
            })

            quantity_entry.delete(0, "end")
            render_cart()

        def remove_from_cart(index):
            if 0 <= index < len(cart):
                cart.pop(index)
                render_cart()

        def finish_order():
            dialog.destroy()
            self.load_orders()
            if self.status_callback:
                self.status_callback("✅ تم حفظ الطلب")

        def submit_order():
            nonlocal order_saved

            if order_saved:
                return

            if not cart:
                self.show_error("السلة فاضية. أضف منتج واحد على الأقل.")
                return

            pharmacy_id = get_selected_pharmacy_id()
            if not pharmacy_id:
                self.show_error("اختر صيدلية صحيحة.")
                return

            items = []
            for item in cart:
                items.append({
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "price": item["price"]
                })

            if not self.check_server_health():
                self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
                return

            try:
                self.update_status("جاري حفظ الطلب...")
                save_button.configure(text="جاري الحفظ...", state="disabled")
                discount = get_discount_value()
                discount_type = discount_type_var.get()
                if is_edit_mode:
                    result = self.api_client.update_order(existing_order.get("id"), pharmacy_id, items, discount, discount_type)
                else:
                    result = self.api_client.create_order(pharmacy_id, items, discount, discount_type)

                if result:
                    order_saved = True
                    self.show_info("✅ تم حفظ الطلب بنجاح")

                    save_button.configure(state="disabled", text="تم الحفظ ✅")
                    cancel_button.configure(text="✔ تم", fg_color="#4CAF50", hover_color="#45a049", command=finish_order)
                    add_to_cart_btn.configure(state="disabled")
                    pharmacy_menu.configure(state="disabled")
                    product_menu.configure(state="disabled")
                    product_search_entry.configure(state="disabled")
                    quantity_entry.configure(state="disabled")

                    self.update_status("✅ تم حفظ الطلب")

                else:
                    self.show_error("فشل حفظ الطلب.")
                    save_button.configure(state="normal", text="💾 حفظ الطلب")
                    self.update_status("❌ فشل حفظ الطلب")

            except Exception as e:
                self.show_error(f"فشل حفظ الطلب:\n{e}")
                save_button.configure(state="normal", text="💾 حفظ الطلب")
                self.update_status("❌ خطأ في حفظ الطلب")

        add_to_cart_btn.configure(command=add_to_cart)
        product_search_entry.bind("<KeyRelease>", lambda e: update_price())
        product_menu.configure(command=lambda v: update_price())
        update_price()

        save_button = ctk.CTkButton(
            buttons_frame,
            text="💾 حفظ الطلب",
            width=150,
            height=40,
            command=submit_order
        )
        save_button.pack(side="right", padx=10)

        cancel_button = ctk.CTkButton(
            buttons_frame,
            text="✖ إلغاء",
            width=120,
            height=40,
            fg_color="#777777",
            hover_color="#666666",
            command=dialog.destroy
        )
        cancel_button.pack(side="right", padx=10)

        render_cart()
