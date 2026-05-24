import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from utils.constants import COLORS, UI_FONT_FAMILY
from utils.app_state import AppState

class ToolPanel(ctk.CTkFrame):
    """Clase base para todos los paneles de herramientas."""
    def __init__(self, master, app_root, title: str, desc: str, icon: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_root = app_root
        
        # 1. Encabezado
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(30, 10))
        
        ctk.CTkLabel(
            header, text=f"{icon} {title}",
            font=(UI_FONT_FAMILY, 22, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header, text=desc,
            font=(UI_FONT_FAMILY, 13), text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(5, 0))
        
        # Barra de ayuda / descripción dinámica explicativa unificada
        self.help_messages = {
            "drop": "📁 Zona interactiva: Haz clic para abrir el explorador local o arrastra tus archivos directamente aquí.",
            "process": "🚀 Iniciar: Comienza a procesar el documento con las opciones y configuraciones elegidas.",
            "default": "💡 Pasa el cursor por las opciones o botones interactivos para ver qué hacen."
        }
        
        self.help_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=38, corner_radius=6, border_width=1, border_color=COLORS["border"])
        self.help_frame.pack(fill="x", padx=40, pady=(0, 15))
        self.help_frame.pack_propagate(False)
        
        self.lbl_help = ctk.CTkLabel(
            self.help_frame, 
            text=self.help_messages["default"], 
            font=(UI_FONT_FAMILY, 12, "bold"), 
            text_color=COLORS["text_secondary"]
        )
        self.lbl_help.place(relx=0.5, rely=0.5, anchor="center")
        
        # 2. Zona de drop (se configura en las subclases si se requiere dnd)
        self.drop_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=120, border_color=COLORS["primary"], border_width=2)
        self.drop_frame.pack(fill="x", padx=40, pady=(0, 20))
        self.drop_frame.pack_propagate(False)
        self.drop_frame.configure(cursor="hand2")
        
        self.drop_label = ctk.CTkLabel(
            self.drop_frame, text="📁\nArrastra tus archivos aquí\no haz clic para seleccionar",
            font=(UI_FONT_FAMILY, 14), text_color=COLORS["text_secondary"]
        )
        self.drop_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Enlazar clic
        self.drop_frame.bind("<Button-1>", self.on_drop_click)
        self.drop_label.bind("<Button-1>", self.on_drop_click)
        
        # Enlazar hover-help
        self.bind_hover(self.drop_frame, "drop")
        self.bind_hover(self.drop_label, "drop")
        
        # Área de Output (común a todos)
        bottom_area = ctk.CTkFrame(self, fg_color="transparent")
        bottom_area.pack(fill="x", side="bottom", padx=40, pady=30)

        # Contenedor central (divisible)
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.pack(fill="both", expand=True, padx=40)
        
        # 3. Chips / Opciones específicas se añaden aquí en las subclases
        self.options_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.options_frame.pack(fill="both", expand=True)
        
        # Se elimina la interfaz de destino automático (se pedirá al convertir)
        
        # Botón procesar
        self.btn_process = ctk.CTkButton(
            bottom_area, text="CONVERTIR", font=(UI_FONT_FAMILY, 16, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["secondary"],
            height=44, corner_radius=8, command=self.on_process
        )
        self.btn_process.pack(fill="x")
        
        self.bind_hover(self.btn_process, "process")
        
        # Progreso
        self.progress_bar = ctk.CTkProgressBar(bottom_area, height=6, progress_color=COLORS["secondary"], fg_color=COLORS["bg_card"])
        self.progress_bar.set(0)
        
        self.lbl_status = ctk.CTkLabel(bottom_area, text="", font=(UI_FONT_FAMILY, 12), text_color=COLORS["text_secondary"])
        
        # Zona resultado
        self.result_frame = ctk.CTkFrame(bottom_area, fg_color=COLORS["bg_card"], corner_radius=6)
        self.result_msg = ctk.CTkLabel(self.result_frame, text="", font=(UI_FONT_FAMILY, 14, "bold"))
        self.result_btn = ctk.CTkButton(self.result_frame, text="Abrir carpeta", fg_color="transparent", hover_color=COLORS["hover"], border_width=1, border_color=COLORS["secondary"], command=self.open_output_dir)

    def get_output_dir(self) -> Path:
        return AppState.get().get_output_dir(Path.home() / "Documents")

    def on_drop_click(self, event):
        pass # Implementado en hijos

    def on_process(self):
        pass # Implementado en hijos

    def set_processing(self, processing: bool):
        if processing:
            self.btn_process.configure(state="disabled", fg_color=COLORS["border"], text="Procesando...")
            self.app_root.configure(cursor="watch")
            self.progress_bar.pack(fill="x", pady=(15, 5))
            self.lbl_status.pack()
            self.result_frame.pack_forget()
        else:
            self.btn_process.configure(state="normal", fg_color=COLORS["primary"], text="CONVERTIR")
            self.app_root.configure(cursor="")
            self.progress_bar.pack_forget()
            self.lbl_status.pack_forget()

    def update_progress(self, percent: int, msg: str):
        self.progress_bar.set(percent / 100.0)
        self.lbl_status.configure(text=msg)

    def show_result(self, type_: str, msg: str):
        import tkinter.messagebox
        
        if type_ == "success":
            tkinter.messagebox.showinfo("Éxito", msg)
            self.open_output_dir()
        elif type_ == "error":
            tkinter.messagebox.showerror("Error", msg)
        elif type_ == "warning":
            tkinter.messagebox.showwarning("Advertencia", msg)

    def open_output_dir(self):
        import os
        import platform
        path = str(self.get_output_dir())
        if platform.system() == "Windows":
            os.startfile(path)

    def show_help(self, key: str):
        """Actualiza el texto y color del panel de descripción interactiva."""
        msg = self.help_messages.get(key, self.help_messages.get("default", ""))
        self.lbl_help.configure(text=msg)
        if key == "default":
            self.lbl_help.configure(text_color=COLORS["text_secondary"])
        else:
            self.lbl_help.configure(text_color=COLORS["primary"])

    def bind_hover(self, widget, help_key: str):
        """
        Enlaza de forma segura los eventos de hover (<Enter> y <Leave>) a un widget,
        incluso si es un widget compuesto de CustomTkinter (que lanzaría NotImplementedError).
        Delega recursivamente a elementos internos si es necesario.
        """
        def on_enter(event):
            self.show_help(help_key)
            
        def on_leave(event):
            self.show_help("default")

        try:
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
        except (NotImplementedError, AttributeError, Exception):
            # Si falla, buscar elementos internos comunes de CustomTkinter
            sub_widgets = []
            for attr in ["_canvas", "_text_label", "_label", "_entry", "_button", "_buttons", "_segmented_button", "_option_menu"]:
                if hasattr(widget, attr):
                    val = getattr(widget, attr)
                    if isinstance(val, list):
                        sub_widgets.extend(val)
                    elif val is not None:
                        sub_widgets.append(val)
                        
            try:
                children = widget.winfo_children()
                if children:
                    sub_widgets.extend(children)
            except Exception:
                pass
                
            for sub in sub_widgets:
                self.bind_hover(sub, help_key)
