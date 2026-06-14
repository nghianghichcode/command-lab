<div align="center">

```
 _   _  ____ _   _ ___    _       ____   ____
| \ | |/ ___| | | |_ _|  / \     |  _ \ / ___|
|  \| | |  _| |_| || |  / _ \    | |_) | |
| |\  | |_| |  _  || | / ___ \   |  __/| |___
|_| \_|\____|_| |_|___/_/   \_\  |_|    \____|
```

# Nghia PC Toolkit

**Interactive Windows terminal toolkit — diagnostics, cleanup & system info at your fingertips.**

![Version](https://img.shields.io/badge/version-v0.4.0-56d364?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-0078d4?style=flat-square&logo=windows)
![Python](https://img.shields.io/badge/python-3.9%2B-3776ab?style=flat-square&logo=python)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

</div>

---

## ✨ Features

- 🖥️ **Arrow-key menu** — navigate with ↑/↓, no need to memorize commands
- 📊 **Dashboard** — instant summary: RAM, disk, network, junk files
- 🌐 **Network checks** — ping, DNS, TCP port testing
- 📡 **Wi-Fi** — interface info and saved profiles
- 🧹 **Safe cleanup** — temp & browser cache scanner with dry-run protection
- 🎨 **3 themes** — Carbon, Graphite, Matrix
- 📦 **No Python required** — ships as a single `.exe`

---

## ⚡ Install

**One-line install** (recommended):

```powershell
powershell -c "irm https://github.com/nghianghichcode/command-lab/raw/main/i.ps1|iex"
```

> Downloads the latest release, installs to `%LOCALAPPDATA%\NghiaPCToolkit`,  
> adds it to your user `PATH`, and launches the tool automatically.

**After installing**, open a new terminal and run:

```
pctool
```

Or open in its own window:

```
pctool-window
```

---

## 🧰 Commands

> The tool shows an **interactive menu** on startup — use arrow keys to navigate and Enter to select.  
> You can also type any command directly.

| Command | Description |
|---|---|
| `dashboard` | Quick health summary — RAM, disk, network, junk |
| `system` | OS, CPU, RAM, user, admin state |
| `disk` | Drive usage with free-space warnings |
| `network` | Local IP, DNS resolution, ping & port checks |
| `wifi` | Wi-Fi status and saved profile names |
| `wifi settings` | Open Windows Wi-Fi settings |
| `ports <host> <port>` | TCP connectivity test — e.g. `ports github.com 443` |
| `apps [name]` | Search installed Start Menu apps |
| `open <app>` | Open an app/folder/setting — e.g. `open chrome` |
| `processes [n]` | Top processes sorted by memory usage |
| `temp` / `junk` | Scan temp folders and browser caches |
| `cleanup` | Dry-run cleanup report (nothing deleted) |
| `cleanup --apply` | Delete temp/cache files after typing `DELETE` |
| `recycle --empty` | Empty Recycle Bin after typing `EMPTY` |
| `startup` | List user startup-folder items |
| `path` | Show all PATH entries |
| `report` | Save a full diagnostic report to Desktop |
| `theme` | Switch theme: `carbon`, `graphite`, `matrix` |
| `history` | Show recent commands |
| `clear` | Redraw the screen |
| `exit` | Close the tool |

> 🔒 **Cleanup is safe by default.** Nothing is deleted without `--apply` and explicit confirmation.

---

## 🎨 Themes

| Theme | Description |
|---|---|
| `carbon` | Dark blue — default |
| `graphite` | Warm amber |
| `matrix` | Green-on-black |

```
theme carbon
theme graphite
theme matrix
```

---

## 🛠️ Build & Publish

Build a standalone `.exe`:

```powershell
powershell -ExecutionPolicy Bypass -File .\make-package.ps1
```

Publish source + GitHub Release:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-github.ps1
```

Run directly without building:

```powershell
python -B terminal_ui.py
```

---

## 📋 Requirements

- Windows 10 / 11
- No Python needed when using the `.exe`
- Python 3.9+ if running from source

---

<div align="center">

Made with ❤️ by [nghianghichcode](https://github.com/nghianghichcode)

</div>
