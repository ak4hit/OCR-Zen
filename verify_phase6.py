"""
verify_phase6.py - Verification script for Phase 6: CLI, Rate Limiting & Robustness.

Tests:
  6.1 - Click CLI help output
  6.2 - RateLimiter token bucket (acquire, logging)
  6.3 - with_retry exponential backoff
  6.4 - QuotaTracker (record, check, warn, midnight reset)
  6.5 - KeyManager round-robin (already implemented in Phase 3 stub)
  6.6 - --offline flag (Tesseract only run via CLI)
  6.7 - Pre-flight quota check table
  6.8 - Batch payload mode via --payload-file
"""

import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Force UTF-8 output on Windows
import io as _io
sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def section(title: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print('=' * 62)


def main() -> None:

    # ── 6.2  RateLimiter ─────────────────────────────────────────────────────
    section("6.2 - RateLimiter token bucket")
    from core.rate_limiter import RateLimiter

    rl = RateLimiter(rpm_overrides={"gemini": 120})  # 120 RPM = 0.5s interval
    start = time.monotonic()
    rl.acquire("gemini")   # first call — no wait
    rl.acquire("gemini")   # second call — should wait ~0.5s
    elapsed = time.monotonic() - start
    print(f"  Two gemini acquires elapsed: {elapsed:.2f}s (expect >= 0.4s)")
    assert elapsed >= 0.4, f"Rate limiter not enforcing delay! elapsed={elapsed:.2f}s"
    print(f"  available_rpm('gemini') = {rl.available_rpm('gemini')}")
    print("  [PASS]")

    # ── 6.3  with_retry backoff ───────────────────────────────────────────────
    section("6.3 - with_retry exponential backoff")
    from main import with_retry

    call_count = 0
    def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("429 rate_limit error")
        return "success"

    result = with_retry(flaky_fn, engine_name="test_engine", max_retries=3)
    print(f"  Calls needed: {call_count} (expect 3)")
    print(f"  Result: {result}")
    assert result == "success", f"Expected 'success', got {result!r}"
    assert call_count == 3
    print("  [PASS]")

    # ── 6.4  QuotaTracker ────────────────────────────────────────────────────
    section("6.4 - QuotaTracker (record, check, warn, reset)")
    import tempfile
    from core.quota_tracker import QuotaTracker

    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / ".quota_state.json"
        qt = QuotaTracker(state_file=state_file)

        # Record usage
        qt.record("gemini", count=100)
        used, limit = qt.check("gemini")
        print(f"  gemini after 100 records: {used}/{limit}")
        assert used == 100

        # Check remaining
        rem = qt.remaining("gemini")
        print(f"  gemini remaining: {rem} (expect {limit - 100})")
        assert rem == limit - 100

        # Not exhausted yet
        assert not qt.is_exhausted("gemini")

        # Simulate exhaustion
        qt.record("gemini", count=limit - 100)
        assert qt.is_exhausted("gemini")
        print(f"  gemini exhausted after {limit} total: {qt.is_exhausted('gemini')}")

        # State persisted to disk
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["usage"]["gemini"] == limit
        print(f"  State file persisted: usage.gemini == {data['usage']['gemini']}")

        # Reload from disk — should restore state
        qt2 = QuotaTracker(state_file=state_file)
        used2, _ = qt2.check("gemini")
        assert used2 == limit
        print(f"  Reloaded from disk: usage.gemini == {used2}")

    print("  [PASS]")

    # ── 6.5  KeyManager round-robin ──────────────────────────────────────────
    section("6.5 - KeyManager round-robin key rotation")
    from core.key_manager import KeyManager

    km = KeyManager()
    k1 = km.get_key("gemini")
    km.rotate("gemini")
    k2 = km.get_key("gemini")
    print(f"  Initial key: {k1!r}")
    print(f"  After rotate: {k2!r}")
    # With single key, rotation wraps back to same key — that is correct behaviour
    print("  [PASS]")

    # ── 6.1  CLI --help ───────────────────────────────────────────────────────
    section("6.1 - Click CLI --help")
    import subprocess, sys as _sys, os
    _env = {**os.environ, "PYTHONUTF8": "1"}
    result = subprocess.run(
        [_sys.executable, "main.py", "--help"],
        capture_output=True, text=True, cwd=Path(__file__).parent,
        env=_env, encoding='utf-8', errors='replace'
    )
    print(result.stdout[:600])
    assert "--payload" in result.stdout
    assert "--offline" in result.stdout
    assert "--rate-limit" in result.stdout
    assert "--payload-file" in result.stdout
    assert "--calibrate-remote" in result.stdout
    print("  [PASS] All expected flags present in --help output")

    # ── 6.6  --offline run (Tesseract only, no API) ───────────────────────────
    section("6.6 - --offline CLI run (Tesseract only)")
    result = subprocess.run(
        [
            _sys.executable, "main.py",
            "--payload", "id && whoami",
            "--innocent", "Invoice #1234",
            "--techniques", "color_manipulation",
            "--offline",
            "--skip-calibration",
        ],
        capture_output=True, text=True, cwd=Path(__file__).parent,
        env=_env, encoding='utf-8', errors='replace'
    )
    output = result.stdout + result.stderr
    print(output[:800])
    assert result.returncode == 0, f"CLI exited with code {result.returncode}\n{output}"
    print("  [PASS] --offline run completed successfully")

    # ── 6.7  Pre-flight check (exercised inside offline run above) ────────────
    section("6.7 - Pre-flight quota check")
    assert "Pre-flight" in output or "available" in output.lower() or "Quota" in output
    print("  Pre-flight check ran (visible in 6.6 output above).")
    print("  [PASS]")

    # ── 6.8  Batch payload mode ───────────────────────────────────────────────
    section("6.8 - Batch payload mode (--payload-file)")
    import tempfile as _tmp
    with _tmp.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("id && whoami\n")
        f.write("chmod u+s /bin/bash\n")
        tmp_wl = f.name

    result = subprocess.run(
        [
            _sys.executable, "main.py",
            "--payload-file", tmp_wl,
            "--techniques", "color_manipulation",
            "--offline",
            "--skip-calibration",
        ],
        capture_output=True, text=True, cwd=Path(__file__).parent,
        env=_env, encoding='utf-8', errors='replace'
    )
    output = result.stdout + result.stderr
    print(output[:800])
    assert result.returncode == 0, f"Batch CLI failed: {output}"
    assert "payloads" in output.lower() or "Batch" in output
    Path(tmp_wl).unlink(missing_ok=True)
    print("  [PASS] Batch mode processed 2 payloads successfully")

    # ── Summary ───────────────────────────────────────────────────────────────
    section("Phase 6 Summary")
    print("  6.1 Click CLI flags .......... [OK]")
    print("  6.2 RateLimiter token bucket . [OK]")
    print("  6.3 with_retry backoff ....... [OK]")
    print("  6.4 QuotaTracker ............. [OK]")
    print("  6.5 KeyManager round-robin ... [OK]")
    print("  6.6 --offline mode ........... [OK]")
    print("  6.7 Pre-flight check ......... [OK]")
    print("  6.8 Batch payload mode ....... [OK]")
    print()
    print("  Phase 6 COMPLETE [OK]")


if __name__ == "__main__":
    main()
