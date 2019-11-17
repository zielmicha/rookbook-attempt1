
cdef class _thread_state:
    cdef list ref_enabled
    cdef bint immutable_ctx
    cdef set record_lookups

cdef extern from "reactive_helpers.c":
   void* _thread_local_c

cdef _thread_state _get_thread_local()

cdef class _QueueItem:
   cdef int priority
   cdef object value

cdef class _OnceQueue:
   cdef list queue
   cdef set added

   cdef void add(self, int priority, object value, bint force)
   cdef object pop(self)

cdef class _BaseRef:
   cdef set _rdepends
   cdef set _depends
   cdef int _height
   cdef bint _enabled
   cdef object _value

   cdef void _enable_internal(self)
   cdef void _enable(self)
   cdef void _disable(self)
   cdef void __add_rdepend(self, _BaseRef val)
   cdef void __remove_rdepend(self, _BaseRef val)
   cdef void _set_depends(self, set new_depends)
   cdef void _record_read(self)
   cdef void _refresh(self)

cdef class ReactiveRef(_BaseRef):
   cdef object _exception
   cdef object _refresh_f

cdef class VarRef(_BaseRef):
   pass

cdef class Observer(_BaseRef):
   cdef object _callback
   cdef _BaseRef _ref
