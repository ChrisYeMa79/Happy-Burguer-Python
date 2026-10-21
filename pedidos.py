"""Pedidos persistentes y tickets de Happy Burger."""
from pathlib import Path
from uuid import uuid4
from decimal import Decimal
from base_datos import RUTA_BD, conectar

RUTA_TICKETS = Path(__file__).resolve().parent / "tickets"


class Pedido:
    """Pedido cuyo precio se obtiene siempre desde SQLite."""

    def __init__(self, pedido, cliente, producto, precio=None, cantidad=1,
                 ruta_bd=RUTA_BD, ruta_tickets=RUTA_TICKETS):
        """Recibe claves; precio se acepta por compatibilidad pero se ignora al crear."""
        self.datos = dict(pedido=pedido, cliente=cliente, producto=producto, precio=precio)
        self.cantidad = cantidad
        self.ruta_bd = ruta_bd
        self.ruta_tickets = Path(ruta_tickets)

    def crear(self):
        """Consulta referencias, guarda el pedido y devuelve la ruta del ticket UTF-8."""
        if any(not isinstance(v, str) or not v.strip()
               for v in (self.datos["pedido"], self.datos["cliente"], self.datos["producto"])):
            raise ValueError("Las claves del pedido, cliente y producto son obligatorias.")
        if type(self.cantidad) is not int or not 0 < self.cantidad <= 1000000:
            raise ValueError("La cantidad debe ser un entero entre 1 y 1000000.")
        ticket = None
        try:
            with conectar(self.ruta_bd) as con:
                con.execute("BEGIN IMMEDIATE")
                cliente = con.execute("SELECT * FROM clientes WHERE clave = ?",
                                      (self.datos["cliente"],)).fetchone()
                producto = con.execute("SELECT * FROM menu WHERE clave = ?",
                                       (self.datos["producto"],)).fetchone()
                if cliente is None or producto is None:
                    raise ValueError("El cliente y el producto deben existir.")
                precio = producto["precio"]
                importe = precio * self.cantidad
                con.execute("INSERT INTO pedido VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (self.datos["pedido"], self.datos["cliente"], self.datos["producto"],
                             precio, self.cantidad, importe, "activo"))
                self.ruta_tickets.mkdir(parents=True, exist_ok=True)
                # UUID evita usar claves del usuario como rutas o sobrescribir tickets.
                destino = self.ruta_tickets / f"ticket_{uuid4().hex}.txt"
                with destino.open("x", encoding="utf-8") as archivo:
                    ticket = destino
                    archivo.write(
                        f"Happy Burger\nPedido: {self.datos['pedido']}\n"
                        f"Cliente: {cliente['clave']} - {cliente['nombre']}\n"
                        f"Producto: {producto['clave']} - {producto['nombre']}\n"
                        f"Precio unitario: ${Decimal(precio) / 100:.2f}\n"
                        f"Cantidad: {self.cantidad}\nImporte total: ${Decimal(importe) / 100:.2f}\n"
                        "Estado al emitir: activo\n")
        except Exception:
            if ticket is not None:
                ticket.unlink(missing_ok=True)
            raise
        self.datos.update(precio=Decimal(precio) / 100, cantidad=self.cantidad,
                          importe=Decimal(importe) / 100, estado="activo")
        return ticket

    def cancelar(self):
        """Marca un pedido activo como cancelado y conserva el historial."""
        with conectar(self.ruta_bd) as con:
            cursor = con.execute(
                "UPDATE pedido SET estado = 'cancelado' WHERE pedido = ? AND estado = 'activo'",
                (self.datos["pedido"],))
            if cursor.rowcount == 0:
                raise ValueError("El pedido no existe o ya está cancelado.")
        self.datos["estado"] = "cancelado"

    @staticmethod
    def consultar(numero, ruta_bd=RUTA_BD):
        """Consulta solo un pedido sin datos de contacto, en modo de solo lectura.

        Las claves existentes son texto (por ejemplo O1), no solo números.
        Devuelve un diccionario o None; nunca enumera otros pedidos.
        """
        if not isinstance(numero, str):
            raise ValueError("Introduce el número de pedido indicado en tu ticket.")
        numero = numero.strip()
        if not numero or len(numero) > 128 or not numero.isprintable():
            raise ValueError("Introduce un número de pedido válido de 1 a 128 caracteres, sin saltos de línea.")
        with conectar(ruta_bd, solo_lectura=True) as con:
            fila = con.execute(
                """SELECT p.pedido, c.nombre AS cliente, m.nombre AS producto,
                          p.cantidad, p.precio, p.importe, p.estado
                   FROM pedido AS p
                   LEFT JOIN clientes AS c ON c.clave = p.cliente
                   LEFT JOIN menu AS m ON m.clave = p.producto
                   WHERE p.pedido = ?""", (numero,)).fetchone()
        if fila is None:
            return None
        datos = dict(fila)
        for campo in ("precio", "importe"):
            if datos[campo] is not None:
                datos[campo] = Decimal(datos[campo]) / 100
        return datos
