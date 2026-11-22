"""Pruebas de las pantallas de ingresos y salidas (usan funciones en memoria).

Ejecutar desde la raíz del proyecto:
    python -m unittest tests.test_interfaz_ingresos_salidas -v
Los cuadros de mensaje se reemplazan por simulacros para no abrir ventanas.
"""

import tkinter as tk
import unittest
from datetime import datetime
from unittest.mock import patch

from interfaz import servicios_demo
from interfaz.formato import formatear_fecha, formatear_pesos, parsear_fecha
from interfaz.pantalla_ingresos import PantallaIngresos
from interfaz.pantalla_salidas import PantallaSalidas
from interfaz.ventana_principal import VentanaPrincipal


class PruebasFormato(unittest.TestCase):
    def test_parsea_con_y_sin_segundos(self):
        self.assertEqual(parsear_fecha("15/11/2026 13:30:10"), datetime(2026, 11, 15, 13, 30, 10))
        self.assertEqual(parsear_fecha("15/11/2026 13:30"), datetime(2026, 11, 15, 13, 30))

    def test_fecha_es_sin_zona_horaria(self):
        self.assertIsNone(parsear_fecha("15/11/2026 13:30").tzinfo)

    def test_fechas_incorrectas_lanzan_value_error(self):
        for texto in ("", "   ", "hola", "31/02/2026 10:00", "2026-11-15 10:00", "15/11/2026"):
            with self.subTest(texto=texto):
                with self.assertRaises(ValueError):
                    parsear_fecha(texto)

    def test_formatear_fecha_y_pesos(self):
        self.assertEqual(formatear_fecha(datetime(2026, 11, 15, 9, 5, 7)), "15/11/2026 09:05:07")
        self.assertEqual(formatear_pesos(0), "$0")
        self.assertEqual(formatear_pesos(5000), "$5.000")
        self.assertEqual(formatear_pesos(1234567), "$1.234.567")


class BasePantallas(unittest.TestCase):
    def setUp(self):
        servicios_demo.reiniciar_demo()
        servicios_demo.registrar_vehiculo("ABCD12", "Ana", "", "")
        servicios_demo.registrar_vehiculo("MENS01", "Mario", "", "")
        self.raiz = tk.Tk()
        self.raiz.withdraw()
        self._parches = [
            patch("tkinter.messagebox.showinfo"),
            patch("tkinter.messagebox.showerror"),
        ]
        self.info, self.error = [p.start() for p in self._parches]

    def tearDown(self):
        for p in self._parches:
            p.stop()
        self.raiz.destroy()

    def texto_mensaje(self, simulacro):
        return simulacro.call_args.args[1]


class PruebasIngresos(BasePantallas):
    def _pantalla(self, funcion=None):
        return PantallaIngresos(self.raiz, funcion or servicios_demo.registrar_ingreso)

    def _llenar(self, pantalla, patente, fecha, modalidad="minuto"):
        pantalla._variables["patente"].set(patente)
        pantalla._variables["fecha"].set(fecha)
        pantalla._variables["modalidad"].set(modalidad)

    def test_ingreso_correcto_envia_datetime_sin_zona_y_confirma(self):
        llamadas = []

        def espia(patente, fecha, modalidad):
            llamadas.append((patente, fecha, modalidad))
            return servicios_demo.registrar_ingreso(patente, fecha, modalidad)

        p = self._pantalla(espia)
        self._llenar(p, "abcd12", "15/11/2026 10:00:00", "diaria")
        p.registrar()

        self.assertEqual(llamadas, [("abcd12", datetime(2026, 11, 15, 10, 0, 0), "diaria")])
        self.assertIsNone(llamadas[0][1].tzinfo)
        self.info.assert_called_once()
        self.error.assert_not_called()
        mensaje = self.texto_mensaje(self.info)
        self.assertIn("ABCD12", mensaje)
        self.assertIn("diaria", mensaje)
        self.assertEqual(p._variables["patente"].get(), "")

    def test_muestra_modalidad_devuelta_mensual(self):
        p = self._pantalla()
        self._llenar(p, "MENS01", "15/11/2026 10:00", "minuto")
        p.registrar()
        mensaje = self.texto_mensaje(self.info)
        self.assertIn("mensual", mensaje)
        self.assertNotIn("Modalidad: minuto", mensaje)

    def test_fecha_incorrecta_no_llama_a_la_funcion_y_conserva_lo_escrito(self):
        llamadas = []
        p = self._pantalla(lambda *args: llamadas.append(args))
        self._llenar(p, "ABCD12", "ayer a las diez", "diaria")
        p.registrar()

        self.assertEqual(llamadas, [])
        self.error.assert_called_once()
        self.assertIn("formato", self.texto_mensaje(self.error))
        self.info.assert_not_called()
        self.assertEqual(p._variables["patente"].get(), "ABCD12")
        self.assertEqual(p._variables["fecha"].get(), "ayer a las diez")
        self.assertEqual(p._variables["modalidad"].get(), "diaria")

    def test_fecha_vacia_muestra_error(self):
        p = self._pantalla()
        self._llenar(p, "ABCD12", "")
        p.registrar()
        self.assertIn("fecha", self.texto_mensaje(self.error).lower())

    def test_patente_vacia_muestra_error_y_conserva_fecha(self):
        p = self._pantalla()
        self._llenar(p, "  ", "15/11/2026 10:00", "diaria")
        p.registrar()
        self.assertIn("patente", self.texto_mensaje(self.error).lower())
        self.assertEqual(p._variables["fecha"].get(), "15/11/2026 10:00")

    def test_vehiculo_no_registrado_muestra_error(self):
        p = self._pantalla()
        self._llenar(p, "ZZZZ99", "15/11/2026 10:00")
        p.registrar()
        self.assertIn("no está registrado", self.texto_mensaje(self.error))
        self.assertEqual(p._variables["patente"].get(), "ZZZZ99")

    def test_no_permite_dos_ingresos_simultaneos(self):
        p = self._pantalla()
        self._llenar(p, "ABCD12", "15/11/2026 10:00")
        p.registrar()
        self.info.reset_mock()

        self._llenar(p, "ABCD12", "15/11/2026 11:00")
        p.registrar()
        self.assertIn("estadía activa", self.texto_mensaje(self.error))
        self.info.assert_not_called()
        self.assertEqual(p._variables["patente"].get(), "ABCD12")

    def test_error_inesperado_no_cierra_la_aplicacion(self):
        def falla(*args):
            raise RuntimeError("fallo interno")

        p = self._pantalla(falla)
        self._llenar(p, "ABCD12", "15/11/2026 10:00", "diaria")
        p.registrar()

        self.error.assert_called_once()
        self.assertNotIn("fallo interno", self.texto_mensaje(self.error))
        self.assertTrue(p.winfo_exists())
        self.assertEqual(p._variables["patente"].get(), "ABCD12")


class PruebasSalidas(BasePantallas):
    def _pantalla(self, funcion=None):
        return PantallaSalidas(self.raiz, funcion or servicios_demo.registrar_salida)

    def _ingresar(self, patente, fecha, modalidad):
        servicios_demo.registrar_ingreso(patente, fecha, modalidad)

    def _salir(self, pantalla, patente, fecha):
        pantalla._variables["patente"].set(patente)
        pantalla._variables["fecha"].set(fecha)
        pantalla.registrar()

    def test_ingreso_y_salida_correctos(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "minuto")
        p = self._pantalla()
        self._salir(p, "abcd12", "15/11/2026 10:30:00")

        self.info.assert_called_once()
        mensaje = self.texto_mensaje(self.info)
        self.assertIn("ABCD12", mensaje)
        self.assertIn("$1.500", mensaje)  # 30 min x $50 (tarifa de prueba)
        self.assertEqual(p._variables["patente"].get(), "")

    def test_1_minuto_10_segundos_se_cobra_como_2_minutos(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "minuto")
        p = self._pantalla()
        self._salir(p, "ABCD12", "15/11/2026 10:01:10")
        self.assertIn("$100", self.texto_mensaje(self.info))  # 2 min x $50

    def test_diaria_24_horas_exactas_es_un_dia(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "diaria")
        p = self._pantalla()
        self._salir(p, "ABCD12", "16/11/2026 10:00:00")
        self.assertIn("$5.000", self.texto_mensaje(self.info))

    def test_diaria_24_horas_y_1_minuto_son_dos_dias(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "diaria")
        p = self._pantalla()
        self._salir(p, "ABCD12", "16/11/2026 10:01:00")
        self.assertIn("$10.000", self.texto_mensaje(self.info))

    def test_mensual_muestra_monto_cero(self):
        self._ingresar("MENS01", datetime(2026, 11, 15, 10, 0, 0), "minuto")
        p = self._pantalla()
        self._salir(p, "MENS01", "20/11/2026 10:00:00")
        mensaje = self.texto_mensaje(self.info)
        self.assertIn("mensual", mensaje)
        self.assertIn("$0", mensaje)

    def test_salida_anterior_al_ingreso_muestra_error_y_conserva_lo_escrito(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "minuto")
        p = self._pantalla()
        self._salir(p, "ABCD12", "15/11/2026 09:00:00")

        self.assertIn("anterior", self.texto_mensaje(self.error))
        self.info.assert_not_called()
        self.assertEqual(p._variables["patente"].get(), "ABCD12")
        self.assertEqual(p._variables["fecha"].get(), "15/11/2026 09:00:00")

    def test_la_estadia_sigue_activa_tras_un_error(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "minuto")
        p = self._pantalla()
        self._salir(p, "ABCD12", "15/11/2026 09:00:00")  # falla
        self.info.reset_mock()
        self._salir(p, "ABCD12", "15/11/2026 10:05:00")  # corrige
        self.info.assert_called_once()
        self.assertIn("$250", self.texto_mensaje(self.info))

    def test_sin_estadia_activa_muestra_error(self):
        p = self._pantalla()
        self._salir(p, "ABCD12", "15/11/2026 10:00:00")
        self.assertIn("no tiene una estadía activa", self.texto_mensaje(self.error))

    def test_no_se_puede_salir_dos_veces(self):
        self._ingresar("ABCD12", datetime(2026, 11, 15, 10, 0, 0), "minuto")
        p = self._pantalla()
        self._salir(p, "ABCD12", "15/11/2026 10:10:00")
        self._salir(p, "ABCD12", "15/11/2026 10:20:00")
        self.error.assert_called_once()

    def test_fecha_incorrecta_no_llama_a_la_funcion(self):
        llamadas = []
        p = self._pantalla(lambda *args: llamadas.append(args))
        self._salir(p, "ABCD12", "31/02/2026 10:00")
        self.assertEqual(llamadas, [])
        self.error.assert_called_once()
        self.assertEqual(p._variables["patente"].get(), "ABCD12")

    def test_error_inesperado_no_cierra_la_aplicacion(self):
        def falla(*args):
            raise RuntimeError("fallo interno")

        p = self._pantalla(falla)
        self._salir(p, "ABCD12", "15/11/2026 10:00")
        self.error.assert_called_once()
        self.assertNotIn("fallo interno", self.texto_mensaje(self.error))
        self.assertTrue(p.winfo_exists())
        self.assertEqual(p._variables["patente"].get(), "ABCD12")


class PruebasVentanaPrincipal(unittest.TestCase):
    def setUp(self):
        servicios_demo.reiniciar_demo()
        self.parche = patch("tkinter.messagebox.showinfo")
        self.parche.start()
        self.ventana = VentanaPrincipal(
            servicios_demo.registrar_vehiculo,
            servicios_demo.listar_vehiculos,
            servicios_demo.registrar_ingreso,
            servicios_demo.registrar_salida,
        )
        self.ventana.withdraw()

    def tearDown(self):
        self.parche.stop()
        self.ventana.destroy()

    def test_tiene_las_tres_pestanas(self):
        textos = [self.ventana._pestanas.tab(i, "text") for i in self.ventana._pestanas.tabs()]
        self.assertEqual(textos, ["Vehículos", "Ingresos", "Salidas"])

    def test_el_registro_de_vehiculos_sigue_operativo(self):
        pantalla = self.ventana.pantalla_vehiculos
        pantalla._variables["patente"].set("abcd12")
        pantalla._variables["nombre_responsable"].set("Ana")
        pantalla.registrar()
        filas = [pantalla._tabla.item(i, "values") for i in pantalla._tabla.get_children()]
        self.assertEqual(filas[0][1], "ABCD12")

    def test_flujo_completo_entre_pestanas(self):
        v = self.ventana.pantalla_vehiculos
        v._variables["patente"].set("ABCD12")
        v.registrar()

        i = self.ventana.pantalla_ingresos
        i._variables["patente"].set("ABCD12")
        i._variables["fecha"].set("15/11/2026 10:00:00")
        i.registrar()

        with patch("tkinter.messagebox.showinfo") as info:
            s = self.ventana.pantalla_salidas
            s._variables["patente"].set("ABCD12")
            s._variables["fecha"].set("15/11/2026 10:01:10")
            s.registrar()
            self.assertIn("$100", info.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
