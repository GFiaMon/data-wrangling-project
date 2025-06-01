# mietspiegel_cleaner.py
import pandas as pd
import numpy as np

def load_pdf(pdf_path, area=[150, 50, 750, 700], pages=1):
    """Load PDF table using Tabula"""
    import tabula
    dfs = tabula.read_pdf(
        pdf_path,
        pages=pages,
        area=area,
        lattice=False,
        stream=True,
        pandas_options={'header': None}
    )
    return dfs[0]  # Assuming first table is always the target

def prefilter_rows(df, rows_to_drop):
    """Remove initial header rows (safely)"""
    valid_rows = df.index.intersection(rows_to_drop)
    return df.drop(index=valid_rows).reset_index(drop=True)

def split_code_quality(df):
    """Extract quality codes (A-L) and quality labels"""
    # Extract code and quality
    df[['Quality_raw', 'Code']] = df.iloc[:, 0].str.extract(r'(.+)\s([A-L])$')
    
    # Get last meaningful quality word
    df['Quality'] = df['Quality_raw'].apply(
        lambda x: next((w for w in reversed(str(x).split()) if len(w) > 1), None)
    )
    
    # Clean up
    return df.drop(columns=['Quality_raw', df.columns[0]])

def split_numeric_columns(df, split_col_idx=2, pattern1_rows=[0,1,4,7]):
    """Split columns with numeric ranges"""
    col_to_split = df.columns[split_col_idx]
    
    # Pattern handling
    mask = df.index.isin(pattern1_rows)
    
    # Temporary columns
    df["_temp1"], df["_temp2"] = np.nan, np.nan
    
    # Split logic
    df.loc[mask, "_temp1"] = df.loc[mask, col_to_split].str.split().str[0]
    df.loc[mask, "_temp2"] = df.loc[mask, col_to_split].str.split().str[1]
    
    df.loc[~mask, "_temp1"] = df.loc[~mask, col_to_split].str.split().str[0]
    df.loc[~mask, "_temp2"] = df.loc[~mask, col_to_split].str.split().str[-1]
    
    # Insert and clean
    df.insert(split_col_idx+1, "temp1", df.pop("_temp1"))
    df.insert(split_col_idx+2, "temp2", df.pop("_temp2"))
    return df.drop(columns=[col_to_split])

def clean_numeric_columns(df, start_col=3):
    """Clean remaining numeric columns"""
    for col in df.columns[start_col:]:
        df[col] = (
            df[col]
            .astype(str)
            .str.extract(r'^(\d+,\d{2})', expand=False)
            .str.replace(',', '.')
            .astype(float)
        )
    return df

def standardize_columns(df):
    """Final column naming/ordering"""
    df.columns = ['Code', 'Quality'] + [str(i) for i in range(1, len(df.columns)-1)]
    return df

def full_pipeline(pdf_path, config):
    """Run complete cleaning process"""
    df = load_pdf(
        pdf_path,
        area=config.get('area'),
        table_index=config.get('table_index', 0)  # <-- New
    )
    df = prefilter_rows(df, rows_to_drop=config.get('rows_to_drop', []))
    df = split_code_quality(df)
    df = split_numeric_columns(df, 
        split_col_idx=config.get('split_col_idx', 2),
        pattern1_rows=config.get('pattern1_rows', []))
    df = clean_numeric_columns(df, start_col=config.get('numeric_start_col', 3))
    df = standardize_columns(df)
    return df