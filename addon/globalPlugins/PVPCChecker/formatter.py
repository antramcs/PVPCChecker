# -*- coding: UTF-8 -*-
# PVPCChecker: Módulo de formateo de mensajes de precios PVPC.
# Copyright (C) Antonio Cascales <antonio.cascales@gmail.com>
# Licencia: GPL v2

"""Construcción de mensajes formateados a partir de los datos de precios."""

import addonHandler
from datetime import datetime

addonHandler.initTranslation()

# Mapa de colores del API a etiquetas de tramo para el usuario.
_COLOR_LABELS = {
	# Translators: Price level label for expensive hours
	"high": _("caro"),
	# Translators: Price level label for normal-priced hours
	"default": _("normal"),
	# Translators: Price level label for cheap hours
	"low": _("barato"),
}


def _fmt_price(price_str):
	"""Formatea un precio a un máximo de 2 decimales.

	Los precios de tarifaluzhora.es vienen con 4 decimales (ej: "0,1364"),
	lo cual es incómodo al ser leído por un lector de pantalla dígito a dígito.
	Esta función los redondea a 2 decimales (ej: "0,14").

	Args:
		price_str: Precio como cadena con coma decimal (ej: "0,1364").

	Returns:
		Cadena formateada con 2 decimales (ej: "0,14").
	"""
	try:
		value = float(price_str.replace(",", "."))
		return "{:.2f}".format(value).replace(".", ",")
	except (ValueError, AttributeError):
		return price_str


def _get_color_label(color_key):
	"""Devuelve la etiqueta traducida para un color de tramo.

	Args:
		color_key: Clave del color ("high", "default", "low").

	Returns:
		Cadena traducida con la etiqueta del tramo.
	"""
	return _COLOR_LABELS.get(color_key, color_key)


def _find_extremes(price_data):
	"""Encuentra la hora más barata y la más cara del día.

	Args:
		price_data: Diccionario con ``raw`` (lista de precios numéricos).

	Returns:
		Tupla (cheapest_hour, cheapest_price, expensive_hour, expensive_price)
		o None si no hay datos ``raw``.
	"""
	raw = price_data.get("raw", [])
	if not raw:
		return None
	min_price = min(raw)
	max_price = max(raw)
	cheapest_hour = raw.index(min_price)
	expensive_hour = raw.index(max_price)
	prices = price_data.get("prices", [])
	cheapest_fmt = _fmt_price(prices[cheapest_hour]) if cheapest_hour < len(prices) else _fmt_price(str(min_price))
	expensive_fmt = _fmt_price(prices[expensive_hour]) if expensive_hour < len(prices) else _fmt_price(str(max_price))
	return (cheapest_hour, cheapest_fmt, expensive_hour, expensive_fmt)


def build_full_message(data, highlight_current=True):
	"""Construye el mensaje completo con tabla de 24h para mostrar al usuario.

	Args:
		data: Diccionario devuelto por ``fetcher.fetch_today_data()`` o similares.
		highlight_current: Si True, marca la hora actual con un indicador.

	Returns:
		Cadena formateada con toda la información de precios.
	"""
	price_data = data["price_data"]
	prices = price_data["prices"]
	colors = price_data.get("colors", [])
	now_hour = datetime.now().hour

	parts = []

	# Encabezado con fecha.
	heading = data.get("heading")
	if heading:
		parts.append(heading)
		parts.append("")

	# Resumen del día.
	summary = data.get("summary")
	if summary:
		parts.append(summary)

	# Hora más barata y más cara.
	extremes = _find_extremes(price_data)
	if extremes:
		cheapest_hour, cheapest_fmt, expensive_hour, expensive_fmt = extremes
		# Translators: Cheapest hour summary line.
		parts.append(
			_("Hora más barata: {start:02d}h - {end:02d}h ({price} €/kWh)").format(
				start=cheapest_hour, end=cheapest_hour + 1, price=cheapest_fmt,
			)
		)
		# Translators: Most expensive hour summary line.
		parts.append(
			_("Hora más cara: {start:02d}h - {end:02d}h ({price} €/kWh)").format(
				start=expensive_hour, end=expensive_hour + 1, price=expensive_fmt,
			)
		)

	parts.append("")

	# Tabla de precios por hora.
	# Translators: Section header for hourly prices table
	parts.append(_("Precios por hora:"))
	# Translators: Column headers for the price table
	parts.append(_("Hora          | Precio       | Tramo"))
	parts.append("-" * 42)

	for hour in range(min(len(prices), 24)):
		price = _fmt_price(prices[hour])
		color_key = colors[hour] if hour < len(colors) else "default"
		label = _get_color_label(color_key)

		# Indicador de hora actual.
		if highlight_current and hour == now_hour:
			# Translators: Marker for the current hour in the price table.
			marker = _(" ◄ ACTUAL")
		else:
			marker = ""

		# Translators: Format for each hourly price line in the table.
		line = "{start:02d}h - {end:02d}h  | {price:<12s} | {level}{marker}".format(
			start=hour,
			end=hour + 1,
			price=price + " €/kWh",
			level=label,
			marker=marker,
		)
		parts.append(line)

	# Nota de fuente.
	parts.append("")
	# Translators: Data source attribution
	parts.append(_("Fuente: tarifaluzhora.es — Datos de Red Eléctrica de España."))

	return "\n".join(parts)


def build_quick_message(data):
	"""Construye un resumen rápido de una línea para anunciar por voz.

	Args:
		data: Diccionario devuelto por ``fetcher.fetch_today_data()``.

	Returns:
		Cadena breve con el precio actual, tramo y media del día.
	"""
	price_data = data["price_data"]
	prices = price_data["prices"]
	colors = price_data.get("colors", [])
	raw = price_data.get("raw", [])
	now_hour = datetime.now().hour

	price = _fmt_price(prices[now_hour]) if now_hour < len(prices) else "N/D"
	color_key = colors[now_hour] if now_hour < len(colors) else "default"
	label = _get_color_label(color_key)

	# Calcular media.
	if raw:
		avg = sum(raw) / len(raw)
		avg_fmt = "{:.2f}".format(avg).replace(".", ",")
	else:
		avg_fmt = "N/D"

	# Translators: Quick voice summary of current price.
	# {start} and {end} are the start/end hours,
	# {price} is the current price, {level} is the price level,
	# {avg} is the daily average.
	return _(
		"{start:02d}h - {end:02d}h: {price} €/kWh [{level}]. "
		"Media del día: {avg} €/kWh"
	).format(
		start=now_hour,
		end=now_hour + 1,
		price=price,
		level=label,
		avg=avg_fmt,
	)


def build_clipboard_text(data):
	"""Genera texto plano optimizado para copiar al portapapeles.

	Args:
		data: Diccionario devuelto por ``fetcher.fetch_today_data()`` o similares.

	Returns:
		Cadena con la información completa en texto plano.
	"""
	# Reutiliza el mensaje completo sin marcador de hora actual.
	return build_full_message(data, highlight_current=False)


def build_hour_change_message(data):
	"""Construye el mensaje para anunciar un cambio de hora.

	Args:
		data: Diccionario devuelto por ``fetcher.fetch_today_data()``.

	Returns:
		Cadena con la información de la nueva hora.
	"""
	price_data = data["price_data"]
	prices = price_data["prices"]
	colors = price_data.get("colors", [])
	now_hour = datetime.now().hour

	price = _fmt_price(prices[now_hour]) if now_hour < len(prices) else "N/D"
	color_key = colors[now_hour] if now_hour < len(colors) else "default"
	label = _get_color_label(color_key)

	# Translators: Announcement when the hour changes.
	return _("Cambio de hora: {start:02d}h - {end:02d}h, precio {price} €/kWh [{level}]").format(
		start=now_hour,
		end=now_hour + 1,
		price=price,
		level=label,
	)
