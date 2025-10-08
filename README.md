## EUCAIM Anonymization Pipeline in a Box

A DICOM Anonymization pipeline in a Docker container. This pipeline is designed to anonymize DICOM files according to the EUCAIM standard and includes the following steps:
- **Step 1 (Optional):** Perform OCR on DICOM pixel data to remove sensitive information (burned-in information).
- **Step 2:** Deidentify DICOM metadata using the RSNA CTP Anonymizer and the [EUCAIM anonymization script](ctp/anon.script).
- **Step 3 (Optional):** Deidentify clinical data provided in a CSV file so that the referenced patient id is anonymized the same way CTP does in Step 2.


### Usage

You can pull the Docker image from GitHub Container Registry:

```
docker pull ghcr.io/sgsfak/eucaim_anon_pipeline
```


Then you can run the pipeline using the following command, which shows the barely minimum information required to run the pipeline:

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
Usage: pipeline [OPTIONS] SITE_ID [INPUT_DIR] [OUTPUT_DIR]

╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    site_id         TEXT          The SITE-ID provided by the EUCAIM Technical team [required]                             │
│      input_dir       [INPUT_DIR]   Input directory to read DICOM files from [default: /input]                               │
│      output_dir      [OUTPUT_DIR]  Output directory to write processed DICOM files to [default: /output]                    │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --ocr                     --no-ocr                    Perform OCR (using Tesseract) and image deidentication                │
│                                                       [default: no-ocr]                                                     │
│ --paddle-ocr              --no-paddle-ocr             Perform OCR using PaddleOCR and image deidentification                │
│                                                       [default: no-paddle-ocr]                                              │
│ --threads                                    INTEGER  Number of threads that RSNA CTP and PaddleOCR (if enabled) will use   │
│                                                       [default: 10]                                                         │
│ --verbose             -v                              Enable verbose logging                                                │
│                                                       installation.                                                         │
│ --help                                                Show this message and exit.                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

* Passing `--ocr` or `--paddle-ocr` will enable the Optical Character Recognition (OCR) feature for redacting "burned-in" text in the raw images. *Please note that by default no OCR will run!* The `--ocr` will run [tesseract OCR](https://github.com/tesseract-ocr/tesseract) and the `--paddle-ocr` will run [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR). PaddleOCR seems to be more accurate than tesseract OCR but also slower and requires more resources.
* `--threads` can be used to specify the number of threads that RSNA CTP and PaddleOCR (if enabled) will use and it can be used to increase the speed of the pipeline if it runs in multi-core CPU. By default, it is set to 10.

### Clinical data
In case there are additional (clinical) data for the patients for which the anonymization is performed, it is recommended to provide the data in a CSV file in the same input directory that contains the DICOM files. This is needed so that the patient ids mentioned in the CSV file are replaced with anonymized patient ids so that they are consistent with the anonymized DICOM files.

There are not specific requirements for the name of the CSV file, it can be anything, but it should have a `.csv` extension. Regarding the actual format of the CSV please keep note of the following:
* The first line of the file is assumed to be a header line containing the column names
* The first column should contain the patientID

You can see an example input CSV [here](example_clinical.csv)
