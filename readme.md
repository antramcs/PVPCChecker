# PVPCChecker

## Inspector del coste de la energía en España.

### Introducción.

El complemento PVPCChecker para NVDA permite a los usuarios conocer en todo momento el coste real de la energía en España para el Precio Voluntario para el Pequeño Consumidor (PVPC) según el mercado regulado disponible en la web [tarifaluzhora.es](https://tarifaluzhora.es/).

Para más información acerca del PVPC y sobre sus características, puede consultarse el artículo de [Wikipedia sobre ello](https://es.wikipedia.org/?curid=2793315).


### Modo de uso.

Este complemento es muy simple de utilizar. Bastará con definir la combinación de teclas necesaria para invocar el complemento desde el diálogo de Gestos de entrada de NVDA (categoría PVPCChecker), y una vez ejecutado, se mostrará la información en pantalla en una ventana sencilla.

La información incluye:

* Fecha actual de los precios consultados.
* Resumen del precio medio del día, hora más barata y hora más cara.
* Tabla completa con los precios de las 24 horas del día, indicando el tramo (barato, normal o caro) de cada hora.
* Fuente de los datos.


### Atajos.

No existen combinaciones de teclas predefinidas actualmente en el complemento para que cada usuario pueda ajustarlo a sus preferencias personales de modo que no entren en conflicto con otros complementos instalados.

Para asignar un atajo, acceda al menú NVDA → Preferencias → Gestos de entrada → PVPCChecker.


### Requisitos.

* NVDA 2024.1 o superior.
* Conexión a Internet.


## Registro de cambios.

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
