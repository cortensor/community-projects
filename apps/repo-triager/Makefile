PY ?= .venv/bin/python

.PHONY: install demo test doctor findings clean

install:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

demo:
	$(PY) -m repo_triager.cli --provider scripted demo

test:
	$(PY) -m pytest

doctor:
	$(PY) -m repo_triager.cli --provider scripted doctor

findings:
	$(PY) findings/repro_instructions_truncation.py
	$(PY) findings/repro_structured_output_schema.py
	$(PY) findings/repro_policy_gate_vs_output_type.py
	$(PY) findings/repro_session_scope.py
	$(PY) findings/repro_operator_id_getpwuid.py
	$(PY) findings/repro_memory_search_truncation.py
	$(PY) findings/measure_turn_cost.py

clean:
	rm -rf var
