"""Modelo persistente de clientes."""
from base_datos import Registro, RUTA_BD


class Cliente(Registro):
    """Cliente con diccionario de datos y operaciones CRUD heredadas."""

    tabla = "clientes"

    def __init__(self, clave, nombre, direccion, correo_electronico, telefono, ruta_bd=RUTA_BD):
        """Inicializa los campos del cliente y la ubicación de SQLite."""
        self.ruta_bd = ruta_bd
        self.datos = dict(clave=clave, nombre=nombre, direccion=direccion,
                          correo_electronico=correo_electronico, telefono=telefono)
