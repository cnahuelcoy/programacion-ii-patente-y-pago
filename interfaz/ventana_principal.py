"""Ventana principal de la aplicación "Patente y Pago".

Contiene un Notebook (pestañas). Cada pantalla es una pestaña; en este PR
solo está "Vehículos". Los siguientes PR agregan las demás pestañas.
"""

import tkinter as tk
from tkinter import ttk

from interfaz.pantalla_vehiculos import PantallaVehiculos


class VentanaPrincipal(tk.Tk):
    def __init__(self, registrar_vehiculo, listar_vehiculos):
        super().__init__()
        self.title("Patente y Pago")
        self.geometry("800x520")
        self.minsize(640, 420)

        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True, padx=5, pady=5)

        self.pantalla_vehiculos = PantallaVehiculos(
            self._pestanas, registrar_vehiculo, listar_vehiculos
        )
        self._pestanas.add(self.pantalla_vehiculos, text="Vehículos")

        # Próximos PR: agregar aquí las pestañas de ingresos/salidas,
        # suscripciones, historial y reportes con self._pestanas.add(...).
