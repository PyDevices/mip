#!/bin/bash

CP=/bin/cp

########################################################################################
# commit formatting

function ci_commit_formatting_run {
    git remote add upstream https://github.com/micropython/micropython-lib.git
    git fetch --depth=100 upstream master
    # If the common ancestor commit hasn't been found, fetch more.
    git merge-base upstream/master HEAD || git fetch --unshallow upstream master
    # For a PR, upstream/master..HEAD ends with a merge commit into master, exclude that one.
    tools/verifygitlog.py -v upstream/master..HEAD --no-merges
}

########################################################################################
# package tests

MICROPYTHON=/tmp/micropython/ports/unix/build-standard/micropython

function ci_package_tests_setup_micropython {
    git clone --depth 1 --branch v1.28.0 https://github.com/micropython/micropython.git /tmp/micropython  # pinned: .mpy ABI must not float with upstream master

    # build mpy-cross and micropython (use -O0 to speed up the build)
    make -C /tmp/micropython/mpy-cross -j CFLAGS_EXTRA=-O0
    make -C /tmp/micropython/ports/unix submodules
    make -C /tmp/micropython/ports/unix -j CFLAGS_EXTRA=-O0
}

function ci_package_tests_setup_lib {
    mkdir -p ~/.micropython/lib
    $CP micropython/ucontextlib/ucontextlib.py ~/.micropython/lib/
    $CP python-stdlib/fnmatch/fnmatch.py ~/.micropython/lib/
    $CP -r python-stdlib/hashlib-core/hashlib ~/.micropython/lib/
    $CP -r python-stdlib/hashlib-sha224/hashlib ~/.micropython/lib/
    $CP -r python-stdlib/hashlib-sha256/hashlib ~/.micropython/lib/
    $CP -r python-stdlib/hashlib-sha384/hashlib ~/.micropython/lib/
    $CP -r python-stdlib/hashlib-sha512/hashlib ~/.micropython/lib/
    $CP python-stdlib/shutil/shutil.py ~/.micropython/lib/
    $CP python-stdlib/tempfile/tempfile.py ~/.micropython/lib/
    $CP -r python-stdlib/unittest/unittest ~/.micropython/lib/
    $CP -r python-stdlib/unittest-discover/unittest ~/.micropython/lib/
    $CP unix-ffi/ffilib/ffilib.py ~/.micropython/lib/
    tree ~/.micropython
}

function ci_package_tests_run {
    for test in \
        micropython/drivers/storage/sdcard/sdtest.py \
        micropython/xmltok/test_xmltok.py \
        python-ecosys/requests/test_requests.py \
        python-stdlib/argparse/test_argparse.py \
        python-stdlib/base64/test_base64.py \
        python-stdlib/binascii/test_binascii.py \
        python-stdlib/collections-defaultdict/test_defaultdict.py \
        python-stdlib/functools/test_partial.py \
        python-stdlib/functools/test_reduce.py \
        python-stdlib/heapq/test_heapq.py \
        python-stdlib/hmac/test_hmac.py \
        python-stdlib/itertools/test_itertools.py \
        python-stdlib/operator/test_operator.py \
        python-stdlib/os-path/test_path.py \
        python-stdlib/pickle/test_pickle.py \
        python-stdlib/string/test_translate.py \
        python-stdlib/unittest/tests/exception.py \
        unix-ffi/gettext/test_gettext.py \
        unix-ffi/pwd/test_getpwnam.py \
        unix-ffi/re/test_re.py \
        unix-ffi/sqlite3/test_sqlite3.py \
        unix-ffi/sqlite3/test_sqlite3_2.py \
        unix-ffi/sqlite3/test_sqlite3_3.py \
        unix-ffi/time/test_strftime.py \
        ; do
        echo "Running test $test"
        (cd `dirname $test` && $MICROPYTHON `basename $test`)
        if [ $? -ne 0 ]; then
            false # make this function return an error code
            return
        fi
    done

    for path in \
        micropython/ucontextlib \
        python-stdlib/contextlib \
        python-stdlib/datetime \
        python-stdlib/fnmatch \
        python-stdlib/hashlib \
        python-stdlib/pathlib \
        python-stdlib/quopri \
        python-stdlib/shutil \
        python-stdlib/tempfile \
        python-stdlib/time \
        python-stdlib/unittest/tests \
        python-stdlib/unittest-discover/tests \
        ; do
        (cd $path && $MICROPYTHON -m unittest)
        if [ $? -ne 0 ]; then false; return; fi
    done

    (cd micropython/usb/usb-device && $MICROPYTHON -m tests.test_core_buffer)
    if [ $? -ne 0 ]; then false; return; fi

    (cd python-ecosys/cbor2 && $MICROPYTHON -m examples.cbor_test)
    if [ $? -ne 0 ]; then false; return; fi
}

########################################################################################
# build packages

function ci_build_packages_setup {
    git clone https://github.com/micropython/micropython.git /tmp/micropython

    # build mpy-cross (use -O0 to speed up the build)
    make -C /tmp/micropython/mpy-cross -j CFLAGS_EXTRA=-O0

    # check the required programs run
    /tmp/micropython/mpy-cross/build/mpy-cross --version
    python3 /tmp/micropython/tools/manifestfile.py --help
}

function ci_build_packages_check_manifest {
    for file in $(find -name manifest.py); do
        echo "##################################################"
        echo "# Testing $file"
        extra_args=
        if [[ "$file" =~ "/unix-ffi/" ]]; then
            extra_args="--unix-ffi"
        fi
        python3 /tmp/micropython/tools/manifestfile.py $extra_args --lib . --compile $file
    done
}

function ci_build_packages_compile_index {
    python3 tools/build.py --latest-only --micropython /tmp/micropython --output $PACKAGE_INDEX_PATH
}

function ci_build_packages_examples {
    for example in $(find -path \*example\*.py); do
        /tmp/micropython/mpy-cross/build/mpy-cross $example
    done
}
