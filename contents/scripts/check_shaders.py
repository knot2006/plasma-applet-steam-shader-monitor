#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import json

def check():
    mock_file = "/tmp/steam_shader_mock.json"
    if os.path.exists(mock_file):
        try:
            with open(mock_file) as mf:
                return json.load(mf)
        except Exception:
            pass

    p = subprocess.run(["pgrep", "-af", "fossilize_replay"], capture_output=True, text=True)
    if p.returncode != 0:
        return {
            "active": False,
            "game": "",
            "app_id": "",
            "percent": 0,
            "counts": "",
            "threads": 0,
            "status": "Idle"
        }

    threads = 0
    tm = re.search(r"--num-threads\s+(\d+)", p.stdout)
    if tm:
        threads = int(tm.group(1))

    m_cmd = re.search(r"shadercache/(\d+)/", p.stdout)
    cmd_appid = m_cmd.group(1) if m_cmd else ""

    log_file = os.path.expanduser("~/.local/share/Steam/logs/shader_log.txt")
    app_id = cmd_appid
    percent = 0
    counts = ""

    if os.path.exists(log_file):
        try:
            with open(log_file, "rb") as f:
                f.seek(max(0, os.path.getsize(log_file) - 16384))
                content = f.read().decode("utf-8", "ignore")
                matches = re.findall(r"replaying (\d+)\s*\(([\d]+)%(?:,\s*([^)]+))?\)", content)
                if matches:
                    app_id, pct_str, counts = matches[-1]
                    percent = int(pct_str)
        except Exception:
            pass

    game_title = app_id
    lib_vdf = os.path.expanduser("~/.local/share/Steam/config/libraryfolders.vdf")
    library_paths = [os.path.expanduser("~/.local/share/Steam")]
    if os.path.exists(lib_vdf):
        try:
            with open(lib_vdf, "r", errors="ignore") as f:
                for line in f:
                    if "\"path\"" in line:
                        parts = line.strip().split("\"")
                        if len(parts) >= 4 and os.path.isdir(parts[3]):
                            library_paths.append(parts[3])
        except Exception:
            pass

    for lib in set(library_paths):
        acf_path = os.path.join(lib, "steamapps", f"appmanifest_{app_id}.acf")
        if os.path.exists(acf_path):
            try:
                with open(acf_path, "r", errors="ignore") as f:
                    for line in f:
                        if "\"name\"" in line:
                            parts = line.strip().split("\"")
                            if len(parts) >= 4:
                                game_title = parts[3]
                                break
                break
            except Exception:
                pass

    return {
        "active": True,
        "game": game_title,
        "app_id": app_id,
        "percent": percent,
        "counts": counts,
        "threads": threads,
        "status": f"{percent}%"
    }

if __name__ == "__main__":
    print(json.dumps(check()))
