# AI Support Engine — Reto práctico (Semana 12, M01)

Bases de datos en la nube · Equipo 9

Prototipo que clasifica solicitudes de soporte en **ACCESS / BUG / FEATURE / SECURITY**, les asigna
prioridad **LOW / MEDIUM / HIGH / CRITICAL** y genera una respuesta. Tiene dos motores con el mismo
contrato de respuesta, expuestos en `POST /api/analyze`:

| Motor | Archivo | Cómo funciona |
|---|---|---|
| `traditional` | `engine/traditional.py` | IA simbólica: reglas ponderadas por palabras clave, reglas de urgencia y de manipulación; respuesta predeterminada por categoría. Sin modelos generativos. |
| `generative` | `engine/generative.py` | LLM real **local con Ollama** (`qwen2.5:7b-instruct`), salida forzada a JSON (`format: json`, temperatura 0), validada contra el contrato y con un reintento si el formato falla. |

## Requisitos

- Python 3.10+ (solo librería estándar, sin `pip install`).
- [Ollama](https://ollama.com) corriendo con el modelo: `ollama pull qwen2.5:7b-instruct`.

## Ejecución

```bash
python server.py                      # API en http://127.0.0.1:8000
python tests/run_comparison.py        # 12 casos x 2 motores -> evidence/
```

Variables de entorno (opcionales, **ningún secreto va en el código**): `PORT`, `OLLAMA_URL`,
`OLLAMA_MODEL`, `OLLAMA_TIMEOUT`, `OLLAMA_API_KEY` (solo si se usa un proveedor remoto; nunca se
registra ni se devuelve).

### Ejemplo

```bash
curl -X POST http://127.0.0.1:8000/api/analyze -H "Content-Type: application/json" \
  -d '{"message": "No puedo iniciar sesion", "mode": "generative"}'
```

```json
{"category": "ACCESS", "priority": "MEDIUM", "response": "...", "requiresHumanReview": false, "mode": "generative"}
```

## Validación y seguridad

- Petición: JSON válido, `Content-Type: application/json`, solo los campos `message` y `mode`,
  `message` no vacío y de hasta 2000 caracteres, `mode` ∈ {`traditional`, `generative`}; cuerpo
  máximo 8 KB. Cualquier violación responde **400** (415/413 en su caso).
- Fallos del proveedor o del modelo (red, timeout, HTTP de error, JSON roto o fuera de contrato)
  responden **502** con un mensaje genérico, sin trazas ni URLs internas.
- La salida generativa se valida campo por campo (`engine/contract.py`): categoría y prioridad
  dentro de los valores permitidos, respuesta no vacía, `requiresHumanReview` booleano.
- **Todo lo clasificado como SECURITY se marca para revisión humana** en el servidor, aunque el
  motor diga lo contrario.
- Defensa contra *prompt injection*: el mensaje va delimitado como dato (`<solicitud>`), el prompt
  de sistema prohíbe seguir instrucciones dentro de él, y el motor tradicional detecta frases de
  manipulación y las manda a revisión humana.
- El log del servidor no guarda el cuerpo de las peticiones.

## Resultados (12 casos: 8 normales, 2 ambiguos, 2 adversariales)

Tabla completa: [`evidence/results.md`](evidence/results.md) · salidas crudas de ambos motores:
[`evidence/raw_outputs.json`](evidence/raw_outputs.json) · consola: [`evidence/run_comparison.log`](evidence/run_comparison.log).

| Motor | Formato válido | Categoría correcta | Categoría + prioridad correctas | Tiempo medio |
|---|---|---|---|---|
| Tradicional | 100% | 83.3% | **75.0%** | 9 ms |
| Generativo | 100% | 83.3% | 58.3% | 3519 ms |

## Conclusión técnica

Con nuestra clasificación de referencia, el motor tradicional acertó más (75% contra 58.3%) y
respondió unas 400 veces más rápido. Sus aciertos se deben a que las reglas de prioridad coinciden
con el criterio que definimos; el generativo identificó igual de bien la categoría (83.3%), pero
sobrestimó la prioridad (puso HIGH o CRITICAL donde esperábamos MEDIUM). El generativo sí entendió
el contexto donde las reglas no alcanzan: detectó como CRITICAL el phishing con credenciales
robadas. Ninguno resolvió el caso ambiguo de datos ajenos visibles ni el adversarial que se
disfraza de sugerencia; ahí el generativo al menos pidió revisión humana y el tradicional no.
Recomendamos un esquema híbrido: reglas primero y LLM con revisión humana para lo ambiguo.

## Estructura

```
server.py                 API HTTP (POST /api/analyze, GET /health)
engine/contract.py        contrato y validaciones de entrada/salida
engine/traditional.py     motor por reglas
engine/generative.py      motor con LLM (Ollama)
tests/cases.json          12 casos con su clasificación de referencia
tests/run_comparison.py   pruebas comparativas contra la API real
evidence/                 resultados y salidas
```
