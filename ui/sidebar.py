import customtkinter as ctk
import webbrowser
from typing import Callable, Optional
from utils.constants import APP_NAME, APP_VERSION, COLORS, UI_FONT_FAMILY

SIDEBAR_TOOLS = [
    {"id": "home", "icon": "🏠", "label": "Inicio", "category": None},
    {"id": "sep_convert", "icon": "", "label": "— CONVERTIR —", "category": "separator"},
    {"id": "pdf_to_word", "icon": "📝", "label": "PDF → Word", "category": "convert"},
    {"id": "word_to_pdf", "icon": "📑", "label": "Word → PDF", "category": "convert"},
    {"id": "excel_to_pdf", "icon": "📊", "label": "Excel → PDF", "category": "convert"},
    {"id": "powerpoint_to_pdf", "icon": "📽️", "label": "PowerPoint → PDF", "category": "convert"},
    {"id": "sep_organize", "icon": "", "label": "— ORGANIZAR —", "category": "separator"},
    {"id": "merge", "icon": "🔗", "label": "Unir PDFs", "category": "organize"},
    {"id": "split", "icon": "✂️", "label": "Dividir PDF", "category": "organize"},
    {"id": "compress", "icon": "🗜️", "label": "Comprimir PDF", "category": "organize"},
    {"id": "sep_images", "icon": "", "label": "— IMÁGENES —", "category": "separator"},
    {"id": "pdf_to_image", "icon": "🖼️", "label": "PDF → Imagen", "category": "images"},
    {"id": "image_to_pdf", "icon": "📷", "label": "Imagen → PDF", "category": "images"},
]

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_tool_selected: Callable[[str], None], width: int, **kwargs):
        super().__init__(
            master, width=width, fg_color=COLORS["bg_sidebar"], corner_radius=0, **kwargs
        )
        self.grid_propagate(False)
        self._on_tool_selected = on_tool_selected
        self._buttons = {}
        self._active_id = None

        # Scroll para las herramientas
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["hover"]
        )
        self._scroll.pack(fill="both", expand=True, pady=(10, 0))

        self._build_tools()
        self._build_footer()

    def _build_tools(self):
        for tool in SIDEBAR_TOOLS:
            tid = tool["id"]
            if tool["category"] == "separator":
                lbl = ctk.CTkLabel(
                    self._scroll, text=tool["label"],
                    font=(UI_FONT_FAMILY, 11, "bold"), text_color=COLORS["text_secondary"],
                    anchor="w"
                )
                lbl.pack(fill="x", padx=15, pady=(15, 5))
                continue

            btn = ctk.CTkButton(
                self._scroll,
                text=f"  {tool['icon']}   {tool['label']}",
                font=(UI_FONT_FAMILY, 14), anchor="w",
                height=40, corner_radius=0,
                fg_color="transparent",
                hover_color=COLORS["hover"],
                text_color=COLORS["text_secondary"],
                command=lambda id=tid: self._on_click(id)
            )
            btn.pack(fill="x", pady=1)
            self._buttons[tid] = btn

    def _build_footer(self):
        # Contenedor principal del footer con fondo diferenciado
        footer = ctk.CTkFrame(self, fg_color="#0F1923", corner_radius=0)
        footer.pack(fill="x", side="bottom")

        # Línea divisoria superior
        divider = ctk.CTkFrame(footer, fg_color=COLORS["border"], height=1)
        divider.pack(fill="x")

        # Contenedor interno con padding
        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        # Fila 1: Badge de versión + GitHub
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        # Badge versión
        badge = ctk.CTkFrame(top_row, fg_color="#1E2D42", corner_radius=4)
        badge.pack(side="left")
        ctk.CTkLabel(
            badge, text=f"v{APP_VERSION}",
            font=(UI_FONT_FAMILY, 10, "bold"),
            text_color=COLORS["primary"],
            padx=7, pady=2
        ).pack()

        # Separador puntito
        ctk.CTkLabel(
            top_row, text="·",
            font=(UI_FONT_FAMILY, 12),
            text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=6)

        # GitHub link
        lbl_github = ctk.CTkLabel(
            top_row, text="⬡  GitHub — Zttxw",
            font=(UI_FONT_FAMILY, 11, "bold"),
            text_color=COLORS["primary"],
            cursor="hand2"
        )
        lbl_github.pack(side="left")

        def on_enter(e):
            lbl_github.configure(font=(UI_FONT_FAMILY, 11, "bold", "underline"))
        def on_leave(e):
            lbl_github.configure(font=(UI_FONT_FAMILY, 11, "bold"))

        lbl_github.bind("<Enter>", on_enter)
        lbl_github.bind("<Leave>", on_leave)
        lbl_github.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/Zttxw"))

        # Fila 2: Créditos compactos en una sola línea
        credits_row = ctk.CTkFrame(inner, fg_color="transparent")
        credits_row.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(
            credits_row,
            text="Desarrollado por  ",
            font=(UI_FONT_FAMILY, 10),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            credits_row,
            text="PRACTICANTES OTI",
            font=(UI_FONT_FAMILY, 10, "bold"),
            text_color="#E67E22"
        ).pack(side="left")

    def _on_click(self, tool_id: str):
        self.set_active(tool_id)
        self._on_tool_selected(tool_id)

    def set_active(self, tool_id: str):
        if self._active_id and self._active_id in self._buttons:
            # Restaurar normal
            self._buttons[self._active_id].configure(
                fg_color="transparent", text_color=COLORS["text_secondary"],
                border_width=0
            )

        if tool_id in self._buttons:
            # Estado activo
            self._buttons[tool_id].configure(
                fg_color="#1E2D42", text_color=COLORS["text_primary"],
                border_width=0
            )

        self._active_id = tool_id