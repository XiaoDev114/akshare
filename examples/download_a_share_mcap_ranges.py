"""Download A-share daily price history for fixed market-cap rank ranges."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

import akshare as ak
import pandas as pd


@dataclass(frozen=True)
class RankRange:
    name: str
    start: int
    end: int


RANK_RANGES = (
    RankRange("top10", 1, 10),
    RankRange("rank_100_200", 100, 200),
    RankRange("rank_1000_1200", 1000, 1200),
)


def fetch_ranked_symbols() -> pd.DataFrame:
    """Fetch current A-share snapshot and return with market-cap ranking."""
    snapshot = ak.stock_zh_a_spot_em()
    snapshot = snapshot.rename(columns={"代码": "code", "总市值": "mcap"})
    snapshot["mcap"] = pd.to_numeric(snapshot["mcap"], errors="coerce")
    snapshot = snapshot.sort_values("mcap", ascending=False).reset_index(drop=True)
    snapshot["rank"] = snapshot.index + 1
    return snapshot


def symbols_for_ranges(snapshot: pd.DataFrame, ranges: Iterable[RankRange]) -> dict[str, list[str]]:
    """Return symbols for each rank range, ensuring fixed counts."""
    result: dict[str, list[str]] = {}
    for rank_range in ranges:
        mask = snapshot["rank"].between(rank_range.start, rank_range.end)
        result[rank_range.name] = snapshot.loc[mask, "code"].tolist()
    return result


def download_history(symbol: str, start_date: str, end_date: str, out_dir: str) -> None:
    """Download daily history for a single symbol and save to CSV."""
    try:
        data = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
    except Exception as exc:  # pragma: no cover - depends on external API
        print(f"[ERR] {symbol}: {exc}")
        return

    if data.empty:
        print(f"[WARN] {symbol}: no data")
        return

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{symbol}.csv")
    data.to_csv(out_path, index=False)
    print(f"[OK] {symbol} -> {out_path}")


def main() -> None:
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=3650)).strftime("%Y%m%d")

    snapshot = fetch_ranked_symbols()
    symbols_by_range = symbols_for_ranges(snapshot, RANK_RANGES)

    for rank_range in RANK_RANGES:
        symbols = symbols_by_range.get(rank_range.name, [])
        out_dir = os.path.join("data", rank_range.name)
        print(f"\n=== Downloading {rank_range.name} ({len(symbols)} symbols) ===")
        for symbol in symbols:
            download_history(symbol, start_date, end_date, out_dir)


if __name__ == "__main__":
    main()
