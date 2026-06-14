from __future__ import annotations

import ctypes
import os
import re
import shlex
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


ESC = "\033["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
REVERSE = f"{ESC}7m"
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


def clear() -> None:
    print(f"{ESC}2J{ESC}H", end="")


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
    panel: tuple[int, int, int]
    panel_alt: tuple[int, int, int]


THEMES: dict[str, Theme] = {
    "dark": Theme(
        "dark",
        fg=(226, 226, 218),
        muted=(136, 138, 145),
        accent=(236, 113, 82),
        accent_2=(92, 190, 255),
        success=(88, 214, 141),
        warning=(238, 199, 89),
        danger=(255, 96, 96),
        panel=(24, 24, 27),
        panel_alt=(38, 38, 43),
    ),
    "ocean": Theme(
        "ocean",
        fg=(225, 242, 245),
        muted=(122, 152, 158),
        accent=(80, 214, 255),
        accent_2=(128, 236, 188),
        success=(132, 230, 162),
        warning=(247, 206, 116),
        danger=(255, 116, 116),
        panel=(8, 32, 42),
        panel_alt=(12, 47, 61),
    ),
    "amber": Theme(
        "amber",
        fg=(244, 235, 214),
        muted=(166, 149, 119),
        accent=(255, 183, 82),
        accent_2=(115, 209, 193),
        success=(133, 224, 128),
        warning=(255, 210, 96),
        danger=(255, 105, 91),
        panel=(38, 31, 23),
        panel_alt=(55, 44, 31),
    ),
}


class CommandLab:
    def __init__(self) -> None:
        self.theme = THEMES["dark"]
        self.history: list[str] = []
        self.notes: list[str] = []
        self.running = True
        self.commands: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "?": self.cmd_help,
            "status": self.cmd_status,
            "run": self.cmd_run,
            "theme": self.cmd_theme,
            "diff": self.cmd_diff,
            "note": self.cmd_note,
            "history": self.cmd_history,
            "about": self.cmd_about,
            "clear": self.cmd_clear,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }

    def color(self, value: str, key: str = "fg", *, bold: bool = False, bg: str | None = None) -> str:
        fg = getattr(self.theme, key)
        prefix = rgb(fg)
        if bg is not None:
            prefix += rgb(getattr(self.theme, bg), background=True)
        if bold:
            prefix += BOLD
        return f"{prefix}{value}{RESET}"

    def panel_width(self) -> int:
        size = shutil.get_terminal_size((112, 32))
        return max(72, min(118, size.columns - 4))

    def line(self, char: str = "-") -> str:
        return char * self.panel_width()

    def write_panel(self, title: str, rows: list[str], footer: str | None = None) -> None:
        width = self.panel_width()
        border = self.color("+" + ("-" * (width - 2)) + "+", "muted")
        title_text = f" {title} "
        print(border)
        print(
            self.color("|", "muted")
            + pad(self.color(title_text, "accent", bold=True), width - 2)
            + self.color("|", "muted")
        )
        print(self.color("+" + ("-" * (width - 2)) + "+", "muted"))

        for row in rows:
            print(self.color("|", "muted") + pad(f" {row}", width - 2) + self.color("|", "muted"))

        if footer:
            print(self.color("+" + ("-" * (width - 2)) + "+", "muted"))
            print(self.color("|", "muted") + pad(f" {footer}", width - 2) + self.color("|", "muted"))

        print(border)

    def boot(self) -> None:
        clear()
        self.render_banner()
        self.cmd_status([])
        self.cmd_diff([])
        print()
        print(
            self.color("cmdlab", "accent", bold=True)
            + self.color(" ready. ", "muted")
            + self.color("Type ", "muted")
            + self.color("help", "accent_2", bold=True)
            + self.color(" for commands.", "muted")
        )
        print()

    def render_banner(self) -> None:
        art = [
            r"   ______                                          __   __          __",
            r"  / ____/___  ____ ___  ____ ___  ____ _____  ____/ /  / /   ____ _/ /_",
            r" / /   / __ \/ __ `__ \/ __ `__ \/ __ `/ __ \/ __  /  / /   / __ `/ __ \\",
            r"/ /___/ /_/ / / / / / / / / / / / /_/ / / / / /_/ /  / /___/ /_/ / /_/ /",
            r"\____/\____/_/ /_/ /_/_/ /_/ /_/\__,_/_/ /_/\__,_/  /_____/\__,_/_.___/",
        ]
        print(self.color(self.line("."), "muted"))
        for row in art:
            print(self.color(row, "accent", bold=True))
        print(self.color("Interactive command terminal - local prototype", "muted"))
        print(self.color(self.line("."), "muted"))
        print()

    def prompt(self) -> str:
        cwd = os.getcwd()
        name = os.path.basename(cwd) or cwd
        return (
            self.color("cmdlab", "accent", bold=True)
            + self.color(":", "muted")
            + self.color(name, "accent_2")
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
            self.error(f"Cannot parse command: {exc}")
            return

        command = parts[0].lower()
        args = parts[1:]
        handler = self.commands.get(command)

        if handler is None:
            self.error(f"Unknown command: {command}")
            print(self.color("Try: help", "muted"))
            return

        handler(args)

    def cmd_help(self, _: list[str]) -> None:
        rows = [
            self.command_row("status", "Show system modules and current theme"),
            self.command_row("run scan", "Run a sample progress workflow"),
            self.command_row("run build", "Run a second sample workflow"),
            self.command_row("theme", "List available themes"),
            self.command_row("theme ocean", "Switch theme: dark, ocean, amber"),
            self.command_row("diff", "Render a code-style diff block"),
            self.command_row("note <text>", "Store a quick in-memory note"),
            self.command_row("history", "Show commands used in this session"),
            self.command_row("clear", "Redraw the screen"),
            self.command_row("exit", "Close the app"),
        ]
        self.write_panel("Commands", rows)

    def command_row(self, command: str, detail: str) -> str:
        return f"{self.color(command.ljust(16), 'accent_2', bold=True)} {self.color(detail, 'fg')}"

    def cmd_status(self, _: list[str]) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        rows = [
            f"{self.color('Theme'.ljust(14), 'muted')} {self.color(self.theme.name, 'accent', bold=True)}",
            f"{self.color('Session'.ljust(14), 'muted')} {self.color('interactive', 'success')}",
            f"{self.color('Clock'.ljust(14), 'muted')} {self.color(now, 'fg')}",
            f"{self.color('Commands'.ljust(14), 'muted')} {self.color(str(len(self.commands)), 'accent_2')}",
            f"{self.color('Notes'.ljust(14), 'muted')} {self.color(str(len(self.notes)), 'accent_2')}",
        ]
        self.write_panel("Status", rows)

    def cmd_run(self, args: list[str]) -> None:
        task = args[0].lower() if args else "scan"
        workflows = {
            "scan": [
                "Indexing command modules",
                "Checking local config",
                "Rendering terminal panels",
                "Validating command router",
                "Writing session summary",
            ],
            "build": [
                "Bundling CLI entrypoint",
                "Preparing assets",
                "Compiling command map",
                "Running smoke checks",
                "Ready",
            ],
            "deploy": [
                "Packaging release",
                "Uploading artifact",
                "Switching active version",
                "Checking health endpoint",
                "Deployment complete",
            ],
        }
        steps = workflows.get(task)

        if steps is None:
            self.error(f"Unknown workflow: {task}")
            print(self.color("Available workflows: scan, build, deploy", "muted"))
            return

        print()
        print(self.color(f"Running workflow: {task}", "accent", bold=True))
        total = len(steps)

        for index, label in enumerate(steps, start=1):
            percent = int(index / total * 100)
            filled = int(percent / 4)
            bar = "#" * filled + "-" * (25 - filled)
            print(
                "\r"
                + self.color("[", "muted")
                + self.color(bar[:filled], "success")
                + self.color(bar[filled:], "muted")
                + self.color("]", "muted")
                + f" {percent:3d}% "
                + self.color(label.ljust(32), "fg"),
                end="",
                flush=True,
            )
            time.sleep(0.28)

        print()
        print(self.color("Done.", "success", bold=True))

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
            self.write_panel("Themes", rows, footer="Use: theme dark | theme ocean | theme amber")
            return

        name = args[0].lower()
        next_theme = THEMES.get(name)

        if next_theme is None:
            self.error(f"Unknown theme: {name}")
            return

        self.theme = next_theme
        clear()
        self.render_banner()
        print(self.color(f"Theme switched to {name}.", "success", bold=True))

    def cmd_diff(self, _: list[str]) -> None:
        rows = [
            self.color("1  function greet() {", "accent_2"),
            self.color('2-   console.log("Hello, World!");', "danger", bg="panel_alt"),
            self.color('2+   console.log("Hello, Command Lab!");', "success", bg="panel_alt"),
            self.color("3  }", "accent_2"),
        ]
        self.write_panel("Syntax Preview", rows, footer="This block is only a visual demo.")

    def cmd_note(self, args: list[str]) -> None:
        if not args:
            if not self.notes:
                print(self.color("No notes yet.", "muted"))
                return

            rows = [f"{index}. {note}" for index, note in enumerate(self.notes, start=1)]
            self.write_panel("Notes", rows)
            return

        note = " ".join(args)
        self.notes.append(note)
        print(self.color("Saved note: ", "success", bold=True) + self.color(note, "fg"))

    def cmd_history(self, _: list[str]) -> None:
        if not self.history:
            print(self.color("No history yet.", "muted"))
            return

        rows = [f"{index:02d}. {item}" for index, item in enumerate(self.history[-12:], start=1)]
        self.write_panel("History", rows)

    def cmd_about(self, _: list[str]) -> None:
        rows = [
            "Command Lab is a small local prototype for an interactive CLI/TUI.",
            "It is dependency-free, so it can run on this machine immediately.",
            "The command map is in terminal_ui.py and each command is a Python method.",
        ]
        self.write_panel("About", rows)

    def cmd_clear(self, _: list[str]) -> None:
        self.boot()

    def cmd_exit(self, _: list[str]) -> None:
        self.running = False
        print(self.color("Closed Command Lab.", "muted"))

    def error(self, message: str) -> None:
        print(self.color("Error: ", "danger", bold=True) + self.color(message, "fg"))


def main() -> int:
    enable_ansi()
    app = CommandLab()
    app.loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
