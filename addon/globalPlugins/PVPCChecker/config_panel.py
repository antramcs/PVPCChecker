# -*- coding: UTF-8 -*-
# PVPCChecker: Panel de configuración del complemento.
# Copyright (C) Antonio Cascales <antonio.cascales@gmail.com>
# Licencia: GPL v2

"""Panel de preferencias de PVPCChecker integrado en la configuración de NVDA."""

import addonHandler
import config
import gui
import wx

addonHandler.initTranslation()

# ---------------------------------------------------------------------------
# Especificación de configuración para config.conf
# ---------------------------------------------------------------------------
_CONFIG_SPEC = {
	"announceOnHourChange": "boolean(default=False)",
	"cacheEnabled": "boolean(default=True)",
	"highlightCurrentHour": "boolean(default=True)",
}

# Registrar la especificación en config.conf de NVDA.
config.conf.spec["pvpcChecker"] = _CONFIG_SPEC


def get_config(key):
	"""Obtiene un valor de configuración de PVPCChecker.

	Args:
		key: Nombre de la clave de configuración.

	Returns:
		Valor de la configuración.
	"""
	return config.conf["pvpcChecker"][key]


def set_config(key, value):
	"""Establece un valor de configuración de PVPCChecker.

	Args:
		key: Nombre de la clave de configuración.
		value: Valor a establecer.
	"""
	config.conf["pvpcChecker"][key] = value


class PVPCCheckerSettingsPanel(gui.settingsDialogs.SettingsPanel):
	"""Panel de configuración de PVPCChecker en las preferencias de NVDA."""

	# Translators: Title of the settings panel in NVDA Preferences.
	title = _("PVPCChecker")

	def makeSettings(self, settingsSizer):
		"""Construye los controles del panel de configuración.

		Args:
			settingsSizer: wx.Sizer proporcionado por NVDA.
		"""
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: Checkbox label for enabling hour change announcements.
		self._announceOnHourChangeCheckBox = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Anunciar el tramo de precio al cambio de hora"),
			)
		)
		self._announceOnHourChangeCheckBox.SetValue(
			get_config("announceOnHourChange")
		)

		# Translators: Checkbox label for enabling data caching.
		self._cacheEnabledCheckBox = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Activar caché de datos (consultas repetidas serán instantáneas)"),
			)
		)
		self._cacheEnabledCheckBox.SetValue(
			get_config("cacheEnabled")
		)

		# Translators: Checkbox label for highlighting the current hour.
		self._highlightCurrentHourCheckBox = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Marcar la hora actual en la tabla de precios"),
			)
		)
		self._highlightCurrentHourCheckBox.SetValue(
			get_config("highlightCurrentHour")
		)

	def onSave(self):
		"""Guarda los valores de configuración cuando el usuario pulsa Aceptar."""
		set_config(
			"announceOnHourChange",
			self._announceOnHourChangeCheckBox.GetValue(),
		)

		cache_was_enabled = get_config("cacheEnabled")
		cache_now_enabled = self._cacheEnabledCheckBox.GetValue()
		set_config("cacheEnabled", cache_now_enabled)

		# Si se desactiva la caché, limpiarla.
		if cache_was_enabled and not cache_now_enabled:
			from . import fetcher
			fetcher.invalidate_cache()

		set_config(
			"highlightCurrentHour",
			self._highlightCurrentHourCheckBox.GetValue(),
		)
