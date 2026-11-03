"""Make an empty, non-overwriting replay directory; never update packages."""
from pathlib import Path
import shutil,sys,re
src=Path(__file__).resolve().parents[1];dest=Path(sys.argv[1]).resolve()
if dest.exists():raise SystemExit('Destination must not already exist')
dest.mkdir(parents=True)
for n in ['code','inputs','provenance']:shutil.copytree(src/n,dest/n,ignore=shutil.ignore_patterns('__pycache__'))
for n in ['logs','data','tables','figures','checkpoints']:(dest/n).mkdir()
shutil.copytree(src/'data/seeds',dest/'data/seeds')
shutil.copy2(src/'tables/SCR_source.csv',dest/'tables/SCR_source.csv')
# Pin the source actually used, including the inherited 60 Hz default.
manifest=dest/'provenance/Manifest.toml';s=manifest.read_text()
a=s.index('[[deps.PowerDynamics]]');b=s.index('\n[[deps.',a+1)
part=s[a:b];part=re.sub(r'git-tree-sha1 = "[^"]+"','path = "PowerDynamics_used"',part)
manifest.write_text(s[:a]+part+s[b:])
print(dest)
print('Run phase 1, analyze.py, phase 2, analyze.py, audit.py, report.py in that order.')
