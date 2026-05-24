import customtkinter as ctk
import datetime
from typing import Callable
from utils.constants import COLORS, UI_FONT_FAMILY

class HomePanel(ctk.CTkFrame):
    def __init__(self, master, on_tool_selected: Callable[[str], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_tool_selected = on_tool_selected
        
        # Saludo dinámico
        hour = datetime.datetime.now().hour
        if hour < 12: greeting = "Buenos días"
        elif hour < 19: greeting = "Buenas tardes"
        else: greeting = "Buenas noches"
        
        ctk.CTkLabel(
            self, text=f"{greeting},",
            font=(UI_FONT_FAMILY, 16), text_color=COLORS["text_secondary"]
        ).pack(anchor="w", padx=40, pady=(25, 0))
        
        ctk.CTkLabel(
            self, text="¿Qué deseas convertir hoy?",
            font=(UI_FONT_FAMILY, 28, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=40, pady=(0, 20))
        
        # Barra de descripción informativa dinámica
        self.info_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=40, corner_radius=6, border_width=1, border_color=COLORS["border"])
        self.info_frame.pack(fill="x", padx=40, pady=(10, 20), side="bottom")
        self.info_frame.pack_propagate(False)
        
        self.lbl_info = ctk.CTkLabel(
            self.info_frame, 
            text="💡 Pasa el cursor sobre cualquier herramienta para conocer en detalle lo que hace.", 
            font=(UI_FONT_FAMILY, 12, "bold"), 
            text_color=COLORS["text_secondary"]
        )
        self.lbl_info.place(relx=0.5, rely=0.5, anchor="center")
        
        self.tool_explanations = {
            "pdf_to_word": "📝 PDF a Word: Extrae de forma segura el texto y las imágenes de un PDF para crear un archivo .docx completamente editable.",
            "word_to_pdf": "📑 Word a PDF: Transforma tus plantillas y documentos de Microsoft Word a formato PDF preservando el diseño exacto.",
            "excel_to_pdf": "📊 Excel a PDF: Convierte libros y hojas de cálculo de Excel a formato PDF manteniendo tablas y celdas formateadas.",
            "powerpoint_to_pdf": "📽️ PowerPoint a PDF: Transforma tus presentaciones de diapositivas a un PDF listo para proyectar o compartir.",
            "merge": "🔗 Unir PDFs: Combina dos o más archivos PDF independientes en un solo documento en el orden que tú decidas.",
            "split": "✂️ Dividir PDF: Divide un PDF multipágina en archivos individuales de menor tamaño o extrae rangos específicos.",
            "pdf_to_image": "🖼️ PDF a Imagen: Extrae y renderiza cada página de tu PDF como una imagen JPG o PNG de alta resolución.",
            "image_to_pdf": "📷 Imagen a PDF: Agrupa tus fotos o capturas escaneadas en un único y limpio documento PDF.",
            "compress": "🗜️ Comprimir PDF: Reduce el tamaño de tu PDF optimizando imágenes y streams internos para compartirlo fácilmente.",
            "default": "💡 Pasa el cursor sobre cualquier herramienta para conocer en detalle lo que hace."
        }
        
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=40)
        
        # Configurar rejilla de 24 columnas para soporte de alineación simétrica perfecta
        for col in range(24):
            grid_frame.grid_columnconfigure(col, weight=1)
            
        # Configurar 3 filas uniformes
        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_rowconfigure(1, weight=1)
        grid_frame.grid_rowconfigure(2, weight=1)
        
        tools = [
            ("pdf_to_word", "📝", "PDF a Word", "Convierte documentos PDF a formato Word editable"),
            ("word_to_pdf", "📑", "Word a PDF", "Transforma archivos Word a formato PDF seguro"),
            ("excel_to_pdf", "📊", "Excel a PDF", "Convierte libros de Excel a formato PDF seguro"),
            ("powerpoint_to_pdf", "📽️", "PowerPoint a PDF", "Convierte presentaciones PowerPoint a PDF"),
            ("pdf_to_image", "🖼️", "PDF a Imagen", "Convierte cada página en una imagen JPG/PNG"),
            ("image_to_pdf", "📷", "Imagen a PDF", "Une varias imágenes en un único documento PDF"),
            ("merge", "🔗", "Unir PDFs", "Combina múltiples archivos PDF en uno solo"),
            ("split", "✂️", "Dividir PDF", "Extrae páginas o divide un PDF en partes"),
            ("compress", "🗜️", "Comprimir PDF", "Reduce el tamaño y peso de tus archivos PDF"),
        ]
        
        for i, (tid, icon, title, desc) in enumerate(tools):
            # 9 herramientas totales, grilla perfecta de 3x3
            # Cada tarjeta abarca 8 columnas de las 24 totales
            row = i // 3
            col = (i % 3) * 8
            span = 8
            
            card = ctk.CTkButton(
                grid_frame, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_input"],
                border_width=1, border_color=COLORS["border"],
                corner_radius=10, height=120, text="", command=lambda id=tid: self.on_tool_selected(id)
            )
            card.grid(row=row, column=col, columnspan=span, padx=10, pady=10, sticky="nsew")
            
            # Contenido de la tarjeta (clickeable delegando al botón mediante bindings)
            inner_frame = ctk.CTkFrame(card, fg_color="transparent")
            inner_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.85)
            
            # Bind events para propagar clics
            for widget in [inner_frame]:
                widget.bind("<Button-1>", lambda e, id=tid: self.on_tool_selected(id))
            
            l_icon = ctk.CTkLabel(inner_frame, text=icon, font=(UI_FONT_FAMILY, 28))
            l_icon.pack(pady=(0, 2))
            l_icon.bind("<Button-1>", lambda e, id=tid: self.on_tool_selected(id))
            
            l_title = ctk.CTkLabel(inner_frame, text=title, font=(UI_FONT_FAMILY, 14, "bold"), text_color=COLORS["text_primary"])
            l_title.pack()
            l_title.bind("<Button-1>", lambda e, id=tid: self.on_tool_selected(id))
            
            l_desc = ctk.CTkLabel(
                inner_frame, text=desc, font=(UI_FONT_FAMILY, 11), 
                text_color=COLORS["text_secondary"], wraplength=160
            )
            l_desc.pack()
            l_desc.bind("<Button-1>", lambda e, id=tid: self.on_tool_selected(id))
            
            # Bind events para hover explicativo interactivo
            for w in [card, inner_frame, l_icon, l_title, l_desc]:
                w.bind("<Enter>", lambda e, id=tid: self.show_info(id), add="+")
                w.bind("<Leave>", lambda e: self.show_info("default"), add="+")

    def show_info(self, key: str):
        """Actualiza la barra de descripción informativa."""
        msg = self.tool_explanations.get(key, self.tool_explanations["default"])
        self.lbl_info.configure(text=msg)
        if key == "default":
            self.lbl_info.configure(text_color=COLORS["text_secondary"])
        else:
            self.lbl_info.configure(text_color=COLORS["primary"])
