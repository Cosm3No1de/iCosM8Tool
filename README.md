# iCosM8 V3.8 - Herramienta de Bypass y Utilidades iOS

![Captura de pantalla de iCosM8 V3.8](/assets/img.png)

## 🚀 Descripción

iCosM8 V3.8 es una potente herramienta gráfica (GUI) desarrollada en Python con Tkinter, diseñada para facilitar diversas operaciones de bypass y utilidades para dispositivos iOS. Ofrece soluciones para la activación de dispositivos en pantalla de Hola (Hello Screen), bypass de passcode, desactivación de FMI (Find My iPhone) y una caja de herramientas completa para jailbreak y modos de dispositivo.

La herramienta busca ser intuitiva y fácil de usar, proporcionando retroalimentación en tiempo real a través de un sistema de registro de logs y un indicador de estado de conexión del dispositivo.

## ✨ Características Principales

* **Interfaz Gráfica Intuitiva (GUI):** Desarrollada con Tkinter para una experiencia de usuario amigable.
* **Gestión de Dispositivos:**
    * Detección y visualización de información clave del dispositivo (Modelo, Serial, ECID, IMEI, Versión de iOS).
    * Indicador de estado de conexión del dispositivo.
* **Bypass de iCloud (Pantalla de Hola):**
    * Función para probar la compatibilidad del dispositivo.
    * Activación del dispositivo en pantalla de Hola con opciones para bloquear actualizaciones, restauraciones y omitir la configuración.
* **Bypass de iCloud (Modo Passcode):**
    * Proceso guiado de tres pasos:
        1.  Inicio en Modo Boot Files (compatible con iOS 14, 15, 16).
        2.  Prueba de compatibilidad y respaldo de tokens.
        3.  Activación final con opciones de bloqueo de actualizaciones/restauraciones y omisión de configuración.
* **FMI OFF (Find My iPhone Off):**
    * Funcionalidad para intentar desactivar "Buscar Mi iPhone" en dispositivos compatibles.
* **Toolbox de Utilidades:**
    * **Jailbreak y Exploit:** Opciones para Jailbreak Automático, Checkra1n y Palera1n (Rootful/Rootless).
    * **Utilidades:** Restaurar dispositivo.
    * **Modos de Salida:** Salir de Modo Boot Files, Recovery, DFU y Purple.
* **Sistema de Logs:** Ventana de logs dedicada para monitorear el progreso y cualquier error.
* **Gestión de Sesiones:** Sistema de inicio de sesión y registro de usuarios (simulado).
* **Temas:** Alterna entre tema oscuro y claro para personalizar la interfaz.
* **Configuración Persistente:** Guarda preferencias como el tema y la ruta del ramdisk.

## 🛠️ Instalación

Para usar iCosM8, sigue estos pasos:

1.  **Clona el repositorio:**
    ```bash
    git clone [https://github.com/tu_usuario/HerramientaM8.git](https://github.com/tu_usuario/HerramientaM8.git)
    cd HerramientaM8
    ```
    (Asegúrate de reemplazar `tu_usuario` si subes el repositorio a tu cuenta de GitHub).

2.  **Crea un entorno virtual (recomendado):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # En Linux/macOS
    # venv\Scripts\activate  # En Windows
    ```

3.  **Instala las dependencias necesarias:**
    ```bash
    pip install -r requirements.txt
    ```
    (Asegúrate de tener un archivo `requirements.txt` en tu proyecto que contenga `Pillow` y cualquier otra dependencia necesaria, como `pyusb`, `libimobiledevice-python` si usas implementaciones reales, etc.)
    Si no tienes un `requirements.txt`, al menos instala `Pillow`:
    ```bash
    pip install Pillow
    ```

4.  **Asegúrate de tener `libimobiledevice` y `usbmuxd` instalados en tu sistema operativo**, ya que son fundamentales para la comunicación con dispositivos iOS. Para sistemas basados en Debian (como Kali Linux):
    ```bash
    sudo apt update
    sudo apt install libimobiledevice-utils usbmuxd ideviceinstaller
    ```
    (Consulta la documentación para otros sistemas operativos).

## 🚀 Uso

1.  **Ejecuta la aplicación:**
    ```bash
    python3 main.py
    ```

2.  **Conecta tu dispositivo iOS:** Asegúrate de que tu dispositivo esté conectado y, si es necesario, confía en el ordenador.

3.  **Explora las pestañas:**
    * **Información del Dispositivo:** Verifica que tu dispositivo sea detectado y se muestre la información correcta.
    * **Activación en Hola:** Sigue los pasos para dispositivos en pantalla de activación.
    * **Activación en Passcode:** Utiliza los tres pasos para dispositivos con passcode habilitado.
    * **FMI OFF:** Intenta desactivar Find My iPhone.
    * **Toolbox:** Accede a utilidades como jailbreak y control de modos.
    * **Logs:** Abre la ventana de logs para ver el progreso de las operaciones.

## 🤝 Contribuyendo

¡Las contribuciones son bienvenidas! Si deseas mejorar iCosM8, por favor:

1.  Haz un "fork" de este repositorio.
2.  Crea una nueva rama (`git checkout -b feature/nueva-caracteristica`).
3.  Realiza tus cambios y confirma (`git commit -m 'feat: Añadir nueva característica'`).
4.  Empuja tu rama (`git push origin feature/nueva-caracteristica`).
5.  Abre un "Pull Request".

## 📄 Licencia

Este proyecto está bajo la licencia [Tu Tipo de Licencia, ej. MIT License]. Consulta el archivo `LICENSE` para más detalles.
