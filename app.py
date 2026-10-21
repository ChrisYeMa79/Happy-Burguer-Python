"""Consulta web local de pedidos; la administración permanece en main.py."""
import sqlite3
from flask import Flask, render_template, request
from base_datos import RUTA_BD
from pedidos import Pedido


def crear_app(ruta_bd=RUTA_BD):
    """Crea una aplicación configurable sin inicializar ni modificar SQLite."""
    app = Flask(__name__)
    app.config.update(DATABASE=ruta_bd, DEBUG=False, MAX_CONTENT_LENGTH=8192)

    @app.template_filter("moneda")
    def moneda(valor):
        """Formatea Decimal sin convertir importes grandes a punto flotante."""
        return f"${valor:.2f}"

    @app.after_request
    def proteger_respuesta(respuesta):
        """Evita caché de resultados y restringe recursos al propio sitio."""
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        respuesta.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'")
        return respuesta

    @app.route("/", methods=["GET", "POST"])
    def consultar():
        """Valida el formulario y presenta un único pedido o un error comprensible."""
        numero = ""
        pedido = None
        mensaje = None
        estado = 200
        if request.method == "POST":
            numero = request.form.get("numero", "")
            try:
                pedido = Pedido.consultar(numero, app.config["DATABASE"])
                if pedido is None:
                    mensaje = "No encontramos un pedido con ese número. Revisa tu ticket."
                    estado = 404
            except ValueError as error:
                mensaje = str(error)
                estado = 400
            except (sqlite3.Error, OSError):
                mensaje = "La consulta no está disponible en este momento. Intenta más tarde."
                estado = 503
        return render_template("consulta.html", numero=numero[:128], pedido=pedido,
                               mensaje=mensaje), estado

    @app.errorhandler(413)
    def formulario_grande(error):
        """Muestra un mensaje para formularios que exceden el límite permitido."""
        return render_template("consulta.html", numero="", pedido=None,
                               mensaje="El formulario es demasiado grande. Introduce solo el número de pedido."), 413

    return app


app = crear_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
