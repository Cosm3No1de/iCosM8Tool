

# device.py
"""
Módulo para la gestión de dispositivos iOS en la aplicación iCosM8 V3.8.
Define la clase DeviceManager, que maneja la detección, información y
operaciones básicas relacionadas con dispositivos iOS usando libimobiledevice.
"""
import subprocess
import threading
import time
import json # Importado por si alguna versión futura lo soporta, pero el parseo se hace manual
import re # Para expresiones regulares, si es necesario parsear de forma más compleja
import os # Importar os para os.path.basename y os.path.exists

from utils import COLORS # Importa COLORS para los estados de la señal
import tkinter as tk # Para tk.StringVar y .after()
from tkinter import ttk # Necesario para ttk.Label si lo usas en el manager

class DeviceManager:
    """
    Gestiona la detección y la información de los dispositivos iOS conectados.
    Utiliza herramientas de libimobiledevice para interactuar con los dispositivos.
    """
    def __init__(self, logger, signal_status_var: tk.StringVar, style_manager: ttk.Style):
        self.logger = logger
        self.signal_status_var = signal_status_var
        self.style_manager = style_manager
        self._device_info = {} # Almacena la última información del dispositivo
        self._device_connected = False
        self._check_thread = None
        self._stop_event = threading.Event()
        self._signal_label_widget = None # Se asignará después de que se cree el widget

    def set_signal_label_widget(self, label_widget: ttk.Label):
        """Asigna la referencia del widget de la etiqueta de señal."""
        self._signal_label_widget = label_widget

    def _update_signal_label_gui(self, status: str, color: str):
        """Actualiza la etiqueta de señal en el hilo principal de la GUI."""
        if self._signal_label_widget:
            self._signal_label_widget.after(0, lambda: self._signal_label_widget.config(text=status, foreground=color))

    def check_dependencies(self):
        """
        Verifica si las herramientas necesarias de libimobiledevice están instaladas.
        """
        self.logger.log("Verificando dependencias de libimobiledevice...", "info")
        required_tools = ["idevice_id", "ideviceinfo", "idevicesyslog", "ideviceenterrecovery", "idevicediagnostics", "ideviceprovision"]
        missing_tools = []

        for tool in required_tools:
            try:
                # Usamos check=False para que no lance excepción si el comando no existe o falla
                # y podamos manejarlo manualmente.
                subprocess.run([tool, "--version"], capture_output=True, check=False, timeout=5)
            except FileNotFoundError:
                missing_tools.append(tool)
            except subprocess.TimeoutExpired:
                self.logger.log(f"ADVERTENCIA: El comando '{tool} --version' excedió el tiempo de espera.", "warning")
                # No lo añadimos a missing_tools porque la herramienta podría existir pero estar lenta
                pass # Continuar con la siguiente herramienta
            except Exception as e:
                self.logger.log(f"ERROR inesperado al verificar '{tool}': {e}", "error")
                missing_tools.append(tool)


        if missing_tools:
            self.logger.log(
                f"ERROR: Las siguientes herramientas de libimobiledevice no se encontraron o no están configuradas correctamente: {', '.join(missing_tools)}. "
                "Por favor, instálalas. En sistemas basados en Debian (como Kali), usa 'sudo apt install libimobiledevice-utils usbmuxd ideviceinstaller'.",
                "danger"
            )
            # Podrías deshabilitar botones o funciones si las dependencias no están
            return False
        else:
            self.logger.log("Todas las dependencias de libimobiledevice encontradas.", "success")
            # Iniciar la detección continua de dispositivos solo si las dependencias están OK
            self.start_device_detection()
            return True

    def start_device_detection(self):
        """Inicia un hilo para la detección continua de dispositivos."""
        if self._check_thread is None or not self._check_thread.is_alive():
            self._stop_event.clear()
            self._check_thread = threading.Thread(target=self._device_detection_loop)
            self._check_thread.daemon = True # El hilo terminará cuando el programa principal termine
            self._check_thread.start()
            self.logger.log("Iniciado hilo de detección de dispositivos.", "info")

    def stop_device_detection(self):
        """Detiene el hilo de detección de dispositivos."""
        self._stop_event.set()
        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=2) # Esperar a que el hilo termine
            self.logger.log("Hilo de detección de dispositivos detenido.", "info")

    def _device_detection_loop(self):
        """Bucle para detectar dispositivos conectados cada pocos segundos."""
        while not self._stop_event.is_set():
            udid = self._get_connected_device_udid()
            if udid and not self._device_connected:
                self.logger.log(f"Dispositivo detectado con UDID: {udid}", "success")
                self._device_connected = True
                self._update_signal_label_gui("Dispositivo Conectado", COLORS["signal_green"])
                # Obtener la información completa solo una vez al conectar
                self.get_device_info(None) # No hay callback directo, solo actualiza _device_info
            elif not udid and self._device_connected:
                self.logger.log("Dispositivo desconectado.", "danger")
                self._device_connected = False
                self._update_signal_label_gui("No Hay Dispositivo", COLORS["signal_red"])
                self._device_info = {} # Limpiar información del dispositivo
                self.signal_status_var.set("No Hay Dispositivo") # Actualizar la variable de GUI
            
            # Si hay un dispositivo conectado, actualizamos la info cada X tiempo (o solo al conectar)
            # Para este ejemplo, actualizaremos la info cada 5 segundos si está conectado.
            # Podrías decidir solo actualizar al conectar o al presionar "Refrescar".
            elif udid and self._device_connected:
                 # Actualizar la info si está conectado, pero solo si es necesario, para evitar spam de logs.
                 # Por ahora, solo lo hace al conectar. Para refrescar, el usuario debe pulsar el botón.
                 pass

            time.sleep(3) # Esperar 3 segundos antes de la próxima comprobación

    def _get_connected_device_udid(self):
        """
        Obtiene el UDID del primer dispositivo conectado usando idevice_id -l.
        Basado en el error proporcionado, 'ideviceinfo -j' no es una opción válida.
        """
        try:
            # idevice_id -l lista los UDIDs de los dispositivos conectados, uno por línea
            # Usamos check=False porque idevice_id -l devuelve 1 si no hay dispositivos
            result = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode == 0:
                udids = result.stdout.strip().split('\n')
                if udids and udids[0]:
                    self.logger.log("UDID obtenida con 'idevice_id -l'.", "info")
                    return udids[0]
            else:
                # Registrar el error si no es solo "No device found"
                if "No device found" not in result.stderr and "no -l option" not in result.stderr:
                    self.logger.log(f"Error al ejecutar 'idevice_id -l': {result.stderr.strip()}", "error")
                elif "no -l option" in result.stderr:
                    self.logger.log("Advertencia: 'idevice_id -l' no es una opción válida en esta versión.", "warning")

            return None
        except FileNotFoundError:
            self.logger.log("Advertencia: 'idevice_id' no encontrado. Asegúrate de que libimobiledevice-utils esté instalado.", "warning")
            return None
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'idevice_id -l' excedió el tiempo de espera.", "warning")
            return None
        except Exception as e:
            self.logger.log(f"Excepción inesperada al intentar obtener UDID con 'idevice_id -l': {e}", "error")
            return None

    def get_device_info(self, callback=None):
        """
        Obtiene la información detallada del dispositivo conectado utilizando ideviceinfo -q <key>.
        Basado en el error proporcionado, 'ideviceinfo -j' no es una opción válida.
        """
        self.logger.log("Intentando obtener información del dispositivo...", "info")
        udid = self._get_connected_device_udid()
        if not udid:
            self.logger.log("No se detectó ningún dispositivo.", "warning")
            self._device_info = {}
            if callback:
                # Ejecutar el callback en el hilo principal de la GUI
                if hasattr(callback, '__call__'):
                    tk.Tk().after(0, lambda: callback(self._device_info))
            self._update_signal_label_gui("No Hay Dispositivo", COLORS["signal_red"])
            self.signal_status_var.set("No Hay Dispositivo")
            return

        device_data = {"UniqueDeviceID": udid} # Ya tenemos el UDID del paso anterior

        # Campos que queremos obtener usando 'ideviceinfo -q <key>'
        # Puedes añadir o quitar campos según tus necesidades.
        # Asegúrate de que los dominios y claves existan en tu versión de ideviceinfo.
        keys_to_get = {
            "ProductType": None,
            "ProductVersion": None,
            "SerialNumber": None,
            "UniqueChipID": None,
            "InternationalMobileEquipmentIdentity": None,
            # Ejemplo de cómo obtener una clave dentro de un dominio específico:
            # "BatteryCurrentCapacity": "com.apple.mobile.battery",
            # "DeviceName": "com.apple.mobile.lockdownd" # El dominio por defecto es "com.apple.mobile.lockdownd"
        }
        
        for key, domain in keys_to_get.items():
            cmd_key = ["ideviceinfo", "-u", udid, "-k", key]
            if domain:
                cmd_key.extend(["-q", domain])

            try:
                key_process = subprocess.run(cmd_key, capture_output=True, text=True, check=True, timeout=5)
                device_data[key] = key_process.stdout.strip()
            except subprocess.CalledProcessError as e:
                # Si la clave no existe o hay un error para esa clave, registrar y continuar
                if "Could not connect to lockdownd" in e.stderr:
                    self.logger.log(f"Error al conectar con el dispositivo para obtener '{key}': {e.stderr.strip()}", "error")
                    # Esto podría significar que el dispositivo se desconectó o cambió de estado
                    # Si esto ocurre, la información del dispositivo puede estar incompleta
                    device_data[key] = "N/A"
                    # Si la conexión falla, es probable que todas las demás llamadas también fallen.
                    # Podemos considerar salir del bucle aquí si es un error crítico de conexión.
                    self.logger.log("Conexión con el dispositivo perdida, no se obtendrá más información.", "danger")
                    break 
                else:
                    self.logger.log(f"Advertencia: No se pudo obtener '{key}': {e.stderr.strip()}", "warning")
                    device_data[key] = "N/A"
            except subprocess.TimeoutExpired:
                self.logger.log(f"El comando 'ideviceinfo -u {udid} -k {key}' excedió el tiempo de espera.", "warning")
                device_data[key] = "N/A"
            except FileNotFoundError:
                self.logger.log("Error: 'ideviceinfo' no encontrado al intentar obtener información detallada.", "danger")
                # Si ideviceinfo no se encuentra, no se puede obtener más información
                break
            except Exception as e:
                self.logger.log(f"Excepción inesperada al obtener '{key}': {e}", "error")
                device_data[key] = "N/A"

        self._device_info = device_data
        self.logger.log("Información del dispositivo obtenida con 'ideviceinfo -u <udid> -k <key>'.", "success")
        
        # Después de obtener la información (o fallar), actualizar la variable de estado
        # Consideramos que hay un dispositivo conectado si al menos se obtuvo el UDID y ProductVersion (o alguna otra clave esencial)
        if self._device_info and self._device_info.get("UniqueDeviceID") and self._device_info.get("ProductVersion") != "N/A":
            self.signal_status_var.set("Dispositivo Conectado")
            self._update_signal_label_gui("Dispositivo Conectado", COLORS["signal_green"])
        else:
            self.signal_status_var.set("No Hay Dispositivo")
            self._update_signal_label_gui("No Hay Dispositivo", COLORS["signal_red"])
            self._device_info = {} # Asegurarse de que la info se limpie si no se detecta nada o está incompleta

        # Llamar al callback con la información obtenida
        if callback:
            # Ejecutar el callback en el hilo principal de la GUI
            if hasattr(callback, '__call__'):
                tk.Tk().after(0, lambda: callback(self._device_info))

    def get_current_device_info(self):
        """Devuelve la última información conocida del dispositivo."""
        return self._device_info

    # --- Métodos para operaciones de cambio de modo de dispositivo ---

    def enter_recovery_mode(self):
        """
        Intenta poner el dispositivo en modo Recovery.
        """
        self.logger.log("Intentando poner el dispositivo en modo Recovery...", "info")
        udid = self._get_connected_device_udid()
        if not udid:
            self.logger.log("No hay dispositivo conectado para entrar en Recovery.", "warning")
            return False
        try:
            # ideviceenterrecovery <UDID>
            # Algunos ideviceenterrecovery no necesitan UDID si solo hay un dispositivo
            subprocess.run(["ideviceenterrecovery"], check=True, capture_output=True, timeout=10)
            self.logger.log("Dispositivo en modo Recovery.", "success")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.log(f"Error al intentar entrar en modo Recovery: {e.stderr.decode()}", "danger")
            return False
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'ideviceenterrecovery' excedió el tiempo de espera.", "warning")
            return False
        except FileNotFoundError:
            self.logger.log("Error: 'ideviceenterrecovery' no encontrado.", "danger")
            return False

    def exit_recovery_mode(self):
        """
        Intenta sacar el dispositivo del modo Recovery.
        """
        self.logger.log("Intentando sacar el dispositivo de modo Recovery...", "info")
        udid = self._get_connected_device_udid() # Obtener UDID para asegurar que hay un dispositivo
        if not udid:
            self.logger.log("No hay dispositivo conectado para salir de Recovery.", "warning")
            return False
        
        try:
            # ideviceenterrecovery -n es una opción común para salir de recovery
            subprocess.run(["ideviceenterrecovery", "-n"], check=True, capture_output=True, timeout=10)
            self.logger.log("Dispositivo forzado a salir de modo Recovery.", "success")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.log(f"Error al intentar salir de modo Recovery con ideviceenterrecovery -n: {e.stderr.decode()}", "warning")
            self.logger.log("Intentando con 'idevicediagnostics restart' (puede requerir un dispositivo booted)...", "info")
            try:
                # idevicediagnostics restart puede reiniciar el dispositivo si está en un estado semi-normal
                subprocess.run(["idevicediagnostics", "restart"], check=True, capture_output=True, timeout=10)
                self.logger.log("Comando de reinicio enviado.", "success")
            except subprocess.CalledProcessError as e2:
                self.logger.log(f"Falló 'idevicediagnostics restart': {e2.stderr.decode()}", "danger")
                self.logger.log("La salida de Recovery puede requerir una herramienta específica como futurerestore o un jailbreak.", "warning")
                return False
            except subprocess.TimeoutExpired:
                self.logger.log("El comando 'idevicediagnostics restart' excedió el tiempo de espera.", "warning")
                return False
            except FileNotFoundError:
                self.logger.log("Error: 'idevicediagnostics' no encontrado.", "danger")
                return False
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'ideviceenterrecovery -n' excedió el tiempo de espera.", "warning")
            return False
        except FileNotFoundError:
            self.logger.log("Error: 'ideviceenterrecovery' no encontrado.", "danger")
            return False
        return True # Si llega aquí, al menos un intento de salida de recovery fue exitoso

    def put_device_in_dfu(self):
        """
        Placeholder para la lógica de poner un dispositivo en DFU.
        Esto es complejo y típicamente requiere interacción del usuario o herramientas específicas
        como checkra1n/palera1n o irecovery.
        """
        self.logger.log("Instrucciones: Por favor, pon tu dispositivo en modo DFU manualmente...", "warning")
        self.logger.log("Una vez en DFU, el software intentará detectarlo.", "warning")
        # Aquí podría haber una función que espera la detección de DFU
        return True # Asumimos que el usuario lo hará

    def detect_dfu_mode(self):
        """
        Detecta si el dispositivo está en modo DFU.
        (Generalmente, `irecovery -q` es una forma, o verificar si `idevice_id -l` no lo ve,
        pero `irecovery` sí). Esto es una simulación por ahora.
        """
        self.logger.log("Detectando modo DFU (simulado)...", "info")
        # En un entorno real, se usaría una herramienta como irecovery para detectar DFU
        # Por ahora, una simulación
        time.sleep(3)
        # Si ideviceinfo no devuelve UDID, podría estar en DFU o simplemente desconectado
        # Una detección real de DFU es más compleja y específica de cada herramienta.
        if not self._get_connected_device_udid(): # Si no hay UDID en modo normal/recovery
             self.logger.log("Dispositivo posiblemente en modo DFU (no detectado en modo normal).", "success")
             return True
        else:
            self.logger.log("Dispositivo detectado en modo normal/recovery, no DFU.", "warning")
            return False

    def send_file_to_device(self, local_path, remote_path):
        """
        Simula el envío de un archivo al dispositivo (e.g., ramdisk, iBSS, iBEC).
        Esto requiere que el dispositivo esté en un estado específico (recovery, DFU con irecovery).
        """
        # Añadida la verificación del archivo local_path
        if not os.path.exists(local_path):
            self.logger.log(f"ERROR: El archivo local '{local_path}' no existe.", "danger")
            return False

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
            self.logger.log("ERROR: Ruta de Ramdisk no válida o el archivo no existe.", "danger")
            return False

        self.logger.log(f"Iniciando arranque del Ramdisk desde: {os.path.basename(ramdisk_path)}...", "info")
        # Aquí iría la secuencia real de arranque de ramdisk (irecovery, etc.)
        # Por ejemplo:
        # if self.detect_dfu_mode():
        #    self.send_file_to_device("path/to/iBSS.img", "/tmp/iBSS")
        #    self.send_file_to_device("path/to/iBEC.img", "/tmp/iBEC")
        #    self.send_file_to_device(ramdisk_path, "/private/var/root/ramdisk.dmg")
        #    subprocess.run(["irecovery", "-c", "bootx"], check=True) # Comando para bootear
        
        # Simulación
        time.sleep(5)
        self.logger.log("Ramdisk arrancado con éxito (simulado).", "success")
        return True