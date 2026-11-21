"""Punto de entrada de "Patente y Pago"."""

from tkinter import messagebox

from interfaz.ventana_principal import VentanaPrincipal
from persistencia.conexion import crear_tablas
from persistencia.vehiculos import registrar_vehiculo, listar_vehiculos


def main():
    try:
        crear_tablas()
    except ValueError as error:
        messagebox.showerror("No se pudo preparar la base de datos", str(error))
        return
    ventana = VentanaPrincipal(registrar_vehiculo, listar_vehiculos)
    ventana.mainloop()


if __name__ == "__main__":
    main()
