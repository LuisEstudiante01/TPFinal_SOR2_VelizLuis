#!/usr/bin/env python3
"""Export the report .docx to PDF with LibreOffice, refreshing the table of contents.

Usage: export_pdf.py <soffice> <input.docx> <output.pdf>

The system python3 starts a headless LibreOffice and re-runs this script with
LibreOffice's own Python (which ships the `uno` module) to drive it: open the
.docx, update every index (the table of contents), and export to PDF.
"""
import glob
import os
import subprocess
import sys
import time

PIPE = "tpfinal_export_pipe"


def find_program_dir(soffice):
    """Return LibreOffice's program/ directory (it holds its python and uno.py)."""
    real = os.path.realpath(soffice)
    base = os.path.dirname(real)
    candidates = [base] + glob.glob(os.path.join(base, "opt", "libreoffice*", "program"))
    for cand in candidates:
        if os.path.exists(os.path.join(cand, "uno.py")):
            return cand
    sys.exit(f"export_pdf: cannot find LibreOffice program/ near {real}")


def drive(docx, pdf):
    """Runs inside LibreOffice's Python."""
    import uno
    from com.sun.star.beans import PropertyValue

    def prop(name, value):
        p = PropertyValue()
        p.Name, p.Value = name, value
        return p

    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    ctx = None
    for _ in range(60):
        try:
            ctx = resolver.resolve(
                f"uno:pipe,name={PIPE};urp;StarOffice.ComponentContext")
            break
        except Exception:
            time.sleep(0.5)
    if ctx is None:
        sys.exit("export_pdf: LibreOffice did not start")
    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)
    doc = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(os.path.abspath(docx)), "_blank", 0,
        (prop("Hidden", True),))
    try:
        indexes = doc.getDocumentIndexes()
        for i in range(indexes.getCount()):
            indexes.getByIndex(i).update()
        doc.refresh()
        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(pdf)),
                       (prop("FilterName", "writer_pdf_Export"),))
    finally:
        doc.close(True)
        try:
            desktop.terminate()
        except Exception:
            pass  # LibreOffice may close the bridge while terminating


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--drive":
        drive(sys.argv[2], sys.argv[3])
        return
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    soffice, docx, pdf = sys.argv[1:]
    program = find_program_dir(soffice)
    office = subprocess.Popen(
        [soffice, "--headless", "--invisible", "--nologo", "--norestore",
         f"--accept=pipe,name={PIPE};urp;"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        subprocess.run([os.path.join(program, "python"), os.path.abspath(__file__),
                        "--drive", docx, pdf], check=True, timeout=300)
    finally:
        try:
            office.wait(timeout=20)
        except subprocess.TimeoutExpired:
            office.kill()


if __name__ == "__main__":
    main()
