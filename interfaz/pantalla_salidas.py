"""Pantalla de salidas: registra la salida de un vehículo y muestra el cobro.

Solo maneja la interfaz. Recibe una función y delega en ella:

    registrar_salida(patente, fecha_salida) -> dict

donde fecha_salida es un datetime sin zona horaria y el diccionario
devuelto incluye patente, fecha_ingreso, fecha_salida, modalidad y monto
(en pesos chilenos). El cálculo del monto NO se hace aquí: lo hace la
lógica de negocio. Si la salida no es válida, la función debe lanzar
ValueError con un mensaje comprensible; la pantalla lo muestra tal cual.
"""

import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from interfaz.formato import formatear_fecha, formatear_pesos, parsear_fecha


class PantallaSalidas(ttk.Frame):
    def __init__(self, master, registrar_salida):
        super().__init__(master, padding=10)
        self._registrar_salida = registrar_salida
        self._variables = {
            "patente": tk.StringVar(),
            "fecha": tk.StringVar(),
        }
        self._resultado = tk.StringVar()
        self._crear_formulario()
        self.poner_fecha_actual()

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Registrar salida", padding=10)
        marco.pack(fill="x")
        marco.columnconfigure(1, weight=1)

        ttk.Label(marco, text="Patente:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=3)
        self._entrada_patente = ttk.Entry(marco, textvariable=self._variables["patente"])
        self._entrada_patente.grid(row=0, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(marco, text="Fecha y hora:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(marco, textvariable=self._variables["fecha"]).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Button(marco, text="Ahora", command=self.poner_fecha_actual).grid(row=1, column=2, padx=(5, 0))

        ttk.Label(marco, text="dd/mm/aaaa HH:MM:SS (se puede editar para pruebas)").grid(
            row=2, column=1, columnspan=2, sticky="w"
        )

        ttk.Button(marco, text="Registrar salida", command=self.registrar).grid(
            row=3, column=0, columnspan=3, sticky="e", pady=(8, 0)
        )
        self._entrada_patente.bind("<Return>", lambda evento: self.registrar())

        ttk.Label(self, textvariable=self._resultado, padding=(0, 10)).pack(anchor="w")

    def poner_fecha_actual(self):
        self._variables["fecha"].set(formatear_fecha(datetime.now()))

    def registrar(self):
        """Convierte la fecha, llama a registrar_salida y muestra el cobro."""
        try:
            fecha = parsear_fecha(self._variables["fecha"].get())
            salida = self._registrar_salida(self._variables["patente"].get(), fecha)
        except ValueError as error:
            messagebox.showerror("No se pudo registrar la salida", str(error))
            return
        except Exception:
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un problema al registrar la salida. Intenta nuevamente.",
            )
            return

        monto = formatear_pesos(salida["monto"])
        texto = (
            "Salida registrada correctamente.\n\n"
            f"Patente: {salida['patente']}\n"
            f"Ingreso: {formatear_fecha(salida['fecha_ingreso'])}\n"
            f"Salida: {formatear_fecha(salida['fecha_salida'])}\n"
            f"Modalidad: {salida['modalidad']}\n"
            f"Monto a pagar: {monto}"
        )
        if salida["modalidad"] == "mensual":
            texto += "\n\nEstadía cubierta por la suscripción mensual: sin cobro adicional."

        self._resultado.set(
            f"Última salida: {salida['patente']} - modalidad {salida['modalidad']} - monto {monto}"
        )
        self._variables["patente"].set("")
        self.poner_fecha_actual()
        self._entrada_patente.focus_set()
        messagebox.showinfo("Salida registrada", texto)
