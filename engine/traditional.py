"""Motor tradicional: IA simbolica basada en reglas ponderadas (sin modelos generativos)."""
import re
import unicodedata

from .contract import validate_response


def _norm(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# Palabras clave por categoria con su peso.
RULES = {
    "SECURITY": {
        "vulnerabilidad": 4, "hack": 4, "hacke": 4, "inyeccion": 4, "sql injection": 4,
        "xss": 4, "phishing": 4, "malware": 4, "ransomware": 5, "se filtr": 3,
        "filtraron": 3, "filtracion": 3, "filtrad": 3, "fuga": 3,
        # Exposicion de datos de terceros: es un incidente de privacidad, no de acceso.
        "otra persona": 3, "otro usuario": 3, "otro cliente": 3, "otros clientes": 3,
        "datos ajenos": 4, "datos de otr": 3, "informacion de otr": 3,
        "expuest": 3, "brecha": 4, "robo de": 3, "robaron": 3, "acceso no autorizado": 5,
        "sin autorizacion": 3, "contrasenas en texto plano": 5, "texto plano": 3,
        "token": 2, "credencial": 2, "sospechos": 3, "ataque": 4, "exploit": 4, "ddos": 4,
        "cifrado": 2, "seguridad": 3, "virus": 3,
    },
    "ACCESS": {
        "iniciar sesion": 3, "inicio de sesion": 3, "login": 3, "contrasena": 2,
        "password": 2, "no puedo entrar": 3, "no puedo acceder": 3, "acceso": 2,
        "bloquead": 2, "cuenta": 1, "2fa": 2, "codigo de verificacion": 2,
        "restablecer": 2, "recuperar": 2, "usuario": 1, "sesion": 2, "permiso": 2,
    },
    "BUG": {
        "error": 3, "falla": 3, "fallo": 3, "no funciona": 3, "se cae": 3, "crash": 3,
        "cierra solo": 3, "se congela": 3, "lento": 2, "500": 3, "404": 2, "bug": 3,
        "pantalla en blanco": 3, "no carga": 3, "no guarda": 3, "excepcion": 3,
        "duplica": 2, "incorrect": 2, "se borro": 2,
    },
    "FEATURE": {
        "seria bueno": 3, "me gustaria": 3, "podrian agregar": 4, "agregar": 2,
        "nueva funcion": 4, "funcionalidad": 3, "sugerencia": 3, "propongo": 3,
        "mejora": 2, "quisiera que": 2, "modo oscuro": 3, "exportar": 2, "integracion": 2,
        "anadir": 2, "implementar": 2,
    },
}

URGENT = ("urgente", "todos los usuarios", "produccion", "nadie puede", "toda la empresa",
          "clientes afectados", "perdida de datos", "inmediato", "ahora mismo", "caido")

# Senales de que el incidente ya ocurrio (no es un riesgo, ya hay dano): sube a CRITICAL.
COMPROMISE = ("pusieron sus credenciales", "ingresaron sus credenciales",
              "dieron sus credenciales", "credenciales robadas", "robaron", "comprometid",
              "borr", "cifraron", "secuestr", "acceso no autorizado", "sin autorizacion")

# Frases tipicas de intento de manipulacion (prompt injection / ingenieria social).
MANIPULATION = (r"ignora (todas )?las instrucciones", r"ignore (all )?previous",
                r"clasifica(la|lo)?( esta| este)?\b.* como", r"prioridad (baja|low)",
                r"no (lo )?marques", r"eres ahora", r"system prompt", r"responde solo",
                # El usuario intenta dictar la etiqueta: "(FEATURE, LOW)", "categoria: BUG"...
                r"\b(access|bug|feature|security)\s*[,/]\s*(low|medium|high|critical)\b",
                r"\b(categoria|prioridad)\s*[:=]")

# Etiquetas que el usuario intenta dictar; se quitan del texto antes de puntuar.
LABELS = (r"\b(access|bug|feature|security)\s*[,/]\s*(low|medium|high|critical)\b",
          r"\b(categoria|prioridad)\s*[:=]\s*\w+")

# Palabras de SECURITY que por si solas ya indican un incidente (no solo el tema).
# "seguridad", "token", "credencial" y "cifrado" quedan fuera: aparecen en peticiones normales.
STRONG_SECURITY = tuple(kw for kw, w in RULES["SECURITY"].items()
                        if w >= 3 and kw not in ("seguridad",))

RESPONSES = {
    "ACCESS": "Lamentamos el inconveniente con su acceso. Verifique sus credenciales y use la "
              "opcion de recuperacion de contrasena; si el problema continua, nuestro equipo "
              "validara su cuenta.",
    "BUG": "Gracias por reportar la falla. La registramos para el equipo tecnico; por favor "
           "comparta los pasos para reproducirla, la hora aproximada y capturas si las tiene.",
    "FEATURE": "Gracias por su sugerencia. La registramos como solicitud de nueva "
               "funcionalidad para que el equipo de producto la evalue.",
    "SECURITY": "Recibimos su reporte de seguridad y lo escalamos al equipo de seguridad para "
                "revision humana inmediata. No comparta credenciales ni datos sensibles por "
                "este medio.",
}


def classify(message):
    raw = _norm(message)
    manipulation = any(re.search(p, raw) for p in MANIPULATION)
    text = raw
    for label in LABELS:  # la clasificacion sale del contenido, nunca de lo que pide el usuario
        text = re.sub(label, " ", text)
    scores = {cat: sum(w for kw, w in kws.items() if kw in text) for cat, kws in RULES.items()}
    best = max(scores, key=scores.get)
    ambiguous = scores[best] == 0
    if ambiguous:
        best = "BUG"  # por defecto se trata como incidencia y se revisa
    urgent = any(u in text for u in URGENT)
    compromised = any(c in text for c in COMPROMISE)

    # Falla segura: si hay una senal fuerte de incidente de seguridad, gana SECURITY aunque
    # otra categoria sume mas (p. ej. un ataque disfrazado de "sugerencia"). Un falso positivo
    # solo cuesta una revision humana; un falso negativo deja un incidente sin atender.
    if best != "SECURITY" and any(kw in text for kw in STRONG_SECURITY):
        best = "SECURITY"

    if best == "SECURITY":
        critical = urgent or compromised or scores["SECURITY"] >= 7
        priority = "CRITICAL" if critical else "HIGH"
    elif best == "BUG":
        priority = "HIGH" if urgent else "MEDIUM"
    elif best == "ACCESS":
        priority = "HIGH" if urgent else "MEDIUM"
    else:
        priority = "LOW"

    result = {
        "category": best,
        "priority": priority,
        "response": RESPONSES[best],
        # Revision humana: seguridad, mensajes sin senales claras o intentos de manipulacion.
        "requiresHumanReview": best == "SECURITY" or ambiguous or manipulation,
    }
    return validate_response(result, "traditional")
