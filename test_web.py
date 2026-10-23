"""Pruebas web con SQLite y tickets temporales, sin alterar datos reales."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app import crear_app
from base_datos import conectar, inicializar
from clientes import Cliente
from menu import Producto
from pedidos import Pedido


class PruebasWeb(unittest.TestCase):
    """Verifica consultas, privacidad, errores y ausencia de escrituras web."""

    def setUp(self):
        """Prepara pedidos activos y cancelados en un directorio aislado."""
        temporal = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(temporal.cleanup)
        self.raiz = Path(temporal.name)
        self.bd = self.raiz / "prueba.db"
        inicializar(self.bd)
        Cliente("C1", "Ana", "Dirección privada", "privado@example.com", "5559998888", self.bd).agregar()
        Cliente("C2", "Otro cliente privado", "Otra dirección", "otro@example.com", "12345", self.bd).agregar()
        self.producto = Producto("P1", "Hamburguesa", "45.50", self.bd)
        self.producto.agregar()
        self.pedido = Pedido("O1", "C1", "P1", cantidad=3, ruta_bd=self.bd,
                             ruta_tickets=self.raiz / "tickets")
        self.pedido.crear()
        Pedido("002", "C2", "P1", ruta_bd=self.bd, ruta_tickets=self.raiz / "tickets").crear()
        self.app = crear_app(self.bd)
        self.app.config["TESTING"] = True
        self.cliente = self.app.test_client()

    def consultar(self, numero):
        """Envía el formulario mediante el cliente de pruebas Flask."""
        return self.cliente.post("/", data={"numero": numero})

    def test_inicio_y_estilos(self):
        """Verifica el formulario inicial, los estilos y la depuración desactivada."""
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        texto = respuesta.get_data(as_text=True)
        for esperado in ["Happy Burger", 'name="numero"', 'name="viewport"', 'lang="es"']:
            self.assertIn(esperado, texto)
        estilos = self.cliente.get("/static/estilos.css")
        self.addCleanup(estilos.close)
        self.assertEqual(estilos.status_code, 200)
        self.assertFalse(self.app.debug)

    def test_pedido_existente_y_presentacion(self):
        """Comprueba los detalles del pedido sin exponer datos de contacto."""
        respuesta = self.consultar("O1")
        self.assertEqual(respuesta.status_code, 200)
        texto = respuesta.get_data(as_text=True)
        for esperado in ["Pedido O1", "Ana", "Hamburguesa", "Cantidad</dt><dd>3",
                         "$45.50", "$136.50", "activo"]:
            self.assertIn(esperado, texto)
        for privado in ["Dirección privada", "privado@example.com", "5559998888",
                        "Otro cliente privado", "otro@example.com", "Pedido 002"]:
            self.assertNotIn(privado, texto)
        self.assertEqual(respuesta.headers["Cache-Control"], "no-store")

    def test_pedido_inexistente(self):
        """Verifica la respuesta 404 para un pedido inexistente."""
        respuesta = self.consultar("9999")
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("No encontramos un pedido", respuesta.get_data(as_text=True))

    def test_numeros_invalidos(self):
        """Verifica el rechazo de claves vacías, largas o con controles."""
        for numero in ["", "   ", "X" * 129, "O\n1", "O\x001"]:
            with self.subTest(numero=numero):
                respuesta = self.consultar(numero)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("válido", respuesta.get_data(as_text=True))
        self.assertEqual(self.cliente.post("/", data={}).status_code, 400)
        self.assertEqual(self.consultar("O1").status_code, 200)

    def test_claves_texto_y_ceros_iniciales(self):
        """Comprueba espacios exteriores y conservación de ceros iniciales."""
        self.assertEqual(self.consultar(" O1 ").status_code, 200)
        self.assertEqual(self.consultar("002").status_code, 200)
        self.assertEqual(self.consultar("2").status_code, 404)

    def test_creacion_rechaza_claves_invalidas_sin_escrituras(self):
        """Creación y web rechazan las mismas claves sin guardar pedidos ni tickets."""
        antes = self.bd.read_bytes()
        tickets = set((self.raiz / "tickets").iterdir())
        for clave in ["", "   ", "X" * 129, " O" + "X" * 128 + " ",
                      "O\n1", "O\r1", "O\t1", "O\x001", "O\x7f1"]:
            with self.subTest(clave=repr(clave)):
                pedido = Pedido(clave, "C1", "P1", ruta_bd=self.bd,
                                ruta_tickets=self.raiz / "tickets")
                with self.assertRaises(ValueError):
                    pedido.crear()
                self.assertEqual(self.consultar(clave).status_code, 400)
        self.assertEqual(antes, self.bd.read_bytes())
        self.assertEqual(tickets, set((self.raiz / "tickets").iterdir()))

    def test_creacion_normaliza_espacios_y_evita_duplicados(self):
        """La clave normalizada se conserva en SQLite, el objeto y el ticket."""
        pedido = Pedido("  NUEVO  ", "C1", "P1", ruta_bd=self.bd,
                        ruta_tickets=self.raiz / "tickets")
        ticket = pedido.crear()
        self.assertEqual(pedido.datos["pedido"], "NUEVO")
        self.assertIn("Pedido: NUEVO\n", ticket.read_text(encoding="utf-8"))
        for clave in ["NUEVO", "  NUEVO  "]:
            self.assertEqual(Pedido.consultar(clave, self.bd)["pedido"], "NUEVO")
            self.assertEqual(self.consultar(clave).status_code, 200)
        with conectar(self.bd, solo_lectura=True) as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM pedido WHERE pedido = ?", ("  NUEVO  ",)).fetchone()[0], 0)
        with self.assertRaises(sqlite3.IntegrityError):
            Pedido(" NUEVO ", "C1", "P1", ruta_bd=self.bd,
                   ruta_tickets=self.raiz / "tickets").crear()
        pedido.cancelar()
        self.assertEqual(Pedido.consultar("NUEVO", self.bd)["estado"], "cancelado")

    def test_creacion_claves_validas_consultables_en_web(self):
        """Conserva ceros iniciales, espacios internos y el límite de 128 caracteres."""
        for clave in ["X" * 128, "003", "Pedido con espacios"]:
            with self.subTest(clave=clave):
                Pedido(" " + clave + " ", "C1", "P1", ruta_bd=self.bd,
                       ruta_tickets=self.raiz / "tickets").crear()
                self.assertEqual(Pedido.consultar(clave, self.bd)["pedido"], clave)
                self.assertEqual(self.consultar(clave).status_code, 200)

    def test_cancelacion_y_precio_historico(self):
        """Comprueba el estado cancelado y el precio original en la consulta."""
        self.pedido.cancelar()
        self.producto.actualizar({"precio": "99.99"})
        texto = self.consultar("O1").get_data(as_text=True)
        self.assertIn("cancelado", texto)
        self.assertIn("$45.50", texto)
        self.assertIn("$136.50", texto)
        self.assertNotIn("$99.99", texto)

    def test_inyeccion_sql_no_devuelve_pedidos(self):
        """Comprueba que una entrada SQL no permita recuperar otros pedidos."""
        respuesta = self.consultar("' OR 1=1 --")
        self.assertEqual(respuesta.status_code, 404)
        self.assertNotIn("Pedido O1", respuesta.get_data(as_text=True))

    def test_escape_html(self):
        """Verifica el escape de HTML en entradas y datos almacenados."""
        with conectar(self.bd) as con:
            con.execute("UPDATE menu SET nombre = ? WHERE clave = ?",
                        ("<script>alert('x')</script>", "P1"))
        texto = self.consultar("O1").get_data(as_text=True)
        self.assertNotIn("<script>", texto)
        self.assertIn("&lt;script&gt;", texto)
        texto = self.consultar('<script>alert("x")</script>').get_data(as_text=True)
        self.assertNotIn("<script>", texto)

    def test_integridad_sin_modificaciones(self):
        """Verifica que las consultas conserven la base y su integridad."""
        antes = hashlib.sha256(self.bd.read_bytes()).hexdigest()
        for numero in ["O1", "002", "inexistente", "", "' OR 1=1 --"]:
            self.consultar(numero)
        despues = hashlib.sha256(self.bd.read_bytes()).hexdigest()
        self.assertEqual(antes, despues)
        with conectar(self.bd, solo_lectura=True) as con:
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedido").fetchone()[0], 2)
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("DELETE FROM pedido")

    def test_bd_ausente_no_se_crea_y_error_no_expone_rutas(self):
        """Comprueba que una base ausente no se cree ni revele su ruta."""
        ruta = self.raiz / "no_existe.db"
        cliente = crear_app(ruta).test_client()
        respuesta = cliente.post("/", data={"numero": "O1"})
        self.assertEqual(respuesta.status_code, 503)
        texto = respuesta.get_data(as_text=True)
        self.assertIn("no está disponible", texto)
        self.assertNotIn(str(ruta), texto)
        self.assertFalse(ruta.exists())

    def test_formulario_demasiado_grande(self):
        """Verifica la respuesta 413 ante un formulario excesivo."""
        respuesta = self.consultar("X" * 10000)
        self.assertEqual(respuesta.status_code, 413)
        self.assertIn("demasiado grande", respuesta.get_data(as_text=True))

    def test_importes_grandes_sin_perder_centavos(self):
        """Comprueba la presentación exacta de importes grandes."""
        self.producto.actualizar({"precio": "999999999.99"})
        Pedido("G1", "C1", "P1", cantidad=999999, ruta_bd=self.bd,
               ruta_tickets=self.raiz / "tickets").crear()
        self.assertIn("$999998999990000.01", self.consultar("G1").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
