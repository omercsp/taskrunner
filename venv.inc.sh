[[ -n ${VIRTUAL_ENV} ]] && return

PROJ_ROOT=$(git rev-parse --show-toplevel)
VENV_FILE="${PROJ_ROOT}/.venv/bin/activate"
if ! source ${VENV_FILE}; then
        echo "Failed to activate virtual environment: ${VENV_FILE}"
        exit 1
fi

# To allow deactivate to work from called shell scripts
export -f deactivate
export VIRTUAL_ENV
export _OLD_VIRTUAL_PATH
export _OLD_VIRTUAL_PYTHONHOME
export _OLD_VIRTUAL_PS1
