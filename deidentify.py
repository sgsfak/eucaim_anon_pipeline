import subprocess
import uuid
from hashlib import sha256
from pathlib import Path


def run_ctp(
    *,
    input_dir: Path,
    output_dir: Path,
    anon_script: Path,
    site_id: str,
    threads: int,
) -> None:
    # use the folder of the anon.script as the current working directory
    cwd = anon_script.parent

    pepper = uuid.uuid4().hex  # Create a random string for "pepper"

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
        "4",
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
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )
    output, err = process.communicate()
    for line in output.decode("utf-8").splitlines():
        if line.startswith("Elapsed time:") or "Anonymized file" in line:
            print(line)
    for line in err.decode("utf-8").splitlines():
        print(f"CTP ERROR: {line}")
