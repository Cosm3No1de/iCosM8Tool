# gui.py
"""
Módulo principal de la Interfaz Gráfica de Usuario (GUI) para la aplicación iCosM8 V3.8.
Define la clase iCosM8ToolGUI, que es responsable de construir y gestionar
todos los elementos visuales y la interacción del usuario, delegando la
lógica de negocio a módulos separados.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk # Se requiere 'Pillow' (pip install Pillow)
import os
import threading

# Importar las clases de los módulos de lógica de negocio y utilidades
from utils import COLORS, Tooltip, ConfigManager, Logger
from device import DeviceManager
from auth import AuthManager
from operations import IOSOperations

class iCosM8ToolGUI:
    """
    Clase principal que define la interfaz de usuario de la herramienta iCosM8.
    Gestiona la creación de widgets, el diseño, los estilos y la interacción con
    los módulos de lógica de negocio.
    """
    def __init__(self, root: tk.Tk):
        """
        Inicializa la interfaz gráfica de usuario.

        Args:
            root (tk.Tk): La ventana raíz de Tkinter.
        """
        self.root = root
        self.root.title("iCosM8 V3.8")
        self.root.geometry("1024x600")
        self.root.resizable(False, False)

        # Inicializar el gestor de configuración para cargar/guardar preferencias
        self.config_manager = ConfigManager()
        # Asegurarse de que la configuración se haya cargado antes de acceder a ella
        self.config_manager.load_config()
        self.theme = self.config_manager.settings.get("theme", "dark") # Tema por defecto o desde config

        # Variables de Tkinter para la interfaz de usuario (StringVar, IntVar, BooleanVar)
        self.ramdisk_path = tk.StringVar(value=self.config_manager.settings.get("ramdisk_path", ""))
        self.device_model = tk.StringVar(value="N/A")
        self.device_ecid = tk.StringVar(value="N/A")
        self.device_imei = tk.StringVar(value="N/A")
        self.device_ios = tk.StringVar(value="0.0") # Se usa para ProductVersion
        self.serial_number = tk.StringVar(value="N/A")
        self.username = tk.StringVar(value="Invitado")
        self.credits = tk.IntVar(value=0)
        self.device_processes = tk.StringVar(value="Ninguno") # No usado directamente en DeviceManager o IOSOperations aún
        self.signal_status = tk.StringVar(value="No Hay Dispositivo")
        self.compatibilidad_resultado = tk.StringVar(value="")
        self.ios_version = tk.StringVar() # Para la selección de iOS en la pestaña Passcode

        # Inicializar el logger ANTES de crear widgets que lo usarán o pasarlo a managers
        self.log_window = None # Referencia a la ventana de logs
        self.resultado_text = None # Referencia al widget ScrolledText dentro de la ventana de logs
        self.logger = Logger() # Instancia del logger (el widget de texto se asignará después)

        # Configurar estilos de Tkinter
        self.setup_styles()

        # Inicializar gestores de lógica de negocio (inyección de dependencias)
        # Se pasa `self.style` al DeviceManager para que pueda usarlo para la etiqueta de señal.
        self.device_manager = DeviceManager(self.logger, self.signal_status, self.style)
        self.auth_manager = AuthManager(self.logger, self.username, self.credits)
        self.operations = IOSOperations(self.logger, self.device_manager, self.auth_manager)

        # Crear todos los widgets de la interfaz. Esto incluye la barra de progreso y su etiqueta.
        # self.progress_bar y self.progress_percentage_label son creados aquí.
        # self.signal_label y self.auth_status_label también son creados aquí.
        self.create_widgets()

        # AHORA que los widgets existen, asignar sus referencias reales a los managers
        # Esto es crucial para que los managers puedan actualizar la GUI.
        self.logger.set_text_widget(self.resultado_text)
        self.device_manager.set_signal_label_widget(self.signal_label) # <--- ¡IMPORTANTE!
        self.auth_manager.set_auth_status_label(self.auth_status_label)
        self.operations.set_progress_widgets(self.progress_bar, self.progress_percentage_label)

        # Aplicar el tema inicial y cargar íconos
        self.apply_theme()
        self.load_icons()
        
        # Iniciar verificación de dependencias y detección de dispositivo en hilos separados
        # para no bloquear la GUI durante el inicio.
        threading.Thread(target=self.device_manager.check_dependencies).start()
        # Iniciar la primera obtención de info de dispositivo después de que los widgets estén listos
        # Esto asegura que la información del dispositivo se intente obtener al inicio
        threading.Thread(target=lambda: self.device_manager.get_device_info(self.actualizar_labels_device_info)).start()

        # Abrir la ventana de logs al inicio
        self.open_log_window_on_start()

    def load_config(self):
        """Carga la configuración de la aplicación usando ConfigManager."""
        # Se modificó para usar self.config_manager.settings directamente
        self.config_manager.load_config()
        self.theme = self.config_manager.settings.get("theme", "dark")
        self.ramdisk_path.set(self.config_manager.settings.get("ramdisk_path", ""))

    def save_config(self):
        """Guarda la configuración actual de la aplicación usando ConfigManager."""
        current_config = {
            "theme": self.theme,
            "ramdisk_path": self.ramdisk_path.get()
        }
        self.config_manager.save_config(current_config)

    def apply_theme(self):
        """Aplica el tema (oscuro/claro) a todos los widgets de la GUI."""
        bg_color = COLORS["dark"] if self.theme == "dark" else COLORS["light"]
        fg_color = COLORS["light"] if self.theme == "dark" else COLORS["text"]
        header_bg = COLORS["dark"] if self.theme == "dark" else COLORS["light"]
        header_fg = COLORS["light"] if self.theme == "dark" else COLORS["text"]
        labelframe_bg = COLORS["dark"] if self.theme == "dark" else COLORS["light"]
        labelframe_fg = COLORS["light"] if self.theme == "dark" else COLORS["text"]
        
        # Configurar estilos generales
        self.root.configure(bg=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("TEntry", fieldbackground=bg_color, foreground=fg_color, insertcolor=fg_color)
        self.style.configure("TLabelframe", background=labelframe_bg, foreground=labelframe_fg)
        self.style.configure("TLabelframe.Label", background=labelframe_bg, foreground=labelframe_fg)
        self.style.configure("TButton", padding=(8,8), font=("Segoe UI", 9, "bold"))
        self.style.configure("Primary.TButton", background=COLORS["primary"], foreground=COLORS["button_text_light"])
        self.style.configure("Secondary.TButton", background=COLORS["secondary"], foreground=COLORS["button_text_light"])
        self.style.configure("Danger.TButton", background=COLORS["danger"], foreground=COLORS["button_text_light"])
        self.style.configure("Warning.TButton", background=COLORS["warning"], foreground=COLORS["text"] if self.theme == "light" else COLORS["button_text_dark"])
        self.style.configure("Signal.TLabel",  font=("Segoe UI", 10, "bold")) # El color se setea dinámicamente
        self.style.configure("UserPanel.TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("RegisterPanel.TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("RegisterPanel.TEntry", fieldbackground=bg_color, foreground=fg_color, insertcolor=fg_color)
        self.style.configure("RegisterPanel.TButton", background=self.style.lookup("TButton", 'background'), foreground=COLORS["text"])
        self.style.configure("Header.TLabel", background=header_bg, foreground=header_fg, font=("Segoe UI", 14, "bold"))
        self.style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        self.style.configure("TRadiobutton", background=bg_color, foreground=fg_color)
        # Asegurarse de que el estilo ScrolledText se aplique al widget (no al 'Frame' interno)
        # Nota: ScrolledText no es un ttk.Widget, por lo que su configuración es directa.
        if self.log_window and self.resultado_text:
            self.resultado_text.configure(bg=COLORS["terminal_bg"], fg=COLORS["terminal_fg"], insertbackground=COLORS["terminal_fg"])
            # Actualizar tags de color si ya hay texto
            self.logger.set_text_widget(self.resultado_text) # Re-aplicar tags si el widget ya tiene texto

        # Actualizar widgets existentes que no se re-crean (como el header y botón de tema)
        if hasattr(self, 'header_label'):
            self.header_label.config(style="Header.TLabel")
        if hasattr(self, 'theme_btn'):
            self.theme_btn.config(text="☀️" if self.theme == "dark" else "🌙")
        if hasattr(self, 'user_info_labels'):
            for label_key, label_widget in self.user_info_labels.items():
                label_widget.config(style="UserPanel.TLabel")
        # signal_label y auth_status_label son actualizados por sus respectivos managers

    def toggle_theme(self):
        """Alterna entre el tema claro y oscuro de la aplicación y guarda la preferencia."""
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme()
        self.save_config()

    def setup_styles(self):
        """Configura los estilos iniciales para los widgets de Tkinter."""
        self.style = ttk.Style()
        self.style.theme_use("clam") # Un tema moderno base
        
        # Definiciones de estilos para cada tipo de widget y botones
        # Estos se recalibran en apply_theme, pero se definen aquí inicialmente
        self.style.configure("TButton", padding=(8,8), font=("Segoe UI", 9, "bold"))
        self.style.configure("Primary.TButton", background=COLORS["primary"], foreground=COLORS["button_text_light"])
        self.style.configure("Secondary.TButton", background=COLORS["secondary"], foreground=COLORS["button_text_light"])
        self.style.configure("Danger.TButton", background=COLORS["danger"], foreground=COLORS["button_text_light"])
        self.style.configure("Warning.TButton", background=COLORS["warning"], foreground=COLORS["text"]) # Texto oscuro en fondo claro
        self.style.configure("TLabel", background=COLORS["light"], foreground=COLORS["text"])
        self.style.configure("TEntry", fieldbackground=COLORS["light"], foreground=COLORS["text"], insertcolor=COLORS["text"])
        self.style.configure("TEntry.Valid", foreground=COLORS["secondary"])
        self.style.configure("TEntry.Invalid", foreground=COLORS["danger"])
        self.style.configure("TLabelframe", background=COLORS["light"], foreground=COLORS["text"])
        self.style.configure("TLabelframe.Label", background=COLORS["light"], foreground=COLORS["text"])
        self.style.configure("UserPanel.TLabel", background=COLORS["light"], foreground=COLORS["text"])
        self.style.configure("RegisterPanel.TLabel", background=COLORS["light"], foreground=COLORS["text"])
        self.style.configure("RegisterPanel.TEntry", fieldbackground=COLORS["light"], foreground=COLORS["text"], insertcolor=COLORS["text"])
        self.style.configure("RegisterPanel.TButton", background=self.style.lookup("TButton", 'background'), foreground=COLORS["text"])
        self.style.configure("Signal.TLabel", font=("Segoe UI", 10, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("TCheckbutton", background=COLORS["light"], foreground=COLORS["text"])
        self.style.configure("TRadiobutton", background=COLORS["light"], foreground=COLORS["text"])
        
        # Mapeo de estados para botones (efecto hover, etc.)
        self.style.map("Primary.TButton", background=[("active", COLORS["highlight"])])
        self.style.map("Secondary.TButton", background=[("active", COLORS["highlight"])])
        self.style.map("Danger.TButton", background=[("active", COLORS["highlight"])])
        self.style.map("Warning.TButton", background=[("active", COLORS["highlight"])])

    def create_widgets(self):
        """Crea y organiza todos los widgets principales de la interfaz de usuario."""
        # Header con título y botón de tema
        header = ttk.Frame(self.root)
        header.pack(fill="x", pady=10)
        self.header_label = ttk.Label(header, text="iCosM8 V3.8", style="Header.TLabel")
        self.header_label.pack(side="left", padx=15)
        self.theme_btn = ttk.Button(header, text="☀️" if self.theme == "dark" else "🌙", command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=15)
        Tooltip(self.theme_btn, "Alternar tema oscuro/claro")

        # Contenedor principal de la aplicación
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Panel de información del dispositivo (lado izquierdo)
        device_info_frame = ttk.LabelFrame(main_frame, text="Información del Dispositivo", width=300)
        device_info_frame.pack(side="left", fill="y", padx=10, pady=10)

        labels_info_dispositivo = [
            ("Modelo:", self.device_model),
            ("Serial:", self.serial_number),
            ("ECID:", self.device_ecid),
            ("IMEI:", self.device_imei),
            ("iOS:", self.device_ios)
        ]

        self.user_info_labels = {} # Para actualizar dinámicamente el estilo
        for i, (label_text, variable) in enumerate(labels_info_dispositivo):
            label_widget_label = ttk.Label(device_info_frame, text=label_text, style="UserPanel.TLabel")
            label_widget_label.grid(row=i, column=0, padx=10, pady=2, sticky="w")
            label_widget_value = ttk.Label(device_info_frame, textvariable=variable, style="UserPanel.TLabel")
            label_widget_value.grid(row=i, column=1, padx=10, pady=2, sticky="w")
            self.user_info_labels[label_text.replace(":", "")] = label_widget_value

        # Estado de la señal de conexión (widget creado aquí)
        ttk.Label(device_info_frame, text="Conexión:", style="UserPanel.TLabel").grid(row=len(labels_info_dispositivo), column=0, padx=10, pady=2, sticky="w")
        self.signal_label = ttk.Label(device_info_frame, textvariable=self.signal_status, style="Signal.TLabel")
        self.signal_label.grid(row=len(labels_info_dispositivo), column=1, padx=10, pady=2, sticky="w")
        # El widget signal_label se asigna al device_manager en __init__ después de su creación

        # Botón para refrescar la información del dispositivo
        refresh_button = ttk.Button(
            device_info_frame, 
            text="Refrescar", 
            command=lambda: threading.Thread(
                target=lambda: self.device_manager.get_device_info(self.actualizar_labels_device_info)
            ).start(), 
            style="Secondary.TButton"
        )
        refresh_button.grid(row=len(labels_info_dispositivo) + 1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Panel de Inicio de Sesión
        login_panel = ttk.LabelFrame(main_frame, text="Inicio de Sesión", width=300)
        login_panel.pack(side="left", fill="y", padx=10, pady=10)

        ttk.Label(login_panel, text="Usuario:", style="UserPanel.TLabel").pack(padx=10, pady=2, anchor="w")
        self.login_username_entry_panel = ttk.Entry(login_panel, style="TEntry")
        self.login_username_entry_panel.pack(padx=10, pady=2, fill="x")

        ttk.Label(login_panel, text="Contraseña:", style="UserPanel.TLabel").pack(padx=10, pady=2, anchor="w")
        self.login_password_entry_panel = ttk.Entry(login_panel, show="*", style="TEntry")
        self.login_password_entry_panel.pack(padx=10, pady=2, fill="x")

        login_button_panel = ttk.Button(login_panel, text="Iniciar Sesión", command=self.iniciar_sesion, style="Primary.TButton")
        login_button_panel.pack(pady=5, padx=10, fill="x")

        # Botón para abrir la ventana de registro
        register_button_login = ttk.Button(login_panel, text="Registrarse", command=self.open_register_window_from_login, style="Secondary.TButton")
        register_button_login.pack(pady=5, padx=10, fill="x")

        ttk.Label(login_panel, text="Créditos Cargados:", style="UserPanel.TLabel").pack(padx=10, pady=2, anchor="w")
        self.credits_label_panel = ttk.Label(login_panel, textvariable=self.credits, style="UserPanel.TLabel")
        self.credits_label_panel.pack(padx=10, pady=2, anchor="w")

        ttk.Label(login_panel, text="Procesos:", style="UserPanel.TLabel").pack(padx=10, pady=2, anchor="w")
        self.processes_label_panel = ttk.Label(login_panel, textvariable=self.device_processes, style="UserPanel.TLabel")
        self.processes_label_panel.pack(padx=10, pady=2, anchor="w")

        # Etiqueta de estado de autenticación (widget creado aquí)
        self.auth_status_label = ttk.Label(login_panel, text="", style="UserPanel.TLabel")
        self.auth_status_label.pack(side="bottom", padx=10, pady=5)

        # Área de acciones (lado derecho con pestañas)
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Notebook (pestañas) para organizar las diferentes operaciones
        self.notebook = ttk.Notebook(actions_frame)
        self.notebook.pack(fill="both", expand=True)

        # Barra de progreso y etiqueta de porcentaje (se crean aquí)
        progress_frame = ttk.Frame(actions_frame) # Usar actions_frame como padre
        progress_frame.pack(fill="x", pady=10)

        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=200)
        self.progress_bar.pack(side="left", fill="x", expand=True)

        self.progress_percentage_label = ttk.Label(progress_frame, text="0%", style="UserPanel.TLabel")
        self.progress_percentage_label.pack(side="right", padx=5)


        # Creación de cada pestaña
        self.hola_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.hola_tab, text="Activación en Hola")
        self.create_hola_tab(self.hola_tab)

        self.passcode_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.passcode_tab, text="Activación en Passcode")
        self.create_passcode_tab(self.passcode_tab)

        self.fmi_off_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.fmi_off_tab, text="FMI OFF")
        self.create_fmi_off_tab(self.fmi_off_tab)

        self.create_toolbox_tab(self.notebook) # La pestaña Toolbox

    def create_hola_tab(self, parent_frame: ttk.Frame):
        """Crea los widgets y la disposición de la pestaña 'Activación en Hola'."""
        hola_frame = ttk.Frame(parent_frame)
        hola_frame.pack(pady=10, padx=20, fill="x")

        compatibilidad_button = ttk.Button(
            hola_frame, 
            text="Probar Compatibilidad", 
            command=lambda: self.operations.probar_compatibilidad_hola(self.compatibilidad_resultado), 
            style="Primary.TButton"
        )
        compatibilidad_button.pack(side="top", fill="x", pady=5)
        Tooltip(compatibilidad_button, "Verifica si el dispositivo es compatible con la activación en Hola.")

        resultado_label = ttk.Label(hola_frame, textvariable=self.compatibilidad_resultado, style="UserPanel.TLabel")
        resultado_label.pack(side="top", fill="x", pady=5)

        options_frame = ttk.Frame(hola_frame)
        options_frame.pack(pady=10, padx=20, fill="x")

        # Checkbuttons para opciones
        # Estas variables BooleanVar deberían ser pasadas a operations si son necesarias
        self.block_updates_var = tk.BooleanVar()
        self.block_updates_check = ttk.Checkbutton(options_frame, text="Bloquear Actualizaciones", variable=self.block_updates_var)
        self.block_updates_check.pack(side="left", padx=10)

        self.block_restore_var = tk.BooleanVar()
        self.block_restore_check = ttk.Checkbutton(options_frame, text="Bloquear Restaurar", variable=self.block_restore_var)
        self.block_restore_check.pack(side="left", padx=10)

        self.omit_setup_var = tk.BooleanVar()
        self.omit_setup_check = ttk.Checkbutton(options_frame, text="Omitir Configuración", variable=self.omit_setup_var)
        self.omit_setup_check.pack(side="left", padx=10)

        # Aquí un botón de "Activar Hola" si aplica
        activate_hola_button = ttk.Button(
            hola_frame,
            text="Activar Dispositivo en Hola",
            # Aquí, la función de operations debe recibir las variables de las opciones
            command=lambda: self.operations.activar_dispositivo_hola(
                block_updates=self.block_updates_var.get(),
                block_restore=self.block_restore_var.get(),
                omit_setup=self.omit_setup_var.get()
            ),
            style="Primary.TButton"
        )
        activate_hola_button.pack(side="top", fill="x", pady=10)
        Tooltip(activate_hola_button, "Activa el dispositivo en pantalla de Hola.")


    def create_passcode_tab(self, parent_frame: ttk.Frame):
        """Crea los widgets y la disposición de la pestaña 'Activación en Passcode'."""
        passcode_frame = ttk.Frame(parent_frame)
        passcode_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Grupo para Modo Boot Files
        boot_files_group = ttk.LabelFrame(passcode_frame, text="Método: Modo Boot Files", style="TLabelframe")
        boot_files_group.pack(fill="x", pady=10)

        ttk.Label(boot_files_group, text="Selecciona la versión de iOS:", style="TLabel").pack(padx=5, pady=2, anchor="w")

        # Radio buttons para selección de iOS
        ios14_radio = ttk.Radiobutton(boot_files_group, text="iOS 14", variable=self.ios_version, value="ios14")
        ios14_radio.pack(padx=20, pady=2, anchor="w")
        ios15_radio = ttk.Radiobutton(boot_files_group, text="iOS 15", variable=self.ios_version, value="ios15")
        ios15_radio.pack(padx=20, pady=2, anchor="w")
        ios16_radio = ttk.Radiobutton(boot_files_group, text="iOS 16", variable=self.ios_version, value="ios16")
        ios16_radio.pack(padx=20, pady=2, anchor="w")

        boot_files_button = ttk.Button(
            boot_files_group, 
            text="Paso 1 - Iniciar en Modo Boot Files", 
            command=lambda: self.operations.iniciar_modo_boot_files(self.ios_version.get()), 
            style="Primary.TButton"
        )
        boot_files_button.pack(pady=5, padx=10, fill="x")
        Tooltip(boot_files_button, "Inicia el proceso en modo Boot Files.")

        # Grupo para Respaldo de Tokens
        respaldo_tokens_group = ttk.LabelFrame(passcode_frame, text="Respaldo de Tokens", style="TLabelframe")
        respaldo_tokens_group.pack(fill="x", pady=10)

        respaldo_button = ttk.Button(
            respaldo_tokens_group, 
            text="Paso 2 - Probar Compatibilidad\ny Hacer Respaldo de Tokens", 
            command=self.operations.respaldar_tokens, 
            style="Secondary.TButton"
        )
        respaldo_button.pack(pady=5, padx=10, fill="x")
        Tooltip(respaldo_button, "Prueba la compatibilidad y realiza el respaldo de tokens.")

        # Grupo para Activación
        activar_group = ttk.LabelFrame(passcode_frame, text="Activar", style="TLabelframe")
        activar_group.pack(fill="both", expand=True, pady=10)

        activar_label = ttk.Label(activar_group, text="Paso 3 - Activar", style="UserPanel.TLabel", font=("Segoe UI", 12, "bold"))
        activar_label.pack(pady=20)

        # Checkbuttons para opciones de activación
        self.block_updates_var_passcode = tk.BooleanVar()
        block_updates_check_passcode = ttk.Checkbutton(activar_group, text="Bloquear Actualizaciones", variable=self.block_updates_var_passcode)
        block_updates_check_passcode.pack(padx=10, pady=2, anchor="w")

        self.block_restore_var_passcode = tk.BooleanVar()
        block_restore_check_passcode = ttk.Checkbutton(activar_group, text="Bloquear Restaurar", variable=self.block_restore_var_passcode)
        block_restore_check_passcode.pack(padx=10, pady=2, anchor="w")

        self.omit_setup_var_passcode = tk.BooleanVar()
        omit_setup_check_passcode = ttk.Checkbutton(activar_group, text="Omitir Configuración", variable=self.omit_setup_var_passcode)
        omit_setup_check_passcode.pack(padx=10, pady=2, anchor="w")

        activar_button = ttk.Button(
            activar_group, 
            text="Activar", 
            command=lambda: self.operations.activar_dispositivo_passcode(
                block_updates=self.block_updates_var_passcode.get(),
                block_restore=self.block_restore_var_passcode.get(),
                omit_setup=self.omit_setup_var_passcode.get()
            ), 
            style="Primary.TButton"
        )
        activar_button.pack(pady=15, padx=10, fill="x", side="bottom")
        Tooltip(activar_button, "Activa el dispositivo.")

    def create_fmi_off_tab(self, parent_frame: ttk.Frame):
        """Crea los widgets y la disposición de la pestaña 'FMI OFF'."""
        fmi_off_frame = ttk.Frame(parent_frame)
        fmi_off_frame.pack(pady=10, padx=20, fill="x")

        fmi_off_button = ttk.Button(
            fmi_off_frame, 
            text="Intentar FMI OFF", 
            command=self.operations.intentar_fmi_off, 
            style="Danger.TButton"
        )
        fmi_off_button.pack(side="top", fill="x", pady=5)
        Tooltip(fmi_off_button, "Intenta desactivar la función Buscar Mi iPhone (FMI).")

        warning_label = ttk.Label(
            fmi_off_frame, 
            text="Advertencia: La desactivación de FMI puede no ser posible en todos los dispositivos y versiones de iOS.", 
            style="Warning.TLabel"
        )
        warning_label.pack(pady=5)

    def create_toolbox_tab(self, parent_notebook: ttk.Notebook):
        """Crea los widgets y la disposición de la pestaña 'Toolbox'."""
        self.toolbox_tab = ttk.Frame(parent_notebook)
        parent_notebook.add(self.toolbox_tab, text="Toolbox")

        main_frame = ttk.Frame(self.toolbox_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        dfu_title = ttk.Label(main_frame, text="Asistente para entrar a Modo DFU",
                                font=("Segoe UI", 12, "bold"))
        dfu_title.pack(pady=(0, 15))

        # Grupo para Jailbreak y Exploit
        jailbreak_frame = ttk.LabelFrame(main_frame, text="Jailbreak y Exploit", style="TLabelframe")
        jailbreak_frame.pack(fill="x", pady=5)

        jailbreak_buttons_data = [
            ("Jailbreak Automático", self.operations.jailbreak_automatico),
            ("Checkra1n", self.operations.ejecutar_checkra1n),
            ("Palera1n Rootful", lambda: self.operations.ejecutar_palera1n(rootful=True)),
            ("Palera1n Rootless", lambda: self.operations.ejecutar_palera1n(rootful=False))
        ]

        for text, command in jailbreak_buttons_data:
            btn = ttk.Button(jailbreak_frame, text=text, command=command, style="Secondary.TButton")
            btn.pack(fill="x", pady=2)

        # Grupo para Utilidades
        utilidades_frame = ttk.LabelFrame(main_frame, text="Utilidades", style="TLabelframe")
        utilidades_frame.pack(fill="x", pady=5)

        restore_btn = ttk.Button(utilidades_frame, text="Restaurar Dispositivo",
                                  command=self.operations.restore_device, style="Warning.TButton")
        restore_btn.pack(fill="x", pady=2)

        # Grupo para Salir de Modos
        exit_mode_frame = ttk.LabelFrame(main_frame, text="Salir de Modo", style="TLabelframe")
        exit_mode_frame.pack(fill="x", pady=5)

        exit_modes_data = [
            ("Salir de Modo Boot Files", self.operations.salir_modo_boot_files),
            ("Salir de Modo Recovery", self.operations.salir_modo_recovery),
            ("Salir de Modo DFU", self.operations.salir_modo_dfu),
            ("Salir de Modo Purple", self.operations.salir_modo_purple)
        ]

        for text, command in exit_modes_data:
            btn = ttk.Button(exit_mode_frame, text=text, command=command, style="Secondary.TButton")
            btn.pack(fill="x", pady=2)

    def actualizar_labels_device_info(self, device_info: dict):
        """
        Callback para actualizar los labels de información del dispositivo en la GUI.
        Es llamado por DeviceManager cuando se obtiene nueva información.

        Args:
            device_info (dict): Un diccionario con la información del dispositivo.
                                 Puede ser vacío si no se detecta ningún dispositivo.
        """
        # Asegurarse de que esta actualización se realice en el hilo principal
        self.root.after(0, lambda: self._update_device_info_gui(device_info))

    def _update_device_info_gui(self, device_info: dict):
        """Actualiza las variables de Tkinter con la información del dispositivo."""
        if not device_info:
            self.device_model.set("N/A")
            self.device_ios.set("0.0")
            self.serial_number.set("N/A")
            self.device_ecid.set("N/A")
            self.device_imei.set("N/A")
            self.compatibilidad_resultado.set("") # Limpiar resultado de compatibilidad
            return

        self.device_model.set(device_info.get("ProductType", "N/A"))
        self.device_ios.set(device_info.get("ProductVersion", "N/A"))
        self.serial_number.set(device_info.get("SerialNumber", "N/A"))
        self.device_ecid.set(device_info.get("UniqueChipID", "N/A"))
        self.device_imei.set(device_info.get("InternationalMobileEquipmentIdentity", "N/A"))

    def create_log_window(self):
        """Crea y muestra la ventana de logs de la aplicación."""
        if self.log_window is None or not self.log_window.winfo_exists():
            self.log_window = tk.Toplevel(self.root)
            self.log_window.title("iCosM8 Logs")
            self.log_window.geometry("600x400")
            self.log_window.protocol("WM_DELETE_WINDOW", self.hide_log_window) # Ocultar en lugar de destruir

            log_frame = ttk.Frame(self.log_window)
            log_frame.pack(fill="both", expand=True, padx=10, pady=10)

            self.resultado_text = ScrolledText(
                log_frame,
                wrap='word',
                height=15,
                bg=COLORS["terminal_bg"],
                fg=COLORS["terminal_fg"],
                insertbackground=COLORS["terminal_fg"],
                font=("Consolas", 10)
            )
            self.resultado_text.pack(fill="both", expand=True)
            self.resultado_text.configure(state='disabled') # Deshabilitar edición
            self.logger.set_text_widget(self.resultado_text) # Asignar el widget de texto al logger
            # Re-aplicar el tema a la ventana de logs y al texto si el tema actual es oscuro
            self.apply_theme() # Esto reconfigurará el ScrolledText con los colores correctos

            clear_log_btn = ttk.Button(log_frame, text="Limpiar Logs", command=self.clear_logs, style="Warning.TButton")
            clear_log_btn.pack(pady=5)
        else:
            self.log_window.lift() # Si ya existe, traerla al frente

    def open_log_window_on_start(self):
        """Asegura que la ventana de logs se muestre al inicio si ya existe o la crea."""
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.deiconify() # Si está oculta, mostrarla
        else:
            self.create_log_window() # Si no existe, crearla

    def hide_log_window(self):
        """Oculta la ventana de logs en lugar de cerrarla completamente."""
        if self.log_window:
            self.log_window.withdraw()

    def clear_logs(self):
        """Limpia todo el texto de la ventana de logs."""
        if self.resultado_text:
            self.resultado_text.configure(state='normal')
            self.resultado_text.delete(1.0, tk.END)
            self.resultado_text.configure(state='disabled')
            self.logger.log("Logs limpiados.", "info")

    def load_icons(self):
        """Carga y gestiona los íconos de la aplicación."""
        # Puedes cargar íconos aquí si los tienes
        # self.icon_name = ImageTk.PhotoImage(Image.open("path/to/icon.png").resize((16, 16)))
        pass # No hay íconos definidos en este ejemplo

    def iniciar_sesion(self):
        """Maneja el inicio de sesión del usuario."""
        username = self.login_username_entry_panel.get()
        password = self.login_password_entry_panel.get()
        threading.Thread(target=self.auth_manager.login, args=(username, password)).start()

    def open_register_window_from_login(self):
        """Abre la ventana de registro desde el panel de inicio de sesión."""
        self.open_register_window()

    def open_register_window(self):
        """Crea y muestra la ventana de registro de nuevos usuarios."""
        register_window = tk.Toplevel(self.root)
        register_window.title("Registrar Nuevo Usuario")
        register_window.geometry("400x300")
        register_window.grab_set() # Hacerla modal

        register_frame = ttk.Frame(register_window)
        register_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ttk.Label(register_frame, text="Nombre de Usuario:", style="RegisterPanel.TLabel").pack(pady=5, anchor="w")
        new_username_entry = ttk.Entry(register_frame, style="RegisterPanel.TEntry")
        new_username_entry.pack(fill="x", pady=2)

        ttk.Label(register_frame, text="Contraseña:", style="RegisterPanel.TLabel").pack(pady=5, anchor="w")
        new_password_entry = ttk.Entry(register_frame, show="*", style="RegisterPanel.TEntry")
        new_password_entry.pack(fill="x", pady=2)

        ttk.Label(register_frame, text="Confirmar Contraseña:", style="RegisterPanel.TLabel").pack(pady=5, anchor="w")
        confirm_password_entry = ttk.Entry(register_frame, show="*", style="RegisterPanel.TEntry")
        confirm_password_entry.pack(fill="x", pady=2)

        def register_user_action():
            username = new_username_entry.get()
            password = new_password_entry.get()
            confirm_password = confirm_password_entry.get()
            # Delegar la lógica de registro al AuthManager
            threading.Thread(target=lambda: self.auth_manager.register(username, password, confirm_password, register_window)).start()

        register_button = ttk.Button(register_frame, text="Registrar", command=register_user_action, style="Primary.TButton")
        register_button.pack(pady=10, fill="x")

        # Asegurarse de que el tema se aplica a la nueva ventana
        register_window.bind("<Map>", lambda event: self.apply_theme_to_toplevel(register_window))

    def apply_theme_to_toplevel(self, toplevel_window: tk.Toplevel):
        """Aplica el tema actual a una ventana Toplevel recién creada."""
        bg_color = COLORS["dark"] if self.theme == "dark" else COLORS["light"]
        fg_color = COLORS["light"] if self.theme == "dark" else COLORS["text"]
        
        toplevel_window.configure(bg=bg_color)
        for widget in toplevel_window.winfo_children():
            if isinstance(widget, ttk.Frame) or isinstance(widget, ttk.LabelFrame):
                widget.configure(style="TFrame" if isinstance(widget, ttk.Frame) else "TLabelframe")
                for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, ttk.Label):
                        sub_widget.configure(style="RegisterPanel.TLabel")
                    elif isinstance(sub_widget, ttk.Entry):
                        sub_widget.configure(style="RegisterPanel.TEntry")
                    elif isinstance(sub_widget, ttk.Button):
                        sub_widget.configure(style="RegisterPanel.TButton")
            elif isinstance(widget, ttk.Label):
                widget.configure(style="RegisterPanel.TLabel")
            elif isinstance(widget, ttk.Entry):
                widget.configure(style="RegisterPanel.TEntry")
            elif isinstance(widget, ttk.Button):
                widget.configure(style="RegisterPanel.TButton")

# El bloque if __name__ == "__main__": permanece en main.py para iniciar la aplicación.
