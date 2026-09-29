"""Portable cleaning/validation rules from the supplied M4.ipynb.

The complete M4 workbook is optional until supplied. Missing M4 fields are
reported as warnings when validating the bundled M2/M3 workbook.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RULES = json.loads(Path(__file__).with_name('notebook_rules.json').read_text())
M4_SOURCE = ROOT / 'data/raw/FranchiseOps_AI_4_Combined_Dataset.xlsx'
FALLBACK = ROOT / 'data/raw/FranchiseOps_AI_Milestone2_Milestone3_Combined_Dataset.xlsx'


def clean_and_validate(source, require_m4=True):
    data = pd.read_excel(source)
    checks = []
    def check(name, ok, detail, warning=False):
        checks.append(dict(Check='M4 notebook: ' + name,
                           Status='Passed' if ok else ('Warning' if warning else 'Failed'),
                           Evidence=str(detail)))
    check('nonempty dataset', not data.empty, f'{len(data)} rows')
    missing = sorted(set(RULES['REQUIRED_COLUMNS']) - set(data.columns))
    check('required columns', not missing, 'Missing: ' + ', '.join(missing) if missing else 'All present', not require_m4)
    check('source workbook', require_m4, Path(source).name + ('; complete M4 workbook was not supplied' if not require_m4 else ''), True)
    for col in ['Outlet_ID', 'SKU_ID', 'Campaign_ID']:
        if col in data:
            data[col] = data[col].astype('string').str.strip().replace({'': pd.NA, 'nan': pd.NA, 'None': pd.NA})
            check(col + ' complete', data[col].notna().all(), f'{data[col].isna().sum()} missing identifiers')
    if 'Month' in data:
        data['Month'] = pd.to_datetime(data['Month'], errors='coerce')
        check('valid months', data.Month.notna().all(), f'{data.Month.isna().sum()} invalid months')
    else:
        check('valid months', False, 'Month column missing')
    repairs = 0
    numeric = set(data.select_dtypes(include=np.number).columns) | (set(RULES['NUMERIC_COLUMNS']) & set(data.columns))
    for col in numeric:
        values = pd.to_numeric(data[col], errors='coerce').replace([np.inf, -np.inf], np.nan)
        repairs += int(values.isna().sum())
        data[col] = values.fillna(values.median())
    for col in RULES['PERCENTAGE_COLUMNS']:
        if col in data:
            values = data[col]
            invalid = ~values.between(0, 100)
            repairs += int(invalid.sum())
            data.loc[invalid, col] = values[values.between(0, 100)].median()
            check(col + ' range', data[col].between(0, 100).all(), '0–100; invalid values use the valid median')
    duplicates = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()
    check('duplicate cleanup', not data.duplicated().any(), f'{duplicates} exact duplicates removed')
    check('missing values', not data.isna().any().any(), f'{int(data.isna().sum().sum())} remaining; {repairs} numeric repairs')
    for col in RULES['NON_NEGATIVE_COLUMNS']:
        if col in data:
            check(col + ' nonnegative', data[col].ge(0).all(), f'{int(data[col].lt(0).sum())} negative values')
    # Notebook dimensions describe its particular source, not a universal schema.
    check('reference dimensions', data.shape == (30120, 66), f'Actual {data.shape}; notebook reference (30120, 66)', True)
    return data, checks


def prepare_notebook_data():
    source = M4_SOURCE if M4_SOURCE.exists() else FALLBACK
    data, checks = clean_and_validate(source, require_m4=M4_SOURCE.exists())
    output = ROOT / 'data/processed'
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(output / 'm4_data_quality.csv', index=False)
    failed = [r['Check'] for r in checks if r['Status'] == 'Failed']
    if failed:
        raise ValueError('; '.join(failed))
    data.to_csv(output / 'm4_clean_data.csv', index=False)
    return checks


if __name__ == '__main__':
    for row in prepare_notebook_data():
        print(row)
