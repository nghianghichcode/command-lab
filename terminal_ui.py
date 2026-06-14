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
APP_VERSION = "0.5.0"

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
    if os.name == "nt":
        os.system("cls")
    else:
        print(f"{ESC}2J{ESC}H", end="", flush=True)


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
        # On Windows with msvcrt available, arrow-key input always works
        # regardless of isatty() — so treat as interactive unconditionally.
        self.interactive = _HAS_MSVCRT or (sys.stdin.isatty() and sys.stdout.isatty())
        self.last_temp_scan: TempScan | None = None
        self.commands: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "trogiup": self.cmd_help,
            "?": self.cmd_help,
            "dashboard": self.cmd_dashboard,
            "tongquan": self.cmd_dashboard,
            "status": self.cmd_dashboard,
            "system": self.cmd_system,
            "hethong": self.cmd_system,
            "sys": self.cmd_system,
            "disk": self.cmd_disk,
            "odia": self.cmd_disk,
            "disks": self.cmd_disk,
            "network": self.cmd_network,
            "net": self.cmd_network,
            "netword": self.cmd_network,
            "ports": self.cmd_ports,
            "port": self.cmd_ports,
            "wifi": self.cmd_wifi,
            "apps": self.cmd_apps,
            "ungdung": self.cmd_apps,
            "app": self.cmd_apps,
            "open": self.cmd_open,
            "mo": self.cmd_open,
            "launch": self.cmd_open,
            "processes": self.cmd_processes,
            "tientrinh": self.cmd_processes,
            "ps": self.cmd_processes,
            "temp": self.cmd_temp,
            "quetrac": self.cmd_temp,
            "junk": self.cmd_temp,
            "clean": self.cmd_cleanup,
            "donrac": self.cmd_cleanup,
            "cleanup": self.cmd_cleanup,
            "recycle": self.cmd_recycle,
            "thungrac": self.cmd_recycle,
            "startup": self.cmd_startup,
            "khoidong": self.cmd_startup,
            "path": self.cmd_path,
            "report": self.cmd_report,
            "baocao": self.cmd_report,
            "theme": self.cmd_theme,
            "giaodien": self.cmd_theme,
            "history": self.cmd_history,
            "lichsu": self.cmd_history,
            "about": self.cmd_about,
            "thongtin": self.cmd_about,
            "clear": self.cmd_clear,
            "xoa": self.cmd_clear,
            "exit": self.cmd_exit,
            "thoat": self.cmd_exit,
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
        # Just show the banner — the loop will immediately call interactive_menu()
        # which does clear+banner+menu, so no need for extra text here.
        clear()
        self.render_banner()
        self.scan_effect("ready")

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
            line = self.color(frame, color, bold=True) + self.color(f" đang tải {text}", "muted")
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
        print(self.color(f"v{APP_VERSION} - Công cụ hệ thống Windows", "muted"))
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
        ("Tổng quan",   "dashboard"),
        ("Hệ thống",    "system"),
        ("Ổ đĩa",       "disk"),
        ("Mạng",        "network"),
        ("Wi-Fi",       "wifi"),
        ("Ứng dụng",    "apps"),
        ("Tiến trình",  "processes"),
        ("Quét rác",    "junk"),
        ("Dọn rác",     "cleanup"),
        ("Khởi động",   "startup"),
        ("Báo cáo",     "report"),
        ("Giao diện",   "theme"),
        ("Lịch sử",     "history"),
        ("Trợ giúp",    "help"),
        ("Thoát",       "exit"),
    ]

    def _read_key(self) -> str:
        """Read a single keypress. Returns 'up', 'down', 'enter', 'esc', or the char.
        Unknown/unsupported special keys return empty string.
        """
        if _HAS_MSVCRT:
            while True:
                ch = _msvcrt.getwch()
                if ch in ("\xe0", "\x00"):  # special key prefix on Windows
                    ch2 = _msvcrt.getwch()
                    if ch2 == "H":
                        return "up"
                    if ch2 == "P":
                        return "down"
                    # ignore other special keys (F-keys, Page Up/Down, etc.)
                    continue
                if ch == "\r":
                    return "enter"
                if ch == "\x1b":
                    return "esc"
                if ch == "\x03":  # Ctrl-C
                    raise KeyboardInterrupt
                # Printable char
                return ch
        # Fallback: just read a line
        try:
            line = input().strip()
        except EOFError:
            raise KeyboardInterrupt
        return line if line else "enter"

    def _render_menu(self, selected: int) -> None:
        """Render the interactive menu (ASCII-safe, works in any Windows terminal)."""
        width = self.panel_width()
        items = self.MENU_ITEMS
        n = len(items)
        half = n // 2 + n % 2  # left column count
        col_w = (width - 5) // 2

        sep = self.color("+" + "-" * (width - 2) + "+", "muted")
        header_text = " " + self.color("MENU", "accent", bold=True) + \
            self.color("  ↑/↓: Di chuyển   Enter: Chọn   ESC: Gõ lệnh", "muted")
        header_line = (
            self.color("|", "muted")
            + pad(header_text, width - 2)
            + self.color("|", "muted")
        )
        print(sep)
        print(header_line)
        print(sep)

        # Two-column layout
        for row in range(half):
            left_idx = row
            right_idx = row + half
            content = " "
            for idx in (left_idx, right_idx):
                if idx >= n:
                    continue
                label, _ = items[idx]
                if idx == selected:
                    cell = (
                        self.color(" > ", "accent", bold=True)
                        + self.color(pad(label, col_w - 3), "fg", bold=True)
                    )
                else:
                    cell = self.color("   " + pad(label, col_w - 3), "muted")
                
                if idx == left_idx:
                    content += pad(cell, col_w) + "  "
                else:
                    content += pad(cell, col_w)
            
            line = self.color("|", "muted") + pad(content, width - 2) + self.color("|", "muted")
            print(line)

        print(sep)

    def interactive_menu(self) -> str | None:
        """
        Show an interactive arrow-key menu using full-screen clear+redraw.
        Returns the selected command string, or None if user pressed ESC.
        """
        if not _HAS_MSVCRT:
            # Fallback: numbered list for non-Windows
            print()
            for i, (label, _) in enumerate(self.MENU_ITEMS, 1):
                print(f"  {self.color(str(i).rjust(2), 'accent_2')}. {self.color(label, 'fg')}")
            print()
            try:
                raw = input(self.prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                return "exit"
            if raw.isdigit():
                n = int(raw) - 1
                if 0 <= n < len(self.MENU_ITEMS):
                    return self.MENU_ITEMS[n][1]
            return raw if raw else None

        selected = 0
        total = len(self.MENU_ITEMS)

        print("\033[?25l", end="", flush=True)  # hide cursor
        try:
            # Initial draw
            clear()
            self.render_banner()
            self._render_menu(selected)

            while True:
                key = self._read_key()
                if key == "up":
                    selected = (selected - 1) % total
                elif key == "down":
                    selected = (selected + 1) % total
                elif key == "enter":
                    return self.MENU_ITEMS[selected][1]
                elif key == "esc":
                    # ESC -> text input mode
                    clear()
                    self.render_banner()
                    return None
                elif key:
                    # Printable char typed -> text mode pre-seeded
                    clear()
                    self.render_banner()
                    try:
                        rest = input(self.prompt() + key).strip()
                        return key + rest
                    except (EOFError, KeyboardInterrupt):
                        return "exit"
                # Redraw: ONLY MOVE CURSOR HOME, DO NOT CLEAR
                print("\033[1;1H", end="", flush=True)
                self.render_banner()
                self._render_menu(selected)
                print("\033[0J", end="", flush=True)
        finally:
            print("\033[?25h", end="", flush=True)  # restore cursor

    def _wait_key(self) -> None:
        """After showing a command result, wait for any key before returning to menu."""
        print()
        print(self.color("  Nhấn phím bất kỳ để quay lại menu...", "muted"))
        if _HAS_MSVCRT:
            _msvcrt.getwch()
        else:
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

    def loop(self) -> None:
        self.boot()

        while self.running:
            try:
                result = self.interactive_menu()
            except KeyboardInterrupt:
                print()
                self.cmd_exit([])
                break

            if result is None:
                # ESC -> text input mode (banner already drawn)
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
                if self.running:
                    self._wait_key()
            else:
                raw = result.strip()
                if not raw:
                    continue
                self.history.append(raw)
                self.dispatch(raw)
                if self.running:
                    self._wait_key()

    def dispatch(self, raw: str) -> None:
        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            self.render_screen("parse error", animate=True)
            self.error(f"Không hiểu được lệnh: {exc}")
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
            handler(args) if handler else self.error(f"Không tìm thấy lệnh: {command}")
            return

        self.render_screen(raw, animate=True)

        if handler is None:
            self.error(f"Không tìm thấy lệnh: {command}")
            return

        handler(args)

    def command_row(self, command: str, detail: str) -> str:
        return f"{self.color(command.ljust(20), 'accent_2', bold=True)} {self.color(detail, 'fg')}"

    def cmd_help(self, _: list[str]) -> None:
        rows = [
            self.command_row("dashboard", "Xem tổng quan sức khỏe hệ thống (RAM, CPU, Ổ đĩa, Mạng)"),
            self.command_row("system", "Thông tin chi tiết về Hệ điều hành, CPU, RAM"),
            self.command_row("disk", "Xem dung lượng các ổ đĩa và cảnh báo đầy"),
            self.command_row("network", "Kiểm tra IP nội bộ, DNS và kết nối mạng"),
            self.command_row("wifi", "Xem trạng thái Wi-Fi và các mạng đã lưu"),
            self.command_row("wifi settings", "Mở Cài đặt Wi-Fi của Windows"),
            self.command_row("ports host port", "Kiểm tra cổng TCP (VD: ports github.com 443)"),
            self.command_row("apps [name]", "Tìm kiếm ứng dụng trong Start Menu"),
            self.command_row("open <app>", "Mở nhanh ứng dụng hoặc thư mục (VD: open chrome)"),
            self.command_row("processes [n]", "Xem các tiến trình ngốn RAM nhất"),
            self.command_row("temp / junk", "Quét tìm tệp rác trong Temp và Cache trình duyệt"),
            self.command_row("cleanup", "Xem trước các tệp rác sẽ bị xóa (chưa xóa thật)"),
            self.command_row("cleanup --apply", "Xóa thật các tệp rác sau khi xác nhận"),
            self.command_row("recycle --empty", "Dọn sạch Thùng rác sau khi xác nhận"),
            self.command_row("startup", "Liệt kê các tệp khởi động cùng Windows"),
            self.command_row("path", "Xem các biến môi trường PATH"),
            self.command_row("report", "Xuất báo cáo hệ thống ra màn hình Desktop"),
            self.command_row("theme", "Đổi giao diện: carbon, graphite, matrix"),
            self.command_row("clear / exit", "Xóa màn hình hoặc Thoát công cụ"),
        ]
        self.write_panel("Trợ Giúp", rows, footer="An toàn: Lệnh dọn rác sẽ không xóa trừ khi bạn dùng --apply và xác nhận.")

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
            self.kv("Máy tính", socket.gethostname()),
            self.kv("Người dùng", getpass.getuser()),
            self.kv("HĐH", platform.platform()),
            self.kv("Quyền Admin", "Có" if self.is_admin() else "Không"),
            self.kv("RAM", self.memory_summary(memory)),
            self.kv("Ổ đĩa", disk_warning),
            self.kv("Mạng", local_ip),
            self.kv("Tệp rác", f"{human_bytes(temp_scan.bytes_total)} trong {temp_scan.files} tệp"),
        ]
        self.write_panel("Tổng Quan", rows, footer="Gõ lệnh: system | disk | network | wifi | apps | cleanup | report")

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
            self.kv("Máy tính", socket.gethostname()),
            self.kv("Người dùng", getpass.getuser()),
            self.kv("Quyền Admin", "Có" if self.is_admin() else "Không"),
            self.kv("HĐH", platform.platform()),
            self.kv("Kiến trúc", platform.machine() or "unknown"),
            self.kv("CPU", self.cpu_name()),
            self.kv("RAM", self.memory_summary(memory)),
            self.kv("Shell", os.environ.get("COMSPEC", "unknown")),
            self.kv("Thư mục cài đặt", str(Path.cwd())),
        ]
        self.write_panel("Hệ Thống", rows)

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
                f"{self.color('trống', 'muted')} {human_bytes(int(item['free']))} "
                f"{self.color('tổng', 'muted')} {human_bytes(int(item['total']))}"
            )
        if not rows:
            rows = ["Không tìm thấy ổ đĩa nào."]
        self.write_panel("Dung Lượng Ổ Đĩa", rows)

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
            self.kv("Tên máy", socket.gethostname()),
            self.kv("IP nội bộ", self.local_ip()),
            self.kv("DNS", self.status_text(dns_ok, dns_message)),
            self.kv("Ping 1.1.1.1", self.status_text(cloudflare_ok, cloudflare_msg)),
            self.kv("Ping 8.8.8.8", self.status_text(google_ok, google_msg)),
            self.kv("GitHub 443", self.status_text(github_ok, "tcp ok" if github_ok else "tcp failed")),
        ]
        self.write_panel("Mạng", rows, footer="Nếu ping thất bại nhưng GitHub 443 OK, ICMP có thể đang bị chặn.")

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
            rows = [self.kv("Cài đặt Wi-Fi", self.status_text(ok, message))]
            self.write_panel("Wi-Fi", rows)
            return

        info = self.wifi_interfaces()
        profiles, profile_error = self.wifi_profiles()
        if "status" in info:
            rows = [
                self.kv("Trạng thái", info["status"]),
                self.kv("Mạng đã lưu", str(len(profiles)) if profiles else profile_error or "không có"),
            ]
        else:
            rows = [
                self.kv("Giao diện", info.get("Name", "không rõ")),
                self.kv("Trạng thái", info.get("State", "không rõ")),
                self.kv("SSID", info.get("SSID", "chưa kết nối")),
                self.kv("Tín hiệu", info.get("Signal", "không rõ")),
                self.kv("Loại sóng", info.get("Radio", "không rõ")),
                self.kv("Bảo mật", info.get("Auth", "không rõ")),
                self.kv("Mạng đã lưu", str(len(profiles)) if profiles else profile_error or "không có"),
            ]
        if profiles:
            rows.append("")
            rows.extend(self.color(name, "accent_2") for name in profiles[:18])
            if len(profiles) > 18:
                rows.append(self.color(f"... {len(profiles) - 18} mạng khác", "muted"))
        self.write_panel(
            "Wi-Fi",
            rows,
            footer='Gõ "wifi settings" để mở Cài đặt. Mật khẩu không được hiển thị để bảo mật.',
        )

    def tcp_check(self, host: str, port: int, timeout: int = 4) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def cmd_ports(self, args: list[str]) -> None:
        if len(args) < 2:
            self.error("Cú pháp: ports <host> <port> [port...]")
            return

        host = args[0]
        rows: list[str] = []
        for raw_port in args[1:]:
            try:
                port = int(raw_port)
            except ValueError:
                rows.append(f"{self.color(raw_port.ljust(8), 'danger')} cổng không hợp lệ")
                continue

            ok = self.tcp_check(host, port)
            rows.append(
                f"{self.color((str(port) + '/tcp').ljust(10), 'accent_2')} "
                + self.status_text(ok, "mở/kết nối được" if ok else "đóng/bị chặn")
            )
        self.write_panel(f"Kiểm tra Cổng: {host}", rows)

    def cmd_processes(self, args: list[str]) -> None:
        limit = 12
        if args:
            try:
                limit = max(1, min(50, int(args[0])))
            except ValueError:
                self.error("Cú pháp: processes [số_lượng]")
                return

        if os.name != "nt":
            self.write_panel("Processes", ["Tính năng này hiện chỉ tối ưu cho Windows."])
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
        self.write_panel("Tiến Trình Đang Chạy", rows, footer="Sắp xếp theo mức dùng RAM.")

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
            self.kv("Thư mục quét", f"{len(scan.roots)} thư mục an toàn"),
            self.kv("Thư mục Temp", str(temp_count)),
            self.kv("Thư mục Cache", str(cache_count)),
            self.kv("Số tệp tin", str(scan.files)),
            self.kv("Thư mục con", str(scan.dirs)),
            self.kv("Dung lượng ước tính", human_bytes(scan.bytes_total)),
            self.kv("Lỗi truy cập", str(scan.errors)),
        ]
        self.write_panel("Quét Rác", rows, footer="Bạn có muốn dọn dẹp các tệp rác này không?")
        
        print()
        print(self.color("  Nhấn phím Y để XÓA NGAY, hoặc phím bất kỳ để quay lại...", "muted"), end="", flush=True)
        key = self._read_key()
        if key.lower() == "y":
            print("\n")
            self.cmd_cleanup(["--apply"])
        else:
            self._skip_wait = True

    def cmd_cleanup(self, args: list[str]) -> None:
        apply = "--apply" in args or "-y" in args
        scan = self.scan_temp()
        self.last_temp_scan = scan

        if not apply:
            rows = [
                self.kv("Chế độ", "chỉ xem trước"),
                self.kv("Targets", ", ".join(str(root) for root in scan.roots)),
                self.kv("Số tệp tin", str(scan.files)),
                self.kv("Dung lượng ước tính", human_bytes(scan.bytes_total)),
                self.kv("Errors", str(scan.errors)),
            ]
            self.write_panel(
                "Xem Trước Dọn Dẹp",
                rows,
                footer="Chưa có gì bị xóa. Bạn có muốn xóa ngay không?",
            )
            print()
            print(self.color("  Nhấn phím Y để XÓA NGAY, hoặc phím bất kỳ để quay lại...", "muted"), end="", flush=True)
            key = self._read_key()
            if key.lower() == "y":
                print("\n")
                self.cmd_cleanup(["--apply"])
            else:
                self._skip_wait = True
            return

        print(self.color("Lệnh này chỉ xóa các tệp rác trong temp/cache.", "warning", bold=True))
        confirm = input(self.color("Gõ XOA để tiếp tục: ", "danger", bold=True)).strip()
        if confirm != "XOA":
            print(self.color("Đã hủy dọn dẹp.", "muted"))
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
            self.kv("Tệp đã xóa", str(deleted_files)),
            self.kv("Đã giải phóng", human_bytes(deleted_bytes)),
            self.kv("Bỏ qua/Lỗi", str(errors)),
        ]
        self.write_panel("Hoàn Tất Dọn Dẹp", rows)

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
        seen_names: set[str] = set()
        junk_keywords = ("uninstall", "gỡ cài", "readme", "help", "manual", "hướng dẫn", "setup", "update", "website", "url")
        
        for root in self.app_roots():
            for current, _, filenames in os.walk(root):
                for filename in filenames:
                    path = Path(current) / filename
                    suffix = path.suffix.lower()
                    if suffix not in allowed:
                        continue
                    
                    name = path.stem.replace(" - Shortcut", "").strip()
                    searchable = name.casefold()
                    
                    if any(junk in searchable for junk in junk_keywords):
                        continue
                    if needle and needle not in searchable:
                        continue
                    if searchable in seen_names:
                        continue
                        
                    seen_names.add(searchable)
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

        if not apps:
            message = f"Không tìm thấy ứng dụng: {query}" if query else "Không có ứng dụng nào."
            self.write_panel("Apps", [message])
            return

        if not _HAS_MSVCRT:
            rows = [self.app_row(app) for app in apps[:24]]
            if len(apps) > 24:
                rows.append(self.color(f"... {len(apps) - 24} mục khác", "muted"))
            title = "Apps" if not query else f"Apps: {query}"
            self.write_panel(title, rows, footer="Dùng lệnh: open <tên> để mở ứng dụng.")
            return

        selected = 0
        total = len(apps)
        start_idx = 0
        title = "Apps" if not query else f"Apps: {query}"

        print("\033[?25l", end="", flush=True)  # hide cursor
        try:
            # We must clear the screen once BEFORE the loop so any previous scan_effect
            # that might have scrolled the viewport is erased, ensuring \033[1;1H is safe.
            if os.name == "nt":
                os.system("cls")
            else:
                clear()
                
            while True:
                term_lines = shutil.get_terminal_size((80, 24)).lines
                # banner(11) + context(3) + panel_overhead(7) + "đang xem"(1) = 22 lines.
                # Subtract 23 to leave a 1-line safe margin at the bottom.
                max_rows = max(3, term_lines - 23)

                if selected < start_idx:
                    start_idx = selected
                elif selected >= start_idx + max_rows:
                    start_idx = selected - max_rows + 1

                print("\033[1;1H", end="", flush=True)
                self.render_banner()
                self.render_context(f"apps {query}".strip())

                display_apps = apps[start_idx : start_idx + max_rows]
                rows = []
                for i, app in enumerate(display_apps):
                    actual_idx = start_idx + i
                    name = shorten(app.name, 34).ljust(36)
                    kind = app.kind.ljust(9)
                    if actual_idx == selected:
                        rows.append(
                            self.color(" > ", "accent", bold=True)
                            + self.color(name, "fg", bold=True)
                            + f" {self.color(kind, 'muted')} "
                            + self.color(str(app.path), "fg")
                        )
                    else:
                        rows.append(
                            self.color("   ", "muted")
                            + self.color(name, "accent_2", bold=True)
                            + f" {self.color(kind, 'muted')} "
                            + self.color(str(app.path), "fg")
                        )
                
                if total > max_rows:
                    rows.append(self.color(f"... đang xem {start_idx + 1}-{min(start_idx + max_rows, total)} / {total} mục", "muted"))

                self.write_panel(title, rows, footer="↑/↓: Di chuyển   Enter: Mở ứng dụng   ESC: Quay lại")
                print("\033[0J", end="", flush=True)

                key = self._read_key()
                if key == "up":
                    selected = (selected - 1) % total
                elif key == "down":
                    selected = (selected + 1) % total
                elif key == "enter":
                    app = apps[selected]
                    if app.kind in ("exe", "shortcut", "script"):
                        ok, msg = self.launch_path(Path(app.path))
                    elif app.kind == "url":
                        ok, msg = self.launch_uri(app.path)
                    elif app.kind == "command":
                        ok, msg = self.launch_command([app.path])
                    else:
                        ok, msg = False, "unknown type"

                    if os.name == "nt":
                        os.system("cls")
                    else:
                        clear()
                    self.render_banner()
                    self.render_context(f"apps {query}".strip())
                    
                    res_row = self.kv(app.name, self.status_text(ok, msg))
                    self.write_panel("Kết quả mở", [res_row])
                    return
                elif key == "esc":
                    if os.name == "nt":
                        os.system("cls")
                    else:
                        clear()
                    self.render_banner()
                    self.render_context(f"apps {query}".strip())
                    self.write_panel(title, rows, footer="Đã hủy.")
                    return
        finally:
            print("\033[?25h", end="", flush=True)  # restore cursor

    def launch_uri(self, uri: str) -> tuple[bool, str]:
        try:
            if os.name == "nt":
                os.startfile(uri)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "đã mở"
        except Exception as exc:
            return False, str(exc)

    def launch_path(self, path: Path) -> tuple[bool, str]:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "đã mở"
        except Exception as exc:
            return False, str(exc)

    def launch_command(self, command: list[str]) -> tuple[bool, str]:
        try:
            subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "đã mở"
        except Exception as exc:
            return False, str(exc)

    def cmd_open(self, args: list[str]) -> None:
        if not args:
            self.error("Cú pháp: open <ứng dụng/cài đặt/thư mục>")
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
            self.write_panel("Mở", [self.kv(target, self.status_text(ok, message))])
            return
        if key in quick_uris:
            ok, message = self.launch_uri(quick_uris[key])
            self.write_panel("Mở", [self.kv(target, self.status_text(ok, message))])
            return
        if key in quick_commands:
            ok, message = self.launch_command(quick_commands[key])
            self.write_panel("Mở", [self.kv(target, self.status_text(ok, message))])
            return

        matches = self.discover_apps(target, limit=10)
        if not matches:
            self.write_panel(
                "Open",
                [self.color(f"Không tìm thấy ứng dụng: {target}", "danger", bold=True)],
                footer="Hãy dùng: apps <tên> để tìm trong Start Menu.",
            )
            return

        selected = matches[0]
        ok, message = self.launch_path(selected.path)
        rows = [
            self.kv("Ứng dụng", selected.name),
            self.kv("Loại", selected.kind),
            self.kv("Kết quả", self.status_text(ok, message)),
        ]
        if len(matches) > 1:
            rows.append("")
            rows.append(self.color("Các kết quả khác:", "muted"))
            rows.extend(self.color(match.name, "accent_2") for match in matches[1:6])
        self.write_panel("Mở", rows, footer=str(selected.path))

    def cmd_recycle(self, args: list[str]) -> None:
        if "--empty" not in args:
            self.write_panel(
                "Thùng Rác",
                [
                    self.kv("Chế độ", "xem trước"),
                    "Lệnh này sẽ dọn sạch Thùng rác Windows.",
                    "Chạy lệnh: recycle --empty và gõ TRONG để xác nhận.",
                ],
                footer="Chưa có gì bị xóa.",
            )
            return

        if os.name != "nt":
            self.write_panel("Recycle Bin", ["Recycle Bin cleanup is currently Windows-only."])
            return

        print(self.color("Tất cả tệp trong Thùng rác sẽ bị xóa vĩnh viễn.", "warning", bold=True))
        confirm = input(self.color("Gõ TRONG để tiếp tục: ", "danger", bold=True)).strip()
        if confirm != "TRONG":
            print(self.color("Đã hủy dọn Thùng rác.", "muted"))
            return

        flags = 0x00000001 | 0x00000002 | 0x00000004
        try:
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            ok = result == 0
            message = "đã dọn sạch" if ok else f"lỗi: HRESULT {result}"
        except Exception as exc:
            ok = False
            message = str(exc)
        self.write_panel("Thùng Rác", [self.kv("Kết quả", self.status_text(ok, message))])

    def cmd_startup(self, _: list[str]) -> None:
        startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if not startup.exists():
            self.write_panel("Startup", ["Không tìm thấy thư mục Khởi động."])
            return
        items = list(startup.iterdir())
        rows = [self.color(item.name, "accent_2") for item in items[:40]]
        if not rows:
            rows = ["Không có tệp nào tự khởi động."]
        self.write_panel("Khởi Động", rows, footer=str(startup))

    def cmd_path(self, _: list[str]) -> None:
        entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
        rows = [f"{index:02d}. {entry}" for index, entry in enumerate(entries[:40], start=1)]
        if len(entries) > 40:
            rows.append(f"... {len(entries) - 40} dòng khác")
        self.write_panel("PATH", rows or ["PATH trống."])

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
                self.write_panel("Báo Cáo", [self.kv("Đã lưu", str(candidate))])
                return
            except OSError as exc:
                last_error = str(exc)
        self.error(f"Không thể xuất báo cáo: {last_error}")

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
            self.write_panel("Giao Diện", rows, footer="Gõ: theme carbon | theme graphite | theme matrix")
            return

        name = args[0].lower()
        next_theme = THEMES.get(name)
        if not next_theme:
            self.render_screen(f"theme {name}", animate=True)
            self.error(f"Không có giao diện này: {name}")
            return
        self.theme = next_theme
        self.render_screen(f"theme {name}", animate=True)
        self.write_panel("Giao Diện", [self.kv("Đang dùng", name)])

    def cmd_history(self, _: list[str]) -> None:
        rows = [f"{index:02d}. {item}" for index, item in enumerate(self.history[-14:], start=1)]
        self.write_panel("History", rows or ["Chưa có lịch sử lệnh."])

    def cmd_about(self, _: list[str]) -> None:
        rows = [
            f"{APP_NAME} là công cụ kiểm tra và bảo trì hệ thống Windows qua dòng lệnh.",
            "Nó chạy dạng độc lập (.exe), mặc định an toàn vì chỉ xem hệ thống.",
            "Việc dọn rác chỉ tác động mục temp/cache và phải xác nhận gõ lệnh rõ ràng.",
        ]
        self.write_panel("Thông Tin", rows)

    def cmd_clear(self, _: list[str]) -> None:
        self.boot()

    def cmd_exit(self, _: list[str]) -> None:
        self.running = False
        print(self.color(f"Đã đóng {APP_NAME}.", "muted"))

    def error(self, message: str) -> None:
        self.write_panel("Lỗi", [self.color(message, "danger", bold=True)], footer="Gõ 'help' để xem các lệnh hỗ trợ.")


def main() -> int:
    configure_stdio()
    enable_ansi()
    app = PCToolkit()
    app.loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
