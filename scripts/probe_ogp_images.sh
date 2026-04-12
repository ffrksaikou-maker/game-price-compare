#!/bin/bash
# Probe OGP images for series pages that have Nuxt.js or no product-img.
# Two URL patterns to try:
#   new pages: /ex/{code}/assets/images/ogp.{png,jpg}
#   old pages: /ex/{code}/images/ogp.{jpg,png}
# Outputs: code<TAB>status<TAB>size<TAB>url

UA="Mozilla/5.0"

# Codes that either don't have product-img or I haven't checked yet
codes=(
  # SS series (mostly Nuxt)
  s1 s1a s1h s2 s2a s3 s3a s4 s4a s5a s5d s5i s5r s6 s6a s6h s7d s7r
  s8 s8a s8b s9 s9a s10 s10a s10b s10d s10p s11 s11a s11b s12 s12a
  # SV no-product-img
  sv1 sv1a sv2a sv3 sv4 sv4a sv5 sv6 sv7 sv7a sv7b sv8 sv8a sv9 sv10 sv11
  sv2p sv2s sv2v sv3a
  # MEGA (most have product-img already, but check)
  m1 m2 m2a m3 m4 mc
)

for code in "${codes[@]}"; do
  # Try old pattern: /ex/{code}/images/ogp.jpg
  url_old_jpg="https://www.pokemon-card.com/ex/${code}/images/ogp.jpg"
  status=$(curl -sI -A "$UA" -o /dev/null -w "%{http_code}" "$url_old_jpg" 2>/dev/null)
  if [ "$status" = "200" ]; then
    size=$(curl -sI -A "$UA" "$url_old_jpg" 2>/dev/null | grep -i content-length | awk '{print $2}' | tr -d '\r')
    echo -e "${code}\t200\t${size}\t${url_old_jpg}"
    continue
  fi

  # Try new pattern: /ex/{code}/assets/images/ogp.png
  url_new_png="https://www.pokemon-card.com/ex/${code}/assets/images/ogp.png"
  status=$(curl -sI -A "$UA" -o /dev/null -w "%{http_code}" "$url_new_png" 2>/dev/null)
  if [ "$status" = "200" ]; then
    size=$(curl -sI -A "$UA" "$url_new_png" 2>/dev/null | grep -i content-length | awk '{print $2}' | tr -d '\r')
    echo -e "${code}\t200\t${size}\t${url_new_png}"
    continue
  fi

  # Try new pattern jpg
  url_new_jpg="https://www.pokemon-card.com/ex/${code}/assets/images/ogp.jpg"
  status=$(curl -sI -A "$UA" -o /dev/null -w "%{http_code}" "$url_new_jpg" 2>/dev/null)
  if [ "$status" = "200" ]; then
    size=$(curl -sI -A "$UA" "$url_new_jpg" 2>/dev/null | grep -i content-length | awk '{print $2}' | tr -d '\r')
    echo -e "${code}\t200\t${size}\t${url_new_jpg}"
    continue
  fi

  echo -e "${code}\tNONE\t0\t-"
done
