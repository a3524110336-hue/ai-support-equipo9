"""Corre los casos contra POST /api/analyze con ambos motores y genera la tabla de resultados.

Uso:  python server.py   (en otra terminal)
      python tests/run_comparison.py [http://127.0.0.1:8000]
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))
KEYS = {"category", "priority", "response", "requiresHumanReview", "mode"}


def analyze(message, mode):
    req = urllib.request.Request(f"{BASE}/api/analyze", method="POST",
                                 data=json.dumps({"message": message, "mode": mode}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


rows, raw = [], []
for mode in ("traditional", "generative"):
    for c in CASES:
        t0 = time.time()
        status, out = analyze(c["message"], mode)
        ms = int((time.time() - t0) * 1000)
        fmt_ok = status == 200 and set(out) == KEYS
        cat_ok = fmt_ok and out["category"] == c["expected_category"]
        pri_ok = fmt_ok and out["priority"] == c["expected_priority"]
        rows.append({"mode": mode, "id": c["id"], "type": c["type"], "expected": f'{c["expected_category"]}/{c["expected_priority"]}',
                     "got": f'{out.get("category")}/{out.get("priority")}' if fmt_ok else f"HTTP {status}",
                     "review": out.get("requiresHumanReview"), "format_ok": fmt_ok,
                     "category_ok": cat_ok, "correct": cat_ok and pri_ok, "ms": ms})
        raw.append({"case": c, "mode": mode, "status": status, "output": out, "ms": ms})
        print(f"[{mode:11}] #{c['id']:>2} {rows[-1]['got']:<22} esperado {rows[-1]['expected']:<20} {'OK' if rows[-1]['correct'] else '--'}")

# Validacion y errores: peticiones invalidas deben responder 400
bad = [({"message": ""}, "vacio"), ({"message": "hola", "mode": "otro"}, "modo invalido"),
       ({"message": "x" * 3000}, "demasiado largo"), ({"mensaje": "hola"}, "campo incorrecto")]
validation = []
for body, label in bad:
    req = urllib.request.Request(f"{BASE}/api/analyze", method="POST", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10); code = 200
    except urllib.error.HTTPError as e:
        code = e.code
    validation.append((label, code))

lines = ["# Resultados comparativos", "",
         "Correcto = categoria **y** prioridad iguales a la clasificacion de referencia (`tests/cases.json`).", "",
         "| # | Tipo | Referencia | Tradicional | Generativo | Formato T/G | Revision humana T/G |",
         "|---|------|-----------|-------------|------------|-------------|---------------------|"]
by = {(r["mode"], r["id"]): r for r in rows}
for c in CASES:
    t, g = by[("traditional", c["id"])], by[("generative", c["id"])]
    mark = lambda r: f'{r["got"]} {"✅" if r["correct"] else ("🟡" if r["category_ok"] else "❌")}'
    lines.append(f'| {c["id"]} | {c["type"]} | {t["expected"]} | {mark(t)} | {mark(g)} | '
                 f'{"✔" if t["format_ok"] else "✘"}/{"✔" if g["format_ok"] else "✘"} | {t["review"]}/{g["review"]} |')
lines += ["", "✅ categoria y prioridad correctas · 🟡 solo categoria correcta · ❌ categoria incorrecta", "",
          "| Motor | Formato valido | Categoria correcta | Categoria + prioridad correctas | Tiempo medio |",
          "|-------|----------------|--------------------|-------------------------------|--------------|"]
summary = {}
for mode in ("traditional", "generative"):
    rs = [r for r in rows if r["mode"] == mode]; n = len(rs)
    s = {"format": sum(r["format_ok"] for r in rs) / n * 100, "category": sum(r["category_ok"] for r in rs) / n * 100,
         "correct": sum(r["correct"] for r in rs) / n * 100, "ms": sum(r["ms"] for r in rs) // n}
    summary[mode] = s
    lines.append(f'| {mode} | {s["format"]:.0f}% | {s["category"]:.1f}% | {s["correct"]:.1f}% | {s["ms"]} ms |')
lines += ["", "## Validaciones de la API", "", "| Caso invalido | HTTP |", "|---|---|"]
lines += [f"| {l} | {c} |" for l, c in validation]

ev = ROOT / "evidence"; ev.mkdir(exist_ok=True)
(ev / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(ev / "raw_outputs.json").write_text(json.dumps({"summary": summary, "validation": validation, "runs": raw},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
print("\n".join(lines[-12:]))
