"""
Filtros para excluir mensajes de bajo valor informativo de los resultados de busqueda.

Filtra monosilabos, risas repetitivas, y mensajes donde todas las palabras son muy cortas.
"""

import re
from typing import Optional

# Patron para risas repetitivas: jaja, jejeje, jajajaja, jiji, etc.
_RISAS_PATTERN = re.compile(r'^(?:j+[aeiou]+)+j*[aeiou]*$', re.IGNORECASE)

# Palabras/expresiones de bajo valor cuando son el mensaje completo
_PALABRAS_BAJO_VALOR = {
    'si', 'sí', 'no', 'ok', 'ya', 'ah', 'oh', 'uh', 'eh',
    'ay', 'uy', 'mm', 'mmm', 'hm', 'hmm', 'xd', 'lol',
    'jj', 'k', 'q', 'x', 'd', 'f', 'va', 'ok', 'sep',
}

# Longitud maxima para considerar una palabra como "corta"
_MAX_CHARS_MONOSILABO = 3


def _normalizar_letras_repetidas(texto: str) -> str:
    """Reduce 2+ repeticiones consecutivas de una letra a 1.

    Ejemplos: 'siii' -> 'si', 'nooo' -> 'no', 'okkk' -> 'ok', 'jajaja' -> 'jajaja' (no afecta)
    """
    return re.sub(r'(.)\1+', r'\1', texto)


def es_mensaje_bajo_valor(texto: Optional[str]) -> bool:
    """
    Determina si un mensaje es de bajo valor informativo y debe excluirse.

    Un mensaje es de bajo valor si:
    1. Esta vacio o es None
    2. Es una risa repetitiva (jaja, jejeje, etc.)
    3. Es una sola palabra de bajo valor conocida (incluyendo variantes alargadas)
    4. Todas sus palabras tienen 3 o menos caracteres

    Args:
        texto: El texto limpio del mensaje (text_clean)

    Returns:
        True si el mensaje debe filtrarse, False si debe conservarse
    """
    if not texto or not texto.strip():
        return True

    texto_limpio = texto.strip().lower()

    # Verificar si es una risa repetitiva
    if _RISAS_PATTERN.match(texto_limpio):
        return True

    # Normalizar letras repetidas para detectar variantes: siii->si, nooo->no
    texto_normalizado = _normalizar_letras_repetidas(texto_limpio)

    # Extraer palabras (solo alfanumericas)
    palabras = re.findall(r'\w+', texto_normalizado)

    if not palabras:
        return True

    # Mensaje de una sola palabra
    if len(palabras) == 1:
        palabra = palabras[0]
        if palabra in _PALABRAS_BAJO_VALOR:
            return True
        if len(palabra) <= _MAX_CHARS_MONOSILABO:
            return True
        return False

    # Mensaje multi-palabra: filtrar si TODAS las palabras son cortas
    if all(len(p) <= _MAX_CHARS_MONOSILABO for p in palabras):
        return True

    return False
