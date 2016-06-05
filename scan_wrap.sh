#!/bin/bash
set -e

# Run the scan with passthrough arguments.
case $1 in
  drop  )
    # Switch to the scanner user while keeping the current env and passing
    # through the current arguments stripped of the 'drop' option.
    sudo -E -u scanner -H bash -l -s ./scan "${@:2}" <<'EOF'
      "$@"
EOF
    ;;
  data  )
    ./scan "${@:2}" --output=/data
    ;;
  *     )
    ./scan $@
    ;;
esac
