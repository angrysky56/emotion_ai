#!/bin/bash
# Aura Backend Environment Activation Helper

if [ -f "../.venv/bin/activate" ]; then
	VENV_PATH="../.venv"
elif [ -f ".venv/bin/activate" ]; then
	VENV_PATH=".venv"
fi

if [ -n "$VENV_PATH" ]; then
	# shellcheck disable=SC1091
	source "$VENV_PATH/bin/activate"
	echo "✅ Virtual environment activated from $VENV_PATH"
	PYTHON_EXE=$(command -v python)
	echo "Python: $PYTHON_EXE"
	PYTHON_VER=$(python --version)
	echo "Version: $PYTHON_VER"
else
	echo "❌ Virtual environment not found. Run 'uv venv' in the project root."
fi
