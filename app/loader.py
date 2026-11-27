import os, sys, json, zipfile, shutil, subprocess, hashlib, tkinter as tk, threading, queue
from tkinter import filedialog, messagebox
from pathlib import Path

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
            name = Path(info.filename)
            if name.is_absolute() or ".." in name.parts: raise ValueError("הארכיון מכיל נתיב לא בטוח.")
            total += info.file_size
            if total > 800 * 1024 * 1024: raise ValueError("הארכיון גדול מדי לאחר חילוץ.")
            out = (target / info.filename).resolve()
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
    def __init__(self, write_pipe, read_pipe):
        self.w, self.r, self.seq = write_pipe, read_pipe, 0
        self.q = queue.Queue()
        threading.Thread(target=self.reader, daemon=True).start()
    def reader(self):
        while True:
            buf = bytearray()
            while True:
                b = self.r.read(1)
                if not b: self.q.put(RuntimeError("Chrome סגר את ערוץ הניפוי.")); return
                if b == b"\0": break
                buf.extend(b)
            try: self.q.put(json.loads(buf.decode("utf-8")))
            except Exception as e: self.q.put(RuntimeError(str(e)))
    def call(self, method, params=None, timeout=30):
        self.seq += 1
        self.w.write(json.dumps({"id":self.seq,"method":method,"params":params or {}},separators=(",",":")).encode()+b"\0")
        self.w.flush()
        while True:
            msg=self.q.get(timeout=timeout)
            if isinstance(msg, Exception): raise msg
            if msg.get("id") != self.seq: continue
            if "error" in msg: raise RuntimeError(msg["error"].get("message","CDP error"))
            return msg.get("result",{})

def launch_and_load(path):
    if os.name != "nt": raise RuntimeError("היישום מיועד ל-Windows בלבד.")
    chrome=find_chrome()
    if not chrome: raise RuntimeError("לא נמצא Google Chrome.")
    ROOT.mkdir(parents=True,exist_ok=True); PROFILE.mkdir(parents=True,exist_ok=True)
    import msvcrt
    child_r,parent_w=os.pipe(); parent_r,child_w=os.pipe()
    for fd in (parent_w,parent_r): os.set_handle_inheritable(fd,False)
    for fd in (child_r,child_w): os.set_handle_inheritable(fd,True)
    pipearg=f"--remote-debugging-io-pipes={msvcrt.get_osfhandle(child_r)},{msvcrt.get_osfhandle(child_w)}"
    args=[str(chrome),"--remote-debugging-pipe",pipearg,"--enable-unsafe-extension-debugging",
          f"--user-data-dir={PROFILE}","--no-first-run","--no-default-browser-check","chrome://extensions"]
    proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                          close_fds=False,creationflags=subprocess.CREATE_NO_WINDOW)
    os.close(child_r); os.close(child_w)
    cdp=CDP(os.fdopen(parent_w,"wb",buffering=0),os.fdopen(parent_r,"rb",buffering=0))
    cdp.call("Extensions.loadUnpacked",{"path":str(EXT.resolve())})
    cdp.call("Extensions.loadUnpacked",{"path":str(Path(path).resolve())})
    return proc

class App:
    def __init__(self):
        self.root=tk.Tk(); self.root.title("טעינת תוסף ZIP ל-Chrome"); self.root.geometry("540x300"); self.root.resizable(False,False)
        tk.Label(self.root,text="טעינת תוסף Chrome מקובץ ZIP",font=("Segoe UI",16,"bold")).pack(pady=(25,12))
        tk.Label(self.root,text="בחר ZIP. הכלי יחלץ את התוסף ויטען אותו בחלון Chrome ייעודי.",font=("Segoe UI",10)).pack(pady=5)
        tk.Button(self.root,text="בחירת ZIP וטעינה אוטומטית",font=("Segoe UI",12),width=30,height=2,command=self.choose).pack(pady=22)
        self.status=tk.StringVar(value="הפרופיל נפרד מ-Chrome הרגיל.")
        tk.Label(self.root,textvariable=self.status,wraplength=490,font=("Segoe UI",10)).pack(pady=10)
    def choose(self):
        p=filedialog.askopenfilename(title="בחר ZIP",filetypes=[("ZIP","*.zip")])
        if not p:return
        try:
            folder,name=extract_zip(p); self.status.set("טוען: "+name); self.root.update_idletasks()
            launch_and_load(folder); self.status.set("בקשת הטעינה נשלחה: "+name)
            messagebox.showinfo("הטעינה הסתיימה",f"התוסף {name} נשלח לטעינה בחלון Chrome ייעודי.")
        except Exception as e:
            self.status.set("הטעינה נכשלה"); messagebox.showerror("שגיאה",str(e))
    def run(self): self.root.mainloop()

if __name__=="__main__": App().run()
