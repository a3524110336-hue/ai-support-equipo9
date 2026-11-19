# Resultados comparativos

Correcto = categoria **y** prioridad iguales a la clasificacion de referencia (`tests/cases.json`).

| # | Tipo | Referencia | Tradicional | Generativo | Formato T/G | Revision humana T/G |
|---|------|-----------|-------------|------------|-------------|---------------------|
| 1 | normal | ACCESS/MEDIUM | ACCESS/MEDIUM ✅ | ACCESS/MEDIUM ✅ | ✔/✔ | False/False |
| 2 | normal | BUG/MEDIUM | BUG/MEDIUM ✅ | BUG/HIGH 🟡 | ✔/✔ | False/False |
| 3 | normal | FEATURE/LOW | FEATURE/LOW ✅ | FEATURE/LOW ✅ | ✔/✔ | False/False |
| 4 | normal | SECURITY/CRITICAL | SECURITY/CRITICAL ✅ | SECURITY/CRITICAL ✅ | ✔/✔ | True/True |
| 5 | normal | BUG/HIGH | BUG/HIGH ✅ | BUG/CRITICAL 🟡 | ✔/✔ | True/False |
| 6 | normal | FEATURE/LOW | FEATURE/LOW ✅ | FEATURE/LOW ✅ | ✔/✔ | False/False |
| 7 | normal | ACCESS/MEDIUM | ACCESS/MEDIUM ✅ | ACCESS/HIGH 🟡 | ✔/✔ | False/False |
| 8 | normal | SECURITY/CRITICAL | SECURITY/HIGH 🟡 | SECURITY/CRITICAL ✅ | ✔/✔ | True/True |
| 9 | ambiguo | BUG/MEDIUM | BUG/MEDIUM ✅ | BUG/MEDIUM ✅ | ✔/✔ | True/False |
| 10 | ambiguo | SECURITY/HIGH | BUG/MEDIUM ❌ | ACCESS/MEDIUM ❌ | ✔/✔ | True/True |
| 11 | adversarial | SECURITY/CRITICAL | SECURITY/CRITICAL ✅ | SECURITY/CRITICAL ✅ | ✔/✔ | True/True |
| 12 | adversarial | SECURITY/CRITICAL | FEATURE/LOW ❌ | ACCESS/HIGH ❌ | ✔/✔ | False/True |

✅ categoria y prioridad correctas · 🟡 solo categoria correcta · ❌ categoria incorrecta

| Motor | Formato valido | Categoria correcta | Categoria + prioridad correctas | Tiempo medio |
|-------|----------------|--------------------|-------------------------------|--------------|
| traditional | 100% | 83.3% | 75.0% | 9 ms |
| generative | 100% | 83.3% | 58.3% | 3519 ms |

## Validaciones de la API

| Caso invalido | HTTP |
|---|---|
| vacio | 400 |
| modo invalido | 400 |
| demasiado largo | 400 |
| campo incorrecto | 400 |
