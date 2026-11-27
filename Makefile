.PHONY: test lint format coverage build docker-run clean

test:
	python -m pytest -q

lint:
	python -m ruff check .

format:
	python -m ruff format .

coverage:
	python -m pytest --cov=github_tool --cov-report=term-missing

build:
	docker build -t github-tool .

docker-run:
	docker run --rm -v $(PWD)/data:/data github-tool

clean:
	python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
