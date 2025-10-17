#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import traceback
from typing import List, Dict, Tuple, Optional

import pandas as pd

# Optional PDF support
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except Exception:
    HAS_PDFPLUMBER = False

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout, QComboBox, QSpinBox, QTextEdit
)

# -----------------------------------------
# Helpers: loading tables from various files
# -----------------------------------------

READABLE_EXTS = {".csv", ".xlsx", ".xls", ".html", ".htm", ".pdf"}

CITY_SYNS = ["city", "town", "municipality", "locality", "suburb"]
REGION_SYNS = ["region", "province", "county", "prefecture", "district", "zone"]
STATE_SYNS = ["state", "state/province", "state_province", "st", "state_code", "statecode", "prov", "province"]

ADDRESS_SYNS = ["address", "full address", "addr", "location", "site"]

def load_tables(path: str) -> List[pd.DataFrame]:
    """
    Load one or more tables from CSV / Excel / HTML / PDF.
    Returns a list of DataFrames. May be length 1 for CSV/Excel.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext not in READABLE_EXTS:
        raise ValueError(f"Unsupported file type: {ext}")

    if ext == ".csv":
        df = pd.read_csv(path)
        return [df]

    if ext in {".xlsx", ".xls"}:
        # Read first sheet by default; if you want all sheets, change to sheet_name=None
        return [pd.read_excel(path)]

    if ext in {".html", ".htm"}:
        dfs = pd.read_html(path)
        if not dfs:
            raise ValueError("No tables found in HTML.")
        return dfs

    if ext == ".pdf":
        if not HAS_PDFPLUMBER:
            raise RuntimeError("pdfplumber is not installed. Please `pip install pdfplumber`.")
        dfs: List[pd.DataFrame] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for t in tables or []:
                    # Convert the raw table (list of rows) into a DataFrame
                    # Use the first non-empty row as header if possible
                    rows = [r if r is not None else [] for r in t]
                    if not rows:
                        continue
                    # Heuristic: find first row that looks like a header (no None-only rows)
                    header_idx = 0
                    for i, r in enumerate(rows[:3]):  # look at first few rows
                        if any(cell not in [None, ""] for cell in r):
                            header_idx = i
                            break
                    header = [clean_header(x) for x in rows[header_idx]]
                    data_rows = rows[header_idx + 1 :]
                    df = pd.DataFrame(data_rows, columns=normalize_header_len(header, data_rows))
                    dfs.append(df)
        if not dfs:
            raise ValueError("No tables found in PDF.")
        return dfs

    raise ValueError(f"Unhandled extension: {ext}")

def clean_header(x) -> str:
    return str(x).strip() if x is not None else ""

def normalize_header_len(header: List[str], data_rows: List[List[str]]) -> List[str]:
    """
    Make sure header length matches the widest data row.
    """
    max_cols = max([len(header)] + [len(r) for r in data_rows] + [1])
    new_header = header[:]
    if len(new_header) < max_cols:
        new_header += [f"col_{i+1}" for i in range(len(new_header), max_cols)]
    elif len(new_header) > max_cols:
        new_header = new_header[:max_cols]
    # Deduplicate header names
    seen = {}
    for i, name in enumerate(new_header):
        n = name or f"col_{i+1}"
        if n in seen:
            seen[n] += 1
            n = f"{n}_{seen[n]}"
        else:
            seen[n] = 1
        new_header[i] = n
    return new_header

# -----------------------------------------
# Column mapping & light heuristics
# -----------------------------------------

def normalize_cols(df: pd.DataFrame) -> Dict[str, str]:
    """
    Return a dict of {lower_stripped_col: original_col} for case-insensitive lookup.
    """
    mapping = {}
    for c in df.columns:
        mapping[str(c).strip().lower()] = c
    return mapping

def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Find a column by synonyms (case-insensitive).
    """
    cmap = normalize_cols(df)
    for cand in candidates:
        key = cand.strip().lower()
        if key in cmap:
            return cmap[key]
    # Try loose contains (e.g., "City Name")
    for key, original in cmap.items():
        for cand in candidates:
            if cand in key:
                return original
    return None

CITY_CANDS = CITY_SYNS
REGION_CANDS = REGION_SYNS
STATE_CANDS = STATE_SYNS

def address_fallback(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    If City/State not found, try to parse from an address-like column:
    pattern: 'City, ST 12345' (US-style)
    Returns (city_col, state_col, region_col) as *synthetic* names created during extraction.
    """
    addr_col = find_col(df, ADDRESS_SYNS)
    if not addr_col:
        return (None, None, None)
    # We'll create two new columns by parsing Address
    city_vals = []
    state_vals = []
    # Very simple regex: "... City, ST 12345" or "... City, ST"
    pattern = re.compile(r"(?P<city>[^,]+),\s*(?P<state>[A-Za-z]{2})(?:\s+\d{4,6})?", re.IGNORECASE)
    for v in df[addr_col].astype(str).fillna(""):
        m = pattern.search(v)
        if m:
            city_vals.append(m.group("city").strip())
            state_vals.append(m.group("state").upper())
        else:
            city_vals.append("")
            state_vals.append("")
    df["__parsed_city"] = city_vals
    df["__parsed_state"] = state_vals
    return ("__parsed_city", "__parsed_state", None)  # region not parsed

def suggest_mappings(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Suggest columns for City / Region / State using synonyms,
    with Address fallback if needed.
    """
    city = find_col(df, CITY_CANDS)
    region = find_col(df, REGION_CANDS)
    state = find_col(df, STATE_CANDS)
    if not city or not state:
        c2, s2, _ = address_fallback(df)
        city = city or c2
        state = state or s2
    return {"City": city, "Region": region, "State": state}

# -----------------------------------------
# Extraction core
# -----------------------------------------

def extract_columns(dfs: List[pd.DataFrame], chosen_cols: List[str]) -> pd.DataFrame:
    """
    Concatenate selected columns from all tables (align by selected names).
    Missing columns are filled with empty strings.
    """
    out_frames = []
    for df in dfs:
        available = {str(c): c for c in df.columns}
        subset = {}
        for name in chosen_cols:
            # find by exact, or case-insensitive
            col = available.get(name)
            if col is None:
                # try case-insensitive
                for k, v in available.items():
                    if k.strip().lower() == name.strip().lower():
                        col = v
                        break
            if col is not None:
                subset[name] = df[col]
            else:
                subset[name] = [""] * len(df)
        out_frames.append(pd.DataFrame(subset))
    if not out_frames:
        return pd.DataFrame(columns=chosen_cols)
    return pd.concat(out_frames, ignore_index=True)

# -----------------------------------------
# GUI
# -----------------------------------------

class ExtractorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Extractor — City / Region / State")
        self.setMinimumSize(1000, 650)

        self.all_tables: List[pd.DataFrame] = []
        self.loaded_path: Optional[str] = None

        # Widgets
        main = QWidget()
        grid = QGridLayout(main)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        # File row
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select a CSV, Excel, HTML, or PDF file...")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.on_browse)
        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self.on_load)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Input file:"))
        file_row.addWidget(self.path_edit, stretch=1)
        file_row.addWidget(btn_browse)
        file_row.addWidget(btn_load)
        grid.addLayout(file_row, 0, 0, 1, 2)

        # Column chooser group
        self.grp_cols = QGroupBox("Select columns to extract")
        cols_layout = QGridLayout()
        self.grp_cols.setLayout(cols_layout)

        self.cmb_city = QComboBox()
        self.cmb_region = QComboBox()
        self.cmb_state = QComboBox()

        self.cmb_city.setEditable(False)
        self.cmb_region.setEditable(False)
        self.cmb_state.setEditable(False)

        cols_layout.addWidget(QLabel("Column-1:"), 0, 0)
        cols_layout.addWidget(self.cmb_city, 0, 1)
        cols_layout.addWidget(QLabel("Column-2"), 1, 0)
        cols_layout.addWidget(self.cmb_region, 1, 1)
        cols_layout.addWidget(QLabel("Column-3"), 2, 0)
        cols_layout.addWidget(self.cmb_state, 2, 1)

        # Other columns list
        self.lst_other = QListWidget()
        self.lst_other.setSelectionMode(self.lst_other.SelectionMode.MultiSelection)
        cols_layout.addWidget(QLabel("Additional columns (optional):"), 3, 0, 1, 2)
        cols_layout.addWidget(self.lst_other, 4, 0, 1, 2)

        grid.addWidget(self.grp_cols, 1, 0)

        # Preview + actions
        right_box = QGroupBox("Preview")
        right_layout = QVBoxLayout()
        right_box.setLayout(right_layout)

        self.table = QTableWidget()
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self.table, stretch=1)

        btn_extract = QPushButton("Extract & Preview")
        btn_extract.clicked.connect(self.on_extract)
        right_layout.addWidget(btn_extract)

        # Save row
        save_row = QHBoxLayout()
        self.save_edit = QLineEdit()
        self.save_edit.setPlaceholderText("Output CSV path (e.g., C:\\Temp\\extracted.csv)")
        btn_save_browse = QPushButton("Save As...")
        btn_save_browse.clicked.connect(self.on_save_browse)
        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self.on_export)
        save_row.addWidget(self.save_edit, stretch=1)
        save_row.addWidget(btn_save_browse)
        save_row.addWidget(btn_export)

        right_layout.addLayout(save_row)

        grid.addWidget(right_box, 1, 1)

        # Logger / status
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        grid.addWidget(self.log, 2, 0, 1, 2)

        self.setCentralWidget(main)
        self.update_columns_ui([])

        self.extracted_df: Optional[pd.DataFrame] = None

    # ---------------- UI actions ----------------

    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select input table", "", "Tables (*.csv *.xlsx *.xls *.html *.htm *.pdf);;All files (*.*)"
        )
        if path:
            self.path_edit.setText(path)

    def on_load(self):
        path = self.path_edit.text().strip()
        if not path:
            self.msg("Please select a file first.")
            return
        if not os.path.exists(path):
            self.msg(f"File does not exist: {path}")
            return
        try:
            self.log_info(f"Loading tables from {path} ...")
            self.all_tables = load_tables(path)
            self.loaded_path = path
            self.log_info(f"Loaded {len(self.all_tables)} table(s).")
            # Build a combined column set
            all_cols = []
            for df in self.all_tables:
                all_cols.extend([str(c) for c in df.columns])
            unique_cols = sorted(list(dict.fromkeys(all_cols)))
            self.update_columns_ui(unique_cols)
            # Suggest mappings based on first table with any columns
            if self.all_tables:
                sug = suggest_mappings(self.all_tables[0].copy())
                self.set_combo_selection(self.cmb_city, sug.get("City"))
                self.set_combo_selection(self.cmb_region, sug.get("Region"))
                self.set_combo_selection(self.cmb_state, sug.get("State"))
            self.log_info("Ready. Pick columns and click 'Extract & Preview'.")
        except Exception as e:
            self.error_box("Load Error", f"{e}\n\n{traceback.format_exc()}")

    def on_extract(self):
        if not self.all_tables:
            self.msg("Please load a file first.")
            return

        chosen = []
        city_col = self.cmb_city.currentText().strip()
        region_col = self.cmb_region.currentText().strip()
        state_col = self.cmb_state.currentText().strip()

        # Only add if they chose something (non-empty)
        if city_col:
            chosen.append(city_col)
        if region_col:
            chosen.append(region_col)
        if state_col:
            chosen.append(state_col)

        # Add other selected columns
        for i in range(self.lst_other.count()):
            item = self.lst_other.item(i)
            if item.isSelected():
                colname = item.text()
                if colname not in chosen:
                    chosen.append(colname)

        if not chosen:
            self.msg("Please choose at least one column to extract.")
            return

        try:
            self.log_info(f"Extracting columns: {', '.join(chosen)}")
            df = extract_columns(self.all_tables, chosen)
            self.extracted_df = df
            self.populate_preview(df.head(50))
            self.log_info(f"Extracted {len(df)} rows.")
        except Exception as e:
            self.error_box("Extraction Error", f"{e}\n\n{traceback.format_exc()}")

    def on_save_browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV files (*.csv);;All files (*.*)"
        )
        if path:
            # Ensure .csv
            if not path.lower().endswith(".csv"):
                path += ".csv"
            self.save_edit.setText(path)

    def on_export(self):
        if self.extracted_df is None or self.extracted_df.empty:
            self.msg("Nothing to export. Please run 'Extract & Preview' first.")
            return
        out_path = self.save_edit.text().strip()
        if not out_path:
            self.msg("Please choose an output CSV path.")
            return
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            self.extracted_df.to_csv(out_path, index=False)
            self.log_info(f"Exported CSV to: {out_path}")
            QMessageBox.information(self, "Done", f"Exported CSV to:\n{out_path}")
        except Exception as e:
            self.error_box("Export Error", f"{e}\n\n{traceback.format_exc()}")

    # ---------------- UI helpers ----------------

    def update_columns_ui(self, columns: List[str]):
        # Fill combos & list
        def fill(combo: QComboBox):
            combo.clear()
            combo.addItem("")  # allow 'none'
            for c in columns:
                combo.addItem(c)

        fill(self.cmb_city)
        fill(self.cmb_region)
        fill(self.cmb_state)

        self.lst_other.clear()
        for c in columns:
            item = QListWidgetItem(c)
            self.lst_other.addItem(item)

    def set_combo_selection(self, combo: QComboBox, value: Optional[str]):
        if not value:
            combo.setCurrentIndex(0)
            return
        idx = combo.findText(value, Qt.MatchFlag.MatchFixedString)
        if idx < 0:
            # Try case-insensitive
            for i in range(combo.count()):
                if combo.itemText(i).strip().lower() == str(value).strip().lower():
                    idx = i
                    break
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def populate_preview(self, df: pd.DataFrame):
        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for r in range(len(df)):
            for c in range(len(df.columns)):
                val = df.iat[r, c]
                self.table.setItem(r, c, QTableWidgetItem("" if pd.isna(val) else str(val)))

        self.table.resizeColumnsToContents()

    def msg(self, text: str):
        QMessageBox.information(self, "Info", text)

    def error_box(self, title: str, text: str):
        QMessageBox.critical(self, title, text)
        self.log_error(text)

    def log_info(self, text: str):
        self.log.append(f"✅ {text}")

    def log_error(self, text: str):
        self.log.append(f"<span style='color:#ff5555'>❌ {text}</span>")

# -----------------------------------------
# Main
# -----------------------------------------

def main():
    app = QApplication(sys.argv)
    w = ExtractorWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
