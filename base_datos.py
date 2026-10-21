"""Esquema, conexiones y operaciones comunes de Happy Burger."""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3

RUTA_BD = Path(__file__).resolve().parent / "happy_burger.db"


def dinero(valor):
    """Valida un precio no negativo con hasta dos decimales."""
    try:
        numero = Decimal(str(valor))
        if not numero.is_finite() or not 0 <= numero <= Decimal("999999999.99"):
            raise ValueError
        if numero != numero.quantize(Decimal("0.01")):
            raise ValueError
        return numero.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("Precio inválido: usa de 0 a 999999999.99 y hasta dos decimales.") from None


@contextmanager
def conectar(ruta=RUTA_BD, solo_lectura=False):
    """Abre una transacción; en lectura no crea ni modifica la base existente."""
    if solo_lectura:
        con = sqlite3.connect(Path(ruta).resolve().as_uri() + "?mode=ro", uri=True)
    else:
        con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        with con:
            yield con
    finally:
        con.close()


def inicializar(ruta=RUTA_BD):
    """Crea las tablas sin borrar registros existentes."""
    with conectar(ruta) as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                clave TEXT PRIMARY KEY NOT NULL, nombre TEXT NOT NULL,
                direccion TEXT NOT NULL, correo_electronico TEXT NOT NULL,
                telefono TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS menu (
                clave TEXT PRIMARY KEY NOT NULL, nombre TEXT NOT NULL,
                precio INTEGER NOT NULL CHECK(precio >= 0)
            );
            CREATE TABLE IF NOT EXISTS pedido (
                pedido TEXT PRIMARY KEY NOT NULL,
                cliente TEXT NOT NULL REFERENCES clientes(clave),
                producto TEXT NOT NULL REFERENCES menu(clave),
                precio INTEGER NOT NULL CHECK(precio >= 0),
                cantidad INTEGER NOT NULL CHECK(cantidad > 0),
                importe INTEGER NOT NULL CHECK(importe >= 0),
                estado TEXT NOT NULL CHECK(estado IN ('activo', 'cancelado'))
            );
        """)


class Registro:
    """Comparte CRUD parametrizado entre clientes y productos."""

    def _validar(self, datos):
        """Valida texto obligatorio y convierte precios a centavos."""
        resultado = dict(datos)
        for campo, valor in resultado.items():
            if campo == "precio":
                resultado[campo] = int(dinero(valor) * 100)
            elif not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"{campo} no puede estar vacío.")
        return resultado

    def agregar(self):
        """Guarda un registro; SQLite rechaza claves duplicadas."""
        datos = self._validar(self.datos)
        campos = ", ".join(datos)
        marcas = ", ".join("?" for _ in datos)
        with conectar(self.ruta_bd) as con:
            con.execute(f"INSERT INTO {self.tabla} ({campos}) VALUES ({marcas})",
                        tuple(datos.values()))

    @classmethod
    def consultar(cls, clave=None, ruta_bd=RUTA_BD):
        """Devuelve diccionarios, filtrados opcionalmente por clave."""
        with conectar(ruta_bd) as con:
            sql = f"SELECT * FROM {cls.tabla}"
            filas = con.execute(
                sql + " ORDER BY clave" if clave is None else sql + " WHERE clave = ?",
                () if clave is None else (clave,)).fetchall()
        datos = [dict(fila) for fila in filas]
        if cls.tabla == "menu":
            for fila in datos:
                fila["precio"] = Decimal(fila["precio"]) / 100
        return datos

    def actualizar(self, cambios):
        """Actualiza campos permitidos conservando la clave original."""
        if not cambios or not set(cambios) <= (set(self.datos) - {"clave"}):
            raise ValueError("Campos de actualización inválidos.")
        datos = self._validar(cambios)
        asignaciones = ", ".join(f"{campo} = ?" for campo in datos)
        with conectar(self.ruta_bd) as con:
            cursor = con.execute(f"UPDATE {self.tabla} SET {asignaciones} WHERE clave = ?",
                                 (*datos.values(), self.datos["clave"]))
            if cursor.rowcount == 0:
                raise ValueError("El registro no existe.")
        self.datos.update(cambios)

    def eliminar(self):
        """Elimina un registro que no esté referenciado por pedidos."""
        with conectar(self.ruta_bd) as con:
            cursor = con.execute(f"DELETE FROM {self.tabla} WHERE clave = ?",
                                 (self.datos["clave"],))
            if cursor.rowcount == 0:
                raise ValueError("El registro no existe.")
