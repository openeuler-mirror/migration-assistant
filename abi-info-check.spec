%global debug_package %{nil}

Name:           abi-info-check
Version:        1.2
Release:        2
Summary:        A tool for checking backward binary compatibility of a C/C++ software library
License:        GPL2
URL:            https://github.com/deepinlinux
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  python3
BuildRequires:  python3-pip
BuildRequires:  python3-distro
BuildRequires:  python3-pandas
BuildRequires:  python3-dnf
BuildRequires:  python3-pexpect
BuildRequires:  python3-six
BuildRequires:  python3-beautifulsoup4
BuildRequires:  zlib-devel

Requires:  python3
Requires:  python3-pip
Requires:  python3-distro
Requires:  python3-pandas
Requires:  python3-dnf
Requires:  python3-pexpect
Requires:  python3-six
Requires:  python3-beautifulsoup4
Requires:  zlib-devel

Requires:       perl-Data-Dumper
Requires:       perl-Getopt-Long
Requires:       gcc
Requires:       gcc-c++
Requires:	make
Requires:       dnf-plugins-core
Requires:       elfutils
Requires:       graphviz
Requires:       ImageMagick


Obsoletes: 	abi-info-collect <= %{version}
Provides: 	abi-info-collect = %{version}

%description
A tool for checking backward binary compatibility of a C/C++ software library.

%prep
%autosetup

%build
pushd 3rdparty/pyinstaller-4.3
pushd bootloader
python3 ./waf all
popd
pip3 install -r requirements.txt
python3 setup.py install --user
popd

pushd abicheck
%make_build
popd

python3 setup.py build_manpage

%install
pushd abicheck
%make_install
popd

mkdir -p %{buildroot}%{_mandir}/man1/
install man/%{name}.1 %{buildroot}%{_mandir}/man1/

pushd  3rdparty/abi-compliance-checker-2.4
%make_install
popd

pushd 3rdparty/abi-dumper-2.1
%make_install
popd

%files
%license LICENSE
%{_bindir}/abi-dumper
%{_bindir}/abi-compliance-checker
%{_datadir}/abi-compliance-checker/

%{_bindir}/abi-info-check
%{_datadir}/abicheck/conf/
%{_mandir}/man1/abi-info-check.1*


%changelog
* Wed Jul 28 2021 guoqinglan <guoqinglan@uniontech.com> - 1.2-2
- Add library dependency graph tab
- Add package dependency graph tab
- Obsoletes abi-info-collect package

* Tue Jun 29 2021 guoqinglan <guoqinglan@uniontech.com> - 1.1-2
- Fix the problem that glibc cannot be analyzed correctly
