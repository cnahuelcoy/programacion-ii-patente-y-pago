# Patente y Pago

Proyecto de Programación II. Aplicación de escritorio para registrar entradas y salidas de vehículos, gestionar cobros por minuto, por día
y por suscripción mensual, y consultar la recaudación del estacionamiento.

## Integrantes

| Nombre | Usuario de GitHub | Correo Institucional |
| --- | --- | --- |
| Gonzalo Albornoz | @galbornoz-uct | galbornoz2026@alu.uct.cl |
| Carlos Nahuelcoy | @cnahuelcoy | cnahuelcoy2026@alu.uct.cl |
| Rodrigo Sevilla | @rsevilla1 | rsevilla2026@alu.uct.cl |

## Tecnologías

Python, Tkinter, SQLAlchemy y SQLite.

Al ejecutar `python main.py`, las pantallas de vehículos e ingresos guardan los
datos en SQLite. La pestaña Salidas queda deshabilitada hasta conectar su función
real. Las pruebas de la interfaz siguen usando datos de ejemplo en memoria.

## Distribución de tareas

- Gonzalo Albornoz: calcula los cobros, revisa la vigencia de las suscripciones y genera los reportes de recaudación.
- Carlos Nahuelcoy: crea la base de datos y se encarga de guardar y consultar los vehículos, estadías, suscripciones y pagos.
- Rodrigo Sevilla: crea las ventanas y formularios en Tkinter y los conecta con el resto del sistema.

Entre los tres probamos el programa y preparamos el informe, los diagramas y la presentación. Si alguien necesita ayuda con una tarea, puede pedírsela al resto del equipo.

## Parte 3 de Carlos: salidas, suscripciones y pagos

Registro de salidas, suscripciones de 30 días y sus pagos, con validaciones y
reversión ante errores. Incluye la consulta de vehículos presentes. Recibe los
montos ya calculados; la conexión con las nuevas pantallas queda pendiente.

## Primer PR: cobro por minuto

La primera etapa implementó la lógica de cobro por minuto en `dominio/`.
No necesita instalar dependencias externas, abrir Tkinter ni conectar SQLite.
Requiere Python 3.

### Ejemplo de uso

La tarifa se recibe al construir el objeto: debe ser un entero positivo en
pesos chilenos por minuto. Los $50 del ejemplo son una tarifa de prueba,
no una tarifa fija impuesta por el sistema.

```python
from datetime import datetime
from dominio.cobro_por_minuto import CobroPorMinuto

cobro = CobroPorMinuto(tarifa=50)
ingreso = datetime(2026, 11, 14, 10, 0, 0)
salida = datetime(2026, 11, 14, 10, 1, 10)
print(cobro.calcular_importe(ingreso, salida))  # 100 pesos
```

Las fechas deben ser objetos `datetime` comparables; para el uso inicial,
se emplean fechas sin zona horaria como en el ejemplo.

### Cómo funciona y cómo explicarlo

- `ModalidadCobro` hereda de `ABC` y declara `calcular_importe` con
  `@abstractmethod`: no se puede instanciar y obliga a las clases concretas
  a implementar ese método.
- `CobroPorMinuto` hereda ese contrato y define la fórmula del cobro.
  Las futuras modalidades podrán usarse mediante el mismo método.
- `__tarifa` es el atributo privado. La propiedad `tarifa` permite consultarlo
  y modificarlo. Su setter rechaza valores no enteros, booleanos, cero y
  negativos. El constructor también pasa por el setter.
- Se valida que las fechas sean `datetime` y que la salida no sea anterior
  al ingreso. Los tipos incorrectos producen `TypeError`; los valores
  inválidos producen `ValueError`.
- Al restar las fechas se obtiene un `timedelta`. `divmod` lo divide por
  un minuto y entrega los minutos completos y el resto. Si sobra tiempo,
  se suma un minuto; `max(1, minutos)` asegura el mínimo de uno.
  Esto evita perder precisión por convertir la duración a decimales.
- El importe es minutos cobrados por tarifa, ambos enteros. El cálculo
  usa las fechas recibidas y la tarifa configurada; no consulta el reloj
  ni modifica datos externos.

### Verificación

Desde la raíz del repositorio:

```bash
python -m unittest discover -s tests -v
```

En Windows también se puede usar `py -m unittest discover -s tests -v`.

Con una tarifa de $50 por minuto:

| Duración | Resultado esperado |
| --- | --- |
| Cero | $50 |
| Exactamente un minuto | $50 |
| Un minuto y diez segundos | $100 |
| Salida anterior al ingreso | `ValueError` |

Las pruebas también comprueban fracciones de microsegundo, una estadía
de 24 horas, tarifas inválidas, cambios de tarifa, tipos de fechas y
la imposibilidad de instanciar la clase abstracta.


## Segundo PR: modalidades diaria y mensual

`CobroDiario` y `CobroMensual` heredan de `ModalidadCobro` e implementan
el mismo método `calcular_importe(ingreso, salida)`. Así, quien solicita un
cálculo puede usar cualquier modalidad mediante el mismo contrato, y cada
clase aplica su propia fórmula.

- `CobroDiario(tarifa)` cobra la tarifa por cada bloque iniciado de 24 horas.
  Una estadía de cero tiempo cuesta un día; 24 horas cuestan un día; 24 horas
y un minuto cuestan dos días.
- `CobroMensual(tarifa)` representa una estadía ya cubierta: su método
  `calcular_importe` valida las fechas y devuelve $0. La vigencia de la
  suscripción se resolverá en la parte 3.
- `calcular_importe_contratacion()` en `CobroMensual` devuelve la tarifa
  mensual a pagar al contratar. Este pago es independiente de terminar una
  estadía cubierta.
- En ambas clases, `__tarifa` es privado y la propiedad `tarifa` permite
  consultarlo y cambiarlo. El setter acepta solo enteros positivos en pesos
  chilenos; rechaza booleanos, decimales, cero y negativos.
- Las modalidades reciben los `datetime` como argumentos. Rechazan tipos
  incorrectos y una salida anterior al ingreso.

Ejemplo:

```python
from datetime import datetime, timedelta
from dominio.cobro_diario import CobroDiario
from dominio.cobro_mensual import CobroMensual

ingreso = datetime(2026, 11, 14, 10, 0)
diario = CobroDiario(tarifa=5000)
print(diario.calcular_importe(ingreso, ingreso + timedelta(hours=24, minutes=1)))
# 10000: se cobra el segundo bloque diario iniciado.

mensual = CobroMensual(tarifa=30000)
print(mensual.calcular_importe_contratacion())  # 30000: pago de la suscripción.
print(mensual.calcular_importe(ingreso, ingreso + timedelta(days=1)))  # 0: estadía cubierta.
```

### Verificar las modalidades

Desde la raíz del repositorio, ejecuta las pruebas de todos los PR:

```bash
python -m unittest discover -s tests -v
```

En Windows también se puede ejecutar `py -m unittest discover -s tests -v`.
Las pruebas de `CobroDiario` cubren cero, 24 horas, 24 horas y un minuto,
tarifas inválidas, tipos de fecha y salida anterior al ingreso. Las de
`CobroMensual` comprueban que la contratación cuesta la tarifa configurada,
que finalizar estadías cubiertas cuesta cero y que las validaciones de tarifa
y fechas se aplican. También se comprueba que las clases concretas se usan
mediante el mismo método polimórfico.
