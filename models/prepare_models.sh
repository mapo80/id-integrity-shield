
#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/models_store
cd /app/models_store

echo "[*] Fetching TruFor split ONNX parts..."
if [ ! -d TruFor ]; then
  git clone --depth 1 https://github.com/mapo80/TruFor.git
fi
cd TruFor/onnx_models || exit 1
# Try both 480 and 384 variants if present
if ls trufor_480x480_op13.onnx.part* 1> /dev/null 2>&1; then
  python /app/scripts/join_parts.py --out /app/models_store/trufor_480x480_op13.onnx --parts trufor_480x480_op13.onnx.part*
elif ls trufor_384x384_op13.onnx.part* 1> /dev/null 2>&1; then
  python /app/scripts/join_parts.py --out /app/models_store/trufor_384x384_op13.onnx --parts trufor_384x384_op13.onnx.part*
else
  echo "WARNING: TruFor parts not found; skipping assemble."
fi
cd /app/models_store

echo "[*] Fetching Noiseprint++ ONNX if available (from same repo or separate)"
# If repo contains noiseprint++ (adjust path if needed), otherwise skip
if [ -f /app/models/noiseprintpp.onnx ]; then
  cp /app/models/noiseprintpp.onnx /app/models_store/noiseprintpp.onnx
else
  echo "NOTE: Place noiseprintpp.onnx under /app/models or mount at runtime."
fi

echo "[*] Fetching ManTraNet ONNX from image-forgery-scanner repo..."
if [ ! -d image-forgery-scanner ]; then
  git clone --depth 1 https://github.com/mapo80/image-forgery-scanner.git
fi
# Try common location
if [ -f image-forgery-scanner/ImageForensics/src/ImageForensics.Core/Models/onnx/ManTraNet.onnx ]; then
  cp image-forgery-scanner/ImageForensics/src/ImageForensics.Core/Models/onnx/ManTraNet.onnx /app/models_store/ManTraNet.onnx
else
  echo "WARNING: ManTraNet.onnx not found in the expected path."
fi

echo "[*] Models prepared at /app/models_store"
