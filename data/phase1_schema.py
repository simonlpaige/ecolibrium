import sqlite3
db = sqlite3.connect(r'C:\Users\simon\.openclaw\workspace\ecolibrium\data\ecolibrium_directory.db')
c = db.cursor()
new_cols = [
    ('lat', 'REAL'),
    ('lon', 'REAL'),
    ('geo_source', 'TEXT'),
    ('model_type', 'TEXT'),
    ('contact_url', 'TEXT'),
    ('tags', 'TEXT'),
    ('alignment_score', 'INTEGER'),
]
for col, typ in new_cols:
    try:
        c.execute(f'ALTER TABLE organizations ADD COLUMN {col} {typ}')
        print(f'Added: {col}')
    except Exception as e:
        print(f'Skip {col}: {e}')
db.commit()
db.close()
print('Schema migration complete')
