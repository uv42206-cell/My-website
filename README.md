# RecreatePDF

A mobile-friendly PDF → DOCX reconstruction website.

## Features included
- Single or batch upload (up to 10 PDFs)
- Editable / Balanced / Exact Layout modes
- Text extraction
- Embedded figures/images
- Table reconstruction attempt
- OCR for scanned PDFs
- English + Hindi OCR data in Docker
- Page breaks
- DOCX integrity verification
- Download per file
- Automatic temporary-file cleanup
- Responsive UI
- 100 MB total request limit

## Run locally
```bash
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Docker
```bash
docker build -t recreatepdf .
docker run -p 8080:8080 recreatepdf
```

## Important
"Exact Layout" is the safest mode for visual fidelity, but its pages are image-based and therefore not fully editable.

For a production public service add HTTPS, rate limiting, authentication where needed, disk quotas, malware scanning and stronger sandboxing for untrusted PDFs.
