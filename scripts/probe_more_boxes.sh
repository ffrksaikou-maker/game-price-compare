#!/bin/bash
# Second-round probe: try more specific codes for unmapped slugs.

UA="Mozilla/5.0"

# Try every (code, pattern) and report which pages exist + what product-img they have
codes=(
  # SV variants
  sv1a sv1h sv1s sv1v sv2h sv2s sv2v sv2p sv3a sv3p
  sv5a sv5k sv5m sv6a sv6b sv7a sv7b sv7d sv7m
  sv8b sv9a sv9b sv9h sv10a sv10b sv11a sv11b sv11d sv11p
  svd sve svf svh svi svj svl svn
  # SS variants
  s1 s1a s1h s1b s1r s1w s2a s2d s3a s3h s4b s5a s5d s5i s5m s5r
  s6b s6d s6h s6k s6p s7 s7a s7d s7h s7p s7r s8a s8c s8d s8m
  s9b s9h s9p s9r s10a s10c s10d s10p s11a s11b s11p s12b
)

for code in "${codes[@]}"; do
  url="https://www.pokemon-card.com/ex/${code}/index.html"
  status=$(curl -sI -A "$UA" -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
  if [ "$status" = "200" ]; then
    html=$(curl -sL -A "$UA" "$url" 2>/dev/null)
    title=$(echo "$html" | grep -oE '<title>[^<]+</title>' | head -1 | sed 's|<title>||; s|</title>||' | head -c 80)
    # Try common image patterns
    product_imgs=$(echo "$html" | grep -oE '(product-img|hero-visual|hero-img|point[0-9]+-box|2pack-img|hero-pack)[a-z0-9_-]*\.(png|jpg|jpeg)' | sort -u | head -5 | tr '\n' ' ')
    echo -e "${code}\t${title}\t${product_imgs}"
  fi
done
