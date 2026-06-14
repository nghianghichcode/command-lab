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

# Windows arrow-key reading
try:
    import msvcrt as _msvcrt
    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False


APP_NAME = "Nghia PC Toolkit"
APP_COMMAND = "pctool"
APP_VERSION = "0.4.0"

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
    return len(strip_ansi(value).replace("\r", " ").replace("\n", " "))


def pad(value: str, width: int) -> str:
    return value + (" " * max(0, width - visible_len(value)))


def shorten(value: str, width: int) -> str:
    value = value.replace("\r", " ").replace("\n", " ")
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


@dataclass(frozen=True)
class AppEntry:
    name: str
    path: Path
    kind: str


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
            "wifi": self.cmd_wifi,
            "apps": self.cmd_apps,
            "app": self.cmd_apps,
            "open": self.cmd_open,
            "launch": self.cmd_open,
            "processes": self.cmd_processes,
            "ps": self.cmd_processes,
            "temp": self.cmd_temp,
            "junk": self.cmd_temp,
            "clean": self.cmd_cleanup,
            "cleanup": self.cmd_cleanup,
            "recycle": self.cmd_recycle,
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
        colors = ("accent", "accent_2", "success", "warning", "accent")
        text = shorten(label, 42)
        for frame, color in zip(frames, colors):
            line = self.color(frame, color, bold=True) + self.color(f" loading {text}", "muted")
            print("\r" + pad(line, width), end="", flush=True)
            time.sleep(0.035)
        print("\r" + (" " * width) + "\r", end="", flush=True)
        print()

    def render_banner(self) -> None:
        art = [
            r" _   _  ____ _   _ ___    _       ____   ____",
            r"| \ | |/ ___| | | |_ _|  / \     |  _ \ / ___|",
            r"|  \| | |  _| |_| || |  / _ \    | |_) | |",
            r"| |\  | |_| |  _  || | / ___ \   |  __/| |___",
            r"|_| \_|\____|_| |_|___/_/   \_\  |_|    \____|",
            r"                 T O O L K I T",
        ]
        print(self.color(self.line("."), "muted"))
        colors = ("accent", "accent_2", "success", "accent_2", "accent", "warning")
        for index, row in enumerate(art):
            print(self.color(row, colors[index % len(colors)], bold=True))
        print(self.color(":: NGHIA PC TOOLKIT ::", "fg", bold=True))
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

    # ------------------------------------------------------------------ #
    # Interactive arrow-key menu                                           #
    # ------------------------------------------------------------------ #
    MENU_ITEMS: list[tuple[str, str]] = [
        ("Dashboard",   "dashboard"),
        ("System Info", "system"),
        ("Disk Usage",  "disk"),
        ("Network",     "network"),
        ("Wi-Fi",       "wifi"),
        ("Apps",        "apps"),
        ("Processes",   "processes"),
        ("Junk Scan",   "temp"),
        ("Cleanup",     "cleanup"),
        ("Startup",     "startup"),
        ("Report",      "report"),
        ("Theme",       "theme"),
        ("History",     "history"),
        ("Help",        "help"),
        ("Exit",        "exit"),
    ]

    def _read_key(self) -> str:
        """Read a single keypress. Returns 'up', 'down', 'enter', 'esc', or the char."""
        if _HAS_MSVCRT:
            ch = _msvcrt.getwch()
            if ch in ("\xe0", "\x00"):  # special key prefix on Windows
                ch2 = _msvcrt.getwch()
                if ch2 == "H":
                    return "up"
                if ch2 == "P":
                    return "down"
                return "other"
            if ch == "\r":
                return "enter"
            if ch == "\x1b":
                return "esc"
            if ch == "\x03":  # Ctrl-C
                raise KeyboardInterrupt
            return ch
        # Fallback: just read a line
        try:
            line = input().strip()
        except EOFError:
            raise KeyboardInterrupt
        return line if line else "enter"

    def _render_menu(self, selected: int) -> None:
        """Render the interactive menu in place."""
        width = self.panel_width()
        items = self.MENU_ITEMS
        n = len(items)
        half = n // 2 + n % 2  # left column count
        col_w = (width - 6) // 2

        # Header
        border_top = self.color("┌" + "─" * (width - 2) + "┐", "muted")
        header_text = " " + self.color("MENU", "accent", bold=True) + \
            self.color("  ↑↓ Navigate   Enter Select   ESC Text Mode", "muted")
        header_line = (
            self.color("│", "muted")
            + pad(header_text, width - 2)
            + self.color("│", "muted")
        )
        divider = self.color("├" + "─" * (width - 2) + "┤", "muted")
        print(border_top)
        print(header_line)
        print(divider)

        # Two-column layout
        for row in range(half):
            left_idx = row
            right_idx = row + half
            line = self.color("│", "muted") + " "
            for idx in (left_idx, right_idx):
                if idx >= n:
                    line += " " * (col_w + 2)
                    continue
                label, _ = items[idx]
                if idx == selected:
                    cell = (
                        self.color(" ► ", "accent", bold=True)
                        + self.color(pad(label, col_w - 3), "fg", bold=True)
                    )
                else:
                    cell = self.color("   " + pad(label, col_w - 3), "muted")
                line += pad(cell, col_w) + "  "
            line = line.rstrip()
            line += self.color("│", "muted")
            print(line)

        print(self.color("└" + "─" * (width - 2) + "┘", "muted"))

    def _count_menu_lines(self) -> int:
        n = len(self.MENU_ITEMS)
        half = n // 2 + n % 2
        return half + 3  # top border + header + divider + rows + bottom border

    def interactive_menu(self) -> str | None:
        """
        Show an interactive arrow-key menu.
        Returns the selected command string, or None if user pressed ESC.
        """
        if not self.interactive or not _HAS_MSVCRT:
            # Fallback: just show the menu as text and ask for number
            print()
            for i, (label, _) in enumerate(self.MENU_ITEMS, 1):
                print(f"  {self.color(str(i).rjust(2), 'accent_2')}. {self.color(label, 'fg')}")
            print()
            try:
                raw = input(self.prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                return "exit"
            # Allow number selection
            if raw.isdigit():
                n = int(raw) - 1
                if 0 <= n < len(self.MENU_ITEMS):
                    return self.MENU_ITEMS[n][1]
            return raw if raw else None

        selected = 0
        total = len(self.MENU_ITEMS)
        menu_lines = self._count_menu_lines()

        # Hide cursor
        print("\033[?25l", end="", flush=True)
        try:
            self._render_menu(selected)
            while True:
                key = self._read_key()
                if key == "up":
                    selected = (selected - 1) % total
                elif key == "down":
                    selected = (selected + 1) % total
                elif key == "enter":
                    cmd = self.MENU_ITEMS[selected][1]
                    # Move cursor up to overwrite menu
                    print(f"\033[{menu_lines}A", end="", flush=True)
                    print(f"\033[J", end="", flush=True)
                    return cmd
                elif key == "esc":
                    print(f"\033[{menu_lines}A", end="", flush=True)
                    print(f"\033[J", end="", flush=True)
                    return None
                else:
                    # Any other char: treat as start of a typed command, rebuild
                    print(f"\033[{menu_lines}A", end="", flush=True)
                    print(f"\033[J", end="", flush=True)
                    # Let the user type a command (pre-seeded with this char)
                    try:
                        rest = input(self.prompt() + key).strip()
                        return key + rest
                    except (EOFError, KeyboardInterrupt):
                        return "exit"
                # Re-render menu in place
                print(f"\033[{menu_lines}A", end="", flush=True)
                self._render_menu(selected)
        finally:
            # Restore cursor
            print("\033[?25h", end="", flush=True)

    def loop(self) -> None:
        self.boot()

        while self.running:
            try:
                print()
                result = self.interactive_menu()
            except KeyboardInterrupt:
                print()
                self.cmd_exit([])
                break

            if result is None:
                # ESC pressed -> text input mode
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
            else:
                raw = result.strip()
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
            self.command_row("wifi", "Wi-Fi status and saved profile names"),
            self.command_row("wifi settings", "Open Windows Wi-Fi settings"),
            self.command_row("ports host port", "Test TCP connectivity, example: ports github.com 443"),
            self.command_row("apps [name]", "Search installed Start Menu apps"),
            self.command_row("open <app>", "Open an installed app, example: open chrome"),
            self.command_row("processes [n]", "Show top running processes by memory"),
            self.command_row("temp / junk", "Scan temp and browser cache folders"),
            self.command_row("cleanup", "Dry-run cleanup report"),
            self.command_row("cleanup --apply", "Delete temp/cache files after confirmation"),
            self.command_row("recycle --empty", "Empty Recycle Bin after confirmation"),
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
            self.kv("Junk files", f"{human_bytes(temp_scan.bytes_total)} across {temp_scan.files} files"),
        ]
        self.write_panel("Dashboard", rows, footer="Run: system | disk | network | wifi | apps | cleanup | report")

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

    def wifi_interfaces(self) -> dict[str, str]:
        code, output = run_capture(["netsh", "wlan", "show", "interfaces"], timeout=8)
        if code != 0 or not output:
            return {"status": " ".join((output or "Wi-Fi command unavailable").split())}

        wanted = {
            "name": "Name",
            "state": "State",
            "ssid": "SSID",
            "signal": "Signal",
            "radio type": "Radio",
            "authentication": "Auth",
            "channel": "Channel",
            "receive rate (mbps)": "Rx",
            "transmit rate (mbps)": "Tx",
        }
        result: dict[str, str] = {}
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key in wanted and value:
                result[wanted[key]] = value
        return result or {"status": "No active Wi-Fi interface found"}

    def wifi_profiles(self) -> tuple[list[str], str]:
        code, output = run_capture(["netsh", "wlan", "show", "profiles"], timeout=8)
        if code != 0:
            return [], output or "Could not read Wi-Fi profiles"

        profiles: list[str] = []
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            name = value.strip()
            if name and "profile" in key and "profiles on interface" not in key:
                profiles.append(name)
        return sorted(set(profiles), key=str.lower), ""

    def cmd_wifi(self, args: list[str]) -> None:
        if args and args[0].lower() in {"open", "settings", "setting"}:
            ok, message = self.launch_uri("ms-settings:network-wifi")
            rows = [self.kv("Wi-Fi Settings", self.status_text(ok, message))]
            self.write_panel("Wi-Fi", rows)
            return

        info = self.wifi_interfaces()
        profiles, profile_error = self.wifi_profiles()
        if "status" in info:
            rows = [
                self.kv("Status", info["status"]),
                self.kv("Profiles", str(len(profiles)) if profiles else profile_error or "none"),
            ]
        else:
            rows = [
                self.kv("Interface", info.get("Name", "unavailable")),
                self.kv("State", info.get("State", "unknown")),
                self.kv("SSID", info.get("SSID", "not connected")),
                self.kv("Signal", info.get("Signal", "unknown")),
                self.kv("Radio", info.get("Radio", "unknown")),
                self.kv("Auth", info.get("Auth", "unknown")),
                self.kv("Profiles", str(len(profiles)) if profiles else profile_error or "none"),
            ]
        if profiles:
            rows.append("")
            rows.extend(self.color(name, "accent_2") for name in profiles[:18])
            if len(profiles) > 18:
                rows.append(self.color(f"... {len(profiles) - 18} more", "muted"))
        self.write_panel(
            "Wi-Fi",
            rows,
            footer="Use wifi settings to open Windows Wi-Fi. Saved passwords are not displayed.",
        )

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

    def browser_cache_roots(self) -> list[Path]:
        roots: list[Path] = []
        local_env = os.environ.get("LOCALAPPDATA")
        roaming_env = os.environ.get("APPDATA")
        local = Path(local_env) if local_env else None
        roaming = Path(roaming_env) if roaming_env else None

        chromium_bases: list[Path] = []
        if local:
            chromium_bases = [
                local / "Google" / "Chrome" / "User Data",
                local / "Microsoft" / "Edge" / "User Data",
                local / "BraveSoftware" / "Brave-Browser" / "User Data",
                local / "CocCoc" / "Browser" / "User Data",
            ]
        cache_names = ("Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache")
        for base in chromium_bases:
            if not base.exists():
                continue
            profiles = [base / "Default"] + sorted(base.glob("Profile *"))
            for profile in profiles:
                for name in cache_names:
                    path = profile / name
                    if path.exists() and path not in roots:
                        roots.append(path)

        firefox_profiles = local / "Mozilla" / "Firefox" / "Profiles" if local else None
        if firefox_profiles and firefox_profiles.exists():
            for profile in firefox_profiles.iterdir():
                for name in ("cache2", "startupCache"):
                    path = profile / name
                    if path.exists() and path not in roots:
                        roots.append(path)

        app_cache_roots: list[Path] = []
        if roaming:
            app_cache_roots = [
                roaming / "discord" / "Cache",
                roaming / "discord" / "Code Cache",
                roaming / "discord" / "GPUCache",
                roaming / "Code" / "Cache",
                roaming / "Code" / "CachedData",
                roaming / "Code" / "Code Cache",
            ]
        for path in app_cache_roots:
            if path.exists() and path not in roots:
                roots.append(path)

        return roots

    def junk_roots(self) -> list[Path]:
        roots: list[Path] = []
        for path in self.temp_roots() + self.browser_cache_roots():
            if path.exists() and path not in roots:
                roots.append(path)
        return roots

    def scan_temp(self, max_items: int = 120000) -> TempScan:
        roots = self.junk_roots()
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
        temp_count = len(self.temp_roots())
        cache_count = len(self.browser_cache_roots())
        rows = [
            self.kv("Targets", f"{len(scan.roots)} safe folders"),
            self.kv("Temp folders", str(temp_count)),
            self.kv("Cache folders", str(cache_count)),
            self.kv("Files", str(scan.files)),
            self.kv("Subfolders", str(scan.dirs)),
            self.kv("Estimated size", human_bytes(scan.bytes_total)),
            self.kv("Access errors", str(scan.errors)),
        ]
        self.write_panel("Junk Scan", rows, footer="Run cleanup for dry-run, or cleanup --apply to delete after confirmation.")

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
            self.write_panel(
                "Cleanup Preview",
                rows,
                footer="Nothing was deleted. Use cleanup --apply and type DELETE to confirm.",
            )
            return

        print(self.color("This will delete files inside temp/cache folders only.", "warning", bold=True))
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

    def app_roots(self) -> list[Path]:
        roots: list[Path] = []
        candidates = [Path.home() / "Desktop"]
        appdata = os.environ.get("APPDATA")
        programdata = os.environ.get("PROGRAMDATA")
        public = os.environ.get("PUBLIC")
        if appdata:
            candidates.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        if programdata:
            candidates.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        if public:
            candidates.append(Path(public) / "Desktop")
        for path in candidates:
            if path.exists() and path not in roots:
                roots.append(path)
        return roots

    def discover_apps(self, query: str = "", limit: int = 120) -> list[AppEntry]:
        allowed = {
            ".lnk": "shortcut",
            ".appref-ms": "app",
            ".url": "url",
            ".cmd": "command",
            ".bat": "command",
        }
        needle = query.casefold().strip()
        entries: list[AppEntry] = []
        seen: set[str] = set()
        for root in self.app_roots():
            for current, _, filenames in os.walk(root):
                for filename in filenames:
                    path = Path(current) / filename
                    suffix = path.suffix.lower()
                    if suffix not in allowed:
                        continue
                    key = str(path).casefold()
                    if key in seen:
                        continue
                    name = path.stem.replace(" - Shortcut", "").strip()
                    searchable = name.casefold()
                    if needle and needle not in searchable:
                        continue
                    seen.add(key)
                    entries.append(AppEntry(name=name, path=path, kind=allowed[suffix]))

        def score(entry: AppEntry) -> tuple[int, int, str]:
            name = entry.name.casefold()
            if not needle:
                rank = 50
            elif name == needle:
                rank = 0
            elif name.startswith(needle):
                rank = 1
            elif needle in name:
                rank = 2
            else:
                rank = 3
            return rank, len(entry.name), entry.name.casefold()

        entries.sort(key=score)
        return entries[:limit]

    def app_row(self, entry: AppEntry) -> str:
        name = self.color(shorten(entry.name, 34).ljust(36), "accent_2", bold=True)
        kind = self.color(entry.kind.ljust(9), "muted")
        return f"{name} {kind} {self.color(str(entry.path), 'fg')}"

    def cmd_apps(self, args: list[str]) -> None:
        query = " ".join(args).strip()
        apps = self.discover_apps(query)
        rows = [self.app_row(app) for app in apps[:24]]
        if not rows:
            message = f"No Start Menu apps matched: {query}" if query else "No Start Menu apps found."
            rows = [message]
        elif len(apps) > 24:
            rows.append(self.color(f"... {len(apps) - 24} more", "muted"))
        title = "Apps" if not query else f"Apps: {query}"
        self.write_panel(title, rows, footer="Use open <app name> to launch the best match.")

    def launch_uri(self, uri: str) -> tuple[bool, str]:
        try:
            if os.name == "nt":
                os.startfile(uri)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "opened"
        except Exception as exc:
            return False, str(exc)

    def launch_path(self, path: Path) -> tuple[bool, str]:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "opened"
        except Exception as exc:
            return False, str(exc)

    def launch_command(self, command: list[str]) -> tuple[bool, str]:
        try:
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "opened"
        except Exception as exc:
            return False, str(exc)

    def cmd_open(self, args: list[str]) -> None:
        if not args:
            self.error("Usage: open <app/settings/folder>")
            return

        target = " ".join(args).strip()
        key = target.casefold()
        quick_paths: dict[str, Path] = {
            "downloads": Path.home() / "Downloads",
            "download": Path.home() / "Downloads",
            "desktop": Path.home() / "Desktop",
            "temp": Path(tempfile.gettempdir()),
            "startup": Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup",
        }
        quick_uris = {
            "settings": "ms-settings:",
            "setting": "ms-settings:",
            "wifi": "ms-settings:network-wifi",
            "wi-fi": "ms-settings:network-wifi",
            "network": "ms-settings:network",
            "apps": "ms-settings:appsfeatures",
        }
        quick_commands = {
            "control": ["control"],
            "control panel": ["control"],
            "taskmgr": ["taskmgr"],
            "task manager": ["taskmgr"],
            "explorer": ["explorer"],
        }

        if key in quick_paths:
            ok, message = self.launch_path(quick_paths[key])
            self.write_panel("Open", [self.kv(target, self.status_text(ok, message))])
            return
        if key in quick_uris:
            ok, message = self.launch_uri(quick_uris[key])
            self.write_panel("Open", [self.kv(target, self.status_text(ok, message))])
            return
        if key in quick_commands:
            ok, message = self.launch_command(quick_commands[key])
            self.write_panel("Open", [self.kv(target, self.status_text(ok, message))])
            return

        matches = self.discover_apps(target, limit=10)
        if not matches:
            self.write_panel(
                "Open",
                [self.color(f"No app matched: {target}", "danger", bold=True)],
                footer="Try apps <name> to search Start Menu shortcuts.",
            )
            return

        selected = matches[0]
        ok, message = self.launch_path(selected.path)
        rows = [
            self.kv("App", selected.name),
            self.kv("Type", selected.kind),
            self.kv("Result", self.status_text(ok, message)),
        ]
        if len(matches) > 1:
            rows.append("")
            rows.append(self.color("Other matches:", "muted"))
            rows.extend(self.color(match.name, "accent_2") for match in matches[1:6])
        self.write_panel("Open", rows, footer=str(selected.path))

    def cmd_recycle(self, args: list[str]) -> None:
        if "--empty" not in args:
            self.write_panel(
                "Recycle Bin",
                [
                    self.kv("Mode", "preview"),
                    "This command can empty the Windows Recycle Bin.",
                    "Run recycle --empty and type EMPTY to confirm.",
                ],
                footer="No files were deleted.",
            )
            return

        if os.name != "nt":
            self.write_panel("Recycle Bin", ["Recycle Bin cleanup is currently Windows-only."])
            return

        print(self.color("This will empty the Windows Recycle Bin.", "warning", bold=True))
        confirm = input(self.color("Type EMPTY to continue: ", "danger", bold=True)).strip()
        if confirm != "EMPTY":
            print(self.color("Recycle Bin cleanup cancelled.", "muted"))
            return

        flags = 0x00000001 | 0x00000002 | 0x00000004
        try:
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            ok = result == 0
            message = "emptied" if ok else f"failed: HRESULT {result}"
        except Exception as exc:
            ok = False
            message = str(exc)
        self.write_panel("Recycle Bin", [self.kv("Result", self.status_text(ok, message))])

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
                "[Junk]",
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
