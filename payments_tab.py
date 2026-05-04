"""
Payments Tab for Pharmacy Management System
Handles payment collection from pharmacies
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
from api_client import APIClient
from datetime import datetime


class PaymentsTab(ctk.CTkFrame):
    """Payments management tab - track and record pharmacy payments"""
    
    def __init__(self, master, api_client=None, status_callback=None):
        """
        Initialize Payments Tab
        
        Args:
            master: Parent widget
            api_client: APIClient instance
            status_callback: Function to update status bar
        """
        super().__init__(master)
        
        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.pharmacy_dict = {}
        self.orders_cache = []
        self.order_dict = {}
        self.is_saving = False
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.configure(fg_color="#1e1e1e")
        
        # Create UI
        self.create_ui()
        
        # Load data
        self.load_pharmacies()
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
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
        """Format money value with 2 decimal places"""
        try:
            return f"{float(value):,.2f}"
        except Exception:
            return "0.00"
    
    def safe_float(self, value, field_name="المبلغ"):
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

    def translate_payment_status(self, status):
        return {
            "unpaid": "لم يدفع",
            "cash": "دفع كاش",
            "partial": "دفع جزء",
            "full": "دفع كامل",
            "deferred": "أجل",
            "collect_on_delivery": "تحصيل عند الاستلام",
        }.get(status or "", status or "-")

    def translate_order_status(self, status):
        return {
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
            "completed": "تم التسليم",
        }.get(status or "pending", status or "جديد")

    def get_payment_type(self):
        label = self.payment_type_var.get() if hasattr(self, "payment_type_var") else "دفع كاش"
        return {
            "دفع كاش": "cash",
            "دفع جزء": "partial",
            "دفع كامل": "full",
            "أجل": "deferred",
            "تحصيل عند الاستلام": "collect_on_delivery",
        }.get(label, "cash")

    def get_selected_order(self):
        if not hasattr(self, "order_var"):
            return None
        label = self.order_var.get()
        if not label or label == "بدون طلب محدد":
            return None
        return self.order_dict.get(label)

    def get_order_total(self, order):
        if not order:
            return 0.0
        try:
            return float(order.get("final_total") or order.get("total") or order.get("total_amount") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def get_order_paid(self, order):
        if not order:
            return 0.0
        try:
            return float(order.get("amount_paid") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def get_order_remaining(self, order):
        if not order:
            return 0.0
        remaining = order.get("remaining_amount")
        try:
            if remaining is not None:
                return max(float(remaining), 0.0)
        except (TypeError, ValueError):
            pass
        return max(self.get_order_total(order) - self.get_order_paid(order), 0.0)
    
    def clear_payments_table(self):
        """Clear all payments from the table"""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def set_pharmacy_controls_state(self, state):
        """Enable/disable pharmacy controls"""
        try:
            self.pharmacy_menu.configure(state=state)
            self.order_menu.configure(state=state)
            self.payment_type_menu.configure(state=state)
            self.notes_entry.configure(state=state)
            self.amount_entry.configure(state=state)
            if state == "normal":
                self.save_btn.configure(state="normal")
            else:
                self.save_btn.configure(state="disabled")
        except:
            pass
    
    # ==========================================
    # UI Creation
    # ==========================================

    def create_summary_card(self, parent, title, variable, color, column):
        card = ctk.CTkFrame(parent, fg_color="#252525", corner_radius=10, border_width=1, border_color="#3a3a3a")
        card.grid(row=0, column=column, sticky="ew", padx=5, pady=5)
        ctk.CTkFrame(card, fg_color=color, height=4, corner_radius=4).pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="#bdbdbd").pack(pady=(2, 0))
        ctk.CTkLabel(card, textvariable=variable, font=ctk.CTkFont(size=18, weight="bold"), text_color=color).pack(pady=(2, 10))
    
    def create_ui(self):
        """Create the user interface"""
        
        # --- Input Frame (Top Section) ---
        self.input_frame = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=10)
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        
        # Title
        ctk.CTkLabel(
            self.input_frame,
            text="تسجيل تحصيل نقدي",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#4CAF50"
        ).grid(row=0, column=0, columnspan=6, pady=15)

        # Summary cards
        self.summary_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.summary_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=10, pady=(0, 10))
        self.summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.total_due_var = ctk.StringVar(value="0.00")
        self.total_paid_var = ctk.StringVar(value="0.00")
        self.total_remaining_var = ctk.StringVar(value="0.00")
        self.unpaid_orders_var = ctk.StringVar(value="0")
        self.create_summary_card(self.summary_frame, "إجمالي المستحق", self.total_due_var, "#FF9800", 0)
        self.create_summary_card(self.summary_frame, "إجمالي المدفوع", self.total_paid_var, "#4CAF50", 1)
        self.create_summary_card(self.summary_frame, "إجمالي المتبقي", self.total_remaining_var, "#f44336", 2)
        self.create_summary_card(self.summary_frame, "طلبات غير مسددة", self.unpaid_orders_var, "#2196F3", 3)
        
        # 1. Pharmacy Selection
        ctk.CTkLabel(
            self.input_frame,
            text="الصيدلية:",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=2, column=5, padx=5, pady=10, sticky="e")
        
        self.pharmacy_var = ctk.StringVar(value="")
        self.pharmacy_menu = ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.pharmacy_var,
            values=["جاري التحميل..."],
            command=self.on_pharmacy_select,
            font=ctk.CTkFont(size=14),
            width=250
        )
        self.pharmacy_menu.grid(row=2, column=4, padx=10, pady=10, sticky="ew")
        
        # 2. Balance Display
        ctk.CTkLabel(
            self.input_frame,
            text="المديونية الحالية:",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=2, column=3, padx=5, pady=10, sticky="e")
        
        self.balance_var = ctk.StringVar(value="0.00")
        self.balance_label = ctk.CTkLabel(
            self.input_frame,
            textvariable=self.balance_var,
            text_color="#FFA500",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.balance_label.grid(row=2, column=2, padx=10, pady=10)
        
        # 3. Amount Input
        ctk.CTkLabel(
            self.input_frame,
            text="المبلغ المحصل:",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=2, column=1, padx=5, pady=10, sticky="e")
        
        self.amount_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="أدخل المبلغ...",
            justify="right",
            font=ctk.CTkFont(size=14),
            width=200
        )
        self.amount_entry.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(
            self.input_frame,
            text="الطلب:",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=3, column=5, padx=5, pady=10, sticky="e")
        self.order_var = ctk.StringVar(value="بدون طلب محدد")
        self.order_menu = ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.order_var,
            values=["بدون طلب محدد"],
            command=lambda _v: self.update_order_payment_preview(),
            font=ctk.CTkFont(size=13),
            width=250
        )
        self.order_menu.grid(row=3, column=4, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(
            self.input_frame,
            text="نوع الدفع:",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=3, column=3, padx=5, pady=10, sticky="e")
        self.payment_type_var = ctk.StringVar(value="دفع كاش")
        self.payment_type_menu = ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.payment_type_var,
            values=["دفع كاش", "دفع جزء", "دفع كامل", "أجل", "تحصيل عند الاستلام"],
            command=lambda _v: self.update_order_payment_preview(),
            font=ctk.CTkFont(size=13)
        )
        self.payment_type_menu.grid(row=3, column=2, padx=10, pady=10, sticky="ew")

        self.order_preview_var = ctk.StringVar(value="إجمالي الطلب: 0.00 | مدفوع سابقًا: 0.00 | المتبقي: 0.00")
        ctk.CTkLabel(
            self.input_frame,
            textvariable=self.order_preview_var,
            font=ctk.CTkFont(size=12),
            text_color="#bdbdbd",
            anchor="e"
        ).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(
            self.input_frame,
            text="ملاحظات:",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=4, column=5, padx=5, pady=10, sticky="e")
        self.notes_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="ملاحظات التحصيل...",
            justify="right",
            font=ctk.CTkFont(size=13)
        )
        self.notes_entry.grid(row=4, column=0, columnspan=5, padx=10, pady=10, sticky="ew")
        
        # 4. Save Button
        self.save_btn = ctk.CTkButton(
            self.input_frame,
            text="💾 حفظ وتحصيل",
            command=self.save_payment,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40
        )
        self.save_btn.grid(row=5, column=0, columnspan=6, pady=20)
        
        # --- Table Frame (Bottom Section) ---
        self.table_frame = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=10)
        self.table_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)
        
        # Table Title
        ctk.CTkLabel(
            self.table_frame,
            text="سجل المدفوعات",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2196F3"
        ).grid(row=0, column=0, pady=(10, 5), sticky="w", padx=15)
        
        # Treeview Frame
        tree_frame = ctk.CTkFrame(self.table_frame, fg_color="#3a3a3a", corner_radius=8)
        tree_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Treeview for payments history
        columns = ("id", "order", "amount", "type", "status", "remaining", "date")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure style
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2d2d2d", foreground="white", fieldbackground="#2d2d2d", rowheight=30)
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#4CAF50", font=("Arial", 12, "bold"))
        style.map("Treeview", background=[("selected", "#2196F3")])
        
        self.tree.heading("id", text="رقم الدفعة")
        self.tree.heading("order", text="الطلب")
        self.tree.heading("amount", text="المبلغ (ج.م)")
        self.tree.heading("type", text="نوع الدفع")
        self.tree.heading("status", text="الحالة")
        self.tree.heading("remaining", text="المتبقي")
        self.tree.heading("date", text="التاريخ والوقت")
        
        self.tree.column("id", width=90, anchor="center")
        self.tree.column("order", width=90, anchor="center")
        self.tree.column("amount", width=120, anchor="center")
        self.tree.column("type", width=130, anchor="center")
        self.tree.column("status", width=130, anchor="center")
        self.tree.column("remaining", width=120, anchor="center")
        self.tree.column("date", width=180, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=5)
    
    def show_server_offline_message(self):
        """Show server offline message in the UI"""
        # Clear existing widgets in input frame
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        
        # Show offline message
        ctk.CTkLabel(
            self.input_frame,
            text="⚠️ السيرفر غير متصل",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#f44336"
        ).grid(row=0, column=0, columnspan=6, pady=30)
        
        ctk.CTkLabel(
            self.input_frame,
            text="قم بتشغيل السيرفر باستخدام الأمر:\npython -m uvicorn main:app --reload",
            font=ctk.CTkFont(size=14),
            text_color="white"
        ).grid(row=1, column=0, columnspan=6, pady=20)
        
        self.update_status("⚠️ السيرفر غير متصل")
    
    # ==========================================
    # Data Loading
    # ==========================================
    
    def load_pharmacies(self):
        """Load pharmacies from API"""
        # Check server health
        if not self.check_server_health():
            self.show_server_offline_message()
            return
        
        try:
            self.update_status("جاري تحميل الصيدليات...")
            
            pharmacies = self.api_client.get_pharmacies()
            self.orders_cache = self.api_client.get_orders() if hasattr(self.api_client, "get_orders") else []
            self.update_summary_cards(pharmacies, self.orders_cache)
            
            if not pharmacies:
                # No pharmacies found
                self.pharmacy_menu.configure(values=["لا توجد صيدليات"])
                self.pharmacy_var.set("لا توجد صيدليات")
                self.save_btn.configure(state="disabled")
                self.amount_entry.configure(state="disabled")
                self.balance_var.set("0.00")
                self.update_status("لا توجد صيدليات")
                return
            
            # Build pharmacy dictionary
            self.pharmacy_dict = {p.get("name", f"صيدلية {p.get('id')}"): p for p in pharmacies}
            pharmacy_names = list(self.pharmacy_dict.keys())
            
            # Update pharmacy menu
            self.pharmacy_menu.configure(values=pharmacy_names)
            self.pharmacy_var.set(pharmacy_names[0] if pharmacy_names else "")
            
            # Load first pharmacy data
            if pharmacy_names:
                self.on_pharmacy_select(pharmacy_names[0])
            
            # Enable controls
            self.save_btn.configure(state="normal")
            self.amount_entry.configure(state="normal")
            
            self.update_status(f"✅ تم تحميل {len(pharmacies)} صيدلية")
            
        except Exception as e:
            self.update_status("❌ خطأ في تحميل الصيدليات")
            self.show_error(f"فشل تحميل الصيدليات:\n{str(e)}")
    
    # ==========================================
    # Pharmacy Selection Handler
    # ==========================================

    def update_summary_cards(self, pharmacies=None, orders=None):
        pharmacies = pharmacies if pharmacies is not None else list(self.pharmacy_dict.values())
        orders = orders if orders is not None else self.orders_cache
        total_due = sum(self.get_pharmacy_balance(p) for p in pharmacies)
        total_remaining = 0.0
        total_paid = 0.0
        unpaid_count = 0
        for order in orders or []:
            total_remaining += self.get_order_remaining(order)
            total_paid += self.get_order_paid(order)
            if (order.get("payment_status") or "unpaid") != "full":
                unpaid_count += 1
        self.total_due_var.set(self.format_money(total_due))
        self.total_paid_var.set(self.format_money(total_paid))
        self.total_remaining_var.set(self.format_money(total_remaining if total_remaining > 0 else total_due))
        self.unpaid_orders_var.set(str(unpaid_count))

    def update_order_menu_for_pharmacy(self, pharmacy_id):
        self.order_dict = {}
        options = ["بدون طلب محدد"]
        for order in self.orders_cache:
            if order.get("pharmacy_id") != pharmacy_id:
                continue
            remaining = self.get_order_remaining(order)
            status = order.get("payment_status") or "unpaid"
            if status == "full" or remaining <= 0:
                continue
            label = f"طلب #{order.get('id')} - متبقي {self.format_money(remaining)}"
            self.order_dict[label] = order
            options.append(label)
        self.order_menu.configure(values=options)
        self.order_var.set(options[0])
        self.update_order_payment_preview()

    def update_order_payment_preview(self):
        order = self.get_selected_order()
        if not order:
            self.order_preview_var.set("إجمالي الطلب: 0.00 | مدفوع سابقًا: 0.00 | المتبقي: 0.00")
            return
        total = self.get_order_total(order)
        paid = self.get_order_paid(order)
        remaining = self.get_order_remaining(order)
        order_status = self.translate_order_status(order.get("status"))
        payment_status = self.translate_payment_status(order.get("payment_status") or "unpaid")
        if (order.get("payment_status") or "") == "full" or remaining <= 0:
            payment_status = "دفع كامل"
        self.order_preview_var.set(
            f"الطلب: {order_status} | الدفع: {payment_status} | إجمالي: {self.format_money(total)} | مدفوع: {self.format_money(paid)} | متبقي: {self.format_money(remaining)}"
        )
    
    def on_pharmacy_select(self, pharmacy_name):
        """Update balance and payments table when pharmacy is selected"""
        if not pharmacy_name or pharmacy_name == "لا توجد صيدليات":
            return
        
        if pharmacy_name not in self.pharmacy_dict:
            return
        
        try:
            pharmacy = self.pharmacy_dict[pharmacy_name]
            pharmacy_id = pharmacy.get("id")
            balance = self.get_pharmacy_balance(pharmacy)
            
            # Update balance display with color
            if balance > 0:
                self.balance_label.configure(text_color="#FFA500")  # Orange for debt
            else:
                self.balance_label.configure(text_color="#4CAF50")  # Green for zero
            
            self.balance_var.set(self.format_money(balance))
            self.update_order_menu_for_pharmacy(pharmacy_id)
            
            # Load payments history
            self.refresh_payments_table(pharmacy_id)
            
        except Exception as e:
            self.update_status(f"❌ خطأ في تحميل بيانات الصيدلية: {str(e)}")
    
    # ==========================================
    # Payment Operations
    # ==========================================
    
    def save_payment(self):
        """Record payment and update balance"""
        # Prevent duplicate submissions
        if self.is_saving:
            return
        
        # Check server health
        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return
        
        # Validate pharmacy selection
        pharmacy_name = self.pharmacy_var.get()
        if not pharmacy_name or pharmacy_name not in self.pharmacy_dict:
            self.show_error("برجاء اختيار صيدلية صحيحة")
            return
        
        payment_type = self.get_payment_type()
        selected_order = self.get_selected_order()
        notes = self.notes_entry.get().strip()

        # Validate amount
        amount_text = self.amount_entry.get().strip()
        if not amount_text and payment_type == "full":
            due_for_full = self.get_order_remaining(selected_order) if selected_order else self.get_pharmacy_balance(self.pharmacy_dict[pharmacy_name])
            amount_text = str(due_for_full)
        if not amount_text and payment_type in ("deferred", "collect_on_delivery"):
            amount_text = "0"
        if not amount_text:
            self.show_error("برجاء إدخال المبلغ")
            self.amount_entry.focus()
            return
        
        try:
            amount = self.safe_float(amount_text, "المبلغ")
            if payment_type not in ("deferred", "collect_on_delivery") and amount <= 0:
                raise ValueError("المبلغ يجب أن يكون أكبر من صفر")
            if amount < 0:
                raise ValueError("المبلغ لا يمكن أن يكون سالبًا")
        except ValueError as e:
            self.show_error(str(e))
            self.amount_entry.focus()
            return
        
        # Get pharmacy data
        pharmacy = self.pharmacy_dict[pharmacy_name]
        pharmacy_id = pharmacy.get("id")
        current_balance = self.get_pharmacy_balance(pharmacy)

        due_limit = self.get_order_remaining(selected_order) if selected_order else current_balance
        if selected_order and due_limit <= 0:
            self.show_warning("هذا الطلب مكتمل السداد بالفعل")
            return
        if amount > due_limit:
            self.show_error(f"المبلغ المحصل ({self.format_money(amount)}) أكبر من المستحق ({self.format_money(due_limit)})")
            self.amount_entry.focus()
            return

        if payment_type == "collect_on_delivery" and selected_order:
            order_status = selected_order.get("status")
            if order_status not in ("with_driver", "on_the_way", "delivered", "completed"):
                self.show_error("تحصيل عند الاستلام متاح فقط عندما يكون الطلب مع المندوب أو في الطريق أو تم التسليم")
                return
        if amount > current_balance:
            self.show_error(f"المبلغ المحصل ({self.format_money(amount)}) أكبر من مديونية الصيدلية الحالية ({self.format_money(current_balance)})")
            self.amount_entry.focus()
            return

        if current_balance == 0 and payment_type not in ("deferred", "collect_on_delivery"):
            self.show_warning("لا توجد مديونية على هذه الصيدلية")
            return
        
        try:
            # Disable save button during processing
            self.is_saving = True
            self.save_btn.configure(text="جاري الحفظ...", state="disabled")
            self.set_pharmacy_controls_state("disabled")
            
            self.update_status("جاري تسجيل التحصيل...")
            
            remaining_after = max(due_limit - amount, 0.0)
            payment_status = "full" if amount > 0 and remaining_after <= 0 else ("partial" if amount > 0 else payment_type)

            # Record payment
            result = self.api_client.add_payment(
                pharmacy_id,
                amount,
                order_id=selected_order.get("id") if selected_order else None,
                payment_type=payment_type,
                payment_status=payment_status,
                amount_paid=amount,
                remaining_amount=remaining_after,
                payment_notes=notes,
            )
            
            if result:
                # Success
                new_balance = result.get("new_balance", current_balance - amount)
                
                self.show_info(f"✅ تم تسجيل التحصيل بنجاح\nالمبلغ: {self.format_money(amount)} جنيه\nالرصيد المتبقي: {self.format_money(new_balance)} جنيه")
                if messagebox.askyesno("إيصال التحصيل", "هل تريد حفظ إيصال PDF لهذه الدفعة؟"):
                    self.export_payment_receipt_pdf(
                        result,
                        pharmacy,
                        amount,
                        new_balance
                    )
                
                # Clear amount entry
                self.amount_entry.delete(0, "end")
                self.notes_entry.delete(0, "end")
                
                # Update local pharmacy data
                self.pharmacy_dict[pharmacy_name]['balance'] = new_balance
                self.orders_cache = self.api_client.get_orders() if hasattr(self.api_client, "get_orders") else self.orders_cache
                self.update_summary_cards()
                self.update_order_menu_for_pharmacy(pharmacy_id)
                
                # Update balance display
                if new_balance > 0:
                    self.balance_label.configure(text_color="#FFA500")
                else:
                    self.balance_label.configure(text_color="#4CAF50")
                self.balance_var.set(self.format_money(new_balance))
                
                # Refresh payments table
                self.refresh_payments_table(pharmacy_id)
                
                self.update_status(f"✅ تم تسجيل التحصيل: {self.format_money(amount)} جنيه")
                
            else:
                # API returned None (failure)
                self.show_error("فشل تسجيل التحصيل. تأكد من أن السيرفر يعمل وأن البيانات صحيحة.")
                self.update_status("❌ فشل تسجيل التحصيل")
                
        except Exception as e:
            error_msg = str(e)
            if "exceeds" in error_msg.lower() or "balance" in error_msg.lower():
                self.show_error(f"المبلغ أكبر من المديونية الحالية.\n\n{error_msg}")
            else:
                self.show_error(f"حدث خطأ أثناء تسجيل التحصيل:\n{error_msg}")
            self.update_status("❌ خطأ في تسجيل التحصيل")
            
        finally:
            # Re-enable save button
            self.is_saving = False
            self.save_btn.configure(text="💾 حفظ وتحصيل", state="normal")
            self.set_pharmacy_controls_state("normal")
    
    def export_payment_receipt_pdf(self, payment, pharmacy, amount, remaining_balance):
        """Export a payment receipt as PDF."""
        try:
            from reportlab.lib.pagesizes import A5
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
        except Exception:
            self.show_error("تصدير الإيصال يحتاج تثبيت reportlab")
            return
        
        payment_id = payment.get("id", datetime.now().strftime("%Y%m%d%H%M%S"))
        default_name = f"receipt_{payment_id}.pdf"
        file_path = filedialog.asksaveasfilename(
            title="حفظ إيصال التحصيل",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")]
        )
        if not file_path:
            return
        
        try:
            styles = getSampleStyleSheet()
            doc = SimpleDocTemplate(file_path, pagesize=A5)
            story = [
                Paragraph("Al Nada Pharmacy Store", styles["Title"]),
                Spacer(1, 10),
                Paragraph(f"Payment Receipt #{payment_id}", styles["Heading2"]),
                Spacer(1, 10),
            ]
            table_data = [
                ["Pharmacy", pharmacy.get("name", "")],
                ["Date", datetime.now().strftime("%Y-%m-%d %H:%M")],
                ["Amount", f"{self.format_money(amount)} EGP"],
                ["Remaining Balance", f"{self.format_money(remaining_balance)} EGP"],
            ]
            table = Table(table_data)
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#2d2d2d")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ]))
            story.append(table)
            doc.build(story)
            self.show_info("تم حفظ إيصال التحصيل PDF بنجاح")
        except Exception as e:
            self.show_error(f"فشل حفظ الإيصال:\n{str(e)}")
    
    # ==========================================
    # Payments Table Management
    # ==========================================
    
    def refresh_payments_table(self, pharmacy_id):
        """Load and display payments history for a pharmacy"""
        self.clear_payments_table()
        
        if not pharmacy_id:
            return
        
        try:
            self.update_status("جاري تحميل المدفوعات...")
            
            payments = self.api_client.get_pharmacy_payments(pharmacy_id)
            
            if not payments:
                # Show empty message in table
                self.tree.insert("", "end", values=("", "", "لا توجد مدفوعات", "", "", "", ""))
                self.update_status("لا توجد مدفوعات لهذه الصيدلية")
                return
            
            # Sort payments by date descending (newest first)
            payments.sort(key=lambda x: x.get("date", ""), reverse=True)
            
            # Insert payments into table
            for payment in payments:
                payment_id = payment.get("id", "-")
                order_id = payment.get("order_id") or "-"
                amount = payment.get("amount", 0)
                payment_type = self.translate_payment_status(payment.get("payment_type", "cash"))
                payment_status = self.translate_payment_status(payment.get("payment_status", "partial"))
                remaining = payment.get("remaining_amount", 0)
                date_str = payment.get("date", "-")
                
                # Format date for display
                if date_str and date_str != "-":
                    # Clean date format (remove T and milliseconds)
                    if "T" in date_str:
                        date_str = date_str.replace("T", " ")
                    if "." in date_str:
                        date_str = date_str.split(".")[0]
                    if len(date_str) > 16:
                        date_str = date_str[:16]
                else:
                    date_str = "-"
                
                self.tree.insert("", "end", values=(
                    payment_id,
                    order_id,
                    self.format_money(amount),
                    payment_type,
                    payment_status,
                    self.format_money(remaining),
                    date_str
                ))
            
            self.update_status(f"✅ تم تحميل {len(payments)} دفعة")
            
        except Exception as e:
            self.update_status("❌ خطأ في تحميل المدفوعات")
            self.tree.insert("", "end", values=("", "", "خطأ في تحميل البيانات", "", "", "", ""))
