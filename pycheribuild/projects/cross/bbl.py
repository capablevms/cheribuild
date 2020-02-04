#
# Copyright (c) 2018 James Clarke
# All rights reserved.
#
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory under DARPA/AFRL contract FA8750-10-C-0237
# ("CTSRD"), as part of the DARPA CRASH research programme.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

from .cheribsd import *
from .crosscompileproject import CrossCompileAutotoolsProject
from .gdb import BuildGDB
from ..project import *


# Using GCC not Clang, so can't use CrossCompileAutotoolsProject
class BuildBBLBase(CrossCompileAutotoolsProject):
    doNotAddToTargets = True
    repository = GitRepository("https://github.com/CTSRD-CHERI/riscv-pk",
        force_branch=True, default_branch="cheri",  # Compilation fixes for clang
        per_target_branches={
            CompilationTargets.CHERIBSD_RISCV_PURECAP: TargetBranchInfo("cheri_purecap", "bbl-cheribsd-purecap")
            },
        old_urls=[b"https://github.com/jrtc27/riscv-pk.git"])
    make_kind = MakeCommandKind.GnuMake
    _always_add_suffixed_targets = True
    is_sdk_target = False
    freebsd_class = None
    cross_install_dir = DefaultInstallDir.ROOTFS

    @classmethod
    def dependencies(cls, config: CheriConfig):
        xtarget = cls.get_crosscompile_target(config)
        # We need GNU objcopy which is installed by gdb-native
        result = [cls.freebsd_class.get_class_for_target(xtarget).target, "gdb-native"]
        return result

    def __init__(self, config: CheriConfig):
        super().__init__(config)
        self.COMMON_LDFLAGS.extend(["-nostartfiles", "-nostdlib", "-static"])
        self.COMMON_FLAGS.append("-nostdlib")

    def configure(self, **kwargs):
        kernel_path = self.freebsd_class.get_installed_kernel_path(self, cross_target=self.crosscompile_target)
        if self.crosscompile_target.is_cheri_purecap(valid_cpu_archs=[CPUArchitecture.RISCV64]):
            self.configureArgs.append("--with-abi=l64pc128")
        else:
            self.configureArgs.append("--with-abi=lp64")

        if self.target_info.is_cheribsd:
            # Enable CHERI extensions
            self.configureArgs.append("--with-arch=rv64imafdcxcheri")
        else:
            self.configureArgs.append("--with-arch=rv64imafdc")
        # BBL build uses weird objcopy flags and therefore requires
        self.add_configure_and_make_env_arg("OBJCOPY",
            BuildGDB.getInstallDir(self, cross_target=CompilationTargets.NATIVE) / "bin/gobjcopy")
        self.add_configure_and_make_env_arg("READELF", self.sdk_bindir / "llvm-readelf")
        self.add_configure_and_make_env_arg("RANLIB", self.sdk_bindir / "llvm-ranlib")
        self.add_configure_and_make_env_arg("AR", self.sdk_bindir / "llvm-ar")

        # Add the kernel as a payload:
        self.configureArgs.append("--with-payload=" + str(kernel_path))
        # Tag bits only in the 0xc region:
        self.configureArgs.append("--with-mem-start=0xc0000000")
        super().configure(**kwargs)

    def compile(self, cwd: Path = None):
        self.runMake("bbl")

    def get_installed_kernel_path(self):
        return self.real_install_root_dir / self.target_info.target_triple / "bin" / "bbl"

    def process(self):
        if not self.query_yes_no("Are you really sure you want to use BBL??? OpenSBI works much better with QEMU"):
            return
        super().process()


class BuildBBLFreeBSDRISCV(BuildBBLBase):
    project_name = "bbl-freebsd"
    target = "bbl-freebsd"
    supported_architectures = [CompilationTargets.FREEBSD_RISCV]
    freebsd_class = BuildFreeBSD


class BuildBBLFreeBSDWithDefaultOptionsRISCV(BuildBBLBase):
    project_name = "bbl-freebsd-with-default-options"
    target = "bbl-freebsd-with-default-options"
    supported_architectures = [CompilationTargets.FREEBSD_RISCV]
    freebsd_class = BuildFreeBSDWithDefaultOptions


class BuildBBLCheriBSDRISCV(BuildBBLBase):
    project_name = "bbl-cheribsd"
    target = "bbl-cheribsd"
    supported_architectures = [CompilationTargets.CHERIBSD_RISCV]
    freebsd_class = BuildCHERIBSD

