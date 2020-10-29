#
# Makefile - simple command-line tools
#
TARBALL=~/Downloads/src.tgz
DEBUG=--debug

clean:
	rm -rf Tmp __pycache__

run:
	python main.py ${DEBUG}

tarball:
	rm -f ${TARBALL}
	tar zcvf ${TARBALL} .

