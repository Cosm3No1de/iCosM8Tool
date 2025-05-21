# utils.py
"""
Módulo de utilidades para la aplicación iCosM8 V3.8.
Contiene clases de ayuda como Logger para el registro de eventos,
ConfigManager para la gestión de la configuración de la aplicación,
Tooltip para mostrar información emergente en widgets de la GUI,
y una paleta de colores global.
"""
import configparser
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext

# Paleta de colores mejorada
COLORS = {
    "primary": "#3498db",          # Azul brillante
    "secondary": "#2ecc71",        # Verde esmeralda
    "danger": "#e74c3c",           # Rojo ladrillo
    "warning": "#f39c12",          # Naranja brillante
    "dark": "#34495e",             # Gris oscuro azulado
    "light": "#ecf0f1",            # Blanco grisáceo (casi blanco)
    "text": "#2c3e50",             # Gris oscuro para texto (similar a dark)
    "highlight": "#bdc3c7",        # Gris claro para resaltados
    "ramdisk": "#9b59b6",          # Púrpura para elementos de Ramdisk
    "button_text_light": "#ffffff",# Blanco para texto en botones oscuros
    "button_text_dark": "#ffffff", # Blanco para texto en botones claros (o cambiar a un oscuro si el fondo es muy claro)
    "terminal_bg": "#000000",      # Negro para fondo de terminal
    "terminal_fg": "#a9b7c6",      # Gris azulado claro para texto de terminal
    "signal_green": "#27ae60",     # Verde para señal de conexión
    "signal_red": "#e74c3c"        # Rojo para señal de desconexión
}

class Tooltip:
    """
    Crea una pequeña ventana emergente con texto cuando el ratón
    pasa sobre un widget.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None  # Ventana del tooltip
        self.id = None  # ID para after, para cancelar si el ratón se mueve
        self.x = 0
        self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave) # Cerrar si se hace click

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide()

    def schedule(self):
        self.unschedule()
        # El tooltip aparece después de 500 ms (0.5 segundos)
        self.id = self.widget.after(500, self.show)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show(self):
        if self.tw:
            return
        # Obtener las coordenadas del widget
        x = self.widget.winfo_rootx() + 20 # 20px a la derecha del widget
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5 # 5px debajo del widget

        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True) # Quitar bordes de la ventana
        self.tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tw, text=self.text, background=COLORS["highlight"],
                         relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"),
                         wraplength=200) # Envolver texto si es muy largo
        label.pack(padx=1, pady=1)

    def hide(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None

class ConfigManager:
    """
    Gestiona la carga y guardado de la configuración de la aplicación
    desde un archivo 'config.ini'.
    """
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.settings = {} # Almacenará la configuración del SECTION 'SETTINGS'
        self.load_config()

    def load_config(self):
        """
        Carga la configuración desde el archivo INI.
        Si el archivo no existe o la sección 'SETTINGS' no está, crea una configuración por defecto.
        """
        self.config.read(self.config_file)
        if 'SETTINGS' not in self.config:
            self._create_default_config()
        
        # Cargar la sección 'SETTINGS' en el atributo 'settings' para un acceso más fácil
        self.settings = self.config['SETTINGS']
        return self.settings

    def _create_default_config(self):
        """Crea un archivo de configuración por defecto y la sección 'SETTINGS' si no existe."""
        self.config['SETTINGS'] = {
            'theme': 'dark',
            'ramdisk_path': ''
        }
        self.save_config(self.config['SETTINGS']) # Guardar la configuración por defecto

    def save_config(self, settings_dict: dict):
        """Guarda la configuración actual en el archivo INI."""
        # Asegurarse de que la sección 'SETTINGS' existe antes de asignar
        if 'SETTINGS' not in self.config:
            self.config['SETTINGS'] = {}

        for key, value in settings_dict.items():
            self.config['SETTINGS'][key] = str(value) # Guardar todo como string

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        self.settings = self.config['SETTINGS'] # Actualizar la variable settings


class Logger:
    """
    Clase para el registro de mensajes en una ventana de texto de la GUI
    y en la consola. Soporta diferentes niveles de mensaje.
    """
    def __init__(self, text_widget: scrolledtext.ScrolledText = None):
        self._text_widget = text_widget
        self._log_lock = threading.Lock() # Para asegurar que solo un hilo escriba a la vez

    def set_text_widget(self, text_widget: scrolledtext.ScrolledText):
        """Asigna el widget de texto donde se mostrarán los logs."""
        self._text_widget = text_widget

    def log(self, message: str, level: str = "info"):
        """
        Registra un mensaje en la consola y opcionalmente en el widget de texto.

        Args:
            message (str): El mensaje a registrar.
            level (str): El nivel del mensaje (e.g., "info", "warning", "error", "success", "danger").
        """
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_message = f"{timestamp} [{level.upper()}] {message}"

        # Imprimir en consola
        print(formatted_message)

        # Escribir en el widget de texto de la GUI
        if self._text_widget:
            # Usar threading.Lock para evitar race conditions al escribir desde múltiples hilos
            with self._log_lock:
                self._text_widget.configure(state='normal')
                self._text_widget.insert(tk.END, formatted_message + "\n")
                
                # Aplicar color basado en el nivel
                if level == "error" or level == "danger":
                    tag_color = COLORS["danger"]
                elif level == "warning":
                    tag_color = COLORS["warning"]
                elif level == "success":
                    tag_color = COLORS["secondary"]
                elif level == "info":
                    tag_color = COLORS["terminal_fg"]
                else:
                    tag_color = COLORS["terminal_fg"] # Default

                self._text_widget.tag_config(level, foreground=tag_color)
                self._text_widget.tag_add(level, f"end-{len(formatted_message) + 1}c linestart", "end-1c")
                
                self._text_widget.see(tk.END) # Auto-scroll al final
                self._text_widget.configure(state='disabled')