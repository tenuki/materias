# MATERIAS 

## URLs

### Principales

La pantalla principal tiene 2 formatos: vertical y horizontal:

`/h/<pabellon-es>` 
: pantalla _horizontal_ con las materias en los pabellones: `pabellon-es`.

`/v/<pabellon-es>`
: pantalla _vertical_ con las materias en los pabellones: `pabellon-es`.


Estas URLs soportan automaticamente el paginado de la información (lista de materias), de modo que en los horarios con 
mayor ocupación, la pantalla va "rotando" la información mostrada en la pantalla sucesivamente de acuerdo a los 
siguientes parámetros:

El primero es la cantidad de materias mostrada por página y el segundo el tiempo para el cambio de página. 

|                    |  vertical |  horizontal |
|:------------------:|----------:|------------:|
| lineas (MAX_LINES) |        20 |          10 |
| tiempo (WAIT_SECS) |       14s |          7s | 

En el servidor se estima cuantas lineas ocupa cada materia y se particiona el contenido en no más de MAX_LINES por 
pantalla, si hay más de una pantalla, se espera WAIT_SECS antes de mostrar la siguiente.


En estas URLs `pabellon-es` representa uno o varios pabellones a elección del usuario, siendo `0`, `1` y `2` los 
válidos al momento. Ejemplos:

 * `/h/0`: página horizontal con las materias del día actual del pabellón 0.
 * `/v/12`: página vertical con las materias del día actual de los pabellones 1 y 2.


Nota: el primer request (cualquiera sea que use datos de las materias) recibido en el día actualiza la información 
desde el spreadsheet indicado sincrónicamente lo cual hace que demore más que los sucesivos requests. Una vez descargada
la información desde dicho spreadsheet, dicha información será utilizada durante todo el día y no volverá a actualizarse
desde la fuente de datos nuevamente (hasta el día siguiente).  Se podría poner una url que fuerce la recarga de los 
datos "en el momento".

Las materias mostradas dependen de la hora de cada request. Se filtran todas las materias preservando aquellas
que comienzan antes _(ahora + 45min)_ y que terminan luego de _(ahora-10min)_. 
De esta forma podemos ver las materias que están por terminar y por empezar además de aquellas que están en transcurso.




### Extra

`/`   
: acceso a esta documentación.

`/json`
: json con todas las actividades de la semana.

`/json/<dia>`
: json con todas las actividades del día `dia`.

`/json/<dia>/<pabellon>`
: json con todas las actividades del día `dia` en el pabellón `pabellon`.

`/human`
: presenta al usuario links para que elija un pabellon o varios en particular.

`/human/<pabellon-es>`
: presenta al usuario los días disponibles para que elija cuales quiere ver.

`/human/<pabellon-es>/<dia>`
: muestra una versión primitiva de los datos de las materias correspondientes al/los pabellon/es correspondientes al día elegido.


### Testing

`/x/<pabellon-es>`
: pantalla _vertical_ con las materias en los pabellones: `pabellon-es` correspondientes al día `lunes` a las `14:00` hs.

`/y/<pabellon-es>` 
: pantalla _horizontal_ con las materias en los pabellones: `pabellon-es` correspondientes al día `lunes` a las `14:00` hs.

`/final/<day>/<pabellon-es>/<desde>`
: versión de `/v..` y `/h..` que recibe parámetros internos para definir `MAX_LINES` y `WAIT_SECS` y deja al usuario especificar la hora.



## Instalación

Requisitos: Python 3.6 o superior

1. Crear un entorno de Python: `python -m venv env`
2. Entrar al entorno: `. ./env/bin/activate` (en Windows: `env\scripts\activate`)
3. Instalar dependencias: `pip install -r requirements.txt`

### Ejecutar en entorno de desarrollo

0. (Entrar al entorno de Python como en el punto 2 anterior)
1. Configurar la aplicación Flask: `export FLASK_APP=server` (en Windows: `set FLASK_APP=server`)
2. Ejecutar Flask: `flask run`

### Ejecutar en entorno de producción

0. (Entrar al entorno de Python como en el punto 2 anterior)
1. `pip install waitress` (deberías poder usar la versión más reciente, no obstante, he usado exitosamente la `3.0.2`)
2. `waitress-serve --port=3001 --call server:get_app`

## Configuración

1. Configurar la hoja de cálculo a ser accedida en el archivo `server.py`, línea 21, en la variable llamada `SPREADSHEET`, así:<br/> `SPREADSHEET = "1pjtykzqGhaTkVfTNK7RsHHuu_u67hiA3jEsn0uMPLFY"`
2. Configurar la clave de usuario para acceder a las hojas de cálculo de Google: guardar las credenciales del usuario de Google en un archivo llamado `sacc-aulas-sa-private-key.json` en el mismo lugar donde se encuentra `server.py`. El archivo tendrá este formato:


<pre>
   {
     "type": "service_account",
     "project_id": "&ltsome-project&gt;",
     "private_key_id": "&lt40-chars hexa id&gt;",
     "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQ... MULTILINE PRIVATE KEY=\n-----END PRIVATE KEY-----\n",
     "client_email": "&ltsome-username&gt;@&ltproject_id&gt;.iam.gserviceaccount.com",
     "client_id": "&lt21 digits decimal-integer number&gt;",
     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
     "token_uri": "https://oauth2.googleapis.com/token",
     "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
     "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/&lt;user email&gt;%40&lt;pre&gt;.iamd.gserviceaccount.com",
     "universe_domain": "googleapis.com"
   }
</pre>

----
