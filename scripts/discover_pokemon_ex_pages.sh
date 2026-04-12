#!/bin/bash
# Discover all /ex/{code}/ pages on pokemon-card.com and extract title + product image URLs.
# Outputs: series_code<TAB>title<TAB>product_image_url

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Enumerate likely codes
codes=(
  # MEGA series
  m1 m2 m2a m3 m4 m5 mc
  # Scarlet&Violet main numbered
  sv1 sv2 sv3 sv4 sv5 sv6 sv7 sv8 sv9 sv10 sv11
  # SV variants with letter suffix (common patterns)
  sv1a sv1s sv1v sv2a sv2d sv2p sv3a sv4a sv4k sv4m sv5a sv5k sv5m
  sv6a sv6p sv7a sv7s sv7e sv8a sv8p sv9a sv9b sv10a sv10b sv11a
  # SV special products
  sva svb svc svd sve svg svp svk svm svhi
  # Sword&Shield series (s*)
  s1a s1h s1s s2 s2a s3 s3a s4 s4a s5a s5d s5i s5r s6 s6a s6h s7d s7r
  s8 s8a s8b s9 s9a s10 s10a s10b s10d s10p s11 s11a s12 s12a
  # Promo/event codes
  sm sma smb smc smd sme smf smg smh smi smj smk
)

for code in "${codes[@]}"; do
  url="https://www.pokemon-card.com/ex/${code}/index.html"
  # HEAD request first
  status=$(curl -sI -A "$UA" -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
  if [ "$status" = "200" ]; then
    # GET and extract title + first product-img
    html=$(curl -sL -A "$UA" "$url" 2>/dev/null)
    title=$(echo "$html" | grep -oE '<title>[^<]+</title>' | head -1 | sed 's|<title>||; s|</title>||')
    first_img=$(echo "$html" | grep -oE 'product-img[a-z0-9_-]*\.(png|jpg|jpeg|webp)' | head -1)
    echo -e "${code}\t${title}\t${first_img}"
  fi
done
