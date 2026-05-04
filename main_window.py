"""
Main Window for Pharmacy Management System Desktop Application
Contains sidebar navigation and main content area
"""

import customtkinter as ctk
from tkinter import messagebox
from api_client import APIClient
from dashboard_tab import DashboardTab
from products_tab import ProductsTab
from categories_tab import CategoriesTab
from suppliers_tab import SuppliersTab
from purchases_tab import PurchasesTab
from pharmacies_tab import PharmaciesTab
from orders_tab import OrdersTab
from payments_tab import PaymentsTab
from settings_tab import SettingsTab
from backup_tab import BackupTab
from alerts_tab import AlertsTab
from reports_tab import ReportsTab
from rtl_utils import rtl

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow:
    """
    Main application window with sidebar navigation
    """
    
    def __init__(self, username: str = None, role: str = "admin"):
        """
        Initialize the main window
        
        Args:
            username (str): Logged-in username (optional)
        """
        self.username = username or "Admin"
        self.role = role or "admin"
        self.api_client = APIClient()
        self.current_tab = None
        
        # Create the main window
        self.window = ctk.CTk()
        self.window.title(f"{rtl('نظام إدارة شركة الأدوية')} - Pharmaceutical Management System")
        self.window.geometry("1200x700")
        
        # Center the window on screen
        self.center_window()
        
        # Configure grid layout for main window
        self.window.grid_rowconfigure(0, weight=1)
        self.window.grid_columnconfigure(0, weight=0)  # Sidebar - fixed width
        self.window.grid_columnconfigure(1, weight=1)  # Main content - expands
        
        # Create UI components
        self.create_sidebar()
        self.apply_role_permissions()
        self.create_main_frame()
        
        # Check server health (optional, doesn't block startup)
        self.check_server_status()
        self.create_auto_backup_if_needed()
        self.show_startup_alerts()
        
        # Set default view to dashboard
        self.show_dashboard()
        
        # Bind escape key to close window
        self.window.bind('<Escape>', lambda e: self.logout())
        
        # Handle window close event
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def center_window(self):
        """Center the window on the screen"""
        self.window.update_idletasks()
        width = 1200
        height = 700
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def check_server_status(self):
        """Check server health and update status"""
        try:
            if hasattr(self.api_client, 'health_check'):
                if self.api_client.health_check():
                    self.update_status("✅ السيرفر متصل")
                else:
                    self.update_status("⚠️ السيرفر غير متصل - شغّل: python -m uvicorn main:app --reload")
            else:
                # Try a simple test connection
                import requests
                try:
                    response = requests.get(f"{self.api_client.base_url}/health", timeout=3)
                    if response.status_code == 200:
                        self.update_status("✅ السيرفر متصل")
                    else:
                        self.update_status("⚠️ السيرفر غير متصل")
                except:
                    self.update_status("⚠️ السيرفر غير متصل - شغّل: python -m uvicorn main:app --reload")
        except:
            self.update_status("⚠️ لا يمكن التحقق من اتصال السيرفر")
    
    def create_auto_backup_if_needed(self):
        """Create one automatic database backup per day when enabled."""
        try:
            import json
            import os
            import shutil
            from datetime import datetime

            settings = {}
            if os.path.exists("app_settings.json"):
                with open("app_settings.json", "r", encoding="utf-8") as file:
                    settings = json.load(file)
            if settings.get("auto_backup_enabled", True) is False:
                return
            source = "pharmacy.db"
            if not os.path.exists(source):
                return
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            target = os.path.join(backup_dir, f"auto_backup_{today}.db")
            if not os.path.exists(target):
                shutil.copy2(source, target)
                self.update_status(f"تم إنشاء نسخة احتياطية تلقائية: {target}")
        except Exception as exc:
            self.update_status(f"تعذر إنشاء النسخة الاحتياطية التلقائية: {exc}")

    def show_startup_alerts(self):
        """Summarize important alerts on startup without blocking the app."""
        try:
            from datetime import datetime, timedelta

            if hasattr(self.api_client, "health_check") and not self.api_client.health_check():
                return
            products = self.api_client.get_products()
            orders = self.api_client.get_orders()
            low_stock = 0
            expiring = 0
            today = datetime.now().date()
            soon = today + timedelta(days=30)
            for product in products:
                quantity = int(product.get("quantity") or 0)
                if quantity <= 5:
                    low_stock += 1
                raw_date = str(product.get("expiry_date") or "").split("T")[0].split(" ")[0]
                try:
                    expiry = datetime.strptime(raw_date, "%Y-%m-%d").date()
                    if today <= expiry <= soon:
                        expiring += 1
                except Exception:
                    pass
            pending_orders = sum(1 for order in orders if str(order.get("status", "")).lower() == "pending")
            if low_stock or expiring or pending_orders:
                self.update_status(
                    f"تنبيهات اليوم: مخزون منخفض {low_stock} | صلاحية قريبة {expiring} | طلبات جديدة {pending_orders}"
                )
        except Exception:
            pass

    def create_sidebar(self):
        """Create the sidebar with navigation buttons"""
        
        # Sidebar frame
        self.sidebar = ctk.CTkFrame(
            self.window, 
            width=200, 
            corner_radius=0,
            fg_color="#1a1a1a"
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.configure(width=200)
        
        # App title in sidebar
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(pady=(30, 20), padx=10, fill="x")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text=rtl("مخزن الندا"),
            font=("Arial", 22, "bold"),
            text_color="#4CAF50"
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Pharmacy System",
            font=("Arial", 12),
            text_color="gray"
        )
        subtitle_label.pack()
        
        # Separator
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color="#2d2d2d")
        separator.pack(fill="x", padx=10, pady=10)
        
        # Navigation buttons frame. It scrolls so future modules do not hide
        # the user panel or logout button on smaller screens.
        nav_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            width=190,
            corner_radius=0,
            scrollbar_button_color="#2d2d2d",
            scrollbar_button_hover_color="#4CAF50"
        )
        nav_frame.pack(pady=(12, 8), padx=0, fill="both", expand=True)
        
        # Dashboard button
        self.dashboard_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("الرئيسية"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_dashboard
        )
        self.dashboard_btn.pack(pady=5, padx=10, fill="x")
        
        # Products button
        self.products_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("المنتجات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_products
        )
        self.products_btn.pack(pady=5, padx=10, fill="x")

        self.categories_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("التصنيفات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_categories
        )
        self.categories_btn.pack(pady=5, padx=10, fill="x")

        self.suppliers_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("الموردين"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_suppliers
        )
        self.suppliers_btn.pack(pady=5, padx=10, fill="x")

        self.purchases_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("المشتريات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_purchases
        )
        self.purchases_btn.pack(pady=5, padx=10, fill="x")
        
        # Pharmacies button
        self.pharmacies_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("الصيدليات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_pharmacies
        )
        self.pharmacies_btn.pack(pady=5, padx=10, fill="x")
        
        # Orders button
        self.orders_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("الطلبات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_orders
        )
        self.orders_btn.pack(pady=5, padx=10, fill="x")
        
        # Payments button
        self.payments_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("التحصيلات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_payments
        )
        self.payments_btn.pack(pady=5, padx=10, fill="x")

        self.returns_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("المرتجعات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_returns
        )
        self.returns_btn.pack(pady=5, padx=10, fill="x")

        self.statements_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("كشف الحساب"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_statements
        )
        self.statements_btn.pack(pady=5, padx=10, fill="x")

        self.reports_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("التقارير"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_reports
        )
        self.reports_btn.pack(pady=5, padx=10, fill="x")

        self.alerts_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("التنبيهات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_alerts
        )
        self.alerts_btn.pack(pady=5, padx=10, fill="x")

        self.expiry_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("الصلاحية"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_expiry
        )
        self.expiry_btn.pack(pady=5, padx=10, fill="x")

        self.audit_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("سجل العمليات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_audit_log
        )
        self.audit_btn.pack(pady=5, padx=10, fill="x")

        self.backup_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("النسخ الاحتياطي"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_backup
        )
        self.backup_btn.pack(pady=5, padx=10, fill="x")

        self.settings_btn = ctk.CTkButton(
            nav_frame,
            text=rtl("الإعدادات"),
            width=180,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="transparent",
            hover_color="#2d2d2d",
            anchor="w",
            command=self.show_settings
        )
        self.settings_btn.pack(pady=5, padx=10, fill="x")
        
        # Spacer to push logout button to bottom
        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=4)
        spacer.pack(fill="x")
        
        # User info frame
        user_frame = ctk.CTkFrame(self.sidebar, fg_color="#2d2d2d", corner_radius=10)
        user_frame.pack(pady=(0, 15), padx=10, fill="x")
        
        user_icon = ctk.CTkLabel(
            user_frame,
            text="👤",
            font=("Arial", 20)
        )
        user_icon.pack(pady=(10, 0))
        
        user_name = ctk.CTkLabel(
            user_frame,
            text=self.username,
            font=("Arial", 12, "bold"),
            text_color="#4CAF50"
        )
        user_name.pack()
        
        user_role = ctk.CTkLabel(
            user_frame,
            text=rtl("مدير النظام"),
            font=("Arial", 10),
            text_color="gray"
        )
        user_role.pack(pady=(0, 10))
        
        # Logout button
        self.logout_btn = ctk.CTkButton(
            self.sidebar,
            text=rtl("تسجيل خروج"),
            width=180,
            height=40,
            font=("Arial", 13, "bold"),
            fg_color="#c0392b",
            hover_color="#e74c3c",
            corner_radius=8,
            command=self.logout
        )
        self.logout_btn.pack(pady=(0, 20), padx=10, fill="x")

    def get_role_label(self):
        """Return a readable Arabic label for the current role."""
        labels = {
            "admin": "مدير النظام",
            "accountant": "محاسب",
            "rep": "مندوب",
        }
        return labels.get(self.role, self.role)

    def allowed_tabs_for_role(self):
        """Define lightweight UI permissions without changing tab internals."""
        if self.role == "admin":
            return {
                "dashboard", "products", "categories", "suppliers", "purchases",
                "pharmacies", "orders", "payments", "returns", "statements",
                "reports", "alerts", "expiry", "audit", "backup", "settings"
            }
        if self.role == "accountant":
            return {
                "dashboard", "products", "categories", "pharmacies", "orders",
                "payments", "returns", "statements", "reports", "settings"
            }
        if self.role == "rep":
            return {"dashboard", "pharmacies", "orders", "statements"}
        return {"dashboard"}

    def is_tab_allowed(self, tab_name):
        return tab_name in self.allowed_tabs_for_role()

    def apply_role_permissions(self):
        """Hide sidebar entries that are not available for the selected role."""
        buttons = {
            "products": self.products_btn,
            "categories": self.categories_btn,
            "suppliers": self.suppliers_btn,
            "purchases": self.purchases_btn,
            "pharmacies": self.pharmacies_btn,
            "orders": self.orders_btn,
            "payments": self.payments_btn,
            "returns": self.returns_btn,
            "statements": self.statements_btn,
            "reports": self.reports_btn,
            "alerts": self.alerts_btn,
            "expiry": self.expiry_btn,
            "audit": self.audit_btn,
            "backup": self.backup_btn,
            "settings": self.settings_btn,
        }
        allowed = self.allowed_tabs_for_role()
        for tab_name, button in buttons.items():
            if tab_name not in allowed:
                button.pack_forget()

    def guard_tab_access(self, tab_name):
        if self.is_tab_allowed(tab_name):
            return True
        self.update_status("هذه الشاشة غير متاحة لهذا الدور")
        messagebox.showwarning("الصلاحيات", "هذه الشاشة غير متاحة لهذا الدور")
        return False
    
    def create_main_frame(self):
        """Create the main content frame"""
        
        # Main content frame
        self.main_frame = ctk.CTkFrame(
            self.window,
            corner_radius=0,
            fg_color="#1e1e1e"
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Header frame with title
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="#2d2d2d", height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_propagate(False)
        
        # Current time label
        self.update_clock()
        
        self.header_title = ctk.CTkLabel(
            self.header_frame,
            text=rtl("لوحة التحكم الرئيسية"),
            font=("Arial", 20, "bold"),
            text_color="#4CAF50"
        )
        self.header_title.pack(side="left", padx=25, pady=15)
        
        self.time_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=("Arial", 12),
            text_color="gray"
        )
        self.time_label.pack(side="right", padx=25, pady=15)
        
        # Content area (where tabs will be placed)
        self.content_area = ctk.CTkFrame(self.main_frame, fg_color="#1e1e1e")
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        
        # Status bar at bottom
        self.status_bar = ctk.CTkFrame(self.main_frame, height=30, fg_color="#2d2d2d")
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.status_bar.grid_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text=rtl("جاهز"),
            font=("Arial", 11),
            text_color="gray"
        )
        self.status_label.pack(side="left", padx=15, pady=5)
    
    def update_clock(self):
        """Update the clock display"""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.time_label.configure(text=current_time)
        except:
            pass
        # Update every second
        self.window.after(1000, self.update_clock)
    
    def clear_content(self):
        """Clear all widgets from content area safely"""
        for widget in list(self.content_area.winfo_children()):
            try:
                if widget and widget.winfo_exists():
                    widget.destroy()
            except:
                pass
    
    def update_header_title(self, title: str):
        """Update the header title"""
        try:
            self.header_title.configure(text=rtl(title))
        except:
            pass
    
    def set_active_button(self, active_button: str):
        """Highlight the active navigation button"""
        # Default style for inactive buttons
        inactive_style = {
            "fg_color": "transparent",
            "hover_color": "#2d2d2d"
        }
        
        # Active style
        active_style = {
            "fg_color": "#4CAF50",
            "hover_color": "#45a049"
        }
        
        # Reset all buttons to inactive style
        self.dashboard_btn.configure(**inactive_style)
        self.products_btn.configure(**inactive_style)
        self.categories_btn.configure(**inactive_style)
        self.suppliers_btn.configure(**inactive_style)
        self.purchases_btn.configure(**inactive_style)
        self.pharmacies_btn.configure(**inactive_style)
        self.orders_btn.configure(**inactive_style)
        self.payments_btn.configure(**inactive_style)
        self.returns_btn.configure(**inactive_style)
        self.statements_btn.configure(**inactive_style)
        self.reports_btn.configure(**inactive_style)
        self.alerts_btn.configure(**inactive_style)
        self.expiry_btn.configure(**inactive_style)
        self.audit_btn.configure(**inactive_style)
        self.backup_btn.configure(**inactive_style)
        self.settings_btn.configure(**inactive_style)
        
        # Highlight active button
        if active_button == "dashboard":
            self.dashboard_btn.configure(**active_style)
        elif active_button == "products":
            self.products_btn.configure(**active_style)
        elif active_button == "categories":
            self.categories_btn.configure(**active_style)
        elif active_button == "suppliers":
            self.suppliers_btn.configure(**active_style)
        elif active_button == "purchases":
            self.purchases_btn.configure(**active_style)
        elif active_button == "pharmacies":
            self.pharmacies_btn.configure(**active_style)
        elif active_button == "orders":
            self.orders_btn.configure(**active_style)
        elif active_button == "payments":
            self.payments_btn.configure(**active_style)
        elif active_button == "returns":
            self.returns_btn.configure(**active_style)
        elif active_button == "statements":
            self.statements_btn.configure(**active_style)
        elif active_button == "reports":
            self.reports_btn.configure(**active_style)
        elif active_button == "alerts":
            self.alerts_btn.configure(**active_style)
        elif active_button == "expiry":
            self.expiry_btn.configure(**active_style)
        elif active_button == "audit":
            self.audit_btn.configure(**active_style)
        elif active_button == "backup":
            self.backup_btn.configure(**active_style)
        elif active_button == "settings":
            self.settings_btn.configure(**active_style)
    
    def update_status(self, message: str):
        """
        Update status message in the status bar
        
        Args:
            message (str): Status message to display
        """
        try:
            # Update status label
            self.status_label.configure(text=rtl(message))
            
            # Update window title with status
            self.window.title(rtl(f"نظام إدارة الأدوية - {message}"))
        except:
            # If status bar doesn't exist yet, just print
            print(f"[Status] {message}")
    
    def navigate_to_tab(self, tab_name: str, product_filter=None):
        """
        Navigate to specific tab from dashboard
        This method is called by DashboardTab when cards are clicked
        
        Args:
            tab_name (str): Name of the tab to navigate to
        """
        if tab_name == "products":
            self.show_products(product_filter=product_filter)
        elif tab_name == "categories":
            self.show_categories()
        elif tab_name == "suppliers":
            self.show_suppliers()
        elif tab_name == "purchases":
            self.show_purchases()
        elif tab_name == "pharmacies":
            self.show_pharmacies()
        elif tab_name == "orders":
            self.show_orders()
        elif tab_name == "payments":
            self.show_payments()
        elif tab_name == "returns":
            self.show_returns()
        elif tab_name == "statements":
            self.show_statements()
        elif tab_name == "expiry":
            self.show_expiry()
        elif tab_name == "audit":
            self.show_audit_log()
        elif tab_name == "dashboard":
            self.show_dashboard()
    
    def show_dashboard(self):
        """Display dashboard tab in main content area"""
        self.clear_content()
        self.update_header_title("مخزن الندا")
        self.set_active_button("dashboard")
        
        # Create DashboardTab with navigation callback
        self.current_tab = DashboardTab(
            self.content_area, 
            api_client=self.api_client, 
            status_callback=self.update_status,
            navigation_callback=self.navigate_to_tab
        )
        self.current_tab.pack(fill="both", expand=True)
    
    def show_products(self, product_filter=None):
        """Display products tab in main content area"""
        if not self.guard_tab_access("products"):
            return
        self.clear_content()
        self.update_header_title("إدارة المنتجات")
        self.set_active_button("products")
        
        # Create ProductsTab with shared api_client
        self.current_tab = ProductsTab(
            self.content_area, 
            api_client=self.api_client, 
            status_callback=self.update_status,
            role=self.role,
            initial_filter=product_filter
        )
        self.current_tab.pack(fill="both", expand=True)

    def open_products_for_category(self, category_name: str, auto_open_add: bool = False):
        """Open products tab focused on a specific category."""
        if not self.guard_tab_access("products"):
            return
        self.clear_content()
        self.update_header_title("إدارة المنتجات")
        self.set_active_button("products")
        self.current_tab = ProductsTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status,
            role=self.role,
            initial_category=category_name,
            auto_open_add=auto_open_add
        )
        self.current_tab.pack(fill="both", expand=True)

    def show_categories(self):
        """Display categories tab in main content area"""
        if not self.guard_tab_access("categories"):
            return
        self.clear_content()
        self.update_header_title("إدارة التصنيفات")
        self.set_active_button("categories")

        self.current_tab = CategoriesTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status,
            role=self.role,
            open_products_callback=self.open_products_for_category
        )
        self.current_tab.pack(fill="both", expand=True)
        
    def show_pharmacies(self):
        """Display pharmacies tab in main content area"""
        if not self.guard_tab_access("pharmacies"):
            return
        self.clear_content()
        self.update_header_title("إدارة الصيدليات")
        self.set_active_button("pharmacies")
        
        # Create PharmaciesTab with shared api_client
        self.current_tab = PharmaciesTab(
            self.content_area, 
            api_client=self.api_client, 
            status_callback=self.update_status,
            role=self.role
        )
        self.current_tab.pack(fill="both", expand=True)
        
    def show_orders(self):
        """Display orders tab in main content area"""
        if not self.guard_tab_access("orders"):
            return
        self.clear_content()
        self.update_header_title("إدارة الطلبات")
        self.set_active_button("orders")
        
        # Create OrdersTab with shared api_client
        self.current_tab = OrdersTab(
            self.content_area, 
            api_client=self.api_client, 
            status_callback=self.update_status,
            role=self.role
        )
        self.current_tab.pack(fill="both", expand=True)
    
    def show_payments(self):
        """Display payments tab in main content area"""
        if not self.guard_tab_access("payments"):
            return
        self.clear_content()
        self.update_header_title("إدارة التحصيلات")
        self.set_active_button("payments")
        
        # Create PaymentsTab with shared api_client
        self.current_tab = PaymentsTab(
            self.content_area, 
            api_client=self.api_client, 
            status_callback=self.update_status
        )
        self.current_tab.pack(fill="both", expand=True)
    
    def show_placeholder(self, title: str, active_button: str):
        """Display a temporary placeholder screen."""
        self.clear_content()
        self.update_header_title(title)
        self.set_active_button(active_button)

        self.current_tab = ctk.CTkFrame(self.content_area, fg_color="#1e1e1e")
        self.current_tab.pack(fill="both", expand=True)

        card = ctk.CTkFrame(self.current_tab, fg_color="#2d2d2d", corner_radius=12)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            card,
            text=rtl("قريبًا"),
            font=("Arial", 34, "bold"),
            text_color="#4CAF50"
        ).pack(padx=80, pady=(45, 10))

        ctk.CTkLabel(
            card,
            text=rtl(title),
            font=("Arial", 16),
            text_color="gray"
        ).pack(padx=80, pady=(0, 45))

    def show_suppliers(self):
        """Display suppliers tab."""
        if not self.guard_tab_access("suppliers"):
            return
        self.clear_content()
        self.update_header_title("الموردين")
        self.set_active_button("suppliers")
        self.current_tab = SuppliersTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status,
            role=self.role
        )
        self.current_tab.pack(fill="both", expand=True)

    def show_purchases(self):
        """Display purchases tab."""
        if not self.guard_tab_access("purchases"):
            return
        self.clear_content()
        self.update_header_title("المشتريات والتوريد")
        self.set_active_button("purchases")
        self.current_tab = PurchasesTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status,
            role=self.role
        )
        self.current_tab.pack(fill="both", expand=True)

    def show_returns(self):
        """Display returns placeholder."""
        if not self.guard_tab_access("returns"):
            return
        self.show_placeholder("المرتجعات", "returns")

    def show_statements(self):
        """Display account statements placeholder."""
        if not self.guard_tab_access("statements"):
            return
        self.show_placeholder("كشف الحساب", "statements")

    def show_expiry(self):
        """Display expiry tracking placeholder."""
        if not self.guard_tab_access("expiry"):
            return
        self.show_placeholder("متابعة الصلاحية", "expiry")

    def show_audit_log(self):
        """Display audit log placeholder."""
        if not self.guard_tab_access("audit"):
            return
        self.show_placeholder("سجل العمليات", "audit")

    def show_reports(self):
        """Display reports tab."""
        if not self.guard_tab_access("reports"):
            return
        self.clear_content()
        self.update_header_title("التقارير")
        self.set_active_button("reports")

        self.current_tab = ReportsTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status,
            navigation_callback=self.navigate_to_tab
        )
        self.current_tab.pack(fill="both", expand=True)

    def show_alerts(self):
        """Display alerts tab."""
        if not self.guard_tab_access("alerts"):
            return
        self.clear_content()
        self.update_header_title("التنبيهات")
        self.set_active_button("alerts")

        self.current_tab = AlertsTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status
        )
        self.current_tab.pack(fill="both", expand=True)

    def show_backup(self):
        """Display backup tab."""
        if not self.guard_tab_access("backup"):
            return
        self.clear_content()
        self.update_header_title("النسخ الاحتياطي")
        self.set_active_button("backup")

        self.current_tab = BackupTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status
        )
        self.current_tab.pack(fill="both", expand=True)

    def show_settings(self):
        """Display settings tab."""
        if not self.guard_tab_access("settings"):
            return
        self.clear_content()
        self.update_header_title("الإعدادات")
        self.set_active_button("settings")

        self.current_tab = SettingsTab(
            self.content_area,
            api_client=self.api_client,
            status_callback=self.update_status,
            username=self.username,
            role=self.role
        )
        self.current_tab.pack(fill="both", expand=True)

    def logout(self):
        """Handle logout action"""
        if messagebox.askyesno("تأكيد تسجيل الخروج", "هل أنت متأكد من رغبتك في تسجيل الخروج؟"):
            self.window.destroy()
            # Return to login window
            try:
                from login_window import LoginWindow
                login = LoginWindow()
                login.run()
            except ImportError:
                # If login_window doesn't exist, just close
                pass
    
    def on_closing(self):
        """Handle window close event"""
        if messagebox.askyesno("تأكيد الإغلاق", "هل أنت متأكد من إغلاق التطبيق؟"):
            self.window.destroy()
    
    def run(self):
        """Run the main application loop"""
        self.window.mainloop()


# Main guard for testing
if __name__ == "__main__":
    # For testing without login
    app = MainWindow(username="admin")
    app.run()
