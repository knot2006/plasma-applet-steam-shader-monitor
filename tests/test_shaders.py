import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import mock_open, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_shaders", ROOT / "contents/scripts/check_shaders.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ShaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.steam = self.home / ".local/share/Steam"
        self.started_at = datetime(2026, 10, 26, 12, 0, 0).timestamp() + 0.5
        self.command = "123 /steam/fossilize_replay --num-threads 8 /steam/steamapps/shadercache/222/cache.foz\n"
        self.process = subprocess.CompletedProcess([], 0, self.command, "")
        self.patch(patch.dict(os.environ, {"HOME": str(self.home)}))
        self.run_process = self.patch(patch.object(helper.subprocess, "run", return_value=self.process))
        self.patch(patch.object(helper, "process_start_time", return_value=self.started_at))
        exists = os.path.exists
        self.patch(patch.object(helper.os.path, "exists", side_effect=lambda path: False if path == "/tmp/steam_shader_mock.json" else exists(path)))

    def patch(self, patcher):
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def write_steam(self, log, steam=None):
        steam = steam or self.steam
        (steam / "logs").mkdir(parents=True, exist_ok=True)
        (steam / "logs/shader_log.txt").write_text(log)
        (steam / "steamapps").mkdir(exist_ok=True)
        for app_id, title in (("111", "Old Game"), ("222", "Current Game")):
            (steam / "steamapps" / f"appmanifest_{app_id}.acf").write_text(f'"name" "{title}"\n')

    def test_current_progress_ignores_other_games(self):
        self.write_steam(
            "[2026-10-26 12:00:01] Still replaying 222 (42%, 42/100).\n"
            "[2026-10-26 12:00:02] Still replaying 111 (100%, 100/100).\n"
        )
        info = helper.check()
        self.assertEqual((info["app_id"], info["game"], info["percent"], info["counts"]),
                         ("222", "Current Game", 42, "42/100"))

    def test_stale_other_game_does_not_replace_process_id(self):
        self.write_steam("[2026-10-26 11:00:00] Still replaying 111 (100%, 100/100).\n")
        info = helper.check()
        self.assertEqual((info["app_id"], info["game"], info["percent"]), ("222", "Current Game", 0))
        self.assertEqual(info["counts"], "")

    def test_stale_same_game_does_not_report_previous_run(self):
        self.write_steam("[2026-10-26 11:59:59] Still replaying 222 (100%, 100/100).\n")
        self.assertEqual(helper.check()["percent"], 0)

    def test_timestamp_precision_and_optional_counts(self):
        self.write_steam("[2026-10-26 12:00:00] Still replaying 222 (7%).\n")
        info = helper.check()
        self.assertEqual((info["percent"], info["counts"]), (7, ""))

    def test_unreadable_process_start_does_not_trust_old_progress(self):
        self.write_steam("[2026-10-26 12:00:01] Still replaying 222 (100%, 100/100).\n")
        helper.process_start_time.return_value = None
        self.assertEqual(helper.check()["percent"], 0)

    def test_bad_timestamp_does_not_hide_valid_progress(self):
        self.write_steam(
            "[2026-10-26 12:00:01] Still replaying 222 (42%, 42/100).\n"
            "[invalid] Still replaying 222 (100%, 100/100).\n"
        )
        self.assertEqual(helper.check()["percent"], 42)

    def test_native_steam_roots(self):
        for relative in (".local/share/Steam", ".steam/debian-installation", ".steam/steam", ".steam/root"):
            with self.subTest(root=relative), tempfile.TemporaryDirectory() as home:
                steam = Path(home) / relative
                self.write_steam("[2026-10-26 12:00:01] Still replaying 222 (42%, 42/100).\n", steam)
                with patch.dict(os.environ, {"HOME": home}):
                    info = helper.check()
                self.assertEqual((info["game"], info["percent"]), ("Current Game", 42))

    def test_steam_root_symlink(self):
        steam = self.home / "custom install"
        self.write_steam("[2026-10-26 12:00:01] Still replaying 222 (42%, 42/100).\n", steam)
        (self.home / ".steam").mkdir()
        (self.home / ".steam/root").symlink_to(steam, target_is_directory=True)
        self.assertEqual(helper.check()["game"], "Current Game")

    def test_secondary_library_modern_and_legacy_locations(self):
        self.write_steam("")
        (self.steam / "steamapps/appmanifest_222.acf").unlink()
        library = self.home / "External Library"
        (library / "steamapps").mkdir(parents=True)
        (library / "steamapps/appmanifest_222.acf").write_text('"name" "External Game"\n')
        for folder in ("steamapps", "config"):
            with self.subTest(folder=folder):
                vdf = self.steam / folder / "libraryfolders.vdf"
                vdf.parent.mkdir(exist_ok=True)
                vdf.write_text(f'"libraryfolders"\n{{\n"1"\n{{\n"path" "{library}"\n}}\n}}\n')
                self.assertEqual(helper.check()["game"], "External Game")
                vdf.unlink()

    def test_idle_without_process(self):
        self.process.returncode = 1
        self.process.stdout = ""
        self.assertFalse(helper.check()["active"])

    def test_threads_and_id_come_from_same_process(self):
        self.process.stdout = "99 /tmp/fossilize_replay --num-threads 99\n" + self.command
        info = helper.check()
        self.assertEqual((info["app_id"], info["threads"]), ("222", 8))
        self.assertEqual(self.run_process.call_args.args[0],
                         ["pgrep", "-u", str(os.getuid()), "-af", "fossilize_replay"])

    def test_mock_simulation_still_works(self):
        data = {"active": True, "game": "Simulation", "percent": 65}
        with patch.object(helper.os.path, "exists", return_value=True), patch("builtins.open", mock_open(read_data=json.dumps(data))):
            self.assertEqual(helper.check(), data)


class ProcessStartTests(unittest.TestCase):
    def test_current_process_start_is_in_past(self):
        started_at = helper.process_start_time(os.getpid())
        self.assertIsNotNone(started_at)
        self.assertLessEqual(started_at, time.time())
        self.assertGreater(started_at, time.time() - 120)

    def test_missing_process_returns_none(self):
        self.assertIsNone(helper.process_start_time("not-a-pid"))

    def test_process_name_can_contain_parentheses(self):
        ticks = 123 * os.sysconf("SC_CLK_TCK")
        stat = "123 (a name ) with (parentheses)) " + " ".join(["S"] + ["0"] * 18 + [str(ticks)])
        with patch("builtins.open", side_effect=[mock_open(read_data=stat)(), mock_open(read_data="btime 1000\n")()]):
            self.assertEqual(helper.process_start_time("123"), 1123)


class CliTests(unittest.TestCase):
    @unittest.skipIf(Path("/tmp/steam_shader_mock.json").exists(), "global shader simulation is active")
    def test_helper_cli_with_native_root_and_live_process_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            steam = home / ".steam/debian-installation"
            (steam / "logs").mkdir(parents=True)
            (steam / "steamapps").mkdir()
            (steam / "steamapps/appmanifest_222.acf").write_text('"name" "Current Game"\n')
            binaries = home / "bin"
            binaries.mkdir()
            pgrep = binaries / "pgrep"
            pgrep.write_text(f'''#!{sys.executable}
import os
from datetime import datetime
from pathlib import Path
steam = Path.home() / ".steam/debian-installation"
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
(steam / "logs/shader_log.txt").write_text(f"[{{timestamp}}] Still replaying 222 (42%, 42/100).\\n")
print(f"{{os.getppid()}} fossilize_replay --num-threads 8 {{steam}}/steamapps/shadercache/222/cache.foz")
''')
            pgrep.chmod(0o755)
            env = dict(os.environ, HOME=str(home), PATH=str(binaries) + os.pathsep + os.environ["PATH"])
            result = subprocess.run([sys.executable, str(ROOT / "contents/scripts/check_shaders.py")],
                                    env=env, capture_output=True, text=True, timeout=5, check=True)
            info = json.loads(result.stdout)
            self.assertEqual((info["active"], info["app_id"], info["game"], info["percent"], info["threads"]),
                             (True, "222", "Current Game", 42, 8))


if __name__ == "__main__":
    unittest.main()
