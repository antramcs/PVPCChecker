# -*- coding: UTF-8 -*-
# PVPCChecker: Módulo de descarga y extracción de datos de precios PVPC.
# Copyright (C) Antonio Cascales <antonio.cascales@gmail.com>
# Licencia: GPL v2

"""Descarga, parsing y caché de datos de precios de tarifaluzhora.es."""

import json
import logging
import re
import time
from datetime import datetime, date
from urllib import request, error
from collections import OrderedDict

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_URL_BASE = "https://tarifaluzhora.es"
_URL_TODAY = _URL_BASE + "/"
_URL_TOMORROW = _URL_BASE + "/info/precio-kwh-manana"
_USER_AGENT = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
	"AppleWebKit/537.36 (KHTML, like Gecko) "
	"Chrome/120.0.0.0 Safari/537.36"
)
_TIMEOUT = 30
_MAX_RETRIES = 2
_BACKOFF_BASE = 1.0
_CACHE_MAX_ENTRIES = 7

# ---------------------------------------------------------------------------
# Caché en memoria
# ---------------------------------------------------------------------------
# Clave: cadena con formato "YYYY-MM-DD" o "tomorrow".
# Valor: dict con "data" (datos extraídos), "html" (HTML crudo), "ts" (timestamp).
_cache: OrderedDict = OrderedDict()


def invalidate_cache():
	"""Limpia toda la caché de datos."""
	_cache.clear()


def _is_cache_valid(key):
	"""Comprueba si una entrada de caché sigue siendo válida.

	Para el día actual, la caché es válida hasta medianoche.
	Para "tomorrow", es válida 30 minutos (los datos pueden actualizarse).
	Para días pasados, es válida indefinidamente.
	"""
	if key not in _cache:
		return False
	entry = _cache[key]
	now = datetime.now()
	today_str = now.strftime("%Y-%m-%d")
	if key == "tomorrow":
		# Los datos de mañana pueden cambiar; caché de 30 min.
		return (time.time() - entry["ts"]) < 1800
	if key == today_str:
		# Válida hasta medianoche.
		midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
		# Si la entrada se creó hoy, es válida.
		entry_date = datetime.fromtimestamp(entry["ts"]).date()
		return entry_date == now.date()
	# Días pasados: siempre válida.
	return True


def _put_cache(key, data, html):
	"""Almacena una entrada en la caché, respetando el límite de tamaño."""
	_cache[key] = {"data": data, "html": html, "ts": time.time()}
	# Mantener el tamaño máximo.
	while len(_cache) > _CACHE_MAX_ENTRIES:
		_cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Descarga con reintentos
# ---------------------------------------------------------------------------
def _fetch_url(url, retries=_MAX_RETRIES, backoff=_BACKOFF_BASE):
	"""Descarga el contenido de una URL con reintentos y backoff exponencial.

	Args:
		url: URL a descargar.
		retries: Número máximo de reintentos.
		backoff: Tiempo base de espera entre reintentos (segundos).

	Returns:
		Cadena con el HTML descargado.

	Raises:
		error.URLError: Si todos los reintentos fallan.
	"""
	last_exc = None
	for attempt in range(retries + 1):
		try:
			req = request.Request(
				url,
				data=None,
				headers={"User-Agent": _USER_AGENT},
			)
			with request.urlopen(req, timeout=_TIMEOUT) as response:
				return response.read().decode("utf-8")
		except error.URLError as exc:
			last_exc = exc
			if attempt < retries:
				wait = backoff * (2 ** attempt)
				log.warning(
					"Intento %d/%d fallido para %s: %s. Reintentando en %.1fs...",
					attempt + 1, retries + 1, url, exc, wait,
				)
				time.sleep(wait)
			else:
				log.error(
					"Todos los intentos fallidos para %s: %s", url, exc,
				)
	raise last_exc


# ---------------------------------------------------------------------------
# Extracción de datos del HTML
# ---------------------------------------------------------------------------
def _extract_price_data(html):
	"""Extrae los datos de precios del JSON embebido en el HTML de tarifaluzhora.es.

	La web utiliza componentes Alpine.js que contienen los datos de precios
	como JSON serializado dentro de llamadas a ``tlhNowHour(JSON.parse(...))``.

	Args:
		html: Cadena con el contenido HTML completo de la página.

	Returns:
		Diccionario con las claves ``prices``, ``colors`` y opcionalmente ``raw``.

	Raises:
		ValueError: Si no se encuentran los datos de precios en el HTML.
	"""
	pattern = r"tlhNowHour\(JSON\.parse\('(.+?)'\)\)"
	match = re.search(pattern, html)
	if not match:
		raise ValueError(
			"No se encontraron datos de precios en la página. "
			"Es posible que la estructura de la web haya cambiado."
		)
	raw_json = match.group(1).replace("\\u0022", '"')
	try:
		data = json.loads(raw_json)
	except json.JSONDecodeError as exc:
		raise ValueError(
			"Error al interpretar los datos de precios: %s" % exc
		) from exc
	if "prices" not in data:
		raise ValueError(
			"Los datos de precios no tienen el formato esperado."
		)
	return data


def _extract_summary(html):
	"""Extrae el resumen textual del precio medio del día.

	Args:
		html: Cadena con el contenido HTML completo de la página.

	Returns:
		Cadena con el resumen o ``None`` si no se encuentra.
	"""
	match = re.search(r"El precio medio de la luz[^<]+", html)
	return match.group(0).strip() if match else None


def _extract_date_heading(html):
	"""Extrae el encabezado con la fecha del día.

	Args:
		html: Cadena con el contenido HTML completo de la página.

	Returns:
		Cadena con el encabezado o ``None`` si no se encuentra.
	"""
	match = re.search(r"<h2[^>]*>([^<]*hoy[^<]*)</h2>", html, re.IGNORECASE)
	if match:
		return match.group(1).strip()
	# Intentar con un patrón más genérico para páginas de otras fechas.
	match = re.search(
		r"<h2[^>]*>([^<]*\d{1,2}\s+\w+\s+\d{4}[^<]*)</h2>", html, re.IGNORECASE
	)
	return match.group(1).strip() if match else None


def _extract_date_from_body(html):
	"""Extrae la fecha del atributo data-pvpc-day del body.

	Args:
		html: Cadena con el contenido HTML completo de la página.

	Returns:
		Cadena con la fecha en formato YYYY-MM-DD o None.
	"""
	match = re.search(r'data-pvpc-day="(\d{4}-\d{2}-\d{2})"', html)
	return match.group(1) if match else None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def fetch_today_data():
	"""Descarga (o devuelve de caché) los datos de precios de hoy.

	Returns:
		Diccionario con claves: ``price_data``, ``summary``, ``heading``, ``date``.

	Raises:
		error.URLError: Si hay un error de red.
		ValueError: Si no se pueden extraer los datos.
	"""
	today_str = date.today().strftime("%Y-%m-%d")
	if _is_cache_valid(today_str):
		return _cache[today_str]["data"]

	html = _fetch_url(_URL_TODAY)
	price_data = _extract_price_data(html)
	summary = _extract_summary(html)
	heading = _extract_date_heading(html)
	pvpc_date = _extract_date_from_body(html) or today_str

	result = {
		"price_data": price_data,
		"summary": summary,
		"heading": heading,
		"date": pvpc_date,
	}
	_put_cache(today_str, result, html)
	return result


def fetch_tomorrow_data():
	"""Descarga los datos de precios de mañana si están disponibles.

	Los precios del día siguiente se publican normalmente a partir de las 20:15h.

	Returns:
		Diccionario con claves: ``price_data``, ``summary``, ``heading``, ``date``
		o ``None`` si los datos de mañana aún no están disponibles.

	Raises:
		error.URLError: Si hay un error de red.
	"""
	if _is_cache_valid("tomorrow"):
		return _cache["tomorrow"]["data"]

	try:
		html = _fetch_url(_URL_TOMORROW)
		price_data = _extract_price_data(html)
		summary = _extract_summary(html)
		heading = _extract_date_heading(html)
		pvpc_date = _extract_date_from_body(html)

		result = {
			"price_data": price_data,
			"summary": summary,
			"heading": heading,
			"date": pvpc_date,
		}
		_put_cache("tomorrow", result, html)
		return result
	except ValueError:
		# Los datos de mañana aún no están disponibles.
		log.info("Los datos de precios de mañana aún no están disponibles.")
		return None


def fetch_date_data(target_date):
	"""Descarga los datos de precios para una fecha concreta.

	Args:
		target_date: Objeto ``datetime.date`` con la fecha a consultar.

	Returns:
		Diccionario con claves: ``price_data``, ``summary``, ``heading``, ``date``.

	Raises:
		error.URLError: Si hay un error de red.
		ValueError: Si no se pueden extraer los datos para esa fecha.
	"""
	date_str = target_date.strftime("%Y-%m-%d")

	# Si es hoy, usar la función específica.
	if target_date == date.today():
		return fetch_today_data()

	if _is_cache_valid(date_str):
		return _cache[date_str]["data"]

	# Intentar con parámetro de fecha en la URL.
	url = "%s/?date=%s" % (_URL_BASE, date_str)
	html = _fetch_url(url)
	price_data = _extract_price_data(html)
	summary = _extract_summary(html)
	heading = _extract_date_heading(html)
	pvpc_date = _extract_date_from_body(html) or date_str

	result = {
		"price_data": price_data,
		"summary": summary,
		"heading": heading,
		"date": pvpc_date,
	}
	_put_cache(date_str, result, html)
	return result


def get_current_hour_info(data):
	"""Extrae la información del precio de la hora actual.

	Args:
		data: Diccionario devuelto por ``fetch_today_data()``.

	Returns:
		Diccionario con claves: ``hour``, ``price``, ``color``, ``raw_price``.
	"""
	now = datetime.now()
	hour = now.hour
	price_data = data["price_data"]
	prices = price_data["prices"]
	colors = price_data.get("colors", [])
	raw = price_data.get("raw", [])

	return {
		"hour": hour,
		"price": prices[hour] if hour < len(prices) else "N/D",
		"color": colors[hour] if hour < len(colors) else "default",
		"raw_price": raw[hour] if hour < len(raw) else 0.0,
	}
