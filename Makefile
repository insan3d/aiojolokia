# Usage:
#
# make clean  # cleanup everything
# make venv   # create fresh Python virtual environment
# make build  # build wheel

ifeq ($(OS), Windows_NT)
	FIXPATH = $(subst /,\,$1)
	WINSILENT = >NUL 2>NUL & ECHO >NUL

	RM = RD /Q /S
	GLOBAL_PYTHON = python.exe
	LOCAL_PYTHON = .\venv\Scripts\python.exe
else
	FIXPATH = $1

	RM = rm -rf
	GLOBAL_PYTHON = python3.11
	LOCAL_PYTHON = ./venv/bin/python
endif

.PHONY: clean

build: dist/aiojolokia-0.1.0-py3-none-any.whl

dist/aiojolokia-0.1.0-py3-none-any.whl:
	$(GLOBAL_PYTHON) -m build

venv:
	$(GLOBAL_PYTHON) -m venv --system-site-packages --clear --prompt "$(notdir $(CURDIR))" venv
	$(LOCAL_PYTHON) -m pip install --upgrade --upgrade build pip setuptools wheel
	$(LOCAL_PYTHON) -m pip install -r requirements.txt

clean:
	$(RM) $(call FIXPATH,dist venv __pycache__ $(notdir $(CURDIR)).egg-info) $(WINSILENT)
