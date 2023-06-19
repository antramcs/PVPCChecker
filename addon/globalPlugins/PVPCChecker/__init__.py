import globalPluginHandler
import api
import gui
import ui

import wx
import sys, os

from scriptHandler import script
from urllib import request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
	del sys.modules['html']
except:
	pass

from bs4 import BeautifulSoup

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self):
        super(GlobalPlugin, self).__init__()

    @script(gesture="kb:NVDA+shift+p", description="Permite consultar el precio de la energía eléctrica en España a día de hoy.", category="PVPCChecker")
    def script_check_energy_price(self, gesture):
        self.consultarPrecioEnergia()

    def consultarPrecioEnergia(self):
        url = "https://tarifaluzhora.es/"
        req = request.Request(url, data=None, headers={"User-Agent": "Mozilla/5.0"})
        html = request.urlopen(req)
        data = html.read().decode("utf-8")
        bs = BeautifulSoup(data, 'html.parser')
        divs = bs.find_all('div', class_="card")
        horarios = bs.find_all('span', {"itemprop": "description"})
        precios = bs.find_all('span', {"itemprop": "price"})
        titulo = bs.find('p', {"class": "template-tlh__colors--hours-title"})
        footnote = bs.find('div', {"class": "template-tlh__footnote"})
        mensaje = ""

        for i in range(0, len(divs) -3):
            for element in divs[i].stripped_strings:
                mensaje = mensaje + element + "\n\n"

        mensaje = mensaje + titulo.text + "\n\n"

        for i in range(0, 24):
            mensaje = mensaje + horarios[i].text + ": " + precios[i].text + ".\n"

        mensaje = mensaje + footnote.text + "\n"

        ui.browseableMessage(mensaje, "PVPCChecker")