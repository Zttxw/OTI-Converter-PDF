import customtkinter as ctk
import logging
from typing import Optional
from utils.constants import APP_NAME, APP_VERSION, UI_WINDOW_WIDTH, UI_WINDOW_HEIGHT, UI_SIDEBAR_WIDTH, COLORS, UI_FONT_FAMILY
from utils.app_state import AppState

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    TkinterDnD = None
    DND_AVAILABLE = False

logger = logging.getLogger(__name__)

class TitleBar(ctk.CTkFrame):
    """Barra superior personalizada (custom title bar)."""
    def __init__(self, master, title: str):
        super().__init__(master, height=48, fg_color=COLORS["bg_sidebar"], corner_radius=0)
        self.master_window = master
        
        # Evitar que la barra se reduzca a su contenido
        self.pack_propagate(False)
        
        # Logo o ícono OTI
        icon_label = ctk.CTkLabel(self, text="[OTI]", font=(UI_FONT_FAMILY, 14, "bold"), text_color=COLORS["primary"])
        icon_label.pack(side="left", padx=(16, 8))
        
        # Título
        title_label = ctk.CTkLabel(self, text=title, font=(UI_FONT_FAMILY, 14), text_color=COLORS["text_primary"])
        title_label.pack(side="left")
        
        # Botón cerrar
        close_btn = ctk.CTkButton(
            self, text="✕", width=40, height=48, corner_radius=0,
            fg_color="transparent", hover_color="#C0392B", text_color=COLORS["text_secondary"],
            command=self.master_window.destroy, font=("Arial", 14)
        )
        close_btn.pack(side="right")
        
        # Botón minimizar
        min_btn = ctk.CTkButton(
            self, text="━", width=40, height=48, corner_radius=0,
            fg_color="transparent", hover_color=COLORS["accent"], text_color=COLORS["text_secondary"],
            command=self.minimize_window, font=("Arial", 14)
        )
        min_btn.pack(side="right")
        
        # Hacer la barra arrastrable
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)
        icon_label.bind("<Button-1>", self.start_move)
        icon_label.bind("<B1-Motion>", self.do_move)
        title_label.bind("<Button-1>", self.start_move)
        title_label.bind("<B1-Motion>", self.do_move)

    def minimize_window(self):
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(self.master_window.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.master_window.winfo_pointerx() - self.x
        y = self.master_window.winfo_pointery() - self.y
        self.master_window.geometry(f"+{x}+{y}")


class OTIApp(ctk.CTk if not DND_AVAILABLE else type("_DnDCTk", (ctk.CTk, TkinterDnD.DnDWrapper), {})):
    def __init__(self):
        from utils.process_guard import check_single_instance, bring_window_to_front
        import sys
        
        # Capa 1 y 2: Detección de Instancia
        if not check_single_instance():
            bring_window_to_front(APP_NAME)
            import tkinter as tk
            import tkinter.messagebox
            root = tk.Tk()
            root.withdraw()
            tkinter.messagebox.showerror(
                "Instancia Detectada",
                "OTI Converter ya está abierto en este equipo."
            )
            sys.exit(0)

        super().__init__()

        # Evento de cierre para Capa 2 (Limpiar lock file)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        if DND_AVAILABLE:
            self.TkdndVersion = TkinterDnD._require(self)

        # Cargar estado
        AppState.get()._load_from_disk()

        self.title(f"{APP_NAME}")
        self.geometry(f"{UI_WINDOW_WIDTH}x{UI_WINDOW_HEIGHT}")
        self.minsize(900, 550)
        self.configure(fg_color=COLORS["bg_main"])

        # Quitar la barra nativa
        self.overrideredirect(True)

        # Hack en Windows para no perder en la taskbar cuando overrideredirect=True
        # El centrado se hace DENTRO del hack, después del deiconify(), para que no se resetee
        self.after(10, self._set_appwindow)

        from utils.constants import get_resource_path
        try:
            self.iconbitmap(get_resource_path('assets/logo.ico'))
        except Exception:
            pass

        # Barra superior custom
        self.title_bar = TitleBar(self, APP_NAME)
        self.title_bar.pack(fill="x", side="top")

        # Contenedor principal debajo de la barra
        self.main_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=1)

        # Sidebar
        from ui.sidebar import Sidebar
        self.sidebar = Sidebar(self.main_container, on_tool_selected=self.show_panel, width=UI_SIDEBAR_WIDTH)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        # Área de paneles
        self.panel_area = ctk.CTkFrame(self.main_container, fg_color=COLORS["bg_main"], corner_radius=0)
        self.panel_area.grid(row=0, column=1, sticky="nsew")
        self.panel_area.grid_rowconfigure(0, weight=1)
        self.panel_area.grid_columnconfigure(0, weight=1)

        self._panels = {}
        self._active_panel_id = None

        self.report_callback_exception = self.handle_exception

        self._register_panels()
        self.show_panel("home")

    def _set_appwindow(self):
        """Hack para mostrar el ícono en la barra de tareas en overrideredirect.
        El centrado se realiza AQUÍ, después del deiconify(), para evitar que
        el withdraw/deiconify resetee las coordenadas calculadas previamente."""
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x00000080 | 0x00040000
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        self.withdraw()
        self.deiconify()
        # Centrar DESPUÉS del deiconify para que las coordenadas no se reseteen
        self._center_window()

    def _center_window(self):
        """Centra la ventana en la pantalla."""
        self.update_idletasks()
        
        # Usar ctypes para obtener el tamaño de la pantalla física y posicionar la ventana de forma precisa
        # Esto soluciona problemas de escalado (DPI) y evita que la ventana aparezca pegada a los bordes.
        import ctypes
        user32 = ctypes.windll.user32
        
        # Obtener resolución real
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        
        # Obtener tamaño real en píxeles que ocupa la ventana
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Si la ventana no está renderizada aún, intentar predecir usando el factor de escala
        if w < 100:
            import customtkinter as ctk
            w = int(UI_WINDOW_WIDTH * ctk.ScalingTracker.get_window_scaling(self))
            h = int(UI_WINDOW_HEIGHT * ctk.ScalingTracker.get_window_scaling(self))
            
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        
        hwnd = user32.GetParent(self.winfo_id())
        # Mover la ventana (SWP_NOSIZE = 0x0001, SWP_NOZORDER = 0x0004)
        user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0001 | 0x0004)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        import traceback
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"Excepción no capturada en UI:\n{tb_str}")

    def _register_panels(self):
        from ui.home_panel import HomePanel
        from ui.panels.pdf_to_word_panel import PdfToWordPanel
        from ui.panels.word_to_pdf_panel import WordToPdfPanel
        from ui.panels.excel_to_pdf_panel import ExcelToPdfPanel
        from ui.panels.powerpoint_to_pdf_panel import PowerpointToPdfPanel
        from ui.panels.merge_panel import MergePanel
        from ui.panels.split_panel import SplitPanel
        from ui.panels.pdf_to_image_panel import PdfToImagePanel
        from ui.panels.image_to_pdf_panel import ImageToPdfPanel
        from ui.panels.compress_panel import CompressPanel

        self._panels["home"] = HomePanel(self.panel_area, on_tool_selected=self.show_panel)
        self._panels["pdf_to_word"] = PdfToWordPanel(self.panel_area, self)
        self._panels["word_to_pdf"] = WordToPdfPanel(self.panel_area, self)
        self._panels["excel_to_pdf"] = ExcelToPdfPanel(self.panel_area, self)
        self._panels["powerpoint_to_pdf"] = PowerpointToPdfPanel(self.panel_area, self)
        self._panels["merge"] = MergePanel(self.panel_area, self)
        self._panels["split"] = SplitPanel(self.panel_area, self)
        self._panels["pdf_to_image"] = PdfToImagePanel(self.panel_area, self)
        self._panels["image_to_pdf"] = ImageToPdfPanel(self.panel_area, self)
        self._panels["compress"] = CompressPanel(self.panel_area, self)

        for panel in self._panels.values():
            panel.grid_forget()

    def show_panel(self, panel_id: str):
        if panel_id not in self._panels:
            return

        if self._active_panel_id and self._active_panel_id in self._panels:
            self._panels[self._active_panel_id].grid_forget()

        panel = self._panels[panel_id]
        panel.grid(row=0, column=0, sticky="nsew")
        self._active_panel_id = panel_id
        self.sidebar.set_active(panel_id)

    def _on_closing(self):
        """Protocolo de cierre limpio de la aplicación."""
        from utils.process_guard import remove_lock_file
        import sys

        logger.info("Cerrando OTI - Converter...")
        remove_lock_file()
        self.destroy()
        sys.exit(0)