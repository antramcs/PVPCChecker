# PVPCChecker

## Inspector del coste de la energía en España.

### Introducción.

El complemento PVPCChecker para NVDA permite a los usuarios conocer en todo momento el coste real de la energía en España para el Precio Voluntario para el Pequeño Consumidor (PVPC) según el mercado regulado disponible en la web [tarifaluzhora.es](https://tarifaluzhora.es/).

Para más información acerca del PVPC y sobre sus características, puede consultarse el artículo de [Wikipedia sobre ello](https://es.wikipedia.org/?curid=2793315).


### Modo de uso.

Este complemento ofrece varias formas de consultar los precios de la electricidad:

#### Consulta rápida (resumen por voz).

Pulse **una vez** el gesto asignado para escuchar un resumen rápido del precio actual:
> "14h - 15h: 0,142 €/kWh [barato]. Media del día: 0,178 €/kWh"

La información también se envía a la línea Braille si hay una conectada.

#### Tabla completa de precios.

Pulse **dos veces** rápidamente el mismo gesto para abrir una ventana con la tabla completa de las 24 horas del día, incluyendo:

* Fecha actual de los precios consultados.
* Resumen del precio medio del día, hora más barata y hora más cara.
* Tabla completa con los precios de las 24 horas, indicando el tramo (barato, normal o caro) de cada hora.
* Marcador visual de la hora actual (configurable).
* Fuente de los datos.

#### Precios de mañana.

Use el gesto correspondiente para consultar los precios del día siguiente. Los precios de mañana suelen estar disponibles a partir de las 20:15h. Si no están publicados aún, se informará al usuario.

#### Consultar fecha concreta.

Use el gesto o el menú para abrir un diálogo de selección de fecha. Seleccione la fecha deseada y pulse Aceptar para ver los precios de ese día.

#### Copiar al portapapeles.

Use el gesto correspondiente para copiar la tabla de precios del día al portapapeles, para poder pegarla en un correo, documento u otra aplicación.

#### Menú de herramientas.

Todas las funciones también están disponibles desde el menú de NVDA: **NVDA → Herramientas → PVPCChecker**. Esto permite usar el complemento sin necesidad de recordar atajos de teclado.


### Atajos.

No existen combinaciones de teclas predefinidas actualmente en el complemento para que cada usuario pueda ajustarlo a sus preferencias personales de modo que no entren en conflicto con otros complementos instalados.

Para asignar atajos, acceda al menú NVDA → Preferencias → Gestos de entrada → PVPCChecker. Los gestos disponibles son:

* **Consulta del precio de la energía**: una pulsación = resumen rápido; doble pulsación = tabla completa.
* **Precios de mañana**: consulta los precios del día siguiente.
* **Consultar fecha concreta**: abre el diálogo de selección de fecha.
* **Copiar al portapapeles**: copia la información de precios.


### Configuración.

El complemento incluye un panel de preferencias accesible desde **NVDA → Preferencias → Opciones → PVPCChecker** con las siguientes opciones:

* **Anunciar el tramo de precio al cambio de hora**: Cuando está activado, al inicio de cada hora se anuncia automáticamente el nuevo precio y su tramo (barato, normal, caro). Desactivado por defecto.
* **Activar caché de datos**: Los precios del día no cambian una vez publicados. Con la caché activada, las consultas repetidas son instantáneas sin necesidad de descargar de nuevo. Activado por defecto.
* **Marcar la hora actual en la tabla de precios**: Añade un indicador visual (◄ ACTUAL) junto a la hora actual en la tabla completa. Activado por defecto.


### Requisitos.

* NVDA 2024.1 o superior.
* Conexión a Internet.


## Registro de cambios.

### Versión 3.0.

* **Consulta rápida por voz**: Una pulsación del gesto anuncia solo el precio de la hora actual sin abrir ventana.
* **Doble pulsación**: Dos pulsaciones rápidas muestran la tabla completa de precios.
* **Precios de mañana**: Nuevo gesto para consultar los precios del día siguiente (disponibles después de las 20:15h).
* **Consulta por fecha concreta**: Diálogo de selección de fecha para consultar precios de cualquier día.
* **Copiar al portapapeles**: Nuevo gesto para copiar la información de precios al portapapeles.
* **Menú en NVDA**: Todas las funciones accesibles desde el menú Herramientas de NVDA.
* **Panel de configuración**: Nuevo panel de preferencias para personalizar el comportamiento del complemento.
* **Caché de datos**: Las consultas repetidas son instantáneas gracias a la caché en memoria.
* **Reintentos automáticos**: El complemento reintenta la descarga en caso de fallos de red transitorios.
* **Soporte Braille**: La información del precio actual se envía también a la línea Braille.
* **Hora actual destacada**: La tabla de precios marca la hora actual para localizarla fácilmente.
* **Hora más barata y más cara**: Se muestra un resumen con los extremos del día.
* **Anuncio al cambio de hora**: Opcionalmente, se anuncia el nuevo precio al inicio de cada hora.
* **Arquitectura modular**: El código se ha reorganizado en módulos separados (fetcher, formatter, config_panel) para mejorar la mantenibilidad.

### Versión 2.0.

* Compatibilidad con NVDA 2026.1 (arquitectura de 64 bits y Python 3.13).
* La consulta de datos se realiza ahora en segundo plano para no bloquear NVDA durante la descarga.
* Adaptación completa al nuevo formato de datos de tarifaluzhora.es.
* Se indica el tramo de precio (barato, normal, caro) para cada hora.
* Se muestra el resumen del precio medio del día.
* Se ha eliminado el gesto predeterminado. El usuario debe asignarlo desde Gestos de entrada.
* Se eliminaron las dependencias empaquetadas (BeautifulSoup) que ya no son necesarias.
* Mejora del manejo de errores con mensajes claros al usuario.
* Soporte completo de internacionalización (i18n) con addonHandler.initTranslation().
* Versión mínima de NVDA requerida actualizada a 2024.1.

### Versión 1.0.

* Versión inicial del complemento.
