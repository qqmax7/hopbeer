"""Создаёт заготовку спецификации в specs/NNN-<slug>.

Пример:
    .venv\\Scripts\\python.exe scripts/new_spec.py --title "Поиск по пиву"
    .venv\\Scripts\\python.exe scripts/new_spec.py --title "API" --slug beer-api --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

TEMPLATES = ('spec.md', 'plan.md', 'tasks.md')

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def slugify(text: str) -> str:
    """Преобразует заголовок в slug: латиница, цифры и дефисы."""
    parts = []
    for char in text.lower():
        if char in TRANSLIT:
            parts.append(TRANSLIT[char])
        elif re.match(r'[a-z0-9]', char):
            parts.append(char)
        else:
            parts.append('-')
    slug = re.sub(r'-+', '-', ''.join(parts)).strip('-')
    if len(slug) > 50:
        slug = slug[:50].rstrip('-')
    return slug or 'feature'


def next_number(specs_dir: Path) -> int:
    """Следующий свободный номер спеки: максимум существующих + 1."""
    numbers = [
        int(match.group(1))
        for path in specs_dir.iterdir()
        if path.is_dir() and (match := re.match(r'^(\d{3})-', path.name))
    ]
    return max(numbers, default=-1) + 1


def render(template_path: Path, values: dict[str, str]) -> str:
    """Подставляет значения в шаблон, не трогая остальной текст."""
    text = template_path.read_text(encoding='utf-8')
    for key, value in values.items():
        text = text.replace('{{' + key + '}}', value)
    return text


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Создать заготовку спецификации в specs/NNN-<slug>.',
    )
    parser.add_argument('-t', '--title', required=True, help='название изменения')
    parser.add_argument(
        '--slug', help='латинский идентификатор папки (по умолчанию из --title)'
    )
    parser.add_argument(
        '--owner', default='', help='владелец спеки (по умолчанию — пусто)'
    )
    parser.add_argument(
        '--dry-run', action='store_true', help='только показать, что будет создано'
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    specs_dir = repo_root / 'specs'
    templates_dir = specs_dir / 'templates'
    if not specs_dir.is_dir() or not templates_dir.is_dir():
        print(f'Не найдены шаблоны: {templates_dir}', file=sys.stderr)
        return 1

    title = args.title.strip()
    if not title:
        print('Название спеки пустое.', file=sys.stderr)
        return 1

    slug = args.slug.strip() if args.slug else slugify(title)
    number = next_number(specs_dir)
    spec_id = f'SPEC-{number:03d}'
    folder_name = f'{number:03d}-{slug}'
    target = specs_dir / folder_name

    if target.exists():
        print(f'Папка уже существует: {target}', file=sys.stderr)
        return 1

    values = {
        'SPEC_ID': spec_id,
        'TITLE': title,
        'DATE': dt.date.today().isoformat(),
        'OWNER': args.owner.strip() or 'не назначен',
    }

    if args.dry_run:
        print(f'Будет создана спека {spec_id}: specs/{folder_name}/')
        for name in TEMPLATES:
            print(f'  - {name}')
        print(f'  владелец: {values["OWNER"]}, дата: {values["DATE"]}')
        return 0

    target.mkdir(parents=True)
    for name in TEMPLATES:
        content = render(templates_dir / name, values)
        (target / name).write_text(content, encoding='utf-8', newline='\n')

    print(f'Создана спека {spec_id}: specs/{folder_name}/')
    print('Дальше: заполните spec.md, пройдите ревью, затем plan.md и tasks.md.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
