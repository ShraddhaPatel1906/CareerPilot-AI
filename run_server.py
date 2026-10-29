import sys
import os

# Ensure Windows CP1252 console handles UTF-8 without crashing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(1.5)
    print("\n[+] Opening browser to http://127.0.0.1:8080 ...")
    webbrowser.open("http://127.0.0.1:8080")

if __name__ == "__main__":
    print("\n" + "="*65)
    print("[*] CAREERPILOT AI: STARTING WEB DASHBOARD & BACKEND SERVER")
    print("="*65)
    print("  -> Web Dashboard:    http://127.0.0.1:8080")
    print("  -> API Documentation: http://127.0.0.1:8080/docs")
    print("="*65 + "\n")
    
    # Auto-open browser in background
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run Uvicorn on Port 8080
    uvicorn.run("src.voice_agent:app", host="127.0.0.1", port=8080, reload=False)
