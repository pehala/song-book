# File handling in Song Book

## Models

### PDFTemplate
* Represents set of configuration options that are used for generating a PDFFile
* No way of recreating exactly the same file, PDFTemplates can change and every regeneration will be based on the new configuration

#### ManualPDFTemplate
#### Category
* Category is a subclass of PDFTemplate and provides songs

### PDFFile
* Represents single file that is either generated or scheduled for generation

### NumberedSong
* Song + fixed song number, used in PDFTemplate to change order of songs in PDF

## Workflow
