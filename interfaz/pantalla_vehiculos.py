"""Pantalla de vehículos: formulario de registro y tabla de consulta.

Esta clase solo maneja la interfaz. No guarda datos ni valida reglas de
negocio: recibe dos funciones y delega en ellas.

    registrar_vehiculo(patente, nombre_responsable, telefono, correo) -> dict
    listar_vehiculos() -> list[dict]

Los diccionarios tienen los campos: id, patente, nombre_responsable,
telefono y correo. Si registrar_vehiculo rechaza los datos, debe lanzar
ValueError con un mensaje comprensible; la pantalla lo muestra tal cual.
"""

import tkinter as tk
from tkinter import ttk, messagebox


class PantallaVehiculos(ttk.Frame):
    # (campo del diccionario, texto del encabezado, ancho en píxeles)
    COLUMNAS = (
        ("id", "ID", 50),
        ("patente", "Patente", 100),
        ("nombre_responsable", "Responsable", 200),
        ("telefono", "Teléfono", 120),
        ("correo", "Correo", 220),
    )

    # (campo del formulario, etiqueta que ve el usuario)
    CAMPOS = (
        ("patente", "Patente:"),
        ("nombre_responsable", "Nombre del responsable:"),
        ("telefono", "Teléfono:"),
        ("correo", "Correo:"),
    )

    def __init__(self, master, registrar_vehiculo, listar_vehiculos):
        super().__init__(master, padding=10)
        self._registrar_vehiculo = registrar_vehiculo
        self._listar_vehiculos = listar_vehiculos
        self._variables = {campo: tk.StringVar() for campo, _ in self.CAMPOS}
        self._entradas = {}

        self._crear_formulario()
        self._crear_tabla()
        self.actualizar_tabla()

    # ---------- Construcción de la pantalla ----------

    def _crear_formulario(self):
        marco = ttk.LabelFrame(self, text="Registrar vehículo", padding=10)
        marco.pack(fill="x")
        marco.columnconfigure(1, weight=1)

        for fila, (campo, etiqueta) in enumerate(self.CAMPOS):
            ttk.Label(marco, text=etiqueta).grid(
                row=fila, column=0, sticky="w", padx=(0, 10), pady=3
            )
            entrada = ttk.Entry(marco, textvariable=self._variables[campo])
            entrada.grid(row=fila, column=1, sticky="ew", pady=3)
            entrada.bind("<Return>", lambda evento: self.registrar())
            self._entradas[campo] = entrada

        botones = ttk.Frame(marco)
        botones.grid(row=len(self.CAMPOS), column=0, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(botones, text="Limpiar", command=self.limpiar_formulario).pack(side="left", padx=5)
        ttk.Button(botones, text="Registrar", command=self.registrar).pack(side="left")

    def _crear_tabla(self):
        marco = ttk.LabelFrame(self, text="Vehículos registrados", padding=10)
        marco.pack(fill="both", expand=True, pady=(10, 0))

        self._tabla = ttk.Treeview(
            marco,
            columns=[campo for campo, _, _ in self.COLUMNAS],
            show="headings",
            selectmode="browse",
        )
        for campo, titulo, ancho in self.COLUMNAS:
            self._tabla.heading(campo, text=titulo)
            self._tabla.column(campo, width=ancho, anchor="w")

        scroll = ttk.Scrollbar(marco, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---------- Acciones ----------

    def registrar(self):
        """Envía el formulario a registrar_vehiculo y actualiza la tabla."""
        datos = {campo: var.get() for campo, var in self._variables.items()}

        try:
            vehiculo = self._registrar_vehiculo(
                datos["patente"],
                datos["nombre_responsable"],
                datos["telefono"],
                datos["correo"],
            )
        except ValueError as error:
            # Error de validación: el mensaje viene de la lógica de negocio.
            messagebox.showerror("No se pudo registrar", str(error))
            return
        except Exception:
            # Cualquier otro fallo: se avisa sin cerrar la aplicación.
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un problema al registrar el vehículo. Intenta nuevamente.",
            )
            return

        self.limpiar_formulario()
        self.actualizar_tabla()
        messagebox.showinfo(
            "Vehículo registrado",
            f"El vehículo {vehiculo['patente']} fue registrado correctamente.",
        )

    def actualizar_tabla(self):
        """Vuelve a cargar la tabla con lo que devuelve listar_vehiculos."""
        try:
            vehiculos = self._listar_vehiculos()
        except Exception:
            messagebox.showerror(
                "Error al consultar",
                "No se pudo cargar la lista de vehículos.",
            )
            return

        self._tabla.delete(*self._tabla.get_children())
        for vehiculo in vehiculos:
            fila = [vehiculo[campo] for campo, _, _ in self.COLUMNAS]
            self._tabla.insert("", "end", values=fila)

    def limpiar_formulario(self):
        for variable in self._variables.values():
            variable.set("")
        self._entradas["patente"].focus_set()
