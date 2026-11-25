# Patente y Pago

Proyecto de Programación II para administrar un estacionamiento y sus cobros por minuto, día y suscripción mensual. Desarrollado con Python, Tkinter, SQLAlchemy y SQLite.

## Integrantes y tareas

| Integrante | GitHub | Correo institucional |
| --- | --- | --- |
| Gonzalo Albornoz | @galbornoz-uct | galbornoz2026@alu.uct.cl |
| Carlos Nahuelcoy | @cnahuelcoy | cnahuelcoy2026@alu.uct.cl |
| Rodrigo Sevilla | @rsevilla1 | rsevilla2026@alu.uct.cl |

- Gonzalo: cálculos de cobro, vigencia mensual y reportes.
- Carlos: base de datos, registros, pagos y consultas.
- Rodrigo: pantallas, formularios y conexión con el sistema.

Entre los tres probamos el programa y preparamos el informe, UML y presentación.

## Instalación y ejecución

Probado con Python 3.12. Se necesita Tkinter. Desde la carpeta del proyecto, en Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

La aplicación crea `estacionamiento.db` automáticamente y conserva los datos al cerrarse.

## Ejemplo de uso

En Vehículos, registra `ABCD12`, el nombre del responsable y un teléfono o correo. En Ingresos, escribe esa patente, revisa la fecha y elige minuto o diaria. Al confirmar, el ingreso queda guardado en SQLite.

## Tarifas de prueba

| Modalidad | Valor |
| --- | --- |
| Minuto | $50 por minuto iniciado, mínimo uno |
| Diaria | $5.000 por bloque iniciado de 24 horas, mínimo uno |
| Mensual | $30.000 por 30 días; las estadías cubiertas no tienen cobro adicional |

Son valores de la demostración. Falta confirmar las tarifas definitivas y conectarlas al flujo real.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan datos temporales. Para probar todas las pantallas con datos en memoria, consulta [interfaz/README.md](interfaz/README.md).

## Estado actual

Vehículos e ingresos funcionan con SQLite. Falta conectar salidas, suscripciones y vehículos presentes, y completar historial, filtros, recaudación y datos de ejemplo persistentes.

Para la entrega también quedan el informe con evidencias, el UML actualizado y el ZIP solicitado en Blackboard.
