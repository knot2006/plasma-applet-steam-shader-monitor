#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import json
from datetime import datetime


def process_start_time(pid):
    try:
        with open(f"/proc/{pid}/stat") as f:
            start_ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/stat") as f:
            boot_time = next(int(line.split()[1]) for line in f if line.startswith("btime "))
        return boot_time + start_ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError, StopIteration):
        return None

def check():
    mock_file = "/tmp/steam_shader_mock.json"
    if os.path.exists(mock_file):
        try:
            with open(mock_file) as mf:
                return json.load(mf)
        except Exception:
            pass

    p = subprocess.run(["pgrep", "-u", str(os.getuid()), "-af", "fossilize_replay"], capture_output=True, text=True)
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

    command = next((line for line in p.stdout.splitlines() if re.search(r"shadercache/\d+/", line)), "")
    started_at = process_start_time(command.split()[0]) if command else None
    threads = 0
    tm = re.search(r"--num-threads\s+(\d+)", command)
    if tm:
        threads = int(tm.group(1))

    m_cmd = re.search(r"shadercache/(\d+)/", command)
    cmd_appid = m_cmd.group(1) if m_cmd else ""

    roots = [os.path.expanduser(path) for path in (
        "~/.steam/root", "~/.steam/steam", "~/.local/share/Steam", "~/.steam/debian-installation"
    )]
    steam_root = next((path for path in roots if os.path.isdir(path)), roots[2])
    log_file = os.path.join(steam_root, "logs", "shader_log.txt")
    app_id = cmd_appid
    percent = 0
    counts = ""

    if os.path.exists(log_file):
        try:
            with open(log_file, "rb") as f:
                f.seek(max(0, os.path.getsize(log_file) - 16384))
                content = f.read().decode("utf-8", "ignore")
                matches = re.findall(r"\[([^\]]+)\][^\n]*?replaying (\d+)\s*\((\d+)%(?:,\s*([^)]+))?\)", content)
                for timestamp, logged_appid, pct_str, logged_counts in reversed(matches):
                    if logged_appid != app_id or started_at is None:
                        continue
                    try:
                        logged_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").timestamp()
                    except ValueError:
                        continue
                    # Steam timestamps have second precision; reject progress from older runs.
                    if logged_at >= int(started_at):
                        percent = int(pct_str)
                        counts = logged_counts
                        # Steam's percentage can disagree with the reported replay counts.
                        count_match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", counts)
                        if count_match:
                            completed, total = map(int, count_match.groups())
                            if total > 0:
                                percent = min(100, completed * 100 // total)
                        break
        except Exception:
            pass

    game_title = app_id
    library_paths = [steam_root]
    lib_vdf = next((os.path.join(steam_root, folder, "libraryfolders.vdf")
                    for folder in ("steamapps", "config")
                    if os.path.isfile(os.path.join(steam_root, folder, "libraryfolders.vdf"))), "")
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
