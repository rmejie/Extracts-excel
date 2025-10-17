🏙️ Table Extractor GUI
Extract City, Region, and State columns from any table (CSV / Excel / HTML / PDF) with a simple PyQt6 GUI
📘 Overview

Table Extractor GUI is a desktop application built using Python + PyQt6 that allows users to:

Load tabular data from CSV, Excel, HTML, or PDF files

Automatically detect columns such as City, Region, and State

Optionally include additional columns in the export

Extract and preview data before exporting

Export results to a clean CSV file

It’s perfect for analysts, researchers, and admins who frequently need to extract location-related columns from large datasets.

🖼️ Features

✅ Supports multiple file formats:

.csv

.xlsx / .xls

.html / .htm

.pdf (via pdfplumber)

✅ Intelligent auto-detection:

Detects common column names and synonyms for City, Region, and State

Parses address strings like "Boston, MA 02110" if no direct City/State columns exist

✅ User control:

Pick exactly which columns to extract

Add optional extra columns

Preview before export

✅ Output:

Save extracted data as .csv

Automatically generates log messages for every action


🧮 Usage Guide

Launch the app
Run TableExtractor.exe or python table_extractor_gui.py.

Select an input file
Click Browse... and choose a CSV, Excel, HTML, or PDF file.

Load the table
Press Load. The app detects available columns and suggests mappings for City, Region, and State.

Select columns
You can adjust the detected columns and add optional columns from the list.

Extract & Preview
Click Extract & Preview to view a preview of the extracted data.

Export CSV

Click Save As… to choose an output location.

Click Export CSV to save the results.

🧠 Intelligent Features

Synonym detection:
Automatically detects column names like Town, Province, ST, or State Code.

Address parsing fallback:
If no City/State columns are present, it uses regex patterns to extract from address fields like "Seattle, WA 98109".

Multi-table handling:
For files with multiple tables (HTML/PDF), all detected tables are concatenated into one dataset.

Preview limit:
Shows the first 50 rows for quick inspection.

🧾 Sample Data

assets/sample_data.csv

Name,City,Region,State
John Doe,New York,Northeast,NY
Jane Smith,Los Angeles,West,CA
Carlos Ruiz,Houston,South,TX
Anita Kapoor,Chicago,Midwest,IL


assets/sample_table.pdf
A small table PDF with the same columns above — useful for testing PDF table extraction.

🧰 Troubleshooting
Issue	Possible Cause	Solution
PDF tables not extracted	PDF is scanned/non-digital	Use a text-based PDF or enable OCR extraction (can be added with ocrmypdf)
Column not detected	Column header uses an uncommon name	Manually select from dropdown in GUI
App not starting	Missing dependencies	Run pip install -r requirements.txt
Export CSV button disabled	No data extracted yet	Click “Extract & Preview” first
🧑‍💻 Technical Details

Language: Python 3.9+

GUI Framework: PyQt6

Libraries:

pandas – table manipulation

pdfplumber – PDF extraction

openpyxl – Excel reader

lxml – HTML parsing

PyQt6 – GUI

🔒 Packaging Notes

The provided table_extractor_gui.spec includes:

Assets (icon + samples)

Hidden imports for PyQt6, pandas, pdfplumber, etc.

The final .exe has no console window.

You can add a digital signature or custom installer using Inno Setup or NSIS if deploying to end-users.

🧠 Future Enhancements (optional ideas)

🧩 Add OCR for scanned PDFs (via ocrmypdf or tesseract)

🌐 Add drag-and-drop file support

🗂️ Add batch folder extraction

💾 Add Excel export option (.xlsx)

🪄 Add auto-generated PDF demo on first launch

📄 License

This project is licensed under the MIT License — free for personal and commercial use with attribution.

🧑‍💼 Author

Ramsis Mejie


Would you like me to include the auto-generated PDF demo logic directly into table_extractor_gui.py (so that the sample PDF is created automatically if it doesn’t exist)?
That way users can just run the EXE without needing pre-bundled PDFs.