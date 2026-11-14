"""Confere se a tag do git bate com calculadora3d.__version__.

Uso: python tools/check_version.py v0.2.0   (sai com 1 se não bater)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calculadora3d import __version__  # noqa: E402


def main(argv: list[str]) -> int:
    tag = argv[0] if argv else ""
    expected = f"v{__version__}"
    if tag == expected:
        return 0
    print(f"Tag {tag} não bate com a versão {__version__} (esperado {expected})",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
