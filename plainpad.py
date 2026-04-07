import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
import json
import os
import re
import tempfile

__version__ = "2.0"


class Document:
    """State for a single tab/document."""

    def __init__(self, text_widget, preview_widget, find_frame, find_var, case_var):
        self.text = text_widget
        self.preview = preview_widget
        self.find_frame = find_frame
        self.find_var = find_var
        self.case_var = case_var
        self.file_path = None
        self.modified = False
        self.find_visible = False
        self.view_mode = "source"
        self.preview_after_id = None

    @property
    def display_name(self):
        name = os.path.basename(self.file_path) if self.file_path else "Untitled"
        return ("* " if self.modified else "") + name


class Notepad:
    def __init__(self, root):
        self.root = root
        self.root.title("Notepad")
        self.root.geometry("800x600")

        self.docs = []       # list of Document
        self.active = None   # current Document
        self._recent_files_limit = 10
        self._recent_files_path = self._get_recent_files_path()
        self._recent_files = []
        self._color_presets = {
            "Black on White": {
                "text_fg": "#111111",
                "text_bg": "#ffffff",
                "preview_fg": "#111111",
                "preview_bg": "#fcfcfc",
                "quote_fg": "#555555",
                "code_bg": "#f2f2f2",
                "selection_bg": "#cfe8ff",
                "selection_fg": "#111111",
                "cursor": "#111111",
                "found_bg": "#ffe066",
                "found_fg": "#111111",
            },
            "Dark Mode": {
                "text_fg": "#f2f2f2",
                "text_bg": "#1e1e1e",
                "preview_fg": "#f2f2f2",
                "preview_bg": "#252526",
                "quote_fg": "#b8b8b8",
                "code_bg": "#333333",
                "selection_bg": "#3d6ea8",
                "selection_fg": "#ffffff",
                "cursor": "#f2f2f2",
                "found_bg": "#8a6d1f",
                "found_fg": "#ffffff",
            },
            "Sepia": {
                "text_fg": "#3d2f1f",
                "text_bg": "#f4ecd8",
                "preview_fg": "#3d2f1f",
                "preview_bg": "#efe5cf",
                "quote_fg": "#74624c",
                "code_bg": "#e5d7bb",
                "selection_bg": "#d3ba86",
                "selection_fg": "#2f2417",
                "cursor": "#3d2f1f",
                "found_bg": "#f0c36d",
                "found_fg": "#2f2417",
            },
            "Slate": {
                "text_fg": "#e8eef5",
                "text_bg": "#2f3b4c",
                "preview_fg": "#e8eef5",
                "preview_bg": "#354255",
                "quote_fg": "#c0cbd8",
                "code_bg": "#435268",
                "selection_bg": "#6887aa",
                "selection_fg": "#ffffff",
                "cursor": "#e8eef5",
                "found_bg": "#d9a441",
                "found_fg": "#18202b",
            },
            "Terminal": {
                "text_fg": "#8af78e",
                "text_bg": "#081b12",
                "preview_fg": "#8af78e",
                "preview_bg": "#0d2418",
                "quote_fg": "#6fd087",
                "code_bg": "#143325",
                "selection_bg": "#1f5c41",
                "selection_fg": "#d7ffe0",
                "cursor": "#8af78e",
                "found_bg": "#335f1d",
                "found_fg": "#d7ffe0",
            },
        }
        self._color_scheme_var = tk.StringVar(value="Black on White")

        self._zoom_size = 11
        self._font = tkfont.Font(font=tkfont.nametofont("TkFixedFont"))
        self._font.configure(size=self._zoom_size)
        self._ui_font = tkfont.Font(font=tkfont.nametofont("TkDefaultFont"))
        self._preview_fonts = {
            "body": tkfont.Font(font=self._ui_font),
            "heading1": tkfont.Font(font=self._ui_font),
            "heading2": tkfont.Font(font=self._ui_font),
            "heading3": tkfont.Font(font=self._ui_font),
            "bold": tkfont.Font(font=self._ui_font),
            "italic": tkfont.Font(font=self._ui_font),
            "bold_italic": tkfont.Font(font=self._ui_font),
            "code": tkfont.Font(font=self._font),
        }
        self._preview_fonts["body"].configure(size=self._zoom_size)
        self._preview_fonts["heading1"].configure(size=self._zoom_size + 8, weight="bold")
        self._preview_fonts["heading2"].configure(size=self._zoom_size + 5, weight="bold")
        self._preview_fonts["heading3"].configure(size=self._zoom_size + 2, weight="bold")
        self._preview_fonts["bold"].configure(size=self._zoom_size, weight="bold")
        self._preview_fonts["italic"].configure(size=self._zoom_size, slant="italic")
        self._preview_fonts["bold_italic"].configure(size=self._zoom_size, weight="bold", slant="italic")

        self._build_menu()
        self._build_tab_bar()
        self._build_content_area()
        self._bind_shortcuts()
        self._load_recent_files()
        self._refresh_recent_menu()

        self.new_tab()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu = file_menu
        file_menu.add_command(label="New",         accelerator="Ctrl+N",       command=self.new_file)
        file_menu.add_command(label="New Tab",     accelerator="Ctrl+T",       command=self.new_tab)
        file_menu.add_command(label="Open...",     accelerator="Ctrl+O",       command=self.open_file)
        self._recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self._recent_menu)
        file_menu.add_command(label="Save",        accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...",  accelerator="F12",    command=self.save_as)
        file_menu.add_command(label="Close Tab",   accelerator="Ctrl+W", command=self.close_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_app)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo",       accelerator="Ctrl+Z", command=self._undo)
        edit_menu.add_command(label="Redo",       accelerator="Ctrl+Y", command=self._redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut",        accelerator="Ctrl+X", command=self._cut)
        edit_menu.add_command(label="Copy",       accelerator="Ctrl+C", command=self._copy)
        edit_menu.add_command(label="Paste",      accelerator="Ctrl+V", command=self._paste)
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self._select_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="Find...",    accelerator="Ctrl+F", command=self.toggle_find_bar)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Source View", accelerator="Alt+1", command=lambda: self._set_view_mode(self.active, "source"))
        view_menu.add_command(label="Preview",     accelerator="Alt+2", command=lambda: self._set_view_mode(self.active, "preview"))
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Preview", accelerator="F6", command=self.toggle_preview)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    def _build_tab_bar(self):
        self.tab_bar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self.tab_bar.pack(side=tk.TOP, fill=tk.X)

        # Scrollable inner frame for tab buttons
        self.tabs_inner = tk.Frame(self.tab_bar)
        self.tabs_inner.pack(side=tk.LEFT)

        self._tab_buttons = {}  # doc -> (frame, label)

        tk.Button(
            self.tab_bar, text="+", width=3,
            command=self.new_tab, relief=tk.FLAT, font=("TkFixedFont", 12), padx=4, pady=1
        ).pack(side=tk.LEFT, padx=2, pady=0)

    def _build_content_area(self):
        """Container that holds whichever text+findbar is active."""
        self.content = tk.Frame(self.root)
        self.content.pack(fill=tk.BOTH, expand=True)

        self.status_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        color_picker = tk.Frame(self.status_bar)
        color_picker.pack(side=tk.LEFT, padx=4, pady=2)
        self._color_menu = tk.OptionMenu(
            color_picker,
            self._color_scheme_var,
            *self._color_presets.keys(),
            command=lambda _choice: self._apply_color_scheme(),
        )
        self._color_menu.config(width=16)
        self._color_menu.pack(side=tk.LEFT)

        mode_switch = tk.Frame(self.status_bar)
        mode_switch.pack(side=tk.RIGHT, padx=4, pady=2)
        self._source_btn = tk.Button(mode_switch, text="Source", relief=tk.SUNKEN, command=lambda: self._set_view_mode(self.active, "source"))
        self._source_btn.pack(side=tk.LEFT, padx=(0, 2))
        self._preview_btn = tk.Button(mode_switch, text="Preview", relief=tk.FLAT, command=lambda: self._set_view_mode(self.active, "preview"))
        self._preview_btn.pack(side=tk.LEFT)

    def _make_doc_widgets(self):
        """Create the text area and find bar widgets for a new document."""
        outer = tk.Frame(self.content)

        # Find bar (packed at bottom when visible)
        find_frame = tk.Frame(outer, bd=1, relief=tk.RAISED)
        find_var = tk.StringVar()
        case_var = tk.BooleanVar(value=False)

        tk.Label(find_frame, text="Find:").pack(side=tk.LEFT, padx=(4, 2))
        find_entry = tk.Entry(find_frame, textvariable=find_var, width=30)
        find_entry.pack(side=tk.LEFT, padx=2)

        # Text area
        stack = tk.Frame(outer)
        stack.pack(fill=tk.BOTH, expand=True)

        text_frame = tk.Frame(stack)
        text_frame.pack(fill=tk.BOTH, expand=True)

        yscroll = tk.Scrollbar(text_frame)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(text_frame, undo=True, wrap=tk.NONE, yscrollcommand=yscroll.set, font=self._font)
        text.pack(fill=tk.BOTH, expand=True)
        yscroll.config(command=text.yview)

        xscroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text.xview)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        text.config(xscrollcommand=xscroll.set)

        preview_frame = tk.Frame(stack)
        preview_yscroll = tk.Scrollbar(preview_frame)
        preview_yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        preview = tk.Text(
            preview_frame,
            wrap=tk.WORD,
            yscrollcommand=preview_yscroll.set,
            font=self._preview_fonts["body"],
            state=tk.DISABLED,
            padx=16,
            pady=12,
            relief=tk.FLAT,
        )
        preview.pack(fill=tk.BOTH, expand=True)
        preview_yscroll.config(command=preview.yview)

        doc = Document(text, preview, find_frame, find_var, case_var)
        doc._outer_frame = outer
        doc._stack = stack
        doc._text_frame = text_frame
        doc._preview_frame = preview_frame
        doc._find_entry = find_entry

        # Wire up find bar buttons
        tk.Button(find_frame, text="Next",
                  command=lambda d=doc: self._find(d, forward=True)).pack(side=tk.LEFT, padx=2)
        tk.Button(find_frame, text="Previous",
                  command=lambda d=doc: self._find(d, forward=False)).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(find_frame, text="Match case", variable=case_var).pack(side=tk.LEFT, padx=4)
        tk.Button(find_frame, text="✕",
                  command=lambda d=doc: self._hide_find(d), relief=tk.FLAT).pack(side=tk.RIGHT, padx=4)

        find_entry.bind("<Return>", lambda e, d=doc: self._find(d, forward=True))
        find_entry.bind("<Escape>", lambda e, d=doc: self._hide_find(d))

        text.bind("<<Modified>>", lambda e, d=doc: self._on_modified(d))
        text.bind("<Control-MouseWheel>", self._zoom)
        preview.bind("<Control-MouseWheel>", self._zoom)
        preview.bind("<1>", lambda e, d=doc: self._focus_visible_widget(d))

        self._configure_preview_tags(preview)
        self._apply_colors_to_doc(doc)

        return doc

    def _current_color_scheme(self):
        return self._color_presets[self._color_scheme_var.get()]

    def _apply_color_scheme(self):
        for doc in self.docs:
            self._apply_colors_to_doc(doc)

    def _apply_colors_to_doc(self, doc):
        colors = self._current_color_scheme()
        doc.text.config(
            foreground=colors["text_fg"],
            background=colors["text_bg"],
            insertbackground=colors["cursor"],
            selectbackground=colors["selection_bg"],
            selectforeground=colors["selection_fg"],
        )
        doc.preview.config(
            foreground=colors["preview_fg"],
            background=colors["preview_bg"],
            insertbackground=colors["cursor"],
            selectbackground=colors["selection_bg"],
            selectforeground=colors["selection_fg"],
        )
        doc.text.tag_config("found", background=colors["found_bg"], foreground=colors["found_fg"])
        self._configure_preview_tags(doc.preview)

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def new_tab(self, file_path=None, content=None):
        doc = self._make_doc_widgets()
        self.docs.append(doc)

        if file_path:
            doc.file_path = file_path
        if content is not None:
            doc.text.insert("1.0", content)
            doc.text.edit_reset()

        self._add_tab_button(doc)
        self._apply_doc_file_type(doc)
        self._switch_to(doc)
        return doc

    def _add_tab_button(self, doc):
        frame = tk.Frame(self.tabs_inner, bd=1, relief=tk.RAISED)
        frame.pack(side=tk.LEFT, padx=1, pady=1)

        lbl = tk.Label(frame, text=doc.display_name, padx=6)
        lbl.pack(side=tk.LEFT)

        close_btn = tk.Button(frame, text="×", relief=tk.FLAT, padx=2,
                              command=lambda d=doc: self.close_tab(d))
        close_btn.config(text="x", padx=4, pady=1, font=("TkDefaultFont", 11))
        close_btn.pack(side=tk.LEFT)

        lbl.bind("<Button-1>", lambda e, d=doc: self._switch_to(d))
        frame.bind("<Button-1>", lambda e, d=doc: self._switch_to(d))

        self._tab_buttons[id(doc)] = (frame, lbl)

    def _switch_to(self, doc):
        if self.active and self.active is not doc:
            # Hide current doc
            self.active._outer_frame.pack_forget()
            self._set_tab_style(self.active, active=False)

        self.active = doc
        doc._outer_frame.pack(fill=tk.BOTH, expand=True)
        self._sync_view_mode(doc)
        self._set_tab_style(doc, active=True)
        self._update_title()
        self._focus_visible_widget(doc)

    def _set_tab_style(self, doc, active):
        entry = self._tab_buttons.get(id(doc))
        if not entry:
            return
        frame, lbl = entry
        bg = "#d0e8ff" if active else self.root.cget("bg")
        frame.config(bg=bg)
        lbl.config(bg=bg, text=doc.display_name)

    def _refresh_tab_label(self, doc):
        entry = self._tab_buttons.get(id(doc))
        if entry:
            _, lbl = entry
            lbl.config(text=doc.display_name)

    def close_tab(self, doc=None):
        if doc is None:
            doc = self.active
        if doc is None:
            return
        if not self._check_save(doc):
            return

        idx = self.docs.index(doc)
        self.docs.remove(doc)
        if doc.preview_after_id:
            try:
                self.root.after_cancel(doc.preview_after_id)
            except tk.TclError:
                pass

        # Remove tab button
        entry = self._tab_buttons.pop(id(doc), None)
        if entry:
            entry[0].destroy()

        doc._outer_frame.destroy()

        if not self.docs:
            self.new_tab()
            return

        # Switch to adjacent tab
        new_idx = min(idx, len(self.docs) - 1)
        self.active = None
        self._switch_to(self.docs[new_idx])

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def new_file(self):
        """Replace the active tab with a blank document."""
        doc = self.active
        if not self._check_save(doc):
            return
        doc.text.delete("1.0", tk.END)
        doc.text.edit_reset()
        doc.file_path = None
        doc.modified = False
        self._set_view_mode(doc, "source")
        self._refresh_tab_label(doc)
        self._update_title()

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if not path:
            return
        self._open_path(path)

    def _open_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")
            return

        # Reuse active tab if it's an unmodified Untitled
        doc = self.active
        if doc.file_path is None and not doc.modified and doc.text.get("1.0", "end-1c") == "":
            doc.text.delete("1.0", tk.END)
            doc.text.insert("1.0", content)
            doc.text.edit_reset()
            doc.file_path = path
            doc.modified = False
            self._apply_doc_file_type(doc)
            self._refresh_tab_label(doc)
            self._update_title()
        else:
            self.new_tab(file_path=path, content=content)
        self._add_recent_file(path)

    def save_file(self):
        doc = self.active
        if doc.file_path:
            return self._write_file(doc, doc.file_path)
        return self.save_as()

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
        )
        if not path:
            return False
        return self._write_file(self.active, path)

    def _write_file(self, doc, path):
        try:
            content = doc.text.get("1.0", "end-1c")
            dir_ = os.path.dirname(os.path.abspath(path))
            fd, tmp_path = tempfile.mkstemp(dir=dir_)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")
            return False
        doc.file_path = path
        doc.modified = False
        self._apply_doc_file_type(doc)
        self._add_recent_file(path)
        self._refresh_tab_label(doc)
        self._update_title()
        return True

    def _check_save(self, doc):
        if not doc.modified:
            return True
        name = os.path.basename(doc.file_path) if doc.file_path else "Untitled"
        result = messagebox.askyesnocancel("Notepad", f"Do you want to save changes to {name}?")
        if result is True:
            return self._write_file(doc, doc.file_path) if doc.file_path else self.save_as()
        elif result is False:
            return True
        return False

    def exit_app(self):
        for doc in list(self.docs):
            self._switch_to(doc)
            if not self._check_save(doc):
                return
        self.root.destroy()

    # ------------------------------------------------------------------
    # Title
    # ------------------------------------------------------------------

    def _update_title(self):
        if self.active:
            suffix = " [Preview]" if self.active.view_mode == "preview" else ""
            self.root.title(f"{self.active.display_name}{suffix} - Notepad")

    def _on_modified(self, doc):
        if doc.text.edit_modified():
            doc.modified = True
            doc.text.edit_modified(False)
            self._schedule_preview_refresh(doc)
            self._refresh_tab_label(doc)
            if doc is self.active:
                self._update_title()

    # ------------------------------------------------------------------
    # Edit commands
    # ------------------------------------------------------------------

    def _undo(self):
        if self.active.view_mode == "preview":
            return
        try:
            self.active.text.edit_undo()
        except tk.TclError:
            pass

    def _redo(self):
        if self.active.view_mode == "preview":
            return
        try:
            self.active.text.edit_redo()
        except tk.TclError:
            pass

    def _cut(self):
        if self.active.view_mode == "preview":
            return
        self.active.text.event_generate("<<Cut>>")

    def _copy(self):
        self._active_edit_widget().event_generate("<<Copy>>")

    def _paste(self):
        if self.active.view_mode == "preview":
            return
        self.active.text.event_generate("<<Paste>>")

    def _select_all(self):
        widget = self._active_edit_widget()
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, tk.END)

    # ------------------------------------------------------------------
    # Find bar
    # ------------------------------------------------------------------

    def toggle_find_bar(self):
        doc = self.active
        if doc.find_visible:
            self._hide_find(doc)
        else:
            self._show_find(doc)

    def _show_find(self, doc):
        doc.find_frame.pack(side=tk.BOTTOM, fill=tk.X, in_=doc._outer_frame)
        doc.find_visible = True
        doc._find_entry.focus_set()
        try:
            sel = doc.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if sel and "\n" not in sel:
                doc.find_var.set(sel)
        except tk.TclError:
            pass
        doc._find_entry.select_range(0, tk.END)

    def _hide_find(self, doc):
        doc.find_frame.pack_forget()
        doc.find_visible = False
        doc.text.tag_remove("found", "1.0", tk.END)
        self._focus_visible_widget(doc)

    def _find(self, doc, forward=True):
        query = doc.find_var.get()
        if not query:
            return

        doc.text.tag_remove("found", "1.0", tk.END)
        colors = self._current_color_scheme()
        doc.text.tag_config("found", background=colors["found_bg"], foreground=colors["found_fg"])
        nocase = not doc.case_var.get()

        try:
            start = doc.text.index(tk.SEL_FIRST if forward else tk.SEL_LAST)
        except tk.TclError:
            start = doc.text.index(tk.INSERT)

        if forward:
            pos = doc.text.search(query, f"{start}+1c", tk.END, nocase=nocase)
            if not pos:
                pos = doc.text.search(query, "1.0", tk.END, nocase=nocase)
        else:
            pos = doc.text.search(query, start, "1.0", nocase=nocase, backwards=True)
            if not pos:
                pos = doc.text.search(query, tk.END, "1.0", nocase=nocase, backwards=True)

        if pos:
            end = f"{pos}+{len(query)}c"
            doc.text.tag_add("found", pos, end)
            doc.text.mark_set(tk.INSERT, pos)
            doc.text.see(pos)
            doc.text.tag_add(tk.SEL, pos, end)
            try:
                doc.text.tag_remove(tk.SEL, "1.0", pos)
                doc.text.tag_remove(tk.SEL, end, tk.END)
            except tk.TclError:
                pass
        else:
            messagebox.showinfo("Find", f'"{query}" not found.')

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _bind_shortcuts(self):
        r = self.root
        r.bind("<Control-n>",         lambda e: self.new_file())
        r.bind("<Control-N>",         lambda e: self.new_file())
        r.bind("<Control-t>",         lambda e: self.new_tab())
        r.bind("<Control-T>",         lambda e: self.new_tab())
        r.bind("<Control-o>",         lambda e: self.open_file())
        r.bind("<Control-O>",         lambda e: self.open_file())
        r.bind("<Control-s>",         lambda e: self.save_file())
        r.bind("<Control-S>",         lambda e: self.save_as())
        r.bind("<F12>",               lambda e: self.save_as())
        r.bind("<Control-w>",         lambda e: self.close_tab())
        r.bind("<Control-W>",         lambda e: self.close_tab())
        r.bind("<Control-f>",         lambda e: self.toggle_find_bar())
        r.bind("<Control-F>",         lambda e: self.toggle_find_bar())
        r.bind("<F6>",                lambda e: self.toggle_preview())
        r.bind("<Alt-1>",             lambda e: self._set_view_mode(self.active, "source"))
        r.bind("<Alt-2>",             lambda e: self._set_view_mode(self.active, "preview"))
        r.bind("<Control-Tab>",       lambda e: self._next_tab())
        r.bind("<Control-Shift-Tab>", lambda e: self._prev_tab())
        r.protocol("WM_DELETE_WINDOW", self.exit_app)

    def _zoom(self, event):
        step = 1 if event.delta > 0 else -1
        new_size = self._zoom_size + step
        if 6 <= new_size <= 72:
            self._zoom_size = new_size
            self._font.configure(size=self._zoom_size)
            self._preview_fonts["body"].configure(size=self._zoom_size)
            self._preview_fonts["heading1"].configure(size=self._zoom_size + 8)
            self._preview_fonts["heading2"].configure(size=self._zoom_size + 5)
            self._preview_fonts["heading3"].configure(size=self._zoom_size + 2)
            self._preview_fonts["bold"].configure(size=self._zoom_size)
            self._preview_fonts["italic"].configure(size=self._zoom_size)
            self._preview_fonts["bold_italic"].configure(size=self._zoom_size)
            self._preview_fonts["code"].configure(size=self._zoom_size)
        return "break"

    def toggle_preview(self):
        if not self.active:
            return
        mode = "source" if self.active.view_mode == "preview" else "preview"
        self._set_view_mode(self.active, mode)

    def _set_view_mode(self, doc, mode):
        if not doc or mode not in ("source", "preview"):
            return
        doc.view_mode = mode
        if mode == "preview":
            self._refresh_markdown_preview(doc)
        if doc is self.active:
            self._sync_view_mode(doc)
            self._update_title()
            self._focus_visible_widget(doc)

    def _sync_view_mode(self, doc):
        if doc.view_mode == "preview":
            doc._text_frame.pack_forget()
            doc._preview_frame.pack(fill=tk.BOTH, expand=True)
            self._source_btn.config(relief=tk.FLAT)
            self._preview_btn.config(relief=tk.SUNKEN)
        else:
            doc._preview_frame.pack_forget()
            doc._text_frame.pack(fill=tk.BOTH, expand=True)
            self._source_btn.config(relief=tk.SUNKEN)
            self._preview_btn.config(relief=tk.FLAT)

    def _focus_visible_widget(self, doc):
        if doc.view_mode == "preview":
            doc.preview.focus_set()
        else:
            doc.text.focus_set()

    def _active_edit_widget(self):
        if self.active and self.active.view_mode == "preview":
            return self.active.preview
        return self.active.text

    def _apply_doc_file_type(self, doc):
        if not doc:
            return
        if self._is_markdown_path(doc.file_path):
            self._schedule_preview_refresh(doc)

    def _is_markdown_path(self, path):
        if not path:
            return False
        return os.path.splitext(path)[1].lower() in (".md", ".markdown")

    def _schedule_preview_refresh(self, doc):
        if doc.preview_after_id:
            try:
                self.root.after_cancel(doc.preview_after_id)
            except tk.TclError:
                pass
        doc.preview_after_id = self.root.after(150, lambda d=doc: self._refresh_markdown_preview(d))

    def _refresh_markdown_preview(self, doc):
        if doc.preview_after_id:
            try:
                self.root.after_cancel(doc.preview_after_id)
            except tk.TclError:
                pass
            doc.preview_after_id = None

        preview = doc.preview
        source = doc.text.get("1.0", "end-1c")
        preview.config(state=tk.NORMAL)
        preview.delete("1.0", tk.END)

        in_code_block = False
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                preview.insert(tk.END, "\n")
                continue

            if in_code_block:
                self._append_preview_line(preview, line, block_tag="codeblock")
                continue

            heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                self._append_preview_line(preview, heading_match.group(2), block_tag=f"heading{level}")
                continue

            quote_match = re.match(r"^\s*>\s?(.*)$", line)
            if quote_match:
                self._append_preview_line(preview, quote_match.group(1), block_tag="blockquote")
                continue

            bullet_match = re.match(r"^(\s*)([-*+])\s+(.*)$", line)
            if bullet_match:
                indent = "  " * (len(bullet_match.group(1)) // 2)
                self._append_preview_line(preview, f"{indent}• {bullet_match.group(3)}", block_tag="list")
                continue

            ordered_match = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
            if ordered_match:
                indent = "  " * (len(ordered_match.group(1)) // 2)
                self._append_preview_line(preview, f"{indent}{ordered_match.group(2)}. {ordered_match.group(3)}", block_tag="list")
                continue

            self._append_preview_line(preview, line)

        preview.config(state=tk.DISABLED)

    def _append_preview_line(self, preview, text, block_tag=None):
        if block_tag in ("codeblock", "table"):
            preview.insert(tk.END, text, (block_tag,))
        else:
            line_start = preview.index(tk.END)
            self._insert_markdown_inline(preview, text)
            if block_tag:
                line_end = preview.index(tk.END)
                preview.tag_add(block_tag, line_start, line_end)
        preview.insert(tk.END, "\n")

    def _insert_markdown_inline(self, preview, text):
        pattern = re.compile(
            r"`([^`]+)`"
            r"|\*\*\*([^*\n]+)\*\*\*"
            r"|___([^_\n]+)___"
            r"|\*\*([^*\n]+)\*\*"
            r"|__([^_\n]+)__"
            r"|\*([^*\n]+)\*"
            r"|_([^_\n]+)_"
        )

        pos = 0
        for match in pattern.finditer(text):
            if match.start() > pos:
                preview.insert(tk.END, text[pos:match.start()])

            if match.group(1) is not None:
                preview.insert(tk.END, match.group(1), ("inline_code",))
            elif match.group(2) is not None:
                preview.insert(tk.END, match.group(2), ("bold_italic",))
            elif match.group(3) is not None:
                preview.insert(tk.END, match.group(3), ("bold_italic",))
            elif match.group(4) is not None:
                preview.insert(tk.END, match.group(4), ("bold",))
            elif match.group(5) is not None:
                preview.insert(tk.END, match.group(5), ("bold",))
            elif match.group(6) is not None:
                preview.insert(tk.END, match.group(6), ("italic",))
            elif match.group(7) is not None:
                preview.insert(tk.END, match.group(7), ("italic",))

            pos = match.end()

        if pos < len(text):
            preview.insert(tk.END, text[pos:])

    def _configure_preview_tags(self, preview):
        colors = self._current_color_scheme()
        preview.tag_config("heading1", font=self._preview_fonts["heading1"], spacing1=6, spacing3=8)
        preview.tag_config("heading2", font=self._preview_fonts["heading2"], spacing1=5, spacing3=7)
        preview.tag_config("heading3", font=self._preview_fonts["heading3"], spacing1=4, spacing3=6)
        preview.tag_config("blockquote", lmargin1=18, lmargin2=18, foreground=colors["quote_fg"], spacing3=3)
        preview.tag_config("list", lmargin1=12, lmargin2=24, spacing3=2)
        preview.tag_config("codeblock", font=self._preview_fonts["code"], background=colors["code_bg"], lmargin1=12, lmargin2=12, spacing1=3, spacing3=3)
        preview.tag_config("inline_code", font=self._preview_fonts["code"], background=colors["code_bg"])
        preview.tag_config("bold", font=self._preview_fonts["bold"])
        preview.tag_config("italic", font=self._preview_fonts["italic"])
        preview.tag_config("bold_italic", font=self._preview_fonts["bold_italic"])

    def _refresh_markdown_preview(self, doc):
        if doc.preview_after_id:
            try:
                self.root.after_cancel(doc.preview_after_id)
            except tk.TclError:
                pass
            doc.preview_after_id = None

        preview = doc.preview
        source = doc.text.get("1.0", "end-1c")
        preview.config(state=tk.NORMAL)
        preview.delete("1.0", tk.END)

        in_code_block = False
        lines = source.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                preview.insert(tk.END, "\n")
                i += 1
                continue

            if in_code_block:
                self._append_preview_line(preview, line, block_tag="codeblock")
                i += 1
                continue

            if (
                i + 1 < len(lines)
                and self._looks_like_table_row(line)
                and self._is_table_separator(lines[i + 1])
            ):
                table_lines = [line]
                i += 2
                while i < len(lines) and self._looks_like_table_row(lines[i]) and lines[i].strip():
                    table_lines.append(lines[i])
                    i += 1
                self._render_table(preview, table_lines)
                continue

            heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                self._append_preview_line(preview, heading_match.group(2), block_tag=f"heading{level}")
                i += 1
                continue

            quote_match = re.match(r"^\s*>\s?(.*)$", line)
            if quote_match:
                self._append_preview_line(preview, quote_match.group(1), block_tag="blockquote")
                i += 1
                continue

            bullet_match = re.match(r"^(\s*)([-*+])\s+(.*)$", line)
            if bullet_match:
                indent = "  " * (len(bullet_match.group(1)) // 2)
                self._append_preview_line(preview, f"{indent}* {bullet_match.group(3)}", block_tag="list")
                i += 1
                continue

            ordered_match = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
            if ordered_match:
                indent = "  " * (len(ordered_match.group(1)) // 2)
                self._append_preview_line(preview, f"{indent}{ordered_match.group(2)}. {ordered_match.group(3)}", block_tag="list")
                i += 1
                continue

            self._append_preview_line(preview, line)
            i += 1

        preview.config(state=tk.DISABLED)

    def _configure_preview_tags(self, preview):
        colors = self._current_color_scheme()
        preview.tag_config("heading1", font=self._preview_fonts["heading1"], spacing1=6, spacing3=8)
        preview.tag_config("heading2", font=self._preview_fonts["heading2"], spacing1=5, spacing3=7)
        preview.tag_config("heading3", font=self._preview_fonts["heading3"], spacing1=4, spacing3=6)
        preview.tag_config("blockquote", lmargin1=18, lmargin2=18, foreground=colors["quote_fg"], spacing3=3)
        preview.tag_config("list", lmargin1=12, lmargin2=24, spacing3=2)
        preview.tag_config("codeblock", font=self._preview_fonts["code"], background=colors["code_bg"], lmargin1=12, lmargin2=12, spacing1=3, spacing3=3)
        preview.tag_config("inline_code", font=self._preview_fonts["code"], background=colors["code_bg"])
        preview.tag_config("table", font=self._preview_fonts["code"], spacing1=2, spacing3=2)
        preview.tag_config("bold", font=self._preview_fonts["bold"])
        preview.tag_config("italic", font=self._preview_fonts["italic"])
        preview.tag_config("bold_italic", font=self._preview_fonts["bold_italic"])

    def _looks_like_table_row(self, line):
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

    def _is_table_separator(self, line):
        if not self._looks_like_table_row(line):
            return False
        cells = self._split_table_row(line)
        if not cells:
            return False
        return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)

    def _split_table_row(self, line):
        return [cell.strip() for cell in line.strip()[1:-1].split("|")]

    def _render_table(self, preview, table_lines):
        rows = [self._split_table_row(line) for line in table_lines]
        if not rows:
            return

        column_count = max(len(row) for row in rows)
        normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
        widths = [max(len(row[col]) for row in normalized_rows) for col in range(column_count)]

        self._append_preview_line(preview, self._format_table_row(normalized_rows[0], widths), block_tag="table")
        self._append_preview_line(preview, self._format_table_separator(widths), block_tag="table")
        for row in normalized_rows[1:]:
            self._append_preview_line(preview, self._format_table_row(row, widths), block_tag="table")
        preview.insert(tk.END, "\n")

    def _format_table_row(self, row, widths):
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    def _format_table_separator(self, widths):
        return "-+-".join("-" * width for width in widths)

    def _get_recent_files_path(self):
        appdata = os.getenv("APPDATA")
        if appdata:
            base_dir = os.path.join(appdata, "Plainpad")
        else:
            base_dir = os.path.join(os.path.expanduser("~"), ".plainpad")
        return os.path.join(base_dir, "recent_files.json")

    def _load_recent_files(self):
        try:
            with open(self._recent_files_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self._recent_files = []
            return
        except Exception:
            self._recent_files = []
            return

        if isinstance(data, list):
            self._recent_files = [
                path for path in data
                if isinstance(path, str) and path
            ][:self._recent_files_limit]
        else:
            self._recent_files = []

    def _save_recent_files(self):
        try:
            os.makedirs(os.path.dirname(self._recent_files_path), exist_ok=True)
            with open(self._recent_files_path, "w", encoding="utf-8") as f:
                json.dump(self._recent_files[:self._recent_files_limit], f, indent=2)
        except Exception:
            pass

    def _add_recent_file(self, path):
        norm_path = os.path.abspath(path)
        self._recent_files = [p for p in self._recent_files if os.path.abspath(p) != norm_path]
        self._recent_files.insert(0, norm_path)
        self._recent_files = self._recent_files[:self._recent_files_limit]
        self._save_recent_files()
        self._refresh_recent_menu()

    def _refresh_recent_menu(self):
        self._recent_menu.delete(0, tk.END)
        if not self._recent_files:
            self._recent_menu.add_command(label="(Empty)", state=tk.DISABLED)
            return

        for path in self._recent_files:
            self._recent_menu.add_command(
                label=path,
                command=lambda p=path: self._open_recent_file(p),
            )
        self._recent_menu.add_separator()
        self._recent_menu.add_command(label="Clear Recent Files", command=self._clear_recent_files)

    def _open_recent_file(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Error", f"File not found:\n{path}")
            self._recent_files = [p for p in self._recent_files if p != path]
            self._save_recent_files()
            self._refresh_recent_menu()
            return
        self._open_path(path)

    def _clear_recent_files(self):
        self._recent_files = []
        self._save_recent_files()
        self._refresh_recent_menu()

    def _next_tab(self):
        if len(self.docs) < 2:
            return
        idx = self.docs.index(self.active)
        self._switch_to(self.docs[(idx + 1) % len(self.docs)])

    def _prev_tab(self):
        if len(self.docs) < 2:
            return
        idx = self.docs.index(self.active)
        self._switch_to(self.docs[(idx - 1) % len(self.docs)])


def main():
    root = tk.Tk()
    app = Notepad(root)
    root.mainloop()


if __name__ == "__main__":
    main()
