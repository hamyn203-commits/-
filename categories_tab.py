import customtkinter as ctk
from tkinter import messagebox
from api_client import APIClient
from rtl_utils import rtl


# Modern glassmorphism palette
BG = "#0A0E1A"
SURFACE = "#141821"
CARD_BG = "#1A1F2E"
CARD_BORDER = "#2A3348"
GLASS_OVERLAY = "rgba(255, 255, 255, 0.05)"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B8C5E0"
TEXT_MUTED = "#7A8BA0"

SUCCESS = "#10B981"
SUCCESS_HOVER = "#059669"
INFO = "#3B82F6"
INFO_HOVER = "#2563EB"
PRIMARY = "#6366F1"
PRIMARY_HOVER = "#4F46E5"
DANGER = "#EF4444"
DANGER_HOVER = "#DC2626"
NEUTRAL = "#6B7280"

# Enhanced color palette for category accents
CARD_ACCENTS = [
    "#10B981",  # Emerald
    "#3B82F6",  # Blue
    "#F59E0B",  # Amber
    "#8B5CF6",  # Violet
    "#06B6D4",  # Cyan
    "#F43F5E",  # Rose
    "#84CC16",  # Lime
    "#F97316",  # Orange
]


class CategoriesTab(ctk.CTkFrame):
    def __init__(self, master, api_client=None, status_callback=None, role="admin", open_products_callback=None):
        super().__init__(master)
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.role = role or "admin"
        self.open_products_callback = open_products_callback
        self.categories = []

        self.configure(fg_color=BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_ui()
        self.load_categories()

    # ----------------------------
    # Helpers
    # ----------------------------
    def ar(self, text):
        return rtl("" if text is None else str(text))

    def can_manage_categories(self):
        return self.role == "admin"

    def update_status(self, message):
        if self.status_callback:
            try:
                self.status_callback(self.ar(message))
            except Exception:
                pass

    # ----------------------------
    # UI
    # ----------------------------
    def create_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        title_wrap = ctk.CTkFrame(header, fg_color="transparent")
        title_wrap.grid(row=0, column=0, sticky="ew")
        title_wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_wrap,
            text=self.ar("التصنيفات"),
            font=("Arial", 30, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="e",
            justify="right",
        ).grid(row=0, column=0, sticky="e")

        ctk.CTkLabel(
            title_wrap,
            text=self.ar("إدارة تصنيفات المنتجات داخل مخزن الندا"),
            font=("Arial", 12),
            text_color=TEXT_SECONDARY,
            anchor="e",
            justify="right",
        ).grid(row=1, column=0, sticky="e", pady=(4, 0))

        self.add_btn = ctk.CTkButton(
            header,
            text=self.ar("إضافة تصنيف"),
            width=150,
            height=38,
            corner_radius=12,
            fg_color=SUCCESS,
            hover_color=SUCCESS_HOVER,
            font=("Arial", 13, "bold"),
            command=self.show_add_dialog,
        )
        self.add_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(14, 0))
        if not self.can_manage_categories():
            self.add_btn.configure(state="disabled")

        self.cards_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=SURFACE,
            corner_radius=20,
            border_color=CARD_BORDER,
            border_width=1,
            scrollbar_button_color=PRIMARY,
            scrollbar_button_hover_color=PRIMARY_HOVER,
        )
        self.cards_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        # Stable 2-column layout
        for col in range(2):
            self.cards_frame.grid_columnconfigure(col, weight=1, uniform="category_cards")

    def clear_cards(self):
        for widget in self.cards_frame.winfo_children():
            widget.destroy()

    # ----------------------------
    # Data rendering
    # ----------------------------
    def load_categories(self):
        self.clear_cards()
        try:
            self.categories = self.api_client.get_categories()
        except Exception:
            self.categories = []

        if not self.categories:
            empty = ctk.CTkFrame(self.cards_frame, fg_color="transparent")
            empty.grid(row=0, column=0, columnspan=3, sticky="ew", padx=12, pady=38)
            ctk.CTkLabel(
                empty,
                text=self.ar("لا توجد تصنيفات حتى الآن"),
                font=("Arial", 15),
                text_color=TEXT_SECONDARY,
                anchor="center",
                justify="center",
            ).pack()
            self.update_status("لا توجد تصنيفات")
            return

        # Stable 2-column grid for predictable card spacing
        cols_per_row = 2
        for i, category in enumerate(self.categories):
            row = i // cols_per_row
            col = i % cols_per_row
            accent = CARD_ACCENTS[i % len(CARD_ACCENTS)]
            try:
                self.create_category_card(category, row, col, accent)
            except Exception:
                # Keep screen usable even if one card has malformed data
                continue

        self.update_status(f"تم تحميل {len(self.categories)} تصنيف")

    def create_category_card(self, category, row, col, accent_color):
        card = ctk.CTkFrame(
            self.cards_frame,
            fg_color="#20242f",
            corner_radius=16,
            border_width=1,
            border_color=CARD_BORDER,
            height=300,
        )
        card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew", padx=12, pady=10)
        content.grid_columnconfigure(0, weight=1)

        # Top accent line
        accent_frame = ctk.CTkFrame(
            content,
            height=6,
            fg_color=accent_color,
            corner_radius=999,
        )
        accent_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 10))
        accent_frame.grid_propagate(False)

        top_section = ctk.CTkFrame(content, fg_color="transparent")
        top_section.grid(row=1, column=0, sticky="ew")
        top_section.grid_columnconfigure(0, weight=1)

        product_count = int(category.get("product_count", 0) or 0)
        count_badge = ctk.CTkFrame(
            top_section,
            fg_color="#252525",
            corner_radius=14,
            border_width=1
        )
        count_badge.configure(border_color=accent_color)
        count_badge.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            count_badge,
            text=self.ar(f"{product_count} منتج"),
            font=("Arial", 11, "bold"),
            text_color=accent_color,
        ).pack(padx=10, pady=4)

        category_name = self.ar(category.get("name", "بدون اسم"))
        name_label = ctk.CTkLabel(
            content,
            text=category_name,
            font=("Arial", 20, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="e",
            justify="right",
            wraplength=280,
        )
        name_label.grid(row=2, column=0, sticky="ew", pady=(10, 6))

        details_label = ctk.CTkLabel(
            content,
            text=self.ar(f"عدد المنتجات: {product_count}"),
            font=("Arial", 13),
            text_color=TEXT_SECONDARY,
            anchor="e",
            justify="right",
        )
        details_label.grid(row=3, column=0, sticky="ew", pady=(2, 2))

        created_at = str(category.get("created_at", ""))[:10] or "-"
        date_label = ctk.CTkLabel(
            content,
            text=self.ar(f"تاريخ الإنشاء: {created_at}"),
            font=("Arial", 11),
            text_color=TEXT_MUTED,
            anchor="e",
            justify="right",
        )
        date_label.grid(row=4, column=0, sticky="ew", pady=(2, 10))

        view_btn = ctk.CTkButton(
            content,
            text=self.ar("عرض المنتجات"),
            height=38,
            corner_radius=12,
            fg_color=INFO,
            hover_color=INFO_HOVER,
            font=("Arial", 13, "bold"),
            command=lambda c=category: self.open_category_products(c),
        )
        view_btn.grid(row=5, column=0, sticky="ew", pady=(2, 8))

        add_product_btn = ctk.CTkButton(
            content,
            text=self.ar("إضافة منتج"),
            height=38,
            corner_radius=12,
            fg_color=SUCCESS,
            hover_color=SUCCESS_HOVER,
            font=("Arial", 13, "bold"),
            command=lambda c=category: self.add_product_in_category(c),
        )
        add_product_btn.grid(row=6, column=0, sticky="ew", pady=(0, 8))

        actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        actions_frame.grid(row=7, column=0, sticky="ew", pady=(0, 2))
        actions_frame.grid_columnconfigure((0, 1), weight=1)

        edit_btn = ctk.CTkButton(
            actions_frame,
            text=self.ar("تعديل"),
            height=36,
            corner_radius=12,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            font=("Arial", 12, "bold"),
            command=lambda c=category: self.show_edit_dialog(c),
        )
        edit_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        delete_btn = ctk.CTkButton(
            actions_frame,
            text=self.ar("حذف"),
            height=36,
            corner_radius=12,
            fg_color=DANGER,
            hover_color=DANGER_HOVER,
            font=("Arial", 12, "bold"),
            command=lambda c=category: self.delete_category(c),
        )
        delete_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Disable management buttons for non-admin users
        if not self.can_manage_categories():
            edit_btn.configure(state="disabled")
            delete_btn.configure(state="disabled")

    # ----------------------------
    # Navigation bridge
    # ----------------------------
    def open_category_products(self, category):
        category_name = category.get("name", "")
        if not category_name:
            return
        if self.open_products_callback:
            self.open_products_callback(category_name, False)
        else:
            self.update_status(f"التصنيف المحدد: {category_name}")

    def add_product_in_category(self, category):
        category_name = category.get("name", "")
        if not category_name:
            return
        if self.open_products_callback:
            self.open_products_callback(category_name, True)
        else:
            self.update_status(f"إضافة منتج في: {category_name}")

    # ----------------------------
    # Dialogs + API logic (unchanged behavior)
    # ----------------------------
    def show_category_dialog(self, title, initial_name, on_save):
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.ar(title))
        dialog.geometry("390x230")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Enhanced glassmorphism dialog frame
        frame = ctk.CTkFrame(
            dialog, 
            fg_color=CARD_BG, 
            corner_radius=20, 
            border_width=2, 
            border_color=CARD_BORDER
        )
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Dialog title with enhanced styling
        ctk.CTkLabel(
            frame,
            text=self.ar(title),
            font=("Arial", 21, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="e",
            justify="right",
        ).pack(fill="x", padx=20, pady=(18, 15))

        # Enhanced entry field with glassmorphism
        name_entry = ctk.CTkEntry(
            frame,
            width=320,
            height=45,
            corner_radius=12,
            placeholder_text=self.ar("اسم التصنيف"),
            justify="right",
            fg_color="#1A1F2E",
            border_color=CARD_BORDER,
            border_width=1,
            font=("Arial", 13),
        )
        name_entry.insert(0, initial_name or "")
        name_entry.pack(pady=10)
        name_entry.focus()

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning(self.ar("بيانات ناقصة"), self.ar("اسم التصنيف مطلوب"))
                return
            if on_save(name):
                dialog.destroy()
                self.load_categories()

        # Enhanced button frame
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(18, 15))
        buttons.grid_columnconfigure((0, 1), weight=1)

        # Save button with glassmorphism
        ctk.CTkButton(
            buttons,
            text=self.ar("حفظ"),
            height=40,
            corner_radius=12,
            fg_color=SUCCESS,
            hover_color=SUCCESS_HOVER,
            font=("Arial", 13, "bold"),
            command=save,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Cancel button with glassmorphism
        ctk.CTkButton(
            buttons,
            text=self.ar("إلغاء"),
            height=40,
            corner_radius=12,
            fg_color=NEUTRAL,
            hover_color="#4B5563",
            font=("Arial", 13, "bold"),
            command=dialog.destroy,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        dialog.bind("<Return>", lambda _event: save())

    def show_add_dialog(self):
        if not self.can_manage_categories():
            messagebox.showwarning(self.ar("الصلاحيات"), self.ar("هذه العملية متاحة للمدير فقط"))
            return

        def save(name):
            result = self.api_client.create_category(name)
            if result:
                messagebox.showinfo(self.ar("نجاح"), self.ar("تم إضافة التصنيف بنجاح"))
                return True
            messagebox.showerror(self.ar("خطأ"), self.ar("فشل إضافة التصنيف. قد يكون الاسم موجودًا بالفعل."))
            return False

        self.show_category_dialog("إضافة تصنيف", "", save)

    def show_edit_dialog(self, category):
        if not self.can_manage_categories():
            messagebox.showwarning(self.ar("الصلاحيات"), self.ar("هذه العملية متاحة للمدير فقط"))
            return

        def save(name):
            result = self.api_client.update_category(category.get("id"), name)
            if result:
                messagebox.showinfo(self.ar("نجاح"), self.ar("تم تعديل التصنيف بنجاح"))
                return True
            messagebox.showerror(self.ar("خطأ"), self.ar("فشل تعديل التصنيف"))
            return False

        self.show_category_dialog("تعديل التصنيف", category.get("name", ""), save)

    def delete_category(self, category):
        if not self.can_manage_categories():
            messagebox.showwarning(self.ar("الصلاحيات"), self.ar("هذه العملية متاحة للمدير فقط"))
            return
        if category.get("product_count", 0):
            messagebox.showwarning(self.ar("لا يمكن الحذف"), self.ar("لا يمكن حذف تصنيف مرتبط بمنتجات"))
            return
        if not messagebox.askyesno(
            self.ar("تأكيد الحذف"),
            self.ar(f"هل تريد حذف التصنيف: {category.get('name', '')}؟"),
        ):
            return
        if self.api_client.delete_category(category.get("id")):
            messagebox.showinfo(self.ar("نجاح"), self.ar("تم حذف التصنيف بنجاح"))
            self.load_categories()
        else:
            messagebox.showerror(self.ar("خطأ"), self.ar("فشل حذف التصنيف"))
