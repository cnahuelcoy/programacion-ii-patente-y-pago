"""Pantalla de ingresos: registra la entrada de un vehículo.

Solo maneja la interfaz. Recibe una función y delega en ella:

    registrar_ingreso(patente, fecha_ingreso, modalidad) -> dict

donde fecha_ingreso es un datetime sin zona horaria, modalidad es "minuto"
o "diaria", y el diccionario devuelto incluye patente, fecha_ingreso y
modalidad (que puede ser "mensual" si el vehículo tiene cobertura).
Si el ingreso no es válido, la función debe lanzar ValueError con un
mensaje comprensible; la pantalla lo muestra tal cual.
"""

import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from interfaz.formato import formatear_fecha, parsear_fecha


class PantallaIngresos(ttk.Frame):
    MODALIDADES = ("minuto", "diaria")

    def __init__(self, master, registrar_ingreso):
        super().__init__(master, padding=10)
        self._registrar_ingreso = registrar_ingreso
        self._variables = {
            "patente": tk.StringVar(),
            "fecha": tk.StringVar(),
            "modalidad": tk.StringVar(value=self.MODALIDADES[0]),
        }
        self._resultado = tk.StringVar()
        self._crear_formulario()
        self.poner_fecha_actual()

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Registrar ingreso", padding=10)
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

        ttk.Label(marco, text="Modalidad:").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Combobox(
            marco,
            textvariable=self._variables["modalidad"],
            values=self.MODALIDADES,
            state="readonly",
        ).grid(row=3, column=1, columnspan=2, sticky="w", pady=3)

        ttk.Button(marco, text="Registrar ingreso", command=self.registrar).grid(
            row=4, column=0, columnspan=3, sticky="e", pady=(8, 0)
        )
        self._entrada_patente.bind("<Return>", lambda evento: self.registrar())

        ttk.Label(self, textvariable=self._resultado, padding=(0, 10)).pack(anchor="w")

    def poner_fecha_actual(self):
        self._variables["fecha"].set(formatear_fecha(datetime.now()))

    def registrar(self):
        """Convierte la fecha, llama a registrar_ingreso y muestra el resultado."""
        modalidad = self._variables["modalidad"].get()

        try:
            fecha = parsear_fecha(self._variables["fecha"].get())
            ingreso = self._registrar_ingreso(self._variables["patente"].get(), fecha, modalidad)
        except ValueError as error:
            # Fecha mal escrita o regla de negocio: se muestra el mensaje
            # y NO se borra lo escrito para que el usuario lo corrija.
            messagebox.showerror("No se pudo registrar el ingreso", str(error))
            return
        except Exception:
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un problema al registrar el ingreso. Intenta nuevamente.",
            )
            return

        texto = (
            "Ingreso registrado correctamente.\n\n"
            f"Patente: {ingreso['patente']}\n"
            f"Fecha y hora: {formatear_fecha(ingreso['fecha_ingreso'])}\n"
            f"Modalidad: {ingreso['modalidad']}"
        )
        if ingreso["modalidad"] == "mensual":
            texto += "\n\nEl vehículo tiene suscripción mensual vigente, por eso se aplicó la modalidad mensual."

        self._resultado.set(
            f"Último ingreso: {ingreso['patente']} - {formatear_fecha(ingreso['fecha_ingreso'])} "
            f"- modalidad {ingreso['modalidad']}"
        )
        self._variables["patente"].set("")
        self.poner_fecha_actual()
        self._entrada_patente.focus_set()
        messagebox.showinfo("Ingreso registrado", texto)
