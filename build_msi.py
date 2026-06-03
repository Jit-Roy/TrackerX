from pathlib import Path
import msilib
from msilib import schema

PRODUCT_NAME = 'TrackerX'
PRODUCT_VERSION = '0.1.0'
COMPANY_NAME = 'TrackerX'

exe_path = Path('dist/TrackerX.exe')
if not exe_path.exists():
    raise FileNotFoundError(f"Executable not found: {exe_path}")

msi_path = Path('dist/TrackerX.msi')

product_code = msilib.gen_uuid()
package_code = msilib.gen_uuid()

# Create MSI database
db = msilib.init_database(
    str(msi_path),
    schema,
    ProductName=PRODUCT_NAME,
    ProductCode=product_code,
    ProductVersion=PRODUCT_VERSION,
    Manufacturer=COMPANY_NAME,
    UpgradeCode=msilib.gen_uuid(),
)
msilib.add_tables(db, schema)

# Directory hierarchy
root = msilib.Directory(db, 'TARGETDIR', 'SourceDir')
program_files = root.add_directory('ProgramFilesFolder', 'ProgramFilesFolder')
app_dir = program_files.add_directory('TrackerXDir', PRODUCT_NAME)

# Feature and component
msilib.add_data(db, 'Feature', [
    ('Complete', 'Complete installation', 'Everything', 1, 1, 1),
])
component = app_dir.add_component('TrackerXComponent', str(exe_path), 0)
component.add_file(str(exe_path), 'TrackerX.exe')

# Shortcut in Start Menu
msilib.add_data(db, 'Directory', [
    ('ProgramMenuFolder', 'ProgramMenuFolder', 'TARGETDIR'),
    ('TrackerXStartMenuDir', 'TrackerX', 'ProgramMenuFolder'),
])
msilib.add_data(db, 'Shortcut', [
    (
        'StartMenuShortcut',
        'Complete',
        'TrackerXStartMenuDir',
        'TrackerX',
        'TrackerX.exe',
        None,
        None,
        None,
        None,
        0,
        0,
        None,
        None,
        None,
    ),
])

# Summary information
summary = msilib.SummaryInformation(db)
summary.set_property(msilib.SI_TITLE, PRODUCT_NAME)
summary.set_property(msilib.SI_SUBJECT, PRODUCT_NAME)
summary.set_property(msilib.SI_AUTHOR, COMPANY_NAME)
summary.set_property(msilib.SI_REVNUMBER, PRODUCT_VERSION)
summary.set_property(msilib.SI_TEMPLATE, template=0x00000000)
summary.write()

# Commit database
msilib.add_data(db, 'Binary', [('Icon', str(exe_path))])
msilib.commit(db)
print('Created', msi_path.resolve())
