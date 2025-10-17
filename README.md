How to use

Save the script as table_extractor_gui.py.

Install requirements (see above).

Run it:

python table_extractor_gui.py


Click Browse… → select your table file.

The app will suggest mappings for City/Region/State (you can change them).

(Optional) Select additional columns to include.

Click Extract & Preview to see the result.

Choose Save As… and hit Export CSV.

Notes & options

PDFs: Works best on clearly structured tables. If your PDFs are scans/photos, you’ll need OCR-based extraction—happy to add that with ocrmypdf/camelot if you want.

Address-only data: If your table lacks City/State columns but has an Address column like "Boston, MA 02110", the app will parse basic city/state pairs and create them on the fly.

Custom fields: The right panel lets you include any other columns in the export.