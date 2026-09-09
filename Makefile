PYTHON = python
# Force UTF-8 stdout on Windows (avoids cp1252 UnicodeEncodeError)
export PYTHONUTF8 = 1


ingest:
	$(PYTHON) -m src.ingest

clean-data:
	$(PYTHON) -m src.clean

threads:
	$(PYTHON) -m src.threads

brand-check:
	$(PYTHON) -m src.brand_check

phase0: ingest clean-data threads brand-check
	@echo ""
	@echo "=== Phase 0 complete ==="
