%define major 0
%define libname %mklibname bcc %{major}
%define devname %mklibname bcc -d

# "fix" underlinking:
%global _disable_ld_no_undefined 1
# luajit is not available for some architectures
%bcond_without lua

Summary:	BPF Compiler Collection (BCC)
Name:		bcc
Version:	0.36.1
Release:	1
License:	ASL 2.0
Group:		Development/Kernel
Url:		https://github.com/iovisor/bcc
Source0:	%{url}/archive/v%{version}/%{name}-%{version}.tar.gz
Source1:	https://github.com/libbpf/blazesym/archive/refs/tags/capi-v0.1.7.tar.gz
Source2:	blazesym-vendor-%{name}%{version}.tar.xz
Patch:		bcc-libbpf-tools-makefile-remove-flags.patch	
BuildRequires:	bison
BuildRequires:	cmake
BuildRequires:	rust-packaging
BuildRequires:	git
%if %{with lua}
BuildRequires:	luajit
BuildRequires:	pkgconfig(luajit)
%endif
BuildRequires:	cmake(clang)
BuildRequires:	%{_lib}bpf-static-devel
BuildRequires:	cmake(llvm)
BuildRequires:	python%{pyver}dist(setuptools)
BuildRequires:	pkgconfig(libbpf)
BuildRequires:	pkgconfig(libelf)
BuildRequires:	pkgconfig(libfl)
BuildRequires:	pkgconfig(liblzma)
BuildRequires:	pkgconfig(libxml-2.0)
BuildRequires:	pkgconfig(libzstd)
BuildRequires:	pkgconfig(ncursesw)
BuildRequires:	pkgconfig(python3)
Requires:	%{name}-tools = %{EVRD}

%description
BCC is a toolkit for creating efficient kernel tracing and manipulation
programs, and includes several useful tools and examples. It makes use of
extended BPF (Berkeley Packet Filters), formally known as eBPF, a new feature
that was first added to Linux 3.15. BCC makes BPF programs easier to write,
with kernel instrumentation in C (and includes a C wrapper around LLVM), and
front-ends in Python and lua. It is suited for many tasks, including
performance analysis and network traffic control.

%package devel
Summary:        Shared library for BPF Compiler Collection (BCC)
Requires:       %{name}
Suggests:       elfutils-debuginfod-client
%description devel
The %{name}-devel package contains libraries and header files for developing
application that use BPF Compiler Collection (BCC).
#----
%package doc
Summary:        Examples for BPF Compiler Collection (BCC)
Recommends:     python-%{name}
Recommends:     %{name}-lua
BuildArch:      noarch
%description doc
Examples for BPF Compiler Collection (BCC)
#----
%package -n python-%{name}
Summary:        Python3 bindings for BPF Compiler Collection (BCC)
Requires:       %{name}
BuildArch:      noarch
%description -n python-%{name}
Python3 bindings for BPF Compiler Collection (BCC)
#----
%if %{with lua}
%package lua
Summary:        Standalone tool to run BCC tracers written in Lua
Requires:       %{name}
%description lua
Standalone tool to run BCC tracers written in Lua
%endif
#----
%package tools
Summary:        Command line tools for BPF Compiler Collection (BCC)
Requires:       %{name}
Requires:       python-%{name}
Requires:       python%{pyver}dist(netaddr)
%description tools
Command line tools for BPF Compiler Collection (BCC)
#----
%package -n libbpf-tools
Summary:        Command line libbpf tools for BPF Compiler Collection (BCC)
BuildRequires:  pkgconfig(libbpf)
BuildRequires:	%{_lib}bpf-static-devel
BuildRequires:  bpftool
%description -n libbpf-tools
Command line libbpf tools for BPF Compiler Collection (BCC)
	
%prep
%autosetup -p1
tar -xf %{S:1} -C libbpf-tools/blazesym
tar -xf %{S:2} -C libbpf-tools/blazesym

%build
# Install bps to /usr/bin
sed -i "s,share/bcc/introspection,bin," introspection/CMakeLists.txt
export LD_LIBRARY_PATH="%{_builddir}/usr/%{_lib}"
export PATH="%{_builddir}/usr/bin":$PATH

%cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo \
       -DREVISION_LAST=%{version} -DREVISION=%{version} -DPYTHON_CMD=python3 \
       -DCMAKE_USE_LIBBPF_PACKAGE:BOOL=TRUE -DENABLE_NO_PIE=OFF \
       %{?with_llvm_shared:-DENABLE_LLVM_SHARED=1}
%cmake build

cd ../..
pushd libbpf-tools
#move files to the correct directory
mv blazesym/blazesym-capi-v0.1.7/{.,}* blazesym
#run `cargo vendor` from within libbpf-tool/blazesym before building
cat >> blazesym/.cargo/config.toml << EOF
[source.crates-io]
replace-with = "vendored-sources"

[source."git+https://github.com/libbpf/vmlinux.h.git?rev=a9c092aa771310bf8b00b5018f7d40a1fdb6ec82"]
git = "https://github.com/libbpf/vmlinux.h.git"
rev = "a9c092aa771310bf8b00b5018f7d40a1fdb6ec82"
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "vendor"

EOF

#Create missing directories
#mkdir bashreadline bindsnoop biolatency biopattern biosnoop \
#	biostacks biotop bitesize cachestat capable \
#	cpudist cpufreq drsnoop execsnoop exitsnoop \
#	filelife filetop fsdist fsslower funclatency futexctn \
#	gethostlatency hardirqs javagc klockstat ksnoop \
#	llcstat mdflush memleak mountsnoop numamove offcputime \
#	runqslower sigsnoop slabratetop softirqs solisten \
#	statsnoop syncsnoop syscount tcptracer tcpconnect \
#	tcpconnlat tcplife tcppktlat tcprtt tcpstates \
#	tcpsynbl tcptop vfsstat wakeuptime
	
%make_build BPFTOOL=bpftool LIBBPF_OBJ=%{_libdir}/libbpf.a CFLAGS="%{optflags} -Wno-implicit-int-float-conversion" LDFLAGS="%{build_ldflags}"

popd
	
%install
%cmake install
# Fix python shebangs
find %{buildroot}%{_datadir}/%{name}/{tools,examples} -type f -exec \
  sed -i -e '1s=^#!/usr/bin/python\([0-9.]\+\)\?$=#!%{__python3}=' \
         -e '1s=^#!/usr/bin/env python\([0-9.]\+\)\?$=#!%{__python3}=' \
         -e '1s=^#!/usr/bin/env bcc-lua$=#!/usr/bin/bcc-lua=' {} \;

pushd libbpf-tools
# package libbpf-tools with 'bpf-' prefix (iovisor/bcc#3263)
%make_install DESTDIR=./tmp-install prefix=
(
    cd tmp-install/bin
    for file in *; do
        mv $file bpf-$file
    done
	
    # now fix the broken symlinks
    for file in `find . -type l`; do
        dest=$(readlink "$file")
        ln -s -f bpf-$dest $file
    done
)
popd
	
# Move man pages to the right location
mkdir -p %{buildroot}%{_mandir}
mv %{buildroot}%{_datadir}/%{name}/man/* %{buildroot}%{_mandir}/
	
# Avoid conflict with other manpages
# https://bugzilla.redhat.com/show_bug.cgi?id=1517408
for i in `find %{buildroot}%{_mandir} -name "*.gz"`; do
  tname=$(basename $i)
  rename $tname %{name}-$tname $i
done
	
mkdir -p %{buildroot}%{_docdir}/%{name}
mv %{buildroot}%{_datadir}/%{name}/examples %{buildroot}%{_docdir}/%{name}/
	
# Delete static libraries we don't want to ship
rm -f %{buildroot}%{_libdir}/lib%{name}*.a
	
# Delete old tools we don't want to ship
rm -rf %{buildroot}%{_datadir}/%{name}/tools/old/
	
# We cannot run the test suit since it requires root and it makes changes to
# the machine (e.g, IP address)
# %%check
	
mkdir -p %{buildroot}/%{_sbindir}
# We cannot use `install` because some of the tools are symlinks and `install`
# follows those. Since all the tools already have the correct permissions set,
# we just need to copy them to the right place while preserving those
cp -a libbpf-tools/tmp-install/bin/* %{buildroot}/%{_sbindir}/
	
%ldconfig_scriptlets
	
%files
%doc README.md
%license LICENSE.txt
%{_libdir}/lib%{name}.so.*
%{_libdir}/libbcc_bpf.so.*
	
%files devel
%{_libdir}/lib%{name}.so
%{_libdir}/libbcc_bpf.so
%{_libdir}/pkgconfig/lib%{name}.pc
%{_includedir}/%{name}/
	
%files -n python-%{name}
%{python3_sitelib}/%{name}*
	
%files doc
%dir %{_docdir}/%{name}
%doc %{_docdir}/%{name}/examples/
	
%files tools
%dir %{_datadir}/%{name}
%{_datadir}/%{name}/tools/
%{_datadir}/%{name}/introspection/
%{_mandir}/man8/*
	
%if %{with lua}	
%files lua	
%{_bindir}/bcc-lua
%endif	
	
%files -n libbpf-tools
%{_sbindir}/bpf-*
