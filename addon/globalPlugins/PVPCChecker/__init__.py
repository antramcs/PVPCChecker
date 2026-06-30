# -*- coding: UTF-8 -*-
# PVPCChecker: Complemento de NVDA para consultar el precio de la energía en España (PVPC).
# Copyright (C) Antonio Cascales <antonio.cascales@gmail.com>
# Licencia: GPL v2

import globalPluginHandler
import addonHandler
import api
import braille
import config
import gui
import scriptHandler
import ui
import wx
import threading
import logging
from datetime import datetime, timedelta
from scriptHandler import script

from . import fetcher
from . import formatter
from .config_panel import PVPCCheckerSettingsPanel, get_config

addonHandler.initTranslation()

log = logging.getLogger(__name__)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Plugin global de NVDA para consultar los precios de la energía eléctrica PVPC."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._fetch_thread = None
		self._hour_change_timer = None
		self._last_announced_hour = None

		# Registrar panel de configuración.
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(
			PVPCCheckerSettingsPanel
		)

		# Crear menú en la barra de herramientas de NVDA.
		self._create_tools_menu()

		# Programar anuncio de cambio de hora si está activado.
		if get_config("announceOnHourChange"):
			self._schedule_hour_change()

	def terminate(self, *args, **kwargs):
		# Eliminar panel de configuración.
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(
			PVPCCheckerSettingsPanel
		)
		# Eliminar menú.
		self._remove_tools_menu()
		# Cancelar timer de cambio de hora.
		if self._hour_change_timer is not None:
			self._hour_change_timer.Stop()
			self._hour_change_timer = None
		super().terminate(*args, **kwargs)

	# -------------------------------------------------------------------
	# Menú de herramientas
	# -------------------------------------------------------------------
	def _create_tools_menu(self):
		"""Crea el submenú PVPCChecker en el menú Herramientas de NVDA."""
		self._tools_menu = wx.Menu()

		# Translators: Menu item to check the current electricity price.
		self._menu_current = self._tools_menu.Append(
			wx.ID_ANY,
			_("&Precio actual"),
			_("Anuncia el precio de la hora actual"),
		)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU, self._on_menu_current, self._menu_current,
		)

		# Translators: Menu item to show the full price table.
		self._menu_full_table = self._tools_menu.Append(
			wx.ID_ANY,
			_("&Tabla completa de hoy"),
			_("Muestra la tabla completa de precios del día"),
		)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU, self._on_menu_full_table, self._menu_full_table,
		)

		# Translators: Menu item to check tomorrow's prices.
		self._menu_tomorrow = self._tools_menu.Append(
			wx.ID_ANY,
			_("Precios de &mañana"),
			_("Muestra los precios de mañana si están disponibles"),
		)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU, self._on_menu_tomorrow, self._menu_tomorrow,
		)

		# Translators: Menu item to check prices for a specific date.
		self._menu_date = self._tools_menu.Append(
			wx.ID_ANY,
			_("Consultar &fecha concreta..."),
			_("Muestra los precios de una fecha seleccionada"),
		)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU, self._on_menu_date, self._menu_date,
		)

		# Translators: Menu item to copy the current price to the clipboard.
		self._menu_clipboard = self._tools_menu.Append(
			wx.ID_ANY,
			_("&Copiar al portapapeles"),
			_("Copia la información de precios al portapapeles"),
		)
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU, self._on_menu_clipboard, self._menu_clipboard,
		)

		# Translators: Label for the PVPCChecker submenu in the Tools menu.
		self._tools_submenu = gui.mainFrame.sysTrayIcon.toolsMenu.AppendSubMenu(
			self._tools_menu,
			_("PVPCChecker"),
		)

	def _remove_tools_menu(self):
		"""Elimina el submenú PVPCChecker del menú Herramientas."""
		try:
			gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self._tools_submenu)
		except Exception:
			pass

	def _on_menu_current(self, event):
		"""Manejador del menú: Precio actual."""
		self._do_quick_check()

	def _on_menu_full_table(self, event):
		"""Manejador del menú: Tabla completa."""
		self._do_full_check()

	def _on_menu_tomorrow(self, event):
		"""Manejador del menú: Precios de mañana."""
		self._do_tomorrow_check()

	def _on_menu_date(self, event):
		"""Manejador del menú: Fecha concreta."""
		self._show_date_picker()

	def _on_menu_clipboard(self, event):
		"""Manejador del menú: Copiar al portapapeles."""
		self._do_copy_to_clipboard()

	# -------------------------------------------------------------------
	# Scripts (gestos de entrada)
	# -------------------------------------------------------------------
	@script(
		# Translators: Description for the main energy price check gesture.
		# Single press announces current price; double press shows full table.
		description=_(
			"Consulta el precio de la energía eléctrica en España (PVPC). "
			"Pulse una vez para el resumen rápido, dos veces para la tabla completa."
		),
		category="PVPCChecker",
	)
	def script_check_energy_price(self, gesture):
		"""Script principal: una pulsación = resumen, doble = tabla completa."""
		repeat = scriptHandler.getLastScriptRepeatCount()
		if repeat == 0:
			self._do_quick_check()
		else:
			self._do_full_check()

	@script(
		# Translators: Description for the tomorrow price check gesture.
		description=_(
			"Consulta los precios de la energía eléctrica de mañana (si están disponibles)."
		),
		category="PVPCChecker",
	)
	def script_check_tomorrow_price(self, gesture):
		"""Script para consultar los precios de mañana."""
		self._do_tomorrow_check()

	@script(
		# Translators: Description for the date-specific price check gesture.
		description=_(
			"Consulta los precios de la energía para una fecha concreta."
		),
		category="PVPCChecker",
	)
	def script_check_date_price(self, gesture):
		"""Script para consultar precios de una fecha concreta."""
		self._show_date_picker()

	@script(
		# Translators: Description for the copy-to-clipboard gesture.
		description=_(
			"Copia la información de precios de la energía al portapapeles."
		),
		category="PVPCChecker",
	)
	def script_copy_price_to_clipboard(self, gesture):
		"""Script para copiar los precios al portapapeles."""
		self._do_copy_to_clipboard()

	# -------------------------------------------------------------------
	# Lógica de negocio
	# -------------------------------------------------------------------
	def _is_fetch_busy(self):
		"""Comprueba si ya hay una descarga en curso."""
		if self._fetch_thread is not None and self._fetch_thread.is_alive():
			# Translators: Message when a fetch is already in progress.
			ui.message(_("Ya se está consultando el precio. Por favor, espere."))
			return True
		return False

	def _do_quick_check(self):
		"""Anuncia el precio de la hora actual por voz y Braille."""
		if self._is_fetch_busy():
			return
		# Translators: Announced while fetching price data.
		ui.message(_("Consultando precio de la energía..."))
		self._fetch_thread = threading.Thread(
			target=self._fetch_and_announce_quick,
			daemon=True,
		)
		self._fetch_thread.start()

	def _do_full_check(self):
		"""Muestra la tabla completa de precios en una ventana."""
		if self._is_fetch_busy():
			return
		# Translators: Announced while fetching price data.
		ui.message(_("Consultando precio de la energía..."))
		self._fetch_thread = threading.Thread(
			target=self._fetch_and_show_full,
			daemon=True,
		)
		self._fetch_thread.start()

	def _do_tomorrow_check(self):
		"""Consulta los precios de mañana."""
		if self._is_fetch_busy():
			return
		# Translators: Announced while fetching tomorrow's price data.
		ui.message(_("Consultando precios de mañana..."))
		self._fetch_thread = threading.Thread(
			target=self._fetch_and_show_tomorrow,
			daemon=True,
		)
		self._fetch_thread.start()

	def _do_copy_to_clipboard(self):
		"""Copia los precios al portapapeles."""
		if self._is_fetch_busy():
			return
		# Translators: Announced while fetching price data for clipboard.
		ui.message(_("Consultando precio de la energía..."))
		self._fetch_thread = threading.Thread(
			target=self._fetch_and_copy,
			daemon=True,
		)
		self._fetch_thread.start()

	# -------------------------------------------------------------------
	# Hilos de descarga
	# -------------------------------------------------------------------
	def _fetch_and_announce_quick(self):
		"""Descarga datos y anuncia el resumen rápido por voz y Braille."""
		try:
			use_cache = get_config("cacheEnabled")
			if not use_cache:
				fetcher.invalidate_cache()
			data = fetcher.fetch_today_data()
			msg = formatter.build_quick_message(data)
			wx.CallAfter(self._announce_quick, msg)
		except Exception as exc:
			self._handle_error(exc)

	def _fetch_and_show_full(self):
		"""Descarga datos y muestra la tabla completa."""
		try:
			use_cache = get_config("cacheEnabled")
			if not use_cache:
				fetcher.invalidate_cache()
			data = fetcher.fetch_today_data()
			highlight = get_config("highlightCurrentHour")
			msg = formatter.build_full_message(data, highlight_current=highlight)
			wx.CallAfter(
				ui.browseableMessage,
				msg,
				# Translators: Title of the full price table window.
				_("PVPCChecker — Precios de hoy"),
			)
		except Exception as exc:
			self._handle_error(exc)

	def _fetch_and_show_tomorrow(self):
		"""Descarga datos de mañana y los muestra."""
		try:
			use_cache = get_config("cacheEnabled")
			if not use_cache:
				fetcher.invalidate_cache()
			data = fetcher.fetch_tomorrow_data()
			if data is None:
				wx.CallAfter(
					ui.message,
					# Translators: Message when tomorrow's prices are not yet available.
					_(
						"Los precios de mañana aún no están disponibles. "
						"Suelen publicarse a partir de las 20:15h."
					),
				)
				return
			msg = formatter.build_full_message(data, highlight_current=False)
			wx.CallAfter(
				ui.browseableMessage,
				msg,
				# Translators: Title of the tomorrow's price table window.
				_("PVPCChecker — Precios de mañana"),
			)
		except Exception as exc:
			self._handle_error(exc)

	def _fetch_and_show_date(self, target_date):
		"""Descarga datos de una fecha concreta y los muestra.

		Args:
			target_date: Objeto ``datetime.date`` con la fecha a consultar.
		"""
		try:
			use_cache = get_config("cacheEnabled")
			if not use_cache:
				fetcher.invalidate_cache()
			data = fetcher.fetch_date_data(target_date)
			msg = formatter.build_full_message(data, highlight_current=False)
			# Translators: Title of the date-specific price table window.
			# {date} is the selected date.
			title = _("PVPCChecker — Precios del {date}").format(
				date=target_date.strftime("%d/%m/%Y"),
			)
			wx.CallAfter(ui.browseableMessage, msg, title)
		except Exception as exc:
			self._handle_error(exc)

	def _fetch_and_copy(self):
		"""Descarga datos y copia al portapapeles."""
		try:
			use_cache = get_config("cacheEnabled")
			if not use_cache:
				fetcher.invalidate_cache()
			data = fetcher.fetch_today_data()
			text = formatter.build_clipboard_text(data)
			wx.CallAfter(self._copy_and_announce, text)
		except Exception as exc:
			self._handle_error(exc)

	# -------------------------------------------------------------------
	# Acciones en el hilo principal (wx)
	# -------------------------------------------------------------------
	def _announce_quick(self, msg):
		"""Anuncia el resumen rápido por voz y Braille."""
		ui.message(msg)
		try:
			braille.handler.message(msg)
		except Exception:
			# Braille puede no estar disponible.
			pass

	def _copy_and_announce(self, text):
		"""Copia texto al portapapeles y anuncia el resultado."""
		api.copyToClip(text)
		# Translators: Announced after successfully copying to clipboard.
		ui.message(_("Información de precios copiada al portapapeles."))

	def _handle_error(self, exc):
		"""Maneja errores de descarga mostrando un mensaje al usuario."""
		from urllib import error as url_error

		log.exception("Error en PVPCChecker: %s", exc)
		if isinstance(exc, url_error.URLError):
			wx.CallAfter(
				ui.message,
				# Translators: Error message for network failures.
				_("Error de conexión al consultar el precio de la energía: %s") % exc,
			)
		elif isinstance(exc, ValueError):
			wx.CallAfter(ui.message, str(exc))
		else:
			wx.CallAfter(
				ui.message,
				# Translators: Generic error message.
				_("Error inesperado al consultar el precio de la energía: %s") % exc,
			)

	# -------------------------------------------------------------------
	# Diálogo de selección de fecha
	# -------------------------------------------------------------------
	def _show_date_picker(self):
		"""Muestra un diálogo para seleccionar una fecha y consultar sus precios."""
		# Debe ejecutarse en el hilo principal de wx.
		wx.CallAfter(self._do_show_date_picker)

	def _do_show_date_picker(self):
		"""Crea y muestra el diálogo de selección de fecha."""
		# Translators: Title of the date picker dialog.
		dialog = wx.Dialog(
			gui.mainFrame,
			title=_("PVPCChecker — Seleccionar fecha"),
			style=wx.DEFAULT_DIALOG_STYLE,
		)

		sizer = wx.BoxSizer(wx.VERTICAL)

		# Translators: Label for the date picker control.
		label = wx.StaticText(dialog, label=_("Seleccione la fecha a consultar:"))
		sizer.Add(label, flag=wx.ALL, border=10)

		date_picker = wx.adv.DatePickerCtrl(
			dialog,
			style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY,
		)
		sizer.Add(date_picker, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=10)

		btn_sizer = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
		sizer.Add(btn_sizer, flag=wx.ALL | wx.ALIGN_CENTER, border=10)

		dialog.SetSizer(sizer)
		sizer.Fit(dialog)
		dialog.CenterOnScreen()

		result = dialog.ShowModal()
		if result == wx.ID_OK:
			wx_date = date_picker.GetValue()
			from datetime import date as date_cls
			target = date_cls(
				wx_date.GetYear(),
				wx_date.GetMonth() + 1,  # wx months are 0-indexed
				wx_date.GetDay(),
			)
			dialog.Destroy()

			if self._is_fetch_busy():
				return
			# Translators: Announced while fetching price data for a date.
			ui.message(
				_("Consultando precios del {date}...").format(
					date=target.strftime("%d/%m/%Y"),
				)
			)
			self._fetch_thread = threading.Thread(
				target=self._fetch_and_show_date,
				args=(target,),
				daemon=True,
			)
			self._fetch_thread.start()
		else:
			dialog.Destroy()

	# -------------------------------------------------------------------
	# Anuncio al cambio de hora
	# -------------------------------------------------------------------
	def _schedule_hour_change(self):
		"""Programa el anuncio para el próximo cambio de hora."""
		now = datetime.now()
		next_hour = (now + timedelta(hours=1)).replace(
			minute=0, second=1, microsecond=0,
		)
		delay_ms = int((next_hour - now).total_seconds() * 1000)
		# Mínimo 1 segundo para evitar bucles.
		delay_ms = max(delay_ms, 1000)
		self._hour_change_timer = wx.CallLater(
			delay_ms, self._on_hour_change,
		)

	def _on_hour_change(self):
		"""Callback ejecutado al inicio de cada hora."""
		if not get_config("announceOnHourChange"):
			return

		now = datetime.now()
		current_hour = now.hour

		# Evitar anuncios duplicados.
		if current_hour == self._last_announced_hour:
			self._schedule_hour_change()
			return
		self._last_announced_hour = current_hour

		# Intentar obtener datos de caché (no bloquear con descarga).
		try:
			from datetime import date
			today_str = date.today().strftime("%Y-%m-%d")
			if today_str in fetcher._cache:
				data = fetcher._cache[today_str]["data"]
				msg = formatter.build_hour_change_message(data)
				ui.message(msg)
				try:
					braille.handler.message(msg)
				except Exception:
					pass
		except Exception:
			log.debug("No se pudo anunciar el cambio de hora.", exc_info=True)

		# Reprogramar para la próxima hora.
		self._schedule_hour_change()