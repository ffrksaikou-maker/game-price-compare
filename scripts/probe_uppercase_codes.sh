#!/bin/bash
# Probe pokemon-card.com with UPPERCASE letter-suffix codes (case-sensitive URLs).
# These cover the older S&S sub-series and SV sub-series.

UA="Mozilla/5.0"

codes=(
  # SV sub-series uppercase variants
  sv1S sv1V sv1T sv1H sv2S sv2V sv2T sv2P sv2K sv2D
  sv3P sv3S sv3T sv3H sv5K sv5M sv5W sv5C
  sv6P sv6T sv7P sv7T sv7N sv8P sv8T
  sv9P sv9T sv10P sv10T sv11P sv11T sv11D
  # S&S sub-series UPPERCASE letters (from common naming)
  s5I s5R s5D s5K s6H s6K s6P s6D
  s7D s7R s7H s7K s7P s7T
  s8I s8R s8H s8K s8P s8T
  s9D s9P s9R s9H s9K
  s10D s10R s10P s10T s10H s10K
  s11D s11R s11P s11T s11H s11K
  # Crown Zenith / special / promo
  cl s11p s12c
  # very early SS
  s1H s1R s1S s1V
  # Misc
  smp smb smc smH smT smP
)

for code in "${codes[@]}"; do
  for path in "images/ogp.jpg" "images/ogp.png" "assets/images/ogp.png" "assets/images/ogp.jpg"; do
    url="https://www.pokemon-card.com/ex/${code}/${path}"
    status=$(curl -sI -A "$UA" -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ "$status" = "200" ]; then
      size=$(curl -sI -A "$UA" "$url" 2>/dev/null | grep -i content-length | awk '{print $2}' | tr -d '\r')
      title=$(curl -sL -A "$UA" "https://www.pokemon-card.com/ex/${code}/index.html" 2>&1 | grep -oE '<title>[^<]+</title>' | head -1)
      echo -e "${code}\t${size}\t${path}\t${title}"
      break
    fi
  done
done
