# -*- coding: UTF-8 -*-
# PVPCChecker: Complemento de NVDA para consultar el precio de la energía en España (PVPC).
# Copyright (C) Antonio Cascales <antonio.cascales@gmail.com>
# Licencia: GPL v2

import globalPluginHandler
import addonHandler
import ui
import wx
import threading
import re
import json
import logging
from urllib import request, error
from scriptHandler import script

addonHandler.initTranslation()

log = logging.getLogger(__name__)

# Constantes
_URL = "https://tarifaluzhora.es/"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_TIMEOUT = 30

# Mapa de colores del API a etiquetas de tramo para el usuario.
_COLOR_LABELS = {
	# Translators: Price level label for expensive hours
	"high": _("caro"),
	# Translators: Price level label for normal-priced hours
	"default": _("normal"),
	# Translators: Price level label for cheap hours
	"low": _("barato"),
}


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
			# Translators: Error when the website structure has changed
			_("No se encontraron datos de precios en la página. "
			  "Es posible que la estructura de la web haya cambiado.")
		)
	raw_json = match.group(1).replace("\\u0022", '"')
	try:
		data = json.loads(raw_json)
	except json.JSONDecodeError as exc:
		raise ValueError(
			# Translators: Error when JSON parsing fails
			_("Error al interpretar los datos de precios: %s") % exc
		) from exc
	if "prices" not in data:
		raise ValueError(
			# Translators: Error when expected data fields are missing
			_("Los datos de precios no tienen el formato esperado.")
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
	return match.group(1).strip() if match else None


def _build_message(html):
	"""Construye el mensaje completo para mostrar al usuario.

	Args:
		html: Cadena con el contenido HTML completo de la página.

	Returns:
		Cadena formateada con la información de precios por hora.
	"""
	data = _extract_price_data(html)
	prices = data["prices"]
	colors = data.get("colors", [])

	parts = []

	# Encabezado con fecha
	heading = _extract_date_heading(html)
	if heading:
		parts.append(heading)
		parts.append("")

	# Resumen del día
	summary = _extract_summary(html)
	if summary:
		parts.append(summary)
		parts.append("")

	# Tabla de precios por hora
	# Translators: Section header for hourly prices table
	parts.append(_("Precios por hora:"))
	parts.append("")
	for hour in range(min(len(prices), 24)):
		price = prices[hour]
		color_key = colors[hour] if hour < len(colors) else "default"
		label = _COLOR_LABELS.get(color_key, color_key)
		# Translators: Format for each hourly price line.
		# {start} is the start hour, {end} is the end hour,
		# {price} is the price, {level} is cheap/normal/expensive.
		line = _("{start:02d}h - {end:02d}h: {price} €/kWh [{level}]").format(
			start=hour,
			end=hour + 1,
			price=price,
			level=label,
		)
		parts.append(line)

	# Nota de fuente
	parts.append("")
	# Translators: Data source attribution
	parts.append(_("Fuente: tarifaluzhora.es — Datos de Red Eléctrica de España."))

	return "\n".join(parts)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Plugin global de NVDA para consultar los precios de la energía eléctrica PVPC."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._fetch_thread = None

	def terminate(self, *args, **kwargs):
		super().terminate(*args, **kwargs)

	@script(
		# Translators: Description shown in the NVDA Input Gestures dialog.
		description=_("Consulta el precio de la energía eléctrica en España (PVPC)"),
		category="PVPCChecker",
	)
	def script_check_energy_price(self, gesture):
		"""Script principal que inicia la consulta de precios en segundo plano."""
		if self._fetch_thread is not None and self._fetch_thread.is_alive():
			# Translators: Message when a fetch is already in progress
			ui.message(_("Ya se está consultando el precio. Por favor, espere."))
			return
		# Translators: Announced while fetching price data from the web
		ui.message(_("Consultando precio de la energía..."))
		self._fetch_thread = threading.Thread(
			target=self._fetch_energy_price,
			daemon=True,
		)
		self._fetch_thread.start()

	def _fetch_energy_price(self):
		"""Descarga y procesa los datos de precios en un hilo secundario."""
		try:
			req = request.Request(
				_URL,
				data=None,
				headers={"User-Agent": _USER_AGENT},
			)
			with request.urlopen(req, timeout=_TIMEOUT) as response:
				html = response.read().decode("utf-8")
			message = _build_message(html)
			wx.CallAfter(ui.browseableMessage, message, "PVPCChecker")
		except error.URLError as exc:
			log.error("Error de red al consultar tarifaluzhora.es: %s", exc)
			wx.CallAfter(
				ui.message,
				# Translators: Error message for network failures
				_("Error de conexión al consultar el precio de la energía: %s") % exc,
			)
		except ValueError as exc:
			log.error("Error al procesar datos de tarifaluzhora.es: %s", exc)
			wx.CallAfter(
				ui.message,
				str(exc),
			)
		except Exception as exc:
			log.exception("Error inesperado en PVPCChecker")
			wx.CallAfter(
				ui.message,
				# Translators: Generic error message
				_("Error inesperado al consultar el precio de la energía: %s") % exc,
			)