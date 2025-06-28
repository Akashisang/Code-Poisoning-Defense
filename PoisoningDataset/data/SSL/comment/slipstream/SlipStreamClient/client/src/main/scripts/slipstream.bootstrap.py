#!/bin/sh
''''which python2 >/dev/null 2>&1 && exec python2 "$0" "$@"
which python  >/dev/null 2>&1 && exec python  "$0" "$@"
which python3 >/dev/null 2>&1 && exec python3 "$0" "$@"
exec echo "Python not found" # '''