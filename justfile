set dotenv-load := true

# List all available commands
_default:
    @just --list --unsorted

# Run a command in the environment
run *ARGS:
    uv run {{ ARGS }}

# recreate vm
recreate-vm:
    vagrant destroy
    vagrant up

# SSH into vm
ssh:
    vagrant ssh

# Run uv command in the django example project
djuv *ARGS:
    #!/usr/bin/env bash
    cd examples/django/bookstore
    uv --project bookstore {{ ARGS }}

# Generate django project requirements:
dj-requirements:
    just djuv pip compile pyproject.toml -o requirements.txt

# Run fujin command in the django example project
fujin *ARGS:
    #!/usr/bin/env bash
    cd examples/django/bookstore
    ../../../.venv/bin/python -m fujin {{ ARGS }}

# -------------------------------------------------------------------------
# RELEASE UTILITIES
#---------------------------------------------------------------------------

# Generate changelog, useful to update the unreleased section
logchange:
    just run git-cliff --output CHANGELOG.md

# Bump project version and update changelog
bumpver VERSION:
    #!/usr/bin/env bash
    set -euo pipefail
    just run bump-my-version bump {{ VERSION }}
    just run git-cliff --output CHANGELOG.md

    if [ -z "$(git status --porcelain)" ]; then
        echo "No changes to commit."
        git push && git push --tags
        exit 0
    fi

    version="$(hatch version)"
    git add CHANGELOG.md
    git commit -m "Generate changelog for version ${version}"
    git tag -f "v${version}"
    git push && git push --tags
