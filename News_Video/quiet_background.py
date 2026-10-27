"""Hide only Agent Reach Python helper consoles; never close browsers or terminals."""
import os,subprocess,threading
from contextlib import contextmanager

def hidden_kwargs():
    if os.name!='nt':return {}
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    return dict(creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=startup)

def hide_reach_consoles():
    if os.name!='nt':return 0
    import ctypes
    from ctypes import wintypes
    u=ctypes.WinDLL('user32',use_last_error=True)
    u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    u.IsWindowVisible.argtypes=[wintypes.HWND];u.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
    count=[];prefix=str(Path_home()/'.agent-reach'/'tools').lower()+chr(92)
    @ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def visit(hwnd,param):
        title=ctypes.create_unicode_buffer(2048);u.GetWindowTextW(hwnd,title,2048)
        value=title.value.lower()
        if value.startswith(prefix) and value.endswith(('\\python.exe','\\pythonw.exe')) and u.IsWindowVisible(hwnd):
            u.ShowWindow(hwnd,0);count.append(1)
        return True
    u.EnumWindows(visit,0);return len(count)

def Path_home():
    from pathlib import Path
    return Path.home()

@contextmanager
def quiet_reach():
    stop=threading.Event()
    def hide():
        while not stop.is_set():
            try:hide_reach_consoles()
            except (OSError,AttributeError):pass
            stop.wait(.2)
    worker=threading.Thread(target=hide,daemon=True) if os.name=='nt' else None
    if worker:worker.start()
    try:yield
    finally:
        stop.set()
        if worker:worker.join(timeout=1)
        if os.name=='nt':
            try:hide_reach_consoles()
            except (OSError,AttributeError):pass
