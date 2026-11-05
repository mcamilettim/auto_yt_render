#!/usr/bin/env bash
# Ejecuta Blender en modo fondo con un backend gráfico que dibuja colores correctos.
# - Linux/CI: xvfb-run + Mesa llvmpipe (OpenGL por software).
# - Windows (notebook con Intel UHD 620): el driver OpenGL de Intel pinta los materiales de rojo en Eevee Next,
#   así que se usa Vulkan por software (lavapipe de mesa-dist-win). Requiere C:/tools/mesa/x64/lvp_icd.x86_64.json.
# Uso: herramientas/blender.sh -P script.py -- args...
set -euo pipefail
case "${OSTYPE:-}" in
  msys*|cygwin*|win*)
    BLENDER="${BLENDER:-C:/tools/blender-4.5.15-windows-x64/blender.exe}"
    ICD="${LVP_ICD:-C:\\tools\\mesa\\x64\\lvp_icd.x86_64.json}"
    VK_DRIVER_FILES="$ICD" VK_ICD_FILENAMES="$ICD" exec "$BLENDER" --gpu-backend vulkan -b "$@"
    ;;
  *)
    BLENDER="${BLENDER:-blender}"
    if [ -z "${DISPLAY:-}" ]; then
      exec xvfb-run -a -s "-screen 0 1920x1080x24" "$BLENDER" -b "$@"
    fi
    exec "$BLENDER" -b "$@"
    ;;
esac
