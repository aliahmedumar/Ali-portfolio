#!/usr/bin/env bash
# Pulls the hero video (or a frame/screenshot) from skimmy.ai into assets/projects/.
# Runs in GitHub Actions, which has open internet access. Best effort: never fails the deploy.
set -uo pipefail

OUT=assets/projects
SITE=https://skimmy.ai
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
mkdir -p "$OUT"

html=$(curl -sL -A "$UA" "$SITE" || true)

resolve() {
  case "$1" in
    http*) echo "$1" ;;
    //*)   echo "https:$1" ;;
    /*)    echo "$SITE$1" ;;
    *)     echo "$SITE/$1" ;;
  esac
}

vid=$(printf '%s' "$html" | grep -oE '[^"'"'"' ()=]+\.(mp4|webm|mov)(\?[^"'"'"' )]*)?' | head -1)
if [ -n "$vid" ]; then
  url=$(resolve "$vid")
  echo "Video found: $url"
  if curl -sfL -A "$UA" -o /tmp/skimmy-src "$url"; then
    ffmpeg -y -loglevel error -i /tmp/skimmy-src -t 12 -an \
      -vf "scale='min(1280,iw)':-2" -c:v libx264 -preset veryfast -crf 28 \
      -pix_fmt yuv420p -movflags +faststart "$OUT/skimmy.mp4" \
    && ffmpeg -y -loglevel error -ss 1 -i "$OUT/skimmy.mp4" -frames:v 1 -q:v 3 "$OUT/skimmy.jpg" \
    && { echo "Saved skimmy.mp4 and skimmy.jpg"; exit 0; }
  fi
fi

echo "No usable video in page HTML; taking a screenshot of the hero instead."
rm -f "$OUT/skimmy.mp4"
for b in google-chrome chromium chromium-browser; do
  if command -v "$b" >/dev/null; then
    "$b" --headless=new --no-sandbox --hide-scrollbars --window-size=1440,720 \
      --virtual-time-budget=8000 --screenshot=/tmp/skimmy.png "$SITE" >/dev/null 2>&1
    [ -s /tmp/skimmy.png ] && ffmpeg -y -loglevel error -i /tmp/skimmy.png -q:v 3 "$OUT/skimmy.jpg" \
      && { echo "Saved skimmy.jpg screenshot"; exit 0; }
  fi
done

og=$(printf '%s' "$html" | grep -oE 'property="og:image"[^>]*content="[^"]+"' | sed -E 's/.*content="([^"]+)".*/\1/' | head -1)
[ -n "$og" ] && curl -sfL -A "$UA" -o /tmp/og "$(resolve "$og")" && ffmpeg -y -loglevel error -i /tmp/og -q:v 3 "$OUT/skimmy.jpg" \
  && echo "Saved og:image as skimmy.jpg"
exit 0
