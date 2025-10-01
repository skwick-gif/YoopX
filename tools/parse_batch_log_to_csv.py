import re
from pathlib import Path
import csv

log_path = Path('tools/batch_run_20250928T121951Z.log')
out_path = Path('tools/batch_run_20250928T121951Z_summary.csv')
text = log_path.read_text(encoding='utf-8')
lines = text.splitlines()

start_re = re.compile(r'^(?P<ts>\S+)\s+START\s+(?P<ticker>.+?)\s+\(')
end_re = re.compile(r'^END\s+(?P<ticker>.+?)\s+summary:\s+rows=(?P<rows>\d+)\s+merged=(?P<merged>\w+)')
date_from_re = re.compile(r'date_from=(?P<date>\S+)')
yahoo_rows_re = re.compile(r'yahoo rows=(?P<rows>\d+)')
fetched_re = re.compile(r'fetched_rows=(?P<fetched>\d+)\s+provider=(?P<provider>\w+)')
wrote_tmp_re = re.compile(r'wrote tmp csv (?P<path>\S+)')

records = []
current = None
for ln in lines:
    ln = ln.strip()
    if not ln:
        continue
    m = start_re.match(ln)
    if m:
        # begin new block
        current = {
            'ticker': m.group('ticker'),
            'start_ts': m.group('ts'),
            'date_from': None,
            'provider': None,
            'yahoo_rows': None,
            'fetched_rows': None,
            'tmp_csv': None,
            'end_rows': None,
            'merged': None,
        }
        continue
    if current is None:
        continue
    m = date_from_re.search(ln)
    if m:
        current['date_from'] = m.group('date')
        continue
    m = yahoo_rows_re.search(ln)
    if m:
        current['yahoo_rows'] = int(m.group('rows'))
        # if provider not set, assume yahoo
        if not current['provider']:
            current['provider'] = 'yahoo'
        continue
    m = fetched_re.search(ln)
    if m:
        current['fetched_rows'] = int(m.group('fetched'))
        current['provider'] = m.group('provider')
        continue
    m = wrote_tmp_re.search(ln)
    if m:
        current['tmp_csv'] = m.group('path')
        continue
    m = end_re.match(ln)
    if m:
        # finalize
        current['end_rows'] = int(m.group('rows'))
        merged_val = m.group('merged')
        current['merged'] = True if merged_val.lower() == 'true' else False
        # prefer fetched_rows if present, else yahoo_rows, else end_rows
        records.append(current)
        current = None

# Write CSV
with out_path.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['ticker','start_ts','date_from','provider','end_rows','fetched_rows','yahoo_rows','tmp_csv','merged'])
    for r in records:
        writer.writerow([
            r.get('ticker'),
            r.get('start_ts'),
            r.get('date_from'),
            r.get('provider'),
            r.get('end_rows'),
            r.get('fetched_rows'),
            r.get('yahoo_rows'),
            r.get('tmp_csv'),
            r.get('merged'),
        ])

# Print short summary
total = len(records)
small = sum(1 for r in records if (r.get('end_rows') or 0) < 10)
not_merged = sum(1 for r in records if not r.get('merged'))
print(f'Parsed {total} ticker blocks. {small} had <10 rows. {not_merged} had merged=False. Wrote CSV to {out_path}')
