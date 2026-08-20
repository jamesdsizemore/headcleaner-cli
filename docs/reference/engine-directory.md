# Engine directory

This page is the per-engine reference for headcleaner. For every engine headcleaner ships, it explains what the engine does, who needs it, how to install it, how headcleaner decides to use it, what the user sees when the engine is missing, and how to recover from common failures.

The engines are listed in the order they appear in headcleaner's routing table. Each entry covers the same set of facts so you can compare them.

## Office documents

### `officecli`

**What it checks:** extracts structured content from `.docx`, `.xlsx`, and `.pptx` files using the OfficeCLI binary. OfficeCLI returns the document's text, headings, tables, and embedded media as a structured payload that headcleaner normalizes into Markdown and OKF.

**Who needs it:** anyone converting Microsoft Office documents in the modern XML-based formats. This is the most-used engine in a typical headcleaner run.

**Install:** `npm install -g @officecli/officecli`. Confirm with `officecli --version`.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.docx`, `.xlsx`, or `.pptx` and OfficeCLI is on `PATH`. If OfficeCLI is missing, the file is converted via the `all2md` fallback if it is installed, otherwise it is skipped with a clear message.

**Missing-engine experience:** the file appears in the report as `skipped` with a message naming OfficeCLI as the required tool. Installing OfficeCLI and re-running picks the file up automatically.

**Common failure recovery:** the most common failure is a version mismatch between OfficeCLI and headcleaner. Reinstall OfficeCLI to get the version headcleaner was tested against. The second most common is a corrupted Office file; the failure message will name the file and the parser error.

### `libreoffice`

**What it checks:** upgrades legacy Office formats (`.doc`, `.xls`, `.ppt`) into the modern XML-based formats so the `officecli` engine can read them. LibreOffice is invoked headless to convert a legacy file into a `.docx`, `.xlsx`, or `.pptx`, which then flows through the normal pipeline.

**Who needs it:** anyone with legacy Office documents in their input folder. Modern Office files do not need LibreOffice.

**Install:** download from [libreoffice.org](https://www.libreoffice.org/) or use your operating system's package manager. On macOS with Homebrew: `brew install --cask libreoffice`. On Ubuntu: `sudo apt install libreoffice`. On Windows: download the installer.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.doc`, `.xls`, or `.ppt`. The conversion is invoked with a timeout and a temporary working directory; the result is consumed by `officecli`.

**Missing-engine experience:** the file is skipped with a message naming LibreOffice as the required tool. The user must install LibreOffice and re-run.

**Common failure recovery:** the most common failure is LibreOffice taking too long on a complex file. The default timeout is generous; if you hit it on a recurring basis, the timeout can be adjusted in your policy file.

## PDFs

### `pdfplumber`

**What it checks:** extracts text, tables, and metadata from `.pdf` files. For text-native PDFs, the extraction is direct and lossless. For image-only PDFs, pdfplumber reports no text and headcleaner falls back to OCR if it is enabled.

**Who needs it:** anyone converting PDF files. Pdfplumber is a required Python dependency and is always installed when headcleaner is installed.

**Install:** installed automatically by `uv sync`. No separate step.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.pdf` and no specific engine was requested.

**Missing-engine experience:** pdfplumber is always installed; this engine should never produce a `skipped` status because of a missing dependency.

**Common failure recovery:** the most common failure is an encrypted or password-protected PDF. Pdfplumber will refuse to extract content from such files; headcleaner surfaces this as a `failed` status with a clear error. Decrypt the file before running headcleaner on it.

### `tesseract` (OCR)

**What it checks:** runs optical character recognition on image-only pages of scanned PDFs. Tesseract is invoked with a configurable profile (`fast`, `balanced`, `archival`) and a configurable set of language codes.

**Who needs it:** anyone converting scanned PDFs or image-only documents that contain no embedded text. Text-native PDFs do not need Tesseract.

**Install:** install Tesseract from [github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) or through your operating system's package manager. On macOS with Homebrew: `brew install tesseract`. On Ubuntu: `sudo apt install tesseract-ocr`. On Windows: download the installer.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.pdf`, the PDF is image-only, and OCR was explicitly enabled with `--ocr`. Without `--ocr`, image-only PDFs are skipped with a message pointing at the missing flag.

**Missing-engine experience:** the file is skipped with a message pointing at Tesseract and the `--ocr` flag. Installing Tesseract and re-running with `--ocr` picks the file up automatically.

**Common failure recovery:** the most common failure is requesting a language pack that is not installed. The run fails before any document processing begins with a clear doctor code pointing at the missing language. Install the language pack and re-run.

## HTML and plain text

### `beautifulsoup` (HTML)

**What it checks:** parses `.html` and `.htm` files using BeautifulSoup and converts them to Markdown with `markdownify`. Inline formatting, links, and basic structure are preserved; scripts and styles are stripped.

**Who needs it:** anyone converting HTML files. BeautifulSoup and markdownify are required Python dependencies and are always installed.

**Install:** installed automatically by `uv sync`. No separate step.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.html` or `.htm`.

**Missing-engine experience:** never. The engine is always available.

**Common failure recovery:** the most common failure is malformed HTML. BeautifulSoup is permissive; if a file fails to parse, the error message will name the parser error. Most malformed HTML files still convert successfully, just with some structure lost.

### `txt` (plain text)

**What it checks:** reads `.txt` files and wraps them in the OKF frontmatter with the file content as the body. Encoding detection uses `chardet`.

**Who needs it:** anyone converting plain text files.

**Install:** installed automatically by `uv sync`. No separate step.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.txt` and no other engine has higher priority.

**Missing-engine experience:** never. The engine is always available.

**Common failure recovery:** the most common failure is a non-text file misidentified as `.txt`. Headcleaner's chardet-based detection will report a low confidence; the file may still be converted but the body content may be garbled. Renaming the file to its actual extension is the right fix.

## Email and personal archives

### `eml`

**What it checks:** parses RFC 822 email messages. Extracts headers (From, To, Subject, Date), the body (text and HTML), and the attachment list. Attachments are recursively processed through the regular adapter pipeline.

**Who needs it:** anyone converting `.eml` files.

**Install:** no external dependencies; the engine is built in.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.eml`.

**Missing-engine experience:** never. The engine is always available.

**Common failure recovery:** the most common failure is a malformed message. The error message will name the parser error; most malformed messages still convert with some headers lost.

### `msg`

**What it checks:** parses Microsoft Outlook `.msg` files using `extract-msg`. Extracts the same fields as the `eml` engine plus Outlook-specific metadata.

**Who needs it:** anyone converting Outlook `.msg` files.

**Install:** `extract-msg` is installed automatically by `uv sync`.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.msg`.

**Missing-engine experience:** never. The engine is always available.

**Common failure recovery:** the most common failure is a corrupted `.msg` file. The parser will report the corruption; the message body may be partial.

### `pst`

**What it checks:** extracts individual messages from Microsoft Outlook `.pst` archives using `readpst`, then processes each message as if it were a standalone `.eml` file.

**Who needs it:** anyone converting Outlook `.pst` archives.

**Install:** install `readpst` from the `libpff` package on Linux (e.g. `sudo apt install pst-utils`), from Homebrew on macOS (`brew install libpff`), or from MSYS2 on Windows. Confirm with `readpst -h`.

**How headcleaner decides to use it:** the engine is selected when the file extension is `.pst`.

**Missing-engine experience:** the file is skipped with a message pointing at `readpst`. Install `readpst` and re-run.

**Common failure recovery:** the most common failure is an encrypted or password-protected `.pst` archive. `readpst` cannot read encrypted archives without the password; headcleaner surfaces this as a `failed` status with a clear error. Decrypt the archive with Outlook before running headcleaner on it.

## Where to read next

The [CLI reference](cli-reference.md) shows how to pass engine-specific flags like `--ocr` and `--ocr-lang`. The [tutorial on PDF and OCR](../tutorials/pdf-and-ocr.md) walks through a realistic PDF-and-OCR workflow. The [tutorial on email and attachments](../tutorials/email-and-attachments.md) walks through `.eml`, `.msg`, and `.pst` workflows.