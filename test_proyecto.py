"""Pruebas aisladas de consola, CRUD, persistencia y tickets."""
import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from base_datos import conectar, inicializar
from clientes import Cliente
from menu import Producto
from pedidos import Pedido
from main import main, solicitar_pedido


class PruebasProyecto(unittest.TestCase):
    """Usa una base y tickets temporales dentro del proyecto."""

    def setUp(self):
        """Prepara una base vacía por prueba."""
        self.temporal = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.bd = self.raiz / "prueba.db"
        self.tickets = self.raiz / "tickets"
        inicializar(self.bd)
        self.cliente = Cliente("C1", "Ana", "Calle 1", "ana@example.com", "555", self.bd)
        self.producto = Producto("P1", "Hamburguesa", "45.50", self.bd)

    def sembrar(self):
        """Guarda un cliente y un producto reutilizables."""
        self.cliente.agregar()
        self.producto.agregar()

    def pedido(self, clave="O1", **opciones):
        """Construye un pedido con rutas aisladas."""
        return Pedido(clave, "C1", "P1", ruta_bd=self.bd,
                      ruta_tickets=self.tickets, **opciones)

    def test_calculo_avance_1(self):
        with patch("builtins.input", side_effect=["Hamburguesa", "45.50", "3"]):
            with redirect_stdout(io.StringIO()) as salida:
                self.assertEqual(solicitar_pedido(), Decimal("136.50"))
        self.assertIn("$136.50", salida.getvalue())

    def test_reintentos_avance_1(self):
        entradas = ["", "Papas", "abc", "NaN", "Infinity", "-1", "10.25", "0", "1.5", "2"]
        with patch("builtins.input", side_effect=entradas):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(solicitar_pedido(), Decimal("20.50"))

    def test_crud_clientes_y_persistencia(self):
        self.cliente.agregar()
        self.cliente.actualizar({"nombre": "Ana María", "telefono": "123"})
        inicializar(self.bd)
        filas = Cliente.consultar("C1", self.bd)
        self.assertEqual(filas[0]["nombre"], "Ana María")
        self.assertEqual(filas[0]["telefono"], "123")
        self.assertEqual(len(Cliente.consultar(ruta_bd=self.bd)), 1)
        Cliente(**filas[0], ruta_bd=self.bd).eliminar()
        self.assertEqual(Cliente.consultar("C1", self.bd), [])

    def test_crud_productos_y_persistencia(self):
        self.producto.agregar()
        self.producto.actualizar({"precio": "60.10", "nombre": "Doble"})
        inicializar(self.bd)
        filas = Producto.consultar("P1", self.bd)
        self.assertEqual(filas[0]["precio"], Decimal("60.10"))
        self.assertEqual(filas[0]["nombre"], "Doble")
        Producto(**filas[0], ruta_bd=self.bd).eliminar()
        self.assertEqual(Producto.consultar(ruta_bd=self.bd), [])

    def test_pedido_precio_bd_ticket_y_cancelacion(self):
        self.sembrar()
        pedido = self.pedido(precio="0.01", cantidad=3)
        ticket = pedido.crear()
        texto = ticket.read_text(encoding="utf-8")
        for esperado in ["O1", "Ana", "Hamburguesa", "$45.50", "Cantidad: 3", "$136.50"]:
            self.assertIn(esperado, texto)
        self.assertEqual(pedido.datos["importe"], Decimal("136.50"))
        self.producto.actualizar({"precio": "99"})
        inicializar(self.bd)
        with conectar(self.bd) as con:
            fila = con.execute("SELECT * FROM pedido WHERE pedido = ?", ("O1",)).fetchone()
            self.assertEqual((fila["precio"], fila["importe"]), (4550, 13650))
        pedido.cancelar()
        with conectar(self.bd) as con:
            self.assertEqual(con.execute("SELECT estado FROM pedido").fetchone()[0], "cancelado")
        with self.assertRaises(ValueError):
            pedido.cancelar()
        self.assertTrue(ticket.exists())

    def test_duplicados_y_referencias_protegidas(self):
        self.sembrar()
        for registro in [self.cliente, self.producto]:
            with self.assertRaises(sqlite3.IntegrityError):
                registro.agregar()
        self.pedido().crear()
        with self.assertRaises(sqlite3.IntegrityError):
            self.pedido().crear()
        self.assertEqual(len(list(self.tickets.glob("*.txt"))), 1)
        for registro in [self.cliente, self.producto]:
            with self.assertRaises(sqlite3.IntegrityError):
                registro.eliminar()

    def test_pedido_referencias_y_cantidades_invalidas(self):
        with self.assertRaises(ValueError):
            self.pedido().crear()
        self.sembrar()
        for cantidad in [0, -1, 1.5, True, 1000001]:
            with self.subTest(cantidad=cantidad), self.assertRaises(ValueError):
                self.pedido(cantidad=cantidad).crear()
        with self.assertRaises(ValueError):
            Pedido("O1", "C1", "inexistente", ruta_bd=self.bd).crear()
        with conectar(self.bd) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedido").fetchone()[0], 0)

    def test_validacion_y_registros_inexistentes(self):
        for precio in ["NaN", "Infinity", "-1", "1.001", "abc"]:
            with self.subTest(precio=precio), self.assertRaises(ValueError):
                Producto("P2", "Papas", precio, self.bd).agregar()
        for operacion in [self.cliente.eliminar, lambda: self.cliente.actualizar({"nombre": "X"}),
                          lambda: self.pedido().cancelar(),
                          lambda: self.cliente.actualizar({"nombre = ?; DROP TABLE clientes;--": "X"}),
                          lambda: Cliente("", "", "", "", "", self.bd).agregar()]:
            with self.assertRaises(ValueError):
                operacion()

    def test_sql_parametrizado(self):
        clave = "C'; DROP TABLE clientes;--"
        cliente = Cliente(clave, "O'Connor", "Calle", "a@b.com", "123", self.bd)
        cliente.agregar()
        self.assertEqual(Cliente.consultar(clave, self.bd)[0]["nombre"], "O'Connor")
        cliente.actualizar({"nombre": "D'Angelo"})
        cliente.eliminar()
        self.assertEqual(Cliente.consultar(ruta_bd=self.bd), [])

    def test_fallo_ticket_revierte_pedido(self):
        self.sembrar()
        self.tickets.write_text("Esto es un archivo, no una carpeta.", encoding="utf-8")
        with self.assertRaises(OSError):
            self.pedido().crear()
        with conectar(self.bd) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM pedido").fetchone()[0], 0)

    def test_clave_pedido_no_es_ruta(self):
        self.sembrar()
        ticket = self.pedido("../../fuera").crear()
        self.assertEqual(ticket.parent, self.tickets)
        self.assertTrue(ticket.name.startswith("ticket_"))

    def test_consola_integrada(self):
        entradas = [
            "9", "2", "1", "C1", "Ana", "Calle", "a@b.com", "123",
            "3", "1", "P1", "Hamburguesa", "45.50",
            "2", "2", "", "3", "3", "P1", "", "50",
            "1", "1", "O1", "C1", "P1", "2",
            "1", "2", "O1",
            "2", "4", "C1",
            "3", "0", "4",
        ]
        with patch("builtins.input", side_effect=entradas):
            with redirect_stdout(io.StringIO()) as salida:
                main(self.bd, self.tickets)
        texto = salida.getvalue()
        for esperado in ["Opción inválida", "$100.00", "Pedido cancelado", "registro asociado", "Gracias"]:
            self.assertIn(esperado, texto)
        self.assertEqual(len(list(self.tickets.glob("*.txt"))), 1)

    def test_consola_error_y_continuacion(self):
        with patch("builtins.input", side_effect=["1", "1", "O1", "C1", "P1", "abc", "4"]):
            with redirect_stdout(io.StringIO()) as salida:
                main(self.bd, self.tickets)
        self.assertIn("No se pudo completar", salida.getvalue())
        self.assertIn("Gracias", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
