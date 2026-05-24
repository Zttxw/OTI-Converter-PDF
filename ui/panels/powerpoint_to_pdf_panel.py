import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.powerpoint_to_pdf import powerpoint_to_pdf, detect_powerpoint_engine

class PowerpointToPdfPanel(ToolPanel):
    def __init__(self, master, app_root):
        super().__init__(
            master, app_root,
            title="PowerPoint a PDF",
            desc="Transforma presentaciones PowerPoint a formato PDF seguro",
            icon="📽️"
        )
        self.selected_file = None
        
        # Personalizar mensajes de ayuda explicativos
        self.help_messages = {
            "drop": "📁 Seleccionar archivo: Haz clic o arrastra aquí tu presentación PowerPoint (.pptx, .ppt) para convertirla.",
            "engine": "⚙️ Motor de conversión: Indica si tienes Microsoft PowerPoint o LibreOffice instalado en tu PC para procesar la conversión offline.",
            "process": "🚀 Iniciar: Convierte la presentación PowerPoint cargada a formato PDF de forma segura.",
            "default": "💡 Pasa el cursor sobre el estado del motor para conocer cómo funciona la conversión."
        }
        self.lbl_help.configure(text=self.help_messages["default"])
        
        self.options_frame.configure(fg_color=COLORS["bg_card"], corner_radius=8)
        self.options_frame.pack_configure(padx=40, pady=20, fill="x", expand=False)
        
        self.lbl_engine = ctk.CTkLabel(self.options_frame, text="Detectando motor...", font=(UI_FONT_FAMILY, 12, "bold"))
        self.lbl_engine.pack(pady=15)
        self.bind_hover(self.lbl_engine, "engine")
        
        self._detect_engine()

    def _detect_engine(self):
        engine = detect_powerpoint_engine()
        if engine == "powerpoint":
            self.lbl_engine.configure(text="✅ Microsoft PowerPoint detectado", text_color=COLORS["success"])
        elif engine == "libreoffice":
            self.lbl_engine.configure(text="✅ LibreOffice detectado", text_color=COLORS["success"])
        else:
            self.lbl_engine.configure(text="❌ No se detectó PowerPoint ni LibreOffice.\nInstala uno para usar esta función.", text_color=COLORS["error"])
            self.btn_process.configure(state="disabled")

    def on_drop_click(self, event):
        path = filedialog.askopenfilename(filetypes=[("PowerPoint files", "*.pptx *.ppt")])
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        valid, msg = FileValidator.validate_file(path)
        if not valid:
            self.show_result("error", msg)
            return
            
        if not path.lower().endswith(('.ppt', '.pptx')):
            self.show_result("error", "Selecciona un archivo .ppt o .pptx")
            return
            
        self.selected_file = Path(path)
        self.drop_label.configure(text=f"📄 {self.selected_file.name}\n({self.selected_file.stat().st_size / 1024 / 1024:.1f} MB)", text_color=COLORS["primary"])

    def on_process(self):
        if not self.selected_file:
            self.show_result("error", "Selecciona un archivo PowerPoint primero.")
            return
            
        initial_dir = str(self.get_output_dir())
        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=f"{self.selected_file.stem}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            title="Guardar como"
        )
        if not path:
            return
            
        out_path = Path(path)
        from utils.app_state import AppState
        AppState.get().set_output_dir(out_path.parent)
        
        kwargs = {
            "input_path": self.selected_file,
            "output_path": out_path
        }
        
        self.set_processing(True)
        worker = WorkerThread(
            app_root=self.app_root,
            target=powerpoint_to_pdf,
            kwargs=kwargs,
            on_progress=self.update_progress,
            on_success=self._on_success,
            on_error=self._on_error
        )
        worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        if result["success"]:
            self.show_result("success", f"PDF generado con motor: {result['engine_used']}")
        else:
            self.show_result("error", result.get("error", "Error desconocido."))

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        self.show_result("error", msg)
