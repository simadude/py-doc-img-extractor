# doc-img-extractor
Tool for extracting images from documents like PDF, DJVU, EPUB, DOC, DOCX using system packages.

Tool should save the metadata from what book/file it's coming from.

## Required Packages

This tool relies on several system packages to extract images from different document types. Please ensure you have the following installed:

*   **djvulibre** or **djvulibre-bin**: For DJVU document support (`ddjvu`, `djvused`).
*   **libreoffice**: For DOC/DOCX and EPUB conversion and extraction (`soffice`).
*   **poppler-utils**: For PDF image extraction (`pdfimages`).
*   **unzip**: For extracting images from ZIP-based formats like DOCX and EPUB.

Debian, Ubuntu, Linux Mint and other Debian-based:
```
sudo apt-get update && sudo apt-get install -y djvulibre-bin libreoffice poppler-utils unzip
```

Fedora (and other RHEL-based distributions like CentOS, AlmaLinux, etc.):
```
sudo dnf install -y djvulibre libreoffice poppler-utils unzip
```