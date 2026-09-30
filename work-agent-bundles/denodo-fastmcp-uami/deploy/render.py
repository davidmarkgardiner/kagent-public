"""Render public templates using a private, non-secret values file."""

import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    parser.add_argument("values", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    values = {}
    for line in args.values.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z_]+", key) or not value or "{{" in value:
            raise ValueError("invalid or unresolved value")
        values[key] = value
    rendered = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values[m.group(1)], args.template.read_text())
    if "{{" in rendered:
        raise ValueError("unresolved template placeholder")
    args.output.write_text(rendered)


if __name__ == "__main__":
    main()
