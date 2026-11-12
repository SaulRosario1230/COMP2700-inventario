"""Pruebas automatizadas de los controles de COMP 2700."""
import json
import tempfile
import unittest
from pathlib import Path

import app
from seguridad import crear_hash


class PruebasInventario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = Path(self.tmp.name)
        self.old_paths = (app.DATOS, app.USUARIOS, app.LOG)
        app.DATOS = raiz / "inventario.json"
        app.USUARIOS = raiz / "usuarios.json"
        app.LOG = raiz / "auditoria.jsonl"
        app._SESIONES_VALIDAS.clear()

        app.DATOS.write_text(json.dumps([
            {"id": "P001", "nombre": "Teclado", "cantidad": 10}
        ]), encoding="utf-8")
        app.USUARIOS.write_text(json.dumps([
            {"usuario": "admin", "rol": "admin", "hash": crear_hash("AdminDemo2700!")},
            {"usuario": "user", "rol": "user", "hash": crear_hash("UserDemo2700!")}
        ]), encoding="utf-8")

    def tearDown(self):
        app._SESIONES_VALIDAS.clear()
        app.DATOS, app.USUARIOS, app.LOG = self.old_paths
        self.tmp.cleanup()

    def cantidad(self):
        return app.cargar_inventario()[0]["cantidad"]

    def test_admin_puede_modificar(self):
        sesion = app.autenticar("admin", "AdminDemo2700!")
        self.assertTrue(app.modificar_cantidad(sesion, "P001", "99"))
        self.assertEqual(self.cantidad(), 99)

    def test_usuario_no_puede_modificar(self):
        sesion = app.autenticar("user", "UserDemo2700!")
        self.assertFalse(app.modificar_cantidad(sesion, "P001", "99"))
        self.assertEqual(self.cantidad(), 10)

    def test_sesion_none_es_rechazada(self):
        self.assertFalse(app.modificar_cantidad(None, "P001", "99"))
        self.assertEqual(self.cantidad(), 10)

    def test_diccionario_fabricado_es_rechazado(self):
        sesion_falsa = {"usuario": "intruso", "rol": "admin"}
        self.assertFalse(app.modificar_cantidad(sesion_falsa, "P001", "99"))
        self.assertEqual(self.cantidad(), 10)

    def test_cantidades_invalidas_no_modifican(self):
        sesion = app.autenticar("admin", "AdminDemo2700!")
        for entrada in ("abc", "", "-1", "1001", "1.5"):
            with self.subTest(entrada=entrada):
                self.assertFalse(app.modificar_cantidad(sesion, "P001", entrada))
                self.assertEqual(self.cantidad(), 10)

    def test_producto_inexistente_no_se_crea(self):
        sesion = app.autenticar("admin", "AdminDemo2700!")
        self.assertFalse(app.modificar_cantidad(sesion, "P999", "20"))
        self.assertEqual(len(app.cargar_inventario()), 1)

    def test_auditoria_es_jsonl(self):
        sesion = app.autenticar("admin", "AdminDemo2700!")
        app.modificar_cantidad(sesion, "P001", "11")
        lineas = app.LOG.read_text(encoding="utf-8").splitlines()
        eventos = [json.loads(linea) for linea in lineas]
        self.assertTrue(any(e["accion"] == "modificar" and e["resultado"] == "exitoso"
                            for e in eventos))
        self.assertTrue(all("clave" not in json.dumps(e) and "hash" not in json.dumps(e)
                            for e in eventos))


if __name__ == "__main__":
    unittest.main(verbosity=2)
