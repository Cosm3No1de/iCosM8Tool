# main.py
"""
Punto de entrada principal de la aplicación iCosM8 V3.8.
Inicializa la ventana de Tkinter y la interfaz gráfica de usuario,
incluyendo una pantalla de bienvenida mejorada.
"""
import tkinter as tk
from tkinter import ttk # Necesario para ttk.Label y ttk.Progressbar
import time # Necesario para time.sleep()

from gui import iCosM8ToolGUI

def show_splash_screen(root):
    """
    Muestra una pantalla de inicio mejorada con un mensaje de copyright
    y una barra de progreso.
    """
    splash_screen = tk.Toplevel(root)
    splash_screen.overrideredirect(True) # Elimina el borde de la ventana y los botones

    # Centrar la pantalla de inicio en la pantalla del usuario
    window_width = 450 # Un poco más ancha
    window_height = 250 # Un poco más alta
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    splash_screen.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Estilo y Colores Modernos
    # Puedes ajustar estos colores a tu gusto
    background_color = "#1a1a2e" # Azul oscuro muy profundo
    text_color = "#e0e0e0"     # Gris claro para buen contraste
    accent_color = "#0f4c75"   # Azul medio para acentos (o #e94560 para rojo)
    progressbar_trough_color = "#3a3a5f" # Color de fondo de la barra de progreso
    progressbar_fill_color = "#3282b8"   # Color de relleno de la barra de progreso

    splash_screen.config(bg=background_color)

    # Contenedor para el texto y la barra de progreso
    frame = tk.Frame(splash_screen, bg=background_color)
    frame.pack(expand=True, padx=20, pady=20)

    # Etiqueta para el mensaje de copyright
    # Usamos una fuente que suele estar disponible o una alternativa genérica
    # Puedes probar "Segoe UI", "Roboto", "Arial Rounded MT Bold" si están instaladas.
    try:
        # Intenta usar una fuente moderna
        title_font = ("Segoe UI", 24, "bold")
        subtitle_font = ("Segoe UI", 12)
        # Si la fuente no existe, Tkinter usará una predeterminada similar
    except Exception:
        title_font = ("Helvetica", 24, "bold")
        subtitle_font = ("Helvetica", 12)

    title_label = tk.Label(
        frame,
        text="iCosM8",
        font=title_font,
        fg=accent_color, # Un azul más brillante
        bg=background_color
    )
    title_label.pack(pady=(10, 0)) # Margen superior para separar del borde

    subtitle_label = tk.Label(
        frame,
        text="iOS Support Tool\nby Cosm3No1de.dev",
        font=subtitle_font,
        fg=text_color,
        bg=background_color
    )
    subtitle_label.pack(pady=(0, 20)) # Margen inferior para separar de la barra de progreso

    # Barra de Progreso (ttk.Progressbar)
    # Crear un estilo personalizado para la barra de progreso
    s = ttk.Style()
    s.theme_use('clam') # 'clam' o 'alt' suelen dar mejor control para personalización
    s.configure("splash.Horizontal.TProgressbar",
                background=progressbar_fill_color, # Color de la barra que avanza
                troughcolor=progressbar_trough_color, # Color de fondo de la barra
                bordercolor=background_color,
                lightcolor=progressbar_fill_color,
                darkcolor=progressbar_fill_color)

    progress_bar = ttk.Progressbar(
        frame,
        style="splash.Horizontal.TProgressbar",
        orient="horizontal",
        length=300, # Longitud de la barra
        mode="determinate" # Para que la barra avance de 0 a 100
    )
    progress_bar.pack(pady=10)

    # Animación de la barra de progreso
    duration = 3000 # Duración total en milisegundos (3 segundos)
    steps = 100     # Número de pasos de la barra de progreso
    delay = duration // steps # Retraso entre cada paso

    for i in range(steps + 1):
        progress_bar['value'] = i # Actualiza el valor de la barra (de 0 a 100)
        splash_screen.update_idletasks() # Procesa eventos pendientes (dibujar barra)
        splash_screen.update()           # Fuerza la actualización visual
        time.sleep(delay / 1000)         # Espera el tiempo de delay (en segundos)

    # Destruir la pantalla de inicio al finalizar
    splash_screen.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal temporalmente

    # Muestra la pantalla de inicio mejorada
    show_splash_screen(root)

    # Inicializa la aplicación principal de iCosM8
    # No es necesario un time.sleep() extra aquí porque show_splash_screen ya bloquea
    # y maneja su propio tiempo de espera y destrucción.
    app = iCosM8ToolGUI(root)

    # Una vez que la pantalla de inicio ha terminado, haz visible la ventana principal.
    root.deiconify()

    # Inicia el bucle principal de Tkinter
    root.mainloop()