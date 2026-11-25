from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from threading import Barrier
import tkinter as tk
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import main
from interfaz.pantalla_vehiculos import PantallaVehiculos
from persistencia import conexion, ingresos, vehiculos
from persistencia.modelos import Estadia, Pago, Suscripcion, Vehiculo


class PruebasPersistencia(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory(prefix="patente-parte2-")
        ruta_directorio = Path(self.directorio.name).resolve()
        self.assertEqual(ruta_directorio.parent, Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.directorio.cleanup)

        ruta_base = ruta_directorio / "prueba.db"
        self.motor = create_engine(f"sqlite:///{ruta_base.as_posix()}")
        self.addCleanup(self.motor.dispose)
        event.listen(self.motor, "connect", conexion.activar_claves_foraneas)
        self.sesiones = sessionmaker(bind=self.motor)

        parches = [
            patch.object(conexion, "motor", self.motor),
            patch.object(vehiculos, "sesion_local", self.sesiones),
            patch.object(ingresos, "sesion_local", self.sesiones),
        ]
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)

        conexion.crear_tablas()
        self.fecha = datetime(2026, 11, 20, 10, 0)
        self.indice = next(iter(Estadia.__table__.indexes))

    def _crear_vehiculo(self, patente="ABCD12"):
        return vehiculos.registrar_vehiculo(
            patente, "Persona de prueba", None, "prueba@example.com"
        )

    def _crear_suscripcion(self, vehiculo_id, inicio, termino):
        with self.sesiones() as sesion:
            suscripcion = Suscripcion(
                vehiculo_id=vehiculo_id,
                fecha_inicio=inicio,
                fecha_termino=termino,
                pago=Pago(
                    monto=30000,
                    fecha_pago=inicio,
                    modalidad="mensual",
                ),
            )
            sesion.add(suscripcion)
            sesion.flush()
            identificador = suscripcion.id
            sesion.commit()
            return identificador

    def _contar(self, modelo):
        with self.sesiones() as sesion:
            return sesion.scalar(select(func.count()).select_from(modelo))

    def _ejecutar_en_paralelo(self, modelo, operacion):
        barrera = Barrier(2)

        def sincronizar(sesion, _contexto, _instancias):
            if any(isinstance(objeto, modelo) for objeto in sesion.new):
                barrera.wait(timeout=5)

        def ejecutar():
            try:
                return operacion()
            except ValueError as error:
                return str(error)

        event.listen(self.sesiones.class_, "before_flush", sincronizar)
        try:
            with ThreadPoolExecutor(max_workers=2) as ejecutor:
                futuros = [ejecutor.submit(ejecutar) for _ in range(2)]
                return [futuro.result(timeout=15) for futuro in futuros]
        finally:
            event.remove(self.sesiones.class_, "before_flush", sincronizar)

    def test_listado_inicial_vacio(self):
        self.assertEqual(vehiculos.listar_vehiculos(), [])

    def test_registro_normaliza_datos_y_persiste_entre_sesiones(self):
        resultado = vehiculos.registrar_vehiculo(
            "  abcd12  ", "  Ana Pérez  ", None, " ana@example.com "
        )

        self.assertEqual(
            resultado,
            {
                "id": 1,
                "patente": "ABCD12",
                "nombre_responsable": "Ana Pérez",
                "telefono": "",
                "correo": "ana@example.com",
            },
        )
        self.assertEqual(vehiculos.listar_vehiculos(), [resultado])
        with self.sesiones() as sesion:
            self.assertIsNone(sesion.get(Vehiculo, resultado["id"]).telefono)

    def test_registro_permite_solo_telefono(self):
        resultado = vehiculos.registrar_vehiculo(
            "ABCD12", "Ana", " +56911112222 ", None
        )
        self.assertEqual(resultado["telefono"], "+56911112222")
        self.assertEqual(resultado["correo"], "")

    def test_telefono_invalido_no_guarda_vehiculo_aunque_haya_correo(self):
        for telefono in ("hola", "123abc", "+569abc", "+", "++56", "123+45",
                         "12 345", "123-456", "123.45", "123\n456", "１２３", 123, True):
            with self.subTest(telefono=telefono):
                with self.assertRaisesRegex(ValueError, "teléfono"):
                    vehiculos.registrar_vehiculo("ABCD12", "Ana", telefono, "ana@example.com")
        self.assertEqual(self._contar(Vehiculo), 0)

    def test_telefono_numerico_conserva_ceros_y_prefijo(self):
        for numero, telefono in enumerate(("00123456", "911112222", "+56911112222")):
            with self.subTest(telefono=telefono):
                resultado = vehiculos.registrar_vehiculo(
                    f"ABCD{numero:02d}", "Ana", f"  {telefono}  ", None
                )
                self.assertEqual(resultado["telefono"], telefono)
        self.assertEqual([v["telefono"] for v in vehiculos.listar_vehiculos()],
                         ["00123456", "911112222", "+56911112222"])

    def test_pantalla_rechaza_telefono_con_letras_y_conserva_formulario(self):
        raiz = tk.Tk()
        raiz.withdraw()
        try:
            with patch("tkinter.messagebox.showinfo") as informacion, \
                    patch("tkinter.messagebox.showerror") as error:
                pantalla = PantallaVehiculos(raiz, vehiculos.registrar_vehiculo, vehiculos.listar_vehiculos)
                pantalla._variables["patente"].set("ABCD12")
                pantalla._variables["nombre_responsable"].set("Ana")
                pantalla._variables["telefono"].set("123abc")
                pantalla._variables["correo"].set("ana@example.com")
                pantalla.registrar()
                error.assert_called_once()
                self.assertIn("teléfono", error.call_args.args[1])
                informacion.assert_not_called()
                self.assertEqual(pantalla._variables["telefono"].get(), "123abc")
                self.assertEqual(pantalla._tabla.get_children(), ())
                self.assertEqual(self._contar(Vehiculo), 0)
        finally:
            raiz.destroy()

    def test_datos_invalidos_no_guardan_vehiculos(self):
        casos = [
            (" ", "Ana", "123", ""),
            (None, "Ana", "123", ""),
            (123, "Ana", "123", ""),
            ("ABCD12", " ", "123", ""),
            ("ABCD12", None, "123", ""),
            ("ABCD12", "Ana", " ", None),
            ("ABCD12", "Ana", 123, "prueba@example.com"),
            ("ABCD12", "Ana", "123", False),
        ]
        for datos in casos:
            with self.subTest(datos=datos):
                with self.assertRaises(ValueError):
                    vehiculos.registrar_vehiculo(*datos)
        self.assertEqual(self._contar(Vehiculo), 0)

    def test_patente_duplicada_normalizada(self):
        self._crear_vehiculo()
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            self._crear_vehiculo(" abcd12 ")
        self.assertEqual(self._contar(Vehiculo), 1)

    def test_patente_antigua_con_unicode_y_espacios(self):
        with self.sesiones() as sesion:
            vehiculo = Vehiculo(
                patente="\tábcd12\u2003",
                nombre_responsable="Registro anterior",
            )
            sesion.add(vehiculo)
            sesion.commit()
            identificador = vehiculo.id

        self.assertEqual(vehiculos.listar_vehiculos()[0]["correo"], "")
        with self.assertRaisesRegex(ValueError, "Ya existe"):
            self._crear_vehiculo("ÁBCD12")
        resultado = ingresos.registrar_ingreso(" ábcd12 ", self.fecha, "minuto")
        self.assertEqual(resultado["vehiculo_id"], identificador)

    def test_listado_ordenado_por_identificador(self):
        primero = self._crear_vehiculo("ZZZZ99")
        segundo = self._crear_vehiculo("AAAA11")
        self.assertEqual(vehiculos.listar_vehiculos(), [primero, segundo])

    def test_patentes_antiguas_ambiguas_se_informan_sin_modificar_registros(self):
        with self.sesiones() as sesion:
            sesion.add_all([
                Vehiculo(patente="ABCD12", nombre_responsable="Ana"),
                Vehiculo(patente=" abcd12 ", nombre_responsable="Beto"),
            ])
            sesion.commit()

        with self.assertRaisesRegex(ValueError, "varios vehículos"):
            self._crear_vehiculo()
        with self.assertRaisesRegex(ValueError, "varios vehículos"):
            ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")
        self.assertEqual(self._contar(Vehiculo), 2)
        self.assertEqual(self._contar(Estadia), 0)

    def test_fallo_de_commit_revierte_el_vehiculo(self):
        with patch.object(
            self.sesiones.class_, "commit", side_effect=RuntimeError("fallo de prueba")
        ):
            with self.assertRaisesRegex(RuntimeError, "fallo de prueba"):
                self._crear_vehiculo()
        self.assertEqual(self._contar(Vehiculo), 0)
        self.assertEqual(self._crear_vehiculo()["patente"], "ABCD12")

    def test_registros_simultaneos_con_la_misma_patente(self):
        resultados = self._ejecutar_en_paralelo(Vehiculo, self._crear_vehiculo)
        self.assertEqual(sum(isinstance(resultado, dict) for resultado in resultados), 1)
        self.assertEqual(sum(isinstance(resultado, str) for resultado in resultados), 1)
        self.assertEqual(self._contar(Vehiculo), 1)

    def test_ingreso_por_minuto_y_diario(self):
        for patente, modalidad in [("ABCD12", "minuto"), ("EFGH34", "diaria")]:
            with self.subTest(modalidad=modalidad):
                vehiculo = self._crear_vehiculo(patente)
                resultado = ingresos.registrar_ingreso(
                    patente.lower(), self.fecha, modalidad
                )
                self.assertEqual(resultado["vehiculo_id"], vehiculo["id"])
                self.assertEqual(resultado["fecha_ingreso"], self.fecha)
                self.assertEqual(resultado["modalidad"], modalidad)
                self.assertIsNone(resultado["fecha_salida"])
                self.assertIsNone(resultado["suscripcion_id"])

    def test_ingreso_rechaza_vehiculo_inexistente(self):
        with self.assertRaisesRegex(ValueError, "No existe"):
            ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")
        self.assertEqual(self._contar(Estadia), 0)

    def test_ingreso_rechaza_fechas_invalidas(self):
        self._crear_vehiculo()
        fechas = [None, "2026-11-20", self.fecha.date(), self.fecha.replace(tzinfo=timezone.utc)]
        for fecha in fechas:
            with self.subTest(fecha=fecha):
                with self.assertRaisesRegex(ValueError, "datetime sin zona horaria"):
                    ingresos.registrar_ingreso("ABCD12", fecha, "minuto")
        self.assertEqual(self._contar(Estadia), 0)

    def test_ingreso_rechaza_modalidades_invalidas(self):
        self._crear_vehiculo()
        for modalidad in (None, "", "mensual", "otra", 1):
            with self.subTest(modalidad=modalidad):
                with self.assertRaisesRegex(ValueError, "modalidad"):
                    ingresos.registrar_ingreso("ABCD12", self.fecha, modalidad)
        self.assertEqual(self._contar(Estadia), 0)

    def test_estadia_activa_impide_un_segundo_ingreso(self):
        self._crear_vehiculo()
        ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")
        with self.assertRaisesRegex(ValueError, "estadía activa"):
            ingresos.registrar_ingreso("ABCD12", self.fecha, "diaria")
        self.assertEqual(self._contar(Estadia), 1)

    def test_permite_nuevo_ingreso_despues_de_una_salida(self):
        self._crear_vehiculo()
        anterior = ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")
        with self.sesiones() as sesion:
            sesion.get(Estadia, anterior["id"]).fecha_salida = self.fecha + timedelta(minutes=10)
            sesion.commit()

        nuevo = ingresos.registrar_ingreso(
            "ABCD12", self.fecha + timedelta(hours=1), "diaria"
        )
        self.assertNotEqual(anterior["id"], nuevo["id"])
        self.assertEqual(self._contar(Estadia), 2)

    def test_limites_de_vigencia_mensual(self):
        inicio = self.fecha
        termino = inicio + timedelta(days=30)
        casos = [
            (inicio - timedelta(microseconds=1), "diaria"),
            (inicio, "mensual"),
            (termino - timedelta(microseconds=1), "mensual"),
            (termino, "diaria"),
        ]
        for numero, (fecha, modalidad) in enumerate(casos):
            with self.subTest(fecha=fecha):
                patente = f"ABCD{numero:02d}"
                vehiculo = self._crear_vehiculo(patente)
                suscripcion_id = self._crear_suscripcion(vehiculo["id"], inicio, termino)
                resultado = ingresos.registrar_ingreso(patente, fecha, "diaria")
                self.assertEqual(resultado["modalidad"], modalidad)
                if modalidad == "mensual":
                    self.assertEqual(resultado["suscripcion_id"], suscripcion_id)
                else:
                    self.assertIsNone(resultado["suscripcion_id"])

    def test_cobertura_guardada_no_genera_otro_pago(self):
        vehiculo = self._crear_vehiculo()
        termino = self.fecha + timedelta(days=30)
        suscripcion_id = self._crear_suscripcion(vehiculo["id"], self.fecha, termino)
        resultado = ingresos.registrar_ingreso(
            "ABCD12", termino - timedelta(minutes=1), "minuto"
        )

        with self.sesiones() as sesion:
            estadia = sesion.get(Estadia, resultado["id"])
            self.assertEqual(estadia.modalidad, "mensual")
            self.assertEqual(estadia.suscripcion_id, suscripcion_id)
        self.assertEqual(self._contar(Pago), 1)

    def test_detecta_suscripciones_antiguas_superpuestas(self):
        vehiculo = self._crear_vehiculo()
        for _ in range(2):
            self._crear_suscripcion(
                vehiculo["id"], self.fecha, self.fecha + timedelta(days=30)
            )
        with self.assertRaisesRegex(ValueError, "superpuestas"):
            ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")
        self.assertEqual(self._contar(Estadia), 0)

    def test_fallo_de_commit_revierte_el_ingreso(self):
        self._crear_vehiculo()
        with patch.object(
            self.sesiones.class_, "commit", side_effect=RuntimeError("fallo de prueba")
        ):
            with self.assertRaisesRegex(RuntimeError, "fallo de prueba"):
                ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")
        self.assertEqual(self._contar(Estadia), 0)
        self.assertEqual(
            ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto")["modalidad"],
            "minuto",
        )

    def test_ingresos_simultaneos_para_el_mismo_vehiculo(self):
        self._crear_vehiculo()
        resultados = self._ejecutar_en_paralelo(
            Estadia,
            lambda: ingresos.registrar_ingreso("ABCD12", self.fecha, "minuto"),
        )
        self.assertEqual(sum(isinstance(resultado, dict) for resultado in resultados), 1)
        self.assertEqual(sum(isinstance(resultado, str) for resultado in resultados), 1)
        self.assertEqual(self._contar(Estadia), 1)

    def test_actualiza_base_anterior_conservando_estadias(self):
        self.indice.drop(bind=self.motor)
        vehiculo = self._crear_vehiculo()
        with self.sesiones() as sesion:
            sesion.add_all([
                Estadia(
                    vehiculo_id=vehiculo["id"],
                    fecha_ingreso=self.fecha - timedelta(days=2),
                    fecha_salida=self.fecha - timedelta(days=1),
                    modalidad="minuto",
                ),
                Estadia(
                    vehiculo_id=vehiculo["id"],
                    fecha_ingreso=self.fecha,
                    modalidad="diaria",
                ),
            ])
            sesion.commit()

        conexion.crear_tablas()
        conexion.crear_tablas()
        self.assertEqual(self._contar(Estadia), 2)
        nombres = {indice["name"] for indice in inspect(self.motor).get_indexes("estadias")}
        self.assertIn("estadia_activa_por_vehiculo", nombres)

        with self.sesiones() as sesion:
            sesion.add(Estadia(
                vehiculo_id=vehiculo["id"],
                fecha_ingreso=self.fecha,
                modalidad="minuto",
            ))
            with self.assertRaises(IntegrityError):
                sesion.commit()
            sesion.rollback()
        self.assertEqual(self._contar(Estadia), 2)

    def test_base_anterior_con_ingresos_duplicados_informa_y_conserva_datos(self):
        self.indice.drop(bind=self.motor)
        vehiculo = self._crear_vehiculo()
        with self.sesiones() as sesion:
            for _ in range(2):
                sesion.add(Estadia(
                    vehiculo_id=vehiculo["id"],
                    fecha_ingreso=self.fecha,
                    modalidad="minuto",
                ))
            sesion.commit()

        with self.assertRaisesRegex(ValueError, "más de una estadía activa"):
            conexion.crear_tablas()
        self.assertEqual(self._contar(Estadia), 2)
        self.assertEqual(self._contar(Vehiculo), 1)

    def test_main_entrega_las_funciones_reales_a_la_ventana(self):
        with patch.object(main, "VentanaPrincipal") as ventana:
            main.main()
            registrar, listar, ingresar = ventana.call_args.args
            self.assertIs(registrar, vehiculos.registrar_vehiculo)
            self.assertIs(listar, vehiculos.listar_vehiculos)
            self.assertIs(ingresar, ingresos.registrar_ingreso)
            resultado = registrar("ABCD12", "Ana", None, "ana@example.com")
            self.assertEqual(listar(), [resultado])
            estadia = ingresar("ABCD12", self.fecha, "minuto")
            self.assertEqual(estadia["vehiculo_id"], resultado["id"])
            self.assertEqual(self._contar(Estadia), 1)
            ventana.return_value.mainloop.assert_called_once()

    def test_main_conecta_las_pantallas_a_sqlite_y_deja_salidas_pendiente(self):
        def comprobar(ventana):
            ventana.withdraw()
            try:
                with (
                    patch("tkinter.messagebox.showinfo"),
                    patch("tkinter.messagebox.showerror") as error,
                ):
                    pantalla = ventana.pantalla_vehiculos
                    pantalla._variables["patente"].set("ABCD12")
                    pantalla._variables["nombre_responsable"].set("Ana")
                    pantalla._variables["correo"].set("ana@example.com")
                    pantalla.registrar()

                    pantalla = ventana.pantalla_ingresos
                    pantalla._variables["patente"].set("ABCD12")
                    pantalla._variables["fecha"].set("20/11/2026 10:00:00")
                    pantalla.registrar()

                    error.assert_not_called()
                    self.assertEqual(self._contar(Vehiculo), 1)
                    self.assertEqual(self._contar(Estadia), 1)
                    self.assertEqual(
                        ventana._pestanas.tab(ventana.pantalla_ingresos, "state"),
                        "normal",
                    )
                    self.assertEqual(
                        ventana._pestanas.tab(ventana.pantalla_salidas, "state"),
                        "disabled",
                    )
            finally:
                ventana.destroy()

        with patch.object(main.VentanaPrincipal, "mainloop", comprobar):
            main.main()

    def test_main_informa_datos_anteriores_inconsistentes(self):
        with (
            patch.object(main, "crear_tablas", side_effect=ValueError("Estadías duplicadas")),
            patch.object(main.messagebox, "showerror") as mensaje,
            patch.object(main, "VentanaPrincipal") as ventana,
        ):
            main.main()
            mensaje.assert_called_once_with(
                "No se pudo preparar la base de datos", "Estadías duplicadas"
            )
            ventana.assert_not_called()

    def test_pantalla_vehiculos_guarda_y_muestra_datos_reales(self):
        raiz = tk.Tk()
        raiz.withdraw()
        try:
            with (
                patch("interfaz.pantalla_vehiculos.messagebox.showinfo") as informacion,
                patch("interfaz.pantalla_vehiculos.messagebox.showerror") as error,
            ):
                pantalla = PantallaVehiculos(
                    raiz, vehiculos.registrar_vehiculo, vehiculos.listar_vehiculos
                )
                pantalla._variables["patente"].set(" abcd12 ")
                pantalla._variables["nombre_responsable"].set("Ana")
                pantalla._variables["correo"].set("ana@example.com")
                pantalla.registrar()

                tabla = pantalla._tabla
                filas = [tabla.item(fila, "values") for fila in tabla.get_children()]
                self.assertEqual(filas, [("1", "ABCD12", "Ana", "", "ana@example.com")])
                self.assertEqual(self._contar(Vehiculo), 1)
                informacion.assert_called_once()
                error.assert_not_called()
        finally:
            raiz.destroy()


if __name__ == "__main__":
    unittest.main()
