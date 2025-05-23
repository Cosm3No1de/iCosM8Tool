# device.py
"""
Módulo para la gestión de dispositivos iOS en la aplicación iCosM8 V3.8.
Define la clase DeviceManager, que maneja la detección, información y
operaciones básicas relacionadas con dispositivos iOS usando libimobiledevice.
"""
import subprocess
import threading
import time
import json
import re
import os
import platform
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from utils import COLORS

class DeviceManager:
    """
    Gestiona la detección y la información de los dispositivos iOS conectados.
    Utiliza herramientas de libimobiledevice para interactuar con los dispositivos.
    """
    def __init__(self, logger, signal_status_var: tk.StringVar, style_manager: ttk.Style):
        self.logger = logger
        self.signal_status_var = signal_status_var
        self.style_manager = style_manager
        self._device_info = {}
        self._device_connected = False
        self._check_thread = None
        self._stop_event = threading.Event()
        self._signal_label_widget = None

    def set_signal_label_widget(self, label_widget: ttk.Label):
        """Asigna la referencia del widget de la etiqueta de señal."""
        self.logger.log("Etiqueta de señal de dispositivo asignada.", "info")
        self._signal_label_widget = label_widget

    def _update_signal_label_gui(self, status: str, color: str):
        """Actualiza la etiqueta de señal en el hilo principal de la GUI."""
        if self._signal_label_widget:
            self._signal_label_widget.after(0, lambda: self._signal_label_widget.config(text=status, foreground=color))

    def _check_and_start_usbmuxd(self) -> bool:
        """
        Verifica el estado de usbmuxd y lo intenta iniciar si es necesario en sistemas Linux.
        Devuelve True si usbmuxd está activo o pudo iniciarse, False en caso contrario.
        """
        if platform.system() == "Linux":
            self.logger.log("Verificando estado del servicio usbmuxd...", "info")
            try:
                status_cmd = ["systemctl", "is-active", "usbmuxd"]
                status_result = subprocess.run(status_cmd, capture_output=True, text=True, check=False, timeout=5)

                if "active" in status_result.stdout.strip():
                    self.logger.log("usbmuxd está activo y corriendo.", "success")
                    return True
                else:
                    self.logger.log("usbmuxd está inactivo. Intentando iniciarlo...", "warning")
                    try:
                        start_cmd = ["sudo", "systemctl", "start", "usbmuxd"]
                        start_result = subprocess.run(start_cmd, capture_output=True, text=True, check=False, timeout=10)

                        if start_result.returncode == 0:
                            self.logger.log("usbmuxd iniciado con éxito. Verificando estado final...", "success")
                            time.sleep(1)
                            status_after_start = subprocess.run(status_cmd, capture_output=True, text=True, check=False, timeout=5)
                            if "active" in status_after_start.stdout.strip():
                                self.logger.log("usbmuxd verificado como activo después del inicio.", "success")
                                return True
                            else:
                                self.logger.log(f"usbmuxd falló en activarse después del intento de inicio. Salida: {status_after_start.stderr.strip()}", "danger")
                                messagebox.showerror("Error de Servicio",
                                    "usbmuxd no pudo iniciarse automáticamente.\n"
                                    "Por favor, abre una terminal y ejecuta:\n\n"
                                    "sudo systemctl start usbmuxd\n\n"
                                    "Luego reintenta la operación."
                                )
                                return False
                        else:
                            self.logger.log(f"Fallo al iniciar usbmuxd con sudo. Código de salida: {start_result.returncode}. Error: {start_result.stderr.strip()}", "danger")
                            messagebox.showerror("Error de Permisos o Inicio",
                                "No se pudo iniciar usbmuxd automáticamente.\n"
                                "Esto puede deberse a que la aplicación no tiene los permisos necesarios (sudo).\n"
                                "Por favor, abre una terminal y ejecuta:\n\n"
                                "sudo systemctl start usbmuxd\n\n"
                                "Luego reintenta la operación."
                            )
                            return False
                    except FileNotFoundError:
                        self.logger.log("Comando 'sudo' o 'systemctl' no encontrado. Asegúrate de que systemd esté disponible y sudo instalado.", "danger")
                        messagebox.showerror("Error de Sistema",
                            "Los comandos de sistema (sudo/systemctl) no se encontraron.\n"
                            "Tu sistema Linux podría no estar configurado correctamente o no usar systemd.\n"
                            "Asegúrate de que 'usbmuxd' esté activo manualmente."
                        )
                        return False
                    except subprocess.TimeoutExpired:
                        self.logger.log("El intento de inicio de usbmuxd excedió el tiempo de espera.", "warning")
                        messagebox.showerror("Error de Servicio",
                            "El intento de iniciar usbmuxd excedió el tiempo de espera.\n"
                            "Por favor, intenta iniciarlo manualmente en la terminal:\n\n"
                            "sudo systemctl start usbmuxd"
                        )
                        return False
                    except Exception as e:
                        self.logger.log(f"Excepción inesperada al intentar iniciar usbmuxd: {e}", "error")
                        messagebox.showerror("Error Inesperado",
                            f"Ocurrió un error inesperado al intentar iniciar usbmuxd: {e}\n"
                            "Por favor, verifica el servicio manualmente."
                        )
                        return False
            except FileNotFoundError:
                self.logger.log("Comando 'systemctl' no encontrado. Asegúrate de que tu sistema use systemd.", "danger")
                messagebox.showerror("Error de Sistema",
                    "El comando 'systemctl' no se encontró.\n"
                    "Tu sistema Linux podría no estar configurado correctamente o no usar systemd.\n"
                    "Asegúrate de que 'usbmuxd' esté activo manualmente."
                )
                return False
            except subprocess.TimeoutExpired:
                self.logger.log("La verificación del estado de usbmuxd excedió el tiempo de espera.", "warning")
                return False
            except Exception as e:
                self.logger.log(f"Excepción inesperada al verificar usbmuxd: {e}", "error")
                return False
        else:
            self.logger.log(f"Sistema operativo '{platform.system()}' no es Linux. Saltando verificación de usbmuxd.", "info")
            return True # Asumimos que no es necesario o se maneja de otra forma en otros OS

    def _install_debian_dependencies(self, missing_tools: list) -> bool:
        """
        Intenta instalar las dependencias de libimobiledevice en sistemas Debian/Ubuntu.
        Devuelve True si la instalación parece exitosa, False en caso contrario.
        """
        self.logger.log("Intentando instalar dependencias de libimobiledevice...", "info")
        required_packages = []

        # Siempre incluimos los paquetes base recomendados
        required_packages.extend([
            "libimobiledevice-utils",
            "usbmuxd",
            "ideviceinstaller",
            "libimobiledevice-dev",
            "irecovery" # Aseguramos que 'irecovery' sea parte de la lista a instalar
        ])

        # Comando para actualizar y luego instalar
        install_cmd = ["sudo", "apt", "update", "&&", "sudo", "apt", "install", "-y"] + required_packages
        
        # Unimos el comando para mostrarlo al usuario si falla
        install_cmd_str = " ".join(install_cmd)

        try:
            # Ejecutar con shell=True porque usamos "&&" para encadenar comandos
            # Esto es menos seguro si la entrada es del usuario, pero aquí el comando es fijo.
            self.logger.log(f"Ejecutando: {install_cmd_str}", "info")
            install_process = subprocess.run(install_cmd_str, shell=True, capture_output=True, text=True, check=False, timeout=300) # 5 minutos

            if install_process.returncode == 0:
                self.logger.log("Dependencias de libimobiledevice instaladas con éxito (o ya presentes).", "success")
                return True
            else:
                self.logger.log(f"Fallo al instalar dependencias. Código de salida: {install_process.returncode}. Errores:\n{install_process.stderr}", "danger")
                messagebox.showerror("Error de Instalación",
                    "No se pudieron instalar las dependencias de libimobiledevice automáticamente.\n"
                    "Esto puede deberse a falta de permisos (sudo), problemas de red, o un repositorio no configurado.\n\n"
                    "Por favor, abre una terminal y ejecuta manualmente:\n\n"
                    f"{install_cmd_str}\n\n"
                    "Luego reinicia la aplicación."
                )
                return False
        except FileNotFoundError:
            self.logger.log("ERROR: 'sudo' o 'apt' no encontrados. Asegúrate de que tu sistema sea Debian/Ubuntu y que sudo esté instalado.", "danger")
            messagebox.showerror("Error de Sistema",
                "Comandos de instalación (sudo/apt) no encontrados.\n"
                "Tu sistema Linux podría no ser Debian/Ubuntu.\n"
                "Instala las herramientas de libimobiledevice manualmente."
            )
            return False
        except subprocess.TimeoutExpired:
            self.logger.log("La instalación de dependencias excedió el tiempo de espera.", "warning")
            messagebox.showerror("Error de Instalación",
                "La instalación de dependencias excedió el tiempo de espera.\n"
                "Por favor, intenta instalarlas manualmente en la terminal:\n\n"
                f"{install_cmd_str}"
            )
            return False
        except Exception as e:
            self.logger.log(f"Excepción inesperada durante la instalación: {e}", "error")
            messagebox.showerror("Error Inesperado",
                f"Ocurrió un error inesperado al intentar instalar dependencias: {e}\n"
                "Por favor, intenta instalarlas manualmente."
            )
            return False

    def check_dependencies(self):
        """
        Verifica si las herramientas necesarias de libimobiledevice están instaladas
        y si el servicio usbmuxd está activo (en Linux). Si no, intenta instalarlas.
        """
        self.logger.log("Iniciando verificación y posible instalación de dependencias de libimobiledevice...", "info")

        # Primero, verifica y/o intenta iniciar usbmuxd si estamos en Linux
        if platform.system() == "Linux":
            if not self._check_and_start_usbmuxd():
                self.logger.log("El servicio usbmuxd no está activo. No se puede proceder con la verificación de herramientas iOS.", "danger")
                return False

        # Continuar con la verificación de otras herramientas de libimobiledevice
        required_tools = ["idevice_id", "ideviceinfo", "idevicesyslog", "ideviceenterrecovery", "idevicediagnostics", "ideviceprovision", "irecovery"]
        missing_tools = []

        for tool in required_tools:
            try:
                # Modificación clave aquí:
                # Para solo verificar si la herramienta existe y puede ejecutarse (--version),
                # y silenciar toda la salida (stdout y stderr), redirigimos ambas a DEVNULL.
                # No usamos 'capture_output=True' porque no queremos capturar nada, solo ejecutar.
                subprocess.run([tool, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=5)
            except FileNotFoundError:
                missing_tools.append(tool)
            except subprocess.TimeoutExpired:
                self.logger.log(f"ADVERTENCIA: El comando '{tool} --version' excedió el tiempo de espera. Podría indicar un problema, pero continuamos.", "warning")
                # No se añade a missing_tools aquí, ya que podría estar la herramienta pero ser lenta
            except Exception as e:
                # Esto captura cualquier otra excepción inesperada durante la verificación
                self.logger.log(f"ERROR inesperado al verificar '{tool}': {e}", "error")
                missing_tools.append(tool) # Si hay una excepción inesperada, la consideramos faltante

        if missing_tools:
            self.logger.log(f"ADVERTENCIA: Se encontraron herramientas de libimobiledevice faltantes: {', '.join(missing_tools)}.", "warning")
            if platform.system() == "Linux":
                self.logger.log("Intentando instalación automática de dependencias en Linux...", "info")
                if self._install_debian_dependencies(missing_tools):
                    # Después de intentar instalar, volvemos a verificar para confirmar
                    self.logger.log("Re-verificando dependencias después de la instalación...", "info")
                    re_missing_tools = []
                    for tool in required_tools:
                        try:
                            subprocess.run([tool, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=5)
                        except FileNotFoundError:
                            re_missing_tools.append(tool)
                        except subprocess.TimeoutExpired:
                            pass
                        except Exception:
                            re_missing_tools.append(tool)

                    if re_missing_tools:
                        self.logger.log(f"ERROR: Aún faltan herramientas después de la instalación automática: {', '.join(re_missing_tools)}.", "danger")
                        messagebox.showerror("Fallo de Instalación",
                            "Algunas herramientas de libimobiledevice aún no se encontraron después de la instalación automática.\n"
                            "Por favor, revisa los logs en la terminal para posibles errores y considera instalarlas manualmente.\n"
                            "Herramientas faltantes: " + ", ".join(re_missing_tools)
                        )
                        return False
                    else:
                        self.logger.log("Todas las dependencias encontradas después de la instalación automática.", "success")
                        self.start_device_detection()
                        return True
                else:
                    self.logger.log("Fallo la instalación automática de dependencias. La aplicación no puede continuar.", "danger")
                    return False
            else: # Otros sistemas operativos
                self.logger.log(
                    f"ERROR: Las siguientes herramientas de libimobiledevice no se encontraron o no están configuradas correctamente: {', '.join(missing_tools)}. "
                    "Para otros sistemas operativos (no Linux), por favor, instala estas herramientas manualmente. "
                    "Consulta la documentación oficial de libimobiledevice para tu sistema operativo.",
                    "danger"
                )
                messagebox.showerror("Dependencias Faltantes",
                    "Algunas herramientas de libimobiledevice no se encontraron.\n"
                    "Para tu sistema operativo, por favor, instálalas manualmente y reinicia la aplicación.\n"
                    "Herramientas faltantes: " + ", ".join(missing_tools)
                )
                return False
        else:
            self.logger.log("Todas las dependencias de libimobiledevice encontradas.", "success")
            self.start_device_detection() # Iniciar la detección continua de dispositivos
            return True


    def start_device_detection(self):
        """Inicia un hilo para la detección continua de dispositivos."""
        if self._check_thread is None or not self._check_thread.is_alive():
            self._stop_event.clear()
            self._check_thread = threading.Thread(target=self._device_detection_loop)
            self._check_thread.daemon = True
            self._check_thread.start()
            self.logger.log("Iniciado hilo de detección de dispositivos.", "info")

    def stop_device_detection(self):
        """Detiene el hilo de detección de dispositivos."""
        self._stop_event.set()
        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=2)
            self.logger.log("Hilo de detección de dispositivos detenido.", "info")

    def _device_detection_loop(self):
        """Bucle para detectar dispositivos conectados cada pocos segundos."""
        while not self._stop_event.is_set():
            udid = self._get_connected_device_udid()
            if udid and not self._device_connected:
                self.logger.log(f"Dispositivo detectado con UDID: {udid}", "success")
                self._device_connected = True
                self._update_signal_label_gui("Dispositivo Conectado", COLORS["signal_green"])
                self.get_device_info(None)
            elif not udid and self._device_connected:
                self.logger.log("Dispositivo desconectado.", "danger")
                self._device_connected = False
                self._update_signal_label_gui("No Hay Dispositivo", COLORS["signal_red"])
                self._device_info = {}
                self.signal_status_var.set("No Hay Dispositivo")
            
            time.sleep(3)

    def _get_connected_device_udid(self):
        """
        Obtiene el UDID del primer dispositivo conectado usando idevice_id -l.
        """
        try:
            result = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True, check=False, timeout=5)
            
            if result.returncode == 0:
                udids = result.stdout.strip().split('\n')
                if udids and udids[0]:
                    self.logger.log(f"UDID obtenida con 'idevice_id -l': {udids[0]}", "info")
                    return udids[0]
            else:
                if "Unable to retrieve device list!" in result.stderr:
                    self.logger.log(
                        "ERROR: 'idevice_id' no puede acceder a la lista de dispositivos. Esto puede deberse a:\n"
                        "  1. El daemon 'usbmuxd' no está corriendo o está mal configurado. (Verifica su estado y reinícialo si es necesario).\n"
                        "  2. Permisos USB incorrectos. Añade tu usuario al grupo 'usbmux'/'plugdev' y reinicia sesión.\n"
                        "  3. El dispositivo no ha aceptado la confianza en esta computadora (desbloquea el dispositivo iOS y acepta la confianza).\n"
                        "  4. Problema con el cable o puerto USB. Prueba otro.",
                        "danger"
                    )
                elif "No device found" not in result.stderr and "no -l option" not in result.stderr:
                    self.logger.log(f"Error al ejecutar 'idevice_id -l': {result.stderr.strip()}", "error")
                elif "no -l option" in result.stderr:
                    self.logger.log("ADVERTENCIA: 'idevice_id -l' no es una opción válida en esta versión de libimobiledevice. La detección de dispositivos podría fallar.", "danger")
            return None
        except FileNotFoundError:
            self.logger.log("ADVERTENCIA: 'idevice_id' no encontrado. Asegúrate de que libimobiledevice-utils esté instalado.", "warning")
            return None
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'idevice_id -l' excedió el tiempo de espera.", "warning")
            return None
        except Exception as e:
            self.logger.log(f"EXCEPCIÓN INESPERADA al intentar obtener UDID con 'idevice_id -l': {e}", "error")
            return None

    def get_device_info(self, callback=None):
        """
        Obtiene la información detallada del dispositivo conectado utilizando ideviceinfo -u <udid> -k <key>.
        """
        self.logger.log("Intentando obtener información del dispositivo...", "info")
        udid = self._get_connected_device_udid()
        if not udid:
            self.logger.log("No se detectó ningún dispositivo.", "warning")
            self._device_info = {}
            if callback:
                callback(self._device_info)
            self._update_signal_label_gui("No Hay Dispositivo", COLORS["signal_red"])
            self.signal_status_var.set("No Hay Dispositivo")
            return

        device_data = {"UniqueDeviceID": udid}

        keys_to_get = {
            "ProductType": None,
            "ProductVersion": None,
            "SerialNumber": None,
            "UniqueChipID": None,
            "InternationalMobileEquipmentIdentity": None,
            "DeviceName": None,
            "BatteryCurrentCapacity": "com.apple.mobile.battery",
            "BoardId": None,
            "ChipID": None,
            "ModelNumber": None,
            "HardwareModel": None,
            "CPUArchitecture": None,
        }

        for key, domain in keys_to_get.items():
            cmd_key = ["ideviceinfo", "-u", udid, "-k", key]
            if domain:
                cmd_key.extend(["-q", domain])

            try:
                key_process = subprocess.run(cmd_key, capture_output=True, text=True, check=True, timeout=5)
                device_data[key] = key_process.stdout.strip()
            except subprocess.CalledProcessError as e:
                if "Could not connect to lockdownd" in e.stderr:
                    self.logger.log(f"ERROR: Conexión con el dispositivo perdida al intentar obtener '{key}': {e.stderr.strip()}", "danger")
                    device_data[key] = "N/A"
                    self.logger.log("No se obtendrá más información del dispositivo debido a un error de conexión.", "danger")
                    break
                elif "No such key" in e.stderr or "Could not get value for key" in e.stderr:
                    self.logger.log(f"ADVERTENCIA: La clave '{key}' no se encontró en el dispositivo o dominio especificado. {e.stderr.strip()}", "warning")
                    device_data[key] = "N/A"
                else:
                    self.logger.log(f"ERROR al ejecutar ideviceinfo para '{key}': {e.stderr.strip()}", "error")
                    device_data[key] = "N/A"
            except subprocess.TimeoutExpired:
                self.logger.log(f"El comando 'ideviceinfo -u {udid} -k {key}' excedió el tiempo de espera.", "warning")
                device_data[key] = "N/A"
            except FileNotFoundError:
                self.logger.log("ERROR CRÍTICO: 'ideviceinfo' no encontrado al intentar obtener información detallada. Verifica tu instalación.", "danger")
                break
            except Exception as e:
                self.logger.log(f"EXCEPCIÓN INESPERADA al obtener '{key}': {e}", "error")
                device_data[key] = "N/A"

        self._device_info = device_data
        
        if self._device_info and self._device_info.get("UniqueDeviceID") and self._device_info.get("ProductVersion") != "N/A":
            self.signal_status_var.set("Dispositivo Conectado")
            self._update_signal_label_gui("Dispositivo Conectado", COLORS["signal_green"])
            self.logger.log("Información del dispositivo obtenida con éxito.", "success")
        else:
            self.signal_status_var.set("No Hay Dispositivo")
            self._update_signal_label_gui("No Hay Dispositivo", COLORS["signal_red"])
            self._device_info = {}
            self.logger.log("No se pudo obtener información completa del dispositivo.", "warning")

        if callback:
            callback(self._device_info)

    def get_current_device_info(self):
        """Devuelve la última información conocida del dispositivo."""
        return self._device_info

    # --- Métodos para operaciones de cambio de modo de dispositivo ---

    def enter_recovery_mode(self):
        """
        Intenta poner el dispositivo en modo Recovery.
        Implementa una lógica más robusta para versiones de ideviceenterrecovery.
        """
        self.logger.log("Intentando poner el dispositivo en modo Recovery...", "info")
        udid = self._get_connected_device_udid()
        if not udid:
            self.logger.log("No hay dispositivo conectado para entrar en Recovery.", "warning")
            return False
        
        try:
            result = subprocess.run(["ideviceenterrecovery"], check=False, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.log("Dispositivo en modo Recovery (sin especificar UDID).", "success")
                return True
            else:
                self.logger.log(f"ideviceenterrecovery sin UDID falló: {result.stderr.strip()}. Intentando con UDID...", "info")
                
                current_udid = self._get_connected_device_udid()
                if current_udid:
                    subprocess.run(["ideviceenterrecovery", current_udid], check=True, capture_output=True, text=True, timeout=10)
                    self.logger.log(f"Dispositivo en modo Recovery (con UDID: {current_udid}).", "success")
                    return True
                else:
                    self.logger.log("No se pudo obtener el UDID para intentar entrar en Recovery con él.", "warning")
                    return False

        except subprocess.CalledProcessError as e:
            self.logger.log(f"Error al intentar entrar en modo Recovery: {e.stderr.strip()}", "danger")
            return False
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'ideviceenterrecovery' excedió el tiempo de espera.", "warning")
            return False
        except FileNotFoundError:
            self.logger.log("ERROR: 'ideviceenterrecovery' no encontrado. Asegúrate de que 'libimobiledevice-utils' esté instalado.", "danger")
            return False
        except Exception as e:
            self.logger.log(f"EXCEPCIÓN INESPERADA al intentar entrar en modo Recovery: {e}", "error")
            return False

    def exit_recovery_mode(self):
        """
        Intenta sacar el dispositivo del modo Recovery.
        Prueba múltiples métodos para mayor robustez.
        """
        self.logger.log("Intentando sacar el dispositivo de modo Recovery...", "info")
        udid = self._get_connected_device_udid()
        if not udid:
            self.logger.log("No hay dispositivo conectado para intentar salir de Recovery.", "warning")
            return False
        
        try:
            self.logger.log("Intentando salir de Recovery con 'ideviceenterrecovery -n'...", "info")
            subprocess.run(["ideviceenterrecovery", "-n"], check=True, capture_output=True, text=True, timeout=10)
            self.logger.log("Dispositivo forzado a salir de modo Recovery (con -n).", "success")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.log(f"Falló 'ideviceenterrecovery -n': {e.stderr.decode().strip()}", "warning")
            self.logger.log("Intentando con 'idevicediagnostics restart' (puede requerir un dispositivo booted o en un estado específico)...", "info")
            try:
                subprocess.run(["idevicediagnostics", "restart"], check=True, capture_output=True, text=True, timeout=10)
                self.logger.log("Comando de reinicio enviado con idevicediagnostics restart.", "success")
                return True
            except subprocess.CalledProcessError as e2:
                self.logger.log(f"Falló 'idevicediagnostics restart': {e2.stderr.decode().strip()}", "danger")
                self.logger.log("La salida de Recovery puede requerir una herramienta específica como futurerestore o un jailbreak (ej. checkra1n/palera1n) si el dispositivo no coopera.", "warning")
                return False
            except subprocess.TimeoutExpired:
                self.logger.log("El comando 'idevicediagnostics restart' excedió el tiempo de espera.", "warning")
                return False
            except FileNotFoundError:
                self.logger.log("ERROR: 'idevicediagnostics' no encontrado. Asegúrate de que esté instalado.", "danger")
                return False
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'ideviceenterrecovery -n' excedió el tiempo de espera.", "warning")
            return False
        except FileNotFoundError:
            self.logger.log("ERROR: 'ideviceenterrecovery' no encontrado. Asegúrate de que esté instalado.", "danger")
            return False
        
        return False

    def put_device_in_dfu(self, checkra1n_path: str = "checkra1n", palera1n_path: str = "palera1n"):
        """
        Intenta poner el dispositivo en modo DFU.
        Esto típicamente requiere la interacción del usuario o el uso de herramientas de exploit
        como checkra1n o palera1n para entrar en "Pwned DFU".
        """
        self.logger.log("ATENCIÓN: Por favor, pon tu dispositivo en modo DFU manualmente o usando una herramienta de exploit.", "warning")
        self.logger.log("Si tu dispositivo es vulnerable a checkm8 (A11 y anteriores), puedes intentar usar checkra1n/palera1n para ponerlo en DFU pwned.", "info")

        self.logger.log("Esperando que el usuario ponga el dispositivo en DFU manualmente. Intenta detectar el modo DFU...", "info")
        return True

    def detect_dfu_mode(self):
        """
        Detecta si el dispositivo está en modo DFU utilizando 'irecovery -q'.
        Un dispositivo en DFU típicamente no aparece con `idevice_id -l`.
        """
        self.logger.log("Detectando modo DFU...", "info")
        try:
            result_irecovery = subprocess.run(["irecovery", "-q"], capture_output=True, text=True, check=False, timeout=5)
            
            if result_irecovery.returncode == 0:
                output_upper = result_irecovery.stdout.upper()
                if "CPID" in output_upper and ("SRAM" in output_upper or "DFU" in output_upper):
                    self.logger.log("Dispositivo detectado en modo DFU.", "success")
                    return True
                else:
                    self.logger.log("Dispositivo detectado en modo Recovery (no DFU, según irecovery -q).", "warning")
                    return False
            else:
                if not self._get_connected_device_udid():
                    self.logger.log("No se detectó un dispositivo en modo normal, pero irecovery -q tampoco lo detectó en DFU/Recovery. Podría estar desconectado o en un estado no reconocido.", "info")
                    return False
                else:
                    self.logger.log(f"irecovery -q no detectó dispositivo en Recovery/DFU: {result_irecovery.stderr.strip()} (dispositivo detectado en modo normal).", "warning")
                    return False

        except FileNotFoundError:
            self.logger.log("ADVERTENCIA: 'irecovery' no encontrado. Necesario para una detección precisa del modo DFU. Asegúrate de instalar 'libirecovery-utils' o compilarlo.", "warning")
            if not self._get_connected_device_udid():
                self.logger.log("Dispositivo posiblemente en modo DFU (no detectado en modo normal, pero 'irecovery' no disponible para confirmar).", "info")
                return True
            return False
        except subprocess.TimeoutExpired:
            self.logger.log("El comando 'irecovery -q' excedió el tiempo de espera.", "warning")
            return False
        except Exception as e:
            self.logger.log(f"EXCEPCIÓN INESPERADA al intentar detectar DFU con irecovery: {e}", "error")
            return False

    def send_file_to_device(self, local_path: str):
        """
        Envía un archivo al dispositivo usando irecovery.
        Requiere que el dispositivo esté en modo Recovery o DFU.
        La ruta remota es implícita para irecovery -f.
        """
        if not os.path.exists(local_path):
            self.logger.log(f"ERROR: El archivo local '{local_path}' no existe.", "danger")
            return False

        self.logger.log(f"Intentando enviar '{os.path.basename(local_path)}' al dispositivo con irecovery...", "info")
        
        try:
            result = subprocess.run(["irecovery", "-f", local_path], check=True, capture_output=True, text=True, timeout=60)
            self.logger.log(f"Archivo '{os.path.basename(local_path)}' enviado con éxito.", "success")
            if result.stdout:
                self.logger.log(f"Salida de irecovery: {result.stdout.strip()}", "debug")
            return True
        except FileNotFoundError:
            self.logger.log("ERROR: 'irecovery' no encontrado. Necesario para enviar archivos al dispositivo.", "danger")
            return False
        except subprocess.CalledProcessError as e:
            self.logger.log(f"ERROR al enviar '{os.path.basename(local_path)}': {e.stderr.strip()}", "danger")
            self.logger.log("Asegúrate de que el dispositivo esté en el modo correcto (ej. DFU) y de que el archivo sea compatible.", "warning")
            return False
        except subprocess.TimeoutExpired:
            self.logger.log(f"El comando 'irecovery -f {os.path.basename(local_path)}' excedió el tiempo de espera.", "warning")
            return False
        except Exception as e:
            self.logger.log(f"EXCEPCIÓN INESPERADA al enviar archivo: {e}", "error")
            return False

    def boot_ramdisk(self, ramdisk_path: str, ibss_path: str = None, ibec_path: str = None):
        """
        Arranca un ramdisk en el dispositivo.
        Requiere que el dispositivo esté en DFU (preferiblemente pwned DFU).
        Implica enviar iBSS, iBEC (si aplica) y luego el ramdisk, y finalmente bootearlo.
        """
        if not os.path.exists(ramdisk_path):
            self.logger.log("ERROR: Ruta de Ramdisk no válida o el archivo no existe.", "danger")
            return False
        
        if ibss_path and not os.path.exists(ibss_path):
            self.logger.log(f"ERROR: Ruta de iBSS no válida o el archivo '{ibss_path}' no existe.", "danger")
            return False
        
        if ibec_path and not os.path.exists(ibec_path):
            self.logger.log(f"ERROR: Ruta de iBEC no válida o el archivo '{ibec_path}' no existe.", "danger")
            return False

        self.logger.log(f"Iniciando secuencia de arranque del Ramdisk desde: {os.path.basename(ramdisk_path)}...", "info")
        
        if not self.detect_dfu_mode():
            self.logger.log("El dispositivo no está en modo DFU. No se puede arrancar el Ramdisk.", "danger")
            return False

        try:
            if ibss_path:
                self.logger.log(f"Enviando iBSS: {os.path.basename(ibss_path)}", "info")
                if not self.send_file_to_device(ibss_path):
                    self.logger.log("Fallo al enviar iBSS. Abortando arranque de Ramdisk.", "danger")
                    return False

            if ibec_path:
                self.logger.log(f"Enviando iBEC: {os.path.basename(ibec_path)}", "info")
                if not self.send_file_to_device(ibec_path):
                    self.logger.log("Fallo al enviar iBEC. Abortando arranque de Ramdisk.", "danger")
                    return False

            self.logger.log(f"Enviando Ramdisk: {os.path.basename(ramdisk_path)}", "info")
            if not self.send_file_to_device(ramdisk_path):
                self.logger.log("Fallo al enviar el Ramdisk. Abortando arranque.", "danger")
                return False

            self.logger.log("Enviando comando de arranque del Ramdisk...", "info")
            
            boot_command = ["irecovery", "-c", "bootx"]

            self.logger.log(f"Ejecutando comando de boot: {' '.join(boot_command)}", "info")
            result_boot = subprocess.run(boot_command, check=True, capture_output=True, text=True, timeout=60)
            self.logger.log(f"Comando de arranque enviado. Salida: {result_boot.stdout.strip()}", "debug")
            
            self.logger.log("Ramdisk arrancado con éxito.", "success")
            return True

        except FileNotFoundError:
            self.logger.log("ERROR: 'irecovery' no encontrado. Necesario para arrancar el ramdisk.", "danger")
            return False
        except subprocess.CalledProcessError as e:
            self.logger.log(f"ERROR al intentar arrancar el Ramdisk: {e.stderr.strip()}", "danger")
            self.logger.log("Asegúrate de que la secuencia de archivos y comandos de arranque sea correcta para tu dispositivo y el ramdisk.", "warning")
            return False
        except subprocess.TimeoutExpired:
            self.logger.log("El comando de arranque del Ramdisk excedió el tiempo de espera.", "warning")
            return False
        except Exception as e:
            self.logger.log(f"EXCEPCIÓN INESPERADA al arrancar Ramdisk: {e}", "error")
            return False