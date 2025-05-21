# auth.py
"""
Módulo para la gestión de autenticación y autorización en la aplicación iCosM8 V3.8.
Define la clase AuthManager, que simula el inicio de sesión, el registro y la
gestión de créditos del usuario.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Importar la clase Logger y COLORS desde el módulo de utilidades
from utils import Logger, COLORS

class AuthManager:
    """
    Gestiona la autenticación de usuarios y la gestión de créditos.
    Actualmente, esto es una simulación de un backend, sin persistencia real
    más allá de la sesión de la aplicación.
    """
    def __init__(self, logger: Logger, username_var: tk.StringVar, credits_var: tk.IntVar):
        """
        Inicializa el AuthManager.

        Args:
            logger (Logger): Instancia del logger para registrar eventos.
            username_var (tk.StringVar): Variable de Tkinter para el nombre de usuario.
            credits_var (tk.IntVar): Variable de Tkinter para los créditos del usuario.
        """
        self.logger = logger
        self.username_var = username_var
        self.credits_var = credits_var
        self.auth_status_label = None # Se inicializa a None, se setea desde GUI
        self.is_authenticated = False
        
        # Simulación de una base de datos de usuarios (en un entorno real, esto sería un backend o DB)
        self.users_db = {
            "testuser": {"password": "testpassword", "credits": 100, "email": "test@example.com", "instagram": "@testuser"},
            "admin": {"password": "admin", "credits": 9999, "email": "admin@example.com", "instagram": "@adminicosm8"},
        }
        self.current_user = None

    def set_auth_status_label(self, widget: ttk.Label):
        """
        Establece el widget Label de Tkinter para mostrar el estado de autenticación.
        Este método es llamado desde la GUI una vez que el widget es creado.
        """
        self.auth_status_label = widget
        self._update_auth_status_display() # Actualizar el display tan pronto como el widget esté disponible

    def _update_auth_status_display(self):
        """
        Actualiza el color y el texto de la etiqueta de estado de autenticación en la GUI.
        Se asegura de que el widget exista y la actualización se haga en el hilo principal.
        """
        if not self.auth_status_label:
            return # No hacer nada si el widget aún no ha sido asignado

        # Ejecutar la actualización en el hilo principal de Tkinter
        self.auth_status_label.after(0, lambda: self._apply_auth_status_style())

    def _apply_auth_status_style(self):
        """Aplica el estilo visual al label de estado de autenticación."""
        if self.is_authenticated:
            self.auth_status_label.config(text=f"Sesión iniciada como: {self.username_var.get()}", foreground=COLORS["secondary"])
        else:
            self.auth_status_label.config(text="Sesión no iniciada", foreground=COLORS["danger"])


    def login(self, username, password, callback=None):
        """
        Simula un intento de inicio de sesión.
        La operación se ejecuta en un hilo separado para no bloquear la GUI.

        Args:
            username (str): Nombre de usuario.
            password (str): Contraseña.
            callback (callable, optional): Función a llamar después del intento de inicio de sesión.
                                          Se le pasa un booleano (True si exitoso, False si falla).
        """
        self.logger.log(f"Intentando iniciar sesión como: {username}...", "info")
        threading.Thread(target=self._simulate_login_backend, args=(username, password, callback)).start()

    def _simulate_login_backend(self, username, password, callback):
        """Lógica simulada de backend para el inicio de sesión."""
        time.sleep(2) # Simular latencia de red

        success = False
        if username in self.users_db and self.users_db[username]["password"] == password:
            self.current_user = username
            self.username_var.set(username)
            self.credits_var.set(self.users_db[username]["credits"])
            self.is_authenticated = True
            self.logger.log(f"Inicio de sesión exitoso para {username}.", "success")
            messagebox.showinfo("Login", "Inicio de sesión exitoso!")
            success = True
        else:
            self.current_user = None
            self.username_var.set("Invitado")
            self.credits_var.set(0)
            self.is_authenticated = False
            self.logger.log(f"Fallo en el inicio de sesión para {username}.", "danger")
            messagebox.showerror("Login Error", "Usuario o contraseña incorrectos.")
            
        self._update_auth_status_display()
        if callback:
            # Ejecutar el callback en el hilo principal de Tkinter
            if self.auth_status_label:
                self.auth_status_label.after(0, lambda: callback(success))
            else:
                callback(success) # Fallback si el widget no está listo

    def register(self, username, email, instagram, password, callback=None):
        """
        Simula el registro de un nuevo usuario.
        La operación se ejecuta en un hilo separado para no bloquear la GUI.

        Args:
            username (str): Nombre de usuario.
            email (str): Correo electrónico.
            instagram (str): Cuenta de Instagram.
            password (str): Contraseña.
            callback (callable, optional): Función a llamar después del intento de registro.
                                          Se le pasa un booleano (True si exitoso, False si falla).
        """
        self.logger.log(f"Intentando registrar usuario: {username}...", "info")
        threading.Thread(target=self._simulate_register_backend, args=(username, email, instagram, password, callback)).start()

    def _simulate_register_backend(self, username, email, instagram, password, callback):
        """Lógica simulada de backend para el registro de usuario."""
        time.sleep(2) # Simular latencia de red

        success = False
        if username in self.users_db:
            self.logger.log(f"El nombre de usuario '{username}' ya existe.", "warning")
            messagebox.showwarning("Registro", "El nombre de usuario ya existe.")
        else:
            # Simular el registro exitoso
            self.users_db[username] = {
                "password": password,
                "credits": 0, # Nuevos usuarios empiezan con 0 créditos
                "email": email,
                "instagram": instagram
            }
            self.logger.log(f"Usuario '{username}' registrado con éxito.", "success")
            messagebox.showinfo("Registro Exitoso", "¡Registro completado! Ya puedes iniciar sesión.")
            success = True
        
        if callback:
            if self.auth_status_label:
                self.auth_status_label.after(0, lambda: callback(success))
            else:
                callback(success)

    def get_credits(self) -> int:
        """Devuelve los créditos del usuario actualmente autenticado."""
        if self.current_user:
            return self.users_db[self.current_user]["credits"]
        return 0

    def deduct_credits(self, amount: int) -> bool:
        """
        Simula la deducción de créditos del usuario actual.
        En un sistema real, esto implicaría una transacción de backend.

        Args:
            amount (int): Cantidad de créditos a deducir.

        Returns:
            bool: True si la deducción fue exitosa, False en caso contrario.
        """
        if not self.is_authenticated:
            self.logger.log("No hay usuario autenticado para deducir créditos.", "warning")
            messagebox.showerror("Error de Autenticación", "Debes iniciar sesión para realizar esta operación.")
            return False

        if self.users_db[self.current_user]["credits"] >= amount:
            self.users_db[self.current_user]["credits"] -= amount
            self.credits_var.set(self.users_db[self.current_user]["credits"])
            self.logger.log(f"Se dedujeron {amount} créditos. Créditos restantes: {self.credits_var.get()}", "info")
            return True
        else:
            self.logger.log(f"No hay suficientes créditos para la operación. Créditos actuales: {self.credits_var.get()}", "warning")
            messagebox.showerror("Créditos Insuficientes", "No tienes suficientes créditos para realizar esta operación.")
            return False