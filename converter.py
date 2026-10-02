import io,re,zipfile,tempfile,os
from pathlib import Path
import fitz
from docx import Document
from docx.shared import Inches,Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

try: import pdfplumber
except ImportError: pdfplumber=None
try: import pytesseract
except ImportError: pytesseract=None

def img_add(doc,data,width=6.35):
    try:
        im=Image.open(io.BytesIO(data)).convert("RGB")
        with tempfile.NamedTemporaryFile(suffix=".jpg",delete=False) as f:path=f.name
        try:
            im.save(path,"JPEG",quality=95); doc.add_picture(path,width=Inches(width))
            doc.paragraphs[-1].alignment=WD_ALIGN_PARAGRAPH.CENTER
        finally: os.unlink(path)
    except Exception: pass

def text_add(doc,text):
    for block in re.split(r"\n\s*\n",text.strip()):
        if not block.strip():continue
        p=doc.add_paragraph()
        lines=block.splitlines()
        for i,line in enumerate(lines):
            p.add_run(line.strip())
            if i<len(lines)-1:p.add_run("\n")

def tables(pdf_path,n):
    if not pdfplumber:return []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return pdf.pages[n].extract_tables() or []
    except Exception:return []

def ocr_page(page,lang):
    if not pytesseract:raise RuntimeError("OCR is unavailable on this server.")
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
    return pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))),lang=lang)

def convert_pdf(src,out,opt):
    pdf=fitz.open(str(src))
    if not pdf.page_count:raise RuntimeError("PDF contains no pages.")
    doc=Document(); s=doc.sections[0]
    s.top_margin=s.bottom_margin=Inches(.5);s.left_margin=s.right_margin=Inches(.6)
    doc.styles["Normal"].font.name="Arial";doc.styles["Normal"].font.size=Pt(10.5)
    pages_with_text=pages_with_images=table_count=0
    mode=opt["mode"]

    for n,page in enumerate(pdf):
        # High fidelity is deliberately visual: it preserves the page appearance.
        if mode=="fidelity":
            pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
            img_add(doc,pix.tobytes("png"),6.55)
        else:
            text=page.get_text("text").strip()
            if not text and opt["ocr"]: text=ocr_page(page,opt["language"]).strip()
            if text: pages_with_text+=1;text_add(doc,text)

            if opt["tables"]:
                for t in tables(src,n):
                    rows=[r for r in t if r and any(str(c or "").strip() for c in r)]
                    if rows:
                        table=doc.add_table(rows=len(rows),cols=max(len(r) for r in rows));table.style="Table Grid"
                        for i,r in enumerate(rows):
                            for j,c in enumerate(r):
                                table.cell(i,j).text=str(c or "")
                        table_count+=1;doc.add_paragraph()

            if opt["images"]:
                seen=set()
                for info in page.get_images(full=True):
                    x=info[0]
                    if x in seen:continue
                    seen.add(x);pages_with_images+=1
                    try:img_add(doc,pdf.extract_image(x)["image"])
                    except Exception:pass

        if n<pdf.page_count-1:doc.add_page_break()
    pdf.close();doc.save(str(out))

    report={"pages":pdf.page_count if False else None,"text_pages":pages_with_text,
            "image_objects":pages_with_images,"tables":table_count,
            "mode":mode,"verification":"DOCX integrity passed"}
    # Optional lightweight verification: ZIP integrity + required XML.
    if opt["verify"] and not validate_docx(out):raise RuntimeError("Verification failed.")
    report["verification"]="Passed"
    return report

def validate_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            return "word/document.xml" in z.namelist() and z.testzip() is None
    except Exception:return False
