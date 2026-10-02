import os, uuid, time, json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from converter import convert_pdf, validate_docx

BASE=Path(__file__).resolve().parent
UPLOAD=BASE/"uploads"; OUT=BASE/"outputs"
UPLOAD.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
app=Flask(__name__)
app.config["MAX_CONTENT_LENGTH"]=100*1024*1024

def cleanup():
    cutoff=time.time()-3600
    for folder in (UPLOAD,OUT):
        for p in folder.glob("*"):
            try:
                if p.is_file() and p.stat().st_mtime<cutoff: p.unlink()
            except OSError: pass

@app.get("/")
def home():
    cleanup(); return render_template("index.html")

@app.post("/convert")
def convert():
    cleanup()
    files=request.files.getlist("pdfs")
    files=[f for f in files if f and f.filename]
    if not files: return jsonify(error="Please select at least one PDF."),400
    if len(files)>10: return jsonify(error="Maximum 10 PDFs per batch."),400
    mode=request.form.get("mode","balanced")
    results=[]
    for f in files:
        if Path(f.filename).suffix.lower()!=".pdf":
            results.append({"name":f.filename,"ok":False,"error":"Not a PDF"})
            continue
        job=uuid.uuid4().hex; src=UPLOAD/f"{job}.pdf"
        base=secure_filename(Path(f.filename).stem) or "document"
        out=OUT/f"{base}_{job[:8]}.docx"
        try:
            f.save(src)
            report=convert_pdf(src,out,{
                "mode":mode,
                "ocr":request.form.get("ocr")=="1",
                "images":request.form.get("images")=="1",
                "tables":request.form.get("tables")=="1",
                "verify":request.form.get("verify")=="1",
                "language":request.form.get("language","eng")
            })
            if not out.exists() or not validate_docx(out):
                raise RuntimeError("Generated DOCX did not pass integrity validation.")
            results.append({"name":f.filename,"ok":True,"filename":out.name,
                            "download":f"/download/{out.name}","report":report})
        except Exception as e:
            try: out.unlink(missing_ok=True)
            except OSError: pass
            results.append({"name":f.filename,"ok":False,"error":str(e)})
        finally:
            try: src.unlink(missing_ok=True)
            except OSError: pass
    return jsonify(results=results)

@app.get("/download/<name>")
def download(name):
    safe=secure_filename(name); p=OUT/safe
    if not p.exists(): return "File expired or not found.",404
    r=send_file(p,as_attachment=True,download_name=safe)
    @r.call_on_close
    def remove():
        try:p.unlink(missing_ok=True)
        except OSError:pass
    return r

@app.errorhandler(413)
def too_large(_): return jsonify(error="File too large. Maximum total request size is 100 MB."),413

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
