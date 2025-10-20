import subprocess
from collections import namedtuple
from hashlib import sha256
from pathlib import Path

from loguru import logger

CTPResults = namedtuple("CTPResults", ["elapsed_time", "processed_count"])


def _process_ctp_output(lines: list[str]) -> CTPResults:
    elapsed_time = 0
    processed_count = 0
    for line in lines:
        if line.startswith("Elapsed time:"):
            elapsed_time = float(line.strip().split(":")[1].strip())
        elif "Anonymized file" in line:
            processed_count += 1
    return CTPResults(elapsed_time, processed_count)


def run_ctp(
    *,
    input_dir: Path,
    output_dir: Path,
    anon_script: Path,
    site_id: str,
    pepper: str,
    threads: int,
) -> None:
    # use the folder of the anon.script as the current working directory
    cwd = anon_script.parent

    # To make more difficult the identification of the original provider given
    # the contents of the anonymized DICOM files, we hash the "site id" and add
    # its hex digest as the "provider id" in the result DICOM images. We are using
    # SHA-256 which produces hex string of 32 x 2 = 64 bytes, so it's ok to add it
    # on any tag of "LO" (Long String) value representation (VR) that is at most 64
    # characters/bytes according to DICOM :
    # https://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html#:~:text=LO
    #
    #
    providerId = sha256(site_id.encode()).hexdigest()

    cmd = [
        "java",
        "-jar",
        "DAT.jar",
        "-n",
        str(threads),
        "-da",
        str(anon_script),
        "-pPROVIDERID",
        providerId,
        "-pSECRET_KEY",
        pepper,
        "-in",
        str(input_dir.absolute()),
        "-out",
        str(output_dir.absolute()),
    ]
    logger.info("Running CTP command, output will be saved to {}".format(output_dir))
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )
    output, err = process.communicate()
    results = _process_ctp_output(output.decode("utf-8").splitlines())
    for line in err.decode("utf-8").splitlines():
        print(f"CTP ERROR: {line}")
    logger.info(
        "CTP command completed, elapsed time: {} seconds, files anonymized: {}".format(
            results.elapsed_time, results.processed_count
        )
    )
