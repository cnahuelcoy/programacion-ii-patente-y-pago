import unittest
from datetime import datetime, timedelta, timezone

from dominio.suscripciones import (
    calcular_termino_suscripcion,
    estadia_cubierta,
    hay_superposicion,
    suscripcion_vigente,
)


class TestCalculoTermino(unittest.TestCase):
    def test_agrega_treinta_dias_consecutivos_y_conserva_la_hora(self):
        inicio = datetime(2024, 1, 31, 23, 45, 12, 345678)
        self.assertEqual(
            calcular_termino_suscripcion(inicio),
            inicio + timedelta(days=30),
        )

    def test_rechaza_tipo_incorrecto_y_datetime_con_zona(self):
        for inicio in ("2024-01-01", datetime(2024, 1, 1, tzinfo=timezone.utc)):
            with self.subTest(inicio=inicio):
                with self.assertRaises((TypeError, ValueError)):
                    calcular_termino_suscripcion(inicio)


class TestVigencia(unittest.TestCase):
    def setUp(self):
        self.inicio = datetime(2026, 1, 1, 12)
        self.termino = calcular_termino_suscripcion(self.inicio)

    def test_incluye_inicio_y_excluye_termino(self):
        self.assertTrue(suscripcion_vigente(self.inicio, self.termino, self.inicio))
        self.assertTrue(
            suscripcion_vigente(
                self.inicio, self.termino, self.termino - timedelta(microseconds=1)
            )
        )
        self.assertFalse(
            suscripcion_vigente(self.inicio, self.termino, self.termino)
        )
        self.assertFalse(
            suscripcion_vigente(
                self.inicio, self.termino, self.termino + timedelta(microseconds=1)
            )
        )

    def test_estadia_cubierta_al_ingreso_sigue_cubierta_al_vencer(self):
        ingreso = self.termino - timedelta(hours=1)
        salida = self.termino + timedelta(hours=1)
        self.assertTrue(
            estadia_cubierta(self.inicio, self.termino, ingreso, salida)
        )

    def test_rechaza_periodo_invalido_y_fechas_invalidas(self):
        with self.assertRaises(ValueError):
            suscripcion_vigente(self.termino, self.inicio, self.inicio)
        with self.assertRaises(ValueError):
            suscripcion_vigente(self.inicio, self.inicio, self.inicio)
        with self.assertRaises(TypeError):
            suscripcion_vigente(self.inicio, self.termino, None)
        with self.assertRaises(ValueError):
            suscripcion_vigente(
                self.inicio,
                self.termino,
                datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        with self.assertRaises(ValueError):
            estadia_cubierta(
                self.inicio, self.termino, self.termino, self.inicio
            )


class TestSuperposicion(unittest.TestCase):
    def setUp(self):
        self.inicio = datetime(2026, 1, 1)
        self.termino = self.inicio + timedelta(days=30)

    def test_detecta_superposicion_parcial_y_contenida(self):
        self.assertTrue(
            hay_superposicion(
                self.inicio,
                self.termino,
                self.inicio + timedelta(days=29),
                self.termino + timedelta(days=30),
            )
        )
        self.assertTrue(
            hay_superposicion(
                self.inicio,
                self.termino,
                self.inicio + timedelta(days=5),
                self.inicio + timedelta(days=10),
            )
        )

    def test_permite_periodos_consecutivos_y_separados(self):
        self.assertFalse(
            hay_superposicion(
                self.inicio,
                self.termino,
                self.termino,
                self.termino + timedelta(days=30),
            )
        )
        self.assertFalse(
            hay_superposicion(
                self.inicio,
                self.termino,
                self.termino + timedelta(seconds=1),
                self.termino + timedelta(days=30),
            )
        )

    def test_rechaza_periodos_invalidos_y_fechas_con_zona(self):
        with self.assertRaises(ValueError):
            hay_superposicion(self.inicio, self.inicio, self.inicio, self.termino)
        with self.assertRaises(ValueError):
            hay_superposicion(
                self.inicio,
                self.termino,
                datetime(2026, 2, 1, tzinfo=timezone.utc),
                self.termino,
            )


if __name__ == "__main__":
    unittest.main()
