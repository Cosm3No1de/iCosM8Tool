# main.py
"""
Punto de entrada principal de la aplicación iCosM8 V3.8.
Inicializa la ventana de Tkinter y la interfaz gráfica de usuario.
"""
import tkinter as tk
from gui import iCosM8ToolGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = iCosM8ToolGUI(root)
    root.mainloop()