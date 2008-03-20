
from utils import AbstractFunctionError
import utils

import sys
import traceback


__excepthook = sys.excepthook
def thunk_hook(type, value, trace):
    """
    This function is meant to replace excepthook and do some
    special work if the exception value has a __thunk_trace__
    field. In that case, it retrieves the field, which should
    contain a trace as returned by traceback.extract_stack,
    and prints it out on stderr.

    The normal excepthook is then called.
    """
    if hasattr(value, '__thunk_trace__'):
        trace2 = value.__thunk_trace__
        if trace2 is None:
            print>>sys.stderr, "Could not find where this Op was defined."
            print>>sys.stderr, " * You might have instantiated this Op directly instead of using a constructor."
            print>>sys.stderr, " * The Op you constructed might have been optimized. Try turning off optimizations."
        elif trace2:
            print>>sys.stderr, "Definition in: "
            for line in traceback.format_list(trace2):
                print>>sys.stderr, line,
    __excepthook(type, value, trace)
sys.excepthook = thunk_hook



class Linker:

    def __init__(self, env):
        self.env = env

    def make_thunk(self, inplace = False):
        """
        This function must return a triplet (function, input_results, output_results)
        where function is a thunk that operates on the returned results. If inplace
        is True, the input_results and output_results lists will be the same as the
        inputs and outputs of the graph provided to the Linker. Else, independent
        results will be returned.

        Example:
         e = x + y
         env = Env([x, y], [e])
         fn, (new_x, new_y), (new_e, ) = MyLinker(env).make_thunk(inplace)
         new_x.data = 1.0
         new_y.data = 2.0
         fn()
         print new_e.data # 3.0
         print e.data # 3.0 iff inplace == True (else unknown)
        """
        raise AbstractFunctionError()

    def make_function(self, inplace = False, unpack_single = True):
        """
        Returns a function that takes values corresponding to the inputs of the
        env used by this Linker and returns values corresponding the the outputs
        of that env. If inplace is True, the calculations will operate in the
        same storage the env uses, else independent storage will be allocated
        for the function.
        
        Example:
         e = x + y
         env = Env([x, y], [e])
         fn = MyLinker(env).make_function(inplace)
         print fn(1.0, 2.0) # 3.0
         print e.data # 3.0 iff inplace == True (else unknown)

        If unpack_single is True (default) and that the function has only one
        output, then that output will be returned. Else, a list or tuple of
        length 1 will be returned.
        """
        thunk, inputs, outputs = self.make_thunk(inplace)

        def execute(*args):
            def e_arity(takes, got):
                return 'Function call takes exactly %i %s (%i given)' \
                        % (takes, ['argument','arguments'][takes>1], got)
            if (len(args) != len(inputs)):
                raise TypeError(e_arity(len(inputs), len(args)))
            for arg, result in zip(args, inputs):
                result.data = arg
            thunk()
            if unpack_single:
                return utils.to_return_values([result.data for result in outputs])
            else:
                return [result.data for result in outputs]

        return execute




class PerformLinker(Linker):
    """
    Basic Linker subclass that calls the perform method on each op in
    the env in the order given by env.toposort.
    """

    def make_thunk(self, inplace = False):
        if inplace:
            env = self.env
        else:
            env = self.env.clone(True)
        order = env.toposort()
        thunks = [op.perform for op in order]
        def f():
            try:
                for thunk, op in zip(thunks, order):
                    thunk()
            except:
                exc_type, exc_value, exc_trace = sys.exc_info()
                try:
                    trace = op.trace
                except AttributeError:
                    trace = ()
                exc_value.__thunk_trace__ = trace
                exc_value.args = exc_value.args + (op, )
                raise exc_type, exc_value, exc_trace

        return f, env.inputs, env.outputs



### PROFILEPERFORMLINKER USES COMPLETELY OUTDATED INTERFACE - FIX ###

# class ProfilePerformLinker(Linker):

#     def compile(self):
#         order = self.env.toposort()
#         thunks = [op.perform for op in order]
#         self.n_calls = 0
#         self.n_thunks = 0
#         self.times = [0.0 for op in self.order]
#         def f():
#             for thunk in thunks:
#                 thunk()
#         self.thunk = f
#         self.order = order
#         self.thunks = thunks
    
#     def slow_call(self):
#         """Run the program, timing each thunk."""
#         for i, thunk in enumerate(self.thunks):
#             start_time = time.time()
#             thunk()
#             self.times[i] += time.time() - start_time
#             self.n_thunks += 1
#         self.n_calls += 1

#     def fast_call(self):
#         """Run the program, but only time the entire loop."""
#         start_time = time.time()
#         for thunk in self.thunks:
#             thunk()
#         self.n_thunks += len(self.thunks)
#         self.n_calls += 1
#         self.times[0] += time.time() - start_time

#     __call__ = slow_call

#     def dump(self, proportion=True):
#         """Print statistics accumulated so far."""
#         total_time = sum(self.times)
#         print self.n_calls, 'calls took', total_time, 'seconds to evaluate',
#         print self.n_thunks, 'thunks'

#         if 0:
#             print 'Proportion of CPU per op'
#             for op, t in zip(self.order, self.times):
#                 s_op = str(op).split()[0][1:]
#                 print "  %-35s %4.5f"% (s_op, t/total_time)

#         print 'Proportion of CPU per op class'
#         dct = {}
#         for op, t in zip(self.order, self.times):
#             s_op = str(op).split()[0][1:]
#             dct[s_op] = dct.get(s_op, 0.0) + t
#         for t, s_op in reversed(sorted([(t,op) for op, t in dct.items()])):
#             if proportion:
#                 print "  %-35s %4.5f"% (s_op, t/total_time)
#             else:
#                 print "  %-35s %4.5f"% (s_op, t)

