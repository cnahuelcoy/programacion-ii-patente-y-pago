from tkinter import ttk, messagebox

from interfaz.formato import formatear_fecha


class PantallaPresentes(ttk.Frame):
    COLUMNAS = (
        ("patente", "Patente", 100),
        ("nombre_responsable", "Responsable", 220),
        ("fecha_ingreso", "Fecha de ingreso", 170),
        ("modalidad", "Modalidad", 100),
    )

    def __init__(self, master, listar_vehiculos_presentes):
        super().__init__(master, padding=10)
        self._listar_vehiculos_presentes = listar_vehiculos_presentes
        self._crear_tabla()
        self.actualizar_tabla()

    def _crear_tabla(self):
        marco = ttk.LabelFrame(self, text="Vehículos presentes", padding=10)
        marco.pack(fill="both", expand=True)

        barra = ttk.Frame(marco)
        barra.pack(fill="x", pady=(0, 8))
        self._boton_actualizar = ttk.Button(barra, text="Actualizar", command=self.actualizar_tabla)
        self._boton_actualizar.pack(side="right")

        contenedor = ttk.Frame(marco)
        contenedor.pack(fill="both", expand=True)

        self._tabla = ttk.Treeview(
            contenedor,
            columns=[campo for campo, _, _ in self.COLUMNAS],
            show="headings",
            selectmode="browse",
        )
        for campo, titulo, ancho in self.COLUMNAS:
            self._tabla.heading(campo, text=titulo)
            self._tabla.column(campo, width=ancho, anchor="w")

        scroll = ttk.Scrollbar(contenedor, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=scroll.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def actualizar_tabla(self):
        try:
            presentes = self._listar_vehiculos_presentes()
        except Exception:
            messagebox.showerror(
                "Error al consultar",
                "No se pudo cargar la lista de vehículos presentes.",
            )
            return

        self._tabla.delete(*self._tabla.get_children())
        for vehiculo in presentes:
            self._tabla.insert(
                "",
                "end",
                values=(
                    vehiculo["patente"],
                    vehiculo["nombre_responsable"],
                    formatear_fecha(vehiculo["fecha_ingreso"]),
                    vehiculo["modalidad"],
                ),
            )
