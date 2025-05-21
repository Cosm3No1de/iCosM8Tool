# device.py
"""
Módulo para la gestión de dispositivos iOS en la aplicación iCosM8 V3.8.
Define la clase DeviceManager, que maneja la detección, información y
operaciones básicas relacionadas con dispositivos iOS usando libimobiledevice.
"""
import platform
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

# Importar la clase Logger y COLORS desde el módulo de utilidades
from utils import Logger, COLORS

class DeviceManager:
    """
    Gestiona la conexión y la información de dispositivos iOS.
    Utiliza herramientas de `libimobiledevice` como `ideviceinfo`, `idevice_id`, etc.
    """
    def __init__(self, logger: Logger, signal_status_var: tk.StringVar, style_manager: ttk.Style):
        """
        Inicializa el DeviceManager.

        Args:
            logger (Logger): Instancia del logger para registrar eventos.
            signal_status_var (tk.StringVar): Variable de Tkinter para el estado de la señal (ej. "Conectado").
            style_manager (ttk.Style): Instancia del gestor de estilos de Tkinter.
        """
        self.logger = logger
        self.signal_status_var = signal_status_var
        self.style = style_manager
        self.device_info = {} # Almacena la información del dispositivo conectado
        self.signal_label_widget = None # Se inicializa a None, se setea desde GUI

        # Iniciar la monitorización de conexión en un hilo separado
        self.monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.monitor_thread.start()

    def set_signal_label_widget(self, widget: ttk.Label):
        """
        Establece el widget Label de Tkinter para mostrar el estado de la señal.
        Este método es llamado desde la GUI una vez que el widget es creado.
        """
        self.signal_label_widget = widget
        self._update_signal_display() # Actualizar el display tan pronto como el widget esté disponible

    def _execute_command(self, command: list, error_message: str, timeout: int = 10):
        """
        Ejecuta un comando del sistema y maneja posibles errores.

        Args:
            command (list): El comando y sus argumentos como una lista.
            error_message (str): Mensaje de error a registrar si el comando falla.
            timeout (int): Tiempo máximo de espera para el comando.

        Returns:
            str: La salida estándar del comando si tiene éxito, o None si falla.
        """
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.log(f"ERROR: {error_message} - {e.cmd} falló con código {e.returncode}.", "error")
            self.logger.log(f"Stderr: {e.stderr.strip()}", "error")
            return None
        except FileNotFoundError:
            self.logger.log(f"ERROR: Comando '{command[0]}' no encontrado. Asegúrate de que esté en tu PATH.", "error")
            return None
        except subprocess.TimeoutExpired:
            self.logger.log(f"ERROR: El comando '{command[0]}' excedió el tiempo de espera de {timeout} segundos.", "error")
            return None
        except Exception as e:
            self.logger.log(f"ERROR inesperado al ejecutar comando '{command[0]}': {e}", "error")
            return None

    def check_dependencies(self):
        """
        Verifica la instalación de libimobiledevice y sus herramientas necesarias.
        """
        self.logger.log("Verificando dependencias de libimobiledevice...", "info")
        required_tools = ["ideviceinfo", "ideviceprovision", "ideviceenterrecovery", "idevicediagnostics", "idevicepair", "idevicesyslog", "idevicebackup2", "idevice_id"]
        all_found = True
        for tool in required_tools:
            # 'where' para Windows, 'which' para Linux/macOS
            command = ["where", tool] if platform.system() == "Windows" else ["which", tool]
            
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=5)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                self.logger.log(f"ADVERTENCIA: '{tool}' no encontrado. Por favor, instala libimobiledevice.", "warning")
                all_found = False
        
        if all_found:
            self.logger.log("Todas las dependencias de libimobiledevice encontradas.", "success")
        else:
            self.logger.log("FALTA: Algunas dependencias de libimobiledevice no se encontraron. La herramienta podría no funcionar correctamente.", "danger")

    def _monitor_connection(self):
        """
        Monitorea continuamente la conexión del dispositivo iOS en un hilo separado.
        Actualiza `signal_status_var` y la apariencia de `signal_label_widget`.
        """
        while True:
            is_connected = self._check_device_connection()
            if is_connected:
                # Solo actualizar si el estado cambia para evitar spam de logs
                if self.signal_status_var.get() != "Conectado":
                    self.signal_status_var.set("Conectado")
                    self._update_signal_display("connected")
                    self.logger.log("Dispositivo iOS conectado.", "info")
            else:
                if self.signal_status_var.get() == "Conectado" or self.signal_status_var.get() == "Buscando...":
                    self.signal_status_var.set("Desconectado")
                    self._update_signal_display("disconnected")
                    self.logger.log("Dispositivo iOS desconectado.", "warning")
                self.device_info = {} # Limpiar información si el dispositivo se desconecta
            time.sleep(3) # Chequear cada 3 segundos

    def _check_device_connection(self) -> bool:
        """
        Verifica si un dispositivo iOS está actualmente conectado utilizando idevice_id.

        Returns:
            bool: True si hay un dispositivo conectado, False en caso contrario.
        """
        try:
            # idevice_id -l lista los UDID de los dispositivos conectados
            result = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True, check=False, timeout=5)
            return bool(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_device_info(self, callback=None):
        """
        Obtiene información detallada del dispositivo iOS conectado.
        Esta operación se ejecuta en un hilo separado para no bloquear la GUI.

        Args:
            callback (callable, optional): Una función de callback para actualizar la GUI
                                          con la información del dispositivo. Se le pasa un diccionario.
        """
        def _get_info_thread():
            self.logger.log("Buscando dispositivo iOS...", "info")
            self.signal_status_var.set("Buscando...")
            self._update_signal_display("searching")

            if not self._check_device_connection():
                self.logger.log("No se detectó ningún dispositivo iOS.", "danger")
                self.signal_status_var.set("Desconectado")
                self._update_signal_display("disconnected")
                self.device_info = {}
                if callback:
                    callback({}) # Enviar diccionario vacío si no hay dispositivo
                return

            command = ["ideviceinfo"]
            info_output = self._execute_command(command, "Error al obtener información del dispositivo")

            if info_output:
                self.device_info = self._parse_device_info(info_output)
                self.logger.log("Información del dispositivo obtenida con éxito.", "success")
                self.signal_status_var.set("Conectado")
                self._update_signal_display("connected")
            else:
                self.logger.log("No se pudo obtener la información del dispositivo.", "error")
                self.device_info = {}
                self.signal_status_var.set("Error de Conexión")
                self._update_signal_display("disconnected") # Mantener como desconectado o error visualmente
            
            if callback:
                # Ejecutar el callback en el hilo principal de Tkinter
                if self.signal_label_widget: # Usar un widget existente para .after
                    self.signal_label_widget.after(0, lambda: callback(self.device_info))
                else:
                    callback(self.device_info) # Fallback si el widget no está listo

        threading.Thread(target=_get_info_thread).start()

    def _parse_device_info(self, info_output: str) -> dict:
        """
        Analiza la salida de `ideviceinfo` y la convierte en un diccionario.
        """
        info = {}
        for line in info_output.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()
        return info

    def _update_signal_display(self, status: str = None):
        """
        Actualiza el color y el texto de la etiqueta de la señal.
        Se asegura de que el widget exista antes de intentar configurarlo.
        """
        if not self.signal_label_widget:
            return # No hacer nada si el widget aún no ha sido asignado

        # Ejecutar la actualización en el hilo principal de Tkinter
        self.signal_label_widget.after(0, lambda: self._apply_signal_style(status))

    def _apply_signal_style(self, status: str):
        """Aplica el estilo visual al label de la señal."""
        current_status = status if status else self.signal_status_var.get().lower()
        
        if current_status == "conectado":
            self.signal_label_widget.config(foreground=COLORS["signal_green"])
        elif current_status == "desconectado":
            self.signal_label_widget.config(foreground=COLORS["signal_red"])
        elif current_status == "buscando...":
            self.signal_label_widget.config(foreground=COLORS["warning"])
        elif current_status == "error de conexión":
            self.signal_label_widget.config(foreground=COLORS["danger"])
        else:
            self.signal_label_widget.config(foreground=COLORS["text"]) # Color por defecto
        
        self.signal_label_widget.config(text=self.signal_status_var.get())

    # --- Métodos para operaciones de cambio de modo de dispositivo ---

    def enter_recovery_mode(self):
        """
        Intenta poner el dispositivo en modo Recovery.
        """
        self.logger.log("Intentando entrar en modo Recovery...", "info")
        command = ["ideviceenterrecovery"]
        result = self._execute_command(command, "Error al entrar en modo Recovery")
        if result:
            self.logger.log("Dispositivo en modo Recovery.", "success")
            return True
        return False

    def exit_recovery_mode(self):
        """
        Intenta sacar el dispositivo del modo Recovery.
        """
        self.logger.log("Intentando salir del modo Recovery...", "info")
        command = ["ideviceenterrecovery", "-e"] # Este comando suele salir del recovery
        result = self._execute_command(command, "Error al salir del modo Recovery")
        if result:
            self.logger.log("Dispositivo salió del modo Recovery.", "success")
            return True
        return False

    def put_device_in_dfu(self):
        """
        Placeholder para la lógica de poner un dispositivo en DFU.
        Esto es complejo y típicamente requiere interacción del usuario o herramientas específicas.
        """
        self.logger.log("Instrucciones: Por favor, pon tu dispositivo en modo DFU manualmente...", "warning")
        self.logger.log("Una vez en DFU, el software intentará detectarlo.", "warning")
        # Aquí podría haber una función que espera la detección de DFU
        return True # Asumimos que el usuario lo hará

    def detect_dfu_mode(self):
        """
        Detecta si el dispositivo está en modo DFU.
        (Generalmente, `irecovery -q` es una forma, o verificar si `idevice_id -l` no lo ve,
        pero `irecovery` sí). Esto es una simulación.
        """
        self.logger.log("Detectando modo DFU...", "info")
        # En un entorno real, se usaría una herramienta como irecovery
        # Por ahora, una simulación
        time.sleep(3)
        if self._check_device_connection(): # Si idevice_id lo ve, no está en DFU "verdadero"
             self.logger.log("Dispositivo detectado en modo normal/recovery, no DFU.", "warning")
             return False
        else:
            # Aquí se asumiría que si no está en modo normal, y se intenta DFU, podría estarlo
            # Lógica más robusta sería necesaria
            self.logger.log("Dispositivo posiblemente en modo DFU (simulado).", "success")
            return True

    def send_file_to_device(self, local_path, remote_path):
        """
        Simula el envío de un archivo al dispositivo (e.g., ramdisk, iBSS, iBEC).
        Esto requiere que el dispositivo esté en un estado específico (recovery, DFU con irecovery).
        """
        self.logger.log(f"Simulando envío de '{os.path.basename(local_path)}' a '{remote_path}'...", "info")
        # Aquí iría la lógica real con `irecovery -f` o similar
        time.sleep(2) # Simulación de tiempo
        self.logger.log(f"Archivo '{os.path.basename(local_path)}' enviado (simulado).", "success")
        return True

    def boot_ramdisk(self, ramdisk_path: str):
        """
        Simula el proceso de arranque de un ramdisk.
        Esto implicaría enviar el ramdisk y otros componentes de arranque.
        """
        if not ramdisk_path or not os.path.exists(ramdisk_path):
            self.logger.log("ERROR: Ruta de Ramdisk no válida.", "danger")
            return False

        self.logger.log(f"Iniciando arranque del Ramdisk desde: {os.path.basename(ramdisk_path)}...", "info")
        # Aquí iría la secuencia real de arranque de ramdisk (irecovery, etc.)
        self.send_file_to_device(ramdisk_path, "/private/var/root/ramdisk.dmg")
        # Enviar otros archivos de arranque como iBSS, iBEC, etc.
        self._simulate_process("Booting Ramdisk", 10)
        self.logger.log("Ramdisk arrancado con éxito (simulado).", "success")
        return True

    def run_exploit(self):
        """Simula la ejecución de un exploit."""
        self.logger.log("Simulando ejecución de exploit...", "info")
        # Lógica para ejecutar exploit (e.g., con checkra1n, palera1n)
        time.sleep(5)
        self.logger.log("Exploit ejecutado (simulado).", "success")
        return True