# File handling in Song Book

## Models

### PDFTemplate
* Represents set of configuration options that are used for generating a PDFFile
* Can be regenerated

#### ManualPDFTemplate
* User created template for creating PDFFiles
* Schedule manually
* Songs need to be configured manually
* Each song carries the title of its section (`PDFSong.section`, empty for none); a run of songs with one title,
  in the order of their numbers, is a section, so the numbers run through all of them. The page that orders the songs
  has a heading row for each section: dragging a heading moves where the section starts, and the page writes the
  title of the heading above a song into the song when it is sent. The song selection can start the sections off
  by category, a song under the first category it is in. A section has to be in one piece: the page refuses an
  order in which a title comes back after another section

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

### Generating now
A scheduled file can be generated at once from the file list, the template list or the category list ("Generate now",
`generate_file_now`). Its `scheduled_at` becomes now and a second job is queued; the original job stays queued, and
`generate_pdf_job` only runs a file that is still `SCHEDULED`, so whichever job comes first generates it and the other
one skips it.

### Manual
Create Template -> Generate File
Existing Template (Including Categories) -> Generate File
