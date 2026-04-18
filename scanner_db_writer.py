"""
scanner_db_writer.py — Task B1: Connect Scanner → Postgres

Usage:
    python scanner_db_writer.py --market NSE
    python scanner_db_writer.py --market US

Requires DATABASE_URL in environment (or .env file in same directory).

Contract with Claude Code (frontend):
  - scans.market          : "NSE" | "US"
  - scan_results.market   : "NSE" | "US"
  - scan_results.symbol   : bare symbol WITHOUT .NS suffix (e.g. "HDFC", "AAPL")
  - scan_results.price_at_scan : raw price in local currency (INR for NSE, USD for US)
"""

import os
import sys
import uuid
import argparse
import logging
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv

from scanner import scan_market

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("scanner_db_writer")


def get_db_connection():
    """Connect to Postgres using DATABASE_URL from environment."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise EnvironmentError(
            "DATABASE_URL is not set. "
            "Add it to your .env file or export it in your shell."
        )
    return psycopg2.connect(db_url)


def run_scan_and_save(market: str = "NSE") -> dict:
    """
    Runs the technical scanner for the given market and writes results to Postgres.

    Args:
        market: "NSE" or "US"

    Returns:
        dict with keys: scan_id, market, total_scanned, good_results_count, status
    """
    if market not in ("NSE", "US"):
        raise ValueError(f"Invalid market '{market}'. Must be 'NSE' or 'US'.")

    conn = get_db_connection()
    cur = conn.cursor()
    scan_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    log.info(f"[{market}] Starting scan — ID: {scan_id}")

    # ── Step 1: Insert scan record (status=RUNNING) ───────────────────────
    try:
        cur.execute(
            """
            INSERT INTO scans (id, run_at, status, market, total_scanned, good_results_count)
            VALUES (%s, %s, 'RUNNING', %s, 0, 0)
            """,
            (scan_id, started_at, market),
        )
        conn.commit()
        log.info(f"[{market}] Scan record created (RUNNING).")
    except Exception as e:
        log.error(f"[{market}] Failed to create scan record: {e}")
        cur.close()
        conn.close()
        raise

    # ── Step 2: Run the scanner ───────────────────────────────────────────
    try:
        results = scan_market(market=market)
        log.info(f"[{market}] Scanner returned {len(results)} hits.")

    except Exception as e:
        log.error(f"[{market}] Scanner failed: {e}")
        cur.execute("UPDATE scans SET status='FAILED' WHERE id=%s", (scan_id,))
        conn.commit()
        cur.close()
        conn.close()
        raise

    # ── Step 3: Insert scan_results rows ─────────────────────────────────
    good_count = 0
    failed_rows = 0

    try:
        for r in results:
            try:
                row_id = str(uuid.uuid4())

                # Determine category — future: OFFLINE if price=0 or data error
                category = r.get("category", "STANDARD")
                if r.get("price", 0) == 0:
                    category = "OFFLINE"

                cur.execute(
                    """
                    INSERT INTO scan_results (
                        id, scan_id, symbol, market,
                        mb_score, mb_tier,
                        total_score, price_at_scan,
                        sector, category,
                        l1, l2, l3, l4, l5, l6
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        row_id,
                        scan_id,
                        r["symbol"],          # clean symbol, no .NS suffix
                        market,
                        float(r.get("mb_score", 0)),
                        r.get("mb_tier", "Builder"),
                        float(r.get("total_score", 0)),
                        float(r.get("price", 0)),
                        r.get("sector", "Unknown"),
                        category,
                        bool(r.get("l1", False)),
                        bool(r.get("l2", False)),
                        bool(r.get("l3", False)),
                        bool(r.get("l4", False)),
                        bool(r.get("l5", False)),
                        bool(r.get("l6", False)),
                    ),
                )

                if category != "OFFLINE":
                    good_count += 1

            except Exception as row_err:
                log.warning(f"[{market}] Failed to insert row for {r.get('symbol', '?')}: {row_err}")
                failed_rows += 1
                # Don't abort the whole scan — skip the bad row and continue

        conn.commit()
        log.info(f"[{market}] Inserted {len(results) - failed_rows} rows ({failed_rows} skipped).")

    except Exception as e:
        log.error(f"[{market}] Bulk insert failed: {e}")
        cur.execute("UPDATE scans SET status='FAILED' WHERE id=%s", (scan_id,))
        conn.commit()
        cur.close()
        conn.close()
        raise

    # ── Step 4: Mark scan COMPLETED ──────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    try:
        cur.execute(
            """
            UPDATE scans
            SET status='COMPLETED', total_scanned=%s, good_results_count=%s
            WHERE id=%s
            """,
            (len(results), good_count, scan_id),
        )
        conn.commit()
        log.info(
            f"[{market}] ✅ Scan COMPLETED in {elapsed:.1f}s — "
            f"{good_count} good results / {len(results)} total scanned."
        )
    except Exception as e:
        log.error(f"[{market}] Failed to mark scan COMPLETED: {e}")
        raise
    finally:
        cur.close()
        conn.close()

    return {
        "scan_id": scan_id,
        "market": market,
        "total_scanned": len(results),
        "good_results_count": good_count,
        "status": "COMPLETED",
        "elapsed_seconds": elapsed,
    }


# ── CLI Entry Point ───────────────────────────────────────────────────────────

def main():
    # Load .env from the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        log.info(f"Loaded environment from {dotenv_path}")
    else:
        log.warning(f".env not found at {dotenv_path} — relying on shell environment.")

    parser = argparse.ArgumentParser(
        description="Fortress Scanner DB Writer — runs the market scanner and writes results to Postgres."
    )
    parser.add_argument(
        "--market",
        type=str,
        default="NSE",
        choices=["NSE", "US"],
        help="Market to scan: NSE (India) or US (S&P 500). Default: NSE",
    )
    args = parser.parse_args()

    try:
        result = run_scan_and_save(market=args.market)
        log.info(f"Done: {result}")
        sys.exit(0)
    except Exception as e:
        log.error(f"Scan failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
