import os, sys, json, zipfile, shutil, subprocess, hashlib, tkinter as tk, threading, queue
from tkinter import filedialog, messagebox
from pathlib import Path
from bidi.algorithm import get_display

def rtl(text):
    try: return get_display(str(text))
    except Exception: return str(text)

APP = "ZipExtensionLoader"
ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / APP
PROFILE = ROOT / "chrome-profile"
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

class CDP:
    def __init__(self, websocket_url):
        import websocket
        self.ws = websocket.create_connection(websocket_url, timeout=20, suppress_origin=True)
        self.seq = 0

    def call(self, method, params=None, timeout=30):
        self.seq += 1
        self.ws.settimeout(timeout)
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params or {}}, separators=(",", ":")))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") != self.seq:
                continue
            if "error" in msg:
                raise RuntimeError(msg["error"].get("message", "CDP error"))
            return msg.get("result", {})

def launch_and_load(path):
    if os.name != "nt": raise RuntimeError("היישום מיועד ל-Windows בלבד.")
    chrome=find_chrome()
    if not chrome: raise RuntimeError("לא נמצא Google Chrome.")
    import time, urllib.request
    ROOT.mkdir(parents=True, exist_ok=True)
    sessions = ROOT / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    # Use a fresh profile so Chrome cannot forward this launch to an older
    # process using the same profile and close the debugging channel.
    profile = sessions / ("profile-" + __import__("uuid").uuid4().hex)
    profile.mkdir(parents=True, exist_ok=True)
    args=[str(chrome),"--remote-debugging-port=0","--enable-unsafe-extension-debugging",
          "--remote-allow-origins=*",
          f"--load-extension={EXT.resolve()}",f"--user-data-dir={profile}",
          "--no-first-run","--no-default-browser-check","chrome://extensions"]
    proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    active_port = profile / "DevToolsActivePort"
    try:
        deadline=time.time()+25
        port=None
        while time.time()<deadline:
            if proc.poll() is not None:
                raise RuntimeError("Chrome נסגר לפני שהפעיל את ממשק הניפוי. בדוק אם Chrome מעודכן או אם מדיניות המחשב חוסמת ניפוי.")
            if active_port.is_file():
                lines=active_port.read_text(encoding="utf-8",errors="ignore").splitlines()
                if lines and lines[0].isdigit():
                    port=int(lines[0]); break
            time.sleep(0.25)
        if port is None:
            raise RuntimeError("Chrome לא פתח את ממשק הניפוי בזמן.")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version",timeout=5) as response:
            version=json.load(response)
        ws_url=version.get("webSocketDebuggerUrl")
        if not ws_url: raise RuntimeError("Chrome לא סיפק כתובת WebSocket לניפוי.")
        cdp=CDP(ws_url)
        cdp.call("Extensions.loadUnpacked",{"path":str(Path(path).resolve())},timeout=30)
        return proc
    except Exception:
        if proc.poll() is None:
            proc.terminate()
        raise

class App:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("ZIP Extension Loader")
        self.root.geometry("560x330")
        self.root.resizable(False,False)
        self.root.configure(bg="#f5f7fb")
        style={"bg":"#f5f7fb","fg":"#172033"}
        tk.Label(self.root,text="טעינת תוסף Chrome מקובץ ZIP",font=("Segoe UI",17,"bold"),**style).pack(pady=(28,12))
        tk.Label(self.root,text="בחר קובץ ZIP של תוסף. הכלי יחלץ אותו ויטען בחלון Chrome נפרד.",wraplength=500,font=("Segoe UI",11),**style).pack(pady=6)
        tk.Button(self.root,text="בחירת ZIP וטעינה",font=("Segoe UI",12,"bold"),width=28,height=2,
                  bg="#2563eb",fg="white",activebackground="#1d4ed8",activeforeground="white",
                  relief="flat",command=self.choose).pack(pady=24)
        self.status=tk.StringVar(value="Chrome הרגיל שלך לא יושפע.")
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
            launch_and_load(folder)
            self.status.set("נשלחה בקשת טעינה: "+name)
            messagebox.showinfo("הטעינה הסתיימה","בקשת הטעינה נשלחה ל-Chrome בחלון ייעודי.")
        except Exception as e:
            self.status.set("הטעינה נכשלה")
            messagebox.showerror("שגיאה",str(e))
    def run(self): self.root.mainloop()

if __name__=="__main__": App().run()
