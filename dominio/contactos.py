import re


def normalizar_telefono(telefono):
    if telefono is None:
        return ""
    if not isinstance(telefono, str):
        raise ValueError("El teléfono debe ser texto.")
    telefono = telefono.strip()
    if telefono and re.fullmatch(r"\+?[0-9]+", telefono) is None:
        raise ValueError("El teléfono debe contener solo números y puede comenzar con +.")
    return telefono
