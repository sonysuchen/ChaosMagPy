#!/usr/bin/env bash

# extract from __init__.py on line with __version__ the expr between ""
version=$(grep __version__ chaosmagpy/__init__.py | sed 's/.*"\(.*\)".*/\1/')
out=chaosmagpy_package_$version.zip

echo -------ChaosMagPy Version $version-------

# build distribution
python setup.py sdist bdist_wheel

# clean build and compile documentary as html
make --directory ./docs clean
make --directory ./docs html

# run example
python chaos_examples.py

# print example file output for checking
cat example1_output.txt

# make temporary directory
tempdir=$(mktemp -t -d XXXXXX)

# copy files to tmp directory
cp dist/chaosmagpy-$version.tar.gz $tempdir/
cp chaos_examples.py $tempdir/
cp example1_output.txt $tempdir/
mkdir $tempdir/data $tempdir/html
cp data/CHAOS-7.mat $tempdir/data/
cp data/SW_OPER_MAGA_LR_1B_20180801T000000_20180801T235959_PT15S.cdf $tempdir/data/SW_OPER_MAGA_LR_1B_20180801T000000_20180801T235959_PT15S.cdf
cp -r docs/build/html/* $tempdir/html/

# create readme.txt and write introduction (without citation rst link)
cat > $tempdir/readme.txt <(head -9 README.rst)

# create readme.txt and write documentation information
cat >> $tempdir/readme.txt <(tail -17 README.rst)

# create readme.txt and write introduction
cat >> $tempdir/readme.txt <(echo) CITATION

# include License
cat >> $tempdir/readme.txt <(echo) LICENSE

# include installation instructions
cat >> $tempdir/readme.txt <(echo) INSTALL.rst

# append explanations of package's contents
cat >> $tempdir/readme.txt << EOF

Contents
========

The directory contains the files/directories:

1. "chaosmagpy-x.x*.tar.gz": pip installable archive of the chaosmagpy package
   (version x.x*)

2. "chaos_examples.py": executable Python script containing several examples
   that can be run by changing the examples in line 16, save and run in the
   command line:

   >>> python chaos_examples.py

   example 1: Calculate CHAOS model field predictions from input coordinates
              and time and output simple data file
   example 2: Calculate and plot residuals between CHAOS model and
              Swarm A data (from L1b MAG cdf data file, example from May 2014).
   example 3: Calculate core field and its time derivatives for specified times
              and radii and plot maps
   example 4: Calculate static (i.e. small-scale crustal) magnetic field and
              plot maps (may take a few seconds)
   example 5: Calculate timeseries of the magnetic field at a ground
              observatory and plot
   example 6: Calculate external and associated induced fields described in SM
              and GSM reference systems and plot maps

3. "data/CHAOS-7.mat": mat-file containing CHAOS-7 model

4. "SW_OPER_MAGA_LR_1B_20180801T000000_20180801T235959_PT15S.cdf":
   cdf-file containing Swarm A magnetic field data from August 1, 2018.

5. directory called "html" containing the built documentation as
   html-files. Open "index.html" in your browser to access the main site.


Clemens Kloss (ancklo@space.dtu.dk)

EOF

# include changelog
cat >> $tempdir/readme.txt <(echo) CHANGELOG.rst

# build archive recursively in tmp directory
cd $tempdir/
zip $out -r *
cd -

# move archive to build
mv -i $tempdir/$out build/$out

# clean up
while true; do
    read -p "Do you wish to delete temporary files in '$tempdir' (y/n)?: " yn
    case $yn in
        [Yy]* ) rm -r $tempdir; rm example1_output.txt; break;;
        [Nn]* ) echo Exit.; exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

# upload to PyPI
# twine check dist/chaosmagpy-$version*
# twine upload dist/chaosmagpy-$version*
