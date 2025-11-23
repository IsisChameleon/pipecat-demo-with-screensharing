#!/bin/bash
# Helper script to run uv commands with local .venv directory
# This ensures uv uses a project-local virtual environment instead of any global UV_PROJECT_ENVIRONMENT

# Unset UV_PROJECT_ENVIRONMENT to force local .venv usage
unset UV_PROJECT_ENVIRONMENT

# Run uv with the provided arguments
uv "$@"

