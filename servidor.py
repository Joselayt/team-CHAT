from flask_socketio import SocketIO
from flask import Flask, request
import time
import websockets
import asyncio
from threading import Thread
from os import listdir, remove, makedirs
import datetime
from tkinter import messagebox
from sys import exit


"""
Esta documentacion ha sido generada por la AI (Gemini)
---

# Documentación Técnica: Servidor Central "team CHAT"

Este script implementa un servidor híbrido diseñado para coordinar una sala de chat grupal y un sistema de intercambio de archivos temporales. Centraliza la lógica de distribución de mensajes, control de presencia y transferencia de flujos binarios.

---

## 1. Arquitectura de Red del Servidor

El servidor expone dos interfaces de red simultáneas en la dirección local completa (`0.0.0.0`):

| Puerto | Protocolo / Framework | Rol Principal | Descripción |
| --- | --- | --- | --- |
| **`33214`** | Flask-SocketIO | **Mensajería y Presencia** | Gestor de conexiones de chat, envío de mensajes y actualización de la lista de usuarios activos. |
| **`12345`** | WebSockets (Puro Async) | **Servidor de Archivos** | Receptor y emisor de archivos binarios en bloques (*chunks*) con límite de tamaño. |

---

## 2. Variables de Estado Global

El servidor mantiene el estado de la sala y de los archivos mediante las siguientes variables:

* **`clientes` (list):** Almacena tuplas con la estructura `(nombre_usuario, request.sid)` para mapear la identidad de cada usuario con su identificador de sesión único de Socket.IO.
* **`tiempo` (dict):** Diccionario clave-valor que asocia el nombre de un archivo con su objeto `datetime` de expiración.
* **`tiempo_temporal` (datetime):** Establece el tiempo de vida de los archivos (calculado globalmente al iniciar el servidor como la hora actual + 5 minutos).
* **`carga` (bool / None):** Bandera de control para discernir si el flujo binario entrante por WebSockets corresponde a una subida (*upload*) o a una descarga (*download*).
* **`limite` (int):** Restricción de tamaño para WebSockets fijada en 5 MB ($5 \times 1024^2$ bytes).

---

## 3. Control de Eventos de Mensajería (Socket.IO)

### `@sock.event: datos(data)`

Este evento es el punto de entrada de un usuario tras conectarse. Recibe el nombre del cliente (`data`) y realiza dos acciones críticas:

1. **Registro:** Añade al usuario y su `sid` a la lista global de `clientes`.
2. **Bucle de Monitoreo (Background Worker):** Entra en un ciclo infinito (`while True:`) que se ejecuta cada 1 segundo. Este bucle:
* Revisa si el tiempo actual superó el tiempo de expiración de algún archivo en `tiempo`. Si es así, elimina el archivo físico de la carpeta `./archivos_temporales/` de forma permanente.
* Escanea la carpeta de archivos y calcula el tamaño actual de cada uno en Megabytes.
* Emite un evento masivo (`'lista'`) hacia los clientes con la nómina actualizada de usuarios en línea y la metadata de los archivos disponibles.



> ⚠️ **Nota de diseño:** Al contener un bucle `while True` bloqueante dentro del evento, este se adueña del hilo/contexto de ejecución para actuar como el despachador central de actualizaciones del servidor.

### `@sock.on('disconnect')`

Se activa automáticamente cuando un cliente cierra la aplicación o pierde conexión. Filtra la lista global `clientes` para remover permanentemente la tupla que coincida con el `request.sid` del usuario desconectado.

### `@sock.event: envio(data)`

Gestiona el enrutamiento de los mensajes de texto recibidos.

* Identifica el nombre del emisor buscando su `request.sid` en la lista de clientes.
* Itera sobre todos los usuarios conectados y reenvía el mensaje (`sock.emit('envio', ...)`) de forma selectiva (`to=c[1]`) a todos los participantes, **exceptuando** al emisor original.

---

## 4. Servidor de Archivos Asíncrono (WebSockets)

El servidor de archivos corre de forma independiente gracias a que se monta en un hilo secundario (`Thread`) configurado como demonio (`daemon=True`), evitando bloquear el servidor Flask.

```
[Cliente] --- Petición con '--b--' ---> [WebSocket Server] ---> Activa modo subida (carga=True)
[Cliente] --- Bloques Binarios --------> [WebSocket Server] ---> Escribe en ./archivos_temporales/

```

### `async def reception(ws)`

Es la función encargada de procesar el tráfico binario del WebSocket analizando "banderas" de texto insertadas en los flujos de datos:

* **Flujo de Subida (Upload):** Si el mensaje contiene la cadena `--b--`, el servidor extrae el nombre del archivo, programa su fecha de expiración en el diccionario `tiempo` y cambia la variable `carga = True`. Los siguientes paquetes de datos recibidos se escribirán (en modo *append* `ab`) directamente en el archivo local.
* **Flujo de Descarga (Download):** Si el mensaje contiene la cadena `--$--`, extrae el nombre del archivo solicitado, calcula su tamaño en disco y se lo envía al cliente. Posteriormente, abre el archivo local en modo lectura binaria (`rb`), lee el archivo en bloques de 1 MB y los transmite progresivamente. Al finalizar, envía la palabra clave `"FIN"` y cierra el canal.

---

## 5. Ciclo de Vida y Arranque

Al ejecutar el script desde la terminal, ocurren los siguientes pasos secuenciales:

1. **Lanzamiento del WebSocket:** Se invoca la función `archivos()`, la cual abre el socket en el puerto `12345` a la escucha de peticiones mediante `websockets.serve`. Esto se encapsula en un hilo dedicado.
2. **Lanzamiento de Flask:** `sock.run(app, host="0.0.0.0", port=33214)` toma el control del hilo principal, levantando el entorno web y quedando a la espera de las conexiones de los clientes del chat.



"""


app = Flask(__name__)
sock = SocketIO(app, cors_origin="*")
carga =  None
limite = 5* (1024**2)
tiempo_temporal = None
tiempo = {}
clientes = []

carpetas = ['archivos_temporales']
for f in carpetas:
    makedirs(f, exist_ok=True)

@sock.on('connect')
def connect():
    pass

@sock.event
def datos(data):
    
    global tiempo, tiempo_temporal
    borrar = None

    clientes.append((data, request.sid))
    while True:

        for clave, valor in tiempo.items():
            if datetime.datetime.now() >= valor:
                borrar = clave

        if borrar:
            remove(f'./archivos_temporales/{borrar}')
            tiempo.pop(borrar)
            print(borrar, "ha sido borrado por tiempo limitado")
            borrar = None

        archivos = listdir('./archivos_temporales/')
        ti = [c - datetime.datetime.now() for v, c in tiempo.items()]
        ti = [str(c).split('.')[0] for c in ti]
        ti = [(m, s) for c in ti for m, s in c.split(":")[1:]]


        try:
                
            sock.emit(
                'lista', 
                [
                    [c[0] for c in clientes], 
                    [
                        (c, f"{len(open(f'./archivos_temporales/{c}', 'rb').read())/1024**2:.2f} MB", str(tiempo[c]-datetime.datetime.now())) for c in archivos
                    ]
                ]
            )
            sock.sleep(1)
        except:
            messagebox.showerror(title="Error", message="Error de servidor, para corregirlo, se borraran todos los archivos de la carpeta 'archivos_temporales'")
            sock.sleep(1)
            for r in listdir('./archivos_temporales'):
                remove(f"./archivos_temporales/{r}")
                print(f"{r} borrado")
            continue

        tiempo_temporal = datetime.datetime.now() + datetime.timedelta(minutes=5)


@sock.on('disconnect')
def disconnect():
    global clientes
    print("cliente desconectado")
    print(request.sid)
    clientes = [c for c in clientes if c[1] != request.sid]

async def reception(ws):
    global carga, tiempo, tiempo_temporal

    while ws.state.value == 1:
        data = await ws.recv()
        if not data:
            await ws.close()

        if "--b--" in str(data):
            nombre = data.strip('--b--')
            tiempo[nombre]=tiempo_temporal
            carga = True
            continue

        if "--$--" in str(data):
            nombre = data.strip("--$--")
            carga = False
            tamaño = len(open(f"./archivos_temporales/{nombre}", "rb").read())
            await ws.send(str(tamaño))
            await asyncio.sleep(2)

            with open(f"./archivos_temporales/{nombre}", "rb") as t:
                while True:
                    content = t.read(1024 ** 2)
                    if not content:
                        await asyncio.sleep(1)
                        await ws.send('FIN')
                        await ws.close()
                        await asyncio.sleep(1)
                        break

                    await ws.send(content)
                    await asyncio.sleep(0.1)

        if carga:                
            with open(f"./archivos_temporales/{nombre}", "ab") as t:
                t.write(data)

    carga = None



async def handler(ws):
    await reception(ws)

async def archivos():
    async with websockets.serve(handler, '0.0.0.0', 12345, max_size=limite):
        await asyncio.Future()

Thread(target=lambda:asyncio.run(archivos()), daemon=True).start()

    
@sock.event
def envio(data):
    global clientes
    nombre = [c for c, v in clientes if v == request.sid][0]

    for c in clientes:
        if c[1] == request.sid:
            continue
        sock.emit('envio', {'nombre':nombre, 'sms':data}, to=c[1])

    


if __name__ == "__main__":
    sock.run(app, host="0.0.0.0", port=33214)