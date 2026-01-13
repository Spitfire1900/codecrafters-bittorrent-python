#!/bin/bash
set -e

pip install --upgrade pip
pip install --upgrade-strategy eager pipx
pipx install xonsh[full]
pipx inject xonsh instld
pipx inject xonsh xontrib-prompt-bar
pipx inject xonsh xontrib-pygitstatus
pipx inject xonsh xontrib-vox

curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://opencode.ai/install | bash
curl -fsSL https://codecrafters.io/install.sh | bash

# Install zoxide (fast "cd" replacement) and add shell initialization
curl -sS https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | bash
if ! grep -q "zoxide init" ~/.bashrc 2>/dev/null; then
	printf '\n# zoxide init\neval "$(zoxide init bash)"\n' >> ~/.bashrc
fi

source ~/.bashrc
