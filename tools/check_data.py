"""Read-only integrity checks for the supplied LTE course simulation cases."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    checked = 0
    for line in (ROOT / 'MANIFEST.sha256').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('File hash mismatch: ' + name)
        checked += 1
    hashes = defaultdict(list)
    for file in sorted((ROOT / 'cases').rglob('*.uod')):
        with zipfile.ZipFile(file) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise ValueError('Invalid UOD ZIP member: ' + bad)
        hashes[hashlib.sha256(file.read_bytes()).hexdigest()].append(file.relative_to(ROOT).as_posix())
    counts = {}
    for scenario in ('overlap', 'overshoot'):
        folder = ROOT / 'cases' / scenario
        raw = (folder / (scenario + '.scene')).read_bytes()
        scene = ET.fromstring(raw.rstrip(b'\x00'))
        with (folder / 'stations.csv').open(encoding='utf-8-sig', newline='') as stream:
            stations = list(csv.DictReader(stream))
        cells = scene.findall('.//CellModel')
        if len(cells) != len(stations):
            raise ValueError('Cell count mismatch: ' + scenario)
        for cell in cells:
            match = next(row for row in stations if row['小区ID'] == cell.findtext('CellID'))
            if match['PCI'] != cell.findtext('PCI') or float(match['天线角度']) != float(cell.findtext('Azimuth')):
                raise ValueError('Cell parameter mismatch: ' + scenario)
        counts[scenario] = len(cells)
    print('Raw file hashes verified:', checked)
    print('UOD ZIP containers checked:', sum(map(len, hashes.values())))
    print('Scene cell counts:', counts)
    for names in hashes.values():
        if len(names) > 1:
            print('WARNING: identical UOD files with different case/phase labels:')
            for name in names:
                print('  ' + name)
    print('Simulation and radio KPI values have not been independently reproduced.')

if __name__ == '__main__':
    main()
