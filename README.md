```

                         ██╗     ███████╗████████╗██╗  ██╗███████╗
                         ██║     ██╔════╝╚══██╔══╝██║  ██║██╔════╝
                         ██║     █████╗     ██║   ███████║█████╗
                         ██║     ██╔══╝     ██║   ██╔══██║██╔══╝
                         ███████╗███████╗   ██║   ██║  ██║███████╗
                         ╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
```

## DICOM Anonymization Pipeline in a Box

A DICOM Anonymization pipeline in a Docker container. This pipeline is designed to anonymize DICOM files according to the EUCAIM standard and includes the following steps:
- **Step 1 (Optional):** Perform OCR on DICOM pixel data to remove sensitive information (burned-in information).
- **Step 2:** Deidentify DICOM metadata using the RSNA CTP Anonymizer and the [EUCAIM anonymization script](ctp/anon.script).
- **Step 3 (Optional):** Deidentify clinical data provided in CSV files so that the referenced patient id is anonymized the same way CTP does in Step 2.


### Usage

You can pull the Docker image from GitHub Container Registry:

```
docker pull ghcr.io/sgsfak/eucaim_anon_pipeline
```


Then you can run the pipeline using the following command, which shows the bare minimum information required to run the pipeline:

```
docker run -v <INPUT-DIR>:/input -v <OUTPUT-DIR>:/output ghcr.io/sgsfak/eucaim_anon_pipeline <SITE-ID>
```

where the options are as follows:

* `<INPUT-DIR>` is the folder on the local machine where the DICOM files to be anonymized reside. Please note that this folder could also contain a CSV file with clinical data so that those data can be properly linked with the anonymized DICOM files (details below)
* `<OUTPUT-DIR>` is the folder on the local machine where the anonymized DICOM files will be written to. In this folder, a new CSV will be also produced containing the anonymized clinical data, should the input folder had one.
* `<SITE-ID>` is the SITE-ID provided by the EUCAIM Technical team and it's a mandatory parameter to the pipeline to be used as "provider id" (after hashing it...)

There are more options that can be specified in the command line. To see the list of available options, please run:

```
docker run ghcr.io/sgsfak/eucaim_anon_pipeline --help
```
which should return the following:

```
Usage: lethe [OPTIONS] SITE_ID [INPUT_DIR] [OUTPUT_DIR]

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    site_id         TEXT          The SITE-ID provided by the EUCAIM        │
│                                    Technical team                            │
│                                    [required]                                │
│      input_dir       [INPUT_DIR]   Input directory to read DICOM files from  │
│                                    [default: /input]                         │
│      output_dir      [OUTPUT_DIR]  Output directory to write processed DICOM │
│                                    files to                                  │
│                                    [default: /output]                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --ocr                                             Perform OCR (using         │
│                                                   Tesseract) and image       │
│                                                   deidentication             │
│ --paddle-ocr                                      Perform OCR using          │
│                                                   PaddleOCR and image        │
│                                                   deidentification           │
│ --threads                                INTEGER  Number of threads that     │
│                                                   RSNA CTP and PaddleOCR (if │
│                                                   enabled) will use          │
│                                                   [default: 10]              │
│ --hierarchical      --no-hierarchical             Output files will be       │
│                                                   organized into a           │
│                                                   hierarchical Patient /     │
│                                                   Study / Series folder      │
│                                                   structure using the        │
│                                                   anonymized UIDs as the     │
│                                                   folder names               │
│                                                   [default: hierarchical]    │
│ --verbose       -v                                Enable verbose logging     │
│ --help                                            Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

* Passing `--ocr` or `--paddle-ocr` will enable the Optical Character Recognition (OCR) feature for redacting "burned-in" text in the raw images. *Please note that by default no OCR will run!* The `--ocr` will run [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and the `--paddle-ocr` will run [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR). PaddleOCR seems to be more accurate than Tesseract OCR but also slower and requires more resources.
* `--threads` can be used to specify the number of threads that RSNA CTP and PaddleOCR (if enabled) will use and it can be used to increase the speed of the pipeline if it runs in multi-core CPU. By default, it is set to 10.
* `--hierarchical` (default) will organize the anonymized DICOM files into a hierarchical folder structure based on the patient ID, study ID, and series ID. Each output DICOM file will also have a name consisting of digits based on an auto-numbering system, e.g. `00001.dcm`, `00002.dcm`, etc. **We suggest to always keep this option in the default `--hierarchical` mode, because it makes the output folder structure more organized but more importantly it makes sure that no sensitive information is leaked in the output folder and file names.**

#### PaddleOCR models
PaddleOCR supports multiple different models for [text detection](https://paddlepaddle.github.io/PaddleX/latest/en/module_usage/tutorials/ocr_modules/text_detection.html), [text recognition](https://paddlepaddle.github.io/PaddleX/latest/en/module_usage/tutorials/ocr_modules/text_recognition.html), etc. By default in this Docker image we include the "lite" (mobile) models of PP-OCRv5: `PP-OCRv5_mobile_det` for text detection and `PP-OCRv5_mobile_rec` for text recognition as can be seen in the integrated [PaddleOCR.yaml](PaddleOCR.yaml) file. To further support additional models like the more complex and accurate "server" models, you can create your own YAML file (by copying the [PaddleOCR.yaml](PaddleOCR.yaml) file and modifying it) with the desired models and then running the `docker run` command with this new YAML file in the host machine mounted as `/app/PaddleOCR.yaml`, like so:

```
docker run -v <INPUT-DIR>:/input -v <OUTPUT-DIR>:/output -v <PADDLEOCR_YAML_FILE>:/app/PaddleOCR.yaml ghcr.io/sgsfak/eucaim_anon_pipeline <SITE-ID> --paddle-ocr
```

### Clinical data
In case there are additional (clinical) data for the patients for which the anonymization is performed, it is recommended to provide the data in one or more CSV files in the same input directory that contains the DICOM files. This is needed so that the patient ids mentioned in the CSV file are replaced with anonymized patient ids so that they are consistent with the anonymized DICOM files.

> **Note:** The CSVs should have a `.csv` file extension and be located directly in the input directory, not in a subdirectory!

In order to accomodate cases where the clinical data have been exported to multiple CSV files, the pipeline will automatically process **all** CSV files found in the input directory **except** those that start with the prefix `_` (undescore). So a CSV with file name `clinical_data.csv` will be processed (hashed, as explained below), whereas a CSV with file name `_clinical_data.csv` will be just copied verbatim to the output directory.

The CSVs to the processed (hashed) are assumed to have the following format:
* The first line of the file is assumed to be a header line containing the column names
* The first column should contain the patientID

You can see an example input CSV of this format [here](example_clinical.csv)
