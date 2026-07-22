# datatrawl-analyzer-template


A working starting point for a [datatrawl](https://github.com/WVURAIL/datatrawl)
analyzer that lives in **your own repository**. Click **Use this template**,
rename a few things, and your science plugin is installable, discoverable, and
tested -- while datatrawl itself stays untouched.
 
That split is deliberate: instrument, source, and reader changes go to
[datatrawl](https://github.com/WVURAIL/datatrawl) as pull requests, while
analyzers are never merged there -- an analyzer lives here, in the repository
that owns the science.

The template ships one complete analyzer, `freq_id-peak` (averaged power
spectrum + peak bin, one product per freq_id). It is small enough to read in one
sitting but exercises everything a real analysis needs: the full `Analyzer`
protocol with per-freq_id fan-out, an analyzer parameter read from
`ctx.options` via `--set dc_mask_hz=...`, and strict resume validation that
stamps parameters into the product and refuses incompatible reruns.

## Quickstart

```bash
git clone <your-copy-of-this-template>
cd <your-repo>

python -m venv .venv
. .venv/bin/activate

pip install -e ".[dev]"    # pulls the pinned datatrawl release from GitHub
pytest -q                  # synthetic data through the real engine; no archive access needed
```

`pip install -e .` is the whole integration: the entry point declared in
`pyproject.toml` makes the analyzer first-class, with no `--plugin` flag:

```bash
datatrawl list analyzers   # freq_id-peak appears
datatrawl doctor --telescope chime --source local \
  --reader chime-baseband --analyzer freq_id-peak
```

The test suite (`tests/test_smoke.py`) is the proof of life: it writes synthetic
CHIME-baseband files with a tone at a known frequency, runs a real
`datatrawl scan` against them via the `local` source, checks the analyzer finds
the tone, and checks the resume contract (an identical rerun is a no-op; a rerun
with a different `--set dc_mask_hz` is refused).

## Making it yours

Replace the science first, rename second:

1. **Science.** Edit `src/my_analyzer/analyzer.py`: `consume_file()` is the
   streaming pass, `save()`/`resume()` are the product and its resume contract.
   Keep the pattern of stamping every meaning-changing parameter into the
   product.
2. **Rename** (grep for each):
   - package dir `src/my_analyzer/` and imports of `my_analyzer`;
   - `name = "my-analyzer"` in `pyproject.toml`;
   - the entry point line `freq_id-peak = "my_analyzer.analyzer"` -- the key is
     your analyzer's CLI name, the value is the module that registers it;
   - `name="freq_id-peak"` in the `PluginInfo`, `_SIGNATURE`, and the class name;
   - the expectations in `tests/test_smoke.py`.
3. **Reinstall** (`pip install -e .`) so the new entry-point metadata is picked
   up, then `pytest -q`.
4. When your analysis outgrows the synthetic tone (different product keys,
   different pass/fail), rewrite the assertions in `test_smoke.py` to match --
   the harness (synthesize, scan, rerun, refuse) is the part worth keeping.

## Version pinning

`pyproject.toml` pins `datatrawl @ git+https://github.com/WVURAIL/datatrawl.git@v0.2.0`.
Bump the tag deliberately when you upgrade, and rerun the tests -- that is your
compatibility check.

## Where the real documentation lives

This template is the *shape*; the contracts are documented in datatrawl:

- [`docs/ADDING_AN_ANALYZER.md`](https://github.com/WVURAIL/datatrawl/blob/master/docs/ADDING_AN_ANALYZER.md)
  -- the analyzer contract: order-dependence, fan-out, run parameters (`--set`),
  resume validation, auxiliary inputs.
- [`docs/TROUBLESHOOTING.md`](https://github.com/WVURAIL/datatrawl/blob/master/docs/TROUBLESHOOTING.md)
  -- long runs, self-healing, quarantine, recovery.
