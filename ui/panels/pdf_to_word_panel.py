import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.pdf_to_word import pdf_to_word

class PdfToWordPanel(ToolPanel):
    def __init__(self, master, app_root):
        super().__init__(
            master, app_root,
            title="PDF a Word",
            desc="Convierte documentos PDF a formato Word editable (.docx)",
            icon="📝"
        )
        self.selected_file = None
        
        # Personalizar mensajes de ayuda explicativos
        self.help_messages = {
            "drop": "📁 Seleccionar archivo: Haz clic o arrastra aquí tu documento PDF para convertirlo.",
            "all": "📝 Todas: Convierte el documento PDF completo de principio a fin.",
            "custom": "✂️ Personalizado: Elige un rango específico de páginas (ej: de la página 1 a la 5) para la conversión.",
            "start": "🔢 Inicio: Número de la primera página que deseas empezar a convertir.",
            "end": "🔢 Fin: Número de la última página que se incluirá en la conversión.",
            "process": "🚀 Iniciar: Convierte las páginas elegidas en un documento Word (.docx) editable.",
            "default": "💡 Pasa el cursor por las opciones del rango de páginas para ver su descripción."
        }
        self.lbl_help.configure(text=self.help_messages["default"])
        
        # Opciones
        self.options_frame.configure(fg_color=COLORS["bg_card"], corner_radius=8)
        self.options_frame.pack_configure(padx=40, pady=20, fill="x", expand=False)
        
        ctk.CTkLabel(self.options_frame, text="Rango de páginas:", font=(UI_FONT_FAMILY, 12, "bold"), text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(15, 5))
        
        # Radio buttons para rango
        self.range_var = ctk.StringVar(value="all")
        rb_all = ctk.CTkRadioButton(self.options_frame, text="Todas", variable=self.range_var, value="all", fg_color=COLORS["primary"], text_color=COLORS["text_secondary"], command=self.toggle_range_inputs)
        rb_all.pack(anchor="w", padx=15, pady=5)
        
        rb_custom = ctk.CTkRadioButton(self.options_frame, text="Personalizado", variable=self.range_var, value="custom", fg_color=COLORS["primary"], text_color=COLORS["text_secondary"], command=self.toggle_range_inputs)
        rb_custom.pack(anchor="w", padx=15, pady=5)
        
        # Inputs para rango personalizado
        self.custom_range_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.custom_range_frame.pack(anchor="w", padx=35, pady=(0, 15))
        
        ctk.CTkLabel(self.custom_range_frame, text="De:", font=(UI_FONT_FAMILY, 12), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 5))
        self.entry_start = ctk.CTkEntry(self.custom_range_frame, width=50, fg_color=COLORS["bg_input"], border_color=COLORS["border"])
        self.entry_start.pack(side="left", padx=(0, 15))
        self.entry_start.insert(0, "1")
        
        ctk.CTkLabel(self.custom_range_frame, text="a:", font=(UI_FONT_FAMILY, 12), text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 5))
        self.entry_end = ctk.CTkEntry(self.custom_range_frame, width=50, fg_color=COLORS["bg_input"], border_color=COLORS["border"])
        self.entry_end.pack(side="left")
        self.entry_end.insert(0, "5")
        
        self.toggle_range_inputs()
        
        self.bind_hover(rb_all, "all")
        self.bind_hover(rb_custom, "custom")
        self.bind_hover(self.entry_start, "start")
        self.bind_hover(self.entry_end, "end")
        
        # Advertencia
        warn = ctk.CTkLabel(self.options_frame, text="⚠️ Puede no preservar formato exacto (depende del PDF)", font=(UI_FONT_FAMILY, 11), text_color=COLORS["warning"])
        warn.pack(anchor="w", padx=15, pady=(0, 15))

    def toggle_range_inputs(self):
        if self.range_var.get() == "all":
            self.entry_start.configure(state="disabled")
            self.entry_end.configure(state="disabled")
        else:
            self.entry_start.configure(state="normal")
            self.entry_end.configure(state="normal")

    def on_drop_click(self, event):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.load_file(path)

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
        self.drop_label.configure(text=f"📄 {self.selected_file.name}\n({self.selected_file.stat().st_size / 1024 / 1024:.1f} MB)", text_color=COLORS["primary"])

    def on_process(self):
        if not self.selected_file:
            self.show_result("error", "Selecciona un archivo PDF primero.")
            return
            
        initial_dir = str(self.get_output_dir())
        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=f"{self.selected_file.stem}.docx",
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
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
        
        if self.range_var.get() == "custom":
            try:
                start = int(self.entry_start.get()) - 1
                end = int(self.entry_end.get())
                if start < 0 or end <= start:
                    raise ValueError()
                kwargs["start_page"] = start
                kwargs["end_page"] = end
            except ValueError:
                self.show_result("error", "Rango de páginas inválido.")
                return

        self.set_processing(True)
        worker = WorkerThread(
            app_root=self.app_root,
            target=pdf_to_word,
            kwargs=kwargs,
            on_progress=self.update_progress,
            on_success=self._on_success,
            on_error=self._on_error
        )
        worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        if result["success"]:
            msg = "Completado exitosamente."
            if result.get("warning"):
                self.show_result("warning", result["warning"])
            else:
                self.show_result("success", msg)
        else:
            self.show_result("error", result.get("error", "Error desconocido."))

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        self.show_result("error", msg)
