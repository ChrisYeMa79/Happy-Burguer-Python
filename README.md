# Happy Burger

Proyecto final del bootcamp de Programación con Python nivel avanzado de Tecmilenio.
Integra los cuatro avances mediante programación modular, orientación a objetos,
diccionarios, SQLite y una consulta web con Flask.

La **consola administrativa es la interfaz principal**: administra clientes, productos
y pedidos. La web permite únicamente consultar un pedido individual por su número.

## Estructura

```text
proyecto_final/
├── main.py                 # Consola administrativa
├── clientes.py             # Clase Cliente
├── menu.py                 # Clase Producto
├── pedidos.py              # Clase Pedido, tickets y consulta individual
├── base_datos.py           # Esquema, conexiones, validación y CRUD común
├── app.py                  # Aplicación Flask de consulta
├── templates/
│   └── consulta.html       # Formulario y resultado
├── static/
│   └── estilos.css         # Diseño responsivo, sin frameworks
├── test_proyecto.py         # 16 pruebas de consola, CRUD y pedidos
├── test_web.py              # 15 pruebas web
├── requirements.txt        # Flask y su versión
├── .gitignore              # Excluye entorno, base y tickets del control de versiones
├── happy_burger.db         # Base local existente; no se reinicia
├── tickets/                # Se crea al generar tickets
├── .venv/                  # Entorno local de Python
└── README.md
```

Los modelos mantienen sus campos en diccionarios y documentan clases y métodos con
docstrings. Cliente y Producto heredan las operaciones comunes de Registro.
Las rutas predeterminadas de la base y los tickets se resuelven desde los módulos.

## Requisitos e instalación

Python **3.9 o posterior**, con SQLite incluido. Flask es la única dependencia directa
externa; pip instala sus dependencias necesarias. HTML y CSS no usan librerías,
fuentes externas ni frameworks adicionales.

Desde la carpeta abierta en VS Code, en PowerShell:

```powershell
cd proyecto_final
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si el entorno ya existe, omite su creación. No es necesario activarlo ni modificar
la política de ejecución de PowerShell. Se validó con Python 3.14.5 y Flask 3.1.3.
Referencia: [instalación oficial de Flask](https://flask.palletsprojects.com/en/stable/installation/).

## Ejecutar la consola

Desde `proyecto_final`:

```powershell
.\.venv\Scripts\python.exe main.py
```

1. **Pedidos**: crear con claves existentes o cancelar por número.
2. **Clientes**: agregar, consultar, actualizar o eliminar.
3. **Menú**: agregar, consultar, actualizar o eliminar productos.
4. **Salir**: termina el programa.

Las opciones principales conservan su numeración original: 1 Pedidos, 2 Clientes,
3 Menú y 4 Salir. Cada submenú vuelve al principal después de operar; 0 permite volver.
En consultas de clientes/productos, una clave vacía lista todos los registros.
Al actualizar, dejar vacío un campo conserva su valor; la clave no se modifica.
Si todos los campos quedan vacíos, se muestra “Sin cambios. Se conservaron los datos
originales.” y se vuelve al menú sin ejecutar UPDATE.

La función independiente `solicitar_pedido()` del avance 1 se conserva y sigue probada.
El flujo actual de Pedidos usa el precio de SQLite y no solicita precios manuales.

## Iniciar la aplicación web

En otra terminal, desde `proyecto_final`:

```powershell
.\.venv\Scripts\python.exe app.py
```

Abre **http://127.0.0.1:5000/** y escribe el número del ticket.
Detén el servidor con Ctrl+C. La consola puede seguir abierta en su propia terminal.

El servidor escucha solo en 127.0.0.1, con depuración y recarga automática desactivadas.
Está destinado al desarrollo local. No se configura un despliegue público.
Referencia: [servidor local de Flask](https://flask.palletsprojects.com/en/stable/quickstart/).

La web reutiliza `Pedido.consultar()` y la misma base existente, abierta en modo SQLite
de **solo lectura**. No inicializa tablas, no inserta registros y no modifica el esquema.
Si falta la base o no puede consultarse, muestra un mensaje genérico; no crea otra base
ni revela rutas internas. En una instalación nueva, inicia primero la consola.

## Ejemplo de uso

Este ejemplo es orientativo: no se insertan datos de demostración en la base real.

1. Desde la consola registra el cliente `C1`, nombre Ana, con sus demás campos.
2. Registra el producto `P1`, Hamburguesa, precio `45.50`.
3. Crea el pedido `O1` para `C1` y `P1`, cantidad `3`.
4. La consola informa un total de `$136.50` y la ruta de un ticket de texto.
5. En la web consulta `O1`: verás número, nombre del cliente, producto, cantidad,
   precio unitario `$45.50`, importe total `$136.50` y estado `activo`.
6. Si lo cancelas desde la consola, la siguiente consulta mostrará `cancelado`.

Usa claves libres si estos identificadores ya existen. Los números de pedido se
conservan como **texto** por compatibilidad: `O1`, `123` y `002` son válidos,
y `002` es diferente de `2`. La creación y la consulta web comparten la función
`validar_clave_pedido()`: primero elimina espacios en blanco exteriores y después
exige de 1 a 128 caracteres imprimibles, sin controles internos. La creación guarda
la clave normalizada y la usa en el ticket; la consulta aplica la misma regla.
Una entrada que queda vacía, supera el límite o conserva controles muestra error
sin interrumpir la aplicación.
Una clave con formato válido pero inexistente muestra “No encontramos un pedido”.

## Persistencia y reglas

Las tablas `clientes`, `menu` y `pedido` conservan los campos del avance 2.
Pedido añade cantidad, importe y estado para registrar el cálculo y la cancelación.
Cliente y producto en pedido son claves foráneas; pedido es su identificador único.

Precios e importes se guardan como enteros en centavos y se presentan con Decimal.
Los precios admiten de 0 a 999999999.99, punto decimal y hasta dos decimales.
Las cantidades son enteros entre 1 y 1000000.
El argumento precio de Pedido se conserva por compatibilidad, pero al crear se
consulta siempre el precio del producto desde SQLite. Cambiarlo posteriormente
no modifica el precio ni el importe histórico del pedido.

Cancelar conserva el registro con estado cancelado. No se eliminan clientes o
productos referenciados, incluso por pedidos cancelados.
Los nombres mostrados se consultan de los catálogos actuales; precio e importe
proceden del pedido. El ticket conserva los datos del momento de emisión y no se
reescribe al cancelar.

Los valores SQL usan parámetros. Las operaciones administrativas permiten
únicamente los campos del modelo; las conexiones cierran al terminar.
Un fallo de escritura del ticket revierte la inserción del pedido; si falla el
commit después de escribir, se intenta eliminar el ticket. SQLite y el sistema de
archivos no tienen una transacción conjunta: un cierre abrupto puede dejar un
archivo huérfano. Los tickets usan UUID para evitar sobrescrituras y rutas provenientes
de entradas del usuario.

## Privacidad y errores web

La consulta devuelve un solo pedido mediante SQL parametrizado y no permite listar,
crear, actualizar, cancelar ni descargar archivos. No selecciona dirección, correo,
teléfono ni datos de otros clientes. Solo muestra el nombre del cliente asociado al
pedido solicitado, conforme al requisito. Los resultados no se almacenan en caché
y las plantillas escapan el HTML de las entradas y los datos guardados.

El formulario usa POST para no incluir el número en la URL. La aplicación limita
el tamaño del formulario y muestra mensajes comprensibles. Los estados HTTP son:
200 para inicio/resultado, 400 para entrada inválida, 404 para pedido inexistente,
413 para formulario excesivo y 503 para base no disponible.

No se implementa autenticación, según el alcance solicitado. Conocer un número
permite consultar ese pedido; esto no acredita la identidad de su propietario.
Por ello el uso previsto es exclusivamente local y no se añade acceso público.

## Ejecutar las pruebas

Desde `proyecto_final`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest -v
```

La suite contiene 16 pruebas en `test_proyecto.py` y 15 en `test_web.py`: 31 en total,
con unittest y el cliente de pruebas de Flask, sin pytest.
Cada prueba crea bases y tickets temporales dentro de `proyecto_final` y los retira
al terminar. Ninguna utiliza la base de uso real para generar datos de prueba.

Cobertura:
- Cálculo del avance 1 y reintentos de entradas inválidas.
- CRUD de clientes/productos y persistencia entre conexiones.
- Pedidos, precio histórico, cancelación, duplicados y claves foráneas.
- Tickets y reversión ante un fallo de escritura.
- Flujo administrativo de consola.
- Actualización sin cambios sin UPDATE, modificaciones válidas y validaciones.
- Validación compartida de claves: longitud, espacios exteriores, controles y duplicados.
- Inicio web, estilos, consulta existente e inexistente y validación.
- Presentación de campos, pedidos cancelados y precisión de importes grandes.
- Privacidad, escape HTML, consultas parametrizadas y límites de formulario.
- Ausencia de base sin creación accidental y manejo de errores.
- Integridad SQLite, claves foráneas y huella idéntica antes/después de consultas.

Resultado de la revisión: **31 pruebas aprobadas (16 de proyecto + 15 web)**.
El cliente Flask verifica las respuestas HTTP sin abrir un servidor.
La adaptación visual está implementada con CSS y media queries; queda pendiente
la comprobación visual manual en un navegador de escritorio y móvil.

## Revisión de los cuatro avances

| Avance | Requisitos cubiertos | Evidencia |
| --- | --- | --- |
| 1 | Carpeta, main.py, menú con condicionales/ciclo, cálculo de producto por cantidad | main.py y pruebas del cálculo/consola |
| 2 | Módulos independientes, clases, campos, diccionarios y docstrings | clientes.py, menu.py, pedidos.py; métodos ahora funcionales |
| 3 | SQLite, tablas, CRUD, pedidos, consulta de precio, cálculo y ticket | base_datos.py, modelos y 16 pruebas en test_proyecto.py |
| 4 | Flask, template para consulta por número y SQLite existente | app.py, consulta.html, estilos.css y 15 pruebas en test_web.py |

La revisión se basa en los requisitos académicos compartidos en esta conversación.
No se encontró un documento académico independiente en la carpeta: no se puede
afirmar una comparación literal con una rúbrica no proporcionada.
No se añaden interfaces administrativas web ni funcionalidades fuera del alcance.
