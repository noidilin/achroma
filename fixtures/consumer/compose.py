"""Explicit object-level overrides; this is not a Stylus backup importer."""
import json
from pathlib import Path
import sys


def compose(payload, variant, user_vars):
    mapping = json.loads((Path(payload) / f'mappings/stylus/{variant}.json').read_text())
    # Only the documented UserCSS variable-value layer is merged. Arrays,
    # selectors, backup records, and browser settings are never deep-merged.
    return {**mapping['usercssVariables'], **user_vars}


if __name__ == '__main__':
    root = Path(sys.argv[1])
    palette = json.loads((root / 'palette/dark.json').read_text())
    assert palette['base'] == '#1e1e1e'
    variables = compose(root, 'dark', {'accentColor': 'blue'})
    assert variables == {'lightFlavor': 'latte', 'darkFlavor': 'mocha', 'accentColor': 'blue'}
    assert (root / 'themes/stylus/import.json').is_file()  # manual native-file import
    fragment = (root / 'fragments/stylus/dark.less').read_text()
    assert '@base: #1e1e1e;' in fragment
    print(json.dumps(variables, indent=2))
