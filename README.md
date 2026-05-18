# team CHAT 🚀

Un sistema de chat de escritorio e intercambio de archivos en red local (LAN) desarrollado en Python. Utiliza una arquitectura híbrida para garantizar fluidez en la comunicación y eficiencia en la transferencia de datos.

## ⚙️ Arquitectura del Proyecto
- **Mensajería en tiempo real:** Controlada mediante **Socket.IO** (Flask-SocketIO en el servidor y python-socketio en el cliente).
- **Transferencia de Archivos:** Implementada con **WebSockets** asíncronos para el envío y descarga de archivos en bloques (*chunks*) de 1 MB.
- **Interfaz Gráfica:** Diseñada en **Tkinter** con soporte de hilos (*multithreading*) para evitar bloqueos en la GUI.

---

## 📁 Estructura del Repositorio
```text
├── servidor.py          # Lógica del servidor (Flask + WebSockets)
├── cliente.py            # Cliente de chat (Interfaz Tkinter)
├── requirements.txt     # Dependencias del proyecto
└── README.md            # Documentación principal