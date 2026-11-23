# ADR-001 · Contrato común, dos motores intercambiables y revisión humana en SECURITY

- **Estado:** aceptado
- **Fecha:** 2026-11-22
- **Autor:** P1 (motor tradicional, contrato y validación)

## Contexto

El reto pide comparar un motor de IA tradicional con uno generativo sobre las mismas
solicitudes de soporte. Para que la comparación sea justa, los dos tienen que recibir la misma
entrada y devolver exactamente la misma forma de respuesta. Además, el generativo puede
inventar valores o salirse del formato, y cualquiera de los dos puede equivocarse con un
incidente de seguridad.

## Decisión

1. **Un solo contrato** en `engine/contract.py`. Ahí viven las categorías (`ACCESS`, `BUG`,
   `FEATURE`, `SECURITY`), las prioridades (`LOW` a `CRITICAL`) y las dos validaciones:
   `validate_request` (lo que entra a la API) y `validate_response` (lo que sale de cualquier
   motor).
2. **Dos motores intercambiables** con la misma firma: `classify(message) -> dict`.
   `server.py` elige uno con el campo `mode` y no sabe nada de cómo funciona cada uno. Agregar
   un tercer motor no obliga a tocar la API.
3. **La validación de entrada va en la API, antes de llamar a un motor:** `415` si no es JSON,
   `413` si el cuerpo pasa de 8 KB, `400` para JSON roto, `Content-Length` inválido, campos de
   más, mensaje vacío o de más de 2000 caracteres, o `mode` desconocido. Ningún motor recibe
   basura.
4. **Toda salida pasa por `validate_response`**, también la del motor tradicional. Si un motor
   devuelve algo fuera del contrato, se rechaza; no se corrige a mano.
5. **Todo lo que sea `SECURITY` va a revisión humana**, y esa regla se aplica en el contrato,
   no en cada motor: aunque un motor diga `requiresHumanReview: false`, el servidor lo cambia a
   `true`.

### Por qué SECURITY siempre va a una persona

- **El costo del error no es simétrico.** Mandar a revisión algo que no era grave cuesta unos
  minutos de alguien. Dejar pasar una filtración o un acceso no autorizado puede costar datos
  de clientes y obligaciones legales.
- **Los dos motores se pueden engañar.** El generativo es vulnerable a *prompt injection*
  ("ignora las instrucciones…") y las reglas no entienden contexto. En las pruebas, un ataque
  disfrazado de sugerencia confundió a ambos motores en la primera versión.
- **Las acciones que siguen son decisiones de una persona:** bloquear cuentas, avisar a
  clientes o escalar a un área legal no se automatizan.
- **Ponerla en el contrato** garantiza que ningún motor, ni uno futuro, se la pueda saltar.

### Falla segura en el motor tradicional

Si aparece una señal fuerte de incidente (por ejemplo ransomware, acceso no autorizado o datos
de otra persona), el motor elige `SECURITY` aunque otra categoría sume más puntos. Si además
hay señales de que el daño ya ocurrió (credenciales entregadas, registros borrados), la
prioridad sube a `CRITICAL`. Las etiquetas que el usuario intenta dictar, como
"(FEATURE, LOW)", se quitan antes de puntuar y marcan el mensaje para revisión.

## Alternativas descartadas

- **Que cada motor decida la revisión humana:** un motor manipulado o mal configurado podría
  apagarla. Por eso queda en el contrato.
- **Validar dentro de cada motor:** se duplica código y los motores podrían validar distinto,
  lo que arruina la comparación.
- **Usar solo el motor generativo:** tarda unos 3.5 s por solicitud contra unos 9 ms del
  tradicional, necesita GPU y es más fácil de manipular.

## Consecuencias

- (+) La comparación es justa: mismo contrato, misma validación, mismas reglas de seguridad.
- (+) Cambiar o agregar un motor no toca la API.
- (−) Habrá falsos positivos de `SECURITY` que una persona tendrá que descartar. Lo aceptamos
  a propósito.
- (−) El motor tradicional depende de palabras clave en español. Las reglas se afinaron
  mirando los casos de `tests/cases.json`, así que su porcentaje en esos casos es optimista;
  por eso las pruebas unitarias usan frases que no están en ese archivo.
