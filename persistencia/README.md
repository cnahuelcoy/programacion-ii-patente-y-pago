# Consultas de historiales

Funciones de `persistencia.consultas`:

```text
listar_historial_estadias(patente=None, fecha_desde=None, fecha_hasta=None, modalidad=None)
listar_pagos(patente=None, fecha_desde=None, fecha_hasta=None, modalidad=None)
```

Devuelven listas de diccionarios, de más reciente a más antiguo. La patente se
busca completa, sin distinguir mayúsculas ni espacios exteriores. Los filtros
vacíos se omiten. Las modalidades son `minuto`, `diaria` y `mensual`.

Las fechas deben ser `datetime` sin zona horaria. El período incluye `fecha_desde`
y excluye `fecha_hasta`. En estadías filtra por ingreso; en pagos, por `fecha_pago`.
Para un día completo, usa medianoche de ese día y medianoche del siguiente.

- Estadías: `estadia_id`, `vehiculo_id`, `patente`, `nombre_responsable`,
  `fecha_ingreso`, `fecha_salida`, `modalidad`, `suscripcion_id`, `pago_id`,
  `monto`, `fecha_pago` y `duracion_segundos`.
- Pagos: `pago_id`, `vehiculo_id`, `patente`, `nombre_responsable`, `fecha_pago`,
  `modalidad`, `monto`, `estadia_id` y `suscripcion_id`.

Las estadías activas tienen duración `None`. Una estadía sin pago tiene monto
`None`, salvo las cubiertas por suscripción, cuyo cobro adicional es cero.
Para recaudación se usa `listar_pagos`: cada mensualidad aparece una sola vez.
