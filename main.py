#!/usr/bin/env python3
import os
import subprocess
import shutil

# ==========================================
# 1. Simple File Type Detection via 'file' command
# ==========================================

def detect_file_type(filepath):
    """Use the system 'file' command for reliable MIME/type detection"""
    try:
        result = subprocess.run(
            ['file', '--brief', '--mime-type', filepath],
            capture_output=True, text=True, check=True
        )
        mime = result.stdout.strip().split(';')[0]

        if mime == 'application/pdf':
            return 'pdf'
        if mime == 'image/vnd.djvu' or 'djvu' in mime:
            return 'djvu'
        if mime in ('application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/epub+zip',
                    'application/zip'):
            return 'docx' if mime.endswith('wordprocessingml.document') else 'zip_container'
        if mime == 'application/msword':
            return 'doc_legacy'
    except FileNotFoundError:
        pass  # 'file' not available

    # Fallback: crude magic bytes if 'file' not present
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
        if header.startswith(b'%PDF'):
            return 'pdf'
        if header.startswith(b'AT&TFORM'):
            return 'djvu'
        if header.startswith(b'\xd0\xcf\x11\xe0'):
            return 'doc_legacy'
        if header.startswith(b'PK\x03\x04'):
            return 'zip_container'
    except:
        pass

    return 'unknown'

# ==========================================
# 2. Extraction Using System Tools Only
# ==========================================

def extract_pdf_images(filepath, output_folder):
    print(f"[PDF] Extracting images from {os.path.basename(filepath)}...")
    os.makedirs(output_folder, exist_ok=True)
    prefix = os.path.join(output_folder, "img")
    cmd = ['pdfimages', '-all', filepath, prefix]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def extract_djvu_images(filepath, output_folder):
    print(f"[DJVU] Rendering pages from {os.path.basename(filepath)}...")
    os.makedirs(output_folder, exist_ok=True)

    # Get page count
    try:
        result = subprocess.run(['djvused', '-e', 'n', filepath],
                                capture_output=True, text=True, check=True)
        pages = int(result.stdout.strip())
    except Exception:
        print("   -> Failed to get page count (djvused missing?)")
        return

    print(f"   -> Rendering {pages} pages sequentially...")
    for page in range(1, pages + 1):
        out_tiff = os.path.join(output_folder, f"page_{page:04d}.tif")
        cmd = ['ddjvu', '-format=tiff', f'-page={page}', filepath, out_tiff]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if page % 10 == 0 or page == pages:
            print(f"      -> Rendered {page}/{pages}")

def extract_zip_container(filepath, output_folder):
    print(f"[ZIP/DOCX/EPUB] Extracting media from {os.path.basename(filepath)}...")
    os.makedirs(output_folder, exist_ok=True)
    cmd = ['unzip', '-j', '-o', filepath,
           '*.[pP][nN][gG]', '*.[jJ][pP][gG]', '*.[jJ][pP][eE][gG]',
           '*.[gG][iI][fF]', '*.[bB][mM][pP]', '*.[tT][iI][fF]*',
           '*.[sS][vV][gG]', '*.[wW][mM][fF]', '*.[eE][mM][fF]',
           '-x', '*/thumbnail*',  # skip thumbnails
           '-d', output_folder]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def convert_and_extract_legacy_doc(filepath, output_folder):
    print(f"[DOC] Converting legacy .doc → .docx → extract...")
    temp_dir = os.path.join(output_folder, "_temp_doc")
    os.makedirs(temp_dir, exist_ok=True)

    cmd = ['soffice', '--headless', '--convert-to', 'docx',
           '--outdir', temp_dir, filepath]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    docx_found = None
    for f in os.listdir(temp_dir):
        if f.lower().endswith('.docx'):
            docx_found = os.path.join(temp_dir, f)
            break

    if docx_found:
        extract_zip_container(docx_found, output_folder)
    else:
        print("   -> Conversion failed: no .docx produced")

    shutil.rmtree(temp_dir, ignore_errors=True)

# ==========================================
# 3. Main Router
# ==========================================

def process_document(filepath, output_root="extracted_output"):
    if not os.path.isfile(filepath):
        print(f"File not found: {filepath}")
        return

    ftype = detect_file_type(filepath)
    basename = os.path.splitext(os.path.basename(filepath))[0]
    target_folder = os.path.join(output_root, basename)

    print(f"\nProcessing: {os.path.basename(filepath)} → {ftype}")

    if ftype == 'pdf':
        extract_pdf_images(filepath, target_folder)

    elif ftype == 'djvu':
        extract_djvu_images(filepath, target_folder)

    elif ftype in ('docx', 'zip_container'):
        extract_zip_container(filepath, target_folder)

    elif ftype == 'doc_legacy':
        convert_and_extract_legacy_doc(filepath, target_folder)

    else:
        print(f"   -> Unsupported or unknown type: {ftype}")

# ==========================================
# Example Usage
# ==========================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            process_document(path)
    else:
        # Test with your own files
        process_document("example1.pdf")
        process_document("example2.djvu")
        process_document("example3.djvu")
        process_document("example4.epub")