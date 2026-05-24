import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.image_to_pdf import images_to_pdf

class ImageToPdfPanel(ToolPanel):
    def __init__(self, master, app_root):
        super().__init__(
            master, app_root,
            title="Imagen a PDF",
            desc="Une varias imágenes en un único documento PDF",
            icon="📷"
        )
        self.files: list[Path] = []
        
        # Personalizar mensajes de ayuda explicativos
        self.help_messages = {
            "size": "📏 Tamaño de página: 'Ajustar imagen' mantiene las dimensiones originales. 'A4' y 'Letter' encajan las fotos en formato estándar de hoja.",
            "add": "➕ Añadir imágenes: Abre un selector local para cargar uno o más archivos de imagen (PNG, JPG, etc.).",
            "up": "↑ Subir: Mueve esta imagen hacia arriba en el orden del PDF resultante.",
            "down": "↓ Bajar: Mueve esta imagen hacia abajo en el orden del PDF resultante.",
            "delete": "✕ Eliminar: Quita esta imagen de la lista de fusión.",
            "process": "🚀 Imagen a PDF: Combina todas las imágenes de la lista en un único documento PDF ordenado.",
            "default": "💡 Pasa el cursor por las opciones o los botones de la lista para ver qué hacen."
        }
        self.lbl_help.configure(text=self.help_messages["default"])
        
        self.drop_frame.pack_forget()
        
        # Opciones
        f_opt = ctk.CTkFrame(self.center_frame, fg_color=COLORS["bg_card"], corner_radius=8)
        f_opt.pack(fill="x", padx=40, pady=(0, 10))
        
        lbl_size = ctk.CTkLabel(f_opt, text="Tamaño de página:", font=(UI_FONT_FAMILY, 12, "bold"))
        lbl_size.pack(side="left", padx=15, pady=10)
        self.size_var = ctk.StringVar(value="auto")
        opt_menu = ctk.CTkOptionMenu(
            f_opt, variable=self.size_var,
            values=["Ajustar imagen", "A4", "Letter"],
            fg_color=COLORS["bg_input"], button_color=COLORS["primary"], button_hover_color=COLORS["secondary"]
        )
        opt_menu.pack(side="left", padx=15, pady=10)
        
        self.bind_hover(opt_menu, "size")
        self.bind_hover(f_opt, "size")
        self.bind_hover(lbl_size, "size")
        
        # Add button
        self.btn_add = ctk.CTkButton(
            self.center_frame, text="+ Añadir Imágenes", font=(UI_FONT_FAMILY, 14, "bold"),
            fg_color="transparent", border_width=2, border_color=COLORS["primary"],
            text_color=COLORS["primary"], hover_color=COLORS["bg_input"],
            command=self.add_files
        )
        self.btn_add.pack(fill="x", padx=40, pady=(0, 10))
        self.bind_hover(self.btn_add, "add")
        
        # List
        self.list_frame = ctk.CTkScrollableFrame(self.center_frame, fg_color=COLORS["bg_card"], corner_radius=8, height=150)
        self.list_frame.pack(fill="both", expand=True, padx=40)
        
        self.chips = []

    def add_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp")])
        for p in paths:
            valid, msg = FileValidator.validate_file(p)
            if valid:
                self.files.append(Path(p))
        self.render_list()

    def render_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.chips.clear()
        
        for idx, fpath in enumerate(self.files):
            chip = ctk.CTkFrame(self.list_frame, fg_color=COLORS["bg_input"], corner_radius=6, height=40)
            chip.pack(fill="x", pady=2, padx=5)
            chip.pack_propagate(False)
            
            ctk.CTkLabel(chip, text=f"[{idx+1}]", font=(UI_FONT_FAMILY, 12, "bold"), text_color=COLORS["primary"]).pack(side="left", padx=10)
            ctk.CTkLabel(chip, text=fpath.name, font=(UI_FONT_FAMILY, 12), text_color=COLORS["text_primary"]).pack(side="left")
            
            btn_del = ctk.CTkButton(chip, text="✕", width=30, height=30, fg_color="transparent", hover_color=COLORS["error"], text_color=COLORS["text_secondary"], command=lambda i=idx: self.remove_file(i))
            btn_del.pack(side="right", padx=(0, 5))
            self.bind_hover(btn_del, "delete")
            
            btn_down = ctk.CTkButton(chip, text="↓", width=30, height=30, fg_color="transparent", hover_color=COLORS["hover"], text_color=COLORS["text_secondary"], command=lambda i=idx: self.move_file(i, 1))
            btn_down.pack(side="right", padx=(0, 2))
            self.bind_hover(btn_down, "down")
            
            btn_up = ctk.CTkButton(chip, text="↑", width=30, height=30, fg_color="transparent", hover_color=COLORS["hover"], text_color=COLORS["text_secondary"], command=lambda i=idx: self.move_file(i, -1))
            btn_up.pack(side="right")
            self.bind_hover(btn_up, "up")
            
            self.chips.append(chip)

    def remove_file(self, idx):
        self.files.pop(idx)
        self.render_list()
        
    def move_file(self, idx, dir):
        if 0 <= idx + dir < len(self.files):
            self.files[idx], self.files[idx+dir] = self.files[idx+dir], self.files[idx]
            self.render_list()

    def on_process(self):
        if not self.files:
            self.show_result("error", "Selecciona al menos 1 imagen.")
            return
            
        initial_dir = str(self.get_output_dir())
        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile="imagenes_unidas.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            title="Guardar como"
        )
        if not path:
            return
            
        out_path = Path(path)
        from utils.app_state import AppState
        AppState.get().set_output_dir(out_path.parent)
        
        sz = self.size_var.get()
        sz_map = {"Ajustar imagen": "fit_image", "A4": "A4", "Letter": "Letter"}
        
        self.set_processing(True)
        worker = WorkerThread(
            self.app_root, images_to_pdf,
            kwargs={"input_paths": self.files, "output_path": out_path, "page_size": sz_map.get(sz, "fit_image")},
            on_progress=self.update_progress, on_success=self._on_success, on_error=self._on_error
        )
        worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        if result["success"]:
            self.show_result("success", f"PDF generado con {result['pages']} imágenes.")
            self.files.clear()
            self.render_list()
        else:
            self.show_result("error", result.get("error", "Error desconocido."))

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        self.show_result("error", msg)
