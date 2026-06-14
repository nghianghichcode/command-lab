# Command Lab

Small local prototype for an interactive command terminal.

## User install flow

This is the command style users normally run after you publish the installer online:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/nghianghichcode/command-lab/main/install-online.ps1 | iex"
```

If this command returns `404 Not Found`, GitHub cannot find the installer file at that URL yet.

The installer downloads the zip, installs the app, adds the command to PATH, and opens the window once.

After that, they can open a new terminal and run:

```bat
cmdlab
```

Open it in a new Windows Terminal tab/window:

```bat
cmdlab-window
```

## How to publish it

Create a zip package:

```powershell
powershell -ExecutionPolicy Bypass -File .\make-package.ps1
```

Or publish everything through GitHub CLI:

```powershell
powershell -ExecutionPolicy Bypass -File .\publish-github.ps1
```

Upload this file somewhere public:

```txt
dist\command-lab.zip
```

The installer is already configured to download from:

```txt
https://github.com/nghianghichcode/command-lab/releases/latest/download/command-lab.zip
```

If your repository name is not `command-lab`, replace `command-lab` in both GitHub URLs with the real repository name.

Upload `install-online.ps1` to the root of the same repository. The user-facing command is:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/nghianghichcode/command-lab/main/install-online.ps1 | iex"
```

## Fix irm 404

Check these items before sharing the install command:

```txt
1. The GitHub repo exists:
   https://github.com/nghianghichcode/command-lab

2. The repo is Public.

3. install-online.ps1 is uploaded at the repo root, not inside a folder.

4. The branch is main.
   If the branch is master, use this instead:
   https://raw.githubusercontent.com/nghianghichcode/command-lab/master/install-online.ps1

5. The release asset exists with this exact filename:
   command-lab.zip
```

Test the installer URL directly in a browser:

```txt
https://raw.githubusercontent.com/nghianghichcode/command-lab/main/install-online.ps1
```

If the browser shows the script text, `irm` will work. If the browser shows `404`, the URL/repo/branch/file path is still wrong.

## Local install

If the files are already on the machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-command.ps1
```

Then open a new terminal and run `cmdlab` or `cmdlab-window`.

## Local run

```bat
run.cmd
```

Useful commands:

```txt
help
status
run scan
run build
theme ocean
theme amber
diff
note your text here
history
clear
exit
```

This version uses only Python standard library and ANSI terminal colors, so it can run without installing packages.
