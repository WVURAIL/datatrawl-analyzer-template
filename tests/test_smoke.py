"""
End-to-end smoke test for the template analyzer.

Runs the *installed* `datatrawl` console script as a subprocess, so it proves
the one thing an in-repo example never could: after `pip install -e .`, the
entry point in pyproject.toml makes the analyzer discoverable with no
`--plugin` flag, and it runs through the real engine.

Needs no archive access and no CADC account: the input is synthetic
CHIME-baseband HDF5 written by datatrawl's own test helper, with a CW tone
injected at a known baseband frequency. If the analyzer's reported peak lands
on the tone, the whole path works.

Cases:
  1. discovery -- `datatrawl list analyzers` shows `freq_id-peak` (entry point);
  2. scan      -- a local-source scan produces a product whose peak is the tone;
  3. resume    -- rerunning the identical command is a no-op (product unchanged);
  4. refusal   -- rerunning with a different `--set dc_mask_hz` is rejected.
"""
from __future__ import annotations

import glob
import os
import shutil
import sys
import subprocess

import numpy as np
import pytest

from datatrawl import instruments as inst_mod
from datatrawl.plugins.readers._baseband_format import FS, NFFT, make_synth_file

FREQ_ID = 844
F_TONE_BB = 12000.0          # injected baseband tone (Hz)
DF_HZ = FS / NFFT            # one FFT bin
N_FILES = 3


def _run(argv, cwd):
    # The console script that belongs to THIS interpreter's environment --
    # a bare PATH lookup can escape the venv and find some other datatrawl.
    exe = os.path.join(os.path.dirname(sys.executable), "datatrawl")
    if not os.path.exists(exe):
        exe = shutil.which("datatrawl")
    assert exe, "datatrawl console script not found -- is datatrawl installed?"
    return subprocess.run([exe, *argv], capture_output=True, text=True, cwd=cwd)


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    """A tiny synthetic file library for one freq_id, named for the local source."""
    d = tmp_path_factory.mktemp("lib")
    inst = inst_mod.load_instrument("chime")
    fc_mhz = inst.freq_of_freq_id(FREQ_ID)
    for k in range(N_FILES):
        make_synth_file(str(d / f"baseband_s{k}_{FREQ_ID}.h5"),
                        6 * NFFT, 32, fc_mhz, F_TONE_BB, seed=k + 1)
    return d


def _scan_argv(library, extra=None):
    return ["scan", "--telescope", "chime", "--source", "local",
            "--reader", "chime-baseband", "--analyzer", "freq_id-peak",
            "--select", str(FREQ_ID), "--source-root", str(library),
            "--checkpoint-every", "1",
            "--set", "dc_mask_hz=500"] + (extra or [])


def _product(root):
    hits = glob.glob(os.path.join(root, "results", "**", f"{FREQ_ID}.npz"),
                     recursive=True)
    assert len(hits) == 1, f"expected exactly one product, found {hits}"
    return hits[0]


def test_entry_point_discovery(tmp_path):
    """pip install -e . is enough: no --plugin flag anywhere in this file."""
    res = _run(["list", "analyzers"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    assert "freq_id-peak" in res.stdout


def test_scan_recovers_the_tone(library, tmp_path):
    res = _run(_scan_argv(library), cwd=tmp_path)
    assert res.returncode == 0, res.stderr + res.stdout

    z = np.load(_product(tmp_path), allow_pickle=False)
    assert int(z["freq_id"]) == FREQ_ID
    assert int(z["count"]) > 0
    assert len(z["files"]) == N_FILES
    assert abs(float(z["peak_hz"]) - F_TONE_BB) <= DF_HZ, (
        f"peak {float(z['peak_hz']):+.1f} Hz is not the injected tone "
        f"{F_TONE_BB:+.1f} Hz")


def test_identical_rerun_is_a_noop(library, tmp_path):
    assert _run(_scan_argv(library), cwd=tmp_path).returncode == 0
    before = open(_product(tmp_path), "rb").read()

    res = _run(_scan_argv(library), cwd=tmp_path)
    assert res.returncode == 0, res.stderr + res.stdout
    assert open(_product(tmp_path), "rb").read() == before, (
        "rerunning a complete scan modified the product")


def test_changed_set_parameter_refuses_resume(library, tmp_path):
    assert _run(_scan_argv(library), cwd=tmp_path).returncode == 0

    res = _run(_scan_argv(library, extra=["--set", "dc_mask_hz=999"]),
               cwd=tmp_path)
    assert res.returncode != 0, "a changed --set parameter must refuse to resume"
    assert "dc_mask_hz" in (res.stderr + res.stdout)
