import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.pdf_merge import merge_pdfs
from PIL import Image
import fitz  # PyMuPDF
from typing import Optional

class MergePanel(ToolPanel):
    def __init__(self, master, app_root):
        super().__init__(
            master, app_root,
            title="Unir PDFs",
            desc="Combina múltiples archivos PDF en uno solo",
            icon="🔗"
        )
        self.files: list[Path] = []
        self.chips: list[ctk.CTkFrame] = []
        self.thumbnail_cache = {}
        self.dragged_chip = None
        self.drag_start_y = 0
        
        # Diccionario de descripciones explicativas para cada función
        self.help_messages = {
            "add": "➕ Añadir PDFs: Abre un selector para cargar uno o más archivos PDF a la lista.",
            "sort": "🔀 Ordenar Alfabéticamente: Organiza los archivos de la lista por su nombre (de la A a la Z).",
            "clear": "🗑️ Limpiar Todo: Vacía la cola completa para que puedas empezar de nuevo.",
            "process": "🚀 Unir PDFs: Genera el archivo PDF final combinado en el orden mostrado.",
            "drag": "☰ Arrastrar: Haz clic y arrastra esta tarjeta para cambiar el orden de fusión.",
            "delete": "✕ Eliminar: Quita este archivo PDF de la lista de fusión.",
            "default": "💡 Pasa el cursor por las opciones o arrastra las tarjetas para reordenarlas."
        }
        
        self.lbl_help.configure(text=self.help_messages["default"])
        
        # Ocultar drop original (usamos la zona interactiva del list_frame)
        self.drop_frame.pack_forget()
        
        # Contenedor de botones (toolbar premium)
        self.toolbar_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.toolbar_frame.pack(fill="x", padx=40, pady=(0, 10))
        
        # Botón Añadir PDFs
        self.btn_add = ctk.CTkButton(
            self.toolbar_frame, text="➕ Añadir PDFs", font=(UI_FONT_FAMILY, 13, "bold"),
            fg_color="transparent", border_width=2, border_color=COLORS["primary"],
            text_color=COLORS["primary"], hover_color=COLORS["bg_input"],
            command=self.add_files
        )
        self.btn_add.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Botón Ordenar Alfabéticamente
        self.btn_sort = ctk.CTkButton(
            self.toolbar_frame, text="🔀 Ordenar Alfabéticamente", font=(UI_FONT_FAMILY, 13, "bold"),
            fg_color="transparent", border_width=2, border_color=COLORS["secondary"],
            text_color=COLORS["secondary"], hover_color=COLORS["bg_input"],
            command=self.sort_alphabetically
        )
        self.btn_sort.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        # Botón Limpiar Todo
        self.btn_clear = ctk.CTkButton(
            self.toolbar_frame, text="🗑️ Limpiar Todo", font=(UI_FONT_FAMILY, 13, "bold"),
            fg_color="transparent", border_width=2, border_color=COLORS["error"],
            text_color=COLORS["error"], hover_color=COLORS["error_bg"],
            command=self.clear_all
        )
        self.btn_clear.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Asignar hover-help a los controles del toolbar y procesador
        self.bind_hover(self.btn_add, "add")
        self.bind_hover(self.btn_sort, "sort")
        self.bind_hover(self.btn_clear, "clear")
        self.bind_hover(self.btn_process, "process")
        
        # Lista scrolleable
        self.list_frame = ctk.CTkScrollableFrame(self.center_frame, fg_color=COLORS["bg_card"], corner_radius=8, height=320)
        self.list_frame.pack(fill="both", expand=True, padx=40)
        
        self.btn_process.configure(text="UNIR PDFS")
        
        # Registrar drag & drop de archivos desde Windows Explorer si está disponible
        from ui.app import DND_AVAILABLE
        if DND_AVAILABLE:
            from tkinterdnd2 import DND_FILES
            self.list_frame._parent_canvas.drop_target_register(DND_FILES)
            self.list_frame._parent_canvas.dnd_bind("<<Drop>>", self._on_files_dropped)
            self.center_frame._canvas.drop_target_register(DND_FILES)
            self.center_frame._canvas.dnd_bind("<<Drop>>", self._on_files_dropped)

    def show_help(self, key: str):
        """Actualiza el texto y color del panel de descripción interactiva."""
        msg = self.help_messages.get(key, self.help_messages["default"])
        self.lbl_help.configure(text=msg)
        if key == "default":
            self.lbl_help.configure(text_color=COLORS["text_secondary"])
        else:
            self.lbl_help.configure(text_color=COLORS["primary"])


    def get_pdf_thumbnail(self, path: Path) -> tuple[Optional[ctk.CTkImage], int]:
        """Genera una miniatura de la primera página del PDF y obtiene el número de páginas."""
        if path in self.thumbnail_cache:
            return self.thumbnail_cache[path]
            
        try:
            doc = fitz.open(str(path))
            page_count = len(doc)
            if page_count > 0:
                page = doc.load_page(0)
                # Escalar para encajar dentro de 45x60 píxeles manteniendo relación de aspecto
                rect = page.rect
                aspect = rect.width / rect.height
                
                max_w, max_h = 45, 60
                if aspect > (max_w / max_h):
                    w = max_w
                    h = int(max_w / aspect)
                else:
                    h = max_h
                    w = int(max_h * aspect)
                
                zoom = h / rect.height
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                
                doc.close()
                self.thumbnail_cache[path] = (ctk_img, page_count)
                return ctk_img, page_count
            doc.close()
        except Exception as e:
            # Captura silenciosa para evitar alertas molestas; usará fallback visual
            pass
            
        self.thumbnail_cache[path] = (None, 0)
        return None, 0

    def get_file_size_str(self, path: Path) -> str:
        """Retorna el tamaño del archivo formateado en KB o MB."""
        try:
            size_bytes = path.stat().st_size
            if size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            return ""

    def add_files(self):
        """Abre explorador de archivos para añadir PDFs."""
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        for p in paths:
            valid, msg = FileValidator.validate_pdf(p)
            if valid:
                self.files.append(Path(p))
            else:
                self.show_result("error", f"Error con '{Path(p).name}': {msg}")
        self.render_list()

    def _on_files_dropped(self, event):
        """Procesa archivos arrastrados y soltados desde el explorador de Windows."""
        data = event.data
        if not data:
            return
            
        import re
        paths = []
        if '{' in data:
            paths = re.findall(r'\{(.*?)\}', data)
            remaining = re.sub(r'\{(.*?)\}', '', data).split()
            paths.extend(remaining)
        else:
            paths = data.split()
            
        for p in paths:
            p_clean = p.strip()
            if p_clean:
                path_obj = Path(p_clean)
                if path_obj.suffix.lower() == ".pdf":
                    valid, msg = FileValidator.validate_pdf(path_obj)
                    if valid:
                        self.files.append(path_obj)
                    else:
                        self.show_result("error", f"Error con '{path_obj.name}': {msg}")
                else:
                    self.show_result("warning", f"El archivo '{path_obj.name}' no es un PDF y fue omitido.")
        self.render_list()

    def render_list(self):
        """Dibuja completamente la lista de archivos como tarjetas visuales premium."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.chips.clear()
        
        for idx, fpath in enumerate(self.files):
            # Tarjeta contenedor
            chip = ctk.CTkFrame(
                self.list_frame, fg_color=COLORS["bg_input"], corner_radius=8,
                height=80, border_color=COLORS["bg_input"], border_width=2
            )
            chip.pack(fill="x", pady=4, padx=10)
            chip.pack_propagate(False)
            
            # Badge de Número de Orden
            badge = ctk.CTkFrame(chip, width=28, height=28, fg_color=COLORS["primary"], corner_radius=14)
            badge.pack(side="left", padx=(15, 10))
            badge.pack_propagate(False)
            lbl_idx = ctk.CTkLabel(badge, text=str(idx+1), font=(UI_FONT_FAMILY, 12, "bold"), text_color=COLORS["text_primary"])
            lbl_idx.place(relx=0.5, rely=0.5, anchor="center")
            chip.lbl_idx = lbl_idx
            
            # Contenedor de Miniatura
            thumb_frame = ctk.CTkFrame(chip, width=45, height=60, fg_color=COLORS["bg_card"], corner_radius=4)
            thumb_frame.pack(side="left", padx=10, pady=10)
            thumb_frame.pack_propagate(False)
            
            thumb_img, page_count = self.get_pdf_thumbnail(fpath)
            if thumb_img:
                lbl_thumb = ctk.CTkLabel(thumb_frame, image=thumb_img, text="")
                lbl_thumb.place(relx=0.5, rely=0.5, anchor="center")
            else:
                fallback = ctk.CTkFrame(thumb_frame, fg_color=COLORS["error"], corner_radius=4)
                fallback.pack(fill="both", expand=True)
                ctk.CTkLabel(fallback, text="PDF", font=(UI_FONT_FAMILY, 10, "bold"), text_color="#FFFFFF").place(relx=0.5, rely=0.5, anchor="center")
            
            # Textos informativos
            info_frame = ctk.CTkFrame(chip, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=(10, 20), pady=10)
            
            lbl_name = ctk.CTkLabel(
                info_frame, text=fpath.name, font=(UI_FONT_FAMILY, 13, "bold"), 
                text_color=COLORS["text_primary"], anchor="w", justify="left"
            )
            lbl_name.pack(fill="x", anchor="w")
            
            size_str = self.get_file_size_str(fpath)
            pages_str = "1 página" if page_count == 1 else f"{page_count} páginas"
            info_str = f"{pages_str}  •  {size_str}" if size_str else pages_str
            
            lbl_info = ctk.CTkLabel(
                info_frame, text=info_str, font=(UI_FONT_FAMILY, 11), 
                text_color=COLORS["text_secondary"], anchor="w"
            )
            lbl_info.pack(fill="x", anchor="w", pady=(2, 0))
            
            # Tirador visual para arrastrar (Drag Handle)
            lbl_handle = ctk.CTkLabel(chip, text="☰", font=(UI_FONT_FAMILY, 16), text_color=COLORS["text_secondary"], cursor="fleur")
            lbl_handle.pack(side="right", padx=(5, 15))
            self.bind_hover(lbl_handle, "drag")
            
            # Botón Eliminar
            btn_del = ctk.CTkButton(
                chip, text="✕", width=28, height=28, corner_radius=14,
                fg_color="transparent", hover_color=COLORS["error"], text_color=COLORS["text_secondary"],
                font=(UI_FONT_FAMILY, 12, "bold"), command=lambda c=chip: self.remove_chip(c)
            )
            btn_del.pack(side="right", padx=5)
            self.bind_hover(btn_del, "delete")
            
            self.chips.append(chip)
            
            # Configurar bindings de drag a los elementos de la tarjeta
            self.setup_drag_bindings(chip, chip)

    def setup_drag_bindings(self, widget, chip_widget):
        """Asigna eventos de arrastrar recursivamente a todos los elementos excepto botones."""
        widget.bind("<Button-1>", lambda e, c=chip_widget: self.on_drag_start(e, c), add="+")
        widget.bind("<B1-Motion>", lambda e, c=chip_widget: self.on_drag_motion(e, c), add="+")
        widget.bind("<ButtonRelease-1>", lambda e, c=chip_widget: self.on_drag_end(e, c), add="+")
        
        for child in widget.winfo_children():
            if not isinstance(child, ctk.CTkButton):
                self.setup_drag_bindings(child, chip_widget)

    def on_drag_start(self, event, chip):
        """Inicio del arrastre."""
        self.dragged_chip = chip
        self.drag_start_y = event.y_root
        chip.configure(border_color=COLORS["primary"], border_width=2)

    def on_drag_motion(self, event, chip):
        """Durante el arrastre: calcula swaps basados en coordenadas Y."""
        if not self.dragged_chip:
            return
            
        y_root = event.y_root
        target_idx = None
        
        # Encontrar cuál tarjeta está bajo el mouse
        for i, other in enumerate(self.chips):
            if other == self.dragged_chip:
                continue
            
            other_y = other.winfo_rooty()
            other_h = other.winfo_height()
            
            if other_y <= y_root <= other_y + other_h:
                target_idx = i
                break
                
        if target_idx is not None:
            dragged_idx = self.chips.index(self.dragged_chip)
            
            # Swaps en datos y widgets
            self.files[dragged_idx], self.files[target_idx] = self.files[target_idx], self.files[dragged_idx]
            self.chips[dragged_idx], self.chips[target_idx] = self.chips[target_idx], self.chips[dragged_idx]
            
            # Repack en orden actualizado (mantiene mouse grab!)
            for c in self.chips:
                c.pack_forget()
            for c in self.chips:
                c.pack(fill="x", pady=4, padx=10)
                
            self.update_indices()

    def on_drag_end(self, event, chip):
        """Finaliza el arrastre y restablece visuales."""
        if self.dragged_chip:
            self.dragged_chip.configure(border_color=COLORS["bg_input"], border_width=2)
            self.dragged_chip = None

    def remove_chip(self, chip):
        """Elimina una tarjeta y actualiza los badges restantes."""
        if chip in self.chips:
            idx = self.chips.index(chip)
            self.files.pop(idx)
            self.chips.pop(idx)
            chip.destroy()
            self.update_indices()

    def update_indices(self):
        """Actualiza el número de orden de todos los badges visuales en la lista."""
        for idx, chip in enumerate(self.chips):
            if hasattr(chip, "lbl_idx"):
                chip.lbl_idx.configure(text=str(idx+1))

    def sort_alphabetically(self):
        """Ordena los archivos en la lista alfabéticamente."""
        if not self.files:
            return
            
        paired = list(zip(self.files, self.chips))
        paired.sort(key=lambda x: x[0].name.lower())
        
        self.files = [p[0] for p in paired]
        self.chips = [p[1] for p in paired]
        
        for c in self.chips:
            c.pack_forget()
        for c in self.chips:
            c.pack(fill="x", pady=4, padx=10)
            
        self.update_indices()

    def clear_all(self):
        """Limpia todos los archivos cargados."""
        self.files.clear()
        self.render_list()

    def on_process(self):
        """Inicia el proceso de fusión de PDFs en un segundo plano."""
        if len(self.files) < 2:
            self.show_result("error", "Selecciona al menos 2 PDFs para unir.")
            return
            
        initial_dir = str(self.get_output_dir())
        path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile="unido.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            title="Guardar como"
        )
        if not path:
            return
            
        out_path = Path(path)
        from utils.app_state import AppState
        AppState.get().set_output_dir(out_path.parent)
        
        self.set_processing(True)
        worker = WorkerThread(
            app_root=self.app_root,
            target=merge_pdfs,
            kwargs={"input_paths": self.files, "output_path": out_path},
            on_progress=self.update_progress,
            on_success=self._on_success,
            on_error=self._on_error
        )
        worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        if result["success"]:
            self.show_result("success", f"Unidos {result['files_processed']} archivos en {result['pages_total']} páginas.")
            self.files.clear()
            self.render_list()
        else:
            self.show_result("error", result.get("error", "Error desconocido."))

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        self.show_result("error", msg)

