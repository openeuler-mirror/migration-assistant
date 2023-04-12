########################################################################
#                  Build the cross-compile toolchain                   #
########################################################################
FROM fedora:33 AS builder

# Install packages required by osxtools
RUN dnf install -y \
    git \
    cmake \
    clang \
    llvm-devel \
    libxml2-devel \
    libuuid-devel \
    openssl-devel \
    bash \
    patch \
    libstdc++-static \
    make \
    xz \
    cpio \
    bzip2-devel

# Check out the osxcross repo
WORKDIR /tmp/osxcross-build
RUN git clone --depth 1 https://github.com/rokm/osxcross.git -b xcode_cmdline_tools .

# Extract MacOSX 11.x SDK from Command Line Tools for Xcode
COPY ./_sdks/osx/Command_Line_Tools_for_Xcode.dmg /tmp/tools.dmg
RUN ./tools/gen_sdk_package_tools_dmg.sh /tmp/tools.dmg && mv MacOSX11*.tar.* tarballs/

# Build the toolchain
ENV UNATTENDED=1
RUN ./build.sh


########################################################################
#                        The actual compiler VM                        #
########################################################################
FROM fedora:33

# Install packages
RUN dnf install -y python3 clang

# Copy cross-compilation toolchain from the builder container
COPY --from=builder /tmp/osxcross-build/target /opt/osxcross

# Set paths
ENV PATH=/opt/osxcross/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/osxcross/lib:$LD_LIBRARY_PATH

# Set macOS deployment target
ENV MACOSX_DEPLOYMENT_TARGET=10.11

# Build the bootloader
# The PyInstaller top source directory must be mounted as a volume to
# /pyinstaller when image is run, e.g.:
# docker run -v "/path/to/pyinstaller:/pyinstaller" <image_name>
WORKDIR /pyinstaller/bootloader
CMD CC=$(basename -a /opt/osxcross/bin/x86_64-*-clang) python3 ./waf configure all --clang
