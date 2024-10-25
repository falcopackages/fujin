set dotenv-load := true

# List all available commands
_default:
    @just --list --unsorted

# Run a command in the environment
run *ARGS:
    uv run {{ ARGS }}

# Create test ubuntu container
create-test-container:
    rm id_rsa && rm id_rsa.pub > /dev/null 2>&1 || true
    ssh-keygen -t rsa -N "" -f id_rsa
    docker stop sshserver && docker rm sshserver > /dev/null 2>&1 || true
    docker build -t sshserver .
    docker run -d -p 2222:22 -p 8000:80 --name sshserver sshserver
#    docker run --privileged \
#    -v /run/systemd/system:/run/systemd/system \
#    -v /lib/systemd:/lib/systemd \
#    -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket \
#    -p 2222:22 \
#    -p 8000:80 \
#    --name sshserver \
#    -it sshserver \
#    bash -c "ln -s /usr/lib/x86_64-linux-gnu/libtinfo.so.6 /usr/lib/x86_64-linux-gnu/libtinfo.so.5 && bash"

# SSH into test container
ssh:
    ssh -i id_rsa test@localhost -p 2222

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
