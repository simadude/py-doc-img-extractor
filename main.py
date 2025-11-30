import fitz  # PyMuPDF library
import io
from PIL import Image
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

def save_image_task(image_filename, image_bytes, image_ext):
    """
    Thread-safe task to save a single image.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.save(image_filename)
        return f"Saved {os.path.basename(image_filename)}"
    except Exception as e:
        return f"Error saving {os.path.basename(image_filename)}: {e}"

def process_djvu_page(page_num, filepath, output_folder):
    """
    Thread-safe task to process a single DJVU page.
    """
    temp_tiff = os.path.join(output_folder, f"temp_{page_num}.tiff")
    final_png = os.path.join(output_folder, f"image_{page_num}.png")

    cmd = [
        'ddjvu', 
        '-format=tiff', 
        f'-page={page_num}', 
        filepath, 
        temp_tiff
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if os.path.exists(temp_tiff):
            with Image.open(temp_tiff) as img:
                img.save(final_png, format="PNG")
            os.remove(temp_tiff)
            return f"Page {page_num} -> Saved"
        else:
            return f"Warning: Page {page_num} failed to extract (ddjvu output missing)."
    except subprocess.CalledProcessError as e:
        return f"ddjvu failed on page {page_num}: {e}"
    except Exception as e:
        if os.path.exists(temp_tiff):
            os.remove(temp_tiff)
        return f"System error on page {page_num}: {e}"

def extract_images_from_pdf(pdf_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    tasks = []
    total_images = 0
    
    for page_index in range(len(doc)):
        page = doc[page_index]
        image_list = page.get_images()
        total_images += len(image_list)
        
        if image_list:
            print(f"Found {len(image_list)} images on page {page_index}")
        
        for image_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_filename = f"{output_folder}/page{page_index}_img{image_index}.{image_ext}"
            tasks.append((image_filename, image_bytes, image_ext))
    
    doc.close()
    
    if not tasks:
        print("No images found in the PDF.")
        return
    
    print(f"Extracted data for {total_images} images. Saving in parallel...")
    
    max_workers = min(32, len(tasks))  # High for I/O-bound saves
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(save_image_task, *task) for task in tasks]
        for future in as_completed(futures):
            print(future.result())
    
    print("PDF image extraction done.")

def get_djvu_page_count(filepath):
    """
    Uses djvused to get the exact number of pages.
    """
    try:
        cmd = ['djvused', '-e', 'n', filepath]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (ValueError, FileNotFoundError):
        pass
    return None

def convert_djvu_safe(filepath, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    # 1. Get the total page count first
    total_pages = get_djvu_page_count(filepath)
    
    if total_pages is None:
        print("Error: Could not determine page count. Is 'djvused' installed?")
        return

    print(f"Document has {total_pages} pages. Starting multithreaded extraction...")

    # 2. Multithreaded page processing
    max_workers = min(16, os.cpu_count() * 2, total_pages)  # Balanced for CPU/I/O/subprocess
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_djvu_page, page_num, filepath, output_folder) 
                   for page_num in range(1, total_pages + 1)]
        
        for future in as_completed(futures):
            print(future.result())

    print("DJVU conversion done.")


extract_images_from_pdf("example1.pdf", "output1")

convert_djvu_safe("example2.djvu", "output2")

convert_djvu_safe("example3.djvu", "output3")