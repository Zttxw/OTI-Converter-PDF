# OTI - Converter

**OTI - Converter** is a desktop utility suite developed in Python aimed at the optimization, conversion, and management of PDF and office documents. It is specifically designed to facilitate document workflows (such as those in municipalities or customer service offices).

## Main Features

*   **PDF to Word:** Accurate conversion from PDF documents to editable `.docx` format.
*   **Compress PDF:** Smart compression engine that reduces the size of heavy documents by cleaning orphaned objects and reducing DPI, ideal for email attachments or government platform uploads.
*   **Word / Excel / PowerPoint to PDF:** Native two-way conversion to PDF.
*   **PDF to Images:** Extracts full pages in `.jpg` or `.png` format.
*   **Images to PDF:** Compiles receipts, photos, or scans into a single PDF document.
*   **Merge and Split PDF:** Combines multiple documents or extracts specific pages.
*   **Security:** Removes PDF passwords (if the original password is known).

## Technologies Used

*   **Language:** Python 3.13
*   **Graphical Interface (UI):** CustomTkinter (modern dark design).
*   **Processing Engines:** `PyMuPDF (fitz)`, `pypdf`, `pdf2docx`, `docx2pdf`, `Pillow`.
*   **Packaging:** PyInstaller and Inno Setup compiler to generate the Windows executable.

## Installation (For Development)

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/oti-converter.git
   cd oti-converter
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the application:
   ```bash
   python main.py
   ```

## Compilation (For Production)

If you wish to package the project to run on computers without Python installed:
1. Run the `build.bat` file. This will create the binaries using PyInstaller and place them in the `dist/OTI-Converter` folder.
2. Run the Inno Setup file `installer.iss` using `ISCC.exe` or the Inno Setup graphical program. 
3. The final `.exe` installer will be saved in the `Output/` folder.

## Contribution

Any improvements, bug fixes, or suggestions for new tools are welcome. Simply open an *Issue* or submit a *Pull Request*.

## License

Developed to facilitate administrative and information technology tasks.
