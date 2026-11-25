from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.orm import sessionmaker

import datos_ejemplo
from persistencia import conexion, consultas
from persistencia.modelos import Estadia, Pago, Vehiculo


class PruebasHistoriales(unittest.TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory(prefix="historial-parte4-")
        self.addCleanup(directorio.cleanup)
        self.ruta = Path(directorio.name) / "pruebas.db"
        datos_ejemplo.generar_datos_ejemplo(self.ruta)
        self.motor = create_engine(f"sqlite:///{self.ruta.as_posix()}")
        self.addCleanup(self.motor.dispose)
        event.listen(self.motor, "connect", conexion.activar_claves_foraneas)
        self.sesiones = sessionmaker(bind=self.motor)
        for modulo, nombre, valor in (
            (consultas, "sesion_local", self.sesiones),
            (conexion, "motor", self.motor),
        ):
            parche = patch.object(modulo, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        self.fecha = datetime(2026, 11, 25, 10)

    def test_historial_incluye_estadias_activas_y_cerradas_en_orden_estable(self):
        historial = consultas.listar_historial_estadias()
        self.assertEqual(len(historial), 8)
        self.assertEqual(sum(e["fecha_salida"] is None for e in historial), 3)
        orden = [(e["fecha_ingreso"], e["estadia_id"]) for e in historial]
        self.assertEqual(orden, sorted(orden, reverse=True))
        minuto = consultas.listar_historial_estadias("DEMO01")[0]
        self.assertEqual(minuto["duracion_segundos"], 70)
        self.assertEqual(minuto["monto"], 100)
        self.assertIsNotNone(minuto["pago_id"])

    def test_estadias_filtra_por_fecha_de_ingreso_con_fin_exclusivo(self):
        resultado = consultas.listar_historial_estadias(
            fecha_desde=self.fecha, fecha_hasta=self.fecha + timedelta(seconds=1)
        )
        self.assertEqual({e["patente"] for e in resultado}, {"DEMO01", "DEMO04", "DEMO05", "DEMO06"})
        antes = consultas.listar_historial_estadias(fecha_hasta=self.fecha)
        self.assertTrue(all(e["fecha_ingreso"] < self.fecha for e in antes))

    def test_pagos_filtra_por_fecha_del_pago_y_no_por_ingreso(self):
        desde = self.fecha + timedelta(minutes=1)
        hasta = self.fecha + timedelta(minutes=2)
        pagos = consultas.listar_pagos("DEMO01", desde, hasta)
        self.assertEqual(len(pagos), 1)
        self.assertEqual(pagos[0]["monto"], 100)
        self.assertEqual(consultas.listar_historial_estadias("DEMO01", desde, hasta), [])
        self.assertEqual(len(consultas.listar_pagos(fecha_hasta=self.fecha)), 2)
        self.assertEqual(len(consultas.listar_pagos(fecha_desde=self.fecha)), 3)

    def test_pagos_incluye_ambos_origenes_y_no_repite_mensualidades(self):
        pagos = consultas.listar_pagos()
        self.assertEqual(len(pagos), 5)
        self.assertEqual(len({p["pago_id"] for p in pagos}), 5)
        self.assertEqual(sum(p["monto"] for p in pagos), 75100)
        self.assertEqual(sum(p["estadia_id"] is not None for p in pagos), 3)
        mensuales = consultas.listar_pagos(modalidad="mensual")
        self.assertEqual(len(mensuales), 2)
        self.assertEqual(sum(p["monto"] for p in mensuales), 60000)
        for pago in pagos:
            self.assertNotEqual(pago["estadia_id"] is None, pago["suscripcion_id"] is None)
        self.assertEqual(len(consultas.listar_historial_estadias("DEMO04")), 3)
        self.assertEqual(len(consultas.listar_pagos("DEMO04")), 1)

    def test_estadia_mensual_muestra_cero_sin_inventar_un_pago(self):
        historial = consultas.listar_historial_estadias("DEMO04")
        self.assertEqual(len(historial), 3)
        for estadia in historial:
            self.assertEqual(estadia["monto"], 0)
            self.assertIsNone(estadia["pago_id"])
            self.assertIsNone(estadia["fecha_pago"])
        self.assertEqual(sorted(e["duracion_segundos"] for e in historial if e["fecha_salida"]), [3600, 3600])

    def test_estadia_activa_sin_cobro_no_muestra_monto_ni_duracion_ficticia(self):
        estadia = consultas.listar_historial_estadias("DEMO06")[0]
        self.assertIsNone(estadia["monto"])
        self.assertIsNone(estadia["duracion_segundos"])
        self.assertIsNone(estadia["fecha_salida"])

    def test_combina_patente_periodo_y_modalidad(self):
        resultado = consultas.listar_historial_estadias(
            " demo04 ", self.fecha - timedelta(hours=3), self.fecha, " MENSUAL "
        )
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["fecha_ingreso"], self.fecha - timedelta(hours=2))
        pagos = consultas.listar_pagos(
            " demo02 ", self.fecha, self.fecha + timedelta(seconds=1), " DIARIA "
        )
        self.assertEqual([p["monto"] for p in pagos], [5000])

    def test_filtros_sin_resultados_devuelven_lista_vacia(self):
        for funcion in (consultas.listar_historial_estadias, consultas.listar_pagos):
            with self.subTest(funcion=funcion.__name__):
                self.assertEqual(funcion(patente="NOEXISTE"), [])
                self.assertEqual(funcion(patente="DEMO01", modalidad="mensual"), [])
                self.assertEqual(funcion(fecha_desde=self.fecha + timedelta(days=365)), [])

    def test_filtros_vacios_equivalen_a_no_filtrar(self):
        for funcion in (consultas.listar_historial_estadias, consultas.listar_pagos):
            with self.subTest(funcion=funcion.__name__):
                self.assertEqual(funcion(patente="  ", modalidad=" "), funcion())

    def test_filtros_invalidos_se_rechazan(self):
        casos = [
            {"patente": 123}, {"patente": True}, {"modalidad": "otra"},
            {"modalidad": False}, {"fecha_desde": "hoy"},
            {"fecha_hasta": self.fecha.date()},
            {"fecha_desde": self.fecha.replace(tzinfo=timezone.utc)},
            {"fecha_hasta": self.fecha.replace(tzinfo=timezone.utc)},
            {"fecha_desde": self.fecha, "fecha_hasta": self.fecha},
            {"fecha_desde": self.fecha, "fecha_hasta": self.fecha - timedelta(seconds=1)},
        ]
        for funcion in (consultas.listar_historial_estadias, consultas.listar_pagos):
            for filtros in casos:
                with self.subTest(funcion=funcion.__name__, filtros=filtros):
                    with self.assertRaises(ValueError):
                        funcion(**filtros)

    def test_consultas_reconocen_patentes_antiguas_con_unicode_y_espacios(self):
        with self.sesiones() as sesion:
            vehiculo = Vehiculo(patente="\tábcd99\u2003", nombre_responsable="Persona anterior")
            estadia = Estadia(
                vehiculo=vehiculo, fecha_ingreso=self.fecha,
                fecha_salida=self.fecha, modalidad="minuto",
                pago=Pago(monto=50, fecha_pago=self.fecha, modalidad="minuto"),
            )
            sesion.add(estadia)
            sesion.commit()
        for funcion in (consultas.listar_historial_estadias, consultas.listar_pagos):
            with self.subTest(funcion=funcion.__name__):
                self.assertEqual(len(funcion(" ÁBCD99 ")), 1)

    def test_patentes_antiguas_ambiguas_no_mezclan_historiales(self):
        with self.sesiones() as sesion:
            sesion.add(Vehiculo(patente=" demo01 ", nombre_responsable="Registro ambiguo"))
            sesion.commit()
        for funcion in (consultas.listar_historial_estadias, consultas.listar_pagos):
            with self.subTest(funcion=funcion.__name__), self.assertRaisesRegex(ValueError, "varios vehículos"):
                funcion("DEMO01")

    def test_cada_listado_sin_patente_usa_una_consulta(self):
        sentencias = []

        def registrar(_conexion, _cursor, sql, _parametros, _contexto, _muchos):
            sentencias.append(sql)

        event.listen(self.motor, "before_cursor_execute", registrar)
        try:
            consultas.listar_historial_estadias(modalidad="diaria")
            consultas.listar_pagos(modalidad="mensual")
        finally:
            event.remove(self.motor, "before_cursor_execute", registrar)
        self.assertEqual(len(sentencias), 2)

    def test_los_listados_no_modifican_la_base_y_devuelven_diccionarios(self):
        antes = self.ruta.read_bytes()
        historial = consultas.listar_historial_estadias()
        pagos = consultas.listar_pagos()
        pagos[0]["monto"] = -1
        historial[0]["patente"] = "CAMBIADA"
        self.assertGreater(consultas.listar_pagos()[0]["monto"], 0)
        self.assertNotEqual(consultas.listar_historial_estadias()[0]["patente"], "CAMBIADA")
        self.assertEqual(self.ruta.read_bytes(), antes)

    def test_actualiza_indice_de_pagos_sin_perder_registros(self):
        indice = next(i for i in Pago.__table__.indexes if i.name == "pago_por_fecha_y_modalidad")
        indice.drop(bind=self.motor)
        conexion.crear_tablas()
        conexion.crear_tablas()
        self.assertIn("pago_por_fecha_y_modalidad", {i["name"] for i in inspect(self.motor).get_indexes("pagos")})
        self.assertEqual(len(consultas.listar_pagos()), 5)


class PruebasGeneradorEjemplos(unittest.TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory(prefix="generador-parte4-")
        self.addCleanup(directorio.cleanup)
        self.ruta = Path(directorio.name) / "ejemplo.db"

    def test_genera_datos_consistentes_y_tres_vehiculos_presentes(self):
        resultado = datos_ejemplo.generar_datos_ejemplo(self.ruta)
        self.assertEqual({k: resultado[k] for k in ("vehiculos", "estadias", "suscripciones", "pagos")},
                         {"vehiculos": 6, "estadias": 8, "suscripciones": 2, "pagos": 5})
        motor = create_engine(f"sqlite:///{self.ruta.as_posix()}")
        try:
            with motor.connect() as conexion_prueba:
                self.assertEqual(conexion_prueba.exec_driver_sql("PRAGMA foreign_key_check").all(), [])
                self.assertEqual(conexion_prueba.exec_driver_sql("PRAGMA quick_check").scalar(), "ok")
                self.assertEqual(conexion_prueba.exec_driver_sql("SELECT COUNT(*) FROM estadias WHERE fecha_salida IS NULL").scalar(), 3)
                self.assertEqual(conexion_prueba.exec_driver_sql("SELECT modalidad FROM estadias JOIN vehiculos ON vehiculos.id=estadias.vehiculo_id WHERE patente='DEMO05'").scalar(), "minuto")
        finally:
            motor.dispose()

    def test_no_modifica_un_archivo_preexistente(self):
        contenido = b"Archivo que debe conservarse"
        self.ruta.write_bytes(contenido)
        with self.assertRaisesRegex(ValueError, "ya existe"):
            datos_ejemplo.generar_datos_ejemplo(self.ruta)
        self.assertEqual(self.ruta.read_bytes(), contenido)

    def test_repetir_el_generador_no_duplica_ni_borra_datos(self):
        datos_ejemplo.generar_datos_ejemplo(self.ruta)
        contenido = self.ruta.read_bytes()
        with self.assertRaises(ValueError):
            datos_ejemplo.generar_datos_ejemplo(self.ruta)
        self.assertEqual(self.ruta.read_bytes(), contenido)

    def test_fallo_durante_generacion_no_deja_base_incompleta(self):
        def fallar(sesion):
            sesion.add(Vehiculo(patente="PRUEBA", nombre_responsable="Prueba"))
            sesion.flush()
            raise RuntimeError("fallo simulado")

        with patch.object(datos_ejemplo, "_cargar_ejemplos", side_effect=fallar):
            with self.assertRaises(RuntimeError):
                datos_ejemplo.generar_datos_ejemplo(self.ruta)
        self.assertFalse(self.ruta.exists())
        datos_ejemplo.generar_datos_ejemplo(self.ruta)

    def test_dos_generaciones_simultaneas_no_sobrescriben_el_archivo(self):
        barrera = Barrier(2)

        def ejecutar():
            barrera.wait(timeout=5)
            try:
                return datos_ejemplo.generar_datos_ejemplo(self.ruta)
            except ValueError as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            resultados = list(ejecutor.map(lambda _: ejecutar(), range(2)))
        self.assertEqual(sum(isinstance(r, dict) for r in resultados), 1)
        self.assertEqual(sum(isinstance(r, str) for r in resultados), 1)

    def test_comando_documentado_genera_ejemplos_y_rechaza_repeticion(self):
        script = Path(datos_ejemplo.__file__).resolve()
        comando = [sys.executable, "-B", str(script), "--base", str(self.ruta)]
        primero = subprocess.run(comando, capture_output=True, text=True)
        self.assertEqual(primero.returncode, 0, primero.stderr)
        contenido = self.ruta.read_bytes()
        segundo = subprocess.run(comando, capture_output=True, text=True)
        self.assertEqual(segundo.returncode, 1)
        self.assertEqual(self.ruta.read_bytes(), contenido)

    def test_ruta_por_defecto_se_puede_probar_sin_tocar_la_base_real(self):
        with patch.object(datos_ejemplo, "RUTA_BASE_DATOS", self.ruta):
            resultado = datos_ejemplo.generar_datos_ejemplo()
        self.assertEqual(resultado["ruta"], str(self.ruta.resolve()))


if __name__ == "__main__":
    unittest.main()
