import sys, json, os, shutil, subprocess, threading, urllib.parse, urllib.request, uuid
import tkinter as tk
from tkinter import ttk, messagebox
import minecraft_launcher_lib as mll

MC_VERSION = "1.21.11"
BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(BASE, "game")
CONFIG = os.path.join(BASE, "config.json")
# Optimization mods (Modrinth slugs). All are legit and allowed on servers.
OPT_MODS = ["sodium", "lithium", "ferrite-core", "immediatelyfast", "entityculling", "fabric-api"]

def load_cfg():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"nick": "Player", "ram": 4}

def save_cfg(c):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(c, f)

def download_opt_mods(log):
    mods_dir = os.path.join(GAME_DIR, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    for slug in OPT_MODS:
        try:
            q = urllib.parse.urlencode({"game_versions": json.dumps([MC_VERSION]),
                                        "loaders": json.dumps(["fabric"])})
            req = urllib.request.Request(f"https://api.modrinth.com/v2/project/{slug}/version?{q}",
                                         headers={"User-Agent": "KoteLauncher/0.1"})
            versions = json.load(urllib.request.urlopen(req, timeout=20))
            if not versions:
                log(f"{slug}: нет версии для {MC_VERSION}"); continue
            f = next((x for x in versions[0]["files"] if x.get("primary")), versions[0]["files"][0])
            path = os.path.join(mods_dir, f["filename"])
            if not os.path.exists(path):
                log(f"Скачиваю {slug}...")
                urllib.request.urlretrieve(f["url"], path)
        except Exception as e:
            log(f"{slug}: ошибка ({e})")

def copy_kote_mod(log):
    mods_dir = os.path.join(GAME_DIR, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    src = os.path.join(BASE, "mods")
    os.makedirs(src, exist_ok=True)
    for name in os.listdir(src):
        if name.endswith(".jar"):
            shutil.copy(os.path.join(src, name), mods_dir)
            log(f"Kote Client мод: {name}")

def run_game(nick, ram, log, done):
    try:
        os.makedirs(GAME_DIR, exist_ok=True)
        cb = {"setStatus": lambda s: log(s), "setProgress": lambda p: None, "setMax": lambda m: None}
        log(f"Ставлю Fabric для {MC_VERSION}...")
        mll.fabric.install_fabric(MC_VERSION, GAME_DIR, callback=cb)
        vid = next(v["id"] for v in mll.utils.get_installed_versions(GAME_DIR)
                   if "fabric-loader" in v["id"] and v["id"].endswith(MC_VERSION))
        download_opt_mods(log)
        copy_kote_mod(log)
        opts = {"username": nick, "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, "OfflinePlayer:" + nick)),
                "token": "", "jvmArguments": [f"-Xmx{ram}G", f"-Xms{max(1, ram // 2)}G"]}
        try:
            rt = mll.runtime.get_version_runtime_information(vid, GAME_DIR)
            if rt:
                log("Ставлю Java для игры (в первый раз долго)...")
                mll.runtime.install_jvm_runtime(rt["name"], GAME_DIR, callback=cb)
                exe = mll.runtime.get_executable_path(rt["name"], GAME_DIR)
                if exe:
                    opts["executablePath"] = exe
        except Exception as e:
            log(f"Java: не вышло поставить свою ({e}), пробую системную")
        cmd = mll.command.get_minecraft_command(vid, GAME_DIR, opts)
        log("Запуск игры...")
        subprocess.Popen(cmd, cwd=GAME_DIR, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        log(f"Ошибка: {e}")
    finally:
        done()

def main():
    cfg = load_cfg()
    root = tk.Tk()
    root.title("Kote Client Launcher")
    root.geometry("460x360")
    root.configure(bg="#14101f")
    st = ttk.Style(); st.theme_use("clam")
    tk.Label(root, text="Kote Client", font=("Segoe UI", 24, "bold"), fg="#b388ff", bg="#14101f").pack(pady=(16, 0))
    tk.Label(root, text=f"Minecraft {MC_VERSION} • Fabric", fg="#8d82a8", bg="#14101f").pack()
    frm = tk.Frame(root, bg="#14101f"); frm.pack(pady=12)
    tk.Label(frm, text="Ник", fg="white", bg="#14101f").grid(row=0, column=0, sticky="w", padx=6)
    nick = tk.Entry(frm, width=22); nick.insert(0, cfg["nick"]); nick.grid(row=0, column=1, pady=4)
    tk.Label(frm, text="ОЗУ, ГБ", fg="white", bg="#14101f").grid(row=1, column=0, sticky="w", padx=6)
    ram = tk.Spinbox(frm, from_=2, to=16, width=6); ram.delete(0, "end"); ram.insert(0, cfg["ram"]); ram.grid(row=1, column=1, sticky="w", pady=4)
    logbox = tk.Text(root, height=8, width=54, bg="#0d0a16", fg="#cfc6e8", bd=0); logbox.pack(padx=12)
    def log(s):
        root.after(0, lambda: (logbox.insert("end", s + "\n"), logbox.see("end")))
    btn = tk.Button(root, text="ИГРАТЬ", font=("Segoe UI", 12, "bold"), bg="#7c4dff", fg="white", bd=0, width=18)
    def play():
        n = nick.get().strip() or "Player"
        r = int(ram.get())
        save_cfg({"nick": n, "ram": r})
        btn.config(state="disabled")
        threading.Thread(target=run_game, args=(n, r, log, lambda: root.after(0, lambda: btn.config(state="normal"))), daemon=True).start()
    btn.config(command=play); btn.pack(pady=10)
    root.mainloop()

if __name__ == "__main__":
    main()

