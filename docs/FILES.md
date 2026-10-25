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

#### AllSongsTemplate
* One per tenant, created with the defaults of the form the first time the category list is opened
* Prints every non-archived song of the tenant, numbered like the all songs list
* With `category_sections` it prints one section per category instead, in the order the categories were created. A
  song is printed once, in the first category it is in; the songs are numbered one after another through the
  sections, in the order of each category's list, so the numbers no longer match the all songs list
* Scheduled automatically while the tenant has the all songs list (`Tenant.all_songs_category`), but can be manually triggered
* Edited on its own row of the category list, which has no URL slug and cannot be deleted

### PDFFile
* Represents single file that is either generated or scheduled for generation
* No way of recreating the exact configuration that led to this File

## Workflow

### Automated
* Create Category -> Schedule PDF generation, if it is enabled
* Song updated -> [Schedule PDF generation for every Category the song is in, if it is enabled]
* Song updated -> [Schedule PDF generation of the all songs PDF of the song's tenants, if it is enabled]

### Manual
Create Template -> Generate File
Existing Template (Including Categories) -> Generate File
