__copyright__ = "Copyright (C) 2012 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""


from loopy.symbolic import (
        TaggedVariable, Reduction, LinearSubscript, TypeCast)
from loopy.diagnostic import LoopyError, LoopyWarning
from loopy.program import iterate_over_kernels_if_given_program

# {{{ imported user interface

from loopy.kernel.instruction import (
        MemoryOrdering, memory_ordering,
        MemoryScope, memory_scope,
        VarAtomicity, OrderedAtomic, AtomicInit, AtomicUpdate,
        InstructionBase,
        MultiAssignmentBase, Assignment, ExpressionInstruction,
        CallInstruction, CInstruction, NoOpInstruction, BarrierInstruction)
from loopy.kernel.data import (
        auto,
        KernelArgument,
        ValueArg, ArrayArg, GlobalArg, ConstantArg, ImageArg,
        AddressSpace, temp_var_scope,
        TemporaryVariable,
        SubstitutionRule,
        CallMangleInfo)
from loopy.kernel.function_interface import (
        CallableKernel, ScalarCallable)
from loopy.program import (
        CallablesTable, Program, make_program)

from loopy.kernel import LoopKernel, KernelState, kernel_state
from loopy.kernel.tools import (
        get_dot_dependency_graph,
        show_dependency_graph,
        add_dtypes,
        add_and_infer_dtypes,
        get_global_barrier_order,
        find_most_recent_global_barrier,
        get_subkernels,
        get_subkernel_to_insn_id_map)
from loopy.types import to_loopy_type
from loopy.kernel.creation import make_kernel, UniqueName, make_function
from loopy.library.reduction import register_reduction_parser

# {{{ import transforms

from loopy.version import VERSION, MOST_RECENT_LANGUAGE_VERSION

from loopy.transform.iname import (
        set_loop_priority, prioritize_loops, untag_inames,
        split_iname, chunk_iname, join_inames, tag_inames, duplicate_inames,
        rename_iname, remove_unused_inames,
        split_reduction_inward, split_reduction_outward,
        affine_map_inames, find_unused_axis_tag,
        make_reduction_inames_unique,
        has_schedulable_iname_nesting, get_iname_duplication_options,
        add_inames_to_insn, add_inames_for_unused_hw_axes)

from loopy.transform.instruction import (
        find_instructions, map_instructions,
        set_instruction_priority, add_dependency,
        remove_instructions,
        replace_instruction_ids,
        tag_instructions,
        add_nosync)

from loopy.transform.data import (
        add_prefetch, change_arg_to_image,
        tag_array_axes, tag_data_axes,
        set_array_axis_names, set_array_dim_names,
        remove_unused_arguments,
        alias_temporaries, set_argument_order,
        rename_argument,
        set_temporary_scope)

from loopy.transform.subst import (extract_subst,
        assignment_to_subst, expand_subst, find_rules_matching,
        find_one_rule_matching)

from loopy.transform.precompute import precompute
from loopy.transform.buffer import buffer_array
from loopy.transform.fusion import fuse_kernels

from loopy.transform.arithmetic import (
        fold_constants,
        collect_common_factors_on_increment)

from loopy.transform.padding import (
        split_array_axis, split_array_dim, split_arg_axis,
        find_padding_multiple,
        add_padding)

from loopy.transform.privatize import privatize_temporaries_with_inames
from loopy.transform.batch import to_batched, save_temporaries_in_loop
from loopy.transform.parameter import assume, fix_parameters
from loopy.transform.save import save_and_reload_temporaries
from loopy.transform.add_barrier import add_barrier
from loopy.transform.callable import (register_callable_kernel,
        register_function_id_to_in_knl_callable_mapper, inline_callable_kernel)
from loopy.transform.pack_and_unpack_args import pack_and_unpack_args_for_call

# }}}

from loopy.type_inference import infer_unknown_types
from loopy.preprocess import (preprocess_kernel, realize_reduction,
        preprocess_program)
from loopy.schedule import (
    generate_loop_schedules, get_one_scheduled_kernel, get_one_linearized_kernel)
from loopy.statistics import (ToCountMap, ToCountPolynomialMap, CountGranularity,
        stringify_stats_mapping, Op, MemAccess, get_op_map, get_mem_access_map,
        get_synchronization_map, gather_access_footprints,
        gather_access_footprint_bytes, Sync)
from loopy.codegen import (
        PreambleInfo,
        generate_code, generate_code_v2, generate_body)
from loopy.codegen.result import (
        GeneratedProgram,
        CodeGenerationResult)
from loopy.compiled import CompiledKernel
from loopy.options import Options
from loopy.auto_test import auto_test_vs_ref
from loopy.frontend.fortran import (c_preprocess, parse_transformed_fortran,
        parse_fortran)

from loopy.target import TargetBase, ASTBuilderBase
from loopy.target.c import CFamilyTarget, CTarget, ExecutableCTarget, generate_header
from loopy.target.cuda import CudaTarget
from loopy.target.opencl import OpenCLTarget
from loopy.target.pyopencl import PyOpenCLTarget, NvidiaPyOpenCLTarget
from loopy.target.ispc import ISPCTarget
from loopy.target.numba import NumbaTarget, NumbaCudaTarget

from loopy.tools import Optional
from loopy.tools import dump_as_python


__all__ = [
        "TaggedVariable", "Reduction", "LinearSubscript", "TypeCast",

        "auto",

        "LoopKernel",
        "KernelState", "kernel_state",  # lower case is deprecated

        "MemoryOrdering", "memory_ordering",  # lower case is deprecated
        "MemoryScope", "memory_scope",  # lower case is deprecated

        "VarAtomicity",
        "OrderedAtomic", "AtomicInit", "AtomicUpdate",
        "InstructionBase",
        "MultiAssignmentBase", "Assignment", "ExpressionInstruction",
        "CallInstruction", "CInstruction", "NoOpInstruction",
        "BarrierInstruction",

        "ScalarCallable", "CallableKernel",

        "CallablesTable", "Program", "make_program",

        "KernelArgument",
        "ValueArg", "ArrayArg", "GlobalArg", "ConstantArg", "ImageArg",
        "AddressSpace", "temp_var_scope",   # temp_var_scope is deprecated
        "TemporaryVariable",
        "SubstitutionRule",
        "CallMangleInfo",

        "make_kernel", "UniqueName", "make_function",

        "register_reduction_parser",

        "VERSION", "MOST_RECENT_LANGUAGE_VERSION",

        # {{{ transforms

        "set_loop_priority", "prioritize_loops", "untag_inames",
        "split_iname", "chunk_iname", "join_inames", "tag_inames",
        "duplicate_inames",
        "rename_iname", "remove_unused_inames",
        "split_reduction_inward", "split_reduction_outward",
        "affine_map_inames", "find_unused_axis_tag",
        "make_reduction_inames_unique",
        "has_schedulable_iname_nesting", "get_iname_duplication_options",
        "add_inames_to_insn", "add_inames_for_unused_hw_axes",

        "add_prefetch", "change_arg_to_image",
        "tag_array_axes", "tag_data_axes",
        "set_array_axis_names", "set_array_dim_names",
        "remove_unused_arguments",
        "alias_temporaries", "set_argument_order",
        "rename_argument", "set_temporary_scope",

        "find_instructions", "map_instructions",
        "set_instruction_priority", "add_dependency",
        "remove_instructions",
        "replace_instruction_ids",
        "tag_instructions",
        "add_nosync",

        "extract_subst", "expand_subst", "assignment_to_subst",
        "find_rules_matching", "find_one_rule_matching",

        "precompute", "buffer_array",
        "fuse_kernels",

        "fold_constants", "collect_common_factors_on_increment",

        "split_array_axis", "split_array_dim", "split_arg_axis",
        "find_padding_multiple", "add_padding",

        "privatize_temporaries_with_inames",

        "to_batched", "save_temporaries_in_loop",

        "assume", "fix_parameters",

        "save_and_reload_temporaries",

        "add_barrier",

        "dump_as_python",

        "register_callable_kernel",
        "register_function_id_to_in_knl_callable_mapper",
        "inline_callable_kernel",

        "pack_and_unpack_args_for_call",

        # }}}

        "get_dot_dependency_graph",
        "show_dependency_graph",
        "add_dtypes",
        "add_and_infer_dtypes",
        "get_global_barrier_order",
        "find_most_recent_global_barrier",
        "get_subkernels",
        "get_subkernel_to_insn_id_map",

        "to_loopy_type",

        "infer_unknown_types",

        "preprocess_kernel", "realize_reduction", "preprocess_program",
        "generate_loop_schedules",
        "get_one_scheduled_kernel", "get_one_linearized_kernel",
        "GeneratedProgram", "CodeGenerationResult",
        "PreambleInfo",
        "generate_code", "generate_code_v2", "generate_body",

        "ToCountMap", "ToCountPolynomialMap", "CountGranularity",
        "stringify_stats_mapping", "Op", "MemAccess", "get_op_map",
        "get_mem_access_map", "get_synchronization_map",
        "gather_access_footprints", "gather_access_footprint_bytes",
        "Sync",

        "CompiledKernel",

        "auto_test_vs_ref",

        "Options",

        "make_kernel",
        "c_preprocess", "parse_transformed_fortran", "parse_fortran",

        "LoopyError", "LoopyWarning",

        "TargetBase",
        "CFamilyTarget", "CTarget", "ExecutableCTarget", "generate_header",
        "CudaTarget", "OpenCLTarget",
        "PyOpenCLTarget", "NvidiaPyOpenCLTarget", "ISPCTarget",
        "NumbaTarget", "NumbaCudaTarget",
        "ASTBuilderBase",

        "Optional",

        # {{{ from this file

        "register_preamble_generators",
        "register_symbol_manglers",
        "register_function_manglers",

        "set_caching_enabled",
        "CacheMode",
        "make_copy_kernel",

        # }}}
        ]

# }}}


# {{{ set_options

@iterate_over_kernels_if_given_program
def set_options(kernel, *args, **kwargs):
    """Return a new kernel with the options given as keyword arguments, or from
    a string representation passed in as the first (and only) positional
    argument.

    See also :class:`Options`.
    """
    assert isinstance(kernel, LoopKernel)

    if args and kwargs:
        raise TypeError("cannot pass both positional and keyword arguments")

    new_opt = kernel.options.copy()

    if kwargs:
        from loopy.options import _apply_legacy_map, Options
        kwargs = _apply_legacy_map(Options._legacy_options_map, kwargs)

        for key, val in kwargs.items():
            if not hasattr(new_opt, key):
                raise ValueError("unknown option '%s'" % key)

            setattr(new_opt, key, val)
    else:
        if len(args) != 1:
            raise TypeError("exactly one positional argument is required if "
                    "no keyword args are given")
        arg, = args

        from loopy.options import make_options
        new_opt.update(make_options(arg))

    return kernel.copy(options=new_opt)

# }}}


# {{{ library registration

@iterate_over_kernels_if_given_program
def register_preamble_generators(kernel, preamble_generators):
    """
    :arg manglers: list of functions of signature ``(preamble_info)``
        generating tuples ``(sortable_str_identifier, code)``,
        where *preamble_info* is a :class:`PreambleInfo`.

    :returns: *kernel* with *manglers* registered
    """
    from loopy.tools import unpickles_equally

    new_pgens = kernel.preamble_generators[:]
    for pgen in preamble_generators:
        if pgen not in new_pgens:
            if not unpickles_equally(pgen):
                raise LoopyError("preamble generator '%s' does not "
                        "compare equally after being upickled "
                        "and would thus disrupt loopy's caches"
                        % pgen)

            new_pgens.insert(0, pgen)

    return kernel.copy(preamble_generators=new_pgens)


@iterate_over_kernels_if_given_program
def register_symbol_manglers(kernel, manglers):
    from loopy.tools import unpickles_equally

    new_manglers = kernel.symbol_manglers[:]
    for m in manglers:
        if m not in new_manglers:
            if not unpickles_equally(m):
                raise LoopyError("mangler '%s' does not "
                        "compare equally after being upickled "
                        "and would disrupt loopy's caches"
                        % m)

            new_manglers.insert(0, m)

    return kernel.copy(symbol_manglers=new_manglers)


@iterate_over_kernels_if_given_program
def register_function_manglers(kernel, manglers):
    """
    :arg manglers: list of functions of signature ``(kernel, name, arg_dtypes)``
        returning a :class:`loopy.CallMangleInfo`.
    :returns: *kernel* with *manglers* registered
    """
    from loopy.tools import unpickles_equally

    new_manglers = kernel.function_manglers[:]
    for m in manglers:
        if m not in new_manglers:
            if not unpickles_equally(m):
                raise LoopyError("mangler '%s' does not "
                        "compare equally after being upickled "
                        "and would disrupt loopy's caches"
                        % m)

            new_manglers.insert(0, m)

    return kernel.copy(function_manglers=new_manglers)

# }}}


# {{{ cache control

import os
CACHING_ENABLED = (
    "LOOPY_NO_CACHE" not in os.environ
    and
    "CG_NO_CACHE" not in os.environ)


def set_caching_enabled(flag):
    """Set whether :mod:`loopy` is allowed to use disk caching for its various
    code generation stages.
    """
    global CACHING_ENABLED
    CACHING_ENABLED = flag


class CacheMode:
    """A context manager for setting whether :mod:`loopy` is allowed to use
    disk caches.
    """

    def __init__(self, new_flag):
        self.new_flag = new_flag

    def __enter__(self):
        global CACHING_ENABLED
        self.previous_mode = CACHING_ENABLED
        CACHING_ENABLED = self.new_flag

    def __exit__(self, exc_type, exc_val, exc_tb):
        global CACHING_ENABLED
        CACHING_ENABLED = self.previous_mode
        del self.previous_mode

# }}}


# {{{ make copy kernel

def make_copy_kernel(new_dim_tags, old_dim_tags=None):
    """Returns a :class:`loopy.Program` that changes the data layout
    of a variable (called "input") to the new layout specified by
    *new_dim_tags* from the one specified by *old_dim_tags*.
    *old_dim_tags* defaults to an all-C layout of the same rank
    as the one given by *new_dim_tags*.
    """

    from loopy.kernel.array import (parse_array_dim_tags,
            SeparateArrayArrayDimTag, VectorArrayDimTag)
    new_dim_tags = parse_array_dim_tags(new_dim_tags, n_axes=None)

    rank = len(new_dim_tags)
    if old_dim_tags is None:
        old_dim_tags = parse_array_dim_tags(
                ",".join(rank * ["c"]), n_axes=None)
    elif isinstance(old_dim_tags, str):
        old_dim_tags = parse_array_dim_tags(
                old_dim_tags, n_axes=None)

    indices = ["i%d" % i for i in range(rank)]
    shape = ["n%d" % i for i in range(rank)]
    commad_indices = ", ".join(indices)
    bounds = " and ".join(
            f"0<={ind}<{shape_i}"
            for ind, shape_i in zip(indices, shape))

    set_str = "{{[{}]: {}}}".format(
                commad_indices,
                bounds
                )
    result = make_kernel(set_str,
            "output[%s] = input[%s]"
            % (commad_indices, commad_indices),
            lang_version=MOST_RECENT_LANGUAGE_VERSION)

    result = tag_array_axes(result, "input", old_dim_tags)
    result = tag_array_axes(result, "output", new_dim_tags)

    unrolled_tags = (SeparateArrayArrayDimTag, VectorArrayDimTag)
    for i in range(rank):
        if (isinstance(new_dim_tags[i], unrolled_tags)
                or isinstance(old_dim_tags[i], unrolled_tags)):
            result = tag_inames(result, {indices[i]: "unr"})

    return result

# }}}


# {{{ default target

_DEFAULT_TARGET = None


def set_default_target(target):
    # deliberately undocumented for now
    global _DEFAULT_TARGET
    _DEFAULT_TARGET = target


def _set_up_default_target():
    try:
        import pyopencl  # noqa
    except ImportError:
        from loopy.target.opencl import OpenCLTarget
        target = OpenCLTarget()
    else:
        from loopy.target.pyopencl import PyOpenCLTarget
        target = PyOpenCLTarget()

    set_default_target(target)


_set_up_default_target()

# }}}


# vim: foldmethod=marker
