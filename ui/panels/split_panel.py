import customtkinter as ctk
import logging
from tkinter import filedialog
from pathlib import Path
from ui.tool_panel import ToolPanel
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.file_validator import FileValidator
from utils.thread_worker import WorkerThread
from core.pdf_split import split_by_pages, split_by_ranges, get_pdf_page_count_and_thumbnails

logger = logging.getLogger(__name__)

class SplitPanel(ToolPanel):
    def __init__(self, master, app_root):
        super().__init__(
            master, app_root,
            title="Dividir PDF",
            desc="Extrae páginas o divide un PDF en múltiples partes",
            icon="✂️"
        )
        self.selected_file = None
        
        # Previsualización variables
        self.page_images = []
        self.page_widgets = []
        self.ctk_images = []
        self.total_pages = 0
        self.selected_pages = set()
        
        # Contenedor de previsualización (inicialmente oculto)
        self.preview_frame = ctk.CTkFrame(self.center_frame, fg_color=COLORS["bg_card"], corner_radius=8, border_width=1, border_color=COLORS["border"])
        self.lbl_preview_title = ctk.CTkLabel(self.preview_frame, text="Vista previa de páginas", font=(UI_FONT_FAMILY, 13, "bold"), text_color=COLORS["text_primary"])
        self.lbl_preview_loading = ctk.CTkLabel(self.preview_frame, text="Cargando vista previa...", font=(UI_FONT_FAMILY, 12, "italic"), text_color=COLORS["text_secondary"])
        
        # Contenedor para el selector de rango de previsualización
        self.preview_config_frame = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        
        self.lbl_preview_range = ctk.CTkLabel(
            self.preview_config_frame, text="Mostrar páginas:", 
            font=(UI_FONT_FAMILY, 11), text_color=COLORS["text_secondary"]
        )
        self.lbl_preview_range.pack(side="left", padx=(0, 5))
        
        self.entry_preview_range = ctk.CTkEntry(
            self.preview_config_frame, width=80, height=24,
            font=(UI_FONT_FAMILY, 11),
            fg_color=COLORS["bg_input"], border_color=COLORS["border"]
        )
        self.entry_preview_range.pack(side="left", padx=5)
        self.entry_preview_range.insert(0, "1-12")
        
        self.btn_update_preview = ctk.CTkButton(
            self.preview_config_frame, text="Ver", width=50, height=24,
            font=(UI_FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            command=self.update_preview_range_click
        )
        self.btn_update_preview.pack(side="left", padx=(5, 0))
        
        self.scroll_preview = ctk.CTkScrollableFrame(self.preview_frame, orientation="horizontal", height=135, fg_color="transparent")
        
        # Personalizar mensajes de ayuda explicativos
        self.help_messages = {
            "drop": "📁 Seleccionar PDF: Haz clic o arrastra un archivo PDF para dividirlo.",
            "mode": "🔀 Modo de división: 'Por páginas' divide cada N páginas. 'Por rangos' extrae páginas específicas en nuevos archivos.",
            "value": "🔢 Entrada de valores: Escribe cuántas páginas tendrá cada fragmento o qué rangos deseas extraer (ej: 1-3, 5).",
            "process": "🚀 Dividir PDF: Inicia el proceso de división de páginas y guarda los archivos resultantes.",
            "default": "💡 Pasa el cursor por las opciones de división para comprender el funcionamiento."
        }
        self.lbl_help.configure(text=self.help_messages["default"])
        
        self.options_frame.configure(fg_color=COLORS["bg_card"], corner_radius=8)
        self.options_frame.pack_configure(padx=40, pady=20, fill="x", expand=False)
        
        # Segmented button para el modo
        self.mode_var = ctk.StringVar(value="pages")
        self.seg_button = ctk.CTkSegmentedButton(
            self.options_frame, values=["Por páginas", "Por rangos"],
            command=self.on_mode_change,
            selected_color=COLORS["primary"], selected_hover_color=COLORS["secondary"],
            unselected_color=COLORS["bg_input"]
        )
        self.seg_button.pack(fill="x", padx=15, pady=15)
        self.seg_button.set("Por páginas")
        self.bind_hover(self.seg_button, "mode")
        
        self.input_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.lbl_input = ctk.CTkLabel(self.input_frame, text="Páginas por archivo:", font=(UI_FONT_FAMILY, 12))
        self.lbl_input.pack(side="left")
        
        self.entry_val = ctk.CTkEntry(self.input_frame, fg_color=COLORS["bg_input"], border_color=COLORS["border"])
        self.entry_val.pack(side="left", padx=10, fill="x", expand=True)
        self.entry_val.insert(0, "1")
        self.bind_hover(self.entry_val, "value")
        
        # Enlazar actualización en tiempo real al escribir en la entrada
        self.entry_val.bind("<KeyRelease>", lambda e: self.update_preview_highlights())
        
        # Checkbox para unir rangos en un solo archivo (solo visible en modo rangos)
        self.cb_merge_ranges = ctk.CTkCheckBox(
            self.options_frame, text="Unir todas las páginas seleccionadas en un único archivo PDF",
            font=(UI_FONT_FAMILY, 12),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            border_color=COLORS["border"]
        )
        self.cb_merge_ranges.select()  # Activado por defecto
        
        self.lbl_preview = ctk.CTkLabel(self.options_frame, text="", font=(UI_FONT_FAMILY, 11), text_color=COLORS["warning"])
        self.lbl_preview.pack(anchor="w", padx=15, pady=(0, 15))
        
        self.btn_process.configure(text="DIVIDIR PDF")

    def on_mode_change(self, value):
        if value == "Por páginas":
            self.mode_var.set("pages")
            self.lbl_input.configure(text="Páginas por archivo:")
            self.entry_val.delete(0, 'end')
            self.entry_val.insert(0, "1")
            self.lbl_preview.configure(text="")
            if hasattr(self, 'cb_merge_ranges'):
                self.cb_merge_ranges.pack_forget()
        else:
            self.mode_var.set("ranges")
            self.lbl_input.configure(text="Rangos (ej: 1-3, 5-8, 10):")
            self.entry_val.delete(0, 'end')
            if hasattr(self, 'selected_pages') and self.selected_pages:
                ranges_str = self.pages_to_ranges_string(self.selected_pages)
                self.entry_val.insert(0, ranges_str)
            else:
                self.entry_val.insert(0, "1-3, 5")
            
            if hasattr(self, 'cb_merge_ranges'):
                self.cb_merge_ranges.pack(anchor="w", padx=15, pady=(0, 10))
                
            self.lbl_preview.configure(text="Cada rango generará un archivo separado si la opción de unir está desactivada.")
            # Mover lbl_preview al final
            self.lbl_preview.pack_forget()
            self.lbl_preview.pack(anchor="w", padx=15, pady=(0, 15))
        self.update_preview_highlights()

    def on_drop_click(self, event):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.load_file(path)

    def load_file(self, path: str):
        valid, msg = FileValidator.validate_file(path)
        if not valid:
            self.show_result("error", msg)
            return
        self.selected_file = Path(path)
        self.drop_label.configure(text=f"📄 {self.selected_file.name}", text_color=COLORS["primary"])
        self.start_preview_generation(path)

    def on_process(self):
        if not self.selected_file:
            self.show_result("error", "Selecciona un archivo PDF.")
            return
            
        val = self.entry_val.get().strip()
        if not val:
            self.show_result("error", "Por favor ingresa un valor de división.")
            return

        # 1. VALIDACIÓN estricta de las entradas antes de continuar
        if self.mode_var.get() == "pages":
            try:
                pages = int(val)
            except ValueError:
                self.show_result("error", "El número de páginas por archivo debe ser un número entero positivo.")
                return
                
            if pages <= 0:
                self.show_result("error", "El número de páginas por archivo debe ser mayor a 0.")
                return
                
            if pages > self.total_pages:
                self.show_result("error", f"El número de páginas por archivo ({pages}) no puede ser mayor al total de páginas del PDF ({self.total_pages}).")
                return
        else:
            # Parse y validación de rangos
            ranges = []
            parts = [p.strip() for p in val.split(",") if p.strip()]
            if not parts:
                self.show_result("error", "Por favor ingresa un rango de páginas válido.")
                return
                
            for p in parts:
                if "-" in p:
                    subparts = p.split("-")
                    if len(subparts) != 2:
                        self.show_result("error", f"Formato de rango inválido: '{p}'. Debe ser 'inicio-fin'.")
                        return
                    
                    s_str, e_str = subparts[0].strip(), subparts[1].strip()
                    if not s_str.isdigit() or not e_str.isdigit():
                        self.show_result("error", f"Las páginas de los rangos deben ser números enteros positivos. Rango erróneo: '{p}'.")
                        return
                        
                    s, e = int(s_str), int(e_str)
                    if s <= 0 or e <= 0:
                        self.show_result("error", "Los números de página deben ser mayores a 0.")
                        return
                    if s > e:
                        self.show_result("error", f"Rango inválido '{p}': La página de inicio no puede ser mayor que la página de fin.")
                        return
                    if s > self.total_pages or e > self.total_pages:
                        self.show_result("error", f"El rango '{p}' excede el total de páginas del PDF ({self.total_pages}).")
                        return
                    ranges.append((s, e))
                else:
                    if not p.isdigit():
                        self.show_result("error", f"El número de página debe ser un entero positivo. Valor erróneo: '{p}'.")
                        return
                    
                    page = int(p)
                    if page <= 0:
                        self.show_result("error", "Los números de página deben ser mayores a 0.")
                        return
                    if page > self.total_pages:
                        self.show_result("error", f"La página {page} excede el total de páginas del PDF ({self.total_pages}).")
                        return
                    ranges.append((page, page))

        # 2. Selección de la carpeta de destino después de pasar la validación
        initial_dir = str(self.get_output_dir())
        dir_path = filedialog.askdirectory(
            initialdir=initial_dir,
            title="Seleccionar carpeta de destino para PDFs divididos"
        )
        if not dir_path:
            return
            
        out_dir = Path(dir_path)
        from utils.app_state import AppState
        AppState.get().set_output_dir(out_dir)
        
        self.set_processing(True)
        
        if self.mode_var.get() == "pages":
            worker = WorkerThread(
                self.app_root, split_by_pages,
                kwargs={"input_path": self.selected_file, "output_dir": out_dir, "pages_per_file": pages},
                on_progress=self.update_progress, on_success=self._on_success, on_error=self._on_error
            )
            worker.start()
        else:
            merge_val = bool(self.cb_merge_ranges.get())
            worker = WorkerThread(
                self.app_root, split_by_ranges,
                kwargs={
                    "input_path": self.selected_file, 
                    "output_dir": out_dir, 
                    "ranges": ranges,
                    "merge_ranges": merge_val
                },
                on_progress=self.update_progress, on_success=self._on_success, on_error=self._on_error
            )
            worker.start()

    def _on_success(self, result: dict):
        self.set_processing(False)
        if result["success"]:
            self.show_result("success", f"Se generaron {result['files_created']} archivos.")
        else:
            self.show_result("error", result.get("error", "Error desconocido."))

    def _on_error(self, msg: str, tb: str):
        self.set_processing(False)
        self.show_result("error", msg)

    def start_preview_generation(self, pdf_path: str, page_range: str = "1-12"):
        # Limpiar miniaturas y elementos previos
        for widget in self.page_widgets:
            widget.destroy()
        self.page_widgets.clear()
        self.page_images.clear()
        self.ctk_images.clear()
        self.total_pages = 0
        self.selected_pages.clear()
        
        # Sincronizar campo de entrada del selector de rango
        self.entry_preview_range.delete(0, 'end')
        self.entry_preview_range.insert(0, page_range)
        
        # Mostrar el contenedor de previsualización y el mensaje de carga
        self.options_frame.pack_forget()
        self.preview_frame.pack(fill="x", padx=40, pady=(10, 10))
        self.options_frame.pack(fill="x", padx=40, pady=(0, 20))
        
        # Configurar rejilla interna
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(1, weight=1)
        
        self.lbl_preview_title.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))
        self.preview_config_frame.grid(row=0, column=1, sticky="e", padx=15, pady=(10, 5))
        
        # Mostrar cargando ocupando ambas columnas
        self.lbl_preview_loading.grid(row=1, column=0, columnspan=2, pady=30)
        self.scroll_preview.grid_forget()
        
        # Iniciar WorkerThread para extraer número de páginas y miniaturas en segundo plano
        worker = WorkerThread(
            self.app_root, get_pdf_page_count_and_thumbnails,
            kwargs={
                "pdf_path": pdf_path,
                "page_range": page_range,
                "return_tuples": True
            },
            on_success=self.on_preview_success,
            on_error=self.on_preview_error
        )
        worker.start()

    def update_preview_range_click(self):
        if not self.selected_file:
            return
        r = self.entry_preview_range.get().strip()
        if not r:
            return
        self.start_preview_generation(str(self.selected_file), page_range=r)

    def load_new_preview_range(self, r: str):
        if not self.selected_file:
            return
        self.entry_preview_range.delete(0, 'end')
        self.entry_preview_range.insert(0, r)
        self.start_preview_generation(str(self.selected_file), page_range=r)

    def on_preview_success(self, result: dict):
        if not result["success"]:
            self.on_preview_error(result.get("error", "Error cargando vista previa"), "")
            return
            
        self.total_pages = result["total_pages"]
        self.page_images = result["thumbnails"]  # Esto contiene tuplas (page_num, img)
        
        self.lbl_preview_loading.grid_forget()
        self.scroll_preview.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        
        # Actualizar el título con el total real de páginas
        self.lbl_preview_title.configure(text=f"Vista previa de páginas ({self.total_pages} páginas detectadas)")
        
        # Encontrar cuál fue el último número de página cargado
        max_page_loaded = 0
        if self.page_images:
            max_page_loaded = max(p_num for p_num, _ in self.page_images)
            
        # Generar las miniaturas de manera interactiva en la UI
        for idx, (page_num, img) in enumerate(self.page_images):
            card = ctk.CTkFrame(
                self.scroll_preview, fg_color=COLORS["bg_input"], 
                corner_radius=6, border_width=0, border_color=COLORS["border"],
                width=85, height=120
            )
            card.grid(row=0, column=idx, padx=5, pady=5)
            
            # Configurar cursor hand2 para interactividad
            card.configure(cursor="hand2")
            
            # Crear y almacenar el CTkImage para evitar que sea recolectado por el GC
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(70, 90))
            self.ctk_images.append(ctk_img)
            
            l_img = ctk.CTkLabel(card, image=ctk_img, text="", cursor="hand2")
            l_img.pack(pady=(5, 2))
            
            l_num = ctk.CTkLabel(card, text=f"Pág. {page_num}", font=(UI_FONT_FAMILY, 10, "bold"), text_color=COLORS["text_secondary"], cursor="hand2")
            l_num.pack()
            
            # Vincular evento de clic en cualquiera de las áreas de la tarjeta
            for w in (card, l_img, l_num):
                w.bind("<Button-1>", lambda e, p_num=page_num: self.toggle_page_selection(p_num))
                
            self.page_widgets.append(card)
            
        # Si hay páginas restantes después del último elemento cargado, colocar tarjeta de indicador restante
        if max_page_loaded < self.total_pages:
            remaining = self.total_pages - max_page_loaded
            card = ctk.CTkFrame(
                self.scroll_preview, fg_color=COLORS["bg_input"], 
                corner_radius=6, border_width=0, border_color=COLORS["border"],
                width=85, height=120
            )
            card.grid(row=0, column=len(self.page_images), padx=5, pady=5)
            card.configure(cursor="hand2")
            
            l_rem = ctk.CTkLabel(
                card, text=f"+ {remaining}\npágs.", 
                font=(UI_FONT_FAMILY, 12, "bold"), 
                text_color=COLORS["primary"],
                cursor="hand2"
            )
            l_rem.place(relx=0.5, rely=0.5, anchor="center")
            
            # Calcular el siguiente rango de páginas para cargar
            loaded_count = len(self.page_images)
            block_size = max(12, loaded_count)
            next_start = max_page_loaded + 1
            next_end = min(self.total_pages, next_start + block_size - 1)
            next_range = f"{next_start}-{next_end}"
            
            # Vincular clics de la tarjeta para cargar el siguiente bloque
            for w in (card, l_rem):
                w.bind("<Button-1>", lambda e, r=next_range: self.load_new_preview_range(r))
                
            self.page_widgets.append(card)
            
        # Aplicar el colorizado interactivo inicial de los bordes
        self.update_preview_highlights()
        
        # Forzar actualización del layout de Tkinter y configurar correctamente la scrollregion del Canvas
        self.scroll_preview.update_idletasks()
        self.scroll_preview._parent_canvas.configure(scrollregion=self.scroll_preview._parent_canvas.bbox("all"))

    def on_preview_error(self, msg: str, tb: str):
        # Fallback seguro: ocultar el panel de previsualización ante cualquier error y logear
        self.preview_frame.pack_forget()
        logger.warning(f"No se pudo cargar la vista previa del PDF: {msg}")

    def update_preview_highlights(self):
        """
        Coloriza dinámicamente los bordes de las miniaturas de las páginas según los rangos
        o divisiones especificadas en la entrada de texto por el usuario en tiempo real.
        """
        if not self.selected_file or self.total_pages == 0 or not self.page_widgets:
            return
            
        val = self.entry_val.get().strip()
        
        # Limpiar bordes primero
        for widget in self.page_widgets:
            try:
                widget.configure(border_width=0, border_color=COLORS["border"])
            except Exception:
                pass
                
        if not val:
            if self.mode_var.get() == "ranges":
                self.selected_pages.clear()
            return
            
        if self.mode_var.get() == "pages":
            try:
                pages_per_file = int(val)
                if pages_per_file <= 0:
                    return
                # Resaltar en grupos con colores alternos para mayor claridad visual
                for idx, (page_num, _) in enumerate(self.page_images):
                    if idx < len(self.page_widgets):
                        group_idx = (page_num - 1) // pages_per_file
                        color = COLORS["primary"] if group_idx % 2 == 0 else COLORS["secondary"]
                        self.page_widgets[idx].configure(border_width=2, border_color=color)
            except ValueError:
                # Entrada temporalmente inválida mientras escribe, se ignora de forma segura
                pass
        else:
            # Modo por rangos - Sincronizar conjunto interno
            new_selection = set()
            parts = [p.strip() for p in val.split(",") if p.strip()]
            for idx, p in enumerate(parts):
                # Usar colores alternos por cada rango
                color = COLORS["primary"] if idx % 2 == 0 else COLORS["secondary"]
                try:
                    if "-" in p:
                        s, e = p.split("-")
                        start, end = int(s), int(e)
                    else:
                        start = end = int(p)
                        
                    # Aplicar borde a las páginas que caen dentro del rango especificado
                    for p_num in range(start, end + 1):
                        for widget_idx, (loaded_p_num, _) in enumerate(self.page_images):
                            if loaded_p_num == p_num and widget_idx < len(self.page_widgets):
                                self.page_widgets[widget_idx].configure(border_width=2, border_color=color)
                        if 1 <= p_num <= self.total_pages:
                            new_selection.add(p_num)
                except ValueError:
                    # Rango incompleto o inválido mientras escribe, ignorar de forma segura
                    continue
            self.selected_pages = new_selection

    def toggle_page_selection(self, page_num: int):
        if self.mode_var.get() == "pages":
            # Cambiar automáticamente a modo por rangos al hacer clic
            self.selected_pages = {page_num}
            self.seg_button.set("Por rangos")
            self.on_mode_change("Por rangos")
        else:
            # Alternar la selección del elemento
            if page_num in self.selected_pages:
                self.selected_pages.remove(page_num)
            else:
                self.selected_pages.add(page_num)
                
            ranges_str = self.pages_to_ranges_string(self.selected_pages)
            self.entry_val.delete(0, 'end')
            self.entry_val.insert(0, ranges_str)
            self.update_preview_highlights()

    def pages_to_ranges_string(self, pages) -> str:
        if not pages:
            return ""
        sorted_pages = sorted(list(pages))
        ranges = []
        start = sorted_pages[0]
        end = sorted_pages[0]
        
        for p in sorted_pages[1:]:
            if p == end + 1:
                end = p
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = p
                end = p
        
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
            
        return ", ".join(ranges)
