set dotenv-load := true

# List all available commands
_default:
    @just --list --unsorted

# Run a command in the environment
run *ARGS:
    uv run {{ ARGS }}

# Run ssh server container
sshserver:
    docker stop sshserver && docker rm sshserver > /dev/null 2>&1 || true
    docker build -t sshserver .
    docker run -d -p 2222:22 --name sshserver sshserver 

# SSH into sshserver
ssh:
    ssh -i id_rsa test@localhost -p 2222

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
