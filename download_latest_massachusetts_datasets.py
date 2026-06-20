from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Dataset:
    file_prefix: str
    csv_url: str


DATASETS = [
    Dataset(
        file_prefix="SAT_Performance",
        csv_url="https://educationtocareer.data.mass.gov/api/views/wihy-jkek/rows.csv?accessType=DOWNLOAD",
    ),
    Dataset(
        file_prefix="Enrollment__Grade,_Race_Ethnicity,_Gender,_and_Selected_Populations",
        csv_url="https://educationtocareer.data.mass.gov/api/views/t8td-gens/rows.csv?accessType=DOWNLOAD",
    ),
    Dataset(
        file_prefix="Student_Discipline",
        csv_url="https://educationtocareer.data.mass.gov/api/views/2kca-w7rq/rows.csv?accessType=DOWNLOAD",
    ),
    Dataset(
        file_prefix="Advanced_Placement_(AP)_Performance",
        csv_url="https://educationtocareer.data.mass.gov/api/views/avkf-cq9k/rows.csv?accessType=DOWNLOAD",
    ),
    Dataset(
        file_prefix="MCAS_Achievement_Results",
        csv_url="https://educationtocareer.data.mass.gov/api/views/i9w6-niyt/rows.csv?accessType=DOWNLOAD",
    ),
]

USER_AGENT = "mass-schools-dataset-downloader/1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the latest Massachusetts education datasets as CSV files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory where the downloaded CSV files should be written.",
    )
    parser.add_argument(
        "--date-stamp",
        default=datetime.now().strftime("%Y%m%d"),
        help="Date suffix to append to each filename. Defaults to today's date in YYYYMMDD format.",
    )
    return parser.parse_args()


def build_output_path(output_dir: Path, dataset: Dataset, date_stamp: str) -> Path:
    return output_dir / f"{dataset.file_prefix}_{date_stamp}.csv"


def download_dataset(dataset: Dataset, output_path: Path) -> int:
    request = Request(dataset.csv_url, headers={"User-Agent": USER_AGENT})
    temp_path = output_path.with_suffix(f"{output_path.suffix}.part")

    with urlopen(request) as response:
        status = getattr(response, "status", response.getcode())
        if status != 200:
            raise RuntimeError(f"Download failed for {dataset.file_prefix}: HTTP {status}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)

    temp_path.replace(output_path)
    return output_path.stat().st_size


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()

    for dataset in DATASETS:
        output_path = build_output_path(output_dir, dataset, args.date_stamp)
        file_size = download_dataset(dataset, output_path)
        print(f"Downloaded {output_path.name} ({file_size / (1024 * 1024):.1f} MB)")


if __name__ == "__main__":
    main()
