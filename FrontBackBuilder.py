"""
Front-Back PDF Builder v2.2
Professional card printing tool
"""

import os
import sys
import json
import io
from datetime import datetime
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk
from pypdf import PdfReader, PdfWriter
from PIL import Image
import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


# ============ Config ============
APP_NAME = "Front-Back PDF Builder"
APP_VERSION = "2.2"
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".fbbuilder_history.json")
MAX_HISTORY = 10

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============ Helpers ============
def get_pdf_info(path):
    try:
        reader = PdfReader(path)
        page = reader.pages[0]
        width_pt = float(page.mediabox.width)
        height_pt = float(page.mediabox.height)
        width_mm = width_pt * 0.352778
        height_mm = height_pt * 0.352778
        return {
            "pages": len(reader.pages),
            "width_pt": width_pt,
            "height_pt": height_pt,
            "width_mm": width_mm,
            "height_mm": height_mm,
        }
    except Exception as e:
        print(f"get_pdf_info error: {e}")
        return None


def render_pdf_page(path, page_num=0, max_size=200):
    try:
        pdf = pdfium.PdfDocument(path)
        page = pdf[page_num]
        pil_image = page.render(scale=1.5).to_pil()
        pil_image.thumbnail((max_size, max_size), Image.LANCZOS)
        pdf.close()
        return pil_image
    except Exception as e:
        print(f"render error: {e}")
        return None


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []


def save_history(entry):
    history = load_history()
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except:
        pass


def build_pdf_fixed_front(front_path, backs_path, output_path, reverse=False):
    """Mode 1: Fixed front (page 1) repeated for each back."""
    front_reader = PdfReader(front_path)
    backs_reader = PdfReader(backs_path)
    writer = PdfWriter()

    front_page = front_reader.pages[0]
    back_count = len(backs_reader.pages)

    for i in range(back_count):
        writer.add_page(front_page)
        back_index = (back_count - 1 - i) if reverse else i
        writer.add_page(backs_reader.pages[back_index])

    with open(output_path, "wb") as f:
        writer.write(f)

    return back_count


def build_pdf_paired(front_path, backs_path, output_path, reverse=False):
    """Mode 2: Paired - Front[i] with Back[i]."""
    front_reader = PdfReader(front_path)
    backs_reader = PdfReader(backs_path)
    writer = PdfWriter()

    front_count = len(front_reader.pages)
    back_count = len(backs_reader.pages)

    if front_count != back_count:
        raise ValueError(
            f"Page count mismatch!\n"
            f"Front PDF: {front_count} pages\n"
            f"Backs PDF: {back_count} pages\n\n"
            f"In Paired mode, both PDFs must have the same number of pages."
        )

    for i in range(front_count):
        index = (front_count - 1 - i) if reverse else i
        writer.add_page(front_reader.pages[index])
        writer.add_page(backs_reader.pages[index])

    with open(output_path, "wb") as f:
        writer.write(f)

    return front_count


def create_report_pdf(report_path, project_info):
    c = canvas.Canvas(report_path, pagesize=A4)
    width, height = A4

    c.setFillColorRGB(0.15, 0.35, 0.75)
    c.rect(0, height - 60, width, 60, fill=True, stroke=False)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(30, height - 40, "Front-Back PDF Builder - Report")

    c.setFillColorRGB(0, 0, 0)
    y = height - 100

    lines = [
        f"Date: {project_info['date']}",
        "",
        "--- Files ---",
        f"Front PDF: {project_info['front']}",
        f"Backs PDF: {project_info['backs']}",
        f"Output PDF: {project_info['output']}",
        "",
        "--- Statistics ---",
        f"Mode: {project_info['mode']}",
        f"Number of cards: {project_info['card_count']}",
        f"Total pages: {project_info['total_pages']}",
        f"Back order: {project_info['order']}",
        "",
        "--- Page Sizes ---",
        f"Front size: {project_info['front_size']}",
        f"Backs size: {project_info['backs_size']}",
        "",
        "--- Print Layout ---",
        "Order: Front / Back / Front / Back ...",
        "",
        "--- Printing Tips ---",
        "- Print at Actual Size (100%)",
        "- Enable duplex printing (both sides)",
        "- For landscape cards: Flip on Short Edge",
        "- For portrait cards: Flip on Long Edge",
        "- Test with 2 cards first, then print all",
    ]

    for line in lines:
        if line.startswith("---"):
            c.setFont("Helvetica-Bold", 12)
            c.setFillColorRGB(0.15, 0.35, 0.75)
        else:
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0, 0, 0)
        c.drawString(30, y, line)
        y -= 18

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(30, 30, f"Generated by {APP_NAME} v{APP_VERSION}")

    c.save()


# ============ Main App ============
class FBBuilderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1000x780")
        self.minsize(950, 740)

        self.front_path = None
        self.backs_path = None
        self.front_info = None
        self.backs_info = None
        self.front_preview_img = None
        self.backs_preview_img = None

        self.build_ui()

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ===== Header =====
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color=("#1f6aa5", "#144870"))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        title = ctk.CTkLabel(
            header,
            text=f"🃏  {APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        title.pack(side="left", padx=25, pady=15)

        history_btn = ctk.CTkButton(
            header,
            text="📜 History",
            width=110,
            height=35,
            command=self.show_history,
            fg_color="#0d3d5c",
            hover_color="#0a2d44"
        )
        history_btn.pack(side="right", padx=25, pady=15)

        # ===== Mode Selector =====
        mode_frame = ctk.CTkFrame(self, corner_radius=10, height=90)
        mode_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(15, 5))
        mode_frame.grid_propagate(False)

        ctk.CTkLabel(
            mode_frame,
            text="🎯 Mode:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=(20, 10), pady=25)

        self.mode_var = ctk.StringVar(value="Fixed Front")
        self.mode_menu = ctk.CTkOptionMenu(
            mode_frame,
            values=["Fixed Front", "Paired (1-to-1)"],
            variable=self.mode_var,
            width=180,
            height=35,
            command=self.on_mode_change
        )
        self.mode_menu.pack(side="left", pady=25)

        self.mode_desc = ctk.CTkLabel(
            mode_frame,
            text="ℹ️ Front page 1 will be used for every back page",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.mode_desc.pack(side="left", padx=20, pady=25)

        # ===== File Panels =====
        self.front_frame = self.build_file_panel(
            "Front PDF",
            "Only page 1 will be used",
            0,
            self.select_front,
            "front"
        )

        self.backs_frame = self.build_file_panel(
            "Backs PDF",
            "All pages will be used",
            1,
            self.select_backs,
            "backs"
        )

        # ===== Bottom Panel =====
        bottom = ctk.CTkFrame(self, corner_radius=10, height=80)
        bottom.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))
        bottom.grid_propagate(False)

        order_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        order_frame.pack(side="left", padx=20, pady=20)

        ctk.CTkLabel(
            order_frame,
            text="Order:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left", padx=(0, 10))

        self.order_var = ctk.StringVar(value="Normal")
        order_menu = ctk.CTkOptionMenu(
            order_frame,
            values=["Normal", "Reverse"],
            variable=self.order_var,
            width=130,
            height=35
        )
        order_menu.pack(side="left")

        self.report_var = ctk.BooleanVar(value=True)
        report_cb = ctk.CTkCheckBox(
            bottom,
            text="Generate PDF Report",
            variable=self.report_var,
            font=ctk.CTkFont(size=12)
        )
        report_cb.pack(side="left", padx=20, pady=20)

        self.build_btn = ctk.CTkButton(
            bottom,
            text="🚀  Build PDF",
            width=220,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.build,
            state="disabled",
            fg_color="#2fa572",
            hover_color="#227052"
        )
        self.build_btn.pack(side="right", padx=20, pady=15)

    def on_mode_change(self, value):
        if value == "Fixed Front":
            self.mode_desc.configure(
                text="ℹ️ Front page 1 will be used for every back page"
            )
            self.front_frame.subtitle_lbl.configure(
                text="Only page 1 will be used"
            )
        else:  # Paired
            self.mode_desc.configure(
                text="ℹ️ Each Front page pairs with the same Back page (F1+B1, F2+B2, ...)"
            )
            self.front_frame.subtitle_lbl.configure(
                text="All pages will be used (must match Backs count)"
            )
        self.check_ready()

    def build_file_panel(self, title, subtitle, col, browse_cmd, tag):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid(row=2, column=col, sticky="nsew", padx=15, pady=(5, 15))

        title_lbl = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_lbl.pack(pady=(15, 3))

        subtitle_lbl = ctk.CTkLabel(
            frame,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        subtitle_lbl.pack(pady=(0, 12))

        preview_frame = ctk.CTkFrame(
            frame,
            height=260,
            corner_radius=8,
            fg_color=("#e0e0e0", "#2b2b2b"),
            border_width=2,
            border_color=("#c0c0c0", "#3f3f3f")
        )
        preview_frame.pack(fill="x", padx=15, pady=8)
        preview_frame.pack_propagate(False)

        preview_lbl = ctk.CTkLabel(
            preview_frame,
            text="📄\n\nDrop PDF here\nor click Browse",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        preview_lbl.pack(expand=True)

        info_lbl = ctk.CTkLabel(
            frame,
            text="ℹ️  No file selected",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray",
            justify="center"
        )
        info_lbl.pack(pady=(12, 5), padx=15)

        file_lbl = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        file_lbl.pack(pady=(0, 8), padx=15)

        browse_btn = ctk.CTkButton(
            frame,
            text="📁  Browse...",
            command=browse_cmd,
            width=170,
            height=38,
            font=ctk.CTkFont(size=13)
        )
        browse_btn.pack(pady=(5, 15))

        frame.preview_frame = preview_frame
        frame.preview_lbl = preview_lbl
        frame.info_lbl = info_lbl
        frame.file_lbl = file_lbl
        frame.subtitle_lbl = subtitle_lbl

        if DND_AVAILABLE:
            try:
                preview_frame.drop_target_register(DND_FILES)
                preview_frame.dnd_bind(
                    '<<Drop>>',
                    lambda e, t=tag: self.on_drop(e, t)
                )
            except Exception as e:
                print(f"DnD error: {e}")

        return frame

    def on_drop(self, event, target):
        path = event.data.strip().strip("{}").strip('"')
        if os.path.isfile(path) and path.lower().endswith(".pdf"):
            if target == "front":
                self.load_front(path)
            else:
                self.load_backs(path)
        else:
            messagebox.showwarning("Invalid File", "Please drop a PDF file.")

    def select_front(self):
        path = filedialog.askopenfilename(
            title="Select Front PDF",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if path:
            self.load_front(path)

    def select_backs(self):
        path = filedialog.askopenfilename(
            title="Select Backs PDF",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if path:
            self.load_backs(path)

    def load_front(self, path):
        info = get_pdf_info(path)
        if not info:
            messagebox.showerror("Error", "Cannot read this PDF file.")
            return

        self.front_path = path
        self.front_info = info

        img = render_pdf_page(path, 0, 220)
        if img:
            ctk_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(img.width, img.height)
            )
            self.front_preview_img = ctk_img
            self.front_frame.preview_lbl.configure(image=ctk_img, text="")

        info_text = (
            f"📐  {info['width_mm']:.1f} × {info['height_mm']:.1f} mm    "
            f"|    📑  {info['pages']} page(s)"
        )
        self.front_frame.info_lbl.configure(text=info_text, text_color=("#1f6aa5", "#4ea6e0"))

        filename = os.path.basename(path)
        if len(filename) > 45:
            filename = filename[:42] + "..."
        self.front_frame.file_lbl.configure(text=f"📄 {filename}", text_color="gray")

        self.check_ready()
        self.check_size_match()
        self.check_paired_match()

    def load_backs(self, path):
        info = get_pdf_info(path)
        if not info:
            messagebox.showerror("Error", "Cannot read this PDF file.")
            return

        self.backs_path = path
        self.backs_info = info

        img = render_pdf_page(path, 0, 220)
        if img:
            ctk_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(img.width, img.height)
            )
            self.backs_preview_img = ctk_img
            self.backs_frame.preview_lbl.configure(image=ctk_img, text="")

        info_text = (
            f"📐  {info['width_mm']:.1f} × {info['height_mm']:.1f} mm    "
            f"|    📑  {info['pages']} card(s)"
        )
        self.backs_frame.info_lbl.configure(text=info_text, text_color=("#1f6aa5", "#4ea6e0"))

        filename = os.path.basename(path)
        if len(filename) > 45:
            filename = filename[:42] + "..."
        self.backs_frame.file_lbl.configure(text=f"📄 {filename}", text_color="gray")

        self.check_ready()
        self.check_size_match()
        self.check_paired_match()

    def check_ready(self):
        if self.front_path and self.backs_path:
            self.build_btn.configure(state="normal")
        else:
            self.build_btn.configure(state="disabled")

    def check_size_match(self):
        if not (self.front_info and self.backs_info):
            return
        fw, fh = self.front_info['width_mm'], self.front_info['height_mm']
        bw, bh = self.backs_info['width_mm'], self.backs_info['height_mm']
        if abs(fw - bw) > 0.5 or abs(fh - bh) > 0.5:
            messagebox.showwarning(
                "Size Mismatch",
                f"Front and Back sizes differ!\n\n"
                f"Front: {fw:.1f} × {fh:.1f} mm\n"
                f"Backs: {bw:.1f} × {bh:.1f} mm\n\n"
                f"This may cause alignment issues in printing."
            )

    def check_paired_match(self):
        """Check page count match in Paired mode."""
        if self.mode_var.get() != "Paired (1-to-1)":
            return
        if not (self.front_info and self.backs_info):
            return
        if self.front_info['pages'] != self.backs_info['pages']:
            messagebox.showwarning(
                "Page Count Mismatch",
                f"In Paired mode, both PDFs must have equal pages!\n\n"
                f"Front: {self.front_info['pages']} pages\n"
                f"Backs: {self.backs_info['pages']} pages"
            )

    def build(self):
        output_path = filedialog.asksaveasfilename(
            title="Save output PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not output_path:
            return

        try:
            reverse = (self.order_var.get() == "Reverse")
            mode = self.mode_var.get()

            if mode == "Fixed Front":
                count = build_pdf_fixed_front(
                    self.front_path,
                    self.backs_path,
                    output_path,
                    reverse
                )
            else:  # Paired
                count = build_pdf_paired(
                    self.front_path,
                    self.backs_path,
                    output_path,
                    reverse
                )

            project_info = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "front": self.front_path,
                "backs": self.backs_path,
                "output": output_path,
                "card_count": count,
                "total_pages": count * 2,
                "order": self.order_var.get(),
                "mode": mode,
                "front_size": f"{self.front_info['width_mm']:.1f} × {self.front_info['height_mm']:.1f} mm",
                "backs_size": f"{self.backs_info['width_mm']:.1f} × {self.backs_info['height_mm']:.1f} mm",
            }

            save_history(project_info)

            if self.report_var.get():
                report_path = output_path.replace(".pdf", "_report.pdf")
                try:
                    create_report_pdf(report_path, project_info)
                except Exception as e:
                    print(f"Report failed: {e}")

            messagebox.showinfo(
                "Success!",
                f"✅ PDF Built Successfully!\n\n"
                f"🎯 Mode: {mode}\n"
                f"📊 Cards: {count}\n"
                f"📄 Total pages: {count * 2}\n"
                f"💾 Saved to:\n{output_path}"
            )

        except ValueError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to build PDF:\n{e}")

    def show_history(self):
        history = load_history()

        win = ctk.CTkToplevel(self)
        win.title("Project History")
        win.geometry("650x500")
        win.transient(self)

        ctk.CTkLabel(
            win,
            text="📜  Recent Projects",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=15)

        if not history:
            ctk.CTkLabel(
                win,
                text="No history yet.\nBuild your first PDF!",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            ).pack(pady=50)
            return

        scroll = ctk.CTkScrollableFrame(win, width=610, height=400)
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        for item in history:
            card = ctk.CTkFrame(scroll, corner_radius=8)
            card.pack(fill="x", pady=5, padx=5)

            mode_str = item.get('mode', 'Fixed Front')
            text = (
                f"📅  {item['date']}\n"
                f"🎯  Mode: {mode_str}\n"
                f"📄  Front: {os.path.basename(item['front'])}\n"
                f"📄  Backs: {os.path.basename(item['backs'])}\n"
                f"📊  {item['card_count']} cards  |  {item['order']}"
            )
            ctk.CTkLabel(
                card,
                text=text,
                justify="left",
                font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=15, pady=10, anchor="w")


if __name__ == "__main__":
    app = FBBuilderApp()
    app.mainloop()
