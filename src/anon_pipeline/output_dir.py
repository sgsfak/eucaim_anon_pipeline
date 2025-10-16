"""
Copy from an input folder all dicom files to an output folder. In hte output folder the files
will be organized in a hierarchical structure based on the patient ID , study UID, and series UID.
"""

import os
import shutil
from collections import namedtuple
from pathlib import Path
from typing import Generator, Tuple

from loguru import logger
from pydicom import FileDataset, dcmread

_DcmFileInfo = namedtuple(
    "_DcmFileInfo", ["path", "patient_id", "study_uid", "series_uid", "instance_number"]
)


def _dcm_generator(input_folder: Path | str) -> Generator[_DcmFileInfo, None, None]:
    for root, dirs, files in os.walk(os.fspath(input_folder), topdown=True):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                ds: FileDataset = dcmread(file_path, stop_before_pixels=True)
                yield _DcmFileInfo(
                    Path(file_path),
                    ds.PatientID,
                    ds.StudyInstanceUID,
                    ds.SeriesInstanceUID,
                    ds.InstanceNumber,
                )
            except Exception as e:
                continue


def copy_and_organize(input_folder: Path, output_folder: Path):
    cnt = 0
    dirs: dict[str, int] = {}
    # XXX: Should we order by InstanceNumber ??
    for dcm_info in _dcm_generator(input_folder):
        current_output_folder = (
            output_folder
            / dcm_info.patient_id
            / dcm_info.study_uid
            / dcm_info.series_uid
        )
        if current_output_folder not in dirs:
            # Since we walk the input directory in top down manner, we are sure that when we visit
            # a directory its parent directory has already been visited and created. So
            # parents=True, exist_ok=True are not needed but ..ok :-)
            current_output_folder.mkdir(parents=True, exist_ok=True)
            dirs[current_output_folder] = 1
        index = dirs[current_output_folder]
        dirs[current_output_folder] += 1
        output_file = current_output_folder / f"{index:05d}.dcm"
        shutil.copy(dcm_info.path, output_file)
        cnt += 1
    logger.info(f"Copied and organized hierarchically {cnt} files")
