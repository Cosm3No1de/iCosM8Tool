# operations.py
"""
Módulo que contiene la lógica de negocio para las operaciones de iOS en la
aplicación iCosM8 V3.8. Define la clase IOSOperations, que interactúa con
DeviceManager y AuthManager para realizar tareas como probar compatibilidad,
respaldar tokens, activar dispositivos, etc.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import os

# Importar las clases de los módulos de utilidades, dispositivo y autenticación
from utils import Logger, COLORS
from device import DeviceManager
from auth import AuthManager

class IOSOperations:
    """
    Clase que encapsula las operaciones de bajo nivel con iOS, interactuando
    con el DeviceManager y el AuthManager. Es el "cerebro" de la aplicación
    para las tareas específicas del dispositivo.
    """
    def __init__(self, logger: Logger, device_manager: DeviceManager, auth_manager: AuthManager):
        """
        Inicializa la clase IOSOperations.

        Args:
            logger (Logger): Instancia del logger para registrar eventos.
            device_manager (DeviceManager): Instancia del gestor de dispositivos.
            auth_manager (AuthManager): Instancia del gestor de autenticación.
        """
        self.logger = logger
        self.device_manager = device_manager
        self.auth_manager = auth_manager
        self.progress_bar = None # Inicialmente None, se setea desde GUI
        self.progress_percentage_label = None # Inicialmente None, se setea desde GUI

    def set_progress_widgets(self, progress_bar: ttk.Progressbar, progress_percentage_label: ttk.Label):
        """
        Establece los widgets de la barra de progreso y la etiqueta de porcentaje.
        Este método es llamado desde la GUI una vez que los widgets son creados.
        """
        self.progress_bar = progress_bar
        self.progress_percentage_label = progress_percentage_label

    def _update_progress(self, value: int, max_value: int, task_name: str):
        """
        Actualiza la barra de progreso y el porcentaje en la GUI.
        Se asegura de que los widgets existan y la actualización se haga en el hilo principal.
        """
        if self.progress_bar and self.progress_percentage_label:
            percentage = int((value / max_value) * 100)
            # Usar .after para asegurar que la actualización se ejecuta en el hilo principal
            self.progress_bar.after(0, lambda: self.progress_bar.config(value=value, maximum=max_value))
            self.progress_percentage_label.after(0, lambda: self.progress_percentage_label.config(text=f"{percentage}% - {task_name}"))
            self.progress_bar.after(0, self.progress_bar.update_idletasks) # Forzar actualización
            self.progress_percentage_label.after(0, self.progress_percentage_label.update_idletasks)

    def _reset_progress(self):
        """
        Reinicia la barra de progreso a 0%.
        Se asegura de que los widgets existan y la actualización se haga en el hilo principal.
        """
        if self.progress_bar and self.progress_percentage_label:
            self.progress_bar.after(0, lambda: self.progress_bar.config(value=0))
            self.progress_percentage_label.after(0, lambda: self.progress_percentage_label.config(text="0%"))
            self.progress_bar.after(0, self.progress_bar.update_idletasks)
            self.progress_percentage_label.after(0, self.progress_percentage_label.update_idletasks)

    def _simulate_process(self, task_name: str, duration: int):
        """
        Simula un proceso de larga duración con una barra de progreso.
        Esta función se ejecuta en un hilo separado por quien la llama.

        Args:
            task_name (str): Nombre de la tarea que se simula.
            duration (int): Duración en segundos de la simulación.
        """
        self.logger.log(f"Iniciando simulación de: {task_name}...", "info")
        self._update_progress(0, duration, task_name) # Inicia progreso en 0%

        for i in range(duration + 1):
            time.sleep(1) # Simula trabajo
            self._update_progress(i, duration, task_name)
        
        self.logger.log(f"Simulación de {task_name} completada.", "success")
        # Usar .after para mostrar el messagebox en el hilo principal de Tkinter
        if self.progress_bar: # Usar un widget existente para .after
            self.progress_bar.after(0, lambda: messagebox.showinfo(task_name, f"La operación '{task_name}' ha sido simulada exitosamente."))
        else: # Fallback si los widgets de progreso no están listos
            messagebox.showinfo(task_name, f"La operación '{task_name}' ha sido simulada exitosamente.")
        self._reset_progress() # Reinicia la barra al finalizar

    # --- Operaciones de la pestaña 'Activación en Hola' ---

    def probar_compatibilidad_hola(self, compatibilidad_resultado_var: tk.StringVar):
        """
        Inicia la simulación de la prueba de compatibilidad para activación en pantalla 'Hola'.
        La operación se ejecuta en un hilo separado.

        Args:
            compatibilidad_resultado_var (tk.StringVar): Variable de Tkinter para mostrar el resultado.
        """
        def _compat_thread():
            self.logger.log("Probando compatibilidad para activación en Hola...", "info")
            self._simulate_process("Prueba de Compatibilidad en Hola", 5)
            
            # Lógica de compatibilidad real iría aquí. Por ahora, un resultado simulado.
            time.sleep(1) # Pequeña pausa para que se vea el "Completada"
            result_text = "Compatible con bloqueo de actualizaciones."
            self.logger.log(f"Resultado de compatibilidad (simulado): {result_text}", "info")
            
            # Actualizar la variable de Tkinter en el hilo principal
            if self.progress_bar: # Usar un widget existente para .after
                self.progress_bar.after(0, lambda: compatibilidad_resultado_var.set(result_text))
            else:
                compatibilidad_resultado_var.set(result_text)

        threading.Thread(target=_compat_thread).start()

    # --- Operaciones de la pestaña 'Activación en Passcode' ---

    def iniciar_modo_boot_files(self, ios_version: str):
        """
        Inicia la simulación o ejecución del inicio en modo Boot Files.
        La operación se ejecuta en un hilo separado.

        Args:
            ios_version (str): La versión de iOS seleccionada (e.g., "ios14", "ios15").
        """
        if not ios_version:
            self.logger.log("ERROR: Por favor, selecciona una versión de iOS para Boot Files.", "danger")
            if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showerror("Error", "Por favor, selecciona una versión de iOS."))
            else: messagebox.showerror("Error", "Por favor, selecciona una versión de iOS.")
            return

        def _boot_thread():
            self.logger.log(f"Simulando inicio en Modo Boot Files para iOS {ios_version}...", "info")
            # Aquí iría la lógica real para poner en modo Boot Files (e.g., con irecovery)
            # Esto podría involucrar:
            # 1. Poner el dispositivo en DFU (quizás con ayuda del usuario o un exploit)
            # 2. Enviar los archivos de arranque (iBSS, iBEC)
            # 3. Enviar el Ramdisk adecuado para la versión de iOS
            # 4. Bootear el Ramdisk
            # self.device_manager.put_device_in_dfu() # Ejemplo, requiere implementación en DeviceManager
            # if self.device_manager.detect_dfu_mode():
            #     self.device_manager.send_file_to_device(f"path/to/iBSS_{ios_version}.img", "/tmp/iBSS")
            #     self.device_manager.send_file_to_device(f"path/to/iBEC_{ios_version}.img", "/tmp/iBEC")
            #     self.device_manager.boot_ramdisk(f"path/to/ramdisk_{ios_version}.dmg")
            self._simulate_process(f"Iniciar Modo Boot Files (iOS {ios_version})", 5)

        threading.Thread(target=_boot_thread).start()

    def respaldar_tokens(self):
        """
        Inicia la simulación o ejecución del respaldo de tokens.
        La operación se ejecuta en un hilo separado y requiere autenticación y créditos.
        """
        def _backup_thread():
            if not self.auth_manager.is_authenticated:
                self.logger.log("ERROR: Debes iniciar sesión para respaldar tokens.", "danger")
                if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación."))
                else: messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación.")
                return

            if not self.auth_manager.deduct_credits(5): # Simula el costo de 5 créditos
                return # Si no hay suficientes créditos, deduct_credits ya mostrará un mensaje

            self.logger.log("Simulando prueba de compatibilidad y respaldo de tokens...", "info")
            self._simulate_process("Respaldo de Tokens", 8)
            # Aquí iría la lógica real para respaldar tokens del dispositivo
            # Esto implicaría conectar al ramdisk, copiar archivos como 'Lockdown'
            if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showinfo("Respaldo de Tokens", "El proceso de respaldo de tokens ha sido simulado."))
            else: messagebox.showinfo("Respaldo de Tokens", "El proceso de respaldo de tokens ha sido simulado.")

        threading.Thread(target=_backup_thread).start()

    def activar_dispositivo_passcode(self):
        """
        Inicia la simulación o ejecución de la activación del dispositivo después del bypass del passcode.
        La operación se ejecuta en un hilo separado y requiere autenticación y créditos.
        """
        def _activate_thread():
            if not self.auth_manager.is_authenticated:
                self.logger.log("ERROR: Debes iniciar sesión para activar el dispositivo.", "danger")
                if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación."))
                else: messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación.")
                return

            if not self.auth_manager.deduct_credits(10): # Simula el costo de 10 créditos
                return

            self.logger.log("Simulando activación del dispositivo (Passcode)...", "info")
            self._simulate_process("Activar Dispositivo (Passcode)", 10)
            # Aquí iría la lógica real para activar el dispositivo, restaurando los tokens
            # y re-activando servicios, quizás omitiendo la configuración inicial.
            if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showinfo("Activar", "El proceso de activación (Passcode) ha sido simulado."))
            else: messagebox.showinfo("Activar", "El proceso de activación (Passcode) ha sido simulado.")

        threading.Thread(target=_activate_thread).start()

    # --- Operaciones de la pestaña 'FMI OFF' ---

    def intentar_fmi_off(self):
        """
        Inicia la simulación o ejecución del intento de desactivar FMI (Buscar Mi iPhone).
        La operación se ejecuta en un hilo separado y requiere autenticación y créditos.
        """
        def _fmi_off_thread():
            if not self.auth_manager.is_authenticated:
                self.logger.log("ERROR: Debes iniciar sesión para intentar FMI OFF.", "danger")
                if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación."))
                else: messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación.")
                return

            if not self.auth_manager.deduct_credits(20): # Simula el costo de 20 créditos
                return

            self.logger.log("Simulando intento de FMI OFF...", "info")
            self._simulate_process("FMI OFF", 15)
            # Lógica real para FMI OFF (a menudo basada en exploits o servicios externos)
            if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showinfo("FMI OFF", "El intento de FMI OFF ha sido simulado."))
            else: messagebox.showinfo("FMI OFF", "El intento de FMI OFF ha sido simulado.")

        threading.Thread(target=_fmi_off_thread).start()

    # --- Operaciones de la pestaña 'Toolbox' ---

    def jailbreak_automatico(self):
        """Simula un proceso de Jailbreak automático."""
        threading.Thread(target=self._simulate_process, args=("Jailbreak Automático", 20)).start()

    def ejecutar_checkra1n(self):
        """Simula la ejecución de Checkra1n."""
        # En un entorno real, esto ejecutaría el binario de checkra1n
        # checkra1n -c # para CLI o con argumentos específicos
        threading.Thread(target=self._simulate_process, args=("Ejecutar Checkra1n", 15)).start()

    def ejecutar_palera1n(self, rootful: bool):
        """
        Simula la ejecución de Palera1n.
        Args:
            rootful (bool): True para rootful, False para rootless.
        """
        mode = "Rootful" if rootful else "Rootless"
        # En un entorno real, esto ejecutaría el binario de palera1n
        # palera1n --rootful # o --rootless
        threading.Thread(target=self._simulate_process, args=(f"Ejecutar Palera1n {mode}", 18)).start()

    def restore_device(self):
        """Simula la restauración del dispositivo."""
        def _restore_thread():
            self.logger.log("Restaurando dispositivo (simulado)...", "warning")
            self._simulate_process("Restaurar Dispositivo", 30)
            # Lógica real para restaurar (e.g., `idevicerestore` o iTunes)
            if self.progress_bar: self.progress_bar.after(0, lambda: messagebox.showwarning("Restaurar Dispositivo", "El dispositivo ha sido restaurado a valores de fábrica (simulado)."))
            else: messagebox.showwarning("Restaurar Dispositivo", "El dispositivo ha sido restaurado a valores de fábrica (simulado).")

        threading.Thread(target=_restore_thread).start()

    def salir_modo_boot_files(self):
        """Simula la salida del modo Boot Files."""
        threading.Thread(target=self._simulate_process, args=("Salir de Modo Boot Files", 5)).start()

    def salir_modo_recovery(self):
        """Simula la salida del modo Recovery."""
        threading.Thread(target=self._simulate_process, args=("Salir de Modo Recovery", 5)).start()
        # self.device_manager.exit_recovery_mode() # Descomentar para usar el método real

    def salir_modo_dfu(self):
        """Simula la salida del modo DFU."""
        threading.Thread(target=self._simulate_process, args=("Salir de Modo DFU", 5)).start()
        # En la vida real, salir de DFU a menudo es un hard reset del dispositivo
        # o un comando específico si estás en DFU con una herramienta como `irecovery`.

    def salir_modo_purple(self):
        """Simula la salida del modo Purple."""
        threading.Thread(target=self._simulate_process, args=("Salir de Modo Purple", 5)).start()
        # El modo Purple (o modo de fábrica) es un estado de bajo nivel.
        # Salir de él a menudo implica flashear un firmware o usar herramientas especializadas.