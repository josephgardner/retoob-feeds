#!/usr/bin/env python3
"""Render the Markdown specification as an HTML page in the Pages artifact, not in the Git tree."""
import argparse
import html
import pathlib

import markdown2

REPOSITORY = 'https://github.com/josephgardner/retoob-feeds'
STYLE = ('main{max-width:820px}main h2{margin-top:2.5em}table{border-collapse:collapse;margin:1em 0;display:block;overflow-x:auto}'
         'th,td{border:1px solid #2a3742;padding:6px 10px;text-align:left;vertical-align:top}'
         'code{background:#161d24;border-radius:4px;padding:1px 4px}pre{background:#161d24;padding:14px;overflow-x:auto}'
         'pre code{padding:0}main p,main li{line-height:1.6}')


def render(source, output):
    text = source.read_text()
    title = text.splitlines()[0].lstrip('# ').strip()
    body = markdown2.markdown(text, extras=['tables', 'fenced-code-blocks', 'header-ids'])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
                      '<meta name="viewport" content="width=device-width,initial-scale=1">'
                      '<title>' + html.escape(title) + '</title><link rel="stylesheet" href="../viewer.css">'
                      '<style>' + STYLE + '</style><header><a href="../">Algoplay feeds</a><a href="' + REPOSITORY +
                      '">GitHub repository</a></header><main>' + body + '</main></html>\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    args = p.parse_args()
    render(args.source, args.output)
