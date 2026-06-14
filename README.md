# Nghia PC Toolkit

Interactive Windows terminal toolkit for quick diagnostics and safe maintenance.

## Install

User-facing one-line install command:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/nghianghichcode/command-lab/main/install-online.ps1 | iex"
```

The installer downloads the release zip, installs the app into `%LOCALAPPDATA%\NghiaPCToolkit`, adds the folder to the user `PATH`, and opens the tool once.

After installing, open a new terminal and run:

```bat
pctool
```

Open it in a new terminal window:

```bat
pctool-window
```

Legacy aliases are kept for old installs:

```bat
cmdlab
cmdlab-window
```

## Tools

```txt
dashboard          Quick health summary
system             OS, CPU, RAM, user, admin state
disk               Drive usage and free-space warnings
network            Local IP, DNS and connectivity checks
ports host port    TCP port check, for example: ports github.com 443
processes [n]      Top processes by memory
temp               Scan temp folders and estimate cleanable size
cleanup            Dry-run cleanup report
cleanup --apply    Delete temp files after typing DELETE
startup            List user startup-folder items
path               Show PATH entries
report             Save a desktop diagnostic report
theme              carbon, graphite, matrix
```

Cleanup is safe by default: it does not delete anything unless `cleanup --apply` is used and the user types `DELETE`.

## Publish

Build the bundled executable and release zip:

```powershell
powershell -ExecutionPolicy Bypass -File .\make-package.ps1
```

Publish source and release through GitHub CLI:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-github.ps1
```

The package includes `pctool.exe` and its `_internal` runtime folder, so users do not need Python installed.

The installer currently downloads:

```txt
https://github.com/nghianghichcode/command-lab/releases/latest/download/command-lab.zip?v=pctool-20260614
```

## Local Run

```bat
run.cmd
```

or:

```bat
python -B terminal_ui.py
```
