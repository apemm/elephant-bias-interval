# The bias interval of the elephant random walk

This repository holds the paper *The bias interval of the elephant random
walk* by Arjun Pemmasani, the scripts behind its numerical values, and
Lean proofs of its finite sign arguments and analytic threshold.

The paper proves a conjecture of Guérin, Laulin, Raschel and Simon. For
every superdiffusive memory, the initial biases that make the limit density
bimodal form an open interval centered at one half. The interval is
nonempty exactly above a single memory threshold, numerically about
0.66881.

## Contents

| Folder | What it holds |
| --- | --- |
| [`paper/`](paper) | LaTeX sources, the class file, the figure, and `build.py` |
| [`certificates/`](certificates) | Interval-arithmetic scripts and their records for the numerical values |
| [`lean/`](lean) | The Lean library `PaperD`, its coverage map and its axiom audit |

## Build the paper

You need pdflatex and the Python package `pypdf`.

```text
python -B paper/build.py
```

The script writes `paper/bias_interval.pdf` and, in `dist/`, the arXiv
source archive, the journal package and the arXiv metadata. It stops if the
LaTeX log has an overfull box, an undefined reference or an error.

## Check the numerical values

The numerical values are not used in any proof. To recompute their interval
enclosures, install python-flint 0.9.0 and run, from `certificates/`:

```text
python -O check_critical_shape.py
python -O certify_critical_constants.py
python -O certify_transition.py --precision 1600 --moments 1100
```

Each script writes a JSON record to `certificates/data/` with its version,
arguments, precision and the hashes of its inputs. Compare a rerun with the
committed record. `certificates/error_analysis.pdf` proves the truncation and
tail bounds the scripts use. The phase figure comes from
`certificates/figures/make_phase_figure.py`, which needs NumPy, SciPy and
Matplotlib. The figure is an illustration, not a certificate.

## Check the Lean proofs

With the toolchain in `lean/lean-toolchain` installed, copy `lean/` to a folder
outside any synchronized drive and run:

```text
lake exe cache get
lake build PaperD
python verify_lean.py PaperD --workspace .
```

The script checks that every theorem uses only the axioms `propext`,
`Classical.choice` and `Quot.sound`, and writes `build-log.txt` and
`verification-manifest.json`. The coverage map [`lean/MAP.md`](lean/MAP.md)
lists the formal statement for each result of the paper and its hypotheses.

## License

See [`LICENSE`](LICENSE).
