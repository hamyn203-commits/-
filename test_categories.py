#!/usr/bin/env python3
"""
Test script for the refactored CategoriesTab
"""
import customtkinter as ctk
from categories_tab import CategoriesTab
from api_client import APIClient

def test_status_callback(message):
    """Simple status callback for testing"""
    print(f"Status: {message}")

def test_open_products_callback(category_name, add_product):
    """Test callback for opening products"""
    action = "إضافة منتج" if add_product else "عرض المنتجات"
    print(f"{action} في تصنيف: {category_name}")

def main():
    # Initialize CustomTkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Create main window
    root = ctk.CTk()
    root.title("اختبار واجهة التصنيفات")
    root.geometry("1200x800")
    
    # Create API client
    api_client = APIClient()
    
    # Create categories tab
    categories_tab = CategoriesTab(
        master=root,
        api_client=api_client,
        status_callback=test_status_callback,
        role="admin",
        open_products_callback=test_open_products_callback
    )
    categories_tab.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Start the application
    root.mainloop()

if __name__ == "__main__":
    main()
