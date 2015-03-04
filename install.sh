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

echo
echo -n "Install lttng-analyses-record and lttng-track-process in /usr/local/bin/ ? [Y/n] "
read -n 1 a
echo
if test "$a" = 'y' -o "$a" = 'Y' -o "$a" = ''; then
	install lttng-analyses-record /usr/local/bin/lttng-analyses-record
	install lttng-track-process /usr/local/bin/lttng-track-process
fi
