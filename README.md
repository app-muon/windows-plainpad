# windows-plainpad v2.0

A minimal Windows Notepad replacement written in Python and Tkinter. No network connections, no AI, no telemetry, just a plain text editor with a lightweight markdown preview mode.

## Features

- Multiple tabs so you can work with several documents at once
- New tab `+` button in the tab strip
- File operations: New, New Tab, Open, Save, Save As, Close Tab
- Recent Files menu with persistent history and one-click reopen
- Atomic saves using a temporary file first, so the original is not lost if save fails
- Save prompts for unsaved changes on close tab, New, Open, and Exit
- Undo / Redo per tab
- Cut, Copy, Paste, Select All
- Inline Find bar with Next / Previous and Match Case
- Fixed-width editing font
- Markdown source / preview mode with a bottom-right view toggle
- Markdown preview supports headings `#` through `######`, lists, block quotes, inline code, fenced code blocks, and aligned pipe tables
- Resizable window with scrollbars
- Zoom in/out with Ctrl+Scroll
- UTF-8 text files

- Keyboard shortcuts:

| Action         | Shortcut       |
|----------------|----------------|
| New            | Ctrl+N         |
| New Tab        | Ctrl+T         |
| Open           | Ctrl+O         |
| Save           | Ctrl+S         |
| Save As        | F12            |
| Close Tab      | Ctrl+W         |
| Undo           | Ctrl+Z         |
| Redo           | Ctrl+Y         |
| Find           | Ctrl+F         |
| Toggle Preview | F6             |
| Source View    | Alt+1          |
| Preview View   | Alt+2          |
| Next Tab       | Ctrl+Tab       |
| Previous Tab   | Ctrl+Shift+Tab |
| Zoom In/Out    | Ctrl+Scroll    |

## Just want to use it?

Download `plainpad.exe` from this page and double-click it. No installation needed.

---

## Running or building from source

These steps are for developers who want to run the Python script directly or build their own `.exe`.

### What you need

- **Python 3**: download from [python.org](https://www.python.org/downloads/). During installation, tick the box that says **"Add Python to PATH"**.

### Running directly

1. Download `plainpad.py` and `build.bat` from this page and save them to the same folder.
2. Open a Command Prompt in that folder.
3. Run:

```text
python plainpad.py
```

To open a file directly at launch, pass the path as the first argument:

```text
python plainpad.py "C:\path\to\file.md"
```

### Building a standalone plainpad.exe

This produces a single `.exe` file you can share with others. They will not need Python installed.

1. Download `plainpad.py` and `build.bat` from this page and save them to the same folder.
2. Open a Command Prompt in that folder.
3. Install PyInstaller:

```text
pip install pyinstaller
```

4. Run the build script:

```text
build.bat
```

5. When it finishes, the file will be at `dist\plainpad.exe`.

You can also launch the built app with a file path:

```text
plainpad.exe "C:\path\to\file.md"
```
