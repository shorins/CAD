# Makefile для запуска тестов CAD System

# Путь к виртуальному окружению
VENV = venv
PYTHON = $(VENV)/bin/python

# Папка с тестами
TEST_DIR = tests

# Находим все тестовые файлы
TEST_FILES = $(wildcard $(TEST_DIR)/test_*.py)

# Цвета для вывода
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: test test-all test-verbose test-clean help

# Запуск всех тестов (по умолчанию)
test: test-all

# Запуск всех тестов последовательно
test-all:
	@echo "$(YELLOW)Запуск всех тестов...$(NC)"
	@echo ""
	@failed=0; \
	total=0; \
	for test_file in $(TEST_FILES); do \
		if [ -s "$$test_file" ]; then \
			total=$$((total + 1)); \
			echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
			echo "$(YELLOW)Запуск: $$test_file$(NC)"; \
			echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
			if $(PYTHON) $$test_file; then \
				echo "$(GREEN)✓ $$test_file - ПРОЙДЕН$(NC)"; \
			else \
				echo "$(RED)✗ $$test_file - ПРОВАЛЕН$(NC)"; \
				failed=$$((failed + 1)); \
			fi; \
			echo ""; \
		fi; \
	done; \
	echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
	if [ $$failed -eq 0 ]; then \
		echo "$(GREEN)✅ Все тесты пройдены! ($$total/$$total)$(NC)"; \
		exit 0; \
	else \
		echo "$(RED)❌ Провалено тестов: $$failed из $$total$(NC)"; \
		exit 1; \
	fi

# Запуск всех тестов с подробным выводом
test-verbose:
	@echo "$(YELLOW)Запуск всех тестов с подробным выводом...$(NC)"
	@echo ""
	@failed=0; \
	total=0; \
	for test_file in $(TEST_FILES); do \
		if [ -s "$$test_file" ]; then \
			total=$$((total + 1)); \
			echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
			echo "$(YELLOW)Запуск: $$test_file$(NC)"; \
			echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
			$(PYTHON) -u $$test_file; \
			if [ $$? -eq 0 ]; then \
				echo "$(GREEN)✓ $$test_file - ПРОЙДЕН$(NC)"; \
			else \
				echo "$(RED)✗ $$test_file - ПРОВАЛЕН$(NC)"; \
				failed=$$((failed + 1)); \
			fi; \
			echo ""; \
		fi; \
	done; \
	echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"; \
	if [ $$failed -eq 0 ]; then \
		echo "$(GREEN)✅ Все тесты пройдены! ($$total/$$total)$(NC)"; \
		exit 0; \
	else \
		echo "$(RED)❌ Провалено тестов: $$failed из $$total$(NC)"; \
		exit 1; \
	fi

# Очистка кэша тестов
test-clean:
	@echo "$(YELLOW)Очистка кэша тестов...$(NC)"
	@find $(TEST_DIR) -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find $(TEST_DIR) -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Кэш очищен$(NC)"

# Справка
help:
	@echo "$(YELLOW)Доступные команды:$(NC)"
	@echo "  $(GREEN)make test$(NC)          - Запустить все тесты"
	@echo "  $(GREEN)make test-all$(NC)      - Запустить все тесты (то же что test)"
	@echo "  $(GREEN)make test-verbose$(NC)  - Запустить все тесты с подробным выводом"
	@echo "  $(GREEN)make test-clean$(NC)    - Очистить кэш тестов (__pycache__)"
	@echo "  $(GREEN)make help$(NC)          - Показать эту справку"
	@echo ""
	@echo "$(YELLOW)Для запуска отдельного теста:$(NC)"
	@echo "  $(GREEN)$(PYTHON) tests/test_zoom_transformations.py$(NC)"

