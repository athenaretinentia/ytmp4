#!/usr/bin/env python3
"""
ytmp4 — YouTube to MP4 Converter
A sleek dark-themed GUI for downloading YouTube videos as MP4 files.
"""

import os, re, subprocess, shutil, threading, queue, shlex
from tkinter import *
from tkinter import ttk, messagebox

# ─── Auto-detect yt-dlp ──────────────────────────────────────
YTLP = None
for candidate in [
    "/opt/homebrew/bin/yt-dlp",
    "/usr/local/bin/yt-dlp",
    "/usr/local/bin/yt-dlp",
    shutil.which("yt-dlp"),
]:
    if candidate and os.path.isfile(candidate):
        YTLP = candidate
        break

if not YTLP:
    # Last resort — try pip-installed location
    for home in [os.path.expanduser("~")]:
        p = os.path.join(home, "Library", "Python", "3.9", "bin", "yt-dlp")
        if os.path.isfile(p):
            YTLP = p
            break

DESKTOP = os.path.expanduser("~/Desktop")

# ─── Colour Palette ───────────────────────────────────────────
C = {
    "bg":         "#0a0a0a",
    "surface":    "#141414",
    "card":       "#1a1a1a",
    "border":     "#2a2a2a",
    "border_focus": "#00ff88",
    "text":       "#f0f0f0",
    "text_dim":   "#666666",
    "accent":     "#00ff88",
    "accent_dim": "#00cc6a",
    "accent_bg":  "#00ff8815",
    "error":      "#ff4466",
    "success":    "#00ff88",
    "log_text":   "#888888",
    "list_bg":    "#121212",
    "scroll_bg":  "#1a1a1a",
    "scroll_fg":  "#333333",
}

FONT = "Helvetica Neue"
FONT_MONO = "SF Mono"


class Ytmp4Converter:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("720x700")
        self.root.minsize(620, 580)
        self.root.configure(bg=C["bg"])
        self.root.overrideredirect(True)

        self.urls = []
        self.downloading = False
        self.log_q = queue.Queue()
        self.status_q = queue.Queue()
        self._drag_data = {"x": 0, "y": 0}

        self._setup_styles()
        self._build_ui()
        self._poll_queues()

    # ── Styles ──────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=C["bg"], foreground=C["text"], font=(FONT, 11))

        s.configure("Accent.TButton",
            background=C["accent"], foreground=C["bg"],
            font=(FONT, 13, "bold"), borderwidth=0, focusthickness=0,
            padding=(20, 10))
        s.map("Accent.TButton",
            background=[("active", "#22ff99"), ("disabled", "#333")],
            foreground=[("disabled", "#555")])

        s.configure("Small.TButton",
            background=C["card"], foreground=C["text_dim"],
            font=(FONT, 10), borderwidth=0, focusthickness=0,
            padding=(10, 5))
        s.map("Small.TButton",
            background=[("active", C["border"]), ("disabled", C["card"])],
            foreground=[("active", C["text"]), ("disabled", "#444")])

        s.configure("Dark.TEntry",
            fieldbackground=C["card"], foreground=C["text"],
            font=(FONT, 13), borderwidth=0, padding=(12, 8))

        s.configure("Dark.Horizontal.TProgressbar",
            background=C["accent"], troughcolor=C["card"],
            borderwidth=0, thickness=4)

        s.configure("Dark.Vertical.TScrollbar",
            background=C["scroll_fg"], troughcolor=C["scroll_bg"],
            borderwidth=0, width=8, arrowsize=0)

    # ── Build UI ────────────────────────────────────────────
    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = Frame(self.root, bg=C["border"], padx=1, pady=1)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        inner = Frame(outer, bg=C["bg"], padx=28, pady=24)
        inner.grid(row=0, column=0, sticky="nsew")
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(2, weight=1)

        # ── Title Bar ──
        title_bar = Frame(inner, bg=C["bg"], height=36, cursor="fleur")
        title_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        title_bar.columnconfigure(1, weight=1)
        title_bar.bind("<Button-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._drag)

        dots = Frame(title_bar, bg=C["bg"])
        dots.grid(row=0, column=0, padx=(0, 14))
        for color, cmd in [("#ff5f56", self._close), ("#ffbd2e", self._minimize),
                            ("#27c93f", self._maximize)]:
            d = Frame(dots, width=12, height=12, bg=color, highlightthickness=0)
            d.pack(side=LEFT, padx=3)
            d.pack_propagate(False)
            d.bind("<Button-1>", lambda e, c=cmd: c())

        title_frame = Frame(title_bar, bg=C["bg"])
        title_frame.grid(row=0, column=1, sticky="w")
        Label(title_frame, text="▶", fg=C["accent"], bg=C["bg"],
              font=(FONT, 16, "bold")).pack(side=LEFT, padx=(0, 8))
        Label(title_frame, text="ytmp4", fg=C["text"],
              bg=C["bg"], font=(FONT, 14, "bold")).pack(side=LEFT)

        # ── Input ──
        input_card = Frame(inner, bg=C["card"], padx=14, pady=14)
        input_card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        input_card.columnconfigure(0, weight=1)

        Label(input_card, text="YouTube URL", fg=C["text_dim"],
              bg=C["card"], font=(FONT, 9, "bold"), anchor="w").grid(
                  row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        entry_row = Frame(input_card, bg=C["card"])
        entry_row.grid(row=1, column=0, columnspan=2, sticky="ew")
        entry_row.columnconfigure(0, weight=1)

        self.url_var = StringVar()
        self.url_entry = ttk.Entry(entry_row, textvariable=self.url_var,
                                    style="Dark.TEntry")
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.insert(0, "https://youtube.com/watch?v=...")
        self.url_entry.config(foreground=C["text_dim"])
        self.url_entry.bind("<FocusIn>", self._on_focus_in)
        self.url_entry.bind("<FocusOut>", self._on_focus_out)
        self.url_entry.bind("<Return>", lambda e: self._add_url())

        add_btn = ttk.Button(entry_row, text="+  ADD", style="Accent.TButton",
                              command=self._add_url)
        add_btn.grid(row=0, column=2)

        # ── URL List ──
        list_card = Frame(inner, bg=C["card"], padx=14, pady=14)
        list_card.grid(row=2, column=0, sticky="nsew", pady=(0, 14))
        list_card.columnconfigure(0, weight=1)
        list_card.rowconfigure(1, weight=1)

        list_hdr = Frame(list_card, bg=C["card"])
        list_hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        list_hdr.columnconfigure(0, weight=1)

        self.count_lbl = Label(list_hdr, text="No URLs added", fg=C["text_dim"],
                                bg=C["card"], font=(FONT, 9, "bold"))
        self.count_lbl.grid(row=0, column=0, sticky="w")

        btn_r = Frame(list_hdr, bg=C["card"])
        btn_r.grid(row=0, column=1)
        ttk.Button(btn_r, text="✕ Remove", style="Small.TButton",
                    command=self._remove_selected).pack(side=LEFT, padx=(0, 4))
        ttk.Button(btn_r, text="Clear All", style="Small.TButton",
                    command=self._clear_urls).pack(side=LEFT)

        list_c = Frame(list_card, bg=C["list_bg"],
                       highlightbackground=C["border"], highlightthickness=1)
        list_c.grid(row=1, column=0, sticky="nsew")
        list_c.columnconfigure(0, weight=1)
        list_c.rowconfigure(0, weight=1)

        self.listbox = Listbox(list_c,
            bg=C["list_bg"], fg=C["text"], selectbackground=C["accent_dim"],
            selectforeground=C["bg"], font=(FONT, 11), borderwidth=0,
            highlightthickness=0, activestyle="none", relief="flat")
        self.listbox.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(list_c, orient="vertical", style="Dark.Vertical.TScrollbar",
                            command=self.listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=sb.set)

        # ── Bottom ──
        bottom = Frame(inner, bg=C["bg"])
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.progress_var = DoubleVar()
        self.progress = ttk.Progressbar(bottom, variable=self.progress_var,
                                         style="Dark.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        self.progress.grid_remove()

        status_row = Frame(bottom, bg=C["bg"])
        status_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        status_row.columnconfigure(0, weight=1)

        self.status_lbl = Label(status_row, text="Ready", fg=C["text_dim"],
                                 bg=C["bg"], font=(FONT, 10))
        self.status_lbl.grid(row=0, column=0, sticky="w")
        self.dl_btn = ttk.Button(status_row, text="⬇  DOWNLOAD ALL",
                                  style="Accent.TButton", command=self._start_download)
        self.dl_btn.grid(row=0, column=1, padx=(12, 0))

        log_card = Frame(bottom, bg=C["card"], padx=14, pady=10)
        log_card.grid(row=2, column=0, columnspan=3, sticky="ew")
        log_card.columnconfigure(0, weight=1)

        Label(log_card, text="Log", fg=C["text_dim"], bg=C["card"],
              font=(FONT, 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))

        log_c = Frame(log_card, bg=C["list_bg"],
                      highlightbackground=C["border"], highlightthickness=1)
        log_c.grid(row=1, column=0, sticky="ew")
        log_c.columnconfigure(0, weight=1)

        self.log_text = Text(log_c,
            bg=C["list_bg"], fg=C["log_text"],
            font=((FONT_MONO if FONT_MONO else FONT), 10),
            borderwidth=0, highlightthickness=0, state="disabled",
            wrap="word", height=5, padx=8, pady=6)
        self.log_text.grid(row=0, column=0, sticky="ew")

        log_sb = ttk.Scrollbar(log_c, orient="vertical",
                                style="Dark.Vertical.TScrollbar",
                                command=self.log_text.yview)
        log_sb.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_sb.set)

    # ── Title Bar Drag ──
    def _start_drag(self, e):
        self._drag_data["x"] = e.x
        self._drag_data["y"] = e.y

    def _drag(self, e):
        x = self.root.winfo_x() + e.x - self._drag_data["x"]
        y = self.root.winfo_y() + e.y - self._drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def _close(self):
        self.root.destroy()

    def _minimize(self):
        self.root.iconify()

    def _maximize(self):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    # ── Entry Handlers ──
    def _on_focus_in(self, e):
        if self.url_var.get() == "https://youtube.com/watch?v=...":
            self.url_var.set("")
            self.url_entry.config(foreground=C["text"])

    def _on_focus_out(self, e):
        if not self.url_var.get():
            self.url_entry.insert(0, "https://youtube.com/watch?v=...")
            self.url_entry.config(foreground=C["text_dim"])

    # ── URL Management ──
    def _is_valid_url(self, u):
        return "youtube.com" in u or "youtu.be" in u

    def _add_url(self):
        url = self.url_var.get().strip()
        if not url or url == "https://youtube.com/watch?v=...":
            return
        if not self._is_valid_url(url):
            self._log("Not a valid YouTube URL", C["error"])
            self.url_var.set("")
            return
        if url in self.urls:
            self._log("URL already in list", C["error"])
            self.url_var.set("")
            return
        self.urls.append(url)
        display = url if len(url) < 65 else url[:62] + "..."
        self.listbox.insert(END, "  " + display)
        self._update_count()
        self.url_var.set("")
        self._log(f"Added: {url}", C["success"])

    def _remove_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        for i in reversed(sel):
            self.listbox.delete(i)
            del self.urls[i]
        self._update_count()

    def _clear_urls(self):
        self.listbox.delete(0, END)
        self.urls.clear()
        self._update_count()
        self._log("Cleared all URLs", C["text_dim"])

    def _update_count(self):
        n = len(self.urls)
        self.count_lbl.config(text=f"{n} URL{'s' if n != 1 else ''} added" if n else "No URLs added")

    # ── Logging ──
    def _log(self, msg, color=C["log_text"]):
        self.log_q.put((msg, color))

    def _write_log(self, msg, color):
        self.log_text.config(state="normal")
        tag = f"tag_{id(msg)}"
        self.log_text.tag_configure(tag, foreground=color)
        self.log_text.insert(END, "  " + msg + "\n", tag)
        self.log_text.see(END)
        self.log_text.config(state="disabled")

    def _poll_queues(self):
        try:
            while True:
                m, c = self.log_q.get_nowait()
                self._write_log(m, c)
        except queue.Empty:
            pass
        try:
            while True:
                s = self.status_q.get_nowait()
                self.status_lbl.config(text=s)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queues)

    # ── Download Logic ──
    def _start_download(self):
        if not self.urls:
            messagebox.showwarning("", "Add at least one YouTube URL first.")
            return
        if self.downloading:
            return
        self.downloading = True
        self.dl_btn.config(text="⬇  DOWNLOADING...", state="disabled")
        self.progress.grid()
        self.progress.start(10)
        self._log("─" * 32, C["accent"])
        self._log("Starting downloads", C["accent"])
        self.status_lbl.config(text="Downloading...")
        threading.Thread(target=self._download_all, daemon=True).start()

    def _download_all(self):
        downloaded = []
        cwd = os.getcwd()
        os.chdir(DESKTOP)
        try:
            for i, url in enumerate(self.urls, 1):
                self.status_q.put(f"[{i}/{len(self.urls)}] Downloading...")
                self.log_q.put((f"[{i}/{len(self.urls)}] {url}", "#ffffff"))
                fname = self._dl_one(url)
                if fname:
                    downloaded.append(fname)
                    self.log_q.put((f"  ✓  {fname}", C["success"]))
                else:
                    self.log_q.put(("  ✗  Failed", C["error"]))

            if not downloaded:
                self.log_q.put(("No files downloaded.", C["error"]))
                self.status_q.put("Failed")
                return

            if len(downloaded) > 1:
                fn = "YouTube Downloads"
                c = 1
                while os.path.exists(os.path.join(DESKTOP, fn)):
                    c += 1
                    fn = f"YouTube Downloads {c}"
                fp = os.path.join(DESKTOP, fn)
                os.makedirs(fp, exist_ok=True)
                for f in downloaded:
                    shutil.move(os.path.join(DESKTOP, f), os.path.join(fp, f))
                self.log_q.put((f"─" * 32, C["accent"]))
                self.log_q.put((f"Moved {len(downloaded)} files -> ~/Desktop/{fn}/", C["accent"]))
                self.status_q.put(f"Done — {fn}")
            else:
                self.log_q.put((f"─" * 32, C["accent"]))
                self.log_q.put(("Saved to Desktop", C["accent"]))
                self.status_q.put("Done ✓")
        finally:
            os.chdir(cwd)
            self.root.after(0, self._finish)

    def _dl_one(self, url):
        try:
            r = subprocess.run(
                [YTLP, "--print", "after_move:filename",
                 "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
                 "--merge-output-format", "mp4",
                 url, "--simulate"],
                capture_output=True, text=True, timeout=15
            )
            predicted = r.stdout.strip().split("\n")[0] if r.stdout.strip() else None
        except:
            predicted = None

        cmd = [
            YTLP,
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]",
            "--merge-output-format", "mp4",
            "--no-overwrites",
            url
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            output = result.stdout + result.stderr
            if result.returncode != 0 and "has already been" not in output:
                err_line = [l for l in output.strip().split("\n") if l][-1]
                self.log_q.put((f"  Error: {err_line}", C["error"]))
                return None

            filename = None
            for line in output.split("\n"):
                if "[Merger]" in line and "Merging formats into" in line:
                    for p in line.split('"'):
                        p = p.strip()
                        if p.endswith(".mp4") and os.path.exists(p):
                            filename = p
                            break
                    if not filename:
                        raw = line.split("into ")[-1].strip().strip("'\"")
                        if raw.endswith(".mp4") and os.path.exists(raw):
                            filename = raw
                if filename:
                    break

            if not filename and predicted and os.path.exists(predicted):
                filename = predicted
            if not filename:
                mp4s = [f for f in os.listdir(DESKTOP)
                        if f.endswith(".mp4") and os.path.isfile(os.path.join(DESKTOP, f))]
                if mp4s:
                    filename = max(mp4s, key=lambda f: os.path.getctime(os.path.join(DESKTOP, f)))
            if filename and os.path.exists(filename):
                return os.path.basename(filename)
            return None
        except subprocess.TimeoutExpired:
            self.log_q.put(("  Timed out (10 min)", C["error"]))
            return None
        except Exception as e:
            self.log_q.put((f"  Exception: {e}", C["error"]))
            return None

    def _finish(self):
        self.downloading = False
        self.progress.stop()
        self.progress.grid_remove()
        self.progress_var.set(0)
        self.dl_btn.config(text="⬇  DOWNLOAD ALL", state="normal")


if __name__ == "__main__":
    root = Tk()
    app = Ytmp4Converter(root)
    root.mainloop()
