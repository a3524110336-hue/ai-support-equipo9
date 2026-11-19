"""Contrato comun de entrada/salida para ambos motores."""

CATEGORIES = ("ACCESS", "BUG", "FEATURE", "SECURITY")
PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
MODES = ("traditional", "generative")
MAX_MESSAGE_LEN = 2000


class ValidationError(ValueError):
    """Peticion o respuesta que no cumple el contrato."""


def validate_request(payload):
    """Valida el cuerpo de POST /api/analyze y devuelve (message, mode)."""
    if not isinstance(payload, dict):
        raise ValidationError("El cuerpo debe ser un objeto JSON.")
    extra = set(payload) - {"message", "mode"}
    if extra:
        raise ValidationError(f"Campos no permitidos: {sorted(extra)}")
    message = payload.get("message")
    mode = payload.get("mode", "traditional")
    if not isinstance(message, str) or not message.strip():
        raise ValidationError("'message' es obligatorio y debe ser texto no vacio.")
    if len(message) > MAX_MESSAGE_LEN:
        raise ValidationError(f"'message' excede {MAX_MESSAGE_LEN} caracteres.")
    if mode not in MODES:
        raise ValidationError(f"'mode' debe ser uno de {MODES}.")
    return message.strip(), mode


def validate_response(data, mode):
    """Comprueba que la salida de un motor cumpla el contrato exacto."""
    if not isinstance(data, dict):
        raise ValidationError("La respuesta del motor no es un objeto JSON.")
    required = {"category", "priority", "response", "requiresHumanReview"}
    missing = required - set(data)
    if missing:
        raise ValidationError(f"Faltan campos: {sorted(missing)}")
    if data["category"] not in CATEGORIES:
        raise ValidationError(f"Categoria invalida: {data['category']!r}")
    if data["priority"] not in PRIORITIES:
        raise ValidationError(f"Prioridad invalida: {data['priority']!r}")
    if not isinstance(data["response"], str) or not data["response"].strip():
        raise ValidationError("'response' debe ser texto no vacio.")
    if not isinstance(data["requiresHumanReview"], bool):
        raise ValidationError("'requiresHumanReview' debe ser booleano.")
    out = {
        "category": data["category"],
        "priority": data["priority"],
        "response": data["response"].strip(),
        "requiresHumanReview": data["requiresHumanReview"],
        "mode": mode,
    }
    # Regla de seguridad del servidor: todo incidente de seguridad va a revision humana,
    # sin importar lo que diga el motor.
    if out["category"] == "SECURITY":
        out["requiresHumanReview"] = True
    return out
