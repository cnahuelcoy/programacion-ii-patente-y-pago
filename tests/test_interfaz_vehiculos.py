"""Pruebas de la pantalla de vehículos (usan las funciones en memoria).

Ejecutar desde la raíz del proyecto:
    python -m unittest tests.test_interfaz_vehiculos -v
Los cuadros de mensaje se reemplazan por simulacros para no abrir ventanas.
"""

import tkinter as tk
import unittest
from unittest.mock import patch

from interfaz import servicios_demo
from interfaz.pantalla_vehiculos import PantallaVehiculos


class PruebasPantallaVehiculos(unittest.TestCase):
    def setUp(self):
        servicios_demo.reiniciar_demo()
        self.raiz = tk.Tk()
        self.raiz.withdraw()
        self._parches = [
            patch("interfaz.pantalla_vehiculos.messagebox.showinfo"),
            patch("interfaz.pantalla_vehiculos.messagebox.showerror"),
        ]
        self.info, self.error = [p.start() for p in self._parches]
        self.pantalla = self._crear_pantalla()

    def tearDown(self):
        for p in self._parches:
            p.stop()
        self.raiz.destroy()

    def _crear_pantalla(self, registrar=None, listar=None):
        return PantallaVehiculos(
            self.raiz,
            registrar or servicios_demo.registrar_vehiculo,
            listar or servicios_demo.listar_vehiculos,
        )

    def _llenar(self, patente="", nombre="", telefono="", correo=""):
        v = self.pantalla._variables
        v["patente"].set(patente)
        v["nombre_responsable"].set(nombre)
        v["telefono"].set(telefono)
        v["correo"].set(correo)

    def _filas(self, pantalla=None):
        tabla = (pantalla or self.pantalla)._tabla
        return [tabla.item(i, "values") for i in tabla.get_children()]

    def test_registro_correcto_actualiza_tabla_y_limpia_formulario(self):
        self._llenar("abcd12", "Ana Pérez", "+56911112222", "ana@correo.cl")
        self.pantalla.registrar()

        self.assertEqual(self._filas(), [("1", "ABCD12", "Ana Pérez", "+56911112222", "ana@correo.cl")])
        self.info.assert_called_once()
        self.error.assert_not_called()
        self.assertEqual(self.pantalla._variables["patente"].get(), "")

    def test_segundo_registro_se_agrega_a_la_tabla(self):
        self._llenar("AAAA11", "Ana")
        self.pantalla.registrar()
        self._llenar("BBBB22", "Beto")
        self.pantalla.registrar()
        self.assertEqual([f[1] for f in self._filas()], ["AAAA11", "BBBB22"])

    def test_telefono_con_letras_no_se_guarda_en_la_demo(self):
        self._llenar("ABCD12", "Ana", "123abc", "ana@example.com")
        self.pantalla.registrar()
        self.error.assert_called_once()
        self.assertIn("teléfono", self.error.call_args.args[1])
        self.info.assert_not_called()
        self.assertEqual(servicios_demo.listar_vehiculos(), [])
        self.assertEqual(self.pantalla._variables["telefono"].get(), "123abc")

    def test_patente_vacia_muestra_error_y_no_registra(self):
        self._llenar("   ", "Ana")
        self.pantalla.registrar()

        self.error.assert_called_once()
        self.assertIn("patente", self.error.call_args.args[1].lower())
        self.info.assert_not_called()
        self.assertEqual(self._filas(), [])
        self.assertEqual(self.pantalla._variables["nombre_responsable"].get(), "Ana")  # no pierde lo escrito

    def test_patente_duplicada_muestra_error(self):
        self._llenar("AAAA11")
        self.pantalla.registrar()
        self.info.reset_mock()

        self._llenar("aaaa11")
        self.pantalla.registrar()

        self.error.assert_called_once()
        self.assertIn("AAAA11", self.error.call_args.args[1])
        self.info.assert_not_called()
        self.assertEqual(len(self._filas()), 1)

    def test_error_inesperado_no_cierra_la_aplicacion(self):
        def falla(*args):
            raise RuntimeError("fallo interno")

        pantalla = self._crear_pantalla(registrar=falla)
        pantalla._variables["patente"].set("AAAA11")
        pantalla.registrar()  # no debe propagar la excepción

        self.error.assert_called_once()
        self.assertNotIn("fallo interno", self.error.call_args.args[1])
        self.assertTrue(pantalla.winfo_exists())

    def test_tabla_inicial_carga_vehiculos_existentes(self):
        servicios_demo.registrar_vehiculo("ZZZZ99", "Zoe", "", "")
        pantalla = self._crear_pantalla()
        self.assertEqual([f[1] for f in self._filas(pantalla)], ["ZZZZ99"])

    def test_fallo_al_listar_muestra_error(self):
        def falla():
            raise RuntimeError("sin base de datos")

        self._crear_pantalla(listar=falla)
        self.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
