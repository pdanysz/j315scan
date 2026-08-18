#!/usr/bin/env python3
"""Desktop GUI for Brother DCP-J315W network scanner."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config, save_user_settings
from extract import extract_objects, save_scan_set, stamp_now
from i18n import SUPPORTED, get_i18n
from protocol import DPI_CHOICES, ScannerError, probe, save_image, scan


class ScannerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.cfg = load_config()
        self.i18n = get_i18n(self.cfg.get("language", "auto"))
        self.minsize(900, 680)
        self.geometry("1080x760")

        self._photo = None
        self._image = None
        self._crops = []
        self._busy = False
        self._widgets: dict[str, tk.Widget] = {}

        self.host = tk.StringVar(value=str(self.cfg.get("host", "192.168.0.80")))
        self.mode = tk.StringVar(value=str(self.cfg.get("mode", "color")))
        self.dpi = tk.IntVar(value=int(self.cfg.get("dpi", 200)))
        self.brightness = tk.IntVar(value=int(self.cfg.get("brightness", 50)))
        self.contrast = tk.IntVar(value=int(self.cfg.get("contrast", 50)))
        self.split = tk.BooleanVar(value=bool(self.cfg.get("split", True)))
        self.outdir = tk.StringVar(value=str(self.cfg.get("outdir")))
        self.language = tk.StringVar(value=str(self.cfg.get("language", "auto")))
        self.status = tk.StringVar(value=self.t("ready"))

        self._build()
        self.after(200, self.check_connection)

    def t(self, key: str, **kwargs) -> str:
        return self.i18n.t(key, **kwargs)

    def persist(self) -> None:
        data = {
            "host": self.host.get().strip(),
            "mode": self.mode.get(),
            "dpi": int(self.dpi.get()),
            "brightness": int(self.brightness.get()),
            "contrast": int(self.contrast.get()),
            "split": bool(self.split.get()),
            "outdir": self.outdir.get().strip(),
            "language": self.language.get().strip() or "auto",
            "filename_prefix": self.cfg.get("filename_prefix", "scan"),
        }
        self.cfg.update(data)
        save_user_settings(data)

    def prefix(self) -> str:
        return str(self.cfg.get("filename_prefix") or "scan")

    def out_dir(self) -> Path:
        path = Path(self.outdir.get().strip() or self.cfg["outdir"]).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _build(self) -> None:
        self.title(self.t("app_title"))
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        side = ttk.Frame(root, padding=(0, 0, 12, 0))
        side.grid(row=0, column=0, sticky="nsw")

        ttk.Label(side, text="DCP-J315W", font=("Helvetica", 18, "bold")).pack(anchor="w")
        self._widgets["subtitle"] = ttk.Label(
            side, text=self.t("app_subtitle", port=int(self.cfg.get("port", 54921)))
        )
        self._widgets["subtitle"].pack(anchor="w", pady=(0, 12))

        lang = ttk.Frame(side)
        lang.pack(fill=tk.X, pady=(0, 8))
        self._widgets["language_lbl"] = ttk.Label(lang, text=self.t("language"))
        self._widgets["language_lbl"].pack(side=tk.LEFT)
        lang_values = ["auto", *SUPPORTED]
        combo = ttk.Combobox(
            lang, textvariable=self.language, values=lang_values, width=8, state="readonly"
        )
        combo.pack(side=tk.LEFT, padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.change_language())

        box = ttk.LabelFrame(side, text=self.t("connection"), padding=8)
        self._widgets["connection"] = box
        box.pack(fill=tk.X, pady=(0, 8))
        self._widgets["ip"] = ttk.Label(box, text=self.t("ip"))
        self._widgets["ip"].grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.host, width=16).grid(row=0, column=1, padx=6)
        self._widgets["check"] = ttk.Button(
            box, text=self.t("check"), command=self.check_connection
        )
        self._widgets["check"].grid(row=0, column=2)

        opts = ttk.LabelFrame(side, text=self.t("scan_box"), padding=8)
        self._widgets["scan_box"] = opts
        opts.pack(fill=tk.X, pady=(0, 8))
        self._widgets["mode"] = ttk.Label(opts, text=self.t("mode"))
        self._widgets["mode"].grid(row=0, column=0, sticky="w")
        modes = ttk.Frame(opts)
        modes.grid(row=0, column=1, sticky="w", pady=2)
        self._widgets["color"] = ttk.Radiobutton(
            modes, text=self.t("color"), variable=self.mode, value="color"
        )
        self._widgets["gray"] = ttk.Radiobutton(
            modes, text=self.t("gray"), variable=self.mode, value="gray"
        )
        self._widgets["color"].pack(side=tk.LEFT)
        self._widgets["gray"].pack(side=tk.LEFT)
        self._widgets["dpi"] = ttk.Label(opts, text=self.t("dpi"))
        self._widgets["dpi"].grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(
            opts, textvariable=self.dpi, values=list(DPI_CHOICES), width=8, state="readonly"
        ).grid(row=1, column=1, sticky="w")
        self._widgets["brightness"] = ttk.Label(opts, text=self.t("brightness"))
        self._widgets["brightness"].grid(row=2, column=0, sticky="w")
        ttk.Scale(opts, from_=0, to=100, variable=self.brightness, orient=tk.HORIZONTAL).grid(
            row=2, column=1, sticky="ew", pady=2
        )
        self._widgets["contrast"] = ttk.Label(opts, text=self.t("contrast"))
        self._widgets["contrast"].grid(row=3, column=0, sticky="w")
        ttk.Scale(opts, from_=0, to=100, variable=self.contrast, orient=tk.HORIZONTAL).grid(
            row=3, column=1, sticky="ew", pady=2
        )
        self._widgets["split"] = ttk.Checkbutton(opts, text=self.t("split"), variable=self.split)
        self._widgets["split"].grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        opts.columnconfigure(1, weight=1)

        dest = ttk.LabelFrame(side, text=self.t("save_box"), padding=8)
        self._widgets["save_box"] = dest
        dest.pack(fill=tk.X, pady=(0, 8))
        ttk.Entry(dest, textvariable=self.outdir, width=28).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(dest, text="…", width=3, command=self.pick_folder).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        self.scan_btn = ttk.Button(side, text=self.t("scan_save"), command=self.start_scan)
        self.scan_btn.pack(fill=tk.X, pady=(4, 4), ipady=6)
        self.save_btn = ttk.Button(
            side, text=self.t("save_again"), command=self.save_now, state=tk.DISABLED
        )
        self.save_btn.pack(fill=tk.X, pady=2)
        self._widgets["save_as"] = ttk.Button(side, text=self.t("save_as"), command=self.save_as)
        self._widgets["save_as"].pack(fill=tk.X, pady=2)
        self._widgets["clear"] = ttk.Button(
            side, text=self.t("clear_preview"), command=self.clear_preview
        )
        self._widgets["clear"].pack(fill=tk.X, pady=2)

        self.progress = ttk.Progressbar(side, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(12, 4))
        ttk.Label(side, textvariable=self.status, wraplength=280).pack(anchor="w")

        preview = ttk.LabelFrame(root, text=self.t("preview"), padding=6)
        self._widgets["preview"] = preview
        preview.grid(row=0, column=1, sticky="nsew")
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(preview, background="#1c1c1c", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _e: self._draw_preview())
        self.bind("<Return>", lambda _e: self.start_scan())

    def refresh_texts(self) -> None:
        self.title(self.t("app_title"))
        self._widgets["subtitle"].configure(
            text=self.t("app_subtitle", port=int(self.cfg.get("port", 54921)))
        )
        mapping = {
            "language_lbl": "language",
            "connection": "connection",
            "ip": "ip",
            "check": "check",
            "scan_box": "scan_box",
            "mode": "mode",
            "color": "color",
            "gray": "gray",
            "dpi": "dpi",
            "brightness": "brightness",
            "contrast": "contrast",
            "split": "split",
            "save_box": "save_box",
            "save_as": "save_as",
            "clear": "clear_preview",
            "preview": "preview",
        }
        for name, key in mapping.items():
            widget = self._widgets.get(name)
            if widget is not None:
                widget.configure(text=self.t(key))
        self.scan_btn.configure(text=self.t("scan_save"))
        self.save_btn.configure(text=self.t("save_again"))
        if self._image is None:
            self.status.set(self.t("ready"))
        self._draw_preview()

    def change_language(self) -> None:
        requested = self.language.get()
        self.i18n.set_language(requested)
        self.persist()
        self.refresh_texts()

    def pick_folder(self) -> None:
        chosen = filedialog.askdirectory(
            initialdir=str(self.out_dir()), title=self.t("save_folder")
        )
        if chosen:
            self.outdir.set(chosen)
            self.persist()

    def set_busy(self, busy: bool, msg: str) -> None:
        self._busy = busy
        self.scan_btn.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.status.set(msg)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def check_connection(self) -> None:
        if self._busy:
            return
        host = self.host.get().strip()
        self.set_busy(True, self.t("connecting", host=host))

        def work() -> None:
            try:
                banner, offer = probe(host)
                text = self.t(
                    "probe_ok",
                    banner=banner,
                    w=offer.px_x,
                    h=offer.px_y,
                    dpi=offer.dpi_x,
                    mmw=offer.mm_x,
                    mmh=offer.mm_y,
                )
                self.after(0, lambda t=text: self._probe_ok(t))
            except Exception as e:
                msg = self.t("no_scanner", error=e)
                self.after(0, lambda m=msg: self._fail(m))

        threading.Thread(target=work, daemon=True).start()

    def _probe_ok(self, text: str) -> None:
        self.persist()
        self.set_busy(False, text)

    def start_scan(self) -> None:
        if self._busy:
            return
        host = self.host.get().strip()
        dpi = int(self.dpi.get())
        mode = self.mode.get()
        do_split = bool(self.split.get())
        folder = str(self.out_dir())
        prefix = self.prefix()
        self.set_busy(True, self.t("scanning", mode=mode, dpi=dpi))

        def work() -> None:
            try:
                result = scan(
                    host=host,
                    dpi=dpi,
                    mode=mode,
                    brightness=int(self.brightness.get()),
                    contrast=int(self.contrast.get()),
                    idle_timeout=float(self.cfg.get("idle_timeout", 25)),
                    max_seconds=float(self.cfg.get("max_seconds", 180)),
                )
                crops = extract_objects(result.image) if do_split else []
                paths = save_scan_set(result.image, crops, folder, stamp=stamp_now(), prefix=prefix)
                self.after(0, lambda r=result, c=crops, p=paths: self._scan_ok(r, c, p))
            except Exception as e:
                msg = self.t("scan_failed", error=e)
                self.after(0, lambda m=msg: self._fail(m))

        threading.Thread(target=work, daemon=True).start()

    def _scan_ok(self, result, crops, paths) -> None:
        self._image = result.image
        self._crops = crops
        self.save_btn.configure(state=tk.NORMAL)
        self.persist()
        w, h = result.image.size
        names = ", ".join(p.name for p in paths)
        extra = self.t("split_extra", n=len(crops)) if crops else ""
        self.set_busy(False, self.t("scan_ok", w=w, h=h, extra=extra, names=names))
        self._draw_preview()

    def report_callback_exception(self, exc, val, tb) -> None:  # type: ignore[override]
        # Keep the window alive if a Tk callback fails (e.g. offline scanner).
        self._fail(str(val) or exc.__name__)

    def _fail(self, msg: str) -> None:
        try:
            self.set_busy(False, msg)
        except tk.TclError:
            pass
        try:
            messagebox.showerror(self.t("error"), msg)
        except tk.TclError:
            pass

    def clear_preview(self) -> None:
        self._image = None
        self._crops = []
        self._photo = None
        self.canvas.delete("all")
        self.save_btn.configure(state=tk.DISABLED)
        self.status.set(self.t("preview_cleared"))
        self._draw_preview()

    def _draw_preview(self) -> None:
        self.canvas.delete("all")
        cw = max(self.canvas.winfo_width(), 40)
        ch = max(self.canvas.winfo_height(), 40)
        if self._image is None:
            self.canvas.create_text(
                cw // 2,
                ch // 2,
                text=self.t("no_scan"),
                fill="#888888",
                font=("Helvetica", 16),
            )
            return
        img = self._image.copy()
        img.thumbnail((cw - 16, ch - 16))
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(cw // 2, ch // 2, image=self._photo)

    def save_now(self) -> None:
        if self._image is None:
            return
        try:
            paths = save_scan_set(
                self._image,
                self._crops if self.split.get() else [],
                self.out_dir(),
                prefix=self.prefix(),
            )
        except OSError as e:
            messagebox.showerror(self.t("save_error"), str(e))
            return
        self.status.set(self.t("saved", names=", ".join(p.name for p in paths)))

    def save_as(self) -> None:
        if self._image is None:
            return
        stamp = stamp_now()
        ext = ".jpg" if self._image.mode == "RGB" else ".png"
        path = filedialog.asksaveasfilename(
            initialdir=str(self.out_dir()),
            initialfile=f"{self.prefix()}-{stamp}{ext}",
            defaultextension=ext,
            filetypes=(
                (self.t("file_jpeg"), "*.jpg"),
                (self.t("file_png"), "*.png"),
                (self.t("file_pdf"), "*.pdf"),
                (self.t("file_tiff"), "*.tif"),
                (self.t("file_all"), "*.*"),
            ),
        )
        if not path:
            return
        dest = Path(path)
        try:
            if self.split.get() and self._crops:
                paths = save_scan_set(
                    self._image,
                    self._crops,
                    dest.parent,
                    stamp=dest.stem,
                    prefix=self.prefix(),
                )
            else:
                paths = [save_image(self._image, dest)]
        except OSError as e:
            messagebox.showerror(self.t("save_error"), str(e))
            return
        self.status.set(self.t("saved", names=", ".join(p.name for p in paths)))


def main() -> None:
    app = ScannerApp()
    app.out_dir()
    app.mainloop()


if __name__ == "__main__":
    main()
