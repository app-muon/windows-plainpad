import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont
import os
import tempfile

__version__ = "2.0"


class Document:
    """State for a single tab/document."""

    def __init__(self, text_widget, find_frame, find_var, case_var):
        self.text = text_widget
        self.find_frame = find_frame
        self.find_var = find_var
        self.case_var = case_var
        self.file_path = None
        self.modified = False
        self.find_visible = False

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

        self._zoom_size = 11
        self._font = tkfont.Font(font=tkfont.nametofont("TkDefaultFont"))
        self._font.configure(size=self._zoom_size)

        self._build_menu()
        self._build_tab_bar()
        self._build_content_area()
        self._bind_shortcuts()

        self.new_tab()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New",         accelerator="Ctrl+N",       command=self.new_file)
        file_menu.add_command(label="New Tab",     accelerator="Ctrl+T",       command=self.new_tab)
        file_menu.add_command(label="Open...",     accelerator="Ctrl+O",       command=self.open_file)
        file_menu.add_command(label="Save",        accelerator="Ctrl+S",       command=self.save_file)
        file_menu.add_command(label="Save As...",  accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_command(label="Close Tab",   accelerator="Ctrl+W",       command=self.close_tab)
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

        self.root.config(menu=menubar)

    def _build_tab_bar(self):
        self.tab_bar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self.tab_bar.pack(side=tk.TOP, fill=tk.X)

        # Scrollable inner frame for tab buttons
        self.tabs_inner = tk.Frame(self.tab_bar)
        self.tabs_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            self.tab_bar, text="+", width=2,
            command=self.new_tab, relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=2, pady=1)

        self._tab_buttons = {}  # doc -> (frame, label)

    def _build_content_area(self):
        """Container that holds whichever text+findbar is active."""
        self.content = tk.Frame(self.root)
        self.content.pack(fill=tk.BOTH, expand=True)

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
        text_frame = tk.Frame(outer)
        text_frame.pack(fill=tk.BOTH, expand=True)

        yscroll = tk.Scrollbar(text_frame)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(text_frame, undo=True, wrap=tk.NONE, yscrollcommand=yscroll.set, font=self._font)
        text.pack(fill=tk.BOTH, expand=True)
        yscroll.config(command=text.yview)

        xscroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text.xview)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        text.config(xscrollcommand=xscroll.set)

        doc = Document(text, find_frame, find_var, case_var)
        doc._outer_frame = outer
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

        return doc

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
        self._switch_to(doc)
        return doc

    def _add_tab_button(self, doc):
        frame = tk.Frame(self.tabs_inner, bd=1, relief=tk.RAISED)
        frame.pack(side=tk.LEFT, padx=1, pady=1)

        lbl = tk.Label(frame, text=doc.display_name, padx=6)
        lbl.pack(side=tk.LEFT)

        close_btn = tk.Button(frame, text="×", relief=tk.FLAT, padx=2,
                              command=lambda d=doc: self.close_tab(d))
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
        self._set_tab_style(doc, active=True)
        self._update_title()
        doc.text.focus_set()

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
        self._refresh_tab_label(doc)
        self._update_title()

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
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
            self._refresh_tab_label(doc)
            self._update_title()
        else:
            self.new_tab(file_path=path, content=content)

    def save_file(self):
        doc = self.active
        if doc.file_path:
            return self._write_file(doc, doc.file_path)
        return self.save_as()

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
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
            self.root.title(f"{self.active.display_name} - Notepad")

    def _on_modified(self, doc):
        if doc.text.edit_modified():
            doc.modified = True
            doc.text.edit_modified(False)
            self._refresh_tab_label(doc)
            if doc is self.active:
                self._update_title()

    # ------------------------------------------------------------------
    # Edit commands
    # ------------------------------------------------------------------

    def _undo(self):
        try:
            self.active.text.edit_undo()
        except tk.TclError:
            pass

    def _redo(self):
        try:
            self.active.text.edit_redo()
        except tk.TclError:
            pass

    def _cut(self):
        self.active.text.event_generate("<<Cut>>")

    def _copy(self):
        self.active.text.event_generate("<<Copy>>")

    def _paste(self):
        self.active.text.event_generate("<<Paste>>")

    def _select_all(self):
        self.active.text.tag_add(tk.SEL, "1.0", tk.END)
        self.active.text.mark_set(tk.INSERT, tk.END)

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
        doc.text.focus_set()

    def _find(self, doc, forward=True):
        query = doc.find_var.get()
        if not query:
            return

        doc.text.tag_remove("found", "1.0", tk.END)
        doc.text.tag_config("found", background="yellow")
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
        r.bind("<Control-w>",         lambda e: self.close_tab())
        r.bind("<Control-W>",         lambda e: self.close_tab())
        r.bind("<Control-f>",         lambda e: self.toggle_find_bar())
        r.bind("<Control-F>",         lambda e: self.toggle_find_bar())
        r.bind("<Control-Tab>",       lambda e: self._next_tab())
        r.bind("<Control-Shift-Tab>", lambda e: self._prev_tab())
        r.protocol("WM_DELETE_WINDOW", self.exit_app)

    def _zoom(self, event):
        step = 1 if event.delta > 0 else -1
        new_size = self._zoom_size + step
        if 6 <= new_size <= 72:
            self._zoom_size = new_size
            self._font.configure(size=self._zoom_size)
        return "break"

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
