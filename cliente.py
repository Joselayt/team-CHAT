# importamos las librerias necesarias

import socketio
from tkinter import Tk, Label, Button, Entry, StringVar, END, messagebox, filedialog, Toplevel, BOTH, Menu
from tkinter import scrolledtext
from os import environ as e
from datetime import datetime
from plyer import notification
import websockets
from asyncio import sleep, Future, run
from threading import Thread, Event
from os import makedirs, path
from sys import exit
import sys
from json import load



# cargamos el icono en el entorno

def cargar_icono(ruta):

    if hasattr(sys, "_MEIPASS"):
        return path.join(sys._MEIPASS, ruta)

    return path.join(path.abspath("."), ruta)

icono= cargar_icono('icono.ico')

# creamos la carpeta de las descargas por si no existe
descargas_chat = "descargas_chat"
makedirs(descargas_chat, exist_ok=True)

#creamos el objeto socketio ya que utilizaremos dos protocolos principales
sock = socketio.Client()

# aqui almacenamos los demas usuarios conectados para saber quien está viendo nuestros mensajes
conectados = None

# este es un archivo que siempre debe existir para establecer conexion con el servidor
# guardamos las ips y los puertos correspondientes

if not path.exists('ips_port.json'):
    # si no existe nos sale un error y el programa se cierra
    messagebox.showerror(title="Error", message="Falta el archivo que contiene las direcciones de conexion. Busca un archivo llamado 'ips_port.json' y pegalo en este mismo directorio")
    exit()

# si existe cargamos y los almacenamos en las dos variables abajo vistas
d = load(open("ips_port.json", "r", encoding="utf-8"))

ip_ws = f"ws://{d['ws'][0]}:{d['ws'][1]}"
ip_sock = f"http://{d['sock_io'][0]}:{d['sock_io'][1]}"
limite = 5 * (1024 ** 2)


# el evento que se ejecuta cuando nos conectamos al servidor
# para nuestro usuario usaremos el nombre de usuario predeterminado de nuestro equipo
# es el nombre que le mandamos al servidor para que nos registre
@sock.event
def connect():
    nombre = e.get('USERNAME')
    sock.emit('datos', nombre)

# el evento que se ejecuta cuando nos desconectamos
@sock.event
def disconnect():
    pass

# ya que en la interface vemos en tiempo real los otros usuarios, aqui recibimos la actualizacion del servidor con las lista de usuarios activos
@sock.event
def lista(lista):
    global conectados
    conectados = lista


# el evento que se activa cuando recibimos un nuevo mensaje
@sock.event
def envio(data):

    notification.notify(data['nombre'], data['sms'], timeout=4, app_name="team CHAT", app_icon=icono)
    mensajes.config(state="normal")
    mensajes.insert(END, f"👨‍🦰 {data['nombre'].capitalize()}: {data['sms'].capitalize()}\n", "izquierda")
    mensajes.insert(END, f"{datetime.now().strftime('%H:%M:%S')}\n\n", "centro_l")
    mensajes.see(END)
    mensajes.config(state="disable")

# creamos nuestra conexion con el servidor con la ip y el puerto ariba cargados
sock.connect(ip_sock)


# creamos el objeto de nuestra interface
root = Tk()
root.iconbitmap(icono)
root.geometry('1000x500') #creamos una dimension predeterminada
root.title('team CHAT') # creamos el titulo de la ventana
root.configure(background="gainsboro") #establecemos el fondo de la ventana


#menu
# la documentacion que aparece en nuestra interface
doc_ = """
Esta documentación fue creada con AI 'Gemini'

---

# Documentación Técnica: Aplicación Cliente "team CHAT"

**team CHAT** es una aplicación de escritorio para mensajería en tiempo real e intercambio de archivos. Combina una interfaz gráfica de usuario (GUI) con una arquitectura de red híbrida que utiliza dos protocolos simultáneos para optimizar el rendimiento.

---

## 1. Arquitectura del Sistema

La aplicación utiliza un enfoque híbrido para separar las responsabilidades de red y mantener la interfaz fluida:

* **Socket.IO (Control y Texto):** Se encarga de la mensajería instantánea de texto, la gestión de presencia (usuarios conectados) y las notificaciones de estado.
* **WebSockets Puros (Datos Async):** Se dedica exclusivamente a la transferencia de archivos pesados de forma asíncrona mediante bloques (*chunks*).
* **Multithreading (Hilos):** Evita que la interfaz de usuario de Tkinter se congele (*freezing*) al delegar las operaciones de red de WebSockets a hilos secundarios (`threading.Thread`).

---

## 2. Configuración y Variables Globales

Al arrancar el script, se configuran las carpetas del sistema y las direcciones de los servidores:

| Variable | Tipo | Descripción |
| --- | --- | --- |
| `descargas_chat` | `str` | Nombre de la carpeta local (`./descargas_chat`) donde se guardan las descargas. Se crea automáticamente si no existe. |
| `ip_sock` | `str` | URL del servidor Socket.IO (Puerto `33214`) para el chat de texto. |
| `ip_ws` | `str` | URL del servidor WebSocket (Puerto `12345`) para la transferencia de archivos. |
| `limite` | `int` | Tamaño máximo de archivo permitido para el WebSocket corporativo: 5 MB ($5 \times 1024^2$). |
| `sock` | `Client` | Instancia del cliente Socket.IO. |
| `conectados` | `list` / `None` | Estructura de datos global actualizada por el servidor con `[lista_usuarios, lista_archivos]`. |

---

## 3. Manejo de Eventos (Socket.IO)

Estos métodos decorados reaccionan de manera asíncrona a los eventos emitidos por el servidor de chat:

### `@sock.event: connect()`

Se ejecuta automáticamente al establecer conexión. Obtiene el nombre de usuario de la sesión actual del sistema operativo (`os.environ['USERNAME']`) y lo envía al servidor mediante el evento `'datos'`.

### `@sock.event: lista(lista)`

Recibe del servidor una lista actualizada de usuarios activos y archivos del servidor, almacenándola en la variable global `conectados`.

### `@sock.event: envio(data)`

Se dispara al recibir un mensaje de texto de otro usuario.

* Muestra una notificación nativa en el sistema operativo mediante `plyer.notification`.
* Desbloquea temporalmente el componente de texto (`mensajes`), inserta el mensaje alineado a la **izquierda** con formato de hora actual y vuelve a bloquearlo para evitar manipulación del usuario.

---

## 4. Módulo de Transferencia de Archivos (WebSockets & Asyncio)

Para transferir datos de forma eficiente sin interrumpir el chat principal, se implementan flujos binarios asíncronos.

### Subida de Archivos (`send_files` y `adj_b`)

1. **`adj_b()`:** Abre un cuadro de diálogo nativo (`filedialog.askopenfilenames`) para seleccionar múltiples archivos de cualquier extensión. Si se eligen archivos, inicia la corrutina `send_files` dentro de un hilo secundario de tipo *daemon*.
2. **`send_files(ar)`:** Deshabilita el botón de adjuntar para evitar spam. Conecta al WebSocket y, para cada archivo, envía un prefijo de control (`--b--{nombre}--b--`). Posteriormente, lee el archivo en bloques binarios de 1 MB y los transmite secuencialmente mientras actualiza el progreso en la interfaz gráfica.

### Descarga de Archivos (`ventana` y `bajar`)

1. **`ventana()`:** Despliega una ventana secundaria (`Toplevel`) que renderiza de forma dinámica botones por cada archivo disponible en el servidor. Cuenta con un efecto visual dinámico (*typing effect*) en su título gracias a la función recursiva `natural()`.
2. **`bajar(t)`:** Al pulsar el botón de un archivo, se crea un hilo que ejecuta esta función. Envía una petición con el prefijo de control (`--$--{nombre}--$--`), recibe el tamaño total del archivo para calcular el porcentaje, y descarga bloques binarios guardándolos en `./descargas_chat` hasta recibir la señal `"FIN"`.

---

## 5. Componentes de la Interfaz Gráfica (Tkinter)

### Gestión de Estilos

El código centraliza la estética visual utilizando diccionarios de configuración (`titulo`, `en_linea`, `entra`, etc.) que unifican fuentes (`Cambria`, `Arial`), colores (`gainsboro`, `deep sky blue`) y bordes de los widgets.

### El Bucle de Presencia (`usu_conect`)

Esta función gestiona de forma periódica el panel izquierdo de usuarios conectados mediante un ciclo de tiempo:

* Se ejecuta automáticamente cada 5 segundos usando `root.after(5000, usu_conect)`.
* **Nota de diseño:** Para "limpiar" los nombres de usuarios anteriores y evitar que el texto se encime, la función redibuja astutamente las etiquetas utilizando el estilo `en_linea_`, cuyo color coincide con el fondo (`gainsboro`), actuando como un borrador visual antes de pintar el nuevo estado.

### Envío de Mensajes Locales (`enviar_sms`)

Toma el texto del campo de entrada, valida que no esté vacío y emite el evento `'envio'` a través de Socket.IO. Renderiza el mensaje de manera inmediata en el lado **derecho** de la pantalla del usuario local y limpia la caja de texto.

---

## 6. Atajos de Teclado y Ejecución

* **Tecla Enter (`<Return>`):** Está enlazada (`root.bind`) globalmente a la ventana principal. Presionar Enter invoca automáticamente a `enviar_sms()`, agilizando la experiencia de chat.
* **`root.mainloop()`:** Inicia el ciclo de vida principal de la aplicación, procesando los clics, las actualizaciones asíncronas de la interfaz y manteniendo la ventana activa.
"""

# la ventana emergente que se activa cuando pulsamos el boton de Documentacion
def sms_doc():
    root_doc = Toplevel()
    root_doc.transient(root)
    root_doc.resizable(False, False)

    # una funcion que imprime la doc con efecto de maquina de escribir, token por token
    def natural_scroll(texto, widget, i=0):
        if len(texto) > i:
            widget.config(state="normal")
            widget.insert(END, texto[i])
            widget.config(state="disable")

            root_doc.after(1, natural_scroll, texto, widget, i+1)
    
    s = scroll_doc = scrolledtext.ScrolledText(root_doc)
    s.pack()
    natural_scroll(doc_, s)


# creamos el menu superior (Documentacion)
menu = Menu(root)
root.configure(menu=menu)
menu.add_command(label="Documentación", command=lambda: sms_doc())


intro = StringVar()
mi_barra = StringVar()
files_ = StringVar()

#funciones



# conectamos al servidor con el protocolo para envios de datos pesados
async def send_files(ar=None):

    
    adj.config(state="disable") #desactivamos temporalmente el boton para evitar spam
    total = 0
    async with websockets.connect(ip_ws, max_size=limite) as ws:
        for r in ar:
            nombre = r.split('/')[-1]
            await ws.send(f'--b--{nombre}--b--') #creamos un header para enviar el nombre del archivo
            with open(r, "rb") as j: #abrimos el archivo en binario
                while True:
                    datos = j.read(1024 ** 2) #leemos los datos por chuck
                    if not datos:
                        break

                    await ws.send(datos)
                    total += len(datos)
                    total_ = total / 1024 **2 #calculamos los datos en MB
                    mi_barra.set(f"Enviando: {nombre} --> {total_:.5} MB") #mostramos el proceso en pantalla para el usuario


            total = 0 #por cada archivo inicializamos el dato que calcula el total
    adj.config(state="normal")
    await ws.close()
    mi_barra.set('') #vaciamos la barra de carga

#funcion cuando queremos cargar un archivo
def adj_b():

    #mostramos el admin de archivos para elegir uno o multiples archivos y enviar
    ar = filedialog.askopenfilenames(title='elgir', filetypes=(('archivos de video', '.mp4'), ('musica', '.mp3'), ('documentos word', '.docx'), ('PDFs', '.pdf'), ('todos los archivos', '*.*')))
    if ar:
        t = Thread(target=lambda:run(send_files(ar)), daemon=True) #para no bloquear la UI creamos un hilo por instruccion
        t.start()

# para ver los archivos disponibles para descargar
# creamos una ventana flotante
def ventana():
    global des
    root_des = Toplevel()
    root_des.configure(background="deep sky blue")
    root_des.transient(root)
    root_des.grab_set()

    if len(des) ==0:
        root_des.destroy()
    infor = StringVar()

    tit = Label(root_des, text="", font=('arial', 18), fg="black", bg="deep sky blue", relief="flat")
    tit.pack(fill=BOTH)
    
    def natural(texto, widget, i=0):
        if len(texto) > i:
            widget.config(text=tit.cget('text') + texto[i])
            root_des.after(10, natural, texto, widget, i+1)


    
    # mostramos las indicaciones con un efecto de maquina de escribir
    natural("Descargas disponibles... pulsa y comienza a descargar\n\n", tit)

    # para descaargar un archivo
    def llamada(t):

        Thread(target=lambda:run(bajar(t)), daemon=True).start()

    # al pulsar descargar, se ejecuta esta funcion
    async def bajar(t):

        #establecemos conexion con el servidor con el protocolo ws
        async with websockets.connect(ip_ws, max_size=limite) as ws:
            await ws.send(f'--$--{t}--$--') #enviamos el nombre del archivo que vamos a descargar
            await sleep(1)
            tamaño = await ws.recv() # recibimos el tamaño para calcular el proceso de descarga
            await sleep(2)
            process = 0

            # escribimos los bytes en la carpeta de descarga en un archivo
            with open(f"./descargas_chat/{t}", "wb") as t:
                while True:
                    datos = await ws.recv()
                    if datos == "FIN": # la señal de FIN es para indicar al cliente que la descarga finalizó
                        break
                    t.write(datos)
                    process += len(datos)
                    infor.set(f"descargando {process * 100 / int(tamaño):.2f} %") #mostramos los resultados de la descarga en pantalla

            t.close() # cerramos el archivo binario
        await ws.close() #cerramos el protocolo de envio
    
    # kwargs de caracteristicas de los widget
    carac = {
        "bg":"deep sky blue",
        "fg":"black",
        "font":('cambria', 11),
        "relief":"flat"
    }

    

    #creamos de manera dimanica los archivos disponibles para la descarga
    if len(des) >0:
        for r in des:
            Button(root_des, text=f"Descargar --> {r[0]}. Tamaño: {r[1]}. Tiempo restante: {r[2]}", command=lambda r=r[0]:llamada(r), **carac).pack(fill=BOTH)

    
    Label(root_des, textvariable=infor, **carac).pack() #la barra de descarga

# para enviar un mensaje de texto
def enviar_sms():

    content = intro.get() #extraemos los datos de nuestra entrada de mensajeria
    if content.strip() != "": #verificamos que no esta vacia
        sock.emit('envio', content)
        mensajes.config(state="normal")
        mensajes.insert(END, f"{content}: 👨‍🦲\n", "derecha") #lo mostramos en pantalla
        mensajes.insert(END, f"{datetime.now().strftime('%H:%M:%S')}\n\n", "centro_r") #con la hora exacta que se envio, coicide con la hora del computador

        mensajes.see(END)
        mensajes.config(state="disable")
        intro.set('') #vaciamos la entrada de texto
        

# kwargs de caracteristicas de los widget

titulo = {
    "font":('cambria', 30),
    "bg":"gainsboro",
    "fg":'black'
}


en_linea = {
    "font":('cambria', 14, 'bold'),
    "bg":"deep sky blue",
    "fg":'black',
    "relief":"flat",
    "width":12,
    "padx":2,
    "pady":2,
}


en_linea_ = {
    "font":('cambria', 14, 'bold'),
    "bg":"gainsboro",
    "fg":'gainsboro',
    "relief":"flat",
    "width":12,
    "padx":2,
    "pady":2,
}

en_linea_num = {
    "font":('arial', 14),
    "bg":"gainsboro",
    "fg":'maroon',
    "relief":"flat",
}
entrantes = {
    "foreground":"black",
    "font":("arial", 18),
}

boton = {
    "fg":"gainsboro",
    "bg":"deep sky blue",
    "relief":"groove",
    "font":("cambria", 14, "bold"),
    "pady":5,
    "padx":5,
    "width":9,
    "command":lambda:enviar_sms()
}

boton_la = {
    "fg":"deep sky blue",
    "bg":"gainsboro",
    "relief":"groove",
    "font":("cambria", 14, "bold"),
    "pady":5,
    "padx":5,
    "width":2,
    "height":2,
    "command":lambda:adj_b()
}

entra = {
    "fg":"black",
    "bg":"white",
    "relief":"flat",
    "font":("cambria", 25, "bold"),
    "width":33
}


entra_ = {
    "fg":"black",
    "bg":"gainsboro",
    "relief":"flat",
    "font":("cambria", 14),
    "underline":True
}


files = {
    "fg":"black",
    "bg":"deep sky blue",
    "relief":"groove",
    "font":("arial", 12),
    "command":lambda:ventana()
}

#titulo de nuestra ventana
Label(root, text="team CHAT", **titulo).pack()

#usuarios conectados
def usu_conect():

    #la funcion que se actualiza cada 5 segundos para mostrarnos los usuarios activos y archivos disponibles a descargar
    global conectados, des
    des = conectados[1]

    num = 0
    Label(root, text=f"Usuarios conectados: {len(conectados[0])}", **en_linea_num).place(x=20, y=10)
    if conectados[0]:
        for c in conectados[0]:
            Label(root, text=f"✔ {c.split()[0].capitalize()}", **en_linea).place(x=20, y=60 + num)
            num += 50
    
    files_.set(f'Archivos disponibles para descargar: {len(conectados[1])}')

    root.after(5000, usu_conect)
    for c in conectados[0]:
        Label(root, text=f"✔ {c.split()[0].capitalize()}", **en_linea_).place(x=20, y=60 + num)
        num += 50

root.after(5000, usu_conect)

# nuestra espacio donde se almacenan los mensajes de todo el chat, se limpia cuando cerramos el programa
mensajes = scrolledtext.ScrolledText(root, width=90, height=20, state="disable")
mensajes.place(x=180, y=50)
mensajes.tag_configure('derecha', justify="right", foreground="black", font=("arial", 18, "bold"))
mensajes.tag_configure('izquierda', justify="left", **entrantes)
mensajes.tag_configure('centro_l', justify="left", font=('cambria', 9), foreground="black")
mensajes.tag_configure('centro_r', justify="right", font=('cambria', 9), foreground="black")

#botones
#boton de enviar
enviar = Button(root, text="Enviar", **boton)
enviar.place(x=850, y=380)
def enter(event):
    enviar_sms()
root.bind('<Return>', enter) #creamos un evento para enviar solo con el boton de INTRO


adj = Button(root, text="➕", **boton_la) #boton de adjuntar
adj.place(x=920, y=50)

#entrada

entrada = Entry(root, textvariable=intro, **entra) #nuestra entra de mensajes
entrada.place(x=180, y=380)


barra_ = Label(root, textvariable=mi_barra, **entra_) #la barra de carga de los archivos
barra_.place(x=180, y=460)


barra = Button(root, textvariable=files_, **files) # el boton que muestra si hay archivos disponibles para descargar
barra.place(x=180, y=430)


root.mainloop() #el bucle que mantiene la ventana activa y actualizada