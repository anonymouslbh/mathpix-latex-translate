"""Conservative static TeX inventory; never a full parser or fidelity proof."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re


def inventory(path):
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Input not found: {path}")
    files = [path] if path.is_file() else sorted(path.rglob('*.tex'))
    if not files or any(p.suffix.lower() != '.tex' for p in files):
        raise ValueError(f"Expected TeX input: {path}")
    groups = {k: Counter() for k in ('labels', 'references', 'citations', 'graphics', 'begins', 'ends')}
    patterns = {
        'labels': r'\\label\s*\{([^{}]*)\}',
        'references': r'\\(?:ref|eqref|autoref|pageref|cref|Cref)\*?\s*\{([^{}]*)\}',
        'citations': r'\\(?:cite|citep|citet|autocite|parencite|textcite)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^{}]*)\}',
        'graphics': r'\\includegraphics\*?\s*(?:\[[^\]]*\]\s*)?\{([^{}]*)\}',
        'begins': r'\\begin\s*\{([^{}]*)\}',
        'ends': r'\\end\s*\{([^{}]*)\}',
    }
    for file in files:
        # Percent begins a comment only when preceded by an even number of slashes.
        content = re.sub(r'(?<!\\)((?:\\\\)*)%[^\n]*', r'\1', file.read_text(encoding='utf-8-sig'))
        for key, pattern in patterns.items():
            for match in re.findall(pattern, content):
                items = match.split(',') if key in ('references', 'citations') else [match]
                groups[key].update(item.strip() for item in items)
    return groups, len(files)


def compare(source, target):
    left, left_count = inventory(source)
    right, right_count = inventory(target)
    differences = {}
    for key in left:
        missing, added = left[key] - right[key], right[key] - left[key]
        if missing or added:
            differences[key] = {'missing': dict(missing), 'added': dict(added)}
    duplicates = {side: {k: n for k, n in data['labels'].items() if n > 1}
                  for side, data in [('baseline', left), ('translation', right)]}
    imbalance = {side: {'unclosed': dict(data['begins'] - data['ends']),
                        'extra_ends': dict(data['ends'] - data['begins'])}
                 for side, data in [('baseline', left), ('translation', right)]}
    passed = not differences and not any(duplicates.values()) and not any(
        entry['unclosed'] or entry['extra_ends'] for entry in imbalance.values())
    return {'static_checks_passed': passed, 'files': {'baseline': left_count, 'translation': right_count},
            'differences': differences, 'duplicate_labels': duplicates, 'environment_counts': imbalance,
            'limitations': ['Regex inventory, not a TeX parser.', 'All TeX files under each supplied directory are scanned.',
                            'Does not validate formulas, environment nesting, coverage, glossary, assets, compilation or layout.',
                            'Custom macros, verbatim and conditional TeX require manual review.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline')
    parser.add_argument('translation')
    args = parser.parse_args()
    try:
        result = compare(args.baseline, args.translation)
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['static_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
