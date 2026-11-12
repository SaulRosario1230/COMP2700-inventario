"""Aplicación educativa de inventario — COMP 2700.

La autorización se comprueba dentro de cada operación protegida.
Las sesiones válidas son objetos creados por este proceso; no basta con
fabricar un diccionario que diga tener rol de administrador.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from seguridad import crear_hash, verificar_clave

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "inventario.json"
USUARIOS = RAIZ / "usuarios.json"
LOG = RAIZ / "auditoria.jsonl"

# El registro mantiene la identidad de las sesiones y sus permisos reales.
# Una sesión creada manualmente no aparecerá en este registro.
class Sesion:
    """Identificador de sesión válido únicamente dentro de este proceso."""
    __slots__ = ()


_SESIONES_VALIDAS = {}


def _guardar_json_atomico(ruta, contenido):
    """Escribe un documento JSON completo y reemplaza el archivo al final."""
    temporal = ruta.with_name(ruta.name + ".tmp")
    texto = json.dumps(contenido, ensure_ascii=False, indent=2) + "\n"
    temporal.write_text(texto, encoding="utf-8")
    temporal.replace(ruta)


def cargar_inventario():
    """Carga y valida el inventario sin alterar archivos ausentes o dañados."""
    try:
        productos = json.loads(DATOS.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("No se encontró inventario.json; no se creó ni sobrescribió.") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("inventario.json contiene JSON inválido; el archivo no fue modificado.") from exc

    if not isinstance(productos, list):
        raise RuntimeError("El inventario debe ser una lista JSON.")
    for producto in productos:
        if not isinstance(producto, dict):
            raise RuntimeError("El inventario contiene un producto inválido.")
        if not all(campo in producto for campo in ("id", "nombre", "cantidad")):
            raise RuntimeError("Un producto no contiene los campos requeridos.")
        if not isinstance(producto["id"], str) or not isinstance(producto["nombre"], str):
            raise RuntimeError("El ID y el nombre del producto deben ser texto.")
        if type(producto["cantidad"]) is not int or not 0 <= producto["cantidad"] <= 1000:
            raise RuntimeError("El inventario contiene una cantidad fuera del rango permitido.")
    return productos


def guardar_inventario(productos):
    """Valida y guarda el documento completo de inventario."""
    if not isinstance(productos, list):
        raise ValueError("El inventario debe ser una lista.")
    for producto in productos:
        if (not isinstance(producto, dict)
                or not isinstance(producto.get("id"), str)
                or not isinstance(producto.get("nombre"), str)
                or type(producto.get("cantidad")) is not int
                or not 0 <= producto["cantidad"] <= 1000):
            raise ValueError("El inventario contiene un producto o cantidad inválidos.")
    _guardar_json_atomico(DATOS, productos)


def registrar_evento(usuario, accion, resultado, **detalles):
    """Añade un evento JSON por línea; no recibe ni registra credenciales."""
    evento = {
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "usuario": str(usuario)[:100],
        "accion": str(accion)[:50],
        "resultado": str(resultado)[:50],
        "detalles": detalles,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(evento, ensure_ascii=False) + "\n")


def _cargar_usuarios():
    """Carga usuarios y migra, una sola vez, claves legadas a hashes Argon2."""
    try:
        usuarios = json.loads(USUARIOS.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("No se encontró usuarios.json.") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("usuarios.json contiene JSON inválido; no fue modificado.") from exc

    if not isinstance(usuarios, list):
        raise RuntimeError("usuarios.json debe contener una lista.")
    modificados = False
    for usuario in usuarios:
        if not isinstance(usuario, dict) or not isinstance(usuario.get("usuario"), str):
            raise RuntimeError("Hay un registro de usuario inválido.")
        if usuario.get("rol") not in ("admin", "user"):
            raise RuntimeError("Hay un rol de usuario inválido.")
        if "hash" not in usuario and isinstance(usuario.get("clave"), str):
            usuario["hash"] = crear_hash(usuario["clave"])
            del usuario["clave"]
            modificados = True
        if not isinstance(usuario.get("hash"), str):
            raise RuntimeError("Un usuario no tiene un hash de contraseña válido.")
    if modificados:
        _guardar_json_atomico(USUARIOS, usuarios)
    return usuarios


def autenticar(nombre, clave):
    """Verifica credenciales y devuelve una sesión del proceso si son válidas."""
    if not isinstance(nombre, str) or not isinstance(clave, str):
        registrar_evento("desconocido", "login", "fallido")
        print("Credenciales incorrectas.")
        return None
    try:
        usuarios = _cargar_usuarios()
    except (OSError, RuntimeError) as exc:
        print(f"No se pudo cargar la información de usuarios: {exc}")
        return None

    for usuario in usuarios:
        if usuario["usuario"] == nombre and verificar_clave(usuario["hash"], clave):
            sesion = Sesion()
            _SESIONES_VALIDAS[sesion] = {
                "usuario": usuario["usuario"],
                "rol": usuario["rol"],
            }
            registrar_evento(nombre, "login", "exitoso")
            return sesion

    registrar_evento(nombre, "login", "fallido")
    print("Credenciales incorrectas.")
    return None


def _datos_sesion(sesion):
    """Devuelve los datos autorizados solo para una sesión registrada."""
    if not isinstance(sesion, Sesion):
        return None
    return _SESIONES_VALIDAS.get(sesion)


def cerrar_sesion(sesion):
    """Invalida una sesión existente."""
    return _SESIONES_VALIDAS.pop(sesion, None) is not None


def consultar_inventario(sesion):
    """Permite consultar el inventario a cualquier usuario autenticado."""
    datos = _datos_sesion(sesion)
    if datos is None:
        registrar_evento("desconocido", "consultar", "rechazado", motivo="sesion_invalida")
        print("Acceso rechazado: debe iniciar sesión.")
        return False
    try:
        productos = cargar_inventario()
    except (OSError, RuntimeError) as exc:
        print(f"No se pudo consultar el inventario: {exc}")
        registrar_evento(datos["usuario"], "consultar", "fallido", motivo="error_archivo")
        return False
    for producto in productos:
        print(producto["id"], producto["nombre"], producto["cantidad"])
    registrar_evento(datos["usuario"], "consultar", "exitoso")
    return True


def modificar_cantidad(sesion, identificador, entrada):
    """Solo admin puede cambiar cantidades enteras entre 0 y 1000."""
    datos = _datos_sesion(sesion)
    if datos is None:
        registrar_evento("desconocido", "modificar", "rechazado", motivo="sesion_invalida")
        print("Acceso rechazado: sesión inválida.")
        return False
    if datos["rol"] != "admin":
        registrar_evento(datos["usuario"], "modificar", "rechazado", motivo="permiso_insuficiente")
        print("Acceso rechazado: solo el administrador puede modificar cantidades.")
        return False

    if not isinstance(identificador, str) or not identificador.strip():
        registrar_evento(datos["usuario"], "modificar", "rechazado", motivo="identificador_invalido")
        print("Identificador inválido.")
        return False
    if not isinstance(entrada, str) or re.fullmatch(r"[0-9]+", entrada.strip()) is None:
        registrar_evento(datos["usuario"], "modificar", "rechazado",
                         producto=identificador, motivo="cantidad_invalida")
        print("Cantidad inválida: escriba un entero entre 0 y 1000.")
        return False
    cantidad = int(entrada.strip())
    if not 0 <= cantidad <= 1000:
        registrar_evento(datos["usuario"], "modificar", "rechazado",
                         producto=identificador, motivo="fuera_de_rango")
        print("Cantidad fuera de rango: debe estar entre 0 y 1000.")
        return False

    try:
        productos = cargar_inventario()
    except (OSError, RuntimeError) as exc:
        print(f"No se pudo modificar el inventario: {exc}")
        registrar_evento(datos["usuario"], "modificar", "fallido", motivo="error_archivo")
        return False

    for producto in productos:
        if producto["id"] == identificador:
            anterior = producto["cantidad"]
            producto["cantidad"] = cantidad
            try:
                guardar_inventario(productos)
            except (OSError, ValueError) as exc:
                print(f"No se pudo guardar el inventario: {exc}")
                registrar_evento(datos["usuario"], "modificar", "fallido",
                                 producto=identificador, motivo="error_guardado")
                return False
            registrar_evento(
                datos["usuario"], "modificar", "exitoso",
                producto=identificador, anterior=anterior, nueva=cantidad
            )
            print("Cantidad actualizada.")
            return True

    registrar_evento(datos["usuario"], "modificar", "rechazado",
                     producto=identificador, motivo="producto_inexistente")
    print("No existe un producto con ese identificador.")
    return False


def main():
    print("Inventario académico — COMP 2700")
    print("Estudiante:", input("Escriba su nombre: "))
    sesion = None
    while True:
        if sesion is None:
            nombre = input("Usuario (o salir): ").strip()
            if nombre.lower() == "salir":
                break
            sesion = autenticar(nombre, input("Contraseña de prueba: "))
            continue

        print("1. Consultar | 2. Modificar | 3. Cerrar sesión | 0. Salir")
        opcion = input("Opción: ").strip()
        if opcion == "1":
            consultar_inventario(sesion)
        elif opcion == "2":
            identificador = input("ID del producto: ").strip()
            entrada = input("Nueva cantidad: ")
            modificar_cantidad(sesion, identificador, entrada)
        elif opcion == "3":
            cerrar_sesion(sesion)
            sesion = None
        elif opcion == "0":
            cerrar_sesion(sesion)
            break
        else:
            print("Opción inválida.")


if __name__ == "__main__":
    main()
