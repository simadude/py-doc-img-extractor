import os
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. File Type Detection (Magic Numbers)
# ==========================================

def detect_file_type(filepath):
    """
    Determines file type by reading binary headers (magic numbers)
    and inspecting internal ZIP structures.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(32)  # Read first 32 bytes
            
        # 1. PDF Signature
        if header.startswith(b'%PDF'):
            return 'pdf'
        
        # 2. DJVU Signature (AT&T FORM)
        if header.startswith(b'AT&T'):
            return 'djvu'
        
        # 3. OLE2 Signature (Legacy DOC, XLS, PPT)
        # Hex: D0 CF 11 E0 A1 B1 1A E1
        if header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            return 'doc_legacy'
            
        # 4. ZIP Signature (DOCX, EPUB, ZIP)
        # Hex: 50 4B 03 04
        if header.startswith(b'PK\x03\x04'):
            try:
                with zipfile.ZipFile(filepath, 'r') as z:
                    name_list = z.namelist()
                    
                    # Check for EPUB
                    if 'mimetype' in name_list:
                        # Read the content of the mimetype file
                        with z.open('mimetype') as m:
                            mime_content = m.read().decode('utf-8', errors='ignore')
                            if 'epub' in mime_content.lower():
                                return 'epub'
                    
                    # Check for DOCX (Word Open XML)
                    # DOCX usually has a 'word/' folder
                    if any(n.startswith('word/') for n in name_list):
                        return 'docx'
                        
                return 'zip_generic' # Fallback for other zip types
            except zipfile.BadZipFile:
                pass
                
    except Exception as e:
        print(f"Error detection file type: {e}")
        return None
        
    return 'unknown'

# ==========================================
# 2. Extraction Strategies
# ==========================================

def extract_pdf_images_poppler(filepath, output_folder):
    """
    Wraps 'pdfimages' (Poppler utils).
    flag -all ensures format retention (png vs jpeg vs tiff).
    """
    print(f"[PDF] Extracting from {os.path.basename(filepath)}...")
    os.makedirs(output_folder, exist_ok=True)
    
    # Base prefix for extracted files
    image_prefix = os.path.join(output_folder, "img")
    
    # -all : Write JPEG, JPEG2000, JBIG2, and CCITT images in their native format.
    #        Write CMYK, TIFF, PNG otherwise.
    cmd = ['pdfimages', '-all', filepath, image_prefix]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        count = len(os.listdir(output_folder))
        print(f"   -> Extracted {count} images to {output_folder}")
    except subprocess.CalledProcessError as e:
        print(f"   -> Error executing pdfimages. Is poppler-utils installed? {e}")

def extract_zip_container_images(filepath, output_folder):
    """
    Handles DOCX and EPUB.
    Directly unzips media files. 
    Saves Vectors as Vectors (SVG/WMF) and Raster as Raster (JPG/PNG).
    """
    print(f"[ARCHIVE] Extracting from {os.path.basename(filepath)}...")
    os.makedirs(output_folder, exist_ok=True)
    
    # Extensions generally found in 'media' or 'images' folders of these formats
    target_extensions = (
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', 
        '.svg', '.wmf', '.emf' # Include Vector formats
    )
    
    extracted_count = 0
    
    try:
        with zipfile.ZipFile(filepath, 'r') as z:
            for file_info in z.infolist():
                # Check extension
                _, ext = os.path.splitext(file_info.filename)
                if ext.lower() in target_extensions:
                    
                    # Ignore thumbnails specific to Office/Epub meta
                    if 'thumbnail' in file_info.filename.lower():
                        continue
                        
                    # Generate a flat filename to avoid creating deep directories
                    safe_name = f"file_{extracted_count:04d}{ext}"
                    out_path = os.path.join(output_folder, safe_name)
                    
                    # Write file
                    with z.open(file_info) as source, open(out_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    extracted_count += 1
                    
        print(f"   -> Extracted {extracted_count} native assets (Vector & Raster preserved).")
        
    except Exception as e:
        print(f"   -> Error extracting archive: {e}")

def extract_legacy_doc_images(filepath, output_folder):
    """
    1. Converts .doc (OLE) -> .docx (ZIP) using LibreOffice (headless).
    2. Runs ZIP extraction.
    """
    print(f"[DOC] Converting Legacy DOC: {os.path.basename(filepath)}...")
    
    temp_dir = os.path.join(output_folder, "_temp_conversion")
    os.makedirs(temp_dir, exist_ok=True)
    
    # LibreOffice headless conversion command
    # Ensure 'soffice' is in your PATH
    cmd = [
        'soffice', '--headless', '--convert-to', 'docx', 
        '--outdir', temp_dir, filepath
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        
        # Locate the resulting docx (filename might be slightly different)
        found_docx = None
        for f in os.listdir(temp_dir):
            if f.endswith(".docx"):
                found_docx = os.path.join(temp_dir, f)
                break
        
        if found_docx:
            # Hand off to the Zip extractor
            extract_zip_container_images(found_docx, output_folder)
        else:
            print("   -> Conversion failed: Output DOCX not found.")
            
    except FileNotFoundError:
        print("   -> Error: 'soffice' command not found. Install LibreOffice.")
    except subprocess.CalledProcessError as e:
        print(f"   -> libreoffice failed: {e}")
    finally:
        # Clean up temp files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# ==========================================
# 3. DJVU Processing (Threaded Rendering)
# ==========================================

def _djvu_page_task(page_num, filepath, output_folder):
	"""Helper to render one DJVU page"""
	# Save directly to TIFF using ddjvu.
	final_tiff = os.path.join(output_folder, f"page_{page_num}")

	# ddjvu command to render page directly to tiff
	cmd = ['ddjvu', f'-page={page_num}', '-format=tiff', filepath, final_tiff]

	try:
		subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		# Check that ddjvu produced the expected file
		if os.path.exists(final_tiff):
			return True
	except Exception:
		return False
	return False

def extract_djvu_images(filepath, output_folder):
    print(f"[DJVU] Rendering pages from {os.path.basename(filepath)}...")
    os.makedirs(output_folder, exist_ok=True)
    
    # 1. Get Page Count using djvused
    try:
        cmd = ['djvused', '-e', 'n', filepath]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        total_pages = int(result.stdout.strip())
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError):
        print("   -> Error: Could not determine DJVU page count. Is 'djvused' installed?")
        return

    print(f"   -> Found {total_pages} pages. Starting multithreaded render...")

    # 2. Parallel Processing
    max_workers = min(16, os.cpu_count() or 4)
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_djvu_page_task, p, filepath, output_folder) 
            for p in range(1, total_pages + 1)
        ]
        
        for future in as_completed(futures):
            if future.result():
                completed_count += 1

    print(f"   -> Rendered {completed_count}/{total_pages} pages.")

# ==========================================
# 4. Main Router
# ==========================================

def process_document(filepath, output_root="extracted_output"):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    ftype = detect_file_type(filepath)
    
    # Create a specific folder for this file
    safe_dirname = os.path.splitext(os.path.basename(filepath))[0]
    target_folder = os.path.join(output_root, safe_dirname)
    
    print(f"\nProcessing: {filepath}")
    print(f"Detected Type: {ftype}")
    
    if ftype == 'pdf':
        extract_pdf_images_poppler(filepath, target_folder)
    
    elif ftype == 'djvu':
        extract_djvu_images(filepath, target_folder)
        
    elif ftype in ['docx', 'epub', 'zip_generic']:
        extract_zip_container_images(filepath, target_folder)
        
    elif ftype == 'doc_legacy':
        extract_legacy_doc_images(filepath, target_folder)
        
    else:
        print(f"Skipping unknown file type for: {filepath}")

# ==========================================
# Example Usage
# ==========================================

if __name__ == "__main__":
    # You can run this on files without extensions, or renamed files
    
    # Example calls (paths need to exist on your system)
    process_document("example1.pdf") 
    process_document("example2.djvu")
    process_document("example3.djvu")
    process_document("example4.epub")
    pass