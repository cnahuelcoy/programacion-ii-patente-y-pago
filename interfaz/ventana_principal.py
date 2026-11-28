"""Ventana principal de la aplicación "Patente y Pago".

Contiene un Notebook (pestañas). Cada pantalla es una pestaña. Recibe las
funciones de negocio/persistencia y se las entrega a cada pantalla; así la
interfaz no depende de dónde vienen los datos.
"""

import tkinter as tk
from tkinter import ttk

from interfaz.pantalla_ingresos import PantallaIngresos
from interfaz.pantalla_presentes import PantallaPresentes
from interfaz.pantalla_salidas import PantallaSalidas
from interfaz.pantalla_suscripciones import PantallaSuscripciones
from interfaz.pantalla_vehiculos import PantallaVehiculos


class VentanaPrincipal(tk.Tk):
    def __init__(
        self,
        registrar_vehiculo,
        listar_vehiculos,
        registrar_ingreso,
        registrar_salida=None,
        contratar_suscripcion=None,
        listar_vehiculos_presentes=None,
    ):
        super().__init__()
        self.title("Patente y Pago")
        self.geometry("800x520")
        self.minsize(640, 420)

        self._pestanas = ttk.Notebook(self)
        self._pestanas.pack(fill="both", expand=True, padx=5, pady=5)

        self.pantalla_vehiculos = PantallaVehiculos(
            self._pestanas, registrar_vehiculo, listar_vehiculos
        )
        self.pantalla_ingresos = PantallaIngresos(self._pestanas, registrar_ingreso)
        self.pantalla_salidas = PantallaSalidas(self._pestanas, registrar_salida)

        self._pestanas.add(self.pantalla_vehiculos, text="Vehículos")
        self._pestanas.add(self.pantalla_ingresos, text="Ingresos")
        self._pestanas.add(self.pantalla_salidas, text="Salidas")
        if registrar_salida is None:
            self._pestanas.tab(self.pantalla_salidas, state="disabled")

        self.pantalla_suscripciones = None
        if contratar_suscripcion is not None:
            self.pantalla_suscripciones = PantallaSuscripciones(
                self._pestanas, contratar_suscripcion
            )
            self._pestanas.add(self.pantalla_suscripciones, text="Suscripciones")

        self.pantalla_presentes = None
        if listar_vehiculos_presentes is not None:
            self.pantalla_presentes = PantallaPresentes(
                self._pestanas, listar_vehiculos_presentes
            )
            self._pestanas.add(self.pantalla_presentes, text="Presentes")

        # Próximos PR: agregar aquí las pestañas de suscripciones,
        # historial y reportes con self._pestanas.add(...).
