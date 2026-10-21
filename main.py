"""Menú de consola de Happy Burger."""
import sqlite3
from decimal import Decimal, InvalidOperation
from base_datos import RUTA_BD, inicializar
from clientes import Cliente
from menu import Producto
from pedidos import Pedido, RUTA_TICKETS


def solicitar_pedido():
    """Conserva el cálculo independiente del avance 1 sin persistencia."""
    nombre = input("Nombre del producto: ").strip()
    while not nombre:
        print("El nombre no puede estar vacío.")
        nombre = input("Nombre del producto: ").strip()
    while True:
        try:
            precio = Decimal(input("Precio del producto: "))
            if not precio.is_finite() or precio < 0:
                raise ValueError
            break
        except (InvalidOperation, ValueError):
            print("Ingresa un precio numérico mayor o igual a cero.")
    while True:
        try:
            cantidad = int(input("Cantidad: "))
            if cantidad <= 0:
                raise ValueError
            break
        except ValueError:
            print("Ingresa una cantidad entera mayor que cero.")
    total = precio * cantidad
    print(f"Producto: {nombre} | Cantidad: {cantidad} | Importe total: ${total:.2f}")
    return total


def gestionar_catalogo(modelo, ruta_bd):
    """Ejecuta una operación CRUD sobre clientes o productos."""
    opcion = input("1. Agregar\n2. Consultar\n3. Actualizar\n4. Eliminar\n0. Volver\nOpción: ").strip()
    if opcion == "0":
        return
    if opcion not in {"1", "2", "3", "4"}:
        raise ValueError("Opción inválida.")
    if opcion == "2":
        clave = input("Clave (vacío para todos): ").strip()
        filas = modelo.consultar(clave or None, ruta_bd)
        for fila in filas:
            print(fila)
        if not filas:
            print("Sin registros.")
        return
    clave = input("Clave: ").strip()
    campos = (["nombre", "direccion", "correo_electronico", "telefono"]
              if modelo is Cliente else ["nombre", "precio"])
    if opcion == "1":
        datos = {campo: input(f"{campo}: ").strip() for campo in campos}
        modelo(clave=clave, ruta_bd=ruta_bd, **datos).agregar()
    else:
        filas = modelo.consultar(clave, ruta_bd)
        if not filas:
            raise ValueError("El registro no existe.")
        registro = modelo(**filas[0], ruta_bd=ruta_bd)
        if opcion == "3":
            print("Deja vacío para conservar el valor actual.")
            cambios = {}
            for campo in campos:
                valor = input(f"{campo} [{filas[0][campo]}]: ").strip()
                if valor:
                    cambios[campo] = valor
            registro.actualizar(cambios)
        else:
            registro.eliminar()
    print("Operación completada.")


def gestionar_pedidos(ruta_bd, ruta_tickets):
    """Crea pedidos desde claves existentes o cancela por identificador."""
    opcion = input("1. Crear pedido\n2. Cancelar pedido\n0. Volver\nOpción: ").strip()
    if opcion == "0":
        return
    if opcion not in {"1", "2"}:
        raise ValueError("Opción inválida.")
    clave = input("Clave del pedido: ").strip()
    if opcion == "2":
        Pedido(clave, None, None, ruta_bd=ruta_bd).cancelar()
        print("Pedido cancelado.")
    else:
        cliente = input("Clave del cliente: ").strip()
        producto = input("Clave del producto: ").strip()
        cantidad = int(input("Cantidad: "))
        pedido = Pedido(clave, cliente, producto, cantidad=cantidad,
                        ruta_bd=ruta_bd, ruta_tickets=ruta_tickets)
        ticket = pedido.crear()
        print(f"Importe total: ${pedido.datos['importe']:.2f}\nTicket: {ticket}")


def main(ruta_bd=RUTA_BD, ruta_tickets=RUTA_TICKETS):
    """Inicializa SQLite y mantiene el menú hasta seleccionar Salir."""
    try:
        inicializar(ruta_bd)
    except (sqlite3.Error, OSError) as error:
        print(f"No se pudo abrir la base de datos: {error}")
        return
    while True:
        try:
            print("\nHappy Burger\n1. Pedidos\n2. Clientes\n3. Menú\n4. Salir")
            opcion = input("Selecciona una opción: ").strip()
            if opcion == "1":
                gestionar_pedidos(ruta_bd, ruta_tickets)
            elif opcion == "2":
                gestionar_catalogo(Cliente, ruta_bd)
            elif opcion == "3":
                gestionar_catalogo(Producto, ruta_bd)
            elif opcion == "4":
                print("Gracias por visitar Happy Burger.")
                break
            else:
                print("Opción inválida. Selecciona del 1 al 4.")
        except sqlite3.IntegrityError:
            print("No se pudo completar: clave duplicada o registro asociado a pedidos.")
        except (ValueError, sqlite3.Error, OSError) as error:
            print(f"No se pudo completar la operación: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nPrograma finalizado.")
            break


if __name__ == "__main__":
    main()
