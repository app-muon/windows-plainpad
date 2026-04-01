# windows-plainpad v2.0

A minimal Windows Notepad replacement written in Python and Tkinter. No network connections, no AI, no telemetry — just a plain text editor.

## Features

- Multiple tabs — open as many documents as you like simultaneously
- File operations: New, New Tab, Open, Save, Save As, Close Tab (UTF-8 encoding)
- Atomic saves — writes to a temp file first, so the original is never lost if a save fails
- Prompts to save unsaved changes on close tab, New, Open, and Exit (per tab)
- Undo / Redo (independent per tab)
- Cut, Copy, Paste, Select All
- Inline Find bar (not a modal) with Next / Previous and Match Case toggle (per tab)
- Resizable window with scrollbars
- Zoom in/out with Ctrl+Scroll
- Keyboard shortcuts:

| Action        | Shortcut           |
|---------------|--------------------|
| New           | Ctrl+N             |
| New Tab       | Ctrl+T             |
| Open          | Ctrl+O             |
| Save          | Ctrl+S             |
| Save As       | Ctrl+Shift+S       |
| Close Tab     | Ctrl+W             |
| Undo          | Ctrl+Z             |
| Redo          | Ctrl+Y             |
| Find          | Ctrl+F             |
| Next tab      | Ctrl+Tab           |
| Previous tab  | Ctrl+Shift+Tab     |
| Zoom in/out   | Ctrl+Scroll        |

## Just want to use it?

Download `plainpad.exe` from this page and double-click it. No installation needed.

---

## Running or building from source

These steps are for developers who want to run the Python script directly or build their own `.exe`.

### What you need

- **Python 3** — download from [python.org](https://www.python.org/downloads/). During installation, tick the box that says **"Add Python to PATH"**.

### Running directly (no .exe needed)

1. Download `plainpad.py` and `build.bat` from this page and save them to the same folder
2. Open a Command Prompt in that folder (type `cmd` into the File Explorer address bar and press Enter)
3. Run:
   ```
   python plainpad.py
   ```

### Building a standalone plainpad.exe

This produces a single `.exe` file you can share with others — they won't need Python installed.

1. Download `plainpad.py` and `build.bat` from this page and save them to the same folder
2. Open a Command Prompt in that folder (type `cmd` into the File Explorer address bar and press Enter)
3. Install PyInstaller by running:
   ```
   pip install pyinstaller
   ```
4. Run the build script:
   ```
   build.bat
   ```
5. When it finishes, the file will be at `dist\plainpad.exe`
