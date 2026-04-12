#!/bin/bash
# For top-popular BOX slugs, probe pokemon-card.com for best available image.
# Tries multiple filename patterns and reports which works.

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# Format: slug|series_code|preferred_filename
# preferred_filename is the first pattern to try (most likely BOX product shot)
BOXES=(
  "inferno|m2|product-img-01.png"
  "mega-brave|m1|product-img-1.png"
  "mega-sinfonia|m1|product-img-2.png"
  "mega-ex|m2a|product-img-01.png"
  "munikis-zero|m3|product-img-02.png"
  "ninja-spinner|m4|product-img-01-4gmgu.png"
  "151|sv2a|hero-visual.png"
  "ruler-of-black-flame|sv3|hero-visual.jpg"
  "ancient-roar|sv4|hero-visual.jpg"
  "future-flash|sv4|hero-visual.jpg"
  "shiny-treasure-ex|sv4a|hero-visual.jpg"
  "chouden-breaker|sv8|hero-visual.jpg"
  "terastal-fes-ex|sv8a|hero-visual.jpg"
  "battle-partners|sv9|hero-visual.jpg"
  "rocket-dan-no-eiko|sv10|hero-visual.jpg"
  "black-bolt|sv11|hero-visual.jpg"
  "white-flare|sv11|hero-visual.jpg"
  "hengen-no-kamen|sv6|hero-visual.jpg"
  "stellar-miracle|sv7|hero-visual.jpg"
  "vmax-climax|s8b|product-img-1.png"
  "vstar-universe|s12a|product-img-1.png"
  "star-birth|s9|product-img-1.png"
  "paradigm-trigger|s12|product-img-1.png"
  "time-gazer|s10|product-img-1.png"
  "space-juggler|s10|product-img-2.png"
  "pokemon-go|s10b|product-img-1.png"
)

echo "slug|series|file|status|size"
echo "---"
for entry in "${BOXES[@]}"; do
  IFS='|' read -r slug code fname <<< "$entry"
  url="https://www.pokemon-card.com/ex/${code}/assets/images/${fname}"
  result=$(curl -sI -A "$UA" "$url" 2>/dev/null | head -5)
  status=$(echo "$result" | grep -oE 'HTTP/[0-9.]+ [0-9]+' | awk '{print $2}')
  size=$(echo "$result" | grep -i content-length | awk '{print $2}' | tr -d '\r')
  echo "${slug}|${code}|${fname}|${status:-?}|${size:-0}"
done
