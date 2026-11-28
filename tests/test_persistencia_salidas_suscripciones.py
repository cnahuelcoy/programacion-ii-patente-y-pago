from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.orm import sessionmaker

from persistencia import conexion, consultas, ingresos, salidas, suscripciones, vehiculos
from persistencia.modelos import Estadia, Pago, Suscripcion, Vehiculo


class PruebasSalidasYSuscripciones(unittest.TestCase):
    def setUp(self):
        directorio = tempfile.TemporaryDirectory(prefix="patente-parte3-")
        self.addCleanup(directorio.cleanup)
        ruta = Path(directorio.name) / "pruebas.db"
        self.motor = create_engine(f"sqlite:///{ruta.as_posix()}")
        self.addCleanup(self.motor.dispose)
        event.listen(self.motor, "connect", conexion.activar_claves_foraneas)
        self.sesiones = sessionmaker(bind=self.motor)
        for modulo, nombre, valor in [
            (conexion, "motor", self.motor),
            *[(modulo, "sesion_local", self.sesiones) for modulo in
              (consultas, ingresos, salidas, suscripciones, vehiculos)],
        ]:
            parche = patch.object(modulo, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)
        conexion.crear_tablas()
        self.fecha = datetime(2026, 11, 23, 10)

    def _vehiculo(self, patente="ABCD12"):
        return vehiculos.registrar_vehiculo(patente, "Ana", None, "ana@example.com")

    def _ingresar(self, patente="ABCD12", modalidad="minuto", fecha=None):
        return ingresos.registrar_ingreso(patente, fecha or self.fecha, modalidad)

    def _suscribir(self, patente="ABCD12", inicio=None, fecha_pago=None):
        inicio = inicio or self.fecha
        return suscripciones.registrar_suscripcion(
            patente, inicio, inicio + timedelta(days=30), 30000, fecha_pago
        )

    def _contar(self, modelo):
        with self.sesiones() as sesion:
            return sesion.scalar(select(func.count()).select_from(modelo))

    def _crear_fallo_al_guardar_pago(self):
        with self.motor.begin() as conexion_prueba:
            conexion_prueba.exec_driver_sql(
                "CREATE TRIGGER rechazar_pago BEFORE INSERT ON pagos "
                "BEGIN SELECT RAISE(ABORT, 'fallo de almacenamiento'); END"
            )

    def _ejecutar_simultaneamente(self, operacion):
        barrera = Barrier(2)

        def ejecutar():
            barrera.wait(timeout=5)
            try:
                return operacion()
            except ValueError as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            futuros = [ejecutor.submit(ejecutar) for _ in range(2)]
            return [futuro.result(timeout=15) for futuro in futuros]

    def test_salida_guarda_el_monto_recibido_y_su_fecha_de_pago(self):
        for patente, modalidad in [("ABCD12", "minuto"), ("EFGH34", "diaria")]:
            with self.subTest(modalidad=modalidad):
                self._vehiculo(patente)
                ingreso = self._ingresar(patente, modalidad)
                salida = self.fecha + timedelta(days=1, minutes=1)
                fecha_pago = salida + timedelta(hours=2)
                resultado = salidas.registrar_salida(patente.lower(), salida, 137, fecha_pago)
                self.assertEqual(resultado["monto"], 137)
                self.assertEqual(resultado["fecha_pago"], fecha_pago)
                with self.sesiones() as sesion:
                    estadia = sesion.get(Estadia, ingreso["id"])
                    pago = sesion.get(Pago, resultado["pago_id"])
                    self.assertEqual(estadia.fecha_salida, salida)
                    self.assertEqual(pago.estadia_id, estadia.id)
                    self.assertIsNone(pago.suscripcion_id)
                    self.assertEqual(pago.modalidad, modalidad)
                    self.assertEqual(pago.monto, 137)
                    self.assertEqual(pago.fecha_pago, fecha_pago)

    def test_salida_usa_la_fecha_del_registro_si_no_se_indica_fecha_pago(self):
        self._vehiculo()
        self._ingresar()
        antes = datetime.now()
        resultado = salidas.registrar_salida("ABCD12", self.fecha, 50)
        self.assertLessEqual(antes, resultado["fecha_pago"])
        self.assertLessEqual(resultado["fecha_pago"], datetime.now())

    def test_salida_rechaza_fechas_y_montos_invalidos_sin_cerrar_estadia(self):
        self._vehiculo()
        ingreso = self._ingresar()
        casos = [(fecha, 50) for fecha in
                 (None, "hoy", self.fecha.date(), self.fecha.replace(tzinfo=timezone.utc))]
        casos += [(self.fecha, monto) for monto in (None, True, 1.5, "50", -1, 0, 2**63)]
        casos.append((self.fecha - timedelta(microseconds=1), 50))
        for fecha, monto in casos:
            with self.subTest(fecha=fecha, monto=monto):
                with self.assertRaises(ValueError):
                    salidas.registrar_salida("ABCD12", fecha, monto)
        with self.sesiones() as sesion:
            self.assertIsNone(sesion.get(Estadia, ingreso["id"]).fecha_salida)
        self.assertEqual(self._contar(Pago), 0)

    def test_salida_rechaza_patente_y_fecha_pago_invalidas(self):
        self._vehiculo()
        self._ingresar()
        for patente in (None, " ", False):
            with self.subTest(patente=patente), self.assertRaises(ValueError):
                salidas.registrar_salida(patente, self.fecha, 50)
        for fecha_pago in ("hoy", self.fecha.replace(tzinfo=timezone.utc)):
            with self.subTest(fecha_pago=fecha_pago), self.assertRaises(ValueError):
                salidas.registrar_salida("ABCD12", self.fecha, 50, fecha_pago)
        self.assertEqual(len(consultas.listar_vehiculos_presentes()), 1)

    def test_salida_exige_vehiculo_existente_y_estadia_activa(self):
        with self.assertRaisesRegex(ValueError, "No existe"):
            salidas.registrar_salida("ABCD12", self.fecha, 50)
        self._vehiculo()
        with self.assertRaisesRegex(ValueError, "no tiene una estadía activa"):
            salidas.registrar_salida("ABCD12", self.fecha, 50)

    def test_salida_no_se_registra_dos_veces(self):
        self._vehiculo()
        self._ingresar()
        salidas.registrar_salida("ABCD12", self.fecha, 50)
        with self.assertRaisesRegex(ValueError, "no tiene una estadía activa"):
            salidas.registrar_salida("ABCD12", self.fecha, 50)
        self.assertEqual(self._contar(Pago), 1)
        self.assertEqual(consultas.listar_vehiculos_presentes(), [])
        self._ingresar(fecha=self.fecha + timedelta(minutes=1))
        self.assertEqual(len(consultas.listar_vehiculos_presentes()), 1)

    def test_mensual_conserva_cobertura_tras_vencer_y_no_duplica_pago(self):
        self._vehiculo()
        suscripcion = self._suscribir()
        vencimiento = suscripcion["fecha_termino"]
        self._ingresar(fecha=vencimiento - timedelta(microseconds=1))
        resultado = salidas.registrar_salida("ABCD12", vencimiento + timedelta(days=2), 0)
        self.assertEqual(resultado["modalidad"], "mensual")
        self.assertEqual(resultado["suscripcion_id"], suscripcion["id"])
        self.assertIsNone(resultado["pago_id"])
        self.assertIsNone(resultado["fecha_pago"])
        self.assertEqual(self._contar(Pago), 1)
        nuevo = self._ingresar(fecha=vencimiento + timedelta(days=3))
        self.assertEqual(nuevo["modalidad"], "minuto")

    def test_salida_mensual_rechaza_un_cobro_adicional(self):
        self._vehiculo()
        self._suscribir()
        self._ingresar()
        with self.assertRaisesRegex(ValueError, "monto cero"):
            salidas.registrar_salida("ABCD12", self.fecha, 50)
        self.assertEqual(len(consultas.listar_vehiculos_presentes()), 1)
        self.assertEqual(self._contar(Pago), 1)

    def test_salida_rechaza_datos_antiguos_inconsistentes(self):
        vehiculo = self._vehiculo()
        for modalidad in ("mensual", "otra"):
            with self.subTest(modalidad=modalidad):
                with self.sesiones() as sesion:
                    estadia = Estadia(vehiculo_id=vehiculo["id"], fecha_ingreso=self.fecha, modalidad=modalidad)
                    sesion.add(estadia)
                    sesion.commit()
                    identificador = estadia.id
                with self.assertRaises(ValueError):
                    salidas.registrar_salida("ABCD12", self.fecha, 0)
                with self.sesiones() as sesion:
                    sesion.delete(sesion.get(Estadia, identificador))
                    sesion.commit()
        self.assertEqual(self._contar(Pago), 0)

    def test_error_al_guardar_pago_revierte_la_salida(self):
        self._vehiculo()
        ingreso = self._ingresar()
        self._crear_fallo_al_guardar_pago()
        with self.assertRaisesRegex(ValueError, "salida y su pago"):
            salidas.registrar_salida("ABCD12", self.fecha, 50)
        with self.sesiones() as sesion:
            self.assertIsNone(sesion.get(Estadia, ingreso["id"]).fecha_salida)
        self.assertEqual(self._contar(Pago), 0)

    def test_error_de_commit_revierte_la_salida(self):
        self._vehiculo()
        self._ingresar()
        with patch.object(self.sesiones.class_, "commit", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                salidas.registrar_salida("ABCD12", self.fecha, 50)
        self.assertEqual(len(consultas.listar_vehiculos_presentes()), 1)
        self.assertEqual(self._contar(Pago), 0)
        salidas.registrar_salida("ABCD12", self.fecha, 50)

    def test_dos_salidas_simultaneas_solo_guardan_un_pago(self):
        self._vehiculo()
        self._ingresar()
        resultados = self._ejecutar_simultaneamente(
            lambda: salidas.registrar_salida("ABCD12", self.fecha, 50)
        )
        self.assertEqual(sum(isinstance(r, dict) for r in resultados), 1)
        self.assertEqual(sum(isinstance(r, str) for r in resultados), 1)
        self.assertEqual(self._contar(Pago), 1)

    def test_dos_salidas_mensuales_simultaneas_solo_cierran_una_vez(self):
        self._vehiculo()
        self._suscribir()
        self._ingresar()
        resultados = self._ejecutar_simultaneamente(
            lambda: salidas.registrar_salida("ABCD12", self.fecha, 0)
        )
        self.assertEqual(sum(isinstance(r, dict) for r in resultados), 1)
        self.assertEqual(sum(isinstance(r, str) for r in resultados), 1)
        self.assertEqual(self._contar(Pago), 1)

    def test_suscripcion_guarda_sus_fechas_y_un_solo_pago(self):
        vehiculo = self._vehiculo()
        fecha_pago = self.fecha - timedelta(days=1)
        resultado = self._suscribir(" abcd12 ", fecha_pago=fecha_pago)
        with self.sesiones() as sesion:
            suscripcion = sesion.get(Suscripcion, resultado["id"])
            pago = sesion.get(Pago, resultado["pago_id"])
            self.assertEqual(suscripcion.vehiculo_id, vehiculo["id"])
            self.assertEqual(suscripcion.fecha_termino - suscripcion.fecha_inicio, timedelta(days=30))
            self.assertEqual(pago.suscripcion_id, suscripcion.id)
            self.assertIsNone(pago.estadia_id)
            self.assertEqual(pago.modalidad, "mensual")
            self.assertEqual(pago.fecha_pago, fecha_pago)
        self.assertEqual(self._contar(Pago), 1)

    def test_suscripcion_usa_fecha_de_registro_independiente_del_inicio(self):
        self._vehiculo()
        antes = datetime.now()
        resultado = self._suscribir(inicio=self.fecha + timedelta(days=90))
        self.assertLessEqual(antes, resultado["fecha_pago"])
        self.assertLessEqual(resultado["fecha_pago"], datetime.now())
        self.assertNotEqual(resultado["fecha_pago"], resultado["fecha_inicio"])

    def test_suscripcion_exige_vehiculo_existente(self):
        with self.assertRaisesRegex(ValueError, "No existe"):
            self._suscribir()
        self.assertEqual(self._contar(Suscripcion), 0)
        self.assertEqual(self._contar(Pago), 0)

    def test_suscripcion_rechaza_fechas_montos_y_patentes_invalidos(self):
        self._vehiculo()
        termino = self.fecha + timedelta(days=30)
        casos = [(patente, self.fecha, termino, 30000) for patente in (None, " ", False)]
        casos += [("ABCD12", fecha, termino, 30000) for fecha in
                  (None, "hoy", self.fecha.replace(tzinfo=timezone.utc))]
        casos += [("ABCD12", self.fecha, fecha, 30000) for fecha in
                  (None, "hoy", termino.replace(tzinfo=timezone.utc), self.fecha,
                   self.fecha - timedelta(days=30), termino - timedelta(microseconds=1),
                   termino + timedelta(microseconds=1))]
        casos += [("ABCD12", self.fecha, termino, monto) for monto in
                  (None, False, True, 1.5, "30000", 0, -1, 2**63)]
        for datos in casos:
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                suscripciones.registrar_suscripcion(*datos)
        with self.assertRaises(ValueError):
            self._suscribir(fecha_pago=termino.replace(tzinfo=timezone.utc))
        self.assertEqual(self._contar(Suscripcion), 0)
        self.assertEqual(self._contar(Pago), 0)

    def test_suscripciones_superpuestas_se_rechazan(self):
        self._vehiculo()
        self._suscribir()
        for desplazamiento in (-29, -1, 0, 1, 29):
            with self.subTest(desplazamiento=desplazamiento):
                with self.assertRaisesRegex(ValueError, "superpone"):
                    self._suscribir(inicio=self.fecha + timedelta(days=desplazamiento))
        self.assertEqual(self._contar(Suscripcion), 1)
        self.assertEqual(self._contar(Pago), 1)

    def test_suscripciones_adyacentes_se_permiten(self):
        self._vehiculo()
        self._suscribir()
        self._suscribir(inicio=self.fecha - timedelta(days=30))
        siguiente = self._suscribir(inicio=self.fecha + timedelta(days=30))
        ingreso = self._ingresar(fecha=siguiente["fecha_inicio"])
        self.assertEqual(ingreso["suscripcion_id"], siguiente["id"])
        self.assertEqual(self._contar(Pago), 3)

    def test_distintos_vehiculos_pueden_tener_la_misma_cobertura(self):
        for patente in ("ABCD12", "EFGH34"):
            self._vehiculo(patente)
            self._suscribir(patente)
        self.assertEqual(self._contar(Suscripcion), 2)
        self.assertEqual(self._contar(Pago), 2)

    def test_error_al_guardar_pago_revierte_la_suscripcion(self):
        self._vehiculo()
        self._crear_fallo_al_guardar_pago()
        with self.assertRaisesRegex(ValueError, "suscripción y su pago"):
            self._suscribir()
        self.assertEqual(self._contar(Suscripcion), 0)
        self.assertEqual(self._contar(Pago), 0)

    def test_error_de_commit_revierte_la_suscripcion(self):
        self._vehiculo()
        with patch.object(self.sesiones.class_, "commit", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                self._suscribir()
        self.assertEqual(self._contar(Suscripcion), 0)
        self.assertEqual(self._contar(Pago), 0)
        self._suscribir()

    def test_suscripciones_simultaneas_no_se_superponen(self):
        self._vehiculo()
        resultados = self._ejecutar_simultaneamente(self._suscribir)
        self.assertEqual(sum(isinstance(r, dict) for r in resultados), 1)
        self.assertEqual(sum(isinstance(r, str) for r in resultados), 1)
        self.assertEqual(self._contar(Suscripcion), 1)
        self.assertEqual(self._contar(Pago), 1)

    def test_presentes_solo_incluye_estadias_activas_y_usa_una_consulta(self):
        for patente in ("ABCD12", "EFGH34", "IJKL56"):
            self._vehiculo(patente)
        self._suscribir("EFGH34")
        self._ingresar("ABCD12", fecha=self.fecha + timedelta(minutes=1))
        mensual = self._ingresar("EFGH34")
        self._ingresar("IJKL56")
        salidas.registrar_salida("IJKL56", self.fecha, 50)
        consultas_sql = []

        def registrar_sql(_conexion, _cursor, sentencia, _parametros, _contexto, _muchos):
            consultas_sql.append(sentencia)

        event.listen(self.motor, "before_cursor_execute", registrar_sql)
        try:
            presentes = consultas.listar_vehiculos_presentes()
        finally:
            event.remove(self.motor, "before_cursor_execute", registrar_sql)
        self.assertEqual(len(consultas_sql), 1)
        self.assertEqual([v["patente"] for v in presentes], ["EFGH34", "ABCD12"])
        self.assertEqual(presentes[0]["modalidad"], "mensual")
        self.assertEqual(presentes[0]["estadia_id"], mensual["id"])
        self.assertEqual(presentes[0]["suscripcion_id"], mensual["suscripcion_id"])

    def test_registros_persisten_al_reabrir_conexiones(self):
        self._vehiculo()
        suscripcion = self._suscribir()
        self._ingresar()
        salidas.registrar_salida("ABCD12", self.fecha, 0)
        self.motor.dispose()
        with self.sesiones() as sesion:
            self.assertIsNotNone(sesion.get(Suscripcion, suscripcion["id"]))
            self.assertEqual(sesion.get(Pago, suscripcion["pago_id"]).monto, 30000)
        self.assertEqual(consultas.listar_vehiculos_presentes(), [])

    def test_actualiza_indice_de_suscripciones_sin_perder_datos(self):
        self._vehiculo()
        self._suscribir()
        indice = next(iter(Suscripcion.__table__.indexes))
        indice.drop(bind=self.motor)
        conexion.crear_tablas()
        conexion.crear_tablas()
        nombres = {indice["name"] for indice in inspect(self.motor).get_indexes("suscripciones")}
        self.assertIn("suscripcion_por_vehiculo_y_fechas", nombres)
        self.assertEqual(self._contar(Suscripcion), 1)
        self.assertEqual(self._contar(Pago), 1)


if __name__ == "__main__":
    unittest.main()
