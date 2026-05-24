import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.pdf_to_image import pdf_to_images

class PdfToImagePanel(ToolPanel):
    def __init__(self, master, app_root):
        super().__init__(
            master, app_root,
            title="PDF a Imagen",
            desc="Convierte cada página en una imagen JPG o PNG",
            icon="🖼️"
        )
        self.selected_file = None
        
        # Personalizar mensajes de ayuda explicativos
        self.help_messages = {
            "drop": "📁 Seleccionar PDF: Haz clic o arrastra un archivo PDF para extraer sus páginas como imágenes.",
            "format": "🖼️ Formato de imagen: JPG ofrece archivos compactos (ideal para fotos). PNG conserva transparencia y máxima nitidez (ideal para texto/capturas).",
            "quality": "🎯 Calidad (DPI): Resolución de salida. 72-96 es estándar para pantalla. 150-300 es ideal para impresión o textos muy definidos.",
            "process": "🚀 PDF a Imagen: Inicia la extracción de páginas como imágenes individuales en la carpeta elegida.",
            "default": "💡 Pasa el cursor por las opciones de formato o calidad para conocer más detalles."
        }
        self.lbl_help.configure(text=self.help_messages["default"])
        
        self.options_frame.configure(fg_color=COLORS["bg_card"], corner_radius=8)
        self.options_frame.pack_configure(padx=40, pady=20, fill="x", expand=False)
        
        # Fila 1: Formato
        f1 = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        f1.pack(fill="x", padx=15, pady=(15, 5))
        lbl_fmt = ctk.CTkLabel(f1, text="Formato:", font=(UI_FONT_FAMILY, 12, "bold"))
        lbl_fmt.pack(side="left")
        
        self.fmt_var = ctk.StringVar(value="jpg")
        rb_jpg = ctk.CTkRadioButton(f1, text="JPG", variable=self.fmt_var, value="jpg", fg_color=COLORS["primary"])
        rb_jpg.pack(side="left", padx=15)
        rb_png = ctk.CTkRadioButton(f1, text="PNG", variable=self.fmt_var, value="png", fg_color=COLORS["primary"])
        rb_png.pack(side="left")
        
        for w in [f1, lbl_fmt, rb_jpg, rb_png]:
            self.bind_hover(w, "format")
        
        # Fila 2: DPI
        f2 = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        f2.pack(fill="x", padx=15, pady=(5, 15))
        lbl_dpi = ctk.CTkLabel(f2, text="Calidad (DPI):", font=(UI_FONT_FAMILY, 12, "bold"))
        lbl_dpi.pack(side="left")
        
        self.dpi_var = ctk.IntVar(value=150)
        for dpi in [72, 96, 150, 300]:
            rb = ctk.CTkRadioButton(f2, text=str(dpi), variable=self.dpi_var, value=dpi, fg_color=COLORS["primary"], command=self._update_badge)
            rb.pack(side="left", padx=(15, 0))
            self.bind_hover(rb, "quality")
            
        self.bind_hover(f2, "quality")
        self.bind_hover(lbl_dpi, "quality")
            
        self.badge = ctk.CTkLabel(f2, text="Alta calidad", fg_color=COLORS["accent"], text_color=COLORS["bg_main"], corner_radius=4, font=(UI_FONT_FAMILY, 10, "bold"))
        self._update_badge()

    def _update_badge(self):
        if self.dpi_var.get() == 300:
            self.badge.pack(side="left", padx=10)
        else:
            self.badge.pack_forget()

    def on_drop_click(self, event):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        valid, msg = FileValidator.validate_file(path)
        if valid:
            self.selected_file = Path(path)
            self.drop_label.configure(text=f"📄 {self.selected_file.name}", text_color=COLORS["primary"])
        else:
            self.show_result("error", msg)

    def on_process(self):
        if not self.selected_file:
            self.show_result("error", "Selecciona un archivo PDF.")
            return
            
        initial_dir = str(self.get_output_dir())
        dir_path = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Seleccionar carpeta de destino para imágenes extraídas"
        )
        if not dir_path:
            return
            
        out_dir = Path(dir_path)
        from utils.app_state import AppState
        AppState.get().set_output_dir(out_dir)
        
        self.set_processing(True)
        worker = WorkerThread(
            self.app_root, pdf_to_images,
            kwargs={
                "input_path": self.selected_file,
                "output_dir": out_dir,
                "format": self.fmt_var.get(),
                "dpi": self.dpi_var.get()
            },
            on_progress=self.update_progress, on_success=self._on_success, on_error=self._on_error
        )
        worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        if result["success"]:
            self.show_result("success", f"Se generaron {result['images_created']} imágenes.")
        else:
            self.show_result("error", result.get("error", "Error desconocido."))

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        self.show_result("error", msg)
