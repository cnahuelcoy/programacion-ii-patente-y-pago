# Interfaz Tkinter

Las pantallas no acceden a la base de datos: reciben funciones y las llaman. Si una función rechaza los datos, debe lanzar `ValueError` con un mensaje claro; la pantalla lo muestra y conserva lo escrito.

## Pestañas y funciones

| Pestaña | Función recibida |
|---|---|
| Vehículos | `registrar_vehiculo(patente, nombre_responsable, telefono, correo)`, `listar_vehiculos()` |
| Ingresos | `registrar_ingreso(patente, fecha_ingreso, modalidad)` |
| Salidas | `registrar_salida(patente, fecha_salida)` |
| Suscripciones | `contratar_suscripcion(patente, fecha_inicio)` |
| Presentes | `listar_vehiculos_presentes()` |

Las fechas llegan como `datetime` sin zona horaria. Las pestañas Suscripciones y Presentes solo aparecen si `VentanaPrincipal` recibe sus funciones; sin ellas la ventana funciona como antes. Si no recibe `registrar_salida`, la pestaña Salidas queda deshabilitada.

## Retornos

- `contratar_suscripcion`: `patente`, `fecha_inicio`, `fecha_termino`, `monto`, `fecha_pago`.
- `listar_vehiculos_presentes`: lista con `estadia_id`, `vehiculo_id`, `patente`, `nombre_responsable`, `fecha_ingreso`, `modalidad`, `suscripcion_id`.

## Probar con datos de ejemplo

```
python -c "from interfaz.ventana_principal import VentanaPrincipal; from interfaz import servicios_demo as s; VentanaPrincipal(s.registrar_vehiculo, s.listar_vehiculos, s.registrar_ingreso, s.registrar_salida, s.contratar_suscripcion, s.listar_vehiculos_presentes).mainloop()"
```

`servicios_demo.py` guarda todo en memoria y sus tarifas son datos de prueba.

## Pruebas

```
python -m unittest tests.test_interfaz_vehiculos tests.test_interfaz_ingresos_salidas tests.test_interfaz_suscripciones_presentes
```
