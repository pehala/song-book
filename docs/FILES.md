# File handling in Song Book

## Models

### PDFTemplate
* Represents set of configuration options that are used for generating a PDFFile
* Can be regenerated

#### ManualPDFTemplate
* User created template for creating PDFFiles
* Schedule manually
* Songs need to be configured manually

#### Category
* Category is a subclass of PDFTemplate.
* When generating PDF from Category, songs will be taken from the Category itself
* Scheduled automatically. but can be manually triggered

### PDFFile
* Represents single file that is either generated or scheduled for generation
* No way of recreating the exact configuration that led to this File

## Workflow

### Automated
* Create Category -> Schedule PDF generation, if it is enabled
* Song updated -> [Schedule PDF generation for every Category the song is in, if it is enabled]

### Manual
Create Template -> Generate File
Existing Template (Including Categories) -> Generate File
