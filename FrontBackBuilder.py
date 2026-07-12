"""
Front-Back PDF Builder v2.0
Professional card printing tool
"""

import os
import sys
import json
import io
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

try:
    import customtkinter as ctk
    from pypdf import PdfReader, PdfWriter
    from PIL import Image, ImageTk
    import fitz  # PyMuPDF
    from tkinterdnd2 import DND_FILES, TkinterDnD
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)


# ============ Config ============
APP_NAME = "Front-Back PDF Builder"
APP_VERSION = "2.0"
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".fbbuilder_history.json")
MAX_HISTORY = 10

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============ Helpers ============
def get_pdf_info(path):
    """Get PDF info: page count and size."""
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
        return None


def render_pdf_page(path, page_num=0, max_size=180):
    """Render PDF page to PIL image for preview."""
    try:
        doc = fitz.open(path)
        page = doc.load_page(page_num)
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        doc.close()
        return img
    except Exception as e:
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


def build_pdf(front_path, backs_path, output_path, reverse=False):
    """Build the final PDF."""
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


def create_report_pdf(report_path, project_info):
    """Create a PDF report of the project."""
    c = canvas.Canvas(report_path, pagesize=A4)
    width, height = A4

    # Header
    c.setFillColorRGB(0.15, 0.35, 0.75)
    c.rect(0, height - 60, width, 60, fill=True, stroke=False)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(30, height - 40, "Front-Back PDF Builder - Report")

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 11)
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
        "• Print at Actual Size (100%)",
        "• Enable duplex printing (both sides)",
        "• For landscape cards: Flip on Short Edge",
        "• For portrait cards: Flip on Long Edge",
        "• Test with 2 cards first, then print all",
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

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(30, 30, f"Generated by {APP_NAME} v{APP_VERSION}")

    c.save()


# ============ Main App ============
class FBBuilderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("980x680")
        self.minsize(900, 620)

        # Data
        self.front_path = None
        self.backs_path = None
        self.front_info = None
        self.backs_info = None
        self.front_preview_img = None
        self.backs_preview_img = None

        self.build_ui()
        self.setup_dnd()

    def build_ui(self):
        # Grid config
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ===== Header =====
        header = ctk.CTkFrame(self, height=70, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_propagate(False)

        title = ctk.CTkLabel(
            header,
            text=f"🃏 {APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(side="left", padx=20, pady=15)

        history_btn = ctk.CTkButton(
            header,
            text="📜 History",
            width=100,
            command=self.show_history
        )
        history_btn.pack(side="right", padx=20, pady=15)

        # ===== Front Panel =====
        self.front_frame = self.build_file_panel(
            "Front PDF",
            "Only page 1 will be used",
            0, 0,
            self.select_front
        )

        # ===== Backs Panel =====
        self.backs_frame = self.build_file_panel(
            "Backs PDF",
            "All pages will be used",
            0, 1,
            self.select_backs
        )

        # ===== Bottom Panel =====
        bottom = ctk.CTkFrame(self, corner_radius=10)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))

        # Order dropdown
        order_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        order_frame.pack(side="left", padx=15, pady=15)

        ctk.CTkLabel(
            order_frame,
            text="Back Order:",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 10))

        self.order_var = ctk.StringVar(value="Normal")
        order_menu = ctk.CTkOptionMenu(
            order_frame,
            values=["Normal", "Reverse"],
            variable=self.order_var,
            width=120
        )
        order_menu.pack(side="left")

        # Report checkbox
        self.report_var = ctk.BooleanVar(value=True)
        report_cb = ctk.CTkCheckBox(
            bottom,
            text="Generate PDF Report",
            variable=self.report_var
        )
        report_cb.pack(side="left", padx=15, pady=15)

        # Build button
        self.build_btn = ctk.CTkButton(
            bottom,
            text="🚀 Build PDF",
            width=200,
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.build,
            state="disabled"
        )
        self.build_btn.pack(side="right", padx=15, pady=15)

    def build_file_panel(self, title, subtitle, row, col, browse_cmd):
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.grid(row=1, column=col, sticky="nsew", padx=15, pady=15)

        # Title
        title_lbl = ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=17, weight="bold")
        )
        title_lbl.pack(pady=(15, 3))

        subtitle_lbl = ctk.CTkLabel(
            frame,
            text=subtitle,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        subtitle_lbl.pack(pady=(0, 12))

        # Preview area
        preview_frame = ctk.CTkFrame(frame, height=220, corner_radius=8)
        preview_frame.pack(fill="x", padx=15, pady=8)
        preview_frame.pack_propagate(False)

        preview_lbl = ctk.CTkLabel(
            preview_frame,
            text="📄\n\nDrag & Drop PDF here\nor click Browse",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        preview_lbl.pack(expand=True)

        # Info area
        info_lbl = ctk.CTkLabel(
            frame,
            text="No file selected",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        info_lbl.pack(pady=8, padx=15)

        # Browse button
        browse_btn = ctk.CTkButton(
            frame,
            text="📁 Browse...",
            command=browse_cmd,
            width=160
        )
        browse_btn.pack(pady=(5, 15))

        # Store references
        frame.preview_frame = preview_frame
        frame.preview_lbl = preview_lbl
        frame.info_lbl = info_lbl

        return frame

    def setup_dnd(self):
        """Setup drag & drop."""
        try:
            self.front_frame.preview_frame.drop_target_register(DND_FILES)
            self.front_frame.preview_frame.dnd_bind(
                '<<Drop>>',
                lambda e: self.on_drop(e, "front")
            )
            self.backs_frame.preview_frame.drop_target_register(DND_FILES)
            self.backs_frame.preview_frame.dnd_bind(
                '<<Drop>>',
                lambda e: self.on_drop(e, "backs")
            )
        except Exception as e:
            print(f"DnD setup failed: {e}")

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
            filetypes=[("PDF Files", "*.pdf")]
        )
        if path:
            self.load_front(path)

    def select_backs(self):
        path = filedialog.askopenfilename(
            title="Select Backs PDF",
            filetypes=[("PDF Files", "*.pdf")]
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

        # Update preview
        img = render_pdf_page(path, 0, 180)
        if img:
            ctk_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(img.width, img.height)
            )
            self.front_preview_img = ctk_img
            self.front_frame.preview_lbl.configure(image=ctk_img, text="")

        # Update info
        info_text = (
            f"📄 File: {os.path.basename(path)}\n"
            f"📐 Size: {info['width_mm']:.1f} × {info['height_mm']:.1f} mm\n"
            f"📑 Pages: {info['pages']} (using page 1)"
        )
        self.front_frame.info_lbl.configure(text=info_text, text_color="white")

        self.check_ready()
        self.check_size_match()

    def load_backs(self, path):
        info = get_pdf_info(path)
        if not info:
            messagebox.showerror("Error", "Cannot read this PDF file.")
            return

        self.backs_path = path
        self.backs_info = info

        # Update preview
        img = render_pdf_page(path, 0, 180)
        if img:
            ctk_img = ctk.CTkImage(
                light_image=img,
                dark_image=img,
                size=(img.width, img.height)
            )
            self.backs_preview_img = ctk_img
            self.backs_frame.preview_lbl.configure(image=ctk_img, text="")

        # Update info
        info_text = (
            f"📄 File: {os.path.basename(path)}\n"
            f"📐 Size: {info['width_mm']:.1f} × {info['height_mm']:.1f} mm\n"
            f"📑 Pages: {info['pages']} cards"
        )
        self.backs_frame.info_lbl.configure(text=info_text, text_color="white")

        self.check_ready()
        self.check_size_match()

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
            count = build_pdf(
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
                "front_size": f"{self.front_info['width_mm']:.1f} × {self.front_info['height_mm']:.1f} mm",
                "backs_size": f"{self.backs_info['width_mm']:.1f} × {self.backs_info['height_mm']:.1f} mm",
            }

            # Save history
            save_history(project_info)

            # Generate report
            if self.report_var.get():
                report_path = output_path.replace(".pdf", "_report.pdf")
                try:
                    create_report_pdf(report_path, project_info)
                except Exception as e:
                    print(f"Report failed: {e}")

            messagebox.showinfo(
                "Success!",
                f"✅ PDF Built Successfully!\n\n"
                f"📊 Cards: {count}\n"
                f"📄 Total pages: {count * 2}\n"
                f"💾 Saved to:\n{output_path}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to build PDF:\n{e}")

    def show_history(self):
        history = load_history()

        win = ctk.CTkToplevel(self)
        win.title("Project History")
        win.geometry("620x480")
        win.transient(self)

        ctk.CTkLabel(
            win,
            text="📜 Recent Projects",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=15)

        if not history:
            ctk.CTkLabel(
                win,
                text="No history yet.\nBuild your first PDF!",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            ).pack(pady=40)
            return

        scroll = ctk.CTkScrollableFrame(win, width=580, height=380)
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        for i, item in enumerate(history):
            card = ctk.CTkFrame(scroll, corner_radius=8)
            card.pack(fill="x", pady=5, padx=5)

            text = (
                f"📅 {item['date']}\n"
                f"📄 Front: {os.path.basename(item['front'])}\n"
                f"📄 Backs: {os.path.basename(item['backs'])}\n"
                f"📊 {item['card_count']} cards | {item['order']}"
            )
            ctk.CTkLabel(
                card,
                text=text,
                justify="left",
                font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=15, pady=10)


if __name__ == "__main__":
    try:
        # Use TkinterDnD root
        root = TkinterDnD.Tk()
        root.withdraw()
        app = FBBuilderApp()
        app.mainloop()
    except Exception as e:
        # Fallback without DnD
        app = FBBuilderApp()
        app.mainloop()
