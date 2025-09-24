import os
from pathlib import Path

def create_project_structure():
    base_dir = Path("FinQuantProUltimateColossus")

    # Основные файлы в корне
    root_files = [
        "main.py",
        "config.yaml",
        "requirements.txt",
        "secrets.yaml",
        "docker-compose.yml",
        "Pipfile",
        "pyproject.toml",
        ".env",
        "README.md"
    ]

    # Структура папок и файлов
    structure = {
        "core": [
            "__init__.py",
            "portfolio_manager.py",
            "risk_engine.py",
            "tax_optimizer.py",
            "asset_classifier.py",
            "supply_chain_analyzer.py",
            "hedge_engine.py"
        ],
        "ml": [
            "__init__.py",
            "ensemble_predictor.py",
            "sentiment_analyzer.py",
            "data_preprocessor.py",
            "anomaly_detector.py",
            "backtester.py"
        ],
        "data": [
            "__init__.py",
            "market_feeder.py",
            "realtime_streamer.py",
            "currency_handler.py",
            "supply_chain_scraper.py",
            "database.py"
        ],
        "optimization": [
            "__init__.py",
            "genetic_optimizer.py",
            "black_litterman.py",
            "factor_model.py"
        ],
        "execution": [
            "__init__.py",
            "alpaca_executor.py"
        ],
        "compute": [
            "__init__.py",
            "dask_cluster.py",
            "ray_manager.py"
        ],
        "ui": [
            "__init__.py",
            "dashboard.py",
            "report_generator.py"
        ],
        "utils": [
            "__init__.py",
            "logger.py",
            "config_loader.py",
            "helpers.py"
        ],
        "monitoring": [
            "__init__.py",
            "health_checker.py",
            "alert_system.py"
        ],
        "tests": [
            "__init__.py",
            "test_core.py",
            "test_ml.py"
        ],
        "scripts": [
            "deploy.sh",
            "migrate_db.py"
        ],
        "models": []  # Пустая папка для моделей
    }

    # Создаем корневую директорию
    base_dir.mkdir(exist_ok=True)
    print(f"Создана директория: {base_dir}")

    # Создаем корневые файлы
    for file in root_files:
        file_path = base_dir / file
        file_path.touch()
        print(f"Создан файл: {file_path}")

    # Создаем поддиректории и файлы
    for folder, files in structure.items():
        folder_path = base_dir / folder
        folder_path.mkdir(exist_ok=True)
        print(f"Создана папка: {folder_path}")

        # Создаем __init__.py для Python пакетов (кроме scripts)
        if folder not in ["scripts", "models"]:
            init_file = folder_path / "__init__.py"
            init_file.touch()

        # Создаем файлы в папке
        for file in files:
            file_path = folder_path / file
            file_path.touch()
            print(f"Создан файл: {file_path}")

    print("\n✅ Структура проекта успешно создана!")
    print("📁 Обзор созданных файлов:")

    # Выводим дерево структуры
    def print_tree(directory, prefix=""):
        contents = list(directory.iterdir())
        pointers = ["├──"] * (len(contents) - 1) + ["└──"]
        for pointer, path in zip(pointers, contents):
            print(prefix + pointer + " " + path.name)
            if path.is_dir():
                extension = "│   " if pointer == "├──" else "    "
                print_tree(path, prefix + extension)

    print_tree(base_dir)

if __name__ == "__main__":
    create_project_structure()
