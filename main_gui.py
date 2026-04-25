import customtkinter as ctk
from PIL import Image
import os
import ctypes
import hardware_checker
import subprocess
import psutil
import pyautogui
import threading
import time
import sys
import json

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"lm_url": "http://localhost:1234/v1", "custom_model": ""}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    path = os.path.join(base_path, relative_path)
    if not os.path.exists(path):
        alt_path = os.path.join(base_path, "_internal", relative_path)
        if os.path.exists(alt_path):
            return alt_path
    return path

try:
    import johnny_sentinel as sentinel
except ImportError:
    sentinel = None

try:
    myappid = 'mycompany.johnny_assistant.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

class SidebarWriter:
    def __init__(self, app_instance):
        self.app = app_instance

    def write(self, text):
        if text.strip() and hasattr(self.app, 'status_bar') and self.app.status_bar:
            try:
                self.app.write_to_status(text)
            except Exception:
                pass
        try:
            if sys.__stdout__ is not None:
                sys.__stdout__.write(text)
        except (AttributeError, Exception):
            pass

    def flush(self):
        try:
            if sys.__stdout__ is not None:
                sys.__stdout__.flush()
        except (AttributeError, Exception):
            pass

class JohnnyApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        self.apply_settings_to_sentinel()

        self.check_and_launch_lm_studio()

        self.title("Джонни")
        self.width = 650
        self.height = 180
        self.geometry(f"{self.width}x{self.height}+500+300")

        self.overrideredirect(True)
        self.attributes("-alpha", 0.90)
        self.attributes("-topmost", True)

        self.icon_off = resource_path("icon_off.ico")
        self.icon_on = resource_path("icon_on.ico")

        if os.path.exists(self.icon_off):
            try:
                self.iconbitmap(self.icon_off)
            except Exception:
                pass

        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a", border_width=1, border_color="#333333")
        self.main_frame.pack(fill="both", expand=True)

        self.main_frame.bind("<Button-1>", self.start_move)
        self.main_frame.bind("<B1-Motion>", self.on_move)

        self.load_images()
        self.setup_ui()

        self.sentinel_thread = None
        sys.stdout = SidebarWriter(self)

    def apply_settings_to_sentinel(self):
        if sentinel:
            try:
                sentinel.client.base_url = self.settings.get("lm_url", "http://localhost:1234/v1")
                # Передаем кастомную модель в модуль sentinel (чтобы он мог ее использовать при поиске)
                sentinel.CUSTOM_TARGET_MODEL = self.settings.get("custom_model", "")
            except Exception as e:
                print(f"[!] Ошибка применения настроек: {e}")

    def is_process_running(self, process_name):
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def check_and_launch_lm_studio(self):
        if self.is_process_running("LM Studio.exe"):
            print("[!] LM Studio уже работает.")
        else:
            user_home = os.path.expanduser("~")
            lm_path = os.path.join(user_home, "AppData", "Local", "Programs", "LM Studio", "LM Studio.exe")
            if os.path.exists(lm_path):
                try:
                    subprocess.Popen(lm_path)
                    print("[!] Запускаю LM Studio...")
                    threading.Timer(8.0, self.automate_lm_studio).start()
                except Exception as e:
                    print(f"[!] Не удалось запустить LM Studio: {e}")

    def automate_lm_studio(self):
        print("[*] Активация функций LM Studio...")
        try:
            window_found = False
            for window in pyautogui.getAllWindows():
                if "LM Studio" in window.title:
                    window.activate()
                    window_found = True
                    break

            if not window_found:
                print("[-] Окно LM Studio не найдено.")
                return

            time.sleep(2.0)
            pyautogui.hotkey('ctrl', '2')
            print("[+] Переход в Developer (Ctrl+2)")
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'l')
            print("[+] Меню выбора модели (Ctrl+L)")
            time.sleep(1.0)
            pyautogui.hotkey('ctrl', 'r')
            print("[+] Запуск сервера (Ctrl+R)")

        except Exception as e:
            print(f"[!] Ошибка автоматизации: {e}")

    def write_to_status(self, text):
        try:
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.configure(state="normal")
                self.status_bar.delete(0, "end")
                self.status_bar.insert(0, str(text).strip())
                self.status_bar.configure(state="disabled")
        except:
            pass

    def setup_ui(self):
        self.logo_label = ctk.CTkLabel(self.main_frame, text="", image=self.img_base)
        self.logo_label.grid(row=0, column=0, rowspan=3, padx=(30, 20), pady=20)

        self.ctrl_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.ctrl_frame.place(x=self.width - 85, y=10)

        self.min_btn = ctk.CTkLabel(self.ctrl_frame, text="—", font=("Arial", 14, "bold"), text_color="#777777", cursor="hand2")
        self.min_btn.pack(side="left", padx=10)
        self.min_btn.bind("<Button-1>", self.safe_minimize)

        self.close_btn = ctk.CTkLabel(self.ctrl_frame, text="✕", font=("Arial", 16), text_color="#777777", cursor="hand2")
        self.close_btn.pack(side="left", padx=5)
        self.close_btn.bind("<Button-1>", lambda e: self.destroy())

        self.title_label = ctk.CTkLabel(self.main_frame, text="AI Ассистент ДЖОННИ", font=("Segoe UI", 16, "bold"), text_color="#ffffff")
        self.title_label.grid(row=0, column=1, sticky="sw", pady=(20, 0))

        self.status_bar = ctk.CTkEntry(self.main_frame, width=420, height=35, placeholder_text="Джонни готов...", corner_radius=8, fg_color="#252525", border_color="#3a3a3a")
        self.status_bar.grid(row=1, column=1, sticky="nw", pady=10)
        self.status_bar.configure(state="disabled")

        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.grid(row=2, column=1, sticky="nw", pady=(0, 20))

        self.is_active = False
        self.toggle_btn = ctk.CTkButton(self.btn_frame, text="ВКЛЮЧИТЬ", width=120, height=32, corner_radius=6, command=self.toggle_johnny)
        self.toggle_btn.pack(side="left", padx=(0, 10))

        self.diag_btn = ctk.CTkButton(self.btn_frame, text="Диагностика", width=100, height=32, corner_radius=6, fg_color="#333333", command=self.open_diagnostic_window)
        self.diag_btn.pack(side="left", padx=(0, 10))

        self.settings_btn = ctk.CTkButton(self.btn_frame, text="Настройки", width=100, height=32, corner_radius=6, fg_color="#333333", command=self.open_settings_window)
        self.settings_btn.pack(side="left")

    def load_images(self):
        img_0_path = resource_path("image_0.png")
        img_1_path = resource_path("image_1.png")

        try:
            img_0 = Image.open(img_0_path).convert("RGBA")
            img_1 = Image.open(img_1_path).convert("RGBA")
            self.img_base = ctk.CTkImage(img_0, size=(85, 85))
            self.img_active = ctk.CTkImage(img_1, size=(85, 85))
        except Exception:
            self.img_base = None
            self.img_active = None

    def safe_minimize(self, event):
        try:
            self.overrideredirect(False)
            self.state('iconic')
            self.bind("<FocusIn>", self.restore_from_minimize)
        except Exception as e:
            print(f"Ошибка сворачивания: {e}")

    def restore_from_minimize(self, event):
        self.overrideredirect(True)
        self.unbind("<FocusIn>")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def on_move(self, event):
        self.geometry(f"+{self.winfo_x() + (event.x - self.x)}+{self.winfo_y() + (event.y - self.y)}")

    def toggle_johnny(self):
        if not self.is_active:
            self.is_active = True
            self.toggle_btn.configure(text="ВЫКЛЮЧИТЬ", fg_color="#c0392b")
            if self.img_active:
                self.logo_label.configure(image=self.img_active)

            if sentinel:
                sentinel.is_working = True
                self.apply_settings_to_sentinel()
                self.sentinel_thread = threading.Thread(target=sentinel.start_listening, args=(self,), daemon=True)
                self.sentinel_thread.start()
        else:
            self.is_active = False
            self.toggle_btn.configure(text="ВКЛЮЧИТЬ", fg_color="#1f6aa5")
            if self.img_base:
                self.logo_label.configure(image=self.img_base)

            if sentinel:
                sentinel.is_working = False
                print("[*] Поток Джонни останавливается...")

    def open_diagnostic_window(self):
        diag_window = ctk.CTkToplevel(self)
        diag_window.title("Диагностика системы")
        diag_window.geometry("480x320")
        diag_window.attributes("-topmost", True)
        diag_window.after(200, lambda: diag_window.focus())

        icon_path = resource_path("icon_off.ico")
        if os.path.exists(icon_path):
            try:
                diag_window.iconbitmap(icon_path)
            except Exception:
                pass

        label = ctk.CTkLabel(diag_window, text="Результаты проверки оборудования:", font=("Segoe UI", 14, "bold"))
        label.pack(pady=(15, 5))
        txt = ctk.CTkTextbox(diag_window, width=440, height=220, corner_radius=10, fg_color="#222222")
        txt.pack(pady=10, padx=20)
        try:
            res = hardware_checker.get_system_recommendation()
            txt.insert("0.0", res)
        except Exception as e:
            txt.insert("0.0", f"Ошибка модуля: {e}")
        txt.configure(state="disabled")

    def open_settings_window(self):
        set_win = ctk.CTkToplevel(self)
        set_win.title("Настройки LM Studio")
        set_win.geometry("450x250")
        set_win.attributes("-topmost", True)
        set_win.after(200, lambda: set_win.focus())

        icon_path = resource_path("icon_off.ico")
        if os.path.exists(icon_path):
            try: set_win.iconbitmap(icon_path)
            except Exception: pass

        ctk.CTkLabel(set_win, text="URL сервера API (Localhost):", font=("Segoe UI", 12, "bold")).pack(pady=(15, 0))
        url_entry = ctk.CTkEntry(set_win, width=380)
        url_entry.pack(pady=5)
        url_entry.insert(0, self.settings.get("lm_url", "http://localhost:1234/v1"))

        ctk.CTkLabel(set_win, text="Точное название модели (оставьте пустым для автопоиска):", font=("Segoe UI", 12, "bold")).pack(pady=(15, 0))
        mod_entry = ctk.CTkEntry(set_win, width=380, placeholder_text="Например: qwen2.5-coder-14b")
        mod_entry.pack(pady=5)
        mod_entry.insert(0, self.settings.get("custom_model", ""))

        def save_and_close():
            self.settings["lm_url"] = url_entry.get().strip()
            self.settings["custom_model"] = mod_entry.get().strip()
            save_settings(self.settings)
            self.apply_settings_to_sentinel()
            print("[!] Настройки успешно сохранены.")
            set_win.destroy()

        save_btn = ctk.CTkButton(set_win, text="Сохранить", command=save_and_close, fg_color="#27ae60", hover_color="#2ecc71")
        save_btn.pack(pady=20)

if __name__ == "__main__":
    app = JohnnyApp()
    app.mainloop()