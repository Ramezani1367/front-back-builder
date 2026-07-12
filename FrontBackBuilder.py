"""
Front-Back PDF Builder
Double-click to run
"""

import os
import sys
from tkinter import Tk, filedialog, messagebox, StringVar
from tkinter.ttk import Label, Button, Combobox, Frame

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    os.system("pip install pypdf")
    from pypdf import PdfReader, PdfWriter


def build_pdf(front_path, backs_path, output_path, reverse):
    front_reader = PdfReader(front_path)
    backs_reader = PdfReader(backs_path)
    writer = PdfWriter()

    front_page = front_reader.pages[0]
    back_count = len(backs_reader.pages)

    for i in range(back_count):
        writer.add_page(front_page)

        if reverse:
            back_index = back_count - 1 - i
        else:
            back_index = i

        writer.add_page(backs_reader.pages[back_index])

    with open(output_path, "wb") as f:
        writer.write(f)

    return back_count


def main():
    root = Tk()
    root.title("Front-Back PDF Builder")
    root.geometry("500x320")
    root.resizable(False, False)

    front_var = StringVar()
    backs_var = StringVar()
    order_var = StringVar(value="Normal")

    # ----- Front -----
    f1 = Frame(root)
    f1.pack(fill="x", padx=20, pady=(20, 5))
    Label(f1, text="Front PDF:").pack(side="left")
    Label(f1, textvariable=front_var, width=40,
          relief="sunken", anchor="w").pack(side="left", padx=5)
    Button(f1, text="Browse...",
           command=lambda: front_var.set(
               filedialog.askopenfilename(
                   title="Select FRONT PDF",
                   filetypes=[("PDF Files", "*.pdf")]
               )
           )).pack(side="left")

    # ----- Info -----
    f_info = Frame(root)
    f_info.pack(fill="x", padx=20, pady=(0, 10))
    Label(f_info,
          text="(Only page 1 will be used, even if it has multiple pages)",
          foreground="gray").pack(anchor="w")

    # ----- Backs -----
    f2 = Frame(root)
    f2.pack(fill="x", padx=20, pady=5)
    Label(f2, text="Backs PDF:").pack(side="left")
    Label(f2, textvariable=backs_var, width=40,
          relief="sunken", anchor="w").pack(side="left", padx=5)
    Button(f2, text="Browse...",
           command=lambda: backs_var.set(
               filedialog.askopenfilename(
                   title="Select BACKS PDF",
                   filetypes=[("PDF Files", "*.pdf")]
               )
           )).pack(side="left")

    # ----- Order -----
    f3 = Frame(root)
    f3.pack(fill="x", padx=20, pady=10)
    Label(f3, text="Back page order:").pack(side="left")
    Combobox(f3, textvariable=order_var,
             values=["Normal", "Reverse"],
             state="readonly", width=12).pack(side="left", padx=5)

    # ----- Info -----
    f4 = Frame(root)
    f4.pack(fill="x", padx=20, pady=5)
    Label(f4, text="Output: Front / Back1 / Front / Back2 / Front / Back3 ...",
          foreground="blue").pack(anchor="w")

    # ----- Build -----
    def do_build():
        fp = front_var.get()
        bp = backs_var.get()

        if not fp or not os.path.isfile(fp):
            messagebox.showerror("Error", "Please select a valid Front PDF.")
            return

        if not bp or not os.path.isfile(bp):
            messagebox.showerror("Error", "Please select a valid Backs PDF.")
            return

        out = filedialog.asksaveasfilename(
            title="Save output PDF as...",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not out:
            return

        try:
            reverse = (order_var.get() == "Reverse")
            count = build_pdf(fp, bp, out, reverse)
            messagebox.showinfo(
                "Done!",
                f"Cards: {count}\n"
                f"Total pages: {count * 2}\n"
                f"Order: Front / Back / Front / Back ...\n\n"
                f"Saved to:\n{out}"
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    f5 = Frame(root)
    f5.pack(fill="x", padx=20, pady=20)
    Button(f5, text="Build PDF", command=do_build).pack(side="right")
    Button(f5, text="Cancel",
           command=root.destroy).pack(side="right", padx=10)

    root.mainloop()


if __name__ == "__main__":
    main()