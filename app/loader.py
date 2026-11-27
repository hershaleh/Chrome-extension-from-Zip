import os, sys, json, zipfile, shutil, subprocess, tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from bidi.algorithm import get_display

def rtl(text):
    try: return get_display(str(text))
    except Exception: return str(text)

APP = "ZipExtensionLoader"
ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP
DEST = ROOT / "loaded-extensions"
MAX_ZIP = 300 * 1024 * 1024
EXT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "extension"

def find_chrome():
    roots = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
             os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
             os.environ.get("LOCALAPPDATA", "")]
    for root in roots:
        p = Path(root) / "Google/Chrome/Application/chrome.exe"
        if p.is_file(): return p
    return None

def extract_zip(zip_path):
    zip_path = Path(zip_path)
    if zip_path.stat().st_size > MAX_ZIP: raise ValueError("קובץ ZIP גדול מדי (מקסימום 300MB).")
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / zip_path.stem
    if target.exists(): shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        total = 0
        for info in z.infolist():
            # ZIP paths are POSIX paths even on Windows; reject traversal and drive paths.
            raw = info.filename.replace("\\", "/")
            parts = raw.split("/")
            if raw.startswith("/") or any(p == ".." for p in parts) or (parts and ":" in parts[0]):
                raise ValueError("הארכיון מכיל נתיב לא בטוח.")
            total += info.file_size
            if total > 800 * 1024 * 1024: raise ValueError("הארכיון גדול מדי לאחר חילוץ.")
            out = (target / raw).resolve()
            if target.resolve() not in out.parents and out != target.resolve(): raise ValueError("נתיב ZIP לא בטוח.")
            if info.is_dir(): out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(out, "wb") as dst: shutil.copyfileobj(src, dst)
    manifest = target / "manifest.json"
    if not manifest.is_file():
        matches = list(target.rglob("manifest.json"))
        if len(matches) != 1: raise ValueError("לא נמצא manifest.json יחיד בתוסף.")
        target = matches[0].parent
    try:
        data = json.loads((target / "manifest.json").read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not data.get("manifest_version"): raise ValueError()
    except Exception: raise ValueError("manifest.json אינו תקין או חסר manifest_version.")
    return target, str(data.get("name") or target.name)

def find_extensions_window():
    from pywinauto import Desktop
    for window in Desktop(backend="uia").windows():
        try:
            title = window.window_text()
            if ("Google Chrome" in title or "Chromium" in title) and (
                "Extensions" in title or "תוספים" in title
            ):
                return window
        except Exception:
            pass
    return None


def install_folder_through_chrome(folder):
    """Use Chrome's own Load unpacked button and automate its folder picker."""
    from pywinauto import Desktop, keyboard
    import time

    chrome_window = find_extensions_window()
    if chrome_window is None:
        raise RuntimeError("לא נמצא חלון Chrome פתוח בדף התוספים. פתח chrome://extensions ונסה שוב.")
    chrome_window.set_focus()
    time.sleep(0.4)

    load_button = None
    for item in chrome_window.descendants(control_type="Button"):
        try:
            label = item.window_text().strip().lower()
            if label in ("load unpacked", "טעינת תוסף שלא נארז", "טעינת תוסף לא ארוז"):
                load_button = item
                break
        except Exception:
            pass
    if load_button is None:
        raise RuntimeError("לא נמצא כפתור 'טעינת תוסף שלא נארז'. ודא שמצב המפתח מופעל בדף התוספים.")

    load_button.click_input()
    time.sleep(0.8)

    desktop = Desktop(backend="uia")
    dialog = None
    deadline = time.time() + 10
    while time.time() < deadline:
        for item in desktop.windows():
            try:
                title = item.window_text().lower()
                if any(word in title for word in ("select", "בחר", "extension directory", "תיקייה")):
                    dialog = item
                    break
            except Exception:
                pass
        if dialog is not None:
            break
        time.sleep(0.2)
    if dialog is None:
        raise RuntimeError("Chrome לא פתח את חלון בחירת תיקיית התוסף.")

    dialog.set_focus()
    keyboard.send_keys("^l")
    keyboard.send_keys(str(Path(folder).resolve()), with_spaces=True, pause=0.01)
    keyboard.send_keys("{ENTER}")
    time.sleep(0.5)

    select_button = None
    for item in dialog.descendants(control_type="Button"):
        try:
            if item.window_text().strip().lower() in (
                "select folder", "בחר תיקייה", "בחירת תיקייה", "בחר תיקיה"
            ):
                select_button = item
                break
        except Exception:
            pass
    if select_button is not None:
        select_button.click_input()
    else:
        keyboard.send_keys("{ENTER}")

    time.sleep(1.5)
    if dialog.exists(timeout=0.2):
        raise RuntimeError(
            "חלון בחירת התיקייה עדיין פתוח. לא בוצעה התקנה אוטומטית; "
            "בחר את התיקייה שחולצה ואשר בחלון Chrome."
        )


class App:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("ZIP Extension Loader")
        self.root.geometry("560x330")
        self.root.resizable(False,False)
        self.root.configure(bg="#f5f7fb")
        style={"bg":"#f5f7fb","fg":"#172033"}
        tk.Label(self.root,text="טעינת תוסף Chrome מקובץ ZIP",font=("Segoe UI",17,"bold"),**style).pack(pady=(28,12))
        tk.Label(self.root,text="פתח מראש chrome://extensions בפרופיל הרצוי והפעל מצב מפתח. בחר ZIP והתוכנה תחלץ ותבחר את התיקייה אוטומטית.",wraplength=500,font=("Segoe UI",11),**style).pack(pady=6)
        tk.Button(self.root,text="בחירת ZIP וטעינה",font=("Segoe UI",12,"bold"),width=28,height=2,
                  bg="#2563eb",fg="white",activebackground="#1d4ed8",activeforeground="white",
                  relief="flat",command=self.choose).pack(pady=24)
        self.status=tk.StringVar(value="יש לפתוח מראש את דף התוספים בפרופיל Chrome הרצוי.")
        if len(sys.argv) > 1 and sys.argv[1].lower().startswith("ziploader://"):
            self.root.after(650, self.choose)
        tk.Label(self.root,textvariable=self.status,wraplength=500,bg="#f5f7fb",fg="#475569",
                 font=("Segoe UI",10)).pack(pady=8)
    def choose(self):
        p=filedialog.askopenfilename(title="בחירת קובץ ZIP",filetypes=[("ZIP","*.zip")])
        if not p:return
        self.status.set("מחלץ וטוען את התוסף...")
        self.root.update_idletasks()
        try:
            folder,name=extract_zip(p)
            self.status.set("מפעיל את מנגנון הטעינה של Chrome...")
            self.root.update_idletasks()
            install_folder_through_chrome(folder)
            self.status.set("התוסף נשלח לטעינה: "+name)
            messagebox.showinfo("הפעולה הסתיימה","Chrome קיבל את תיקיית התוסף. בדוק שהוא מופיע ברשימת התוספים.")
        except Exception as e:
            self.status.set("הטעינה נכשלה")
            messagebox.showerror("שגיאה",str(e))
    def run(self): self.root.mainloop()

if __name__=="__main__": App().run()
