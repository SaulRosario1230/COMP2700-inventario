# COMP 2700 — Aplicación de inventario corregida

**Estudiante:** [Escriba su nombre aquí]

## Alcance

Esta entrega corrige la aplicación educativa original. Conserva el inventario,
las cuentas ficticias y las operaciones existentes: iniciar sesión, consultar,
modificar cantidades, cerrar sesión y salir. No es una aplicación de producción.

## Requisitos y ejecución

Requiere Python 3.10 o posterior.

```bash
python -m venv .venv
```

Windows CMD:
```bat
.venv\Scripts\activate.bat
```

macOS/Linux:
```bash
source .venv/bin/activate
```

Instale la dependencia y ejecute:
```bash
python -m pip install -r requirements.txt
python app.py
```

En algunos sistemas se utiliza `python3` en lugar de `python`.

## Cuentas ficticias para las pruebas

- `admin` / `AdminDemo2700!` — puede consultar y modificar.
- `user` / `UserDemo2700!` — puede consultar, pero no modificar.

Las contraseñas no están guardadas en texto legible. `usuarios.json` contiene
hashes Argon2. La aplicación también puede migrar automáticamente un archivo
legado que todavía contenga el campo `clave`: crea el hash y elimina ese campo
al guardar el documento actualizado.

## Controles aplicados

1. **Autenticación:** `seguridad.py` utiliza Argon2 para crear y verificar hashes.
2. **Autorización:** las operaciones consultan una sesión creada y registrada
   por el proceso actual. Solo el rol `admin` puede modificar cantidades.
3. **Validación:** la cantidad debe ser un entero decimal entre 0 y 1000.
   Los valores inválidos no detienen el programa ni modifican el inventario.
4. **Persistencia:** JSON contiene el documento completo. El guardado utiliza
   un archivo temporal y reemplazo. Los archivos ausentes o con JSON inválido
   producen un mensaje de error y no se sobrescriben automáticamente.
5. **Auditoría:** `auditoria.jsonl` añade un objeto JSON por línea con fecha/hora
   UTC, usuario, acción, resultado y detalles. No registra contraseñas ni hashes.

## Pruebas manuales recomendadas

1. Inicie sesión como `admin`, consulte el inventario y confirme que P001 inicia
   con cantidad 10.
2. Como `admin`, cambie P001 a 99 y consulte nuevamente.
3. Cierre sesión e inicie como `user`. La consulta debe funcionar.
4. Como `user`, intente cambiar P001 a 50. La operación debe rechazarse y la
   cantidad debe permanecer igual.
5. Pruebe cantidades como `abc`, `-1`, `1001` y una entrada vacía. Todas deben
   rechazarse sin interrumpir la aplicación.
6. Intente modificar un ID inexistente. No debe crearse ningún producto.
7. Desde un script que importe `app`, pruebe `app.modificar_cantidad(None,
   "P001", "99")`. Debe rechazarse sin cambiar el inventario.
8. Revise `auditoria.jsonl`: cada línea debe poder leerse como un objeto JSON
   independiente.

No fabrique un diccionario con rol `admin`: las funciones solo aceptan objetos
de sesión registrados por el proceso actual.

## Archivos

- `app.py`: flujo de la aplicación, autenticación, autorización, validación,
  persistencia y auditoría.
- `seguridad.py`: funciones Argon2 suministradas.
- `usuarios.json`: cuentas ficticias con hashes.
- `inventario.json`: datos iniciales del inventario.
- `requirements.txt`: dependencia Argon2.
- `pruebas.py`: pruebas automatizadas de los controles principales.

## Fuentes y uso de IA

Fuente principal: archivos base proporcionados para la actividad de COMP 2700
(README, app.py, seguridad.py, usuarios.json, inventario.json y requirements.txt).

Se utilizó ChatGPT como apoyo para analizar los TODO, proponer correcciones,
documentar el código y preparar pruebas. El estudiante debe revisar el resultado,
ejecutar las pruebas y completar su nombre y cualquier requisito adicional
solicitado por el profesor antes de entregar.
