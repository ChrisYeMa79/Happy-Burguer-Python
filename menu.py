"""Modelo persistente de productos del menú."""
from base_datos import Registro, RUTA_BD


class Producto(Registro):
    """Producto con diccionario de datos y operaciones CRUD heredadas."""

    tabla = "menu"

    def __init__(self, clave, nombre, precio, ruta_bd=RUTA_BD):
        """Inicializa los campos del producto y la ubicación de SQLite."""
        self.ruta_bd = ruta_bd
        self.datos = dict(clave=clave, nombre=nombre, precio=precio)
