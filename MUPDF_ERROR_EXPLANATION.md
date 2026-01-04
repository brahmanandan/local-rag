# MuPDF Error Explanation

## Where the Error Comes From

The error **"MuPDF error: syntax error: expected object number"** originates from the **MuPDF library** (the underlying C library that PyMuPDF wraps).

### Error Source Chain

```
Corrupted PDF File
    ↓
PyMuPDF (Python library) - fitz.open()
    ↓
MuPDF (C library) - PDF parser
    ↓
ERROR: "syntax error: expected object number"
```

## Where It Happens in the Code

The error occurs in **two places** in `main.py`:

### 1. In `is_pdf_corrupted()` function (Line 82)

```python
def is_pdf_corrupted(file_path):
    """Check if a PDF file is corrupted by trying to open it with PyMuPDF."""
    try:
        doc = fitz.open(file_path)  # ← ERROR OCCURS HERE
        page_count = len(doc)
        doc.close()
        return page_count == 0
    except (fitz.FileDataError, fitz.FileNotFoundError, RuntimeError, ValueError, SyntaxError) as e:
        # This catches the MuPDF syntax error
        logger.warning(f"PDF appears corrupted (syntax/format error): {file_path} - {e}")
        return True
```

**What happens:**
- The code tries to open the PDF with `fitz.open(file_path)`
- If the PDF is corrupted, MuPDF throws a syntax error
- The error is caught and the function returns `True` (PDF is corrupted)

### 2. In `PyMuPDFLoader().load()` (Line 136)

```python
if file.lower().endswith(".pdf"):
    # Check if PDF is corrupted before trying to load
    if is_pdf_corrupted(path):
        logger.warning(f"Skipping corrupted PDF: {path}")
        continue
        
    try:
        docs += PyMuPDFLoader(path).load()  # ← ERROR CAN ALSO OCCUR HERE
    except Exception as e:
        logger.error(f"Error loading PDF {path}: {e}")
        continue
```

**What happens:**
- Even after the corruption check, `PyMuPDFLoader` might still encounter the error
- This happens if the PDF passes the initial check but fails during actual text extraction
- The error is caught and logged, then the code continues with the next file

## Why This Error Occurs

The error **"syntax error: expected object number"** means:

1. **PDF Structure Corruption**: The PDF file's internal structure is broken
   - Missing or malformed object references
   - Corrupted cross-reference table
   - Invalid object numbers

2. **Common Causes:**
   - File transfer errors (incomplete downloads)
   - Disk corruption
   - Software bugs during PDF creation
   - File system errors
   - Incomplete file saves

## How It's Handled

The code handles this error in **multiple layers**:

### Layer 1: Pre-check (is_pdf_corrupted)
```python
if is_pdf_corrupted(path):
    logger.warning(f"Skipping corrupted PDF: {path}")
    continue  # Skip before trying to load
```

### Layer 2: Try-catch during loading
```python
try:
    docs += PyMuPDFLoader(path).load()
except Exception as e:
    logger.error(f"Error loading PDF {path}: {e}")
    continue  # Skip and continue with next file
```

### Layer 3: Exception handling in is_pdf_corrupted
```python
except (fitz.FileDataError, fitz.FileNotFoundError, RuntimeError, ValueError, SyntaxError) as e:
    # Catches MuPDF syntax errors
    logger.warning(f"PDF appears corrupted (syntax/format error): {file_path} - {e}")
    return True
```

## What You See in the Logs

When this error occurs, you'll see:

```
WARNING:__main__:PDF appears corrupted (syntax/format error): ./path/to/file.pdf - MuPDF error: syntax error: expected object number
WARNING:__main__:Skipping corrupted PDF: ./path/to/file.pdf
```

Or if it happens during loading:

```
ERROR:__main__:Error loading PDF ./path/to/file.pdf: MuPDF error: syntax error: expected object number
```

## Is This a Problem?

**No, this is handled automatically!**

- ✅ Corrupted PDFs are automatically detected and skipped
- ✅ Indexing continues with all other valid PDFs
- ✅ You'll see warnings but the process won't crash
- ✅ The system processes all valid documents successfully

## How to Fix Corrupted PDFs

If you want to include a corrupted PDF:

1. **Try opening it in a PDF viewer** (Adobe Reader, Preview, etc.)
2. **Re-save or export** it as a new PDF
3. **Use a PDF repair tool** (online or desktop)
4. **Re-download** the file if it came from the internet
5. **Remove the file** if it's not critical

## Technical Details

### MuPDF Library
- **MuPDF** is a lightweight PDF rendering library written in C
- **PyMuPDF** (fitz) is the Python binding for MuPDF
- The error comes from MuPDF's PDF parser when it encounters invalid PDF structure

### Error Types Caught
- `fitz.FileDataError` - General file data errors
- `fitz.FileNotFoundError` - File not found
- `RuntimeError` - Runtime errors from MuPDF
- `ValueError` - Invalid values
- `SyntaxError` - Syntax errors (like "expected object number")
- Generic `Exception` - Any other unexpected errors

## Summary

**Error Source:** MuPDF C library (via PyMuPDF/fitz)  
**Location:** `main.py` lines 82 and 136  
**Handling:** Automatically caught and skipped  
**Impact:** None - corrupted PDFs are skipped, valid ones are processed  
**Action Required:** None - the system handles it automatically

The error is **expected behavior** when encountering corrupted PDFs and is **fully handled** by the code.

