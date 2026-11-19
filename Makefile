PYTHON ?= python

.PHONY: setup verify run evidence

setup: ## Dependencias: ninguna de pip; descarga el modelo local de Ollama
	ollama pull qwen2.5:7b-instruct

verify: ## Pruebas unitarias del contrato y del motor tradicional
	$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v

run: ## API en http://127.0.0.1:8000
	$(PYTHON) server.py

evidence: ## Corre los 12 casos contra la API en marcha (make run en otra terminal)
	$(PYTHON) tests/run_comparison.py
