from __future__ import annotations

import csv
import ctypes
import getpass
import io
import json
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


APP_NAME = "Nghia PC Toolkit"
APP_COMMAND = "pctool"
APP_VERSION = "0.2.1"

ESC = "\033["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def enable_ansi() -> None:
    if os.name != "nt":
        return

    os.system("")
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint32()

    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)


def rgb(value: tuple[int, int, int], background: bool = False) -> str:
    prefix = "48" if background else "38"
    return f"{ESC}{prefix};2;{value[0]};{value[1]};{value[2]}m"


def strip_ansi(value: str) -> str:
    return ANSI_RE.sub("", value)


def visible_len(value: str) -> int:
    return len(strip_ansi(value))


def pad(value: str, width: int) -> str:
    return value + (" " * max(0, width - visible_len(value)))


def shorten(value: str, width: int) -> str:
    plain = strip_ansi(value)
    if len(plain) <= width:
        return value
    if width <= 3:
        return plain[:width]
    return plain[: width - 3] + "..."


def clear() -> None:
    print(f"{ESC}2J{ESC}H", end="")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def human_bytes(value: int | float) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def safe_percent(used: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((used / total) * 100, 1)


def run_capture(command: list[str], timeout: int = 8) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (completed.stdout or completed.stderr or "").strip()
        return completed.returncode, output
    except Exception as exc:
        return 1, str(exc)


def run_powershell(script: str, timeout: int = 8) -> tuple[int, str]:
    return run_capture(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "$ErrorActionPreference='Stop'; " + script,
        ],
        timeout=timeout,
    )


@dataclass(frozen=True)
class Theme:
    name: str
    fg: tuple[int, int, int]
    muted: tuple[int, int, int]
    accent: tuple[int, int, int]
    accent_2: tuple[int, int, int]
    success: tuple[int, int, int]
    warning: tuple[int, int, int]
    danger: tuple[int, int, int]
    panel_alt: tuple[int, int, int]


THEMES: dict[str, Theme] = {
    "carbon": Theme(
        "carbon",
        fg=(230, 232, 236),
        muted=(139, 145, 155),
        accent=(86, 156, 214),
        accent_2=(78, 201, 176),
        success=(87, 199, 133),
        warning=(232, 192, 88),
        danger=(238, 98, 98),
        panel_alt=(35, 38, 43),
    ),
    "graphite": Theme(
        "graphite",
        fg=(238, 238, 232),
        muted=(150, 150, 142),
        accent=(220, 139, 87),
        accent_2=(127, 201, 214),
        success=(126, 211, 139),
        warning=(239, 200, 113),
        danger=(244, 111, 111),
        panel_alt=(42, 40, 37),
    ),
    "matrix": Theme(
        "matrix",
        fg=(219, 245, 225),
        muted=(114, 157, 127),
        accent=(79, 225, 129),
        accent_2=(123, 216, 248),
        success=(100, 234, 156),
        warning=(235, 209, 107),
        danger=(255, 118, 118),
        panel_alt=(20, 38, 27),
    ),
}


@dataclass
class TempScan:
    roots: list[Path]
    files: int
    dirs: int
    bytes_total: int
    errors: int


class PCToolkit:
    def __init__(self) -> None:
        self.theme = THEMES["carbon"]
        self.history: list[str] = []
        self.running = True
        self.interactive = sys.stdin.isatty() and sys.stdout.isatty()
        self.last_temp_scan: TempScan | None = None
        self.commands: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "?": self.cmd_help,
            "dashboard": self.cmd_dashboard,
            "status": self.cmd_dashboard,
            "system": self.cmd_system,
            "sys": self.cmd_system,
            "disk": self.cmd_disk,
            "disks": self.cmd_disk,
            "network": self.cmd_network,
            "net": self.cmd_network,
            "netword": self.cmd_network,
            "ports": self.cmd_ports,
            "port": self.cmd_ports,
            "processes": self.cmd_processes,
            "ps": self.cmd_processes,
            "temp": self.cmd_temp,
            "cleanup": self.cmd_cleanup,
            "startup": self.cmd_startup,
            "path": self.cmd_path,
            "report": self.cmd_report,
            "theme": self.cmd_theme,
            "history": self.cmd_history,
            "about": self.cmd_about,
            "clear": self.cmd_clear,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }

    def color(self, value: str, key: str = "fg", *, bold: bool = False, bg: str | None = None) -> str:
        prefix = rgb(getattr(self.theme, key))
        if bg:
            prefix += rgb(getattr(self.theme, bg), background=True)
        if bold:
            prefix += BOLD
        return f"{prefix}{value}{RESET}"

    def panel_width(self) -> int:
        size = shutil.get_terminal_size((112, 32))
        return max(76, min(122, size.columns - 4))

    def line(self, char: str = "-") -> str:
        return char * self.panel_width()

    def write_panel(self, title: str, rows: list[str], footer: str | None = None) -> None:
        width = self.panel_width()
        border = self.color("+" + ("-" * (width - 2)) + "+", "muted")
        print(border)
        print(
            self.color("|", "muted")
            + pad(self.color(f" {title} ", "accent", bold=True), width - 2)
            + self.color("|", "muted")
        )
        print(self.color("+" + ("-" * (width - 2)) + "+", "muted"))

        for row in rows:
            content = shorten(f" {row}", width - 2)
            print(self.color("|", "muted") + pad(content, width - 2) + self.color("|", "muted"))

        if footer:
            print(self.color("+" + ("-" * (width - 2)) + "+", "muted"))
            print(self.color("|", "muted") + pad(f" {footer}", width - 2) + self.color("|", "muted"))

        print(border)

    def boot(self) -> None:
        self.render_screen("dashboard", animate=True)
        self.cmd_dashboard([])
        print()
        print(
            self.color(APP_COMMAND, "accent", bold=True)
            + self.color(" ready. ", "muted")
            + self.color("Type ", "muted")
            + self.color("help", "accent_2", bold=True)
            + self.color(" to see tools.", "muted")
        )
        print()

    def render_screen(self, label: str | None = None, *, animate: bool = False) -> None:
        clear()
        self.render_banner()
        if label:
            self.render_context(label)
        if animate:
            self.scan_effect(label or "ready")

    def render_context(self, label: str) -> None:
        width = self.panel_width()
        timestamp = datetime.now().strftime("%H:%M:%S")
        machine = socket.gethostname()
        left = self.color(" command ", "muted") + self.color(shorten(label, 54), "accent_2", bold=True)
        right = self.color(f"{machine} / {timestamp}", "muted")
        gap = " " * max(1, width - visible_len(left) - visible_len(right))
        print(left + gap + right)
        print(self.color(self.line("."), "muted"))
        print()

    def scan_effect(self, label: str) -> None:
        if not self.interactive:
            return
        width = min(self.panel_width(), 88)
        frames = ("[=       ]", "[===     ]", "[=====   ]", "[======= ]", "[========]")
        text = shorten(label, 42)
        for frame in frames:
            line = self.color(frame, "accent_2", bold=True) + self.color(f" loading {text}", "muted")
            print("\r" + pad(line, width), end="", flush=True)
            time.sleep(0.035)
        print("\r" + (" " * width) + "\r", end="", flush=True)
        print()

    def render_banner(self) -> None:
        art = [
            r" _   _       _     _        ____   ____   _____           _ _    _ _",
            r"| \ | | __ _| |__ (_) __ _ |  _ \ / ___| |_   _|__   ___ | | | _(_) |_",
            r"|  \| |/ _` | '_ \| |/ _` || |_) | |       | |/ _ \ / _ \| | |/ / | __|",
            r"| |\  | (_| | | | | | (_| ||  __/| |___    | | (_) | (_) | |   <| | |_",
            r"|_| \_|\__, |_| |_|_|\__, ||_|    \____|   |_|\___/ \___/|_|_|\_\_|\__|",
            r"       |___/         |___/",
        ]
        print(self.color(self.line("."), "muted"))
        for row in art:
            print(self.color(row, "accent", bold=True))
        print(self.color(f"{APP_NAME} v{APP_VERSION} - Windows diagnostics and maintenance CLI", "muted"))
        print(self.color(self.line("."), "muted"))
        print()

    def prompt(self) -> str:
        machine = socket.gethostname()
        return (
            self.color(APP_COMMAND, "accent", bold=True)
            + self.color(":", "muted")
            + self.color(machine, "accent_2")
            + self.color(" > ", "fg", bold=True)
        )

    def loop(self) -> None:
        self.boot()

        while self.running:
            try:
                raw = input(self.prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.cmd_exit([])
                break

            if not raw:
                continue

            self.history.append(raw)
            self.dispatch(raw)

    def dispatch(self, raw: str) -> None:
        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            self.render_screen("parse error", animate=True)
            self.error(f"Cannot parse command: {exc}")
            return

        command = parts[0].lower()
        args = parts[1:]
        handler = self.commands.get(command)

        if command in ("exit", "quit"):
            handler(args) if handler else self.cmd_exit([])
            return

        if command == "clear":
            self.cmd_clear(args)
            return

        if command == "theme" and args:
            handler(args) if handler else self.error(f"Unknown command: {command}")
            return

        self.render_screen(raw, animate=True)

        if handler is None:
            self.error(f"Unknown command: {command}")
            return

        handler(args)

    def command_row(self, command: str, detail: str) -> str:
        return f"{self.color(command.ljust(20), 'accent_2', bold=True)} {self.color(detail, 'fg')}"

    def cmd_help(self, _: list[str]) -> None:
        rows = [
            self.command_row("dashboard", "Quick health summary for this PC"),
            self.command_row("system", "OS, CPU, RAM, user, admin state"),
            self.command_row("disk", "Drive usage and free-space warnings"),
            self.command_row("network", "Local IP, DNS, gateway-style connectivity checks"),
            self.command_row("ports host port", "Test TCP connectivity, example: ports github.com 443"),
            self.command_row("processes [n]", "Show top running processes by memory"),
            self.command_row("temp", "Scan safe temp folders and estimate cleanable size"),
            self.command_row("cleanup", "Dry-run cleanup report"),
            self.command_row("cleanup --apply", "Delete temp files after explicit confirmation"),
            self.command_row("startup", "List user startup-folder items"),
            self.command_row("path", "Show PATH entries"),
            self.command_row("report", "Write a desktop diagnostic report"),
            self.command_row("theme", "Switch theme: carbon, graphite, matrix"),
            self.command_row("clear / exit", "Redraw screen or close the tool"),
        ]
        self.write_panel("Tools", rows, footer="Safe by default: cleanup does not delete unless you use --apply and confirm.")

    def cmd_dashboard(self, _: list[str]) -> None:
        local_ip = self.local_ip()
        memory = self.memory_info()
        disks = self.disk_info()
        temp_scan = self.scan_temp(max_items=35000)
        self.last_temp_scan = temp_scan

        disk_warning = "ok"
        if disks:
            worst = max(disks, key=lambda item: item["used_percent"])
            disk_warning = f"{worst['drive']} {worst['used_percent']:.1f}% used"

        rows = [
            self.kv("Computer", socket.gethostname()),
            self.kv("User", getpass.getuser()),
            self.kv("OS", platform.platform()),
            self.kv("Admin", "yes" if self.is_admin() else "no"),
            self.kv("Memory", self.memory_summary(memory)),
            self.kv("Disk", disk_warning),
            self.kv("Network", local_ip),
            self.kv("Temp files", f"{human_bytes(temp_scan.bytes_total)} across {temp_scan.files} files"),
        ]
        self.write_panel("Dashboard", rows, footer="Run: system | disk | network | temp | report")

    def kv(self, key: str, value: str) -> str:
        display = shorten(value, 92)
        if ESC in display:
            return f"{self.color(key.ljust(14), 'muted')} {display}"
        return f"{self.color(key.ljust(14), 'muted')} {self.color(display, 'fg')}"

    def memory_summary(self, memory: dict[str, int] | None) -> str:
        if not memory:
            return "unavailable"
        used = memory["total"] - memory["free"]
        return f"{human_bytes(used)} / {human_bytes(memory['total'])} used ({safe_percent(used, memory['total']):.1f}%)"

    def is_admin(self) -> bool:
        if os.name != "nt":
            return os.geteuid() == 0 if hasattr(os, "geteuid") else False
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def memory_info(self) -> dict[str, int] | None:
        if os.name == "nt":
            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {"total": int(status.ullTotalPhys), "free": int(status.ullAvailPhys)}

        code, output = run_powershell(
            "$m=Get-CimInstance Win32_OperatingSystem; "
            "@{total=[int64]$m.TotalVisibleMemorySize*1KB; free=[int64]$m.FreePhysicalMemory*1KB} | ConvertTo-Json -Compress"
        )
        if code != 0:
            return None
        try:
            data = json.loads(output)
            return {"total": int(data["total"]), "free": int(data["free"])}
        except Exception:
            return None

    def cpu_name(self) -> str:
        code, output = run_powershell("(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)")
        if code == 0 and output:
            candidate = " ".join(output.split())
            if "Get-CimInstance" not in candidate and "Access denied" not in candidate:
                return candidate
        return os.environ.get("PROCESSOR_IDENTIFIER", platform.processor() or "unknown")

    def cmd_system(self, _: list[str]) -> None:
        memory = self.memory_info()
        rows = [
            self.kv("Computer", socket.gethostname()),
            self.kv("User", getpass.getuser()),
            self.kv("Admin", "yes" if self.is_admin() else "no"),
            self.kv("OS", platform.platform()),
            self.kv("Arch", platform.machine() or "unknown"),
            self.kv("CPU", self.cpu_name()),
            self.kv("RAM", self.memory_summary(memory)),
            self.kv("Shell", os.environ.get("COMSPEC", "unknown")),
            self.kv("Install dir", str(Path.cwd())),
        ]
        self.write_panel("System", rows)

    def disk_info(self) -> list[dict[str, int | float | str]]:
        drives: list[dict[str, int | float | str]] = []
        if os.name == "nt":
            candidates = [Path(f"{letter}:\\") for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
        else:
            candidates = [Path("/")]

        for drive in candidates:
            if not drive.exists():
                continue
            try:
                usage = shutil.disk_usage(drive)
            except OSError:
                continue
            used = usage.total - usage.free
            drives.append(
                {
                    "drive": str(drive),
                    "total": usage.total,
                    "used": used,
                    "free": usage.free,
                    "used_percent": safe_percent(used, usage.total),
                }
            )
        return drives

    def cmd_disk(self, _: list[str]) -> None:
        rows: list[str] = []
        for item in self.disk_info():
            pct = float(item["used_percent"])
            key = "danger" if pct >= 90 else "warning" if pct >= 80 else "success"
            rows.append(
                f"{self.color(str(item['drive']).ljust(8), 'accent_2', bold=True)} "
                f"{self.color(f'{pct:5.1f}% used', key)} "
                f"{self.color('free', 'muted')} {human_bytes(int(item['free']))} "
                f"{self.color('total', 'muted')} {human_bytes(int(item['total']))}"
            )
        if not rows:
            rows = ["No readable drives found."]
        self.write_panel("Disk Usage", rows)

    def local_ip(self) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.2)
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
            sock.close()
            return address
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "unavailable"

    def ping_host(self, host: str) -> tuple[bool, str]:
        if os.name == "nt":
            command = ["ping", "-n", "1", "-w", "1400", host]
        else:
            command = ["ping", "-c", "1", "-W", "2", host]
        code, output = run_capture(command, timeout=4)
        if code == 0:
            match = re.search(r"time[=<]\s*([0-9]+)ms", output, re.IGNORECASE)
            return True, f"ok {match.group(1)}ms" if match else "ok"
        return False, "failed"

    def cmd_network(self, _: list[str]) -> None:
        dns_ok = False
        dns_message = "failed"
        try:
            socket.gethostbyname("github.com")
            dns_ok = True
            dns_message = "ok"
        except Exception as exc:
            dns_message = str(exc)

        cloudflare_ok, cloudflare_msg = self.ping_host("1.1.1.1")
        google_ok, google_msg = self.ping_host("8.8.8.8")
        github_ok = self.tcp_check("github.com", 443, timeout=3)

        rows = [
            self.kv("Hostname", socket.gethostname()),
            self.kv("Local IP", self.local_ip()),
            self.kv("DNS", self.status_text(dns_ok, dns_message)),
            self.kv("Ping 1.1.1.1", self.status_text(cloudflare_ok, cloudflare_msg)),
            self.kv("Ping 8.8.8.8", self.status_text(google_ok, google_msg)),
            self.kv("GitHub 443", self.status_text(github_ok, "tcp ok" if github_ok else "tcp failed")),
        ]
        self.write_panel("Network", rows, footer="If ping fails but GitHub 443 is ok, ICMP may be blocked by the network.")

    def status_text(self, ok: bool, value: str) -> str:
        return self.color(value, "success" if ok else "danger", bold=ok)

    def tcp_check(self, host: str, port: int, timeout: int = 4) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def cmd_ports(self, args: list[str]) -> None:
        if len(args) < 2:
            self.error("Usage: ports <host> <port> [port...]")
            return

        host = args[0]
        rows: list[str] = []
        for raw_port in args[1:]:
            try:
                port = int(raw_port)
            except ValueError:
                rows.append(f"{self.color(raw_port.ljust(8), 'danger')} invalid port")
                continue

            ok = self.tcp_check(host, port)
            rows.append(
                f"{self.color((str(port) + '/tcp').ljust(10), 'accent_2')} "
                + self.status_text(ok, "open/reachable" if ok else "closed/blocked")
            )
        self.write_panel(f"Port Check: {host}", rows)

    def cmd_processes(self, args: list[str]) -> None:
        limit = 12
        if args:
            try:
                limit = max(1, min(50, int(args[0])))
            except ValueError:
                self.error("Usage: processes [number]")
                return

        if os.name != "nt":
            self.write_panel("Processes", ["Process listing is currently optimized for Windows."])
            return

        code, output = run_capture(["tasklist", "/FO", "CSV", "/NH"], timeout=10)
        processes = []
        if code == 0:
            for row in csv.reader(io.StringIO(output)):
                if len(row) < 5:
                    continue
                mem_raw = row[4].replace(",", "").replace("K", "").strip()
                try:
                    mem_kb = int(mem_raw)
                except ValueError:
                    mem_kb = 0
                processes.append((row[0], row[1], mem_kb))
        else:
            ps_code, ps_output = run_powershell(
                "Get-Process | Sort-Object WorkingSet64 -Descending | "
                f"Select-Object -First {limit} Name,Id,WorkingSet64 | ConvertTo-Csv -NoTypeInformation",
                timeout=10,
            )
            if ps_code != 0:
                self.error(output or ps_output or "process listing failed")
                return
            reader = csv.DictReader(io.StringIO(ps_output))
            for row in reader:
                try:
                    mem_kb = int(row.get("WorkingSet64", "0")) // 1024
                except ValueError:
                    mem_kb = 0
                processes.append((row.get("Name", "unknown"), row.get("Id", "?"), mem_kb))

        processes.sort(key=lambda item: item[2], reverse=True)
        rows = [
            f"{self.color(name[:32].ljust(34), 'accent_2')} "
            f"{self.color(('pid ' + pid).ljust(12), 'muted')} "
            f"{human_bytes(mem_kb * 1024)}"
            for name, pid, mem_kb in processes[:limit]
        ]
        self.write_panel("Top Processes", rows, footer="Sorted by memory.")

    def temp_roots(self) -> list[Path]:
        roots: list[Path] = []
        for value in (tempfile.gettempdir(), os.environ.get("TEMP"), os.environ.get("TMP")):
            if value:
                path = Path(value)
                if path.exists() and path not in roots:
                    roots.append(path)
        windows_temp = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Temp"
        if windows_temp.exists() and windows_temp not in roots:
            roots.append(windows_temp)
        return roots

    def scan_temp(self, max_items: int = 120000) -> TempScan:
        roots = self.temp_roots()
        files = 0
        dirs = 0
        bytes_total = 0
        errors = 0

        for root in roots:
            for current, dirnames, filenames in os.walk(root, topdown=True):
                dirs += len(dirnames)
                for filename in filenames:
                    if files >= max_items:
                        return TempScan(roots, files, dirs, bytes_total, errors)
                    path = Path(current) / filename
                    try:
                        bytes_total += path.stat().st_size
                        files += 1
                    except OSError:
                        errors += 1
        return TempScan(roots, files, dirs, bytes_total, errors)

    def cmd_temp(self, _: list[str]) -> None:
        scan = self.scan_temp()
        self.last_temp_scan = scan
        rows = [
            self.kv("Folders", ", ".join(str(root) for root in scan.roots) or "none"),
            self.kv("Files", str(scan.files)),
            self.kv("Subfolders", str(scan.dirs)),
            self.kv("Estimated size", human_bytes(scan.bytes_total)),
            self.kv("Access errors", str(scan.errors)),
        ]
        self.write_panel("Temp Scan", rows, footer="Run cleanup for dry-run, or cleanup --apply to delete after confirmation.")

    def cmd_cleanup(self, args: list[str]) -> None:
        apply = "--apply" in args or "-y" in args
        scan = self.scan_temp()
        self.last_temp_scan = scan

        if not apply:
            rows = [
                self.kv("Mode", "dry-run"),
                self.kv("Targets", ", ".join(str(root) for root in scan.roots)),
                self.kv("Files", str(scan.files)),
                self.kv("Estimated size", human_bytes(scan.bytes_total)),
                self.kv("Errors", str(scan.errors)),
            ]
            self.write_panel("Cleanup Preview", rows, footer="Nothing was deleted. Use cleanup --apply and type DELETE to confirm.")
            return

        print(self.color("This will delete files inside temp folders only.", "warning", bold=True))
        confirm = input(self.color("Type DELETE to continue: ", "danger", bold=True)).strip()
        if confirm != "DELETE":
            print(self.color("Cleanup cancelled.", "muted"))
            return

        deleted_files = 0
        deleted_bytes = 0
        errors = 0
        for root in scan.roots:
            for current, _, filenames in os.walk(root, topdown=False):
                for filename in filenames:
                    path = Path(current) / filename
                    try:
                        size = path.stat().st_size
                        path.unlink()
                        deleted_files += 1
                        deleted_bytes += size
                    except OSError:
                        errors += 1
                try:
                    if Path(current) != root:
                        Path(current).rmdir()
                except OSError:
                    pass

        rows = [
            self.kv("Deleted files", str(deleted_files)),
            self.kv("Freed", human_bytes(deleted_bytes)),
            self.kv("Skipped/errors", str(errors)),
        ]
        self.write_panel("Cleanup Complete", rows)

    def cmd_startup(self, _: list[str]) -> None:
        startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if not startup.exists():
            self.write_panel("Startup", ["Startup folder not found."])
            return
        items = list(startup.iterdir())
        rows = [self.color(item.name, "accent_2") for item in items[:40]]
        if not rows:
            rows = ["No user startup-folder items."]
        self.write_panel("Startup Folder", rows, footer=str(startup))

    def cmd_path(self, _: list[str]) -> None:
        entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
        rows = [f"{index:02d}. {entry}" for index, entry in enumerate(entries[:40], start=1)]
        if len(entries) > 40:
            rows.append(f"... {len(entries) - 40} more")
        self.write_panel("PATH", rows or ["PATH is empty."])

    def cmd_report(self, _: list[str]) -> None:
        desktop = Path.home() / "Desktop"
        target_dir = desktop if desktop.exists() else Path.cwd()
        target = target_dir / f"pctool-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"

        memory = self.memory_info()
        temp_scan = self.scan_temp()
        lines = [
            f"{APP_NAME} v{APP_VERSION}",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "[System]",
            f"Computer: {socket.gethostname()}",
            f"User: {getpass.getuser()}",
            f"Admin: {'yes' if self.is_admin() else 'no'}",
            f"OS: {platform.platform()}",
            f"CPU: {self.cpu_name()}",
            f"RAM: {self.memory_summary(memory)}",
            "",
            "[Disks]",
        ]
        for disk in self.disk_info():
            lines.append(
                f"{disk['drive']} used={disk['used_percent']:.1f}% "
                f"free={human_bytes(int(disk['free']))} total={human_bytes(int(disk['total']))}"
            )
        lines.extend(
            [
                "",
                "[Network]",
                f"Local IP: {self.local_ip()}",
                f"GitHub 443: {'ok' if self.tcp_check('github.com', 443) else 'failed'}",
                "",
                "[Temp]",
                f"Roots: {', '.join(str(root) for root in temp_scan.roots)}",
                f"Files: {temp_scan.files}",
                f"Estimated size: {human_bytes(temp_scan.bytes_total)}",
                f"Errors: {temp_scan.errors}",
            ]
        )
        last_error = ""
        candidates = [
            target,
            Path.cwd() / target.name,
            Path(tempfile.gettempdir()) / target.name,
        ]
        for candidate in candidates:
            try:
                candidate.write_text("\n".join(lines), encoding="utf-8")
                self.write_panel("Report", [self.kv("Saved", str(candidate))])
                return
            except OSError as exc:
                last_error = str(exc)
        self.error(f"Could not write report: {last_error}")

    def cmd_theme(self, args: list[str]) -> None:
        if not args:
            rows = []
            for name in THEMES:
                marker = "*" if name == self.theme.name else " "
                rows.append(
                    f"{self.color(marker, 'accent')} "
                    + self.color(name.ljust(10), "accent_2", bold=name == self.theme.name)
                    + self.color(f"theme {name}", "muted")
                )
            self.write_panel("Themes", rows, footer="Use: theme carbon | theme graphite | theme matrix")
            return

        name = args[0].lower()
        next_theme = THEMES.get(name)
        if not next_theme:
            self.render_screen(f"theme {name}", animate=True)
            self.error(f"Unknown theme: {name}")
            return
        self.theme = next_theme
        self.render_screen(f"theme {name}", animate=True)
        self.write_panel("Theme", [self.kv("Active", name)])

    def cmd_history(self, _: list[str]) -> None:
        rows = [f"{index:02d}. {item}" for index, item in enumerate(self.history[-14:], start=1)]
        self.write_panel("History", rows or ["No history yet."])

    def cmd_about(self, _: list[str]) -> None:
        rows = [
            f"{APP_NAME} is a local Windows diagnostics and maintenance CLI.",
            "It runs as a bundled executable and uses safe read-only checks by default.",
            "Cleanup only touches temp folders and requires explicit confirmation.",
        ]
        self.write_panel("About", rows)

    def cmd_clear(self, _: list[str]) -> None:
        self.boot()

    def cmd_exit(self, _: list[str]) -> None:
        self.running = False
        print(self.color(f"Closed {APP_NAME}.", "muted"))

    def error(self, message: str) -> None:
        self.write_panel("Error", [self.color(message, "danger", bold=True)], footer="Run help to list available commands.")


def main() -> int:
    configure_stdio()
    enable_ansi()
    app = PCToolkit()
    app.loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
