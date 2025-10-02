from pathlib import Path

import pydicom
import typer
from loguru import logger
from presidio_image_redactor import DicomImageRedactorEngine
from typing_extensions import Annotated

INPUT_DIR: Path = Path("/input")
OUTPUT_DIR: Path = Path("/output")


def perform_ocr(input_dir: str | Path, output_dir: str | Path) -> None:
    engine = DicomImageRedactorEngine()
    output_dir = Path(output_dir)
    for file_path in Path(input_dir).rglob("*.dcm"):
        dicom_data = pydicom.dcmread(file_path)
        redacted_data = engine.redact(dicom_data, fill="contrast")
        output_path = output_dir / file_path.relative_to(INPUT_DIR)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        redacted_data.save_as(output_path)
        logger.info(f"Redacted {file_path.relative_to(INPUT_DIR)}")


def pipeline(
    ocr: Annotated[
        bool, typer.Option(help="Perform OCR and image deidentication")
    ] = True,
    input_dir: Annotated[
        Path,
        typer.Argument(
            help="Input directory to read DICOM files from", show_default=True
        ),
    ] = INPUT_DIR,
    output_dir: Annotated[
        Path,
        typer.Argument(
            help="Output directory to write processed DICOM files to",
            show_default=True,
        ),
    ] = OUTPUT_DIR,
):
    if ocr:
        perform_ocr(input_dir, output_dir)


if __name__ == "__main__":
    typer.run(pipeline)
