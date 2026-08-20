#!/usr/bin/env sh
set -eu
git config core.hooksPath .githooks
[ "$(git config --get core.hooksPath)" = ".githooks" ]
printf '%s\n' 'Installed documentation-governance hook source: .githooks'
