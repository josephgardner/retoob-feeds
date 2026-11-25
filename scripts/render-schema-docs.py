#!/usr/bin/env python3
"""Render each JSON Schema as an HTML reference page in the Pages artifact, not in the Git tree."""
import argparse
import html
import pathlib
import subprocess

REPOSITORY = 'https://github.com/josephgardner/retoob-feeds'


def render(source, output):
    output.mkdir(parents=True, exist_ok=True)
    for schema in sorted(source.glob('*.schema.json')):
        page = output / (schema.name[:-len('.json')] + '.html')
        subprocess.run(['generate-schema-doc', '--config', 'template_name=js_offline', str(schema), str(page)], check=True)
        text = page.read_text()
        if text.count('<h1>') != 1:
            raise ValueError('Unexpected schema page layout')
        links = ('<p class="schema-links" style="display:flex;flex-wrap:wrap;gap:0 1.5rem"><a href="' +
                 html.escape(schema.name, quote=True) + '">Raw JSON Schema</a><a href="' + REPOSITORY +
                 '">GitHub repository</a><a href="../">Feed directory</a></p>')
        page.write_text(text.replace('<h1>', links + '<h1>'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    render(args.source, args.output)
