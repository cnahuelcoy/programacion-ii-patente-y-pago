"""Punto de entrada de "Patente y Pago"."""

from interfaz.ventana_principal import VentanaPrincipal

# TODO(integración): reemplazar por las funciones reales, p. ej.
#   from persistencia.vehiculos import registrar_vehiculo, listar_vehiculos
#   from ... import registrar_ingreso, registrar_salida
# y llamar antes a crear_tablas() de persistencia.conexion.
from interfaz.servicios_demo import (
    registrar_vehiculo,
    listar_vehiculos,
    registrar_ingreso,
    registrar_salida,
)


def main():
    ventana = VentanaPrincipal(
        registrar_vehiculo, listar_vehiculos, registrar_ingreso, registrar_salida
    )
    ventana.mainloop()


if __name__ == "__main__":
    main()
