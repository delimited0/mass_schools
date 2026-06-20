from pathlib import Path

import pandas as pd


DATASET_PATTERNS = [
    "SAT_Performance_*",
    "Enrollment__Grade,_Race_Ethnicity,_Gender,_and_Selected_Populations_*",
    "Student_Discipline_*",
    "Advanced_Placement_(AP)_Performance_*",
    "MCAS_Achievement_Results_*",
    "pittsford_sat_scores",
]


def collect_csv_paths(base_path: Path) -> list[Path]:
    csv_paths: dict[str, Path] = {}
    for pattern in DATASET_PATTERNS:
        for path in base_path.glob(f"{pattern}.csv"):
            csv_paths[path.stem] = path
    return sorted(csv_paths.values())


def convert_csv_to_parquet(csv_path: Path) -> tuple[Path, int, int]:
    parquet_path = csv_path.with_suffix(".parquet")
    df = pd.read_csv(csv_path, low_memory=False)
    df.to_parquet(parquet_path, index=False, compression="snappy")
    return parquet_path, csv_path.stat().st_size, parquet_path.stat().st_size


def main() -> None:
    base_path = Path(__file__).resolve().parent
    csv_paths = collect_csv_paths(base_path)
    if not csv_paths:
        print("No matching CSV files found.")
        return

    for csv_path in csv_paths:
        parquet_path, csv_size, parquet_size = convert_csv_to_parquet(csv_path)
        reduction = 100 * (1 - (parquet_size / csv_size)) if csv_size else 0.0
        print(
            f"{csv_path.name} -> {parquet_path.name} | "
            f"{csv_size / (1024 * 1024):.1f} MB -> {parquet_size / (1024 * 1024):.1f} MB "
            f"({reduction:.1f}% smaller)"
        )


if __name__ == "__main__":
    main()
