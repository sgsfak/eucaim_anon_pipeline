import os
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable

from pydicom import FileDataset, dcmread
from sortedcontainers import SortedDict

DcmFileInfo = namedtuple(
    "DcmFileInfo",
    [
        "path",
        "patient_id",
        "study_uid",
        "series_uid",
        "instance_number",
    ],
)


@dataclass(kw_only=True, eq=False)
class SeriesInfo:
    patient_id: str
    study_uid: str
    series_uid: str
    series_description: str
    study_description: str
    modality: str
    image_count: int


def series_information(input_dir: Path) -> Iterable[SeriesInfo]:
    seen_so_far: SortedDict[tuple[str, str, str], SeriesInfo] = SortedDict()
    for root, dirs, files in os.walk(os.fspath(input_dir), topdown=True):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                dataset: FileDataset = dcmread(file_path, stop_before_pixels=True)
                key = (
                    dataset.PatientID,
                    dataset.StudyInstanceUID,
                    dataset.SeriesInstanceUID,
                )
                if key in seen_so_far:
                    seen_so_far[key].image_count += 1
                    continue
                series_info = SeriesInfo(
                    patient_id=dataset.PatientID,
                    study_uid=dataset.StudyInstanceUID,
                    series_uid=dataset.SeriesInstanceUID,
                    series_description=dataset.get("SeriesDescription", ""),
                    study_description=dataset.get("StudyDescription", ""),
                    modality=dataset.get("Modality", ""),
                    image_count=1,
                )
                seen_so_far[key] = series_info
            except Exception:
                continue
    return seen_so_far.values()


def dcm_generator(input_folder: Path | str) -> Generator[DcmFileInfo, None, None]:
    for root, dirs, files in os.walk(os.fspath(input_folder), topdown=True):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                ds: FileDataset = dcmread(file_path, stop_before_pixels=True)
                yield DcmFileInfo(
                    Path(file_path),
                    ds.PatientID,
                    ds.StudyInstanceUID,
                    ds.SeriesInstanceUID,
                    ds.InstanceNumber,
                )
            except Exception:
                continue
