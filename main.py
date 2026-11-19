"""Punto de entrada de "Patente y Pago"."""

from interfaz.ventana_principal import VentanaPrincipal

# TODO(integración): cuando estén listas las funciones reales de persistencia,
# reemplazar la línea de abajo por su import, por ejemplo:
#   from persistencia.vehiculos import registrar_vehiculo, listar_vehiculos
# y llamar antes a crear_tablas() de persistencia.conexion.
from interfaz.servicios_demo import registrar_vehiculo, listar_vehiculos


def main():
    ventana = VentanaPrincipal(registrar_vehiculo, listar_vehiculos)
    ventana.mainloop()


if __name__ == "__main__":
    main()