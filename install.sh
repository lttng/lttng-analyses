#!/bin/sh

set -e

cd linuxautomaton
./setup.py install
cd ..

cd lttnganalyses
./setup.py install
cd ..

cd lttnganalysescli
./setup.py install
cd ..

echo "Install lttng-analyses-record in /usr/local/bin/ ? [Yn]"
read a
if test "$a" = 'y' -o "$a" = 'Y' -o "$a" = ''; then
	install lttng-analyses-record /usr/local/bin/lttng-analyses-record
fi
