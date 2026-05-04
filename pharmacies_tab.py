"""
Pharmacies Tab for Pharmacy Management System
Displays and manages pharmacies with CRUD operations
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime
from api_client import APIClient
import urllib.parse
import webbrowser


class PharmaciesTab(ctk.CTkFrame):
    """
    Pharmacies management tab
    """
    
    def __init__(self, master, api_client=None, status_callback=None, role="admin"):
        super().__init__(master)
        
        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.role = role or "admin"
        self.selected_pharmacy = None
        self.selected_row = None
        
        # Configure frame
        self.configure(fg_color="#1e1e1e")
        
        # Create UI
        self.create_ui()
        
        # Load data
        self.load_pharmacies()

    def can_manage_pharmacies(self):
        return self.role == "admin"

    def show_permission_denied(self):
        self.show_warning("هذه العملية غير متاحة لهذا الدور")
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
    def safe_float(self, value, field_name="الرصيد"):
        """Convert value to float safely"""
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} يجب أن يكون رقماً صحيحاً")
    
    def get_pharmacy_balance(self, pharmacy):
        """Get pharmacy balance safely"""
        balance = pharmacy.get("balance", 0.0)
        try:
            return float(balance)
        except (ValueError, TypeError):
            return 0.0
    
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
        """Format money safely."""
        try:
            return f"{float(value):,.2f}"
        except (ValueError, TypeError):
            return "0.00"
    
    def parse_datetime(self, value):
        """Parse API date values safely for sorting."""
        if not value:
            return datetime.min
        
        if hasattr(value, "strftime"):
            return value
        
        text = str(value).strip().replace("Z", "")
        text = text.replace("T", " ").split(".")[0]
        
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        
        try:
            return datetime.fromisoformat(str(value).replace("Z", ""))
        except (ValueError, TypeError):
            return datetime.min
    
    def format_date(self, value):
        """Format date for display."""
        parsed = self.parse_datetime(value)
        if parsed == datetime.min:
            return "-"
        return parsed.strftime("%Y-%m-%d %H:%M")
    
    def get_order_total(self, order):
        """Get order total safely."""
        total = order.get("total", order.get("total_amount", order.get("total_price", 0)))
        try:
            return float(total)
        except (ValueError, TypeError):
            return 0.0
    
    def get_order_date(self, order):
        """Get order date safely."""
        return order.get("order_date") or order.get("created_at") or order.get("date") or ""
    
    # ==========================================
    # UI Creation Methods
    # ==========================================
    
    def create_ui(self):
        """Create the user interface"""
        
        # Top frame for search and buttons
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        # Search section
        search_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        search_frame.pack(side="left", fill="x", expand=True)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍  بحث باسم الصيدلية أو الهاتف...",
            width=250,
            height=35,
            font=("Arial", 13)
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.search_pharmacies())
        
        self.search_btn = ctk.CTkButton(
            search_frame,
            text="بحث",
            width=80,
            height=35,
            font=("Arial", 12, "bold"),
            command=self.search_pharmacies
        )
        self.search_btn.pack(side="left", padx=(0, 10))
        
        # Refresh button
        self.refresh_btn = ctk.CTkButton(
            search_frame,
            text="تحديث",
            width=80,
            height=35,
            font=("Arial", 12, "bold"),
            fg_color="#2d2d2d",
            hover_color="#3d3d3d",
            command=self.load_pharmacies
        )
        self.refresh_btn.pack(side="left")
        
        # Add pharmacy button
        self.add_btn = ctk.CTkButton(
            self.top_frame,
            text="+ إضافة صيدلية",
            width=150,
            height=35,
            font=("Arial", 12, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.show_add_dialog
        )
        self.add_btn.pack(side="right")
        if not self.can_manage_pharmacies():
            self.add_btn.configure(state="disabled")
        
        # Scrollable frame for pharmacies table
        self.table_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#2d2d2d",
            corner_radius=10
        )
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=(10, 8))
        
        # Table headers
        self.create_headers()
        
        # Dictionary to store pharmacy rows
        self.rows = {}
        self.all_pharmacies = []  # Store all pharmacies for local search
        
        # Fixed action bar below the table.
        self.create_actions_bar()
    
    def create_headers(self):
        """Create table headers"""
        headers_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
        headers_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        headers = [
            {"text": "ID", "width": 60},
            {"text": "اسم الصيدلية", "width": 200},
            {"text": "الحالة", "width": 110},
            {"text": "الهاتف", "width": 150},
            {"text": "العنوان", "width": 250},
            {"text": "الرصيد", "width": 120}
        ]
        
        self.header_labels = []
        for header in headers:
            label = ctk.CTkLabel(
                headers_frame,
                text=header["text"],
                width=header["width"],
                font=("Arial", 14, "bold"),
                text_color="#4CAF50",
                anchor="center"
            )
            label.pack(side="left", padx=5, pady=5)
            self.header_labels.append(label)
        
        separator = ctk.CTkFrame(self.table_frame, height=2, fg_color="#3d3d3d")
        separator.pack(fill="x", padx=10, pady=(0, 10))
    
    def create_actions_bar(self):
        """Create fixed action buttons below the table."""
        self.actions_bar = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=10)
        self.actions_bar.pack(fill="x", padx=20, pady=(0, 20))
        
        self.selected_label = ctk.CTkLabel(
            self.actions_bar,
            text="اختر صيدلية من الجدول",
            font=("Arial", 13, "bold"),
            text_color="#bdbdbd",
            anchor="e"
        )
        self.selected_label.pack(side="right", padx=15, pady=12)
        
        buttons_frame = ctk.CTkFrame(self.actions_bar, fg_color="transparent")
        buttons_frame.pack(side="left", padx=15, pady=10)
        
        self.edit_selected_btn = ctk.CTkButton(
            buttons_frame,
            text="تعديل",
            width=100,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#2196F3",
            hover_color="#1976D2",
            command=self.edit_selected_pharmacy
        )
        self.edit_selected_btn.pack(side="left", padx=5)
        
        self.delete_selected_btn = ctk.CTkButton(
            buttons_frame,
            text="سحب صلاحية",
            width=100,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#f44336",
            hover_color="#d32f2f",
            command=self.delete_selected_pharmacy
        )
        self.delete_selected_btn.pack(side="left", padx=5)

        # Account control buttons (approval / block / reset device)
        self.approve_btn = ctk.CTkButton(
            buttons_frame,
            text="اعتماد",
            width=110,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.approve_selected_pharmacy
        )
        self.approve_btn.pack(side="left", padx=5)

        self.block_btn = ctk.CTkButton(
            buttons_frame,
            text="حظر",
            width=90,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#FF9800",
            hover_color="#F57C00",
            command=self.block_selected_pharmacy
        )
        self.block_btn.pack(side="left", padx=5)

        self.reset_device_btn = ctk.CTkButton(
            buttons_frame,
            text="إعادة ربط الجهاز",
            width=140,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#607D8B",
            hover_color="#546E7A",
            command=self.reset_selected_device
        )
        self.reset_device_btn.pack(side="left", padx=5)
        
        self.statement_btn = ctk.CTkButton(
            buttons_frame,
            text="كشف حساب",
            width=120,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#FF9800",
            hover_color="#F57C00",
            command=self.show_account_statement
        )
        self.statement_btn.pack(side="left", padx=5)
        
        self.reminder_btn = ctk.CTkButton(
            buttons_frame,
            text="إرسال تذكير",
            width=120,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.show_reminder_dialog
        )
        self.reminder_btn.pack(side="left", padx=5)
        
        self.export_pdf_btn = ctk.CTkButton(
            buttons_frame,
            text="تصدير PDF",
            width=110,
            height=32,
            font=("Arial", 12, "bold"),
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            command=self.export_account_statement_pdf
        )
        self.export_pdf_btn.pack(side="left", padx=5)
        
        self.update_action_buttons()
    
    # ==========================================
    # Pharmacy Display Methods
    # ==========================================
    
    def load_pharmacies(self):
        """Load pharmacies from API"""
        # Check server health first
        if not self.check_server_health():
            self.update_status("⚠️ السيرفر غير متصل")
            self.clear_rows()
            self.show_empty_message(
                "⚠️ السيرفر غير متصل\n\n"
                "قم بتشغيل السيرفر باستخدام الأمر:\n"
                "python -m uvicorn main:app --reload"
            )
            return
        
        try:
            self.update_status("جاري تحميل الصيدليات...")
            
            pharmacies = self.api_client.get_pharmacies()
            
            # Store all pharmacies for search
            self.all_pharmacies = pharmacies
            
            # Clear empty message if exists
            if "empty" in self.rows:
                self.rows["empty"].destroy()
                del self.rows["empty"]
            
            self.clear_rows()
            
            if not pharmacies or len(pharmacies) == 0:
                self.show_empty_message("🏪 لا توجد صيدليات\nاضغط على 'إضافة صيدلية' لإضافة صيدلية جديدة")
                self.update_status("لا توجد صيدليات")
                return
            
            # Sort pharmacies by id
            pharmacies.sort(key=lambda x: x.get("id", 0))
            
            for pharmacy in pharmacies:
                self.add_pharmacy_row(pharmacy)
            
            self.update_status(f"✅ تم تحميل {len(pharmacies)} صيدلية")
                
        except Exception as e:
            self.update_status("❌ خطأ في تحميل الصيدليات")
            self.clear_rows()
            self.show_empty_message(f"⚠️ حدث خطأ أثناء تحميل الصيدليات\n\n{str(e)}")
    
    def search_pharmacies(self):
        """Search pharmacies by name or phone"""
        search_term = self.search_entry.get().strip()
        
        if not search_term:
            # Reload all pharmacies
            self.load_pharmacies()
            return
        
        # Use local filtering
        if not self.all_pharmacies:
            return
        
        # Filter pharmacies by name or phone
        search_term_lower = search_term.lower()
        filtered_pharmacies = [
            p for p in self.all_pharmacies 
            if search_term_lower in p.get("name", "").lower() 
            or search_term_lower in p.get("phone", "").lower()
        ]
        
        # Clear current display
        self.clear_rows()
        
        if not filtered_pharmacies:
            self.show_empty_message(f"🔍 لا توجد نتائج لـ '{search_term}'")
            self.update_status(f"لا توجد نتائج لـ '{search_term}'")
            return
        
        # Sort filtered pharmacies
        filtered_pharmacies.sort(key=lambda x: x.get("id", 0))
        
        for pharmacy in filtered_pharmacies:
            self.add_pharmacy_row(pharmacy)
        
        self.update_status(f"✅ تم العثور على {len(filtered_pharmacies)} صيدلية")
    
    def add_pharmacy_row(self, pharmacy):
        """Add a pharmacy row to the table"""
        row_frame = ctk.CTkFrame(self.table_frame, fg_color="#333333", corner_radius=8, height=42)
        row_frame.pack(fill="x", padx=10, pady=4)
        row_frame.pack_propagate(False)
        
        pharmacy_id = pharmacy.get("id")
        balance = self.get_pharmacy_balance(pharmacy)
        account_status = str(pharmacy.get("account_status") or "active").lower().strip()
        status_map = {
            "pending": ("قيد المراجعة", "#FF9800"),
            "active": ("نشط", "#4CAF50"),
            "blocked": ("محظور", "#f44336"),
            "deleted": ("ملغي", "#9E9E9E"),
        }
        status_text, status_color = status_map.get(account_status, ("نشط", "#4CAF50"))
        
        # Determine balance color
        balance_color = "#4CAF50" if balance == 0 else "#FF9800" if balance > 0 else "white"
        
        data = [
            {"text": str(pharmacy_id), "width": 60, "color": "white", "anchor": "center"},
            {"text": pharmacy.get("name", "N/A"), "width": 200, "color": "white", "anchor": "e"},
            {"text": status_text, "width": 110, "color": status_color, "anchor": "center"},
            {"text": pharmacy.get("phone", "غير محدد"), "width": 150, "color": "white", "anchor": "center"},
            {"text": pharmacy.get("address", "غير محدد"), "width": 250, "color": "white", "anchor": "e"},
            {"text": f"{balance:.2f}", "width": 120, "color": balance_color, "anchor": "e"}
        ]
        
        for item in data:
            label = ctk.CTkLabel(
                row_frame,
                text=item["text"],
                width=item["width"],
                font=("Arial", 12),
                anchor=item["anchor"],
                justify="right",
                text_color=item["color"]
            )
            label.pack(side="left", padx=5, pady=5)
            label.bind("<Button-1>", lambda event, p=pharmacy, r=row_frame: self.select_pharmacy(p, r))
        
        row_frame.bind("<Button-1>", lambda event, p=pharmacy, r=row_frame: self.select_pharmacy(p, r))
        
        self.rows[pharmacy_id] = row_frame
    
    def select_pharmacy(self, pharmacy, row_frame):
        """Select a pharmacy row and enable action buttons."""
        if self.selected_row and self.selected_row.winfo_exists():
            self.selected_row.configure(fg_color="#333333")
        
        self.selected_pharmacy = pharmacy
        self.selected_row = row_frame
        row_frame.configure(fg_color="#3f4a3f")
        self.update_action_buttons()
        self.update_status(f"تم اختيار الصيدلية: {pharmacy.get('name', '')}")
    
    def update_action_buttons(self):
        """Enable or disable action buttons based on selection."""
        has_selection = self.selected_pharmacy is not None
        state = "normal" if has_selection else "disabled"
        
        if hasattr(self, "edit_selected_btn"):
            manage_state = state if self.can_manage_pharmacies() else "disabled"
            self.edit_selected_btn.configure(state=manage_state)
            self.delete_selected_btn.configure(state=manage_state)
            if hasattr(self, "approve_btn"):
                self.approve_btn.configure(state=manage_state)
            if hasattr(self, "block_btn"):
                self.block_btn.configure(state=manage_state)
            if hasattr(self, "reset_device_btn"):
                self.reset_device_btn.configure(state=manage_state)
            self.statement_btn.configure(state=state)
            self.reminder_btn.configure(state=state)
            self.export_pdf_btn.configure(state=state)
        
        if hasattr(self, "selected_label"):
            if has_selection:
                name = self.selected_pharmacy.get("name", "صيدلية")
                self.selected_label.configure(text=f"الصيدلية المحددة: {name}", text_color="#ffffff")
            else:
                self.selected_label.configure(text="اختر صيدلية من الجدول", text_color="#bdbdbd")
    
    def edit_selected_pharmacy(self):
        """Edit the selected pharmacy."""
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        self.edit_pharmacy(self.selected_pharmacy)
    
    def delete_selected_pharmacy(self):
        """Revoke access for the selected pharmacy (soft delete)."""
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        self.revoke_pharmacy_access(self.selected_pharmacy.get("id"))
    
    def show_account_statement(self):
        """Show a practical account statement for the selected pharmacy."""
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        
        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return
        
        try:
            pharmacy = self.selected_pharmacy
            pharmacy_id = pharmacy.get("id")
            balance = self.get_pharmacy_balance(pharmacy)
            self.update_status("جاري تجهيز كشف الحساب...")
            
            transactions = self.build_account_transactions(pharmacy_id)
            total_orders = sum(item["debit"] for item in transactions)
            total_payments = sum(item["credit"] for item in transactions)
            
            dialog = ctk.CTkToplevel(self)
            dialog.title("كشف حساب الصيدلية")
            dialog.geometry("820x620")
            dialog.resizable(True, True)
            dialog.transient(self)
            dialog.grab_set()
            
            main_frame = ctk.CTkFrame(dialog, fg_color="#1e1e1e")
            main_frame.pack(fill="both", expand=True)
            
            header = ctk.CTkFrame(main_frame, fg_color="#2d2d2d", corner_radius=12)
            header.pack(fill="x", padx=20, pady=(20, 12))
            
            ctk.CTkLabel(
                header,
                text="كشف حساب الصيدلية",
                font=("Arial", 22, "bold"),
                text_color="#4CAF50",
                anchor="e"
            ).pack(anchor="e", padx=18, pady=(14, 4))
            
            ctk.CTkLabel(
                header,
                text=f"{pharmacy.get('name', '')} | {pharmacy.get('phone', '')}",
                font=("Arial", 14),
                text_color="#d0d0d0",
                anchor="e"
            ).pack(anchor="e", padx=18, pady=(0, 14))
            
            summary_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            summary_frame.pack(fill="x", padx=20, pady=(0, 12))
            summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
            
            self.create_statement_summary_card(summary_frame, "الرصيد الحالي", self.format_money(balance), "#FF9800", 0)
            self.create_statement_summary_card(summary_frame, "إجمالي الطلبات", self.format_money(total_orders), "#f44336", 1)
            self.create_statement_summary_card(summary_frame, "إجمالي التحصيلات", self.format_money(total_payments), "#4CAF50", 2)
            self.create_statement_summary_card(summary_frame, "عدد العمليات", str(len(transactions)), "#2196F3", 3)
            
            table = ctk.CTkScrollableFrame(main_frame, fg_color="#2d2d2d", corner_radius=12)
            table.pack(fill="both", expand=True, padx=20, pady=(0, 12))
            
            self.create_statement_header(table)
            
            if transactions:
                for transaction in transactions:
                    self.create_statement_row(table, transaction)
            else:
                ctk.CTkLabel(
                    table,
                    text="لا توجد طلبات معتمدة أو تحصيلات لهذه الصيدلية",
                    font=("Arial", 14),
                    text_color="#9e9e9e"
                ).pack(pady=40)
            
            close_btn = ctk.CTkButton(
                main_frame,
                text="إغلاق",
                width=120,
                height=36,
                fg_color="#555555",
                hover_color="#666666",
                command=dialog.destroy
            )
            close_btn.pack(pady=(0, 18))
            
            self.update_status("تم تجهيز كشف الحساب")
            
        except Exception as e:
            self.update_status("خطأ في تجهيز كشف الحساب")
            self.show_error(f"حدث خطأ أثناء تجهيز كشف الحساب:\n{str(e)}")
    
    def build_account_transactions(self, pharmacy_id):
        """Build account transactions from existing orders and payments APIs."""
        transactions = []
        pharmacy_id_text = str(pharmacy_id)
        
        orders = self.api_client.get_orders()
        for order in orders:
            if str(order.get("pharmacy_id")) != pharmacy_id_text:
                continue
            
            status = str(order.get("status", "")).lower()
            if status not in ("approved", "reviewed", "completed"):
                continue
            
            transactions.append({
                "date": self.get_order_date(order),
                "type": "طلب",
                "description": f"طلب رقم {order.get('id', '-')}",
                "debit": self.get_order_total(order),
                "credit": 0.0,
                "color": "#f44336"
            })
        
        payments = self.api_client.get_pharmacy_payments(pharmacy_id)
        for payment in payments:
            amount = payment.get("amount", 0)
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0.0
            
            transactions.append({
                "date": payment.get("date", ""),
                "type": "تحصيل",
                "description": f"دفعة رقم {payment.get('id', '-')}",
                "debit": 0.0,
                "credit": amount,
                "color": "#4CAF50"
            })
        
        transactions.sort(key=lambda item: self.parse_datetime(item["date"]), reverse=True)
        return transactions
    
    def create_statement_summary_card(self, parent, title, value, color, column):
        """Create a compact summary card for account statement."""
        card = ctk.CTkFrame(parent, fg_color="#2d2d2d", corner_radius=10)
        card.grid(row=0, column=column, sticky="ew", padx=5)
        
        ctk.CTkFrame(card, fg_color=color, height=4).pack(fill="x", padx=10, pady=(10, 8))
        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 12, "bold"),
            text_color="#dcdcdc",
            anchor="e"
        ).pack(anchor="e", padx=12)
        ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 18, "bold"),
            text_color=color
        ).pack(anchor="e", padx=12, pady=(4, 12))
    
    def create_statement_header(self, parent):
        """Create account statement table header."""
        header = ctk.CTkFrame(parent, fg_color="#1f1f1f", corner_radius=8)
        header.pack(fill="x", padx=8, pady=(8, 4))
        
        headers = [
            ("التاريخ", 150),
            ("النوع", 90),
            ("البيان", 220),
            ("مدين", 120),
            ("دائن", 120),
        ]
        
        for text, width in headers:
            ctk.CTkLabel(
                header,
                text=text,
                width=width,
                font=("Arial", 12, "bold"),
                text_color="#4CAF50"
            ).pack(side="left", padx=4, pady=8)
    
    def create_statement_row(self, parent, transaction):
        """Create one account statement row."""
        row = ctk.CTkFrame(parent, fg_color="#333333", corner_radius=8)
        row.pack(fill="x", padx=8, pady=3)
        
        values = [
            (self.format_date(transaction["date"]), 150, "#ffffff"),
            (transaction["type"], 90, transaction["color"]),
            (transaction["description"], 220, "#ffffff"),
            (self.format_money(transaction["debit"]) if transaction["debit"] else "-", 120, "#f44336"),
            (self.format_money(transaction["credit"]) if transaction["credit"] else "-", 120, "#4CAF50"),
        ]
        
        for text, width, color in values:
            ctk.CTkLabel(
                row,
                text=text,
                width=width,
                font=("Arial", 12),
                text_color=color,
                anchor="center"
            ).pack(side="left", padx=4, pady=8)
    
    def show_reminder_dialog(self):
        """Send a payment reminder through WhatsApp or email client."""
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        
        pharmacy = self.selected_pharmacy
        balance = self.get_pharmacy_balance(pharmacy)
        message = f"تذكير بدفع مستحقات: رصيدك الحالي {balance:.2f} جنيه. يرجى تسوية المبلغ."
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("إرسال تذكير")
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            frame,
            text=f"إرسال تذكير إلى: {pharmacy.get('name', '')}",
            font=("Arial", 16, "bold"),
            text_color="#4CAF50"
        ).pack(pady=(18, 8))
        
        ctk.CTkButton(
            frame,
            text="واتساب",
            width=140,
            height=36,
            fg_color="#4CAF50",
            command=lambda: [self.open_whatsapp_reminder(pharmacy, message), dialog.destroy()]
        ).pack(side="left", padx=(45, 8), pady=30)
        
        ctk.CTkButton(
            frame,
            text="إيميل",
            width=140,
            height=36,
            fg_color="#2196F3",
            command=lambda: [self.open_email_reminder(pharmacy, message), dialog.destroy()]
        ).pack(side="left", padx=8, pady=30)
    
    def open_whatsapp_reminder(self, pharmacy, message):
        phone = "".join(ch for ch in str(pharmacy.get("phone", "")) if ch.isdigit())
        if not phone:
            self.show_error("رقم الهاتف غير صالح")
            return
        webbrowser.open(f"https://wa.me/{phone}?text={urllib.parse.quote(message)}")
        self.update_status("تم فتح واتساب لإرسال التذكير")
    
    def open_email_reminder(self, pharmacy, message):
        target = str(pharmacy.get("email") or pharmacy.get("phone") or "").strip()
        subject = "تذكير بسداد المستحقات"
        webbrowser.open(
            f"mailto:{target}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(message)}"
        )
        self.update_status("تم فتح البريد لإرسال التذكير")
    
    def export_account_statement_pdf(self):
        """Export current pharmacy account statement as PDF."""
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
        except Exception:
            self.show_error("تصدير PDF يحتاج تثبيت reportlab")
            return
        
        pharmacy = self.selected_pharmacy
        file_path = filedialog.asksaveasfilename(
            title="حفظ كشف الحساب PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not file_path:
            return
        
        try:
            transactions = self.build_account_transactions(pharmacy.get("id"))
            balance = self.get_pharmacy_balance(pharmacy)
            styles = getSampleStyleSheet()
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            story = [
                Paragraph("Al Nada Pharmacy Store - Account Statement", styles["Title"]),
                Spacer(1, 12),
                Paragraph(f"Pharmacy: {pharmacy.get('name', '')}", styles["Normal"]),
                Paragraph(f"Phone: {pharmacy.get('phone', '')}", styles["Normal"]),
                Paragraph(f"Address: {pharmacy.get('address', '')}", styles["Normal"]),
                Paragraph(f"Current Balance: {balance:.2f}", styles["Normal"]),
                Paragraph(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
                Spacer(1, 12),
            ]
            
            table_data = [["Date", "Type", "Description", "Debit", "Credit"]]
            for item in transactions:
                table_data.append([
                    self.format_date(item["date"]),
                    item["type"],
                    item["description"],
                    self.format_money(item["debit"]) if item["debit"] else "-",
                    self.format_money(item["credit"]) if item["credit"] else "-",
                ])
            if len(table_data) == 1:
                table_data.append(["-", "-", "No transactions", "-", "-"])
            
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d2d2d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ]))
            story.append(table)
            doc.build(story)
            self.show_info("تم تصدير كشف الحساب PDF بنجاح")
            self.update_status("تم تصدير كشف الحساب PDF")
        except Exception as e:
            self.show_error(f"فشل تصدير PDF:\n{str(e)}")
    
    def clear_rows(self):
        """Clear all pharmacy rows from the table safely"""
        self.selected_pharmacy = None
        self.selected_row = None
        self.update_action_buttons()
        
        rows_to_clear = list(self.rows.values())
        
        for row in rows_to_clear:
            try:
                if row and row.winfo_exists():
                    row.destroy()
            except:
                pass
        
        self.rows.clear()
    
    def show_empty_message(self, message="🏪 لا توجد صيدليات"):
        """Show empty state message"""
        empty_label = ctk.CTkLabel(
            self.table_frame,
            text=message,
            font=("Arial", 14),
            text_color="gray"
        )
        empty_label.pack(pady=50)
        self.rows["empty"] = empty_label
    
    # ==========================================
    # Pharmacy CRUD Operations
    # ==========================================
    
    def show_add_dialog(self):
        """Show dialog to add new pharmacy"""
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("إضافة صيدلية جديدة")
        dialog.geometry("450x600")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Bind Escape to close
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        main_frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            main_frame,
            text="إضافة صيدلية جديدة",
            font=("Arial", 20, "bold"),
            text_color="#4CAF50"
        )
        title.pack(pady=(20, 30))
        
        fields_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        fields_frame.pack(pady=10)
        
        # Name field
        ctk.CTkLabel(fields_frame, text="اسم الصيدلية:", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        name_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        name_entry.pack(pady=(0, 15))
        name_entry.focus()
        
        # Address field
        ctk.CTkLabel(fields_frame, text="العنوان:", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        address_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        address_entry.pack(pady=(0, 15))
        
        # Phone field
        ctk.CTkLabel(fields_frame, text="رقم الهاتف:", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        phone_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        phone_entry.pack(pady=(0, 15))
        
        # Balance field
        ctk.CTkLabel(fields_frame, text="الرصيد (EGP):", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        balance_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        balance_entry.insert(0, "0.00")
        balance_entry.pack(pady=(0, 15))
        
        is_saving = False
        
        def save_pharmacy():
            nonlocal is_saving
            
            if is_saving:
                return
            
            try:
                # Validate name
                name = name_entry.get().strip()
                if not name:
                    self.show_error("اسم الصيدلية مطلوب")
                    name_entry.focus()
                    return
                
                # Validate address
                address = address_entry.get().strip()
                if not address:
                    self.show_error("العنوان مطلوب")
                    address_entry.focus()
                    return
                
                # Validate phone
                phone = phone_entry.get().strip()
                if not phone:
                    self.show_error("رقم الهاتف مطلوب")
                    phone_entry.focus()
                    return
                
                # Validate balance
                balance_text = balance_entry.get().strip()
                if not balance_text:
                    balance = 0.0
                else:
                    try:
                        balance = self.safe_float(balance_text, "الرصيد")
                        if balance < 0:
                            self.show_error("الرصيد لا يمكن أن يكون سالباً")
                            balance_entry.focus()
                            return
                    except ValueError as e:
                        self.show_error(str(e))
                        balance_entry.focus()
                        return
                
                # Check server health
                if not self.check_server_health():
                    self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
                    return
                
                # Disable save button
                is_saving = True
                save_btn.configure(text="جاري الحفظ...", state="disabled")
                
                self.update_status("جاري حفظ الصيدلية...")
                
                # Try to save pharmacy
                result = self.api_client.create_pharmacy(name, address, phone, balance)
                
                if result:
                    self.show_info(f"✅ تم إضافة الصيدلية '{name}' بنجاح")
                    dialog.destroy()
                    self.load_pharmacies()
                    self.update_status(f"✅ تم إضافة صيدلية جديدة: {name}")
                else:
                    self.show_error(
                        "فشل إضافة الصيدلية.\n\n"
                        "الأسباب المحتملة:\n"
                        "• مشكلة في الاتصال بقاعدة البيانات\n"
                        "• اسم الصيدلية قد يكون مكرراً\n\n"
                        "تأكد من أن السيرفر يعمل بشكل صحيح"
                    )
                    
            except Exception as e:
                self.show_error(f"حدث خطأ غير متوقع: {str(e)}")
            finally:
                is_saving = False
                save_btn.configure(text="💾 حفظ", state="normal")
                self.update_status("جاهز")
        
        # Buttons
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 حفظ",
            width=120,
            height=40,
            font=("Arial", 13, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=save_pharmacy
        )
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="✖ إلغاء",
            width=120,
            height=40,
            font=("Arial", 13, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", padx=10)
        
        # Bind Enter key to save
        dialog.bind("<Return>", lambda e: save_pharmacy())
    
    def edit_pharmacy(self, pharmacy):
        """Edit existing pharmacy"""
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("تعديل بيانات الصيدلية")
        dialog.geometry("450x600")
        dialog.resizable(False, False)
        
        # Make dialog modal
        dialog.transient(self)
        dialog.grab_set()
        
        # Bind Escape to close
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        main_frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            main_frame,
            text="تعديل بيانات الصيدلية",
            font=("Arial", 20, "bold"),
            text_color="#2196F3"
        )
        title.pack(pady=(20, 30))
        
        fields_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        fields_frame.pack(pady=10)
        
        # Name field
        ctk.CTkLabel(fields_frame, text="اسم الصيدلية:", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        name_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        name_entry.insert(0, pharmacy.get("name", ""))
        name_entry.pack(pady=(0, 15))
        name_entry.focus()
        
        # Address field
        ctk.CTkLabel(fields_frame, text="العنوان:", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        address_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        address_entry.insert(0, pharmacy.get("address", ""))
        address_entry.pack(pady=(0, 15))
        
        # Phone field
        ctk.CTkLabel(fields_frame, text="رقم الهاتف:", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        phone_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        phone_entry.insert(0, pharmacy.get("phone", ""))
        phone_entry.pack(pady=(0, 15))
        
        # Balance field
        ctk.CTkLabel(fields_frame, text="الرصيد (EGP):", font=("Arial", 13)).pack(anchor="w", pady=(10, 5))
        balance_entry = ctk.CTkEntry(fields_frame, width=350, height=40, font=("Arial", 13))
        balance = self.get_pharmacy_balance(pharmacy)
        balance_entry.insert(0, f"{balance:.2f}")
        balance_entry.pack(pady=(0, 15))
        
        is_updating = False
        
        def update_pharmacy():
            nonlocal is_updating
            
            if is_updating:
                return
            
            try:
                # Validate name
                name = name_entry.get().strip()
                if not name:
                    self.show_error("اسم الصيدلية مطلوب")
                    name_entry.focus()
                    return
                
                # Validate address
                address = address_entry.get().strip()
                if not address:
                    self.show_error("العنوان مطلوب")
                    address_entry.focus()
                    return
                
                # Validate phone
                phone = phone_entry.get().strip()
                if not phone:
                    self.show_error("رقم الهاتف مطلوب")
                    phone_entry.focus()
                    return
                
                # Validate balance
                balance_text = balance_entry.get().strip()
                if not balance_text:
                    balance = 0.0
                else:
                    try:
                        balance = self.safe_float(balance_text, "الرصيد")
                        if balance < 0:
                            self.show_error("الرصيد لا يمكن أن يكون سالباً")
                            balance_entry.focus()
                            return
                    except ValueError as e:
                        self.show_error(str(e))
                        balance_entry.focus()
                        return
                
                # Check server health
                if not self.check_server_health():
                    self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
                    return
                
                # Disable update button
                is_updating = True
                save_btn.configure(text="جاري التحديث...", state="disabled")
                
                self.update_status("جاري تحديث الصيدلية...")
                
                # Try to update pharmacy
                result = self.api_client.update_pharmacy(
                    pharmacy["id"], name, address, phone, balance
                )
                
                if result:
                    self.show_info(f"✅ تم تحديث بيانات الصيدلية '{name}' بنجاح")
                    dialog.destroy()
                    self.load_pharmacies()
                    self.update_status("✅ تم تحديث الصيدلية")
                else:
                    self.show_error(
                        "فشل تحديث الصيدلية.\n\n"
                        "الأسباب المحتملة:\n"
                        "• مشكلة في الاتصال بقاعدة البيانات\n"
                        "• اسم الصيدلية قد يكون مكرراً\n\n"
                        "تأكد من أن السيرفر يعمل بشكل صحيح"
                    )
                    
            except Exception as e:
                self.show_error(f"حدث خطأ غير متوقع: {str(e)}")
            finally:
                is_updating = False
                save_btn.configure(text="💾 حفظ التغييرات", state="normal")
                self.update_status("جاهز")
        
        # Buttons
        buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        buttons_frame.pack(pady=20)
        
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 حفظ التغييرات",
            width=120,
            height=40,
            font=("Arial", 13, "bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=update_pharmacy
        )
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="✖ إلغاء",
            width=120,
            height=40,
            font=("Arial", 13, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", padx=10)
        
        # Bind Enter key to save
        dialog.bind("<Return>", lambda e: update_pharmacy())
    
    def revoke_pharmacy_access(self, pharmacy_id):
        """Revoke pharmacy access after confirmation (soft delete)."""
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        # Check server health first
        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return
        
        # Show confirmation with askyesno
        confirm = messagebox.askyesno(
            "تأكيد سحب الصلاحية",
            "⚠️ هل أنت متأكد من سحب صلاحية هذه الصيدلية؟\n\n"
            "سيتم منعها من استخدام تطبيق المندوب/الصيدلي، مع الاحتفاظ بكل البيانات."
        )
        
        if not confirm:
            return
        
        try:
            self.update_status("جاري سحب الصلاحية...")

            note = "revoke from admin"
            if hasattr(self.api_client, "delete_or_revoke_pharmacy_account"):
                success = self.api_client.delete_or_revoke_pharmacy_account(pharmacy_id, note=note)
            else:
                success = self.api_client.delete_pharmacy(pharmacy_id)

            if success:
                self.show_info("✅ تم سحب صلاحية الصيدلية بنجاح")
                self.load_pharmacies()
                self.update_status("✅ تم سحب الصلاحية")
            else:
                self.show_error(
                    "فشل سحب صلاحية الصيدلية.\n\n"
                    "الأسباب المحتملة:\n"
                    "• مشكلة في الاتصال بقاعدة البيانات\n"
                    "• السيرفر لا يستجيب"
                )
                self.update_status("❌ فشل سحب الصلاحية")
                
        except Exception as e:
            error_msg = str(e)
            self.show_error(f"حدث خطأ أثناء سحب الصلاحية: {error_msg}")
            self.update_status("❌ خطأ في سحب الصلاحية")

    def approve_selected_pharmacy(self):
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        pharmacy_id = self.selected_pharmacy.get("id")
        name = self.selected_pharmacy.get("name", "")
        confirm = messagebox.askyesno(
            "تأكيد الاعتماد",
            f"هل تريد اعتماد حساب الصيدلية التالية؟\n\n{name}"
        )
        if not confirm:
            return
        self.update_status("جاري اعتماد الحساب...")
        ok = self.api_client.approve_pharmacy_account(pharmacy_id, note="approved from admin") if hasattr(self.api_client, "approve_pharmacy_account") else False
        if ok:
            self.show_info("✅ تم اعتماد الحساب")
            self.load_pharmacies()
            self.update_status("✅ تم اعتماد الحساب")
        else:
            self.show_error("فشل اعتماد الحساب")
            self.update_status("❌ فشل اعتماد الحساب")

    def block_selected_pharmacy(self):
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        pharmacy_id = self.selected_pharmacy.get("id")
        name = self.selected_pharmacy.get("name", "")
        confirm = messagebox.askyesno(
            "تأكيد الحظر",
            f"⚠️ هل تريد حظر حساب الصيدلية التالية؟\n\n{name}\n\nسيتم منعها من استخدام التطبيق مؤقتاً."
        )
        if not confirm:
            return
        self.update_status("جاري حظر الحساب...")
        ok = self.api_client.block_pharmacy_account(pharmacy_id, note="blocked from admin") if hasattr(self.api_client, "block_pharmacy_account") else False
        if ok:
            self.show_info("✅ تم حظر الحساب")
            self.load_pharmacies()
            self.update_status("✅ تم حظر الحساب")
        else:
            self.show_error("فشل حظر الحساب")
            self.update_status("❌ فشل حظر الحساب")

    def reset_selected_device(self):
        if not self.can_manage_pharmacies():
            self.show_permission_denied()
            return
        if not self.selected_pharmacy:
            self.show_warning("اختر صيدلية أولاً")
            return
        pharmacy_id = self.selected_pharmacy.get("id")
        name = self.selected_pharmacy.get("name", "")
        confirm = messagebox.askyesno(
            "تأكيد إعادة ربط الجهاز",
            f"هل تريد مسح ربط الجهاز لهذه الصيدلية؟\n\n{name}\n\n"
            "ملاحظة: لن يؤثر ذلك على البيانات، فقط يسمح بإعادة ربط جهاز جديد إذا كان النظام يدعم ذلك."
        )
        if not confirm:
            return
        self.update_status("جاري إعادة ربط الجهاز...")
        ok = self.api_client.reset_pharmacy_device(pharmacy_id) if hasattr(self.api_client, "reset_pharmacy_device") else False
        if ok:
            self.show_info("✅ تم مسح ربط الجهاز")
            self.load_pharmacies()
            self.update_status("✅ تم مسح ربط الجهاز")
        else:
            self.show_error("فشل مسح ربط الجهاز")
            self.update_status("❌ فشل مسح ربط الجهاز")
