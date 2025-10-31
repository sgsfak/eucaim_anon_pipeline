"""
Copy from an input folder all dicom files to an output folder. In hte output folder the files
will be organized in a hierarchical structure based on the patient ID , study UID, and series UID.
"""

import os
import shutil
from collections import namedtuple
from pathlib import Path
from typing import Generator

from loguru import logger

from .dicom_utils import dcm_generator


def copy_and_organize(input_folder: Path, output_folder: Path):
    cnt = 0
    dirs: dict[str, int] = {}
    # XXX: Should we order by InstanceNumber ??
    for dcm_info in dcm_generator(input_folder):
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
