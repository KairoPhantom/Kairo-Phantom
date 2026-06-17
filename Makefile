# Kairo Phantom — Command Surface (SPEC §S9)
# A stage isn't done until its command prints a real green result.
# The kernel imports nothing from /domains or /legacy.

.PHONY: build test demo bench gauntlet safety acceptance domains-check license-check help

PYTHON ?= python
FIXTURES_DIR ?= fixtures/invoice
DEMO_FILE ?= $(FIXTURES_DIR)/sample_invoice_01.txt

help: ## Show this help
	@echo "Kairo Phantom — Command Surface (SPEC S9)"
	@echo ""
	@echo "  make build          Build kernel + wedge Pack (NOT /domains)"
	@echo "  make test           Real unit/integration suites"
	@echo "  make demo FILE=...  Full on-device pipeline -> overlay"
	@echo "  make bench          Run labeled fixtures -> REPORT.json/md"
	@echo "  make gauntlet       Verification gauntlet, full denominator"
	@echo "  make safety         Air-gap + injection + fuzz + gate-bypass"
	@echo "  make acceptance     Full acceptance -> ACCEPTANCE.md"
	@echo "  make domains-check  CI guard: /domains byte-for-byte unchanged"
	@echo ""

build: ## Build kernel + wedge Pack (NOT /domains)
	$(PYTHON) -c "import kernel; import packs; import bench; print('kernel + packs + bench import OK')"
	$(PYTHON) scripts/ci/kernel_purity_guard.py
	$(PYTHON) scripts/ci/license_check.py
	@echo "BUILD: GREEN"

license-check:
	$(PYTHON) scripts/ci/license_check.py

test: ## Real unit/integration suites (no mocks on production path)
	$(PYTHON) -m pytest kernel/tests/ packs/tests/ -v --tb=short
	$(PYTHON) scripts/ci/kernel_purity_guard.py
	@echo "TEST: GREEN"

demo: ## Full on-device pipeline -> overlay
	$(PYTHON) -m kernel.sidecar.demo --file $(or $(FILE),$(DEMO_FILE))

bench: ## Run labeled fixtures -> REPORT.json/md
	$(PYTHON) -m bench.harness --fixtures-dir $(FIXTURES_DIR) --output bench/REPORT.json
	@echo "BENCH: see bench/REPORT.json and bench/REPORT.md"

gauntlet: ## Verification gauntlet, full denominator (PENDING-REAL-APP counted, not passed)
	$(PYTHON) scripts/ci/kernel_purity_guard.py
	$(PYTHON) scripts/ci/domains_unchanged_guard.py
	$(PYTHON) -m pytest kernel/tests/ packs/tests/ -v --tb=short
	$(PYTHON) -m bench.safety --fixtures-dir $(FIXTURES_DIR)
	$(PYTHON) -m bench.harness --fixtures-dir $(FIXTURES_DIR) --output bench/REPORT.json
	@echo "GAUNTLET: GREEN"

safety: ## Air-gap egress + injection corpus + ingestor fuzz + gate-bypass
	$(PYTHON) -m bench.safety --fixtures-dir $(FIXTURES_DIR)
	@echo "SAFETY: GREEN"

acceptance: ## Full acceptance on a real wedge doc -> ACCEPTANCE.md
	$(PYTHON) -m bench.acceptance --file $(or $(FILE),$(DEMO_FILE)) --output ACCEPTANCE.md
	@echo "ACCEPTANCE: see ACCEPTANCE.md"

domains-check: ## CI guard: /domains byte-for-byte unchanged
	$(PYTHON) scripts/ci/domains_unchanged_guard.py
	@echo "DOMAINS-CHECK: GREEN"
