#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install test dependencies
pip install pytest pytest-cov

# Run tests with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi 