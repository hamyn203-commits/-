import requests
import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# إعداد نظام التسجيل للأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIClient:
    """عميل اتصال API لبرنامج إدارة شركة الأدوية"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        """
        تهيئة عميل API
        
        Args:
            base_url: رابط السيرفر الأساسي
            timeout: مهلة الاتصال بالثواني
        """
        self.base_url = (base_url or self.load_server_url()).rstrip('/')
        self.timeout = timeout
    
    def load_server_url(self) -> str:
        try:
            if os.path.exists("app_settings.json"):
                with open("app_settings.json", "r", encoding="utf-8") as file:
                    settings = json.load(file)
                return settings.get("server_url") or "http://127.0.0.1:8000"
        except Exception as e:
            logger.warning(f"Could not read app settings: {e}")
        return "http://127.0.0.1:8000"
    
    def set_base_url(self, base_url: str):
        self.base_url = str(base_url or "http://127.0.0.1:8000").rstrip("/")
    
    def _handle_response(self, response: requests.Response) -> Optional[Any]:
        """
        معالجة استجابة السيرفر
        
        Args:
            response: كائن الاستجابة من requests
            
        Returns:
            JSON كأي نوع (dict, list) إذا نجح الطلب، أو قاموس فارغ إذا كان status 204، أو None عند الفشل
        """
        try:
            # حالة عدم وجود محتوى
            if response.status_code == 204:
                return {}
            
            # رفع استثناء للأخطاء (4xx, 5xx)
            response.raise_for_status()
            
            # محاولة تحويل الاستجابة إلى JSON
            try:
                return response.json()
            except ValueError as json_error:
                logger.error(f"JSON Parsing Error - URL: {response.url}, Error: {str(json_error)}")
                return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error - URL: {response.url}, Status: {response.status_code}, Response: {response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error - URL: {response.url}, Error: {str(e)}")
            return None
    
    # ==========================================
    # قسم المنتجات (Products)
    # ==========================================
    
    def get_products(self, search: str = "") -> List[Dict[str, Any]]:
        """
        جلب قائمة جميع المنتجات
        
        Args:
            search: نص البحث (اختياري)
            
        Returns:
            قائمة المنتجات أو قائمة فارغة عند الفشل
        """
        try:
            url = f"{self.base_url}/products"
            params = {"search": search} if search else None
            
            response = requests.get(url, params=params, timeout=self.timeout)
            result = self._handle_response(response)
            
            return result if isinstance(result, list) else []
            
        except Exception as e:
            logger.error(f"Error in get_products: {str(e)}")
            return []

    def get_client_products(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/client/products", timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in get_client_products: {str(e)}")
            return []

    def get_categories(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/categories", timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in get_categories: {str(e)}")
            return []

    def create_category(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(f"{self.base_url}/categories", json={"name": name}, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in create_category: {str(e)}")
            return None

    def update_category(self, category_id: int, name: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.put(f"{self.base_url}/categories/{category_id}", json={"name": name}, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in update_category: {str(e)}")
            return None

    def delete_category(self, category_id: int) -> bool:
        try:
            response = requests.delete(f"{self.base_url}/categories/{category_id}", timeout=self.timeout)
            return self._handle_response(response) is not None
        except Exception as e:
            logger.error(f"Error in delete_category: {str(e)}")
            return False

    def get_suppliers(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/suppliers", timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in get_suppliers: {str(e)}")
            return []

    def create_supplier(
        self,
        name: str,
        phone: str = "",
        address: str = "",
        company: str = "",
        balance: float = 0.0,
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "name": name,
                "phone": phone,
                "address": address,
                "company": company,
                "balance": float(balance or 0.0),
                "notes": notes,
            }
            response = requests.post(f"{self.base_url}/suppliers", json=payload, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in create_supplier: {str(e)}")
            return None

    def update_supplier(
        self,
        supplier_id: int,
        name: str,
        phone: str = "",
        address: str = "",
        company: str = "",
        balance: float = 0.0,
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "name": name,
                "phone": phone,
                "address": address,
                "company": company,
                "balance": float(balance or 0.0),
                "notes": notes,
            }
            response = requests.put(f"{self.base_url}/suppliers/{supplier_id}", json=payload, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in update_supplier: {str(e)}")
            return None

    def delete_supplier(self, supplier_id: int) -> bool:
        try:
            response = requests.delete(f"{self.base_url}/suppliers/{supplier_id}", timeout=self.timeout)
            return self._handle_response(response) is not None
        except Exception as e:
            logger.error(f"Error in delete_supplier: {str(e)}")
            return False

    def get_purchases(self, supplier_id: Optional[int] = None) -> List[Dict[str, Any]]:
        try:
            params = {"supplier_id": supplier_id} if supplier_id else None
            response = requests.get(f"{self.base_url}/purchases", params=params, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in get_purchases: {str(e)}")
            return []

    def create_purchase(
        self,
        supplier_id: int,
        items: List[Dict[str, Any]],
        invoice_number: str = "",
        amount_paid: float = 0.0,
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        try:
            payload = {
                "supplier_id": int(supplier_id),
                "items": items,
                "invoice_number": invoice_number or None,
                "amount_paid": float(amount_paid or 0.0),
                "notes": notes,
            }
            response = requests.post(f"{self.base_url}/purchases", json=payload, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in create_purchase: {str(e)}")
            return None
    
    def create_product(
        self,
        name: str,
        price: float,
        quantity: int,
        expiry_date: str,
        image_path: str = "",
        image_url: str = "",
        is_active: int = 1,
        category_id: Optional[int] = None,
        description: str = "",
        images: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        إضافة منتج جديد
        
        Args:
            name: اسم المنتج
            price: السعر
            quantity: الكمية
            expiry_date: تاريخ الانتهاء (YYYY-MM-DD)
            
        Returns:
            بيانات المنتج المُضاف أو None عند الفشل
        """
        try:
            # تحويل القيم والتأكد من صحة النوع
            try:
                price = float(price)
                quantity = int(quantity)
            except (ValueError, TypeError) as e:
                logger.error(f"Error in create_product - Invalid price or quantity: {e}")
                return None
            
            # توليد barcode تلقائي باستخدام الوقت الحالي
            barcode = f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            
            product_data = {
                "name": name,
                "price": price,
                "unit_price": price,
                "quantity": quantity,
                "expiry_date": expiry_date,
                "image_path": image_path,
                "image_url": image_url,
                "images": images or ([image_url] if image_url else ([image_path] if image_path else [])),
                "description": description or "",
                "is_active": 1 if int(is_active or 0) == 1 else 0,
                "category_id": category_id,
                "barcode": barcode,
                "category": None if category_id else "عام",
                "company": "غير محدد"
            }
            
            response = requests.post(
                f"{self.base_url}/products",
                json=product_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in create_product: {str(e)}")
            return None
    
    def update_product(
        self,
        product_id: int,
        name: str,
        price: float,
        quantity: int,
        expiry_date: str,
        image_path: str = "",
        image_url: str = "",
        is_active: int = 1,
        category_id: Optional[int] = None,
        description: str = "",
        images: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        تحديث بيانات منتج موجود
        
        Args:
            product_id: معرف المنتج
            name: اسم المنتج
            price: السعر
            quantity: الكمية
            expiry_date: تاريخ الانتهاء
            
        Returns:
            بيانات المنتج المُحدث أو None عند الفشل
        """
        try:
            # تحويل القيم والتأكد من صحة النوع
            try:
                price = float(price)
                quantity = int(quantity)
            except (ValueError, TypeError) as e:
                logger.error(f"Error in update_product - Invalid price or quantity: {e}")
                return None
            
            product_data = {
                "name": name,
                "price": price,
                "unit_price": price,
                "quantity": quantity,
                "expiry_date": expiry_date,
                "image_path": image_path,
                "image_url": image_url,
                "images": images or ([image_url] if image_url else ([image_path] if image_path else [])),
                "description": description or "",
                "is_active": 1 if int(is_active or 0) == 1 else 0,
                "category_id": category_id,
                "barcode": f"AUTO-{product_id}",
                "category": None if category_id else "عام",
                "company": "غير محدد"
            }
            
            response = requests.put(
                f"{self.base_url}/products/{product_id}",
                json=product_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in update_product: {str(e)}")
            return None
    
    def delete_product(self, product_id: int) -> bool:
        """
        حذف منتج
        
        Args:
            product_id: معرف المنتج
            
        Returns:
            True عند النجاح، False عند الفشل
        """
        try:
            response = requests.delete(
                f"{self.base_url}/products/{product_id}",
                timeout=self.timeout
            )
            result = self._handle_response(response)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error in delete_product: {str(e)}")
            return False
    
    # ==========================================
    # قسم الصيدليات (Pharmacies)
    # ==========================================
    
    def get_pharmacies(self) -> List[Dict[str, Any]]:
        """
        جلب قائمة الصيدليات
        
        Returns:
            قائمة الصيدليات أو قائمة فارغة عند الفشل
        """
        try:
            response = requests.get(f"{self.base_url}/pharmacies", timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
            
        except Exception as e:
            logger.error(f"Error in get_pharmacies: {str(e)}")
            return []
    
    def create_pharmacy(self, name: str, address: str, phone: str, balance: float = 0.0) -> Optional[Dict[str, Any]]:
        """
        إضافة صيدلية جديدة
        
        Args:
            name: اسم الصيدلية
            address: العنوان
            phone: رقم الهاتف
            balance: الرصيد الافتتاحي (اختياري)
            
        Returns:
            بيانات الصيدلية المُضافة أو None عند الفشل
        """
        try:
            pharmacy_data = {
                "name": name,
                "address": address,
                "phone": phone,
                "balance": balance
            }
            
            response = requests.post(
                f"{self.base_url}/pharmacies",
                json=pharmacy_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in create_pharmacy: {str(e)}")
            return None
    
    def update_pharmacy(self, pharmacy_id: int, name: str, address: str, phone: str, balance: float = 0.0) -> Optional[Dict[str, Any]]:
        """
        تحديث بيانات صيدلية
        
        Args:
            pharmacy_id: معرف الصيدلية
            name: اسم الصيدلية
            address: العنوان
            phone: رقم الهاتف
            balance: الرصيد
            
        Returns:
            بيانات الصيدلية المُحدثة أو None عند الفشل
        """
        try:
            pharmacy_data = {
                "name": name,
                "address": address,
                "phone": phone,
                "balance": balance
            }
            
            response = requests.put(
                f"{self.base_url}/pharmacies/{pharmacy_id}",
                json=pharmacy_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in update_pharmacy: {str(e)}")
            return None
    
    def delete_pharmacy(self, pharmacy_id: int) -> bool:
        """
        حذف صيدلية
        
        Args:
            pharmacy_id: معرف الصيدلية
            
        Returns:
            True عند النجاح، False عند الفشل
        """
        try:
            response = requests.delete(
                f"{self.base_url}/pharmacies/{pharmacy_id}",
                timeout=self.timeout
            )
            
            # قبول 404 و 405 كحالات فشل عادية دون انهيار البرنامج
            if response.status_code in [404, 405]:
                logger.warning(f"Cannot delete pharmacy {pharmacy_id}: Status {response.status_code}")
                return False
                
            result = self._handle_response(response)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error in delete_pharmacy: {str(e)}")
            return False

    def approve_pharmacy_account(self, pharmacy_id: int, note: str = "") -> bool:
        try:
            response = requests.put(
                f"{self.base_url}/pharmacies/{int(pharmacy_id)}/approve",
                json={"note": note or ""},
                timeout=self.timeout,
            )
            result = self._handle_response(response)
            return result is not None
        except Exception as e:
            logger.error(f"Error in approve_pharmacy_account: {str(e)}")
            return False

    def block_pharmacy_account(self, pharmacy_id: int, note: str = "") -> bool:
        try:
            response = requests.put(
                f"{self.base_url}/pharmacies/{int(pharmacy_id)}/block",
                json={"note": note or ""},
                timeout=self.timeout,
            )
            result = self._handle_response(response)
            return result is not None
        except Exception as e:
            logger.error(f"Error in block_pharmacy_account: {str(e)}")
            return False

    def delete_or_revoke_pharmacy_account(self, pharmacy_id: int, note: str = "") -> bool:
        try:
            response = requests.put(
                f"{self.base_url}/pharmacies/{int(pharmacy_id)}/revoke",
                json={"note": note or ""},
                timeout=self.timeout,
            )
            result = self._handle_response(response)
            return result is not None
        except Exception as e:
            logger.error(f"Error in delete_or_revoke_pharmacy_account: {str(e)}")
            return False

    def reset_pharmacy_device(self, pharmacy_id: int) -> bool:
        try:
            response = requests.put(
                f"{self.base_url}/pharmacies/{int(pharmacy_id)}/reset-device",
                timeout=self.timeout,
            )
            result = self._handle_response(response)
            return result is not None
        except Exception as e:
            logger.error(f"Error in reset_pharmacy_device: {str(e)}")
            return False
    
    # ==========================================
    # قسم الطلبات (Orders)
    # ==========================================
    
    def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        جلب قائمة الطلبات
        
        Args:
            status: حالة الطلب (Approved/Rejected/Pending) - اختياري
            
        Returns:
            قائمة الطلبات أو قائمة فارغة عند الفشل
        """
        try:
            url = f"{self.base_url}/orders"
            params = {"status": status} if status else None
            
            response = requests.get(url, params=params, timeout=self.timeout)
            result = self._handle_response(response)
            
            return result if isinstance(result, list) else []
            
        except Exception as e:
            logger.error(f"Error in get_orders: {str(e)}")
            return []
    
    def create_order(
        self,
        pharmacy_id: int,
        items: List[Dict[str, Any]],
        discount: float = 0.0,
        discount_type: str = "value",
        delivery_person: str = "",
        notes: str = "",
        expected_delivery_note: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        إنشاء طلبية جديدة
        
        Args:
            pharmacy_id: معرف الصيدلية
            items: قائمة العناصر المطلوبة
            
        Returns:
            بيانات الطلبية أو None عند الفشل
        """
        try:
            order_data = {
                "pharmacy_id": pharmacy_id,
                "items": items,
                "discount": discount,
                "discount_type": discount_type,
                "delivery_person": delivery_person,
                "notes": notes,
                "expected_delivery_note": expected_delivery_note
            }
            
            response = requests.post(
                f"{self.base_url}/orders",
                json=order_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in create_order: {str(e)}")
            return None
    
    def update_order(
        self,
        order_id: int,
        pharmacy_id: int,
        items: List[Dict[str, Any]],
        discount: float = 0.0,
        discount_type: str = "value",
        delivery_person: str = "",
        notes: str = "",
        expected_delivery_note: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Update a pending order."""
        try:
            order_data = {
                "pharmacy_id": pharmacy_id,
                "items": items,
                "discount": discount,
                "discount_type": discount_type,
                "delivery_person": delivery_person,
                "notes": notes,
                "expected_delivery_note": expected_delivery_note
            }
            response = requests.put(
                f"{self.base_url}/orders/{order_id}",
                json=order_data,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error in update_order: {str(e)}")
            return None
    
    def update_order_status(
        self,
        order_id: int,
        status: str,
        delivery_person: Optional[str] = None,
        notes: Optional[str] = None,
        expected_delivery_note: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        تحديث حالة الطلبية
        
        Args:
            order_id: معرف الطلبية
            status: الحالة الجديدة (Approved/Rejected)
            
        Returns:
            بيانات الطلبية المُحدثة أو None عند الفشل
        """
        try:
            payload = {"status": status}
            if delivery_person is not None:
                payload["delivery_person"] = delivery_person
            if notes is not None:
                payload["notes"] = notes
            if expected_delivery_note is not None:
                payload["expected_delivery_note"] = expected_delivery_note
            
            response = requests.put(
                f"{self.base_url}/orders/{order_id}/status",
                json=payload,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in update_order_status: {str(e)}")
            return None
    
    # ==========================================
    # قسم التحصيلات (Payments)
    # ==========================================
    
    def add_payment(
        self,
        pharmacy_id: int,
        amount: float,
        order_id: Optional[int] = None,
        payment_type: str = "cash",
        payment_status: Optional[str] = None,
        amount_paid: Optional[float] = None,
        remaining_amount: Optional[float] = None,
        payment_notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        إضافة دفعة مالية جديدة
        
        Args:
            pharmacy_id: معرف الصيدلية
            amount: المبلغ
            
        Returns:
            بيانات الدفعة أو None عند الفشل
        """
        try:
            payload = {
                "pharmacy_id": pharmacy_id,
                "amount": amount,
                "order_id": order_id,
                "payment_type": payment_type,
                "payment_status": payment_status,
                "amount_paid": amount_paid,
                "remaining_amount": remaining_amount,
                "payment_notes": payment_notes,
            }
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=payload,
                timeout=self.timeout
            )
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in add_payment: {str(e)}")
            return None
    
    def get_pharmacy_payments(self, pharmacy_id: int) -> List[Dict[str, Any]]:
        """
        جلب تاريخ مدفوعات صيدلية
        
        Args:
            pharmacy_id: معرف الصيدلية
            
        Returns:
            قائمة المدفوعات أو قائمة فارغة عند الفشل
        """
        try:
            response = requests.get(
                f"{self.base_url}/pharmacies/{pharmacy_id}/payments",
                timeout=self.timeout
            )
            result = self._handle_response(response)
            
            return result if isinstance(result, list) else []
            
        except Exception as e:
            logger.error(f"Error in get_pharmacy_payments: {str(e)}")
            return []
    
    def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=self.timeout
            )
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in login: {str(e)}")
            return None

    def get_users(self) -> List[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/users", timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in get_users: {str(e)}")
            return []
    
    def create_user(self, username: str, password: str, role: str = "rep") -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(
                f"{self.base_url}/users",
                json={"username": username, "password": password, "role": role},
                timeout=self.timeout
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"Error in create_user: {str(e)}")
            return None
    
    def delete_user(self, user_id: int) -> bool:
        try:
            response = requests.delete(f"{self.base_url}/users/{user_id}", timeout=self.timeout)
            return self._handle_response(response) is not None
        except Exception as e:
            logger.error(f"Error in delete_user: {str(e)}")
            return False

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            response = requests.get(
                f"{self.base_url}/audit-logs",
                params={"limit": limit},
                timeout=self.timeout
            )
            result = self._handle_response(response)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error(f"Error in get_audit_logs: {str(e)}")
            return []

    def export_data(self) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{self.base_url}/data/export", timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in export_data: {str(e)}")
            return None

    def import_data(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(f"{self.base_url}/data/import", json=payload, timeout=self.timeout)
            result = self._handle_response(response)
            return result if isinstance(result, dict) else None
        except Exception as e:
            logger.error(f"Error in import_data: {str(e)}")
            return None
    
    # ==========================================
    # قسم الصحة (Health Check)
    # ==========================================
    
    def health_check(self) -> bool:
        """
        التحقق من صحة السيرفر
        
        Returns:
            True إذا كان السيرفر يعمل بشكل طبيعي، False عند الفشل
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            result = self._handle_response(response)
            return result is not None
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    # ==========================================
    # Aliases للتوافق مع الكود القديم
    # ==========================================
    
    def add_pharmacy(self, pharmacy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Alias لـ create_pharmacy للتوافق مع الكود القديم
        
        Args:
            pharmacy_data: قاموس يحتوي على بيانات الصيدلية
            
        Returns:
            بيانات الصيدلية المُضافة أو None عند الفشل
        """
        return self.create_pharmacy(
            name=pharmacy_data.get("name", ""),
            address=pharmacy_data.get("address", ""),
            phone=pharmacy_data.get("phone", ""),
            balance=pharmacy_data.get("balance", 0.0)
        )
    
    def add_product(self, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Alias لـ create_product للتوافق مع الكود القديم
        
        Args:
            product_data: قاموس يحتوي على بيانات المنتج
            
        Returns:
            بيانات المنتج المُضاف أو None عند الفشل
        """
        # دعم كل من price و unit_price
        price = product_data.get("price")
        if price is None:
            price = product_data.get("unit_price", 0.0)
        
        return self.create_product(
            name=product_data.get("name", ""),
            price=price,
            quantity=product_data.get("quantity", 0),
            expiry_date=product_data.get("expiry_date", ""),
            image_path=product_data.get("image_path", ""),
            image_url=product_data.get("image_url", ""),
            is_active=product_data.get("is_active", 1),
            category_id=product_data.get("category_id"),
            description=product_data.get("description", ""),
            images=product_data.get("images")
        )
