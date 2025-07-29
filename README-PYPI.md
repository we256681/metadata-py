# Руководство по публикации `metadata-py` на PyPI

Полное руководство по публикации и поддержке пакета `metadata-py` для управления метаданными в Markdown-файлах.

## 1. Структура проекта

Создайте корневую папку проекта (например, `update-docs-system/`) и добавьте в неё необходимые файлы и папки. В корне обычно присутствуют файлы `setup.py`, `pyproject.toml` (необязательно, но рекомендуется для современных билд-систем), `requirements.txt`, `README.md`, `CHANGELOG.md` и другие. Код пакета поместите в поддиректорию, например, `update_docs/`, с файлом `__init__.py` и модулями (например, `cli.py`, `core.py` и т.д.). Пример структуры проекта (из технического задания) может выглядеть так:

```text
update-docs-system/
├── setup.py
├── pyproject.toml
├── requirements.txt
├── README.md
├── CHANGELOG.md
└── update_docs/
    ├── __init__.py
    ├── core.py
    └── cli.py
```

Каждый модуль пакета (`update_docs/`) должен быть оформлен как обычный модуль Python (с `__init__.py`). В `cli.py` реализуйте функцию `main()` для запуска через консоль. Также можно добавить папки `templates/` или `scripts/` для шаблонов и вспомогательных скриптов, если это требуется проектом.

## 2. Настройка `setup.py` и (опционально) `pyproject.toml`

Для публикации на PyPI настройте файл `setup.py` с метаданными пакета. В нём укажите как минимум название (`name`), версию, автора, краткое описание, список пакетов (обычно через `find_packages()`), зависимости и другие поля. Пример содержимого `setup.py` (по мотивам проекта):

```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="update-docs-system",          # имя пакета на PyPI:contentReference[oaicite:3]{index=3}
    version="1.0.0",
    author="Ваше Имя",
    author_email="you@example.com",
    description="Комплексная система автоматизации документации для Markdown-файлов",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/update-docs-system",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    # далее добавим entry_points в шаге 3
)
```

Если вы используете *PEP 517/518* (современную сборку), то создайте файл `pyproject.toml` с минимальным описанием билд-системы. Например:

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"
```

Это укажет, что для сборки используется setuptools. Пакетные метаданные можно оставить в `setup.py`, как показано выше.

## 3. Добавление console-сценария (`console_scripts`)

Чтобы при установке пакета через `pip` команда `update-docs` была доступна в консоли, добавьте в `setup.py` раздел `entry_points` с ключом `console_scripts`. Формат следующий: `"имя_команды=пакет.модуль:функция"`. Для нашего примера (функция `main` в модуле `update_docs.cli`) это может быть так:

```python
setup(
    # ... остальные параметры ...
    entry_points={
        "console_scripts": [
            "update-docs=update_docs.cli:main",
        ],
    },
    include_package_data=True,
    package_data={"update_docs": ["templates/*"]},
)
```

Здесь `"update-docs=update_docs.cli:main"` означает, что после установки команды `update-docs` будет вызывать функцию `main()` из `update_docs/cli.py`. После установки пакета `pip install update-docs-system` команда будет доступна глобально.

## 4. Релиз на GitHub и связь с PyPI

Оформите релиз пакета в GitHub:

* **Создание тега и релиза.** Установите версию в `setup.py` (например, `version="1.0.0"`), затем закоммитьте и запушьте код. Создайте Git-тег той же версии, например:

  ```bash
  git tag v1.0.0
  git push origin main --tags
  ```

  На GitHub автоматически (или вручную через Releases) создайте Release на основе этого тега. В описании релиза можно указать изменения (из `CHANGELOG.md`), и даже прикрепить сборки (т. е. файлы из `dist/`) как артефакты.

* **Привязка к PyPI.** Версия пакета на PyPI должна совпадать с Git-тегом/релизом. После загрузки пакета на PyPI (см. следующий раздел) пользователи, увидев релиз на GitHub, смогут установить ту же версию через `pip`. GitHub и PyPI не имеют автоматической двусторонней связи – важно лишь, чтобы у них совпадали номера версий и название пакета.

* **Автоматизация через GitHub Actions.** Можно настроить Workflow GitHub Actions, который при пуше тега `v*.*.*` или при создании Release будет автоматически собирать и публиковать пакет (см. шаг 6 ниже).

## 5. Публикация на PyPI (настройка `~/.pypirc`)

Чтобы опубликовать пакет на PyPI, выполните следующие действия:

1. **Создайте аккаунт на PyPI** (если ещё нет) и получите **API-токен** в разделе настроек (запомните токен или сохраните его в безопасном месте).

2. **Создайте файл `~/.pypirc`.** В нём укажите PyPI-репозиторий и ваши учётные данные (рекомендуется использовать токен как пароль). Пример содержимого `~/.pypirc`:

   ```ini
   [pypi]
   username = __token__
   password = pypi-0123456789abcdefghijklmnopqrstuvwx
   ```

   Здесь `__token__` — специальное значение вместо имени пользователя, а в `password` вставьте полученный API-токен (начинается с `pypi-`). Если хотите пробовать публикацию на тестовом PyPI (`test.pypi.org`), добавьте секцию `[testpypi]` аналогичным образом.

3. **Установите `build` и `twine`.** В виртуальном окружении (или глобально) выполните:

   ```bash
   pip install --upgrade build twine
   ```

4. **Соберите дистрибутивы.** В корне проекта выполните:

   ```bash
   python -m build
   ```

   Это создаст папку `dist/` с архивом `*.tar.gz` и, возможно, колесом `*.whl`. Альтернативно можно использовать старый способ: `python setup.py sdist bdist_wheel`.

5. **Опубликуйте пакет.** После сборки загрузите дистрибутивы на PyPI командой:

   ```bash
   twine upload dist/*
   ```

   Так как в `~/.pypirc` уже прописаны учётные данные, вас не спросят логин/пароль. По завершении пакет станет доступен на PyPI.

6. **Проверьте установку.** Попробуйте в чистом окружении:

   ```bash
   pip install update-docs-system
   ```

   Команда `update-docs` должна работать. Это подтвердит, что публикация прошла успешно.

## 6. Автоматизация публикации через GitHub Actions

Для автоматического обновления релизов GitHub и публикации на PyPI настройте GitHub Actions workflow. Например, можно запускать сборку при пуше тега `vX.Y.Z` или создании Release. Пример простого `.github/workflows/release.yml`:

```yaml
name: 🚀 Publish

on:
  push:
    tags: ['v*.*.*']

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install build tools
        run: pip install --upgrade build twine

      - name: Build distribution
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}  # Поместите PyPI token в секреты репозитория
        run: twine upload dist/*

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*.*
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

В этом примере:

* Workflow срабатывает при пуше тега `vX.Y.Z`.
* Сборка (`python -m build`) создаёт дистрибутив.
* Публикация на PyPI через `twine upload` с использованием секретного токена `PYPI_TOKEN` (его нужно добавить в **Settings → Secrets** вашего репозитория).
* Создаётся GitHub Release с прикреплёнными файлами из `dist/` (используется действие `softprops/action-gh-release`). Вы можете использовать и официальное действие `actions/create-release`, если предпочитаете.

Таким образом, при создании нового тега система автоматически соберёт пакет, запушит его на PyPI и создаст релиз на GitHub с артефактами сборки. Это завершает цикл публикации: версия пакета синхронизирована между GitHub и PyPI.

**Источники:** Примеры структуры проекта и настройки `setup.py` взяты из внутренней технической документации проекта.
