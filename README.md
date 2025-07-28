# shinypkg

A simple CLI tool to scaffold and package single-file [Shiny for Python](https://shiny.posit.co/py/) apps.

This tool is designed for **educational and pedagogical use**. It provides an easy, reproducible way to build minimal Shiny apps that can be installed and run as Python packages.

## 📦 Installation

We recommend using [uv](https://github.com/astral-sh/uv) for clean, reproducible development:

```bash
#uv tool install shinypkg
uv tool install git+https://github.com/kenjisato/shinypkg
```

Alternatively:

```bash
#pipx install shinypkg
```

## 🚀 Create an App Project

```bash
# Step 1: Create a new Shiny app project
shinypkg create myapp

# Step 2: Move into the project directory
cd myapp

# Step 3: Add Shiny to the project dependencies
uv add shiny

# Step 4: Run the app (no installation needed)
uv run myapp

# Optional: Install the app as a tool
uv tool install -e .
myapp
```

### 🧰 What does it generate?

After `shinypkg create myapp`, you will get:

```
myapp/
├── myapp/
│   ├── __init__.py
│   ├── __main__.py
│   ├── _util.py
│   └── app.py
├── pyproject.toml
├── README.md
└── .gitignore
```

- `app.py`: Your Shiny app goes here.
- `__main__.py`: Enables `python -m myapp` or `uv run myapp`.
- `_util.py`: Place for helper functions.
- `pyproject.toml`: Declares your app as a package.
- `.gitignore`: Standard Python and venv ignores.


## 📦 Packaging an Existing Shiny App

If you already have a directory with `app.py`, you can turn it into a Python package using:

```bash
shinypkg pack myapp
```

This will create a new project directory with the same structure as `shinypkg create`, wrapping your app in a minimal Python package layout. 



## ✨ Features

- Minimal Shiny app starter
- Works seamlessly with `uv`, `uvx`, and `pipx`
- CLI and Python module compatible
- Auto-fills Git author info if available
- Optionally initializes a Git repo
- Turn an existing app into a package
- Suitable for beginners and reproducible teaching setups

## 🧑‍🏫 For Teaching

This project minimizes friction for learners. It separates user-editable files from internal logic, avoids deep nesting, and produces working apps with a single command. Ideal for:

- Classroom instruction
- Online tutorials
- Hands-on workshops

## 📄 License

MIT
