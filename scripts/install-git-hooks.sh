#!/usr/bin/env sh
set -eu

git config core.hooksPath .githooks
configured=$(git config --get core.hooksPath)
[ "$configured" = ".githooks" ]
printf '%s\n' "Installed repository hooks from .githooks"
