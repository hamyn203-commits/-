import customtkinter as ctk
from tkinter import messagebox
from main_window import MainWindow
from api_client import APIClient

class LoginWindow:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("نظام إدارة الشركة - تسجيل الدخول")
        self.window.geometry("400x400")
        self.window.resizable(False, False)
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Center the window
        self.center_window()
        
        # Create login frame
        self.create_login_ui()
        
    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = 400
        height = 400
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_login_ui(self):
        # Title
        title_label = ctk.CTkLabel(
            self.window,
            text="نظام إدارة شركة الأدوية",
            font=("Arial", 24, "bold")
        )
        title_label.pack(pady=30)
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            self.window,
            text="تسجيل الدخول",
            font=("Arial", 18)
        )
        subtitle_label.pack(pady=10)
        
        # Username field
        self.username_entry = ctk.CTkEntry(
            self.window,
            placeholder_text="اسم المستخدم",
            width=250,
            font=("Arial", 14)
        )
        self.username_entry.pack(pady=10)
        
        # Password field
        self.password_entry = ctk.CTkEntry(
            self.window,
            placeholder_text="كلمة المرور",
            width=250,
            font=("Arial", 14),
            show="*"
        )
        self.password_entry.pack(pady=10)

        self.role_var = ctk.StringVar(value="admin")
        self.role_menu = ctk.CTkOptionMenu(
            self.window,
            values=["admin", "accountant", "rep"],
            variable=self.role_var,
            width=250,
            font=("Arial", 13)
        )
        self.role_menu.pack(pady=8)
        
        # Login button
        login_button = ctk.CTkButton(
            self.window,
            text="تسجيل الدخول",
            width=200,
            height=40,
            font=("Arial", 14, "bold"),
            command=self.login
        )
        login_button.pack(pady=20)
        
        # Bind Enter key
        self.window.bind('<Return>', lambda event: self.login())
        
        # Demo credentials label
        demo_label = ctk.CTkLabel(
            self.window,
            text="بيانات الدخول التجريبية:\nadmin / admin",
            font=("Arial", 11),
            text_color="gray"
        )
        demo_label.pack(pady=10)
        
        # Set focus to username field
        self.username_entry.focus()
    
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        user = APIClient().login(username, password)
        if user:
            self.window.destroy()
            app = MainWindow(username=user.get("username", username), role=user.get("role", self.role_var.get()))
            app.run()
            return
        
        # Simple authentication (temporary)
        if username == "admin" and password == "admin":
            self.window.destroy()
            app = MainWindow(username=username, role=self.role_var.get())
            app.run()
        else:
            messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")
    
    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = LoginWindow()
    app.run()
