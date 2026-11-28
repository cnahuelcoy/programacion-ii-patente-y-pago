import copy
import unittest
from datetime import datetime, timedelta, timezone

from reportes import (
    calcular_total_recaudado,
    calcular_totales_por_modalidad,
    filtrar_pagos,
    generar_reporte_recaudacion,
)


class TestReportesRecaudacion(unittest.TestCase):
    def setUp(self):
        self.desde = datetime(2026, 11, 1)
        self.hasta = datetime(2026, 12, 1)
        self.pagos = [
            {"pago_id": 1, "fecha_pago": self.desde, "modalidad": "minuto", "monto": 500},
            {"pago_id": 2, "fecha_pago": datetime(2026, 11, 15), "modalidad": "diaria", "monto": 5000},
            {"pago_id": 3, "fecha_pago": datetime(2026, 11, 20), "modalidad": "mensual", "monto": 30000},
            {"pago_id": 4, "fecha_pago": self.hasta, "modalidad": "minuto", "monto": 100},
            {"pago_id": 5, "fecha_pago": self.desde - timedelta(microseconds=1), "modalidad": "diaria", "monto": 10},
        ]

    def test_total_y_totales_por_modalidad(self):
        self.assertEqual(calcular_total_recaudado(self.pagos), 35610)
        self.assertEqual(
            calcular_totales_por_modalidad(self.pagos),
            {"total": 35610, "minuto": 600, "diaria": 5010, "mensual": 30000},
        )

    def test_fechas_incluyen_desde_y_excluyen_hasta(self):
        pagos = filtrar_pagos(self.pagos, self.desde, self.hasta)
        self.assertEqual([pago["pago_id"] for pago in pagos], [1, 2, 3])

    def test_filtra_por_modalidad_y_fecha_de_pago(self):
        reporte = generar_reporte_recaudacion(
            self.pagos, self.desde, self.hasta, " MENSUAL "
        )
        self.assertEqual(
            reporte, {"total": 30000, "minuto": 0, "diaria": 0, "mensual": 30000}
        )

    def test_pago_mensual_repetido_por_varias_estadias_se_cuenta_una_vez(self):
        pago_mensual = self.pagos[2]
        pagos = self.pagos[:3] + [dict(pago_mensual), dict(pago_mensual)]
        self.assertEqual(calcular_total_recaudado(pagos), 35500)
        self.assertEqual(calcular_totales_por_modalidad(pagos)["mensual"], 30000)

    def test_lista_vacia_devuelve_ceros(self):
        self.assertEqual(calcular_total_recaudado([]), 0)
        self.assertEqual(
            calcular_totales_por_modalidad([]),
            {"total": 0, "minuto": 0, "diaria": 0, "mensual": 0},
        )
        self.assertEqual(
            generar_reporte_recaudacion([], self.desde, self.hasta),
            {"total": 0, "minuto": 0, "diaria": 0, "mensual": 0},
        )

    def test_filtros_invalidos(self):
        casos = [
            (("2026-11-01", None, None), ValueError),
            ((datetime(2026, 11, 1, tzinfo=timezone.utc), None, None), ValueError),
            ((self.hasta, self.desde, None), ValueError),
            ((None, None, "semanal"), ValueError),
            ((None, None, 10), ValueError),
        ]
        for filtros, error in casos:
            with self.subTest(filtros=filtros):
                with self.assertRaises(error):
                    filtrar_pagos(self.pagos, *filtros)

    def test_no_modifica_los_pagos_recibidos(self):
        copia = copy.deepcopy(self.pagos)
        generar_reporte_recaudacion(self.pagos, self.desde, self.hasta)
        self.assertEqual(self.pagos, copia)


if __name__ == "__main__":
    unittest.main()
