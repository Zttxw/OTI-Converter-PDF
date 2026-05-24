import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
import logging
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.pdf_compress import compress_pdf

logger = logging.getLogger(__name__)

class CompressPanel(ToolPanel):
    def __init__(self, master, app_root, **kwargs):
        super().__init__(
            master, app_root,
            title="Comprimir PDF",
            desc="Reduce el tamaño de tu PDF optimizando imágenes y streams internos.",
            icon="🗜️",
            **kwargs
        )
        self.selected_file = None
        self.output_dir = None
        
        # Personalizar descripciones explicativas de hover
        self.help_messages = {
            "drop": "📁 Seleccionar PDF: Haz clic o arrastra un archivo PDF para optimizar su peso.",
            "quality": "⚡ Nivel de compresión: Elige entre Alta calidad, Balanceada (recomendado) o Máxima compresión.",
            "process": "🚀 Iniciar: Elige la carpeta destino y optimiza el archivo PDF seleccionado.",
            "default": "💡 Pasa el cursor por las opciones de compresión para ver más detalles."
        }
        self.lbl_help.configure(text=self.help_messages["default"])
        
        # Estilo del panel de opciones
        self.options_frame.configure(fg_color=COLORS["bg_card"], corner_radius=8)
        self.options_frame.pack_configure(padx=40, pady=20, fill="x", expand=False)
        
        # Título de las opciones
        ctk.CTkLabel(
            self.options_frame, text="Nivel de compresión:",
            font=(UI_FONT_FAMILY, 12, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        # Variables de calidad
        self.quality_var = ctk.StringVar(value="media")
        self.quality_options = ["🟢 Alta calidad", "🟡 Balanceada", "🔴 Máxima compresión"]
        self.quality_map = {
            "🟢 Alta calidad": "alta",
            "🟡 Balanceada": "media",
            "🔴 Máxima compresión": "baja"
        }
        self.quality_desc = {
            "alta": "Compresión ligera. Ideal para preservar la máxima nitidez en textos y gráficos vectoriales.",
            "media": "Recomendado. Excelente equilibrio entre reducción de tamaño de archivo y calidad visual de imágenes.",
            "baja": "Máxima compresión. Reduce agresivamente la resolución y calidad de imágenes para un peso mínimo."
        }
        
        # Segmented button para calidad
        self.seg_quality = ctk.CTkSegmentedButton(
            self.options_frame, values=self.quality_options,
            command=self.on_quality_change,
            selected_color=COLORS["primary"], selected_hover_color=COLORS["secondary"],
            unselected_color=COLORS["bg_input"], text_color=COLORS["text_secondary"]
        )
        self.seg_quality.pack(fill="x", padx=15, pady=(5, 10))
        self.seg_quality.set("🟡 Balanceada")
        
        # Descripción dinámica del nivel de calidad seleccionado
        self.lbl_quality_desc = ctk.CTkLabel(
            self.options_frame, text=self.quality_desc["media"],
            font=(UI_FONT_FAMILY, 12), text_color=COLORS["text_secondary"],
            justify="left", wraplength=600
        )
        self.lbl_quality_desc.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Enlazar hover-help
        self.bind_hover(self.seg_quality, "quality")
        self.bind_hover(self.lbl_quality_desc, "quality")
        
        # Personalizar botón e inicio de procesamiento
        self.btn_process.configure(text="COMPRIMIR PDF", state="disabled")
        
        # Diseñar el result_frame personalizado
        self.result_frame.configure(fg_color=COLORS["bg_card"], border_width=1, border_color=COLORS["border"])
        
        self.lbl_result_title = ctk.CTkLabel(
            self.result_frame, text="", font=(UI_FONT_FAMILY, 14, "bold")
        )
        self.lbl_result_title.pack(anchor="w", padx=20, pady=(15, 5))
        
        self.lbl_sizes = ctk.CTkLabel(
            self.result_frame, text="", font=(UI_FONT_FAMILY, 12),
            text_color=COLORS["text_primary"], justify="left"
        )
        self.lbl_sizes.pack(anchor="w", padx=20, pady=2)
        
        self.lbl_reduction = ctk.CTkLabel(
            self.result_frame, text="", font=(UI_FONT_FAMILY, 13, "bold")
        )
        self.lbl_reduction.pack(anchor="w", padx=20, pady=(2, 15))
        
        self.btn_open_folder = ctk.CTkButton(
            self.result_frame, text="Abrir carpeta", font=(UI_FONT_FAMILY, 12, "bold"),
            fg_color="transparent", hover_color=COLORS["hover"], border_width=1, border_color=COLORS["secondary"],
            text_color=COLORS["secondary"], height=32, corner_radius=6, command=self._open_output_folder
        )
        # El botón de abrir carpeta se packeará dinámicamente
        
        # Registrar Drag & Drop si está disponible
        from ui.app import DND_AVAILABLE
        if DND_AVAILABLE:
            from tkinterdnd2 import DND_FILES
            try:
                self.drop_frame.drop_target_register(DND_FILES)
                self.drop_frame.dnd_bind("<<Drop>>", self._on_file_dropped)
                self.drop_label.drop_target_register(DND_FILES)
                self.drop_label.dnd_bind("<<Drop>>", self._on_file_dropped)
            except Exception as e:
                logger.error(f"Error al registrar Drag & Drop en CompressPanel: {e}")

    def on_quality_change(self, value):
        quality_key = self.quality_map.get(value, "media")
        self.quality_var.set(quality_key)
        self.lbl_quality_desc.configure(text=self.quality_desc[quality_key])

    def on_drop_click(self, event):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.load_file(path)

    def _on_file_dropped(self, event):
        data = event.data
        if not data:
            return
        path = data.strip()
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        
        path_obj = Path(path)
        if path_obj.suffix.lower() == ".pdf":
            self.load_file(path)
        else:
            self.show_result("error", "El archivo arrastrado no es un PDF.")

    def load_file(self, path: str):
        valid, msg = FileValidator.validate_file(path)
        if not valid:
            self.show_result("error", msg)
            return
        valid, msg = FileValidator.validate_magic_bytes(path, 'pdf')
        if not valid:
            self.show_result("error", msg)
            return
            
        self.selected_file = Path(path)
        size_mb = self.selected_file.stat().st_size / 1024 / 1024
        self.drop_label.configure(
            text=f"📄 {self.selected_file.name}\n({size_mb:.2f} MB)",
            text_color=COLORS["primary"]
        )
        self.btn_process.configure(state="normal")
        self.result_frame.pack_forget()

    def update_progress(self, progress_val: float, msg: str):
        """Sobrescribe la actualización de progreso para soportar valores de callback entre 0.0 y 1.0."""
        self.progress_bar.set(progress_val)
        self.lbl_status.configure(text=msg)

    def on_process(self):
        if not self.selected_file:
            self.show_result("error", "Selecciona un archivo PDF primero.")
            return
            
        # Solicitar directorio de destino
        initial_dir = str(self.get_output_dir())
        dir_path = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Seleccionar carpeta para guardar PDF comprimido"
        )
        if not dir_path:
            return
            
        self.output_dir = Path(dir_path)
        
        # Guardar en AppState
        from utils.app_state import AppState
        AppState.get().set_output_dir(self.output_dir)
        
        # Construir ruta de salida única
        out_name = f"{self.selected_file.stem}_comprimido.pdf"
        out_path = self.output_dir / out_name
        
        # Si ya existe, se sobrescribirá directamente (no usamos get_safe_output_path)
        
        kwargs = {
            "input_path": self.selected_file,
            "output_path": out_path,
            "quality": self.quality_var.get()
        }
        
        self.set_processing(True)
        
        # Lanzar hilo secundario WorkerThread
        worker = WorkerThread(
            app_root=self.app_root,
            target=compress_pdf,
            kwargs=kwargs,
            on_progress=self.update_progress,
            on_success=self._on_success,
            on_error=self._on_error
        )
        worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        
        orig_mb = result["original_size"] / 1024 / 1024
        final_mb = result["compressed_size"] / 1024 / 1024
        
        # Limpiar empaquetado del botón por si acaso
        self.btn_open_folder.pack_forget()
        
        if result.get("already_optimized"):
            # Caso en que ya estaba optimizado (advertencia / warning amarillo)
            self.lbl_result_title.configure(
                text="⚠️ PDF ya optimizado",
                text_color=COLORS["warning"]
            )
            self.lbl_sizes.configure(
                text=f"El archivo ya contaba con una compresión óptima.\nNo se realizaron modificaciones para evitar inflar el peso."
            )
            self.lbl_reduction.configure(
                text=f"Tamaño actual: {orig_mb:.2f} MB",
                text_color=COLORS["text_secondary"]
            )
            self.btn_open_folder.pack(side="right", padx=20, pady=(0, 15))
            self.result_frame.pack(fill="x", pady=15)
            self.show_result("warning", "El archivo ya estaba optimizado. Se copió sin modificaciones.")
        else:
            # Caso de compresión exitosa
            self.lbl_result_title.configure(
                text="⚡ Compresión completada",
                text_color=COLORS["primary"]
            )
            self.lbl_sizes.configure(
                text=f"Tamaño original: {orig_mb:.2f} MB  •  Tamaño final: {final_mb:.2f} MB"
            )
            self.lbl_reduction.configure(
                text=f"¡Reducción del {result['reduction_percent']}% en espacio!",
                text_color=COLORS["secondary"]
            )
            self.btn_open_folder.pack(side="right", padx=20, pady=(0, 15))
            self.result_frame.pack(fill="x", pady=15)
            self.show_result("success", "El PDF ha sido comprimido exitosamente.")

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        # Interceptar el error específico de cifrado en el traceback
        if "El PDF está protegido con contraseña" in tb or "El PDF está protegido con contraseña" in msg:
            msg = "El PDF está protegido con contraseña. No se puede procesar."
        self.show_result("error", msg)

    def _open_output_folder(self):
        if self.output_dir:
            import os
            import platform
            path = str(self.output_dir)
            try:
                if platform.system() == "Windows":
                    os.startfile(path)
            except Exception as e:
                logger.error(f"Error al abrir la carpeta destino: {e}")
