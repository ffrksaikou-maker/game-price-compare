"""Generate index.html from template.html + price data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .matcher import MasterProduct

logger = logging.getLogger(__name__)

# JST timezone
JST = timezone(timedelta(hours=9))

# Shop IDs in display order
SHOP_IDS = ["morimori", "homura", "icchome", "shouten", "rudeya", "kaikyo", "sommelier", "runto"]


def generate_product_js(products: list[MasterProduct]) -> str:
    """Generate the JavaScript `const P = [...]` array from product data."""
    lines = []
    lines.append("const P=[")

    # Group by category
    current_cat = None
    for p in products:
        if p.category != current_cat:
            current_cat = p.category
            lines.append(f"// ===== {current_cat.upper()} =====")

        # Build price dict
        prices = {}
        for sid in SHOP_IDS:
            prices[sid] = p.prices.get(sid, 0)

        # Escape product name for JS string
        name_escaped = p.name.replace("\\", "\\\\").replace('"', '\\"')

        price_parts = ",".join(f"{sid}:{prices[sid]}" for sid in SHOP_IDS)
        line = (
            f'{{c:"{p.category}",n:"{name_escaped}",'
            f'r:{p.retail_price},p:{{{price_parts}}}}}'
        )
        lines.append(line + ",")

    lines.append("];")
    return "\n".join(lines)


def generate_html(
    products: list[MasterProduct],
    template_path: Path | None = None,
    output_path: Path | None = None,
) -> str:
    """Generate index.html from template and product data.

    Args:
        products: List of master products with prices filled in.
        template_path: Path to template.html (default: project root/template.html)
        output_path: Path to write index.html (default: project root/index.html)

    Returns:
        The generated HTML content.
    """
    project_root = Path(__file__).resolve().parent.parent
    if template_path is None:
        template_path = project_root / "template.html"
    if output_path is None:
        output_path = project_root / "index.html"

    template = template_path.read_text(encoding="utf-8")

    # Generate product data JS
    product_js = generate_product_js(products)

    # Generate update date in JST
    now = datetime.now(JST)
    update_date = now.strftime("%Y/%m/%d %H:%M")

    # Replace placeholders
    html = template.replace("// {{PRODUCT_DATA}}", product_js)
    html = html.replace("{{UPDATE_DATE}}", update_date)

    # Write output
    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    return html
