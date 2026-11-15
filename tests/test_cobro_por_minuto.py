import unittest
from datetime import datetime, timedelta

from dominio.cobro_por_minuto import CobroPorMinuto
from dominio.modalidad_cobro import ModalidadCobro


class TestCobroPorMinuto(unittest.TestCase):
    def setUp(self):
        self.cobro = CobroPorMinuto(50)
        self.ingreso = datetime(2026, 11, 14, 10, 0)

    def test_duraciones(self):
        casos = [
            (timedelta(0), 50),
            (timedelta(minutes=1), 50),
            (timedelta(minutes=1, seconds=10), 100),
            (timedelta(microseconds=1), 50),
            (timedelta(minutes=1, microseconds=1), 100),
            (timedelta(days=1), 72000),
        ]
        for duracion, esperado in casos:
            with self.subTest(duracion=duracion):
                importe = self.cobro.calcular_importe(
                    self.ingreso, self.ingreso + duracion
                )
                self.assertEqual(importe, esperado)
                self.assertIs(type(importe), int)

    def test_salida_anterior(self):
        with self.assertRaises(ValueError):
            self.cobro.calcular_importe(
                self.ingreso, self.ingreso - timedelta(seconds=1)
            )

    def test_tarifas_invalidas_al_crear_y_modificar(self):
        for valor, error in [
            (0, ValueError), (-50, ValueError), (1.5, TypeError),
            ("50", TypeError), (True, TypeError), (None, TypeError),
        ]:
            with self.subTest(tarifa=valor):
                with self.assertRaises(error):
                    CobroPorMinuto(valor)
                with self.assertRaises(error):
                    self.cobro.tarifa = valor
                self.assertEqual(self.cobro.tarifa, 50)

    def test_modificar_tarifa(self):
        self.cobro.tarifa = 100
        self.assertEqual(self.cobro.tarifa, 100)
        self.assertEqual(
            self.cobro.calcular_importe(self.ingreso, self.ingreso), 100
        )

    def test_fechas_invalidas(self):
        for ingreso, salida in [(None, self.ingreso), (self.ingreso, "2026-11-14")]:
            with self.subTest(ingreso=ingreso, salida=salida):
                with self.assertRaises(TypeError):
                    self.cobro.calcular_importe(ingreso, salida)

    def test_contrato_abstracto(self):
        with self.assertRaises(TypeError):
            ModalidadCobro()
        self.assertIsInstance(self.cobro, ModalidadCobro)


if __name__ == "__main__":
    unittest.main()
