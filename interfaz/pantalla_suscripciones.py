import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

from interfaz.formato import formatear_fecha, formatear_pesos, parsear_fecha


class PantallaSuscripciones(ttk.Frame):
    def __init__(self, master, contratar_suscripcion):
        super().__init__(master, padding=10)
        self._contratar_suscripcion = contratar_suscripcion
        self._variables = {
            "patente": tk.StringVar(),
            "fecha": tk.StringVar(),
        }
        self._resultado = tk.StringVar()
        self._crear_formulario()
        self.poner_fecha_actual()

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Contratar suscripción mensual", padding=10)
        marco.pack(fill="x")
        marco.columnconfigure(1, weight=1)

        ttk.Label(marco, text="Patente:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=3)
        self._entrada_patente = ttk.Entry(marco, textvariable=self._variables["patente"])
        self._entrada_patente.grid(row=0, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(marco, text="Fecha de inicio:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=3)
        ttk.Entry(marco, textvariable=self._variables["fecha"]).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Button(marco, text="Ahora", command=self.poner_fecha_actual).grid(row=1, column=2, padx=(5, 0))

        ttk.Label(marco, text="dd/mm/aaaa HH:MM:SS (se puede editar para pruebas)").grid(
            row=2, column=1, columnspan=2, sticky="w"
        )

        ttk.Button(marco, text="Contratar suscripción", command=self.contratar).grid(
            row=3, column=0, columnspan=3, sticky="e", pady=(8, 0)
        )
        self._entrada_patente.bind("<Return>", lambda evento: self.contratar())

        ttk.Label(self, textvariable=self._resultado, padding=(0, 10)).pack(anchor="w")

    def poner_fecha_actual(self):
        self._variables["fecha"].set(formatear_fecha(datetime.now()))

    def contratar(self):
        try:
            fecha = parsear_fecha(self._variables["fecha"].get())
            suscripcion = self._contratar_suscripcion(self._variables["patente"].get(), fecha)
        except ValueError as error:
            messagebox.showerror("No se pudo contratar la suscripción", str(error))
            return
        except Exception:
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un problema al contratar la suscripción. Intenta nuevamente.",
            )
            return

        inicio = formatear_fecha(suscripcion["fecha_inicio"])
        termino = formatear_fecha(suscripcion["fecha_termino"])
        monto = formatear_pesos(suscripcion["monto"])
        texto = (
            "Suscripción contratada correctamente.\n\n"
            f"Patente: {suscripcion['patente']}\n"
            f"Inicio: {inicio}\n"
            f"Término: {termino}\n"
            f"Monto pagado: {monto}\n"
            f"Pago registrado el: {formatear_fecha(suscripcion['fecha_pago'])}"
        )

        self._resultado.set(
            f"Última suscripción: {suscripcion['patente']} - {inicio} a {termino} - monto {monto}"
        )
        self._variables["patente"].set("")
        self.poner_fecha_actual()
        self._entrada_patente.focus_set()
        messagebox.showinfo("Suscripción contratada", texto)
