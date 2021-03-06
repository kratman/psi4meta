#! /Users/github/anaconda/envs/python3/bin/python
import glob
import subprocess as sp
from multiprocessing import Pool
import os
import time
import shutil

sp.call("bash source activate python3", shell=True)
base_path = "/Users/github/builds/"
os.chdir(base_path)

if os.path.isdir(base_path + "/psi4"):
    shutil.rmtree(base_path + "/psi4")

sp.call("/usr/bin/git clone https://github.com/psi4/psi4.git", shell=True)
os.chdir(base_path + "/psi4")

sp.call("""/Users/github/anaconda/envs/python3/bin/cmake -H. \
                         -B/Users/github/builds/psi4/objdir \
                         -DCMAKE_BUILD_TYPE=debug \
                         -DCMAKE_C_FLAGS="-coverage" \
                         -DCMAKE_CXX_FLAGS="-coverage" \
                         -DPYTHON_EXECUTABLE=/Users/github/anaconda/envs/python3/bin/python \
                         -DPYTHON_LIBRARY=/Users/github/anaconda/envs/python3/lib/libpython3.5m.dylib \
                         -DPYTHON_INCLUDE_DIR=/Users/github/anaconda/envs/python3/include/python3.5m \
                         -DLAPACK_LIBRARIES="/System/Library/Frameworks/Accelerate.framework/Accelerate" \
                         -DBLAS_LIBRARIES="/System/Library/Frameworks/Accelerate.framework/Accelerate"
""", shell=True)

os.chdir(base_path + "/psi4/objdir")
sp.call("/Users/github/Git/psi4meta/mac-psinet/macpsinet_make.py")

test_time = time.time()
os.environ["PYTHONPATH"] = base_path + "/psi4/objdir/stage/usr/local/psi4/lib/"
outfile = open(base_path + "/output_coverage", "w")

cov_path = "/Users/github/anaconda/envs/python3/bin/coverage"
cov_command = "run"
cov_mode = '--parallel-mode'
psi_path = base_path + "/psi4/objdir/stage/usr/local/psi4/bin/psi4"

os.chdir(base_path + "/psi4")
files = glob.glob('tests/*/input.dat')
#files += glob.glob('tests/*cbs*/input.dat')
files += glob.glob('tests/*/*/input.py')
files += glob.glob('tests/*/*/input.dat')

# Remove whole subsections because they take too long
files = [x for x in files if 'input.py.dat' not in x]
files = [x for x in files if 'cfour' not in x]
files = [x for x in files if '/mrcc/' not in x]
files = [x for x in files if 'dmrg' not in x]
files = [x for x in files if 'pcm' not in x]
files = [x for x in files if 'optking' not in x]
files = [x for x in files if 'sowreap' not in x]
files = [x for x in files if 'caspt2' not in x]

# Remove specific long running jobs
explicit_exclude = ['fsapt-diff1', 'fd-freq-gradient-large', 'fsapt1', 'fd-freq-energy-large',
                    'isapt1', 'scf11-freq-from-energies', 'cc5', 'opt10', 'bccd_driver',
                     'ccenergy_driver', 'gdma1', 'scf-bz2'] 
files = [x for x in files if x not in explicit_exclude]

files = list(enumerate(files))
total_files = len(files)

print("\n\n ==> Starting %d test cases <== \n" % total_files)

start_path = os.path.dirname(os.path.abspath(__file__))

failures = []
def run_test(fname):
    num, fname = fname
    fname = os.path.abspath(fname)
    path = '/'.join(fname.split('/')[:-1])
    os.chdir(path)
    fname = fname.split('/')[-1]

    if ".py" in fname:
        cmd = [cov_path, cov_command, cov_mode, fname]
    else:
        cmd = [cov_path, cov_command, cov_mode, psi_path, fname]

    t = time.time()
    ret = sp.call(cmd, stdout=outfile)
    total_time = time.time() - t
    input_name = path.split('/')[-1]
    if ret == 0:
        print("%3d/%3d Success! %25s (%8.2f seconds)" % (num, total_files, input_name, total_time))
    else:
        print("%3d/%3d Failure! %25s" % (num, total_files, input_name))
        failures.append(fname)
    os.chdir(start_path)

#map(run_test, files)
p = Pool(2, maxtasksperchild=1)
p.map(run_test, files, chunksize=1)

print("\n\n ==> Failed cases <== \n")
for name in failures:
    print(name)

print("\n\n ==> Combining Python data <== \n")

for n, f in files:
    if (n % 50) == 0:
        print("%3d/%3d files parsed" % (n, total_files))
    path = os.path.dirname(f)
    sp.call([cov_path, "combine", "--append",  path])
sp.call([cov_path, "report"])

print("\n\n ==> Uploading CodeCov data <== \n")

with open("/Users/github/.tokens/codecov", "r") as infile:
    coverage_token = infile.read().strip()

sp.call(["/Users/github/anaconda/bin/codecov",
                  "--token", coverage_token], stdout=outfile)

os.chdir(start_path)
for f in glob.glob('*.gcov'):
    os.remove(f)

outfile.close()

test_time = time.time() - test_time
print("Testing took a total of %.2f seconds." % test_time)
