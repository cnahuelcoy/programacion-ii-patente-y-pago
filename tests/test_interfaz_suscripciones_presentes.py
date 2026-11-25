import tkinter as tk
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from interfaz import servicios_demo
from interfaz.pantalla_presentes import PantallaPresentes
from interfaz.pantalla_suscripciones import PantallaSuscripciones
from interfaz.ventana_principal import VentanaPrincipal

INICIO = datetime(2026, 11, 1, 10, 0, 0)
TERMINO = datetime(2026, 12, 1, 10, 0, 0)


class PruebasServiciosDemo(unittest.TestCase):
    def setUp(self):
        servicios_demo.reiniciar_demo()
        servicios_demo.registrar_vehiculo("ABCD12", "Ana", "", "")

    def test_contratacion_devuelve_fechas_monto_y_pago(self):
        resultado = servicios_demo.contratar_suscripcion("abcd12", INICIO)
        self.assertEqual(
            set(resultado), {"patente", "fecha_inicio", "fecha_termino", "monto", "fecha_pago"}
        )
        self.assertEqual(resultado["patente"], "ABCD12")
        self.assertEqual(resultado["fecha_inicio"], INICIO)
        self.assertEqual(resultado["fecha_termino"], TERMINO)
        self.assertEqual(resultado["monto"], servicios_demo.TARIFA_MENSUAL_DEMO)
        self.assertIsInstance(resultado["fecha_pago"], datetime)

    def test_errores_de_contratacion(self):
        casos = [
            ("", INICIO, "patente"),
            ("ZZZZ99", INICIO, "no está registrado"),
            ("ABCD12", "ayer", "fecha"),
        ]
        for patente, fecha, texto in casos:
            with self.subTest(patente=patente):
                with self.assertRaises(ValueError) as contexto:
                    servicios_demo.contratar_suscripcion(patente, fecha)
                self.assertIn(texto, str(contexto.exception))

    def test_no_permite_suscripciones_superpuestas(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        with self.assertRaises(ValueError):
            servicios_demo.contratar_suscripcion("ABCD12", INICIO + timedelta(days=10))
        with self.assertRaises(ValueError):
            servicios_demo.contratar_suscripcion("ABCD12", INICIO - timedelta(days=10))

    def test_permite_suscripcion_que_empieza_al_termino_de_la_anterior(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        resultado = servicios_demo.contratar_suscripcion("ABCD12", TERMINO)
        self.assertEqual(resultado["fecha_inicio"], TERMINO)

    def test_ingreso_con_suscripcion_vigente_es_mensual(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        ingreso = servicios_demo.registrar_ingreso("ABCD12", INICIO + timedelta(days=5), "minuto")
        self.assertEqual(ingreso["modalidad"], "mensual")

    def test_vigencia_incluye_inicio_y_excluye_termino(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        en_inicio = servicios_demo.registrar_ingreso("ABCD12", INICIO, "minuto")
        servicios_demo.registrar_salida("ABCD12", INICIO + timedelta(hours=1))
        en_termino = servicios_demo.registrar_ingreso("ABCD12", TERMINO, "minuto")
        self.assertEqual(en_inicio["modalidad"], "mensual")
        self.assertEqual(en_termino["modalidad"], "minuto")

    def test_suscripcion_vencida_o_futura_no_da_cobertura(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        antes = servicios_demo.registrar_ingreso("ABCD12", INICIO - timedelta(days=1), "diaria")
        servicios_demo.registrar_salida("ABCD12", INICIO - timedelta(hours=1))
        despues = servicios_demo.registrar_ingreso("ABCD12", TERMINO + timedelta(days=1), "diaria")
        self.assertEqual(antes["modalidad"], "diaria")
        self.assertEqual(despues["modalidad"], "diaria")

    def test_estadia_cubierta_sigue_cubierta_aunque_la_suscripcion_venza(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        servicios_demo.registrar_ingreso("ABCD12", TERMINO - timedelta(hours=1), "minuto")
        salida = servicios_demo.registrar_salida("ABCD12", TERMINO + timedelta(days=3))
        self.assertEqual(salida["modalidad"], "mensual")
        self.assertEqual(salida["monto"], 0)

    def test_presentes_devuelve_los_campos_acordados(self):
        servicios_demo.contratar_suscripcion("ABCD12", INICIO)
        servicios_demo.registrar_ingreso("ABCD12", INICIO + timedelta(days=1), "minuto")
        presentes = servicios_demo.listar_vehiculos_presentes()
        self.assertEqual(len(presentes), 1)
        self.assertEqual(
            set(presentes[0]),
            {
                "estadia_id",
                "vehiculo_id",
                "patente",
                "nombre_responsable",
                "fecha_ingreso",
                "modalidad",
                "suscripcion_id",
            },
        )
        self.assertEqual(presentes[0]["nombre_responsable"], "Ana")
        self.assertEqual(presentes[0]["modalidad"], "mensual")
        self.assertIsNotNone(presentes[0]["suscripcion_id"])

    def test_presentes_sin_suscripcion_tiene_suscripcion_id_nulo(self):
        servicios_demo.registrar_ingreso("ABCD12", INICIO, "diaria")
        self.assertIsNone(servicios_demo.listar_vehiculos_presentes()[0]["suscripcion_id"])

    def test_presentes_excluye_a_quienes_ya_salieron_y_ordena_por_ingreso(self):
        servicios_demo.registrar_vehiculo("BBBB22", "Beto", "", "")
        servicios_demo.registrar_vehiculo("CCCC33", "Cata", "", "")
        servicios_demo.registrar_ingreso("BBBB22", INICIO + timedelta(hours=2), "minuto")
        servicios_demo.registrar_ingreso("ABCD12", INICIO, "minuto")
        servicios_demo.registrar_ingreso("CCCC33", INICIO + timedelta(hours=1), "diaria")
        servicios_demo.registrar_salida("CCCC33", INICIO + timedelta(hours=3))
        patentes = [p["patente"] for p in servicios_demo.listar_vehiculos_presentes()]
        self.assertEqual(patentes, ["ABCD12", "BBBB22"])


class BasePantallas(unittest.TestCase):
    def setUp(self):
        servicios_demo.reiniciar_demo()
        servicios_demo.registrar_vehiculo("ABCD12", "Ana", "", "")
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


class PruebasPantallaSuscripciones(BasePantallas):
    def _pantalla(self, funcion=None):
        return PantallaSuscripciones(self.raiz, funcion or servicios_demo.contratar_suscripcion)

    def _llenar(self, pantalla, patente, fecha):
        pantalla._variables["patente"].set(patente)
        pantalla._variables["fecha"].set(fecha)

    def test_contratacion_correcta_muestra_fechas_monto_y_confirmacion(self):
        llamadas = []

        def espia(patente, fecha):
            llamadas.append((patente, fecha))
            return servicios_demo.contratar_suscripcion(patente, fecha)

        p = self._pantalla(espia)
        self._llenar(p, "abcd12", "01/11/2026 10:00:00")
        p.contratar()

        self.assertEqual(llamadas, [("abcd12", INICIO)])
        self.assertIsNone(llamadas[0][1].tzinfo)
        self.error.assert_not_called()
        mensaje = self.texto_mensaje(self.info)
        self.assertIn("ABCD12", mensaje)
        self.assertIn("01/11/2026 10:00:00", mensaje)
        self.assertIn("01/12/2026 10:00:00", mensaje)
        self.assertIn("$30.000", mensaje)
        self.assertIn("Pago registrado", mensaje)
        self.assertEqual(p._variables["patente"].get(), "")

    def test_fecha_incorrecta_no_llama_y_conserva_lo_escrito(self):
        llamadas = []
        p = self._pantalla(lambda *args: llamadas.append(args))
        self._llenar(p, "ABCD12", "ayer")
        p.contratar()
        self.assertEqual(llamadas, [])
        self.assertIn("formato", self.texto_mensaje(self.error))
        self.info.assert_not_called()
        self.assertEqual(p._variables["patente"].get(), "ABCD12")
        self.assertEqual(p._variables["fecha"].get(), "ayer")

    def test_vehiculo_no_registrado_conserva_lo_escrito(self):
        p = self._pantalla()
        self._llenar(p, "ZZZZ99", "01/11/2026 10:00:00")
        p.contratar()
        self.assertIn("no está registrado", self.texto_mensaje(self.error))
        self.assertEqual(p._variables["patente"].get(), "ZZZZ99")
        self.assertEqual(p._variables["fecha"].get(), "01/11/2026 10:00:00")

    def test_patente_vacia_muestra_error(self):
        p = self._pantalla()
        self._llenar(p, "  ", "01/11/2026 10:00:00")
        p.contratar()
        self.assertIn("patente", self.texto_mensaje(self.error).lower())

    def test_suscripcion_superpuesta_muestra_error_y_conserva_lo_escrito(self):
        p = self._pantalla()
        self._llenar(p, "ABCD12", "01/11/2026 10:00:00")
        p.contratar()
        self.info.reset_mock()

        self._llenar(p, "ABCD12", "10/11/2026 10:00:00")
        p.contratar()
        self.assertIn("suscripción", self.texto_mensaje(self.error))
        self.info.assert_not_called()
        self.assertEqual(p._variables["patente"].get(), "ABCD12")
        self.assertEqual(p._variables["fecha"].get(), "10/11/2026 10:00:00")

    def test_error_inesperado_no_cierra_la_aplicacion(self):
        def falla(*args):
            raise RuntimeError("fallo interno")

        p = self._pantalla(falla)
        self._llenar(p, "ABCD12", "01/11/2026 10:00:00")
        p.contratar()
        self.error.assert_called_once()
        self.assertNotIn("fallo interno", self.texto_mensaje(self.error))
        self.assertTrue(p.winfo_exists())
        self.assertEqual(p._variables["patente"].get(), "ABCD12")


class PruebasPantallaPresentes(BasePantallas):
    def _pantalla(self, funcion=None):
        return PantallaPresentes(self.raiz, funcion or servicios_demo.listar_vehiculos_presentes)

    def _filas(self, pantalla):
        tabla = pantalla._tabla
        return [tabla.item(i, "values") for i in tabla.get_children()]

    def test_tabla_vacia_al_inicio(self):
        self.assertEqual(self._filas(self._pantalla()), [])

    def test_carga_inicial_muestra_las_cuatro_columnas(self):
        servicios_demo.registrar_ingreso("ABCD12", INICIO, "diaria")
        filas = self._filas(self._pantalla())
        self.assertEqual(filas, [("ABCD12", "Ana", "01/11/2026 10:00:00", "diaria")])

    def test_boton_actualizar_recarga_la_tabla(self):
        p = self._pantalla()
        self.assertEqual(self._filas(p), [])
        servicios_demo.registrar_ingreso("ABCD12", INICIO, "minuto")
        self.assertEqual(self._filas(p), [])
        p._boton_actualizar.invoke()
        self.assertEqual(len(self._filas(p)), 1)

    def test_vehiculo_que_sale_desaparece_al_actualizar(self):
        servicios_demo.registrar_ingreso("ABCD12", INICIO, "minuto")
        p = self._pantalla()
        servicios_demo.registrar_salida("ABCD12", INICIO + timedelta(minutes=5))
        p._boton_actualizar.invoke()
        self.assertEqual(self._filas(p), [])

    def test_falla_al_listar_muestra_error_y_conserva_la_tabla(self):
        servicios_demo.registrar_ingreso("ABCD12", INICIO, "minuto")
        estado = {"falla": False}

        def listar():
            if estado["falla"]:
                raise RuntimeError("sin base de datos")
            return servicios_demo.listar_vehiculos_presentes()

        p = self._pantalla(listar)
        estado["falla"] = True
        p._boton_actualizar.invoke()

        self.error.assert_called_once()
        self.assertEqual(len(self._filas(p)), 1)
        self.assertTrue(p.winfo_exists())


class PruebasVentanaPrincipal(unittest.TestCase):
    def setUp(self):
        servicios_demo.reiniciar_demo()
        self.parche = patch("tkinter.messagebox.showinfo")
        self.info = self.parche.start()
        self.ventanas = []

    def tearDown(self):
        self.parche.stop()
        for ventana in self.ventanas:
            ventana.destroy()

    def _ventana(self, *extras):
        ventana = VentanaPrincipal(
            servicios_demo.registrar_vehiculo,
            servicios_demo.listar_vehiculos,
            servicios_demo.registrar_ingreso,
            servicios_demo.registrar_salida,
            *extras,
        )
        ventana.withdraw()
        self.ventanas.append(ventana)
        return ventana

    def _textos(self, ventana):
        return [ventana._pestanas.tab(i, "text") for i in ventana._pestanas.tabs()]

    def test_con_cuatro_funciones_queda_compatible_con_main_actual(self):
        ventana = self._ventana()
        self.assertEqual(self._textos(ventana), ["Vehículos", "Ingresos", "Salidas"])
        self.assertIsNone(ventana.pantalla_suscripciones)
        self.assertIsNone(ventana.pantalla_presentes)

    def test_con_tres_funciones_como_el_main_actual_deja_salidas_deshabilitada(self):
        ventana = VentanaPrincipal(
            servicios_demo.registrar_vehiculo,
            servicios_demo.listar_vehiculos,
            servicios_demo.registrar_ingreso,
        )
        ventana.withdraw()
        self.ventanas.append(ventana)
        self.assertEqual(self._textos(ventana), ["Vehículos", "Ingresos", "Salidas"])
        self.assertEqual(ventana._pestanas.tab(ventana.pantalla_salidas, "state"), "disabled")
        self.assertIsNone(ventana.pantalla_suscripciones)
        self.assertIsNone(ventana.pantalla_presentes)

    def test_agrega_las_pestanas_cuando_recibe_sus_funciones(self):
        ventana = self._ventana(
            servicios_demo.contratar_suscripcion, servicios_demo.listar_vehiculos_presentes
        )
        self.assertEqual(
            self._textos(ventana),
            ["Vehículos", "Ingresos", "Salidas", "Suscripciones", "Presentes"],
        )

    def test_agrega_solo_la_pestana_cuya_funcion_recibe(self):
        ventana = self._ventana(servicios_demo.contratar_suscripcion)
        self.assertEqual(
            self._textos(ventana), ["Vehículos", "Ingresos", "Salidas", "Suscripciones"]
        )

    def test_flujo_completo_entre_pestanas(self):
        ventana = self._ventana(
            servicios_demo.contratar_suscripcion, servicios_demo.listar_vehiculos_presentes
        )
        v = ventana.pantalla_vehiculos
        v._variables["patente"].set("ABCD12")
        v._variables["nombre_responsable"].set("Ana")
        v.registrar()

        s = ventana.pantalla_suscripciones
        s._variables["patente"].set("ABCD12")
        s._variables["fecha"].set("01/11/2026 10:00:00")
        s.contratar()

        i = ventana.pantalla_ingresos
        i._variables["patente"].set("ABCD12")
        i._variables["fecha"].set("05/11/2026 08:00:00")
        i.registrar()

        p = ventana.pantalla_presentes
        p._boton_actualizar.invoke()
        filas = [p._tabla.item(f, "values") for f in p._tabla.get_children()]
        self.assertEqual(filas, [("ABCD12", "Ana", "05/11/2026 08:00:00", "mensual")])


if __name__ == "__main__":
    unittest.main()
