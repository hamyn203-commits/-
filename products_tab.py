"""
Products Tab for Pharmacy Management System
Displays and manages products with CRUD operations
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, Menu
from datetime import datetime, timedelta
from api_client import APIClient
from rtl_utils import rtl
import threading
import os
import json
import shutil
import uuid
import sys
import sqlite3
import urllib.parse
from io import BytesIO
from pathlib import Path
import requests
import webbrowser

try:
    from PIL import Image, ImageOps, ImageFile, ImageTk, ImageChops, ImageStat, UnidentifiedImageError
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:
    Image = None
    ImageOps = None
    ImageTk = None
    ImageChops = None
    ImageStat = None
    UnidentifiedImageError = Exception

try:
    from barcode_generator import generate_barcode_image
except Exception:
    generate_barcode_image = None


class ProductsTab(ctk.CTkFrame):
    """
    Products management tab
    """
    
    def __init__(
        self,
        master,
        api_client=None,
        status_callback=None,
        role="admin",
        initial_filter=None,
        initial_category=None,
        auto_open_add=False
    ):
        """
        Initialize Products Tab
        
        Args:
            master: Parent widget
            api_client: APIClient instance
            status_callback: Function to update status bar
        """
        super().__init__(master)
        
        self.master = master
        self.api_client = api_client or APIClient()
        self.status_callback = status_callback
        self.role = role or "admin"
        self.active_filter = initial_filter
        self.active_category = initial_category
        self.auto_open_add = bool(auto_open_add)
        self.categories_cache = []
        self.image_cache = {}
        self.tk_images = {}
        self.thumbnail_cache_version = "v3"
        self.base_dirs = self._get_runtime_base_dirs()
        
        # Configure the frame
        self.configure(fg_color="#1e1e1e")
        
        # Create UI
        self.create_ui()
        
        # Load data
        self.load_products()
        if self.auto_open_add and self.can_manage_products():
            self.after(250, lambda: self.show_add_dialog(preselected_category=self.active_category))

    def can_manage_products(self):
        return self.role == "admin"

    def show_permission_denied(self):
        self.show_warning("هذه العملية غير متاحة لهذا الدور")

    def ar(self, text):
        return rtl("" if text is None else str(text))

    def _is_remote_image(self, image_source):
        source = (image_source or "").strip().lower()
        return source.startswith("http://") or source.startswith("https://")

    def debug_image(self, stage, source, message, exc=None):
        details = f"[products_tab:image:{stage}] source={repr(source)} | {message}"
        if exc is not None:
            details += f" | exception={type(exc).__name__}: {exc}"
        print(details)

    def _normalize_local_path(self, image_source):
        source = (image_source or "").strip().strip('"').strip("'")
        if not source:
            return ""
        source = urllib.parse.unquote(source)
        source = source.replace("\\\\", "\\")
        if source.lower().startswith("file:///"):
            source = source[8:]
        elif source.lower().startswith("file://"):
            source = source[7:]
        # Handle paths that sometimes arrive as /D:/folder/file.png
        if len(source) > 3 and source[0] in ("/", "\\") and source[2] == ":" and source[1].isalpha():
            source = source[1:]
        expanded = os.path.expanduser(source)
        normalized = os.path.normpath(expanded)
        if not os.path.isabs(normalized):
            normalized = os.path.abspath(normalized)
        try:
            return str(Path(normalized))
        except Exception:
            return normalized

    def _resolve_local_image_path(self, image_source):
        source_text = str(image_source or "").strip()
        if source_text.startswith("/product_images/") or source_text.startswith("product_images/") or source_text.startswith("product_images\\"):
            filename_only = os.path.basename(source_text.replace("\\", "/"))
            if filename_only:
                in_library = os.path.join(self.product_images_dir(), filename_only)
                if os.path.exists(in_library):
                    return os.path.abspath(in_library)
        local_path = self._normalize_local_path(source_text)
        if local_path and os.path.exists(local_path):
            return local_path

        filename = os.path.basename(local_path or str(image_source or ""))
        if filename:
            candidates = [os.path.join(self.product_images_dir(), filename)]
            for base_dir in self.base_dirs:
                candidates.append(os.path.join(base_dir, filename))
                candidates.append(os.path.join(base_dir, "product_images", filename))
            for candidate in candidates:
                if os.path.exists(candidate):
                    self.debug_image("local-fallback", image_source, f"resolved via fallback: {candidate}")
                    return os.path.abspath(candidate)

            try:
                for root, _dirs, files in os.walk(self.product_images_dir()):
                    if filename in files:
                        found = os.path.join(root, filename)
                        self.debug_image("local-fallback", image_source, f"resolved by search: {found}")
                        return os.path.abspath(found)
            except Exception as exc:
                self.debug_image("local-fallback-error", image_source, "failed while searching product_images", exc)

        self.debug_image("file-not-found", image_source, f"normalized path not found: {local_path}")
        return ""

    def product_images_dir(self):
        preferred_roots = list(self.base_dirs) + [os.getcwd()]
        target_dir = ""
        for root in preferred_roots:
            try:
                candidate = os.path.join(root, "product_images")
                os.makedirs(candidate, exist_ok=True)
                target_dir = candidate
                break
            except Exception:
                continue
        if not target_dir:
            target_dir = os.path.join(os.getcwd(), "product_images")
            os.makedirs(target_dir, exist_ok=True)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def _get_runtime_base_dirs(self):
        """Collect stable base directories for loading/saving product images."""
        roots = []
        try:
            roots.append(os.path.dirname(os.path.abspath(__file__)))
        except Exception:
            pass
        try:
            if getattr(sys, "frozen", False):
                roots.append(os.path.dirname(sys.executable))
        except Exception:
            pass
        try:
            roots.append(os.path.abspath(os.getcwd()))
        except Exception:
            pass
        unique_roots = []
        seen = set()
        for root in roots:
            normalized = os.path.abspath(root)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_roots.append(normalized)
        return unique_roots

    def is_library_image(self, image_source):
        try:
            source = self._normalize_local_path(image_source)
            library_dir = os.path.abspath(self.product_images_dir())
            return os.path.abspath(source).startswith(library_dir)
        except Exception:
            return False

    def import_product_image_to_library(self, image_source):
        """Copy and normalize a local image into the app-managed image library."""
        source = (image_source or "").strip()
        if not source:
            return ""
        if self._is_remote_image(source):
            return source
        local_path = self._normalize_local_path(source)
        if self.is_library_image(local_path) and os.path.exists(local_path):
            return local_path
        if not os.path.exists(local_path):
            self.show_warning(f"الصورة غير موجودة:\n{local_path}")
            return ""

        filename = f"product_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        target_path = os.path.join(self.product_images_dir(), filename)
        try:
            if Image is not None:
                image = self._load_pil_image(local_path)
                if image is None:
                    raise ValueError("cannot open image")
                image = image.convert("RGB")
                resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
                image.thumbnail((1600, 1600), resampling)
                image.save(target_path, format="PNG", optimize=True)
            else:
                ext = os.path.splitext(local_path)[1] or ".png"
                target_path = os.path.join(self.product_images_dir(), f"product_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}")
                shutil.copy2(local_path, target_path)
            return os.path.abspath(target_path)
        except Exception as exc:
            print(f"[products_tab] image library import failed: {local_path} | {exc}")
            try:
                ext = os.path.splitext(local_path)[1] or ".img"
                fallback_path = os.path.join(self.product_images_dir(), f"product_{uuid.uuid4().hex[:12]}{ext}")
                shutil.copy2(local_path, fallback_path)
                return os.path.abspath(fallback_path)
            except Exception:
                self.show_warning(f"تعذر تجهيز الصورة:\n{local_path}")
                return ""

    def _load_pil_image(self, image_source):
        source = (image_source or "").strip()
        if not source or Image is None:
            self.debug_image("pil-unavailable", source, "Pillow is unavailable or source is empty")
            return None
        try:
            if self._is_remote_image(source):
                response = requests.get(source, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            else:
                local_path = self._resolve_local_image_path(source)
                if not local_path:
                    return None
                image = Image.open(local_path)
            try:
                image.load()
            except Exception as exc:
                self.debug_image("image-load-warning", source, "PIL opened the image but load() reported a warning", exc)
            return ImageOps.exif_transpose(image) if ImageOps is not None else image
        except FileNotFoundError as exc:
            self.debug_image("file-not-found", source, "local file does not exist", exc)
            return None
        except UnidentifiedImageError as exc:
            self.debug_image("invalid-image", source, "PIL could not identify this image file", exc)
            return None
        except OSError as exc:
            self.debug_image("unsupported-or-corrupt", source, "unsupported format or corrupted image data", exc)
            return None
        except requests.RequestException as exc:
            self.debug_image("remote-request-failed", source, "remote image request failed", exc)
            return None
        except Exception as exc:
            self.debug_image("pil-load-failed", source, "unexpected image load failure", exc)
            return None

    def _load_tk_photo_fallback(self, image_source):
        if self._is_remote_image(image_source):
            return None
        local_path = self._resolve_local_image_path(image_source)
        if not local_path:
            return None
        try:
            return tk.PhotoImage(file=local_path)
        except tk.TclError as exc:
            self.debug_image("tk-photo-fallback-failed", image_source, "Tk PhotoImage could not load this file", exc)
            return None
        except Exception as exc:
            self.debug_image("tk-photo-fallback-error", image_source, "unexpected Tk fallback failure", exc)
            return None

    def _fit_image_to_square(self, image, size):
        image = image.convert("RGBA")
        background = Image.new("RGBA", image.size, "#1f1f1f")
        if image.mode == "RGBA":
            background.alpha_composite(image)
            image = background.convert("RGB")
        else:
            image = image.convert("RGB")

        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
        max_inner = max(size - 12, 24)

        # Always use contain so the entire image is visible inside the square
        # without any crop, while keeping aspect ratio.
        fitted = ImageOps.contain(image, (max_inner, max_inner), method=resampling) if ImageOps is not None else image
        if fitted is image:
            fitted = image.copy()
            fitted.thumbnail((max_inner, max_inner), resampling)

        canvas = Image.new("RGB", (size, size), "#171717")
        x = (size - fitted.width) // 2
        y = (size - fitted.height) // 2
        canvas.paste(fitted, (x, y))
        return canvas

    def _trim_safe_outer_whitespace(self, image):
        """Trim only obvious outer whitespace so catalog thumbnails remain readable."""
        if ImageChops is None:
            return image
        try:
            rgb = image.convert("RGB")
            corners = [
                rgb.getpixel((0, 0)),
                rgb.getpixel((rgb.width - 1, 0)),
                rgb.getpixel((0, rgb.height - 1)),
                rgb.getpixel((rgb.width - 1, rgb.height - 1)),
            ]
            bg = tuple(int(sum(pixel[i] for pixel in corners) / 4) for i in range(3))
            diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg))
            diff = ImageOps.grayscale(diff).point(lambda px: 255 if px > 18 else 0)
            bbox = diff.getbbox()
            if not bbox:
                return image
            left, top, right, bottom = bbox
            trim_w = rgb.width - (right - left)
            trim_h = rgb.height - (bottom - top)
            if trim_w < rgb.width * 0.06 and trim_h < rgb.height * 0.06:
                return image
            pad_x = max(int((right - left) * 0.06), 8)
            pad_y = max(int((bottom - top) * 0.06), 8)
            left = max(left - pad_x, 0)
            top = max(top - pad_y, 0)
            right = min(right + pad_x, rgb.width)
            bottom = min(bottom + pad_y, rgb.height)
            cropped = rgb.crop((left, top, right, bottom))
            if cropped.width < rgb.width * 0.18 or cropped.height < rgb.height * 0.18:
                return image
            return cropped
        except Exception as exc:
            self.debug_image("trim-failed", "PIL image", "safe whitespace trim failed", exc)
            return image

    def _is_visually_useful_image(self, image):
        # Disabled by design: if Pillow can open the image, the admin list should display it.
        return True

    def _make_contained_preview(self, image, width, height, bg="#151515"):
        image = image.convert("RGB")
        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.BICUBIC)
        image.thumbnail((width - 16, height - 16), resampling)
        canvas = Image.new("RGB", (width, height), bg)
        canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
        return canvas

    def _display_pil_image_on_label(self, label, image, width, height, cache_key):
        try:
            preview = self._make_contained_preview(image, width, height)
            photo = ImageTk.PhotoImage(preview, master=label) if ImageTk is not None else None
            if photo is None:
                return False
            self.tk_images[cache_key] = photo
            label.configure(text="", image=photo)
            label.image = photo
            return True
        except Exception as exc:
            self.debug_image("label-display-failed", cache_key, "failed to display PIL image on label", exc)
            return False

    def _get_thumbnail_image(self, image_source, size=72):
        source = (image_source or "").strip()
        if not source or Image is None:
            self.debug_image("thumbnail-skipped", source, "empty source or Pillow unavailable")
            return None
        cache_source = source if self._is_remote_image(source) else (self._resolve_local_image_path(source) or self._normalize_local_path(source))
        cache_key = (self.thumbnail_cache_version, cache_source, size)
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        try:
            image = self._load_pil_image(source)
            if image is None:
                self.debug_image("thumbnail-source-failed", source, "no PIL image returned; trying next source if available")
                return None
            canvas = self._fit_image_to_square(image, size)
            self.image_cache[cache_key] = canvas
            return canvas
        except Exception as exc:
            self.debug_image("thumbnail-build-failed", source, "failed while creating thumbnail", exc)
            return None

    def update_image_widget(self, target_label, image_source, size=72, missing_text="لا توجد صورة", invalid_text="تعذر تحميل الصورة"):
        self.update_image_widget_from_sources(target_label, [image_source], size, missing_text, invalid_text)

    def update_image_widget_from_sources(self, target_label, image_sources, size=72, missing_text="لا توجد صورة", invalid_text="تعذر تحميل الصورة", allow_raw_fallback=False):
        sources = image_sources if isinstance(image_sources, list) else [image_sources]
        valid_sources = [str(source or "").strip() for source in sources if str(source or "").strip()]
        should_try_raw_fallback = bool(allow_raw_fallback or Image is None)
        for source in valid_sources:
            thumbnail = self._get_thumbnail_image(source, size=size)
            if thumbnail is None:
                if should_try_raw_fallback:
                    fallback_photo = self._load_tk_photo_fallback(source)
                    if fallback_photo is not None:
                        try:
                            target_label.configure(text="", image=fallback_photo)
                            target_label.image = fallback_photo
                            target_label.loaded_source = source
                            self.tk_images[(source, size, "tk-photo-fallback")] = fallback_photo
                            self.debug_image("display-fallback-ok", source, "displayed using raw Tk PhotoImage fallback")
                            return source
                        except Exception as exc:
                            self.debug_image("display-widget-failure", source, "Tk fallback image loaded but widget configure failed", exc)
                continue
            cache_source = source if self._is_remote_image(source) else (self._resolve_local_image_path(source) or self._normalize_local_path(source))
            image_order = ("tk",) if isinstance(target_label, tk.Label) else ("ctk", "tk")
            for image_kind in image_order:
                try:
                    cache_key = (cache_source, size, image_kind)
                    display_image = self.tk_images.get(cache_key)
                    if display_image is None:
                        if image_kind == "ctk":
                            display_image = ctk.CTkImage(light_image=thumbnail, dark_image=thumbnail, size=(size, size))
                        else:
                            if ImageTk is None:
                                continue
                            try:
                                display_image = ImageTk.PhotoImage(thumbnail, master=target_label)
                            except TypeError:
                                display_image = ImageTk.PhotoImage(thumbnail)
                        self.tk_images[cache_key] = display_image
                    target_label.configure(text="", image=display_image)
                    target_label.image = display_image
                    target_label.loaded_source = source
                    self.debug_image("display-ok", source, f"displayed with {image_kind}")
                    return source
                except Exception as exc:
                    self.debug_image("display-widget-failure", source, f"display failed with {image_kind}", exc)
                    continue
        if isinstance(target_label, tk.Label):
            target_label.configure(text=missing_text if not valid_sources else invalid_text, image="", fg="#bdbdbd")
        else:
            target_label.configure(text=self.ar(missing_text if not valid_sources else invalid_text), image=None, text_color="#bdbdbd")
        target_label.image = None
        target_label.loaded_source = ""
        self.debug_image("all-sources-failed", valid_sources, "no valid product image could be displayed")
        return ""

    def get_product_images(self, product):
        images = []
        raw_images = product.get("images") if isinstance(product, dict) else None
        if isinstance(raw_images, list):
            for item in raw_images:
                if isinstance(item, dict):
                    nested_source = item.get("url") or item.get("path") or item.get("image_url") or item.get("image_path")
                    if nested_source:
                        images.append(nested_source)
                else:
                    images.append(item)
        elif isinstance(raw_images, str) and raw_images.strip():
            parsed_raw = None
            try:
                parsed_raw = json.loads(raw_images)
            except Exception:
                parsed_raw = None
            if isinstance(parsed_raw, list):
                images.extend(parsed_raw)
            elif isinstance(parsed_raw, dict):
                nested_source = parsed_raw.get("url") or parsed_raw.get("path") or parsed_raw.get("image_url") or parsed_raw.get("image_path")
                if nested_source:
                    images.append(nested_source)
            else:
                images.append(raw_images)
        raw_json = product.get("product_images_json") if isinstance(product, dict) else ""
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, list):
                    images.extend(parsed)
            except Exception:
                pass
        for legacy_key in ("image_url", "image_path"):
            legacy = (product.get(legacy_key, "") if isinstance(product, dict) else "").strip()
            if legacy:
                images.append(legacy)

        cleaned = []
        seen = set()
        for source in images:
            source = str(source or "").strip()
            if source and source not in seen:
                cleaned.append(source)
                seen.add(source)
        cleaned.sort(key=lambda source: 0 if (self._is_remote_image(source) or os.path.exists(self._normalize_local_path(source))) else 1)
        return cleaned

    def collect_images_for_save(self, selected_images, manual_source=""):
        images = []
        manual_source = (manual_source or "").strip()
        if manual_source:
            if not self._is_remote_image(manual_source):
                manual_source = self.import_product_image_to_library(manual_source) or manual_source
            images.append(manual_source)
        for source in (selected_images or []):
            source = str(source or "").strip()
            if source and not self._is_remote_image(source):
                source = self.import_product_image_to_library(source) or source
            images.append(source)
        cleaned = []
        seen = set()
        for source in images:
            source = str(source or "").strip()
            if source and source not in seen:
                cleaned.append(source)
                seen.add(source)
        return cleaned

    def safe_description_preview(self, description, max_len=90):
        text = str(description or "").strip()
        if not text:
            return ""
        # Existing "????" usually means the text was already corrupted before
        # rendering, so keep it safe and readable without trying to mutate data.
        text = text.replace("\ufffd", "?")
        while "??????" in text:
            text = text.replace("??????", "????")
        plain = text.replace(" ", "").replace("\n", "")
        if plain and plain.count("?") / max(len(plain), 1) > 0.45:
            return ""
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    def pick_multiple_images(self, selected_images, render_callback=None):
        paths = filedialog.askopenfilenames(
            title=self.ar("اختيار صور المنتج"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.gif"), ("All files", "*.*")]
        )
        for path in paths:
            path = self.import_product_image_to_library(str(path or "").strip())
            if path and path not in selected_images:
                selected_images.append(path)
        if callable(render_callback):
            render_callback()

    def create_images_gallery(self, parent, selected_images, primary_getter=None, primary_setter=None, on_primary_change=None):
        gallery = ctk.CTkScrollableFrame(parent, fg_color="#1f1f1f", height=132, corner_radius=12, border_width=1, border_color="#3a3a3a")
        gallery.pack(fill="x", pady=(6, 10))
        gallery.grid_columnconfigure(0, weight=1)

        def render():
            for widget in gallery.winfo_children():
                widget.destroy()
            if not selected_images:
                ctk.CTkLabel(
                    gallery,
                    text=self.ar("لا توجد صور إضافية"),
                    font=("Arial", 12),
                    text_color="#bdbdbd",
                ).pack(pady=36)
                return
            for index, source in enumerate(list(selected_images)):
                row = ctk.CTkFrame(gallery, fg_color="#252525", corner_radius=10)
                row.pack(fill="x", padx=8, pady=5)
                thumb = tk.Label(row, text="صورة", bg="#191919", fg="#bdbdbd", bd=0, compound="center")
                thumb.pack(side="right", padx=8, pady=8)
                self.update_image_widget(thumb, source, size=52, missing_text="صورة", invalid_text="تعذر")
                is_primary = False
                try:
                    is_primary = (primary_getter and primary_getter() == source) or (not primary_getter and index == 0)
                except Exception:
                    is_primary = index == 0
                if is_primary:
                    ctk.CTkLabel(row, text=self.ar("رئيسية"), width=62, height=24, fg_color="#4CAF50", text_color="white", corner_radius=8, font=("Arial", 10, "bold")).pack(side="right", padx=(0, 6))
                ctk.CTkLabel(
                    row,
                    text=source,
                    font=("Arial", 11),
                    text_color="#d0d0d0",
                    anchor="w",
                    wraplength=330,
                ).pack(side="right", fill="x", expand=True, padx=6)

                def remove(src=source):
                    if src in selected_images:
                        selected_images.remove(src)
                    if callable(primary_getter) and callable(primary_setter):
                        try:
                            if primary_getter() == src:
                                primary_setter(selected_images[0] if selected_images else "")
                        except Exception:
                            pass
                    render()

                def make_primary(src=source):
                    if src in selected_images:
                        selected_images.remove(src)
                    selected_images.insert(0, src)
                    if callable(primary_setter):
                        primary_setter(src)
                    if callable(on_primary_change):
                        on_primary_change()
                    render()

                ctk.CTkButton(row, text=self.ar("اجعلها رئيسية"), width=105, height=30, fg_color="#2196F3", hover_color="#1976D2", command=make_primary).pack(side="left", padx=(4, 0))
                ctk.CTkButton(row, text=self.ar("حذف"), width=62, height=30, fg_color="#f44336", hover_color="#d32f2f", command=remove).pack(side="left", padx=8)
        render()
        return render

    def show_product_image_gallery(self, product_name, image_sources, start_index=0):
        images = [str(source or "").strip() for source in (image_sources or []) if str(source or "").strip()]
        if not images:
            self.show_warning("لا توجد صور لهذا المنتج")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(self.ar("معرض صور المنتج"))
        dialog.geometry("760x560")
        dialog.minsize(680, 500)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color="#151515")
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        preferred_index = max(0, min(int(start_index or 0), len(images) - 1))
        index_var = {"index": preferred_index}

        title = ctk.CTkLabel(dialog, text=self.ar(product_name or "صور المنتج"), font=("Arial", 20, "bold"), text_color="#ffffff", anchor="e")
        title.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))

        viewer = ctk.CTkFrame(dialog, fg_color="#101010", corner_radius=14, border_width=1, border_color="#333333")
        viewer.grid(row=1, column=0, sticky="nsew", padx=18, pady=8)
        viewer.grid_rowconfigure(0, weight=1)
        viewer.grid_columnconfigure(0, weight=1)

        image_label = tk.Label(viewer, text="", bg="#101010", fg="#bdbdbd", font=("Arial", 15), bd=0, justify="center")
        image_label.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        controls = ctk.CTkFrame(dialog, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 16))
        controls.grid_columnconfigure(1, weight=1)
        counter_label = ctk.CTkLabel(controls, text="", text_color="#bdbdbd", font=("Arial", 13, "bold"))
        counter_label.grid(row=0, column=1)

        def advance_to_valid_index(from_index):
            if not images:
                return from_index
            total = len(images)
            for step in range(total):
                candidate = (from_index + step) % total
                source = images[candidate]
                image = self._load_pil_image(source)
                if image is not None:
                    return candidate
                fallback_photo = self._load_tk_photo_fallback(source)
                if fallback_photo is not None:
                    self.tk_images[("gallery-probe-fallback", source, candidate)] = fallback_photo
                    return candidate
            return from_index

        index_var["index"] = advance_to_valid_index(index_var["index"])

        def render_current():
            source = images[index_var["index"]]
            try:
                image = self._load_pil_image(source)
                if image is None:
                    raise ValueError("image could not be loaded")
                # Gallery previews full images and deliberately does not apply
                # small-thumbnail suitability checks.
                ok = self._display_pil_image_on_label(
                    image_label,
                    image,
                    660,
                    380,
                    ("gallery", source, index_var["index"])
                )
                if not ok:
                    fallback_photo = self._load_tk_photo_fallback(source)
                    if fallback_photo is not None:
                        image_label.configure(text="", image=fallback_photo)
                        image_label.image = fallback_photo
                        self.tk_images[("gallery-fallback", source, index_var["index"])] = fallback_photo
                        ok = True
                if not ok:
                    raise ValueError("display image creation failed")
            except Exception as exc:
                self.debug_image("gallery-display-failed", source, "gallery could not display source", exc)
                next_index = advance_to_valid_index((index_var["index"] + 1) % len(images))
                if next_index != index_var["index"]:
                    index_var["index"] = next_index
                    return render_current()
                image_label.configure(text="تعذر معاينة الصورة", image="")
                image_label.image = None
            counter_label.configure(text=f"{index_var['index'] + 1} / {len(images)}")

        def prev_image():
            index_var["index"] = (index_var["index"] - 1) % len(images)
            render_current()

        def next_image():
            index_var["index"] = (index_var["index"] + 1) % len(images)
            render_current()

        ctk.CTkButton(controls, text=self.ar("السابق"), width=110, height=38, fg_color="#444444", hover_color="#555555", command=prev_image).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(controls, text=self.ar("التالي"), width=110, height=38, fg_color="#2196F3", hover_color="#1976D2", command=next_image).grid(row=0, column=2, sticky="e")
        dialog.bind("<Left>", lambda _e: next_image())
        dialog.bind("<Right>", lambda _e: prev_image())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        render_current()

    def bind_entry_shortcuts(self, entry):
        menu = Menu(entry, tearoff=0)
        menu.add_command(label=self.ar("نسخ"), command=lambda: self._entry_copy(entry))
        menu.add_command(label=self.ar("لصق"), command=lambda: self._entry_paste(entry))
        menu.add_command(label=self.ar("قص"), command=lambda: self._entry_cut(entry))
        menu.add_separator()
        menu.add_command(label=self.ar("تحديد الكل"), command=lambda: (entry.select_range(0, "end"), entry.icursor("end")))

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return "break"

        entry.bind("<Button-3>", show_menu)
        entry.bind("<Control-a>", lambda _e: (entry.select_range(0, "end"), entry.icursor("end"), "break")[2])
        entry.bind("<Control-A>", lambda _e: (entry.select_range(0, "end"), entry.icursor("end"), "break")[2])
        entry.bind("<Control-c>", lambda _e: (self._entry_copy(entry), "break")[1])
        entry.bind("<Control-C>", lambda _e: (self._entry_copy(entry), "break")[1])
        entry.bind("<Control-v>", lambda _e: (self._entry_paste(entry), "break")[1])
        entry.bind("<Control-V>", lambda _e: (self._entry_paste(entry), "break")[1])
        entry.bind("<Control-x>", lambda _e: (self._entry_cut(entry), "break")[1])
        entry.bind("<Control-X>", lambda _e: (self._entry_cut(entry), "break")[1])

    def _entry_copy(self, entry):
        try:
            txt = entry.selection_get()
            entry.clipboard_clear()
            entry.clipboard_append(txt)
        except Exception:
            pass

    def _entry_paste(self, entry):
        try:
            txt = entry.clipboard_get()
            if entry.selection_present():
                entry.delete("sel.first", "sel.last")
            entry.insert(entry.index("insert"), txt)
        except Exception:
            pass

    def _entry_cut(self, entry):
        try:
            txt = entry.selection_get()
            entry.clipboard_clear()
            entry.clipboard_append(txt)
            entry.delete("sel.first", "sel.last")
        except Exception:
            pass

    def pick_image_path_for_entry(self, entry_widget, on_change=None):
        file_path = filedialog.askopenfilename(
            title=self.ar("اختيار صورة المنتج"),
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.gif"), ("All files", "*.*")]
        )
        if not file_path:
            return
        file_path = self.import_product_image_to_library(file_path)
        if not file_path:
            return
        entry_widget.delete(0, "end")
        entry_widget.insert(0, file_path)
        if callable(on_change):
            on_change()

    def open_image_source(self, image_source):
        source = (image_source or "").strip()
        if not source:
            return
        try:
            if self._is_remote_image(source):
                webbrowser.open(source)
                return
            local_path = self._normalize_local_path(source)
            if os.path.exists(local_path):
                os.startfile(local_path)
        except Exception as exc:
            print(f"[products_tab] open image failed: {source} | {exc}")

    def find_duplicate_product(self, name, category_display=None):
        n_name = (name or "").strip().lower()
        if not n_name:
            return None
        try:
            products = self.api_client.get_products()
        except Exception:
            return None
        for product in products:
            if (product.get("name", "").strip().lower() != n_name):
                continue
            if category_display and category_display != "بدون تصنيف":
                if self.get_product_category_display(product) != category_display:
                    continue
            return product
        return None

    def load_categories(self):
        try:
            self.categories_cache = self.api_client.get_categories()
        except Exception:
            self.categories_cache = []
        return self.categories_cache

    def get_category_options(self):
        categories = self.load_categories()
        return ["بدون تصنيف"] + [category.get("name", "") for category in categories if category.get("name")]

    def get_category_id_by_name(self, name):
        if not name or name == "بدون تصنيف":
            return None
        for category in self.categories_cache:
            if category.get("name") == name:
                return category.get("id")
        return None

    def get_product_category_display(self, product):
        return product.get("category_name") or product.get("category") or "بدون تصنيف"

    def normalize_category_name(self, value):
        return ("" if value is None else str(value)).strip().lower()

    def filter_by_category(self, category_name):
        """Public helper used by navigation to focus products by category."""
        self.active_category = category_name
        self.load_products()

    def apply_category_filter(self, products):
        if not self.active_category:
            return products
        target = self.normalize_category_name(self.active_category)
        return [
            product for product in products
            if self.normalize_category_name(self.get_product_category_display(product)) == target
        ]
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
    def get_product_price(self, product):
        """Get product price safely from price or unit_price"""
        price = product.get("price")
        if price is not None:
            return float(price)
        unit_price = product.get("unit_price")
        if unit_price is not None:
            return float(unit_price)
        return 0.0
    
    def get_product_expiry(self, product):
        """Get cleaned expiry date from product"""
        expiry = product.get("expiry_date", "")
        return self.clean_date_string(expiry)
    
    def is_product_expired(self, expiry_date):
        """Check if product is expired"""
        if not expiry_date or expiry_date.strip() == "":
            return False
        try:
            expiry_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
            return expiry_obj < datetime.now()
        except:
            return False
    
    def is_low_stock(self, quantity):
        """Check if stock is low (1-5 items)"""
        return 1 <= quantity <= 5
    
    def is_out_of_stock(self, quantity):
        """Check if product is out of stock"""
        return quantity == 0

    def is_product_expiring_soon(self, expiry_date):
        """Check if product expires within 30 days."""
        if not expiry_date or expiry_date.strip() == "":
            return False
        try:
            expiry_obj = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            return today <= expiry_obj <= today + timedelta(days=30)
        except Exception:
            return False

    def get_filter_label(self):
        labels = {
            "out_of_stock": "المنتجات النافدة",
            "low_stock": "منتجات مخزون منخفض",
            "expired": "منتجات منتهية الصلاحية",
            "expiring_soon": "منتجات قرب انتهاء الصلاحية",
        }
        return labels.get(self.active_filter, "")

    def apply_active_filter(self, products):
        if not self.active_filter:
            return products
        filtered = []
        for product in products:
            try:
                quantity = int(product.get("quantity") or 0)
            except (TypeError, ValueError):
                quantity = 0
            expiry_date = self.get_product_expiry(product)
            if self.active_filter == "out_of_stock" and self.is_out_of_stock(quantity):
                filtered.append(product)
            elif self.active_filter == "low_stock" and self.is_low_stock(quantity):
                filtered.append(product)
            elif self.active_filter == "expired" and self.is_product_expired(expiry_date):
                filtered.append(product)
            elif self.active_filter == "expiring_soon" and self.is_product_expiring_soon(expiry_date):
                filtered.append(product)
        return filtered

    def clear_active_filter(self):
        self.active_filter = None
        self.active_category = None
        self.load_products()
    
    def safe_float(self, value, field_name="السعر"):
        """Convert value to float safely"""
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} يجب أن يكون رقماً صحيحاً")
    
    def safe_int(self, value, field_name="الكمية"):
        """Convert value to int safely"""
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} يجب أن يكون رقماً صحيحاً")
    
    def show_error(self, message, title="خطأ"):
        """Show error message box"""
        messagebox.showerror(title, message)
    
    def show_info(self, message, title="معلومات"):
        """Show info message box"""
        messagebox.showinfo(title, message)

    def show_warning(self, message, title="تنبيه"):
        """Show warning message box"""
        messagebox.showwarning(title, message)
    
    def update_status(self, message):
        """Update status bar safely"""
        if self.status_callback:
            try:
                self.status_callback(message)
            except:
                pass
    
    def clean_date_string(self, date_string):
        """
        Clean date string by removing time component if present
        
        Args:
            date_string: Date string that might contain time
            
        Returns:
            str: Clean date string without time
        """
        if not date_string or date_string.strip() == "":
            return ""
        
        date_string = date_string.strip()
        
        # Remove time component if present (e.g., "2026-04-30 00:00:00" -> "2026-04-30")
        if " " in date_string:
            date_string = date_string.split(" ")[0]
        
        # Remove T separator if present (e.g., "2026-04-30T00:00:00" -> "2026-04-30")
        if "T" in date_string:
            date_string = date_string.split("T")[0]
        
        return date_string
    
    def normalize_expiry_date(self, date_string):
        """
        Normalize expiry date to YYYY-MM-DD format
        
        Args:
            date_string: Date string in various formats (YYYY-MM-DD, YYYYMMDD, DD/MM/YYYY, DD-MM-YYYY)
        
        Returns:
            str: Date in YYYY-MM-DD format
            
        Raises:
            ValueError: If date format is invalid
        """
        # First clean the date string from any time component
        date_string = self.clean_date_string(date_string)
        
        # If date is empty, return empty string
        if not date_string:
            return ""
        
        # Try different formats
        formats = [
            ("%Y-%m-%d", "YYYY-MM-DD"),      # 2026-04-30
            ("%Y%m%d", "YYYYMMDD"),           # 20260430
            ("%d/%m/%Y", "DD/MM/YYYY"),       # 30/04/2026
            ("%d-%m-%Y", "DD-MM-YYYY")        # 30-04-2026
        ]
        
        for date_format, format_name in formats:
            try:
                parsed_date = datetime.strptime(date_string, date_format)
                # Return in YYYY-MM-DD format
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        # If no format matched, raise error
        raise ValueError("تاريخ الصلاحية غير صحيح. استخدم مثلًا 2026-04-30 أو 20260430 أو 30/04/2026 أو 30-04-2026")
    
    def format_expiry_date_focus_out(self, entry_widget):
        """
        Format expiry date automatically when focus leaves the field
        
        Args:
            entry_widget: The CTkEntry widget containing the date
        """
        date_string = entry_widget.get().strip()
        
        if not date_string:
            entry_widget.configure(border_color="#555555", border_width=1)
            return
        
        try:
            # Try to normalize the date
            normalized_date = self.normalize_expiry_date(date_string)
            # Update the entry with formatted date
            entry_widget.delete(0, "end")
            entry_widget.insert(0, normalized_date)
            # Change border color to green to indicate valid date
            entry_widget.configure(border_color="#4CAF50", border_width=2)
        except ValueError:
            # Change border color to red to indicate invalid date
            entry_widget.configure(border_color="#f44336", border_width=2)
    
    def reset_entry_border(self, entry_widget):
        """Reset entry border color"""
        entry_widget.configure(border_color="#555555", border_width=1)
    
    def check_server_health(self):
        """Check if server is reachable"""
        try:
            if hasattr(self.api_client, 'health_check'):
                return self.api_client.health_check()
            # If health_check not available, try simple get
            import requests
            response = requests.get(f"{self.api_client.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    # ==========================================
    # UI Creation Methods
    # ==========================================
    
    def create_ui(self):
        """Create the user interface"""
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=(20, 10))

        search_frame = ctk.CTkFrame(self.top_frame, fg_color="#252525", corner_radius=12)
        search_frame.pack(side="left", fill="x", expand=True)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text=self.ar("بحث عن منتج..."),
            width=250,
            height=38,
            font=("Arial", 13),
            justify="right",
            fg_color="#1f1f1f",
            border_color="#3a3a3a",
        )
        self.search_entry.pack(side="left", padx=(12, 10), pady=10)
        self.search_entry.bind("<Return>", lambda e: self.search_products())

        self.search_btn = ctk.CTkButton(
            search_frame,
            text=self.ar("بحث"),
            width=80,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color="#2196F3",
            hover_color="#1976D2",
            command=self.search_products,
        )
        self.search_btn.pack(side="left", padx=(0, 10), pady=10)

        self.refresh_btn = ctk.CTkButton(
            search_frame,
            text=self.ar("تحديث"),
            width=80,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color="#2d2d2d",
            hover_color="#3d3d3d",
            command=self.load_products,
        )
        self.refresh_btn.pack(side="left", pady=10)

        self.import_excel_btn = ctk.CTkButton(
            search_frame,
            text=self.ar("استيراد Excel"),
            width=110,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color="#FF9800",
            hover_color="#F57C00",
            command=self.import_products_from_excel,
        )
        self.import_excel_btn.pack(side="left", padx=(10, 12), pady=10)

        self.import_sql_btn = ctk.CTkButton(
            search_frame,
            text=self.ar("استيراد SQL"),
            width=110,
            height=36,
            font=("Arial", 12, "bold"),
            fg_color="#00ACC1",
            hover_color="#0097A7",
            command=self.import_products_from_sql_database,
        )
        self.import_sql_btn.pack(side="left", padx=(0, 12), pady=10)

        self.add_btn = ctk.CTkButton(
            self.top_frame,
            text=self.ar("إضافة منتج جديد"),
            width=170,
            height=38,
            font=("Arial", 12, "bold"),
            fg_color="#4CAF50",
            hover_color="#43A047",
            command=self.show_add_dialog,
        )
        self.add_btn.pack(side="right")
        if not self.can_manage_products():
            self.import_excel_btn.configure(state="disabled")
            self.import_sql_btn.configure(state="disabled")
            self.add_btn.configure(state="disabled")

        toolbar_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12, border_width=1, border_color="#343434")
        toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))
        toolbar_frame.grid_columnconfigure(0, weight=1)
        toolbar_frame.grid_columnconfigure(1, weight=0)
        toolbar_frame.grid_columnconfigure(2, weight=0)
        ctk.CTkLabel(
            toolbar_frame,
            text=self.ar("فلترة سريعة"),
            font=("Arial", 12, "bold"),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        ).grid(row=0, column=0, sticky="e", padx=(10, 6), pady=8)
        self.sort_menu = ctk.CTkOptionMenu(
            toolbar_frame,
            values=[
                "الأحدث أولاً",
                "الأقدم أولاً",
                "الاسم أ-ي",
                "الاسم ي-أ",
                "السعر الأعلى",
                "السعر الأقل",
                "الأكثر كمية",
                "الأقل كمية",
            ],
            width=170,
            height=32,
            font=("Arial", 12),
            command=lambda _v: self.load_products(),
        )
        self.sort_menu.set("الأحدث أولاً")
        self.sort_menu.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=8)
        ctk.CTkLabel(
            toolbar_frame,
            text=self.ar("ترتيب"),
            font=("Arial", 12),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        ).grid(row=0, column=2, sticky="e", padx=(0, 10), pady=8)

        quick_filters = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        quick_filters.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        quick_filters.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="qf")
        self.quick_filter_buttons = {}
        quick_defs = [
            ("all", "عرض الكل", "#4CAF50", None),
            ("out_of_stock", "نافد", "#f44336", "out_of_stock"),
            ("low_stock", "منخفض", "#FF9800", "low_stock"),
            ("expired", "منتهي", "#E91E63", "expired"),
            ("expiring_soon", "ينتهي قريبًا", "#03A9F4", "expiring_soon"),
        ]
        for idx, (key, title, color, filt) in enumerate(quick_defs):
            btn = ctk.CTkButton(
                quick_filters,
                text=self.ar(title),
                height=32,
                font=("Arial", 11, "bold"),
                fg_color=color if (filt and self.active_filter == filt) or (filt is None and not self.active_filter) else "#3a3a3a",
                hover_color=color,
                command=lambda f=filt: self.set_quick_filter(f),
            )
            btn.grid(row=0, column=idx, sticky="ew", padx=4, pady=2)
            self.quick_filter_buttons[key] = (btn, color, filt)

        self.kpi_frame = ctk.CTkFrame(self, fg_color="#252525", corner_radius=12, border_width=1, border_color="#343434")
        self.kpi_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="kpi")
        self.kpi_cards = {}
        self.kpi_cards["total"] = self.create_kpi_card(self.kpi_frame, 0, "إجمالي المنتجات", "0", "#4CAF50")
        self.kpi_cards["available"] = self.create_kpi_card(self.kpi_frame, 1, "متوفر", "0", "#00BCD4")
        self.kpi_cards["low"] = self.create_kpi_card(self.kpi_frame, 2, "منخفض المخزون", "0", "#FF9800")
        self.kpi_cards["out"] = self.create_kpi_card(self.kpi_frame, 3, "نافد", "0", "#f44336")

        self.filter_frame = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=8)
        if self.active_filter or self.active_category:
            self.filter_frame.pack(fill="x", padx=20, pady=(0, 10))
            filter_text = self.get_filter_label() if self.active_filter else f"تصنيف: {self.active_category}"
            ctk.CTkLabel(
                self.filter_frame,
                text=self.ar(f"الفلتر الحالي: {filter_text}"),
                font=("Arial", 13, "bold"),
                text_color="#4CAF50",
                anchor="e",
                justify="right",
            ).pack(side="right", padx=12, pady=8)
            ctk.CTkButton(
                self.filter_frame,
                text=self.ar("عرض الكل"),
                width=90,
                height=30,
                fg_color="#555555",
                hover_color="#666666",
                command=self.clear_active_filter
            ).pack(side="left", padx=12, pady=8)
        
        # Scrollable frame for products table
        self.table_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#2d2d2d",
            corner_radius=10
        )
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # Table headers
        self.create_headers()
        
        # Dictionary to store product rows
        self.rows = {}

    def create_kpi_card(self, parent, column, title, value, color):
        card = ctk.CTkFrame(parent, fg_color="#1f1f1f", corner_radius=10, border_width=1, border_color="#353535")
        card.grid(row=0, column=column, sticky="ew", padx=6, pady=8)
        ctk.CTkLabel(
            card,
            text=self.ar(title),
            font=("Arial", 12),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
        ).pack(fill="x", padx=10, pady=(8, 2))
        value_label = ctk.CTkLabel(
            card,
            text=str(value),
            font=("Arial", 20, "bold"),
            text_color=color,
            anchor="e",
            justify="right",
        )
        value_label.pack(fill="x", padx=10, pady=(0, 8))
        return value_label

    def set_quick_filter(self, filter_key):
        self.active_filter = filter_key
        self.load_products()

    def update_quick_filter_buttons(self):
        for _key, (btn, color, filt) in self.quick_filter_buttons.items():
            is_active = (filt and self.active_filter == filt) or (filt is None and not self.active_filter)
            btn.configure(fg_color=color if is_active else "#3a3a3a")

    def apply_sort_mode(self, products):
        sort_mode = self.sort_menu.get() if hasattr(self, "sort_menu") else "الأحدث أولاً"
        items = list(products or [])
        if sort_mode == "الأقدم أولاً":
            items.sort(key=lambda x: x.get("id", 0))
        elif sort_mode == "الاسم أ-ي":
            items.sort(key=lambda x: str(x.get("name", "")).strip().lower())
        elif sort_mode == "الاسم ي-أ":
            items.sort(key=lambda x: str(x.get("name", "")).strip().lower(), reverse=True)
        elif sort_mode == "السعر الأعلى":
            items.sort(key=lambda x: self.get_product_price(x), reverse=True)
        elif sort_mode == "السعر الأقل":
            items.sort(key=lambda x: self.get_product_price(x))
        elif sort_mode == "الأكثر كمية":
            items.sort(key=lambda x: int(x.get("quantity") or 0), reverse=True)
        elif sort_mode == "الأقل كمية":
            items.sort(key=lambda x: int(x.get("quantity") or 0))
        else:
            items.sort(key=lambda x: x.get("id", 0), reverse=True)
        return items

    def update_kpis(self, products):
        product_list = products if isinstance(products, list) else []
        total = len(product_list)
        available = 0
        low = 0
        out = 0
        for product in product_list:
            try:
                qty = int(product.get("quantity") or 0)
            except (TypeError, ValueError):
                qty = 0
            if self.is_out_of_stock(qty):
                out += 1
            elif self.is_low_stock(qty):
                low += 1
            else:
                available += 1
        self.kpi_cards["total"].configure(text=str(total))
        self.kpi_cards["available"].configure(text=str(available))
        self.kpi_cards["low"].configure(text=str(low))
        self.kpi_cards["out"].configure(text=str(out))
    
    def create_headers(self):
        """Create a compact list header that matches the card layout."""
        headers_frame = ctk.CTkFrame(self.table_frame, fg_color="#252525", corner_radius=10)
        headers_frame.pack(fill="x", padx=(10, 14), pady=(10, 8))
        headers_frame.grid_columnconfigure(0, weight=1)
        headers_frame.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            headers_frame,
            text=self.ar("قائمة المنتجات"),
            font=("Arial", 15, "bold"),
            text_color="#4CAF50",
            anchor="e",
            justify="right",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            headers_frame,
            text=self.ar("كل منتج يظهر ككارت منظم يحتوي على الصورة والبيانات والحالة والإجراءات"),
            font=("Arial", 11),
            text_color="#9e9e9e",
            anchor="e",
            justify="right",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            headers_frame,
            text=self.ar("الإجراءات"),
            font=("Arial", 12, "bold"),
            text_color="#bdbdbd",
            anchor="center",
            justify="center",
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 14), pady=10)
    
    # ==========================================
    # Data Loading Methods
    # ==========================================
    
    def load_products(self):
        """Load products from API"""
        # Check server health first
        if not self.check_server_health():
            self.update_status("⚠️ السيرفر غير متصل")
            self.update_kpis([])
            self.update_quick_filter_buttons()
            self.clear_rows()
            self.show_empty_message(
                "⚠️ السيرفر غير متصل\n\n"
                "قم بتشغيل السيرفر باستخدام الأمر:\n"
                "python -m uvicorn main:app --reload"
            )
            return
        
        try:
            self.update_status("جاري تحميل المنتجات...")
            self.update_quick_filter_buttons()
            self.image_cache.clear()
            self.tk_images.clear()
            
            products = self.apply_category_filter(self.apply_active_filter(self.api_client.get_products()))
            
            # Clear existing rows
            self.clear_rows()

            if (self.active_filter or self.active_category) and (not products or len(products) == 0):
                self.update_kpis([])
                if self.active_category:
                    self.show_empty_message(f"لا توجد منتجات في هذا التصنيف: {self.active_category}")
                    self.update_status(f"لا توجد منتجات في هذا التصنيف: {self.active_category}")
                    return
                self.show_empty_message(f"لا توجد نتائج في فلتر: {self.get_filter_label()}")
                self.update_status(f"لا توجد نتائج في فلتر: {self.get_filter_label()}")
                return
            
            if not products or len(products) == 0:
                self.update_kpis([])
                self.show_empty_message("📦 لا توجد منتجات\nاضغط على 'إضافة منتج جديد' لإضافة منتج")
                self.update_status("لا توجد منتجات")
                return
            
            products = self.apply_category_filter(self.apply_active_filter(products))
            if (self.active_filter or self.active_category) and not products:
                self.update_kpis([])
                if self.active_category:
                    self.show_empty_message(f"لا توجد منتجات في هذا التصنيف: {self.active_category}")
                    self.update_status(f"لا توجد منتجات في هذا التصنيف: {self.active_category}")
                    return
                self.show_empty_message(f"لا توجد نتائج داخل فلتر: {self.get_filter_label()}")
                self.update_status(f"لا توجد نتائج داخل فلتر: {self.get_filter_label()}")
                return

            # Sort products by selected mode
            products = self.apply_sort_mode(products)
            self.update_kpis(products)
            
            # Display products
            for idx, product in enumerate(products, start=1):
                self.add_product_row(product, idx)
            if self.active_filter:
                self.update_status(f"تم عرض {len(products)} منتج في فلتر: {self.get_filter_label()}")
                return
            if self.active_category:
                self.update_status(f"تم عرض {len(products)} منتج في تصنيف: {self.active_category}")
                return
            
            self.update_status(f"✅ تم تحميل {len(products)} منتج")
                
        except Exception as e:
            self.update_status("❌ خطأ في تحميل المنتجات")
            self.update_kpis([])
            self.update_quick_filter_buttons()
            self.clear_rows()
            self.show_empty_message(f"⚠️ حدث خطأ أثناء تحميل المنتجات\n\n{str(e)}")
    
    def search_products(self):
        """Search products by name"""
        search_term = self.search_entry.get().strip()
        
        if not search_term:
            self.load_products()
            return
        
        # Check server health first
        if not self.check_server_health():
            self.update_status("⚠️ السيرفر غير متصل")
            self.update_kpis([])
            self.update_quick_filter_buttons()
            self.clear_rows()
            self.show_empty_message("⚠️ السيرفر غير متصل\nتأكد من تشغيل السيرفر")
            return
        
        try:
            self.update_status(f"جاري البحث عن: {search_term}")
            self.image_cache.clear()
            self.tk_images.clear()
            
            self.update_quick_filter_buttons()
            products = self.apply_active_filter(self.apply_category_filter(self.api_client.get_products(search=search_term)))
            
            # Clear existing rows
            self.clear_rows()
            
            if not products or len(products) == 0:
                # Try local filtering as fallback
                all_products = self.apply_active_filter(self.apply_category_filter(self.api_client.get_products()))
                products = [p for p in all_products if search_term.lower() in p.get("name", "").lower()]
                
                if not products:
                    self.update_kpis([])
                    if self.active_category:
                        self.show_empty_message(f"لا توجد منتجات في هذا التصنيف تطابق البحث: {self.active_category}")
                        self.update_status(f"لا توجد نتائج داخل تصنيف: {self.active_category}")
                    else:
                        self.show_empty_message(f"🔍 لا توجد نتائج لـ '{search_term}'")
                        self.update_status(f"لا توجد نتائج لـ '{search_term}'")
                    return
            
            products = self.apply_sort_mode(products)
            self.update_kpis(products)
            
            for idx, product in enumerate(products, start=1):
                self.add_product_row(product, idx)
            
            self.update_status(f"✅ تم العثور على {len(products)} منتج")
                
        except Exception as e:
            self.update_status("❌ خطأ في البحث")
            self.update_kpis([])
            self.update_quick_filter_buttons()
            self.show_error(f"فشل البحث: {str(e)}")

    def create_info_pair(self, parent, label, value, value_color="#ffffff"):
        """Create a small label/value pair inside a product card."""
        box = ctk.CTkFrame(parent, fg_color="#202020", corner_radius=8)
        ctk.CTkLabel(
            box,
            text=self.ar(label),
            font=("Arial", 10),
            text_color="#9e9e9e",
            anchor="e",
            justify="right",
        ).pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkLabel(
            box,
            text=str(value),
            font=("Arial", 12, "bold"),
            text_color=value_color,
            anchor="e",
            justify="right",
        ).pack(fill="x", padx=8, pady=(1, 6))
        return box

    def create_status_badge(self, parent, text, color):
        """Create a compact colored status badge."""
        badge = ctk.CTkLabel(
            parent,
            text=self.ar(text),
            height=26,
            font=("Arial", 11, "bold"),
            text_color=color,
            fg_color="#303030",
            corner_radius=8,
            anchor="center",
            justify="center",
        )
        return badge
    
    def add_product_row(self, product, index=None):
        """Add a responsive product card to the list."""
        row_bg = "#252525" if (index or 0) % 2 else "#2b2b2b"
        row_frame = ctk.CTkFrame(self.table_frame, fg_color=row_bg, corner_radius=12, border_width=1, border_color="#353535")
        row_frame.pack(fill="x", padx=(10, 14), pady=6)
        row_frame.grid_columnconfigure(1, weight=1, minsize=150)
        row_frame.grid_columnconfigure(2, weight=2, minsize=210)
        row_frame.grid_columnconfigure(3, weight=0, minsize=150)
        
        product_id = product.get("id")
        
        # Get product data
        product_name = self.ar(product.get("name", "N/A"))
        actual_price = self.get_product_price(product)
        try:
            quantity = int(product.get("quantity") or 0)
        except (TypeError, ValueError):
            quantity = 0
        expiry_date = self.get_product_expiry(product)
        product_images = self.get_product_images(product)
        images_count = len(product_images)
        description_preview = self.safe_description_preview(product.get("description"))
        is_active = int(product.get("is_active", 1) or 1) == 1
        
        # Determine visual states
        is_expired = self.is_product_expired(expiry_date)
        is_low = self.is_low_stock(quantity)
        is_out = self.is_out_of_stock(quantity)
        
        # Display expiry date
        display_expiry = expiry_date if expiry_date else "غير محدد"
        category_text = self.get_product_category_display(product)
        stock_text = "نافد" if is_out else ("منخفض" if is_low else "متوفر")
        qty_color = "#f44336" if is_out else ("#FF9800" if is_low else "#4CAF50")
        expiry_color = "#f44336" if (is_expired and expiry_date) else "#bdbdbd"
        visibility_color = "#4CAF50" if is_active else "#888888"

        media_frame = ctk.CTkFrame(row_frame, fg_color="#191919", width=104, height=118, corner_radius=14, border_width=1, border_color="#3b3b3b")
        media_frame.grid(row=0, column=0, sticky="nsw", padx=(10, 10), pady=10)
        media_frame.grid_propagate(False)

        image_box = ctk.CTkFrame(media_frame, fg_color="#111111", width=84, height=84, corner_radius=12, border_width=1, border_color="#444444")
        image_box.place(relx=0.5, y=10, anchor="n")
        image_box.pack_propagate(False)

        image_label = tk.Label(
            image_box,
            text="لا توجد صورة",
            bg="#111111",
            fg="#9e9e9e",
            font=("Arial", 8),
            bd=0,
            compound="center",
            justify="center",
        )
        image_label.place(relx=0.5, rely=0.5, anchor="center", width=76, height=76)
        loaded_image_source = self.update_image_widget_from_sources(
            image_label,
            product_images,
            size=76,
            missing_text="لا توجد صورة",
            invalid_text="تعذر تحميل الصورة",
            allow_raw_fallback=True
        )

        ctk.CTkLabel(
            media_frame,
            text=f"#{index or product_id}",
            height=18,
            font=("Arial", 10, "bold"),
            text_color="#cfcfcf",
            fg_color="#2b2b2b",
            corner_radius=6,
        ).place(x=10, y=94)

        if images_count > 1:
            ctk.CTkLabel(
                media_frame,
                text=f"{images_count} صور",
                height=20,
                font=("Arial", 10, "bold"),
                text_color="#ffffff",
                fg_color="#2196F3",
                corner_radius=8,
            ).place(relx=1.0, y=94, x=-10, anchor="ne")

        def open_gallery(_event=None):
            start_at = 0
            if loaded_image_source in product_images:
                start_at = product_images.index(loaded_image_source)
            self.show_product_image_gallery(product.get("name", ""), product_images, start_index=start_at)

        if product_images:
            for clickable in (media_frame, image_box, image_label):
                try:
                    clickable.bind("<Button-1>", open_gallery)
                    clickable.configure(cursor="hand2")
                except Exception:
                    pass

        info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        info_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            info_frame,
            text=product_name,
            font=("Arial", 14, "bold"),
            text_color="#ffffff",
            anchor="e",
            justify="right",
            wraplength=220,
        ).grid(row=0, column=0, sticky="ew", pady=(2, 4))

        ctk.CTkLabel(
            info_frame,
            text=self.ar(category_text),
            font=("Arial", 12),
            text_color="#bdbdbd",
            anchor="e",
            justify="right",
            wraplength=210,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        if description_preview:
            ctk.CTkLabel(
                info_frame,
                text=self.ar(description_preview),
                font=("Arial", 11),
                text_color="#9e9e9e",
                anchor="e",
                justify="right",
                wraplength=220,
            ).grid(row=2, column=0, sticky="ew", pady=(0, 8))

        badges_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        badges_frame.grid(row=3, column=0, sticky="e")
        self.create_status_badge(badges_frame, stock_text, qty_color).pack(side="right", padx=(4, 0))
        self.create_status_badge(badges_frame, "ظاهر للعميل" if is_active else "مخفي", visibility_color).pack(side="right", padx=(4, 0))

        details_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        details_frame.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)
        details_frame.grid_columnconfigure((0, 1), weight=1, uniform="product_details")

        self.create_info_pair(details_frame, "السعر", f"{actual_price:.2f}", "#4CAF50").grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        self.create_info_pair(details_frame, "الكمية", str(quantity), qty_color).grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        self.create_info_pair(details_frame, "الصلاحية", display_expiry, expiry_color).grid(row=1, column=0, sticky="ew", padx=3, pady=3)
        self.create_info_pair(details_frame, "الصور", f"{images_count} صورة" if loaded_image_source else "لا تظهر", "#4CAF50" if loaded_image_source else "#f44336").grid(row=1, column=1, sticky="ew", padx=3, pady=3)

        buttons_frame = ctk.CTkFrame(row_frame, fg_color="#202020", width=150, corner_radius=10)
        buttons_frame.grid(row=0, column=3, sticky="nse", padx=(0, 10), pady=10)
        buttons_frame.grid_propagate(False)
        buttons_frame.grid_columnconfigure(0, weight=1)
        
        # Edit button
        edit_btn = ctk.CTkButton(
            buttons_frame,
            text=self.ar("تعديل"),
            height=30,
            font=("Arial", 11),
            fg_color="#2196F3",
            hover_color="#1976D2",
            command=lambda p=product: self.edit_product(p)
        )
        edit_btn.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        if not self.can_manage_products():
            edit_btn.configure(state="disabled")
        
        # Delete button
        delete_btn = ctk.CTkButton(
            buttons_frame,
            text=self.ar("حذف"),
            height=30,
            font=("Arial", 11),
            fg_color="#f44336",
            hover_color="#d32f2f",
            command=lambda pid=product_id: self.delete_product(pid)
        )
        delete_btn.grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        if not self.can_manage_products():
            delete_btn.configure(state="disabled")
        
        barcode_btn = ctk.CTkButton(
            buttons_frame,
            text=self.ar("باركود"),
            height=30,
            font=("Arial", 11),
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            command=lambda p=product: self.show_barcode_window(p)
        )
        barcode_btn.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        
        # Store row reference
        self.rows[product_id] = row_frame
    
    def clear_rows(self):
        """Clear all product rows from the table safely"""
        # Get list of rows to avoid dictionary modification issues
        rows_to_clear = list(self.rows.values())
        
        for row in rows_to_clear:
            try:
                if row and row.winfo_exists():
                    row.destroy()
            except:
                pass
        
        self.rows.clear()
    
    def show_empty_message(self, message="📦 لا توجد منتجات"):
        """Show empty state message"""
        empty_label = ctk.CTkLabel(
            self.table_frame,
            text=message,
            font=("Arial", 14),
            text_color="gray"
        )
        empty_label.pack(pady=50)
        self.rows["empty"] = empty_label
    
    def import_products_from_excel(self):
        """Import products from an Excel file with columns: name, price, quantity, expiry_date."""
        if not self.can_manage_products():
            self.show_permission_denied()
            return
        try:
            import pandas as pd
        except Exception:
            self.show_error("ميزة الاستيراد تحتاج تثبيت pandas و openpyxl")
            return
        
        file_path = filedialog.askopenfilename(
            title="اختيار ملف Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            data = pd.read_excel(file_path)
            required = {"name", "price", "quantity", "expiry_date"}
            missing = required - set(data.columns)
            if missing:
                self.show_error(f"أعمدة ناقصة في الملف: {', '.join(sorted(missing))}")
                return
            
            added = 0
            failed = 0
            for _, row in data.iterrows():
                try:
                    name = str(row["name"]).strip()
                    price = float(row["price"])
                    quantity = int(row["quantity"])
                    expiry = self.normalize_expiry_date(str(row["expiry_date"]).split(" ")[0])
                    if not name:
                        failed += 1
                        continue
                    result = self.api_client.create_product(name, price, quantity, expiry)
                    added += 1 if result else 0
                    failed += 0 if result else 1
                except Exception:
                    failed += 1
            
            self.load_products()
            self.show_info(f"تم الاستيراد\n\nتمت الإضافة: {added}\nفشل: {failed}")
            self.update_status(f"تم استيراد {added} منتج من Excel")
        except Exception as e:
            self.show_error(f"فشل استيراد الملف:\n{str(e)}")

    def import_products_from_sql_database(self):
        """Import products from a SQLite database file."""
        if not self.can_manage_products():
            self.show_permission_denied()
            return

        db_path = filedialog.askopenfilename(
            title=self.ar("اختيار قاعدة بيانات SQL"),
            filetypes=[
                ("SQLite DB", "*.db *.sqlite *.sqlite3"),
                ("All files", "*.*"),
            ],
        )
        if not db_path:
            return

        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            preferred = ["products", "product", "items", "inventory", "stock_products"]
            table_name = ""
            for candidate in preferred:
                if candidate in tables:
                    table_name = candidate
                    break
            if not table_name and tables:
                table_name = tables[0]
            if not table_name:
                self.show_error("لم يتم العثور على أي جدول داخل قاعدة البيانات")
                return

            columns_info = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            if not columns_info:
                self.show_error(f"لم يتم العثور على أعمدة في الجدول: {table_name}")
                return
            columns = [str(col["name"] if isinstance(col, sqlite3.Row) else col[1]) for col in columns_info]

            def pick_col(options):
                for option in options:
                    if option in columns:
                        return option
                return None

            col_name = pick_col(["name", "product_name", "title"])
            col_price = pick_col(["price", "unit_price", "sell_price"])
            col_quantity = pick_col(["quantity", "qty", "stock", "amount"])
            col_expiry = pick_col(["expiry_date", "expiry", "exp_date", "expire_date"])
            col_image = pick_col(["image_url", "image", "image_path", "photo", "picture"])
            col_desc = pick_col(["description", "desc", "notes", "details"])

            if not col_name or not col_price or not col_quantity:
                self.show_error(
                    "الجدول لا يحتوي على الأعمدة الأساسية المطلوبة.\n\n"
                    "مطلوب على الأقل:\n"
                    "• اسم المنتج (name)\n"
                    "• السعر (price)\n"
                    "• الكمية (quantity)"
                )
                return

            selected_cols = [col_name, col_price, col_quantity]
            for optional_col in (col_expiry, col_image, col_desc):
                if optional_col and optional_col not in selected_cols:
                    selected_cols.append(optional_col)

            query = f"SELECT {', '.join(selected_cols)} FROM {table_name}"
            rows = cursor.execute(query).fetchall()
            if not rows:
                self.show_warning("لا توجد بيانات منتجات داخل الجدول المحدد")
                return

            added = 0
            failed = 0
            for row in rows:
                try:
                    name = str(row[col_name] or "").strip()
                    if not name:
                        failed += 1
                        continue

                    price = float(row[col_price] or 0.0)
                    quantity = int(row[col_quantity] or 0)
                    if price <= 0 or quantity < 0:
                        failed += 1
                        continue

                    expiry_date = ""
                    if col_expiry:
                        raw_expiry = str(row[col_expiry] or "").strip()
                        if raw_expiry:
                            try:
                                expiry_date = self.normalize_expiry_date(raw_expiry)
                            except Exception:
                                expiry_date = ""

                    image_source = ""
                    images = []
                    if col_image:
                        raw_image = str(row[col_image] or "").strip()
                        if raw_image:
                            image_source = raw_image
                            if not self._is_remote_image(raw_image):
                                imported = self.import_product_image_to_library(raw_image)
                                image_source = imported or raw_image
                            images = [image_source] if image_source else []

                    description = str(row[col_desc] or "").strip() if col_desc else ""
                    result = self.api_client.create_product(
                        name=name,
                        price=price,
                        quantity=quantity,
                        expiry_date=expiry_date,
                        image_path="",
                        image_url=image_source if image_source else "",
                        is_active=1,
                        category_id=None,
                        description=description,
                        images=images,
                    )
                    if result:
                        added += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

            self.load_products()
            self.show_info(
                f"تم استيراد بيانات SQL بنجاح\n\n"
                f"الجدول: {table_name}\n"
                f"تمت الإضافة: {added}\n"
                f"فشل: {failed}"
            )
            self.update_status(f"تم استيراد {added} منتج من قاعدة SQL")
        except Exception as e:
            self.show_error(f"فشل استيراد قاعدة SQL:\n{str(e)}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    def choose_product_image(self, image_var, label):
        """Choose image path for a product."""
        file_path = filedialog.askopenfilename(
            title="اختيار صورة المنتج",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        if not file_path:
            return
        image_var.set(file_path)
        label.configure(text=os.path.basename(file_path))
    
    def show_barcode_window(self, product):
        """Show barcode preview for a product."""
        if generate_barcode_image is None:
            self.show_error("ميزة الباركود تحتاج تثبيت python-barcode و Pillow")
            return
        
        try:
            barcode_value = product.get("barcode") or f"PRODUCT-{product.get('id', '')}"
            image = generate_barcode_image(barcode_value)
            
            dialog = ctk.CTkToplevel(self)
            dialog.title("باركود المنتج")
            dialog.geometry("520x420")
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.grab_set()
            
            frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=12)
            frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            ctk.CTkLabel(
                frame,
                text=product.get("name", ""),
                font=("Arial", 20, "bold"),
                text_color="#4CAF50"
            ).pack(pady=(16, 6))
            
            ctk.CTkLabel(
                frame,
                text=f"السعر: {self.get_product_price(product):.2f} جنيه",
                font=("Arial", 14),
                text_color="white"
            ).pack(pady=(0, 12))
            
            if Image is None:
                self.show_error("Pillow غير مثبتة لعرض صورة الباركود")
                return
            
            image = image.resize((420, 150))
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(420, 150))
            label = ctk.CTkLabel(frame, text="", image=ctk_image)
            label.image = ctk_image
            label.pack(pady=10)
            
            ctk.CTkLabel(
                frame,
                text=str(barcode_value),
                font=("Arial", 12),
                text_color="#bdbdbd"
            ).pack(pady=(0, 12))
            
            ctk.CTkButton(
                frame,
                text="طباعة",
                width=120,
                height=36,
                fg_color="#2196F3",
                command=lambda: self.show_info("يمكن طباعة الباركود من نافذة النظام لاحقًا")
            ).pack(side="left", padx=(130, 8), pady=10)
            
            ctk.CTkButton(
                frame,
                text="إغلاق",
                width=120,
                height=36,
                fg_color="#555555",
                command=dialog.destroy
            ).pack(side="left", pady=10)
        except Exception as e:
            self.show_error(f"فشل عرض الباركود:\n{str(e)}")
    
    # ==========================================
    # Product CRUD Operations
    # ==========================================
    
    def show_add_dialog(self, preselected_category=None):
        """Show dialog to add new product"""
        if not self.can_manage_products():
            self.show_permission_denied()
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.ar("إضافة منتج جديد"))
        dialog.geometry("620x700")
        dialog.resizable(True, True)
        dialog.minsize(560, 640)
        dialog.transient(self)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        main_frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(main_frame, text=self.ar("إضافة منتج جديد"), font=("Arial", 20, "bold"), text_color="#4CAF50", anchor="e", justify="right").grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        form_area = ctk.CTkScrollableFrame(main_frame, fg_color="#252525", corner_radius=12)
        form_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        fields_frame = ctk.CTkFrame(form_area, fg_color="transparent")
        fields_frame.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(fields_frame, text=self.ar("اسم المنتج"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(8, 4))
        name_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        name_entry.pack(fill="x", pady=(0, 12))
        name_entry.focus()
        self.bind_entry_shortcuts(name_entry)

        category_options = self.get_category_options()
        ctk.CTkLabel(fields_frame, text=self.ar("التصنيف"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        category_menu = ctk.CTkOptionMenu(fields_frame, values=category_options, height=40, font=("Arial", 13))
        if preselected_category and preselected_category in category_options:
            category_menu.set(preselected_category)
        else:
            category_menu.set(category_options[0])
        category_menu.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(fields_frame, text=self.ar("السعر (EGP)"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        price_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        price_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(price_entry)

        ctk.CTkLabel(fields_frame, text=self.ar("الكمية"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        quantity_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        quantity_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(quantity_entry)

        ctk.CTkLabel(fields_frame, text=self.ar("تاريخ الصلاحية"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(fields_frame, text=self.ar("الصيغ المدعومة: 2026-04-30 أو 20260430 أو 30/04/2026 أو 30-04-2026"), font=("Arial", 10), text_color="#888888", anchor="e", justify="right").pack(fill="x", pady=(0, 5))
        expiry_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        expiry_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(expiry_entry)
        expiry_entry.bind("<FocusOut>", lambda e: self.format_expiry_date_focus_out(expiry_entry))
        expiry_entry.bind("<FocusIn>", lambda e: self.reset_entry_border(expiry_entry))

        ctk.CTkLabel(fields_frame, text=self.ar("وصف المنتج"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        description_box = ctk.CTkTextbox(fields_frame, height=92, font=("Arial", 13))
        description_box.pack(fill="x", pady=(0, 12))

        image_path_var = ctk.StringVar(value="")
        ctk.CTkLabel(fields_frame, text=self.ar("رابط الصورة (URL) / مسار الصورة"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        image_url_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        image_url_entry.pack(fill="x", pady=(0, 8))
        self.bind_entry_shortcuts(image_url_entry)
        selected_images = []

        preview_after_id = None
        preview_box = ctk.CTkFrame(fields_frame, fg_color="#1f1f1f", width=130, height=130, corner_radius=12, border_width=1, border_color="#3a3a3a")
        preview_box.pack(anchor="e", pady=(8, 10))
        preview_box.pack_propagate(False)
        preview_label = tk.Label(preview_box, text="لا توجد صورة", bg="#1f1f1f", fg="#bdbdbd", font=("Arial", 10), bd=0, compound="center")
        preview_label.place(relx=0.5, rely=0.5, anchor="center", width=120, height=120)

        def refresh_preview():
            nonlocal preview_after_id
            if preview_after_id:
                try:
                    dialog.after_cancel(preview_after_id)
                except Exception:
                    pass
            preview_after_id = dialog.after(250, lambda: self.update_image_widget(preview_label, image_url_entry.get().strip(), size=120))

        btn_row = ctk.CTkFrame(fields_frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(btn_row, text=self.ar("اختيار صورة"), width=120, height=34, fg_color="#2196F3", hover_color="#1976D2", command=lambda: self.pick_image_path_for_entry(image_url_entry, refresh_preview)).pack(side="right")
        ctk.CTkButton(btn_row, text=self.ar("اختيار عدة صور"), width=130, height=34, fg_color="#4CAF50", hover_color="#43A047", command=lambda: self.pick_multiple_images(selected_images, render_gallery)).pack(side="right", padx=(0, 8))
        ctk.CTkButton(btn_row, text=self.ar("فتح الصورة"), width=110, height=34, fg_color="#555555", hover_color="#666666", command=lambda: self.open_image_source(image_url_entry.get().strip())).pack(side="right", padx=(0, 8))
        ctk.CTkLabel(fields_frame, text=self.ar("يمكنك إدخال رابط صورة من الإنترنت أو اختيار ملف من الجهاز"), font=("Arial", 10), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", pady=(0, 8))
        def set_primary_image(source):
            image_url_entry.delete(0, "end")
            if source:
                image_url_entry.insert(0, source)

        render_gallery = self.create_images_gallery(
            fields_frame,
            selected_images,
            primary_getter=lambda: image_url_entry.get().strip(),
            primary_setter=set_primary_image,
            on_primary_change=refresh_preview
        )

        ctk.CTkLabel(fields_frame, text=self.ar("الظهور للعميل"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        visibility_menu = ctk.CTkOptionMenu(fields_frame, values=["ظاهر", "مخفي"], height=40, font=("Arial", 13))
        visibility_menu.set("ظاهر")
        visibility_menu.pack(fill="x", pady=(0, 8))

        image_url_entry.bind("<FocusOut>", lambda _e: refresh_preview())
        image_url_entry.bind("<KeyRelease>", lambda _e: refresh_preview())
        refresh_preview()

        is_saving = False

        def save_product():
            nonlocal is_saving
            if is_saving:
                return
            try:
                name = name_entry.get().strip()
                if not name:
                    self.show_error("اسم المنتج مطلوب")
                    name_entry.focus()
                    return
                
                try:
                    price = self.safe_float(price_entry.get(), "السعر")
                    if price <= 0:
                        self.show_error("السعر يجب أن يكون أكبر من 0")
                        price_entry.focus()
                        return
                except ValueError as e:
                    self.show_error(str(e))
                    price_entry.focus()
                    return
                
                try:
                    quantity = self.safe_int(quantity_entry.get(), "الكمية")
                    if quantity < 0:
                        self.show_error("الكمية لا يمكن أن تكون سالبة")
                        quantity_entry.focus()
                        return
                except ValueError as e:
                    self.show_error(str(e))
                    quantity_entry.focus()
                    return
                
                expiry_date_raw = expiry_entry.get().strip()
                expiry_date = ""
                if expiry_date_raw:
                    try:
                        expiry_date = self.normalize_expiry_date(expiry_date_raw)
                    except ValueError as e:
                        self.show_error(str(e))
                        expiry_entry.focus()
                        return
                
                if not self.check_server_health():
                    self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
                    return

                category_id = self.get_category_id_by_name(category_menu.get())
                is_active = 1 if visibility_menu.get() == "ظاهر" else 0
                duplicate = self.find_duplicate_product(name, category_menu.get())
                if duplicate:
                    merge = messagebox.askyesno(self.ar("منتج مكرر"), self.ar("هذا المنتج موجود بالفعل، هل تريد زيادة الكمية على المنتج الحالي بدل إنشاء نسخة جديدة؟"))
                    if merge:
                        current_qty = int(duplicate.get("quantity") or 0)
                        merged_qty = current_qty + quantity
                        keep_price = messagebox.askyesno(self.ar("تحديث السعر"), self.ar("هل تريد تحديث السعر بالسعر الجديد؟"))
                        merged_price = price if keep_price else self.get_product_price(duplicate)
                        description = description_box.get("1.0", "end").strip() or duplicate.get("description", "")
                        images = self.collect_images_for_save(selected_images, image_url_entry.get().strip())
                        if not images:
                            images = self.get_product_images(duplicate)
                        image_url = images[0] if images else (duplicate.get("image_url") or "")
                        try:
                            merged = self.api_client.update_product(
                                duplicate.get("id"),
                                duplicate.get("name"),
                                merged_price,
                                merged_qty,
                                duplicate.get("expiry_date") or expiry_date,
                                duplicate.get("image_path", ""),
                                image_url,
                                int(duplicate.get("is_active", 1) or 1),
                                duplicate.get("category_id", category_id),
                                description,
                                images,
                            )
                        except TypeError:
                            merged = self.api_client.update_product(duplicate.get("id"), duplicate.get("name"), merged_price, merged_qty, duplicate.get("expiry_date") or expiry_date, duplicate.get("image_path", ""))
                        if merged:
                            self.show_info(self.ar("تمت زيادة كمية المنتج الحالي بنجاح"))
                            dialog.destroy()
                            self.load_products()
                        else:
                            self.show_error(self.ar("فشل تحديث المنتج الحالي"))
                        return

                is_saving = True
                save_btn.configure(text=self.ar("جاري الحفظ..."), state="disabled")
                self.update_status("جاري حفظ المنتج...")

                description = description_box.get("1.0", "end").strip()
                images = self.collect_images_for_save(selected_images, image_url_entry.get().strip())
                image_url = images[0] if images else ""
                try:
                    result = self.api_client.create_product(name, price, quantity, expiry_date, image_path_var.get(), image_url, is_active, category_id, description, images)
                except TypeError:
                    result = self.api_client.create_product(name, price, quantity, expiry_date, image_path_var.get())

                if result:
                    self.show_info(f"✅ تم إضافة المنتج '{name}' بنجاح")
                    dialog.destroy()
                    self.load_products()
                    self.update_status(f"✅ تم إضافة منتج جديد: {name}")
                else:
                    self.show_error(
                        "فشل إضافة المنتج.\n\n"
                        "الأسباب المحتملة:\n"
                        "• اسم المنتج قد يكون مكرراً\n"
                        "• مشكلة في الاتصال بقاعدة البيانات\n\n"
                        "تأكد من أن السيرفر يعمل بشكل صحيح"
                    )
                    
            except Exception as e:
                self.show_error(f"حدث خطأ غير متوقع: {str(e)}")
            finally:
                is_saving = False
                save_btn.configure(text=self.ar("حفظ"), state="normal")
                self.update_status("جاهز")

        buttons_frame = ctk.CTkFrame(main_frame, fg_color="#252525", corner_radius=10)
        buttons_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        save_btn = ctk.CTkButton(buttons_frame, text=self.ar("حفظ"), height=40, font=("Arial", 13, "bold"), fg_color="#4CAF50", hover_color="#45a049", command=save_product)
        save_btn.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=10)
        ctk.CTkButton(buttons_frame, text=self.ar("إلغاء"), height=40, font=("Arial", 13, "bold"), fg_color="#555555", hover_color="#666666", command=dialog.destroy).grid(row=0, column=1, sticky="ew", padx=(6, 10), pady=10)

        dialog.bind("<Return>", lambda e: save_product())
    
    def edit_product(self, product):
        """Edit existing product"""
        if not self.can_manage_products():
            self.show_permission_denied()
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title(self.ar("تعديل المنتج"))
        dialog.geometry("620x700")
        dialog.resizable(True, True)
        dialog.minsize(560, 640)
        dialog.transient(self)
        dialog.grab_set()
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        main_frame = ctk.CTkFrame(dialog, fg_color="#2d2d2d", corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(main_frame, text=self.ar("تعديل المنتج"), font=("Arial", 20, "bold"), text_color="#2196F3", anchor="e", justify="right").grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        form_area = ctk.CTkScrollableFrame(main_frame, fg_color="#252525", corner_radius=12)
        form_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        fields_frame = ctk.CTkFrame(form_area, fg_color="transparent")
        fields_frame.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(fields_frame, text=self.ar("اسم المنتج"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(8, 4))
        name_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        name_entry.insert(0, product.get("name", ""))
        name_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(name_entry)

        category_options = self.get_category_options()
        ctk.CTkLabel(fields_frame, text=self.ar("التصنيف"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        category_menu = ctk.CTkOptionMenu(fields_frame, values=category_options, height=40, font=("Arial", 13))
        current_category = self.get_product_category_display(product)
        category_menu.set(current_category if current_category in category_options else "بدون تصنيف")
        category_menu.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(fields_frame, text=self.ar("السعر (EGP)"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        price_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        actual_price = self.get_product_price(product)
        price_entry.insert(0, str(actual_price))
        price_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(price_entry)

        ctk.CTkLabel(fields_frame, text=self.ar("الكمية"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        quantity_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        quantity_entry.insert(0, str(product.get("quantity", 0)))
        quantity_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(quantity_entry)

        ctk.CTkLabel(fields_frame, text=self.ar("تاريخ الصلاحية"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        ctk.CTkLabel(fields_frame, text=self.ar("الصيغ المدعومة: 2026-04-30 أو 20260430 أو 30/04/2026 أو 30-04-2026"), font=("Arial", 10), text_color="#888888", anchor="e", justify="right").pack(fill="x", pady=(0, 5))
        expiry_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        expiry_date = self.get_product_expiry(product)
        expiry_entry.insert(0, expiry_date)
        expiry_entry.pack(fill="x", pady=(0, 12))
        self.bind_entry_shortcuts(expiry_entry)
        expiry_entry.bind("<FocusOut>", lambda e: self.format_expiry_date_focus_out(expiry_entry))
        expiry_entry.bind("<FocusIn>", lambda e: self.reset_entry_border(expiry_entry))

        ctk.CTkLabel(fields_frame, text=self.ar("وصف المنتج"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        description_box = ctk.CTkTextbox(fields_frame, height=92, font=("Arial", 13))
        description_box.insert("1.0", product.get("description", "") or "")
        description_box.pack(fill="x", pady=(0, 12))

        image_path_var = ctk.StringVar(value=product.get("image_path", "") or "")
        ctk.CTkLabel(fields_frame, text=self.ar("رابط الصورة (URL) / مسار الصورة"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        image_url_entry = ctk.CTkEntry(fields_frame, height=40, font=("Arial", 13), justify="right")
        selected_images = [source for source in self.get_product_images(product) if source]
        image_url_entry.insert(0, selected_images[0] if selected_images else (product.get("image_url", "") or product.get("image_path", "") or ""))
        image_url_entry.pack(fill="x", pady=(0, 8))
        self.bind_entry_shortcuts(image_url_entry)

        preview_after_id = None
        preview_box = ctk.CTkFrame(fields_frame, fg_color="#1f1f1f", width=130, height=130, corner_radius=12, border_width=1, border_color="#3a3a3a")
        preview_box.pack(anchor="e", pady=(8, 10))
        preview_box.pack_propagate(False)
        preview_label = tk.Label(preview_box, text="لا توجد صورة", bg="#1f1f1f", fg="#bdbdbd", font=("Arial", 10), bd=0, compound="center")
        preview_label.place(relx=0.5, rely=0.5, anchor="center", width=120, height=120)

        def refresh_preview():
            nonlocal preview_after_id
            if preview_after_id:
                try:
                    dialog.after_cancel(preview_after_id)
                except Exception:
                    pass
            preview_after_id = dialog.after(250, lambda: self.update_image_widget(preview_label, image_url_entry.get().strip(), size=120))

        btn_row = ctk.CTkFrame(fields_frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(btn_row, text=self.ar("اختيار صورة"), width=120, height=34, fg_color="#2196F3", hover_color="#1976D2", command=lambda: self.pick_image_path_for_entry(image_url_entry, refresh_preview)).pack(side="right")
        ctk.CTkButton(btn_row, text=self.ar("اختيار عدة صور"), width=130, height=34, fg_color="#4CAF50", hover_color="#43A047", command=lambda: self.pick_multiple_images(selected_images, render_gallery)).pack(side="right", padx=(0, 8))
        ctk.CTkButton(btn_row, text=self.ar("فتح الصورة"), width=110, height=34, fg_color="#555555", hover_color="#666666", command=lambda: self.open_image_source(image_url_entry.get().strip())).pack(side="right", padx=(0, 8))
        ctk.CTkLabel(fields_frame, text=self.ar("يمكنك إدخال رابط صورة من الإنترنت أو اختيار ملف من الجهاز"), font=("Arial", 10), text_color="#bdbdbd", anchor="e", justify="right").pack(fill="x", pady=(0, 8))
        def set_primary_image(source):
            image_url_entry.delete(0, "end")
            if source:
                image_url_entry.insert(0, source)

        render_gallery = self.create_images_gallery(
            fields_frame,
            selected_images,
            primary_getter=lambda: image_url_entry.get().strip(),
            primary_setter=set_primary_image,
            on_primary_change=refresh_preview
        )

        ctk.CTkLabel(fields_frame, text=self.ar("الظهور للعميل"), font=("Arial", 13), anchor="e", justify="right").pack(fill="x", pady=(4, 4))
        visibility_menu = ctk.CTkOptionMenu(fields_frame, values=["ظاهر", "مخفي"], height=40, font=("Arial", 13))
        visibility_menu.set("ظاهر" if int(product.get("is_active", 1) or 1) == 1 else "مخفي")
        visibility_menu.pack(fill="x", pady=(0, 8))
        image_url_entry.bind("<FocusOut>", lambda _e: refresh_preview())
        image_url_entry.bind("<KeyRelease>", lambda _e: refresh_preview())
        refresh_preview()

        is_updating = False
        
        def update_product():
            nonlocal is_updating
            
            if is_updating:
                return
            
            try:
                # Validate name
                name = name_entry.get().strip()
                if not name:
                    self.show_error("اسم المنتج مطلوب")
                    name_entry.focus()
                    return
                
                # Validate price
                try:
                    price = self.safe_float(price_entry.get(), "السعر")
                    if price <= 0:
                        self.show_error("السعر يجب أن يكون أكبر من 0")
                        price_entry.focus()
                        return
                except ValueError as e:
                    self.show_error(str(e))
                    price_entry.focus()
                    return
                
                # Validate quantity
                try:
                    quantity = self.safe_int(quantity_entry.get(), "الكمية")
                    if quantity < 0:
                        self.show_error("الكمية لا يمكن أن تكون سالبة")
                        quantity_entry.focus()
                        return
                except ValueError as e:
                    self.show_error(str(e))
                    quantity_entry.focus()
                    return
                
                # Validate and normalize expiry date
                expiry_date_raw = expiry_entry.get().strip()
                expiry_date = ""
                if expiry_date_raw:
                    try:
                        expiry_date = self.normalize_expiry_date(expiry_date_raw)
                    except ValueError as e:
                        self.show_error(str(e))
                        expiry_entry.focus()
                        return
                
                # Check server health
                if not self.check_server_health():
                    self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
                    return
                
                is_updating = True
                save_btn.configure(text=self.ar("جاري التحديث..."), state="disabled")
                self.update_status("جاري تحديث المنتج...")

                category_id = self.get_category_id_by_name(category_menu.get())
                is_active = 1 if visibility_menu.get() == "ظاهر" else 0
                description = description_box.get("1.0", "end").strip()
                images = self.collect_images_for_save(selected_images, image_url_entry.get().strip())
                image_url = images[0] if images else ""
                try:
                    result = self.api_client.update_product(
                        product["id"], name, price, quantity, expiry_date, image_path_var.get(), image_url, is_active, category_id, description, images
                    )
                except TypeError:
                    result = self.api_client.update_product(
                        product["id"], name, price, quantity, expiry_date, image_path_var.get()
                    )
                
                if result:
                    self.show_info(f"✅ تم تحديث المنتج '{name}' بنجاح")
                    dialog.destroy()
                    self.load_products()
                    self.update_status("✅ تم تحديث المنتج")
                else:
                    self.show_error(
                        "فشل تحديث المنتج.\n\n"
                        "الأسباب المحتملة:\n"
                        "• اسم المنتج قد يكون مكرراً\n"
                        "• مشكلة في الاتصال بقاعدة البيانات\n\n"
                        "تأكد من أن السيرفر يعمل بشكل صحيح"
                    )
                    
            except Exception as e:
                self.show_error(f"حدث خطأ غير متوقع: {str(e)}")
            finally:
                is_updating = False
                save_btn.configure(text=self.ar("حفظ التغييرات"), state="normal")
                self.update_status("جاهز")

        buttons_frame = ctk.CTkFrame(main_frame, fg_color="#252525", corner_radius=10)
        buttons_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        save_btn = ctk.CTkButton(buttons_frame, text=self.ar("حفظ التغييرات"), height=40, font=("Arial", 13, "bold"), fg_color="#4CAF50", hover_color="#45a049", command=update_product)
        save_btn.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=10)
        ctk.CTkButton(buttons_frame, text=self.ar("إلغاء"), height=40, font=("Arial", 13, "bold"), fg_color="#555555", hover_color="#666666", command=dialog.destroy).grid(row=0, column=1, sticky="ew", padx=(6, 10), pady=10)

        dialog.bind("<Return>", lambda e: update_product())
    
    def delete_product(self, product_id):
        """Delete product after confirmation"""
        if not self.can_manage_products():
            self.show_permission_denied()
            return
        if not self.check_server_health():
            self.show_error("السيرفر غير متصل. تأكد من تشغيل السيرفر")
            return
        
        if messagebox.askyesno("تأكيد الحذف", "⚠️ هل أنت متأكد من حذف هذا المنتج؟\n\nلا يمكن التراجع عن هذا الإجراء."):
            try:
                self.update_status("جاري حذف المنتج...")
                
                success = self.api_client.delete_product(product_id)
                
                if success:
                    self.show_info("✅ تم حذف المنتج بنجاح")
                    self.load_products()
                    self.update_status("✅ تم حذف المنتج")
                else:
                    self.show_error(
                        "فشل حذف المنتج.\n\n"
                        "الأسباب المحتملة:\n"
                        "• المنتج قد يكون مرتبطاً بطلبات\n"
                        "• مشكلة في الاتصال بقاعدة البيانات\n"
                        "• السيرفر لا يستجيب"
                    )
                    
            except Exception as e:
                self.show_error(f"حدث خطأ أثناء الحذف: {str(e)}")
                self.update_status("❌ خطأ في حذف المنتج")
