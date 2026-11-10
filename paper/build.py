"""Build the paper and its arXiv and journal packages.

Run from any folder with `python -B paper/build.py`. The script

1. checks that the statement on AI use matches its pinned text,
2. compiles bias_interval.tex with pdflatex in a temporary folder and
   refuses overfull boxes, undefined references and LaTeX errors,
3. copies the PDF to paper/bias_interval.pdf,
4. writes dist/arxiv_source.tar.gz, dist/journal_submission.zip and
   dist/arxiv_metadata.json.

It needs pdflatex and the Python package pypdf.
"""
from pathlib import Path
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

from pypdf import PdfReader

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
DIST = ROOT / 'dist'
MAIN = 'bias_interval.tex'
DISCLOSURE_SHA256 = '773e02b6e0cd12bebf6b44e372fe7b62b7386e3fc167420892e52504bdccd690'


def require(value, message):
    if not value:
        raise SystemExit(f'build failed: {message}')


inputs = []


def flatten(path):
    if path not in inputs:
        inputs.append(path)
    source = path.read_text(encoding='utf-8').replace('\r\n', '\n')
    return re.sub(r'\\input\{([^}]+)\}', lambda m: flatten(
        path.parent / (m[1] if m[1].endswith('.tex') else m[1] + '.tex')).rstrip('\n'), source)


def braced(text, start):
    """Return the contents of the brace group that opens at text[start]."""
    require(text[start] == '{', 'expected a brace group')
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{' and text[i - 1] != '\\':
            depth += 1
        elif text[i] == '}' and text[i - 1] != '\\':
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    raise SystemExit('build failed: unbalanced braces')


source = flatten(PAPER / MAIN)
require(source.count(r'\section*{Statement on AI use}') == 1, 'missing statement on AI use')
disclosure = source.split(r'\section*{Statement on AI use}', 1)[1].split(
    r'\begin{thebibliography}', 1)[0].strip()
require(hashlib.sha256(disclosure.encode()).hexdigest() == DISCLOSURE_SHA256,
        'the statement on AI use differs from its pinned text; update DISCLOSURE_SHA256 '
        'only after you have reviewed the new statement')
require(not any(ord(c) < 32 and c not in '\n\t' for c in source), 'control character in the source')

figures = sorted(set(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', source)))
sources = [PAPER / '00README.json', PAPER / 'ejpecp.cls', *inputs, *(PAPER / f for f in figures)]
for f in sources:
    require(f.exists(), f'missing file {f.name}')

env = dict(os.environ)
try:
    env['SOURCE_DATE_EPOCH'] = subprocess.check_output(
        ['git', 'log', '-1', '--format=%ct'], cwd=ROOT, text=True).strip()
except (OSError, subprocess.CalledProcessError):
    pass

with tempfile.TemporaryDirectory(prefix='bias-interval-') as folder:
    work = Path(folder)
    for f in sources:
        target = work / f.relative_to(PAPER)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
    for _ in range(3):
        subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', MAIN],
                       cwd=work, env=env, stdout=subprocess.DEVNULL, check=False)
    log = (work / MAIN).with_suffix('.log').read_text(encoding='utf-8', errors='replace')
    for bad in ['Overfull', '! ', 'undefined', 'Undefined', 'multiply defined', 'Rerun to get']:
        require(bad not in log, f'LaTeX log contains "{bad}"')
    pdf = PAPER / 'bias_interval.pdf'
    shutil.copy2((work / MAIN).with_suffix('.pdf'), pdf)

reader = PdfReader(pdf)
pages = len(reader.pages)
abstract = ' '.join(braced(source, source.index(r'\ABSTRACT') + len(r'\ABSTRACT')).split())
title = braced(source, source.index(r'\TITLE') + len(r'\TITLE'))
cited = set(k.strip() for group in re.findall(r'\\cite(?:\[[^\]]*\])?\{([^}]+)\}', source)
            for k in group.split(','))
printed = set(re.findall(r'\\bibitem\{([^}]+)\}', source))
require(cited <= printed, f'cited but not in the bibliography: {sorted(cited - printed)}')
require(printed <= cited, f'in the bibliography but not cited: {sorted(printed - cited)}')

DIST.mkdir(exist_ok=True)
names = sorted(f.relative_to(PAPER).as_posix() for f in sources)
with tarfile.open(DIST / 'arxiv_source.tar.gz', 'w:gz', format=tarfile.USTAR_FORMAT) as tar:
    for name in names:
        data = (PAPER / name).read_bytes()
        info = tarfile.TarInfo(name)
        info.size, info.mode, info.mtime = len(data), 0o644, 0
        tar.addfile(info, io.BytesIO(data))
with zipfile.ZipFile(DIST / 'journal_submission.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(pdf, 'bias_interval.pdf')
    for name in names:
        z.write(PAPER / name, name)
figure_count = source.count(r'\begin{figure}')
metadata = {
    'title': title,
    'author': 'Arjun Pemmasani',
    'primary_category': 'math.PR',
    'cross_list': 'cond-mat.stat-mech',
    'abstract': abstract,
    'comments': f'{pages} pages, {figure_count} figures. Code, certificates and Lean files: '
                'https://github.com/apemm/elephant-bias-interval',
    'license': 'arXiv.org perpetual, non-exclusive license',
}
(DIST / 'arxiv_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pages': pages, 'figures': figure_count, 'files': len(names),
                  'citations': len(printed), 'disclosure': 'unchanged'}, indent=2))
