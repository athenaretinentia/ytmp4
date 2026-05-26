#!/usr/bin/env python3
"""
ytmp4 — YouTube to MP4 Converter
Designed with intention. Every pixel matters.
"""

import os, re, subprocess, shutil, threading, queue
from tkinter import *
from tkinter import ttk, messagebox
import math, time

# ─── Auto-detect yt-dlp ──────────────────────────────────
YTLP = None
for c in ["/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp",
           shutil.which("yt-dlp")]:
    if c and os.path.isfile(c): YTLP = c; break
    if c and os.path.isfile(c): YTLP = c; break
    if c and os.path.isfile(c): YTLP = c; break
if not YTLP:
    h = os.path.expanduser("~")
    for p in [os.path.join(h,"Library","Python","3.9","bin","yt-dlp"),
              os.path.join(h,"Library","Python","3.10","bin","yt-dlp")]:
        if os.path.isfile(p): YTLP = p; break

DESKTOP = os.path.expanduser("~/Desktop")

# ─── Design Tokens ───────────────────────────────────────
class T:
    # Backgrounds
    bg          = "#0b0b0b"
    surface     = "#131313"
    card        = "#181818"
    card_hover  = "#1e1e1e"
    border      = "#222222"
    border_acc  = "#00ff88"
    border_sub  = "#2a2a2a"

    # Text
    text        = "#eeeeee"
    text_dim    = "#666666"
    text_muted  = "#444444"
    text_inv    = "#0b0b0b"

    # Accent
    accent      = "#00ff88"
    accent_dim  = "#00cc66"
    accent_sub  = "#00ff8820"
    accent_glow = "#00ff8820"

    # Feedback
    error       = "#ff3355"
    error_bg    = "#ff335512"
    success     = "#00ff88"
    success_bg  = "#00ff8810"
    warn        = "#ffaa00"

    # Misc
    scroll_track = "#181818"
    scroll_thumb = "#333333"

    # Sizing
    radius = 8
    radius_sm = 4
    pad = 24
    pad_sm = 12
    pad_xs = 8


class RoundedCanvas(Canvas):
    """Canvas wrapper with anti-aliased rounded rect support."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.config(highlightthickness=0, bd=0)

    def rrect(self, x1, y1, x2, y2, r=T.radius, **kw):
        points = []
        for i in range(0, 360, 3):
            t = math.radians(i)
            if i < 90:
                cx, cy = x2 - r, y1 + r
            elif i < 180:
                cx, cy = x2 - r, y2 - r
            elif i < 270:
                cx, cy = x1 + r, y2 - r
            else:
                cx, cy = x1 + r, y1 + r
            points.append(cx + r * math.cos(t))
            points.append(cy + r * math.sin(t))
        return self.create_polygon(points, smooth=True, **kw)


class Ytmp4Converter:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("760x760")
        self.root.minsize(640, 660)
        self.root.configure(bg=T.bg)
        self.root.overrideredirect(True)

        self.urls = []
        self.downloading = False
        self.log_q = queue.Queue()
        self.status_q = queue.Queue()
        self._drag = {"x": 0, "y": 0}
        self._anim_frame = 0
        self._hovered = set()

        self._build()
        self._poll()

    # ═══════════════════════════════════════════════════════
    #  BUILD
    # ═══════════════════════════════════════════════════════
    def _build(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Outer border glow
        outer = Frame(self.root, bg=T.border_acc, padx=1, pady=1)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        inner = Frame(outer, bg=T.bg, padx=0, pady=0)
        inner.grid(row=0, column=0, sticky="nsew")
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(2, weight=1)

        # ─── TITLE BAR ─────────────────────────────────────
        tb = Frame(inner, bg=T.surface, height=48, cursor="fleur")
        tb.grid(row=0, column=0, sticky="ew")
        tb.columnconfigure(1, weight=1)
        tb.bind("<Button-1>", self._drag_start)
        tb.bind("<B1-Motion>", self._drag_move)

        # Accent line under title bar
        acc_line = Frame(inner, bg=T.accent, height=1)
        acc_line.grid(row=1, column=0, sticky="ew")

        # Traffic lights
        dots = Frame(tb, bg=T.surface)
        dots.grid(row=0, column=0, padx=(16, 12))
        for color, cmd in [("#ff5f56", self._close), ("#ffbd2e", self._minimize),
                            ("#27c93f", self._maximize)]:
            d = Frame(dots, width=12, height=12, bg=color, highlightthickness=0)
            d.pack(side=LEFT, padx=3)
            d.pack_propagate(False)
            d.bind("<Button-1>", lambda e, c=cmd: c())

        # Logo + title
        tf = Frame(tb, bg=T.surface)
        tf.grid(row=0, column=1, sticky="w")
        # Play icon
        icon_c = RoundedCanvas(tf, width=28, height=28, bg=T.surface, bd=0)
        icon_c.pack(side=LEFT, padx=(0, 10))
        icon_c.rrect(2, 2, 26, 26, r=6, fill=T.accent_sub, outline="")
        icon_c.create_polygon(9, 6, 9, 22, 23, 14,
                              fill=T.accent, smooth=False)

        Label(tf, text="ytmp4", fg=T.text, bg=T.surface,
              font=("Helvetica Neue", 15, "bold")).pack(side=LEFT)
        Label(tf, text="converter", fg=T.text_dim, bg=T.surface,
              font=("Helvetica Neue", 15)).pack(side=LEFT)

        self.count_badge = Frame(tb, bg=T.accent, padx=6, pady=1)
        self.count_badge.grid(row=0, column=2, padx=(0, 16))
        self.count_lbl_tb = Label(self.count_badge, text="0", fg=T.text_inv,
                                   bg=T.accent, font=("Helvetica Neue", 10, "bold"))
        self.count_lbl_tb.pack()
        self._show_count(0)

        # ─── CONTENT ──────────────────────────────────────
        content = Frame(inner, bg=T.bg, padx=T.pad, pady=(T.pad, T.pad))
        content.grid(row=2, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)

        # ── SECTION: Input ──
        self._build_input(content)

        # ── SECTION: Queue ──
        self._build_queue(content)

        # ── SECTION: Bottom (progress + log) ──
        self._build_bottom(content)

    def _build_input(self, parent):
        sec = Frame(parent, bg=T.bg)
        sec.grid(row=0, column=0, sticky="ew", pady=(0, T.pad))
        sec.columnconfigure(1, weight=1)

        # Label
        Label(sec, text="Add videos", fg=T.text_dim, bg=T.bg,
              font=("Helvetica Neue", 9, "bold")).grid(
                  row=0, column=0, columnspan=3, sticky="sw", pady=(0, 8))

        # Search bar
        entry_card = Frame(sec, bg=T.card,
                           highlightbackground=T.border, highlightthickness=1,
                           padx=14, pady=0)
        entry_card.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 10))
        entry_card.columnconfigure(0, weight=1)

        self.url_var = StringVar()
        self.url_entry = Entry(entry_card, textvariable=self.url_var,
                                bg=T.card, fg=T.text_dim, bd=0,
                                font=("Helvetica Neue", 13),
                                insertbackground=T.accent, relief="flat")
        self.url_entry.grid(row=0, column=0, sticky="ew", ipady=10)
        self.url_entry.insert(0, "Paste a YouTube link...")
        self.url_entry.bind("<FocusIn>", self._in_focus)
        self.url_entry.bind("<FocusOut>", self._in_blur)
        self.url_entry.bind("<Return>", lambda e: self._add_url())

        add_btn = RoundedCanvas(sec, width=100, height=40, bg=T.bg, bd=0)
        add_btn.grid(row=1, column=2, sticky="e")
        add_btn.rrect(0, 0, 100, 40, r=T.radius, fill=T.accent, tags="bg")
        add_btn.create_text(50, 20, text="+ Add", fill=T.text_inv,
                            font=("Helvetica Neue", 12, "bold"), tags="txt")
        add_btn.bind("<Button-1>", lambda e: self._add_url())
        add_btn.bind("<Enter>", lambda e: add_btn.itemconfig("bg",
                      fill=T.accent_dim))
        add_btn.bind("<Leave>", lambda e: add_btn.itemconfig("bg", fill=T.accent))

        # Accent underline
        Frame(sec, bg=T.accent_sub, height=1).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))

    def _build_queue(self, parent):
        sec = Frame(parent, bg=T.bg)
        sec.grid(row=2, column=0, sticky="nsew", pady=(0, T.pad))
        sec.columnconfigure(0, weight=1)
        sec.rowconfigure(1, weight=1)

        # Header
        hdr = Frame(sec, bg=T.bg)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        hdr.columnconfigure(0, weight=1)

        Label(hdr, text="Queue", fg=T.text_dim, bg=T.bg,
              font=("Helvetica Neue", 9, "bold")).grid(row=0, column=0, sticky="w")

        btn_r = Frame(hdr, bg=T.bg)
        btn_r.grid(row=0, column=1)
        self._mk_small_btn(btn_r, "✕ Remove", self._remove_selected).pack(
            side=LEFT, padx=(0, 6))
        self._mk_small_btn(btn_r, "Clear", self._clear_urls).pack(side=LEFT)

        self._mk_small_btn = None  # prevent gc

        # List container
        lc = Frame(sec, bg=T.card,
                   highlightbackground=T.border, highlightthickness=1)
        lc.grid(row=1, column=0, sticky="nsew")
        lc.columnconfigure(0, weight=1)
        lc.rowconfigure(0, weight=1)

        self.listbox = Listbox(lc,
            bg=T.card, fg=T.text, selectbackground=T.accent + "40",
            selectforeground=T.text,
            font=("Helvetica Neue", 12), borderwidth=0,
            highlightthickness=0, activestyle="none", relief="flat")
        self.listbox.grid(row=0, column=0, sticky="nsew")

        sb = Scrollbar(lc, orient="vertical", bg=T.scroll_track,
                        troughcolor=T.scroll_track,
                        activebackground=T.accent, bd=0, highlightthickness=0)
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=sb.set)
        sb.config(command=self.listbox.yview)

    def _build_bottom(self, parent):
        sec = Frame(parent, bg=T.bg)
        sec.grid(row=3, column=0, sticky="ew")
        sec.columnconfigure(0, weight=1)

        # Progress bar
        prog_c = RoundedCanvas(sec, height=4, bg=T.bg, bd=0)
        prog_c.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        prog_c.rrect(0, 0, 760, 4, r=2, fill=T.card, tags="track")
        prog_c.rrect(0, 0, 0, 4, r=2, fill=T.accent, tags="bar")
        prog_c.itemconfig("track", state="hidden")
        prog_c.itemconfig("bar", state="hidden")
        self.prog_c = prog_c
        self.prog_width = 0

        # Status row
        sr = Frame(sec, bg=T.bg)
        sr.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, T.pad_sm))
        sr.columnconfigure(0, weight=1)

        self.status_lbl = Label(sr, text="Ready", fg=T.text_muted,
                                 bg=T.bg, font=("Helvetica Neue", 10))
        self.status_lbl.grid(row=0, column=0, sticky="w")

        self.dl_btn_c = RoundedCanvas(sr, width=180, height=44, bg=T.bg, bd=0)
        self.dl_btn_c.grid(row=0, column=1)
        self.dl_btn_c.rrect(0, 0, 180, 44, r=T.radius, fill=T.accent, tags="bg")
        self.dl_btn_c.create_text(90, 22, text="⬇  Download All", fill=T.text_inv,
                                   font=("Helvetica Neue", 12, "bold"), tags="txt")
        self.dl_btn_c.bind("<Button-1>", lambda e: self._start_download())
        self.dl_btn_c.bind("<Enter>", lambda e: self._btn_over())
        self.dl_btn_c.bind("<Leave>", lambda e: self._btn_out())

        # Log
        log_card = Frame(sec, bg=T.card, padx=14, pady=10)
        log_card.grid(row=2, column=0, columnspan=3, sticky="ew")
        log_card.columnconfigure(0, weight=1)

        Label(log_card, text="Activity", fg=T.text_dim, bg=T.card,
              font=("Helvetica Neue", 8, "bold")).grid(
                  row=0, column=0, sticky="w", pady=(0, 6))

        lc = Frame(log_card, bg=T.bg,
                   highlightbackground=T.border, highlightthickness=1)
        lc.grid(row=1, column=0, sticky="ew")
        lc.columnconfigure(0, weight=1)

        self.log_text = Text(lc,
            bg=T.bg, fg=T.text_muted,
            font=("SF Mono", 9),
            borderwidth=0, highlightthickness=0, state="disabled",
            wrap="word", height=5, padx=10, pady=8)
        self.log_text.grid(row=0, column=0, sticky="ew")

        lsb = Scrollbar(lc, orient="vertical", bg=T.scroll_track,
                         troughcolor=T.scroll_track,
                         activebackground=T.accent, bd=0, highlightthickness=0)
        lsb.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=lsb.set)
        lsb.config(command=self.log_text.yview)

    # ─── Helpers ──────────────────────────────────────────
    def _mk_small_btn(self, parent, text, cmd):
        c = RoundedCanvas(parent, width=72, height=28, bg=T.bg, bd=0)
        c.rrect(0, 0, 72, 28, r=T.radius_sm, fill=T.card, tags="bg")
        c.create_text(36, 14, text=text, fill=T.text_dim,
                      font=("Helvetica Neue", 9), tags="txt")
        c.bind("<Button-1>", lambda e: cmd())
        c.bind("<Enter>", lambda e: c.itemconfig("bg", fill=T.card_hover))
        c.bind("<Leave>", lambda e: c.itemconfig("bg", fill=T.card))
        self._mk_small_btn = c
        return c

    def _show_count(self, n):
        txt = str(n) if n else ""
        self.count_lbl_tb.config(text=txt)
        if n:
            self.count_badge.pack(side=RIGHT, padx=(0, 16))
        else:
            self.count_badge.pack_forget()

    # ─── Drag ─────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag["x"] = e.x; self._drag["y"] = e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._drag["x"]
        y = self.root.winfo_y() + e.y - self._drag["y"]
        self.root.geometry(f"+{x}+{y}")

    def _close(self): self.root.destroy()
    def _minimize(self): self.root.iconify()
    def _maximize(self):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    # ─── Input ────────────────────────────────────────────
    def _in_focus(self, e):
        if self.url_var.get() == "Paste a YouTube link...":
            self.url_var.set("")
            self.url_entry.config(fg=T.text)

    def _in_blur(self, e):
        if not self.url_var.get():
            self.url_entry.insert(0, "Paste a YouTube link...")
            self.url_entry.config(fg=T.text_dim)

    def _is_url(self, u):
        return "youtube.com" in u or "youtu.be" in u

    def _add_url(self):
        url = self.url_var.get().strip()
        if not url or url == "Paste a YouTube link...":
            return
        if not self._is_url(url):
            self._log("Not a valid YouTube URL", T.error)
            self.url_var.set("")
            return
        if url in self.urls:
            self._log("Already in queue", T.warn)
            self.url_var.set("")
            return
        self.urls.append(url)
        display = url if len(url) < 60 else url[:57] + "..."
        self.listbox.insert(END, f"  {display}")
        self._show_count(len(self.urls))
        self.url_var.set("")
        self._log("Added to queue", T.accent)

    def _remove_selected(self):
        sel = self.listbox.curselection()
        if not sel: return
        for i in reversed(sel): self.listbox.delete(i); del self.urls[i]
        self._show_count(len(self.urls))

    def _clear_urls(self):
        self.listbox.delete(0, END); self.urls.clear()
        self._show_count(0); self._log("Queue cleared", T.text_muted)

    # ─── Log ──────────────────────────────────────────────
    def _log(self, msg, color=T.text_muted):
        self.log_q.put((msg, color))

    def _poll(self):
        try:
            while True:
                m, c = self.log_q.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert(END, "  " + m + "\n")
                self.log_text.see(END)
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        try:
            while True:
                s = self.status_q.get_nowait()
                self.status_lbl.config(text=s)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    # ─── Button ──────────────────────────────────────────
    def _btn_over(self):
        self.dl_btn_c.itemconfig("bg", fill=T.accent_dim)

    def _btn_out(self):
        if not self.downloading:
            self.dl_btn_c.itemconfig("bg", fill=T.accent)

    # ─── Download ─────────────────────────────────────────
    def _start_download(self):
        if not self.urls:
            messagebox.showwarning("", "Add at least one YouTube URL first.")
            return
        if self.downloading: return
        self.downloading = True
        self.dl_btn_c.itemconfig("bg", fill=T.text_muted)
        self.dl_btn_c.itemconfig("txt", text="⬇  Downloading...")
        self.prog_c.itemconfig("track", state="normal")
        self.prog_c.itemconfig("bar", state="normal")
        self.prog_width = self.prog_c.winfo_width() or 700
        self._anim_progress(0)
        self._log("▸ Starting downloads", T.accent)
        self.status_lbl.config(text="Downloading...")
        threading.Thread(target=self._dl_all, daemon=True).start()

    def _anim_progress(self, pct):
        if not self.downloading:
            return
        w = self.prog_c.winfo_width() or 700
        bar_w = int(w * min(pct, 1.0))
        self.prog_c.coords("bar", 0, 0, bar_w, 4)
        self.root.after(50, lambda: self._anim_progress(pct))

    def _dl_all(self):
        downloaded = []
        cwd = os.getcwd()
        os.chdir(DESKTOP)
        try:
            total = len(self.urls)
            for i, url in enumerate(self.urls):
                self.status_q.put(f"[{i+1}/{total}] Downloading...")
                self.log_q.put((f"[{i+1}/{total}]", "#ffffff"))
                fname = self._dl_one(url)
                if fname:
                    downloaded.append(fname)
                    self.log_q.put((f"  ✓ {fname}", T.success))
                else:
                    self.log_q.put(("  ✗ Failed", T.error))
                self._anim_progress((i + 1) / total)

            if not downloaded:
                self.log_q.put(("No files downloaded.", T.error))
                self.status_q.put("Failed")
                return

            if len(downloaded) > 1:
                fn = "YouTube Downloads"
                c = 1
                while os.path.exists(os.path.join(DESKTOP, fn)):
                    c += 1; fn = f"YouTube Downloads {c}"
                fp = os.path.join(DESKTOP, fn)
                os.makedirs(fp, exist_ok=True)
                for f in downloaded:
                    shutil.move(os.path.join(DESKTOP, f), os.path.join(fp, f))
                self.log_q.put((f"Moved to ~/Desktop/{fn}/", T.accent))
                self.status_q.put(f"Done — {fn}")
            else:
                self.log_q.put(("Saved to Desktop ✓", T.accent))
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
                err = output.strip().split("\n")[-1] if output.strip() else "?"
                self.log_q.put((f"  Error: {err}", T.error))
                return None

            filename = None
            for line in output.split("\n"):
                if "[Merger]" in line and "into" in line:
                    for p in line.split('"'):
                        p = p.strip()
                        if p.endswith(".mp4") and os.path.exists(p):
                            filename = p; break
                    if not filename:
                        raw = line.split("into ")[-1].strip().strip("'\"")
                        if raw.endswith(".mp4") and os.path.exists(raw):
                            filename = raw
                if filename: break

            if not filename and predicted and os.path.exists(predicted):
                filename = predicted
            if not filename:
                mp4s = [f for f in os.listdir(DESKTOP)
                        if f.endswith(".mp4") and os.path.isfile(os.path.join(DESKTOP, f))]
                if mp4s:
                    filename = max(mp4s, key=lambda f: os.path.getctime(os.path.join(DESKTOP, f)))
            if filename and os.path.exists(filename if filename.startswith("/") else os.path.join(DESKTOP, filename)):
                return os.path.basename(filename)
            return None
        except subprocess.TimeoutExpired:
            self.log_q.put(("  Timed out (10 min)", T.error))
            return None
        except Exception as e:
            self.log_q.put((f"  Error: {e}", T.error))
            return None

    def _finish(self):
        self.downloading = False
        self.dl_btn_c.itemconfig("bg", fill=T.accent)
        self.dl_btn_c.itemconfig("txt", text="⬇  Download All")
        self.prog_c.itemconfig("track", state="hidden")
        self.prog_c.itemconfig("bar", state="hidden")


if __name__ == "__main__":
    root = Tk()
    Ytmp4Converter(root)
    root.mainloop()
