import unittest
from datetime import datetime, timedelta

from dominio.cobro_diario import CobroDiario
from dominio.cobro_mensual import CobroMensual
from dominio.cobro_por_minuto import CobroPorMinuto
from dominio.modalidad_cobro import ModalidadCobro


class TestCobroDiario(unittest.TestCase):
    def setUp(self):
        self.cobro = CobroDiario(1000)
        self.ingreso = datetime(2026, 11, 14, 10, 0)

    def test_cobra_bloques_de_24_horas_con_minimo_de_un_dia(self):
        casos = [
            (timedelta(0), 1000),
            (timedelta(days=1), 1000),
            (timedelta(days=1, minutes=1), 2000),
        ]
        for duracion, esperado in casos:
            with self.subTest(duracion=duracion):
                salida = self.ingreso + duracion
                self.assertEqual(
                    self.cobro.calcular_importe(self.ingreso, salida), esperado
                )

    def test_rechaza_salida_anterior_y_fechas_invalidas(self):
        with self.assertRaises(ValueError):
            self.cobro.calcular_importe(
                self.ingreso, self.ingreso - timedelta(seconds=1)
            )
        with self.assertRaises(TypeError):
            self.cobro.calcular_importe(None, self.ingreso)

    def test_tarifa_privada_y_validada_al_crear_y_modificar(self):
        self.assertTrue(hasattr(self.cobro, "_CobroDiario__tarifa"))
        self.assertFalse(hasattr(self.cobro, "__tarifa"))
        self.assertEqual(self.cobro.tarifa, 1000)
        for valor, error in [
            (0, ValueError), (-1, ValueError), (1.5, TypeError), (True, TypeError)
        ]:
            with self.subTest(tarifa=valor):
                with self.assertRaises(error):
                    CobroDiario(valor)
                with self.assertRaises(error):
                    self.cobro.tarifa = valor
                self.assertEqual(self.cobro.tarifa, 1000)


class TestCobroMensual(unittest.TestCase):
    def setUp(self):
        self.cobro = CobroMensual(30000)
        self.ingreso = datetime(2026, 11, 14, 10, 0)

    def test_contratacion_y_estadia_cubierta_son_cobros_distintos(self):
        self.assertEqual(self.cobro.calcular_importe_contratacion(), 30000)
        for duracion in (timedelta(0), timedelta(days=30), timedelta(days=35)):
            with self.subTest(duracion=duracion):
                salida = self.ingreso + duracion
                importe_estadia = self.cobro.calcular_importe(self.ingreso, salida)
                self.assertEqual(importe_estadia, 0)
                self.assertIs(type(importe_estadia), int)
        # Finalizar estadías cubiertas no modifica el precio de contratar.
        self.assertEqual(self.cobro.calcular_importe_contratacion(), 30000)

    def test_rechaza_salida_anterior_y_fechas_invalidas(self):
        with self.assertRaises(ValueError):
            self.cobro.calcular_importe(
                self.ingreso, self.ingreso - timedelta(seconds=1)
            )
        with self.assertRaises(TypeError):
            self.cobro.calcular_importe(self.ingreso, "2026-11-14")

    def test_tarifa_privada_y_validada_al_crear_y_modificar(self):
        self.assertTrue(hasattr(self.cobro, "_CobroMensual__tarifa"))
        self.assertFalse(hasattr(self.cobro, "__tarifa"))
        self.assertEqual(self.cobro.tarifa, 30000)
        for valor, error in [
            (0, ValueError), (-1, ValueError), (1.5, TypeError), (True, TypeError)
        ]:
            with self.subTest(tarifa=valor):
                with self.assertRaises(error):
                    CobroMensual(valor)
                with self.assertRaises(error):
                    self.cobro.tarifa = valor
                self.assertEqual(self.cobro.tarifa, 30000)


class TestPolimorfismo(unittest.TestCase):
    def test_modalidades_comparten_el_metodo_de_calculo(self):
        ingreso = datetime(2026, 11, 14, 10, 0)
        salida = ingreso + timedelta(days=1, minutes=1)
        modalidades: list[ModalidadCobro] = [
            CobroPorMinuto(50),
            CobroDiario(1000),
            CobroMensual(30000),
        ]
        importes = [
            modalidad.calcular_importe(ingreso, salida)
            for modalidad in modalidades
        ]
        self.assertEqual(importes, [72050, 2000, 0])


if __name__ == "__main__":
    unittest.main()
