from __future__ import annotations

import contextlib
import itertools
from collections.abc import Callable, Generator, Iterable, Iterator
from threading import Condition, Lock, Thread
from typing import Generic, TypeVar, overload

T = TypeVar("T")
U = TypeVar("U")


class MailboxShutDown(Exception):  # noqa: N818 (An exception, but not an error)
    """Exception to indicate that a Mailbox has been shut down.

    This will be raised if Mailbox.get() or Mailbox.put() is run on a
    mailbox after its .shutdown() method has been called, or if it is
    called while waiting.
    """

    def __init__(self, mailbox: Mailbox) -> None:
        #: The mailbox that was shut down
        self.mailbox = mailbox

    def __str__(self) -> str:
        return f"Mailbox shut down: {self.mailbox}"


class Mailbox(Generic[T]):
    """Thread-safe container to pass a single object at a time between threads.

    A Mailbox can be shut down to indicate that it is no longer
    available.  This can be used by a producer to indicate that no
    more items will be forthcoming, or by a consumer to indicate that
    it is no longer able to accept more objects.

    In Python 3.13, this has the same basic functionality as
    queue.Queue(1).  Prior to 3.13, there was no
    queue.Queue.shutdown() method.  The mechanisms for using mailboxes
    as iterables, or adding items from iterables, are also not part of
    queue.Queue in any version of Python.
    """

    def __init__(self) -> None:
        #: Lock to protect mailbox state
        self.lock = Lock()
        self._condition = Condition(lock=self.lock)
        #: Indicates whether an item is present in the mailbox
        self.has_item = False
        self._item: T | None = None
        #: Indicates whether the mailbox has been shut down
        self.is_shutdown = False

    def get(self) -> T:
        """Return and remove the item being held by the mailbox.

        If an item is not presently available, block until another
        thread calls .put().
        """
        with self._condition:
            while True:
                # We test to see if an item is present before testing if the queue is shut down.  This is so that a
                # non-immediate shutdown allows the mailbox to be drained.
                if self.has_item:
                    rv = self._item
                    self._item = None  # Don't hold an unnecessary reference
                    self.has_item = False
                    self._condition.notify_all()
                    return rv  # type:ignore[return-value]
                if self.is_shutdown:
                    raise MailboxShutDown(self)
                self._condition.wait()

    def get_many(self) -> Iterable[T]:
        """Yield items as they appear in the mailbox.

        The iterator exits the mailbox is shut down; MailboxShutDown
        is not raised into the caller.
        """
        return iter(self)

    def put(self, item: T) -> None:
        """Store an item in the mailbox.

        If an item is already in the mailbox, block until another
        thread calls .get().
        """
        with self._condition:
            while True:
                if self.is_shutdown:
                    raise MailboxShutDown(self)
                if not self.has_item:
                    self._item = item
                    self.has_item = True
                    self._condition.notify()
                    return
                self._condition.wait()

    def put_many(self, items: Iterable[T]) -> Iterator[T]:
        """Put the elements of iterable in the mailbox, one at a time.

        If the mailbox is shut down before all the elements can be put
        into it, a MailboxShutDown exception is _not_ raised.

        Returns an iterator containing any remaining items, including
        the one that was being processed when the mailbox was shut
        down.  The first item (if any) of this iterator can be
        immediately accessed with next; subsequent items defer to the
        input iterable, so may block.
        """
        iterator = iter(items)
        for item in iterator:
            # We put this try/except inside the for loop, to make sure we don't accidentally filter out an exception
            # that escaped the items iterator.
            try:
                self.put(item)
            except MailboxShutDown:
                return itertools.chain([item], iterator)
            # Remove references to the value once it's not needed.  This lets objects with advanced buffer semantics
            # reclaim the object's memory immediately, without waiting for the next iteration of the iterable.
            del item
        return iter([])

    def shutdown(self, *, immediate: bool = False) -> None:
        """Shut down the mailbox, marking it as unavailable for future use.

        Any callers currently blocked in .get or .put, or any future
        caller to those methods, will recieve a MailboxShutDown
        exception.  Callers using .get_many or iterating over the
        mailbox will see the iteration end.  Callers to .put_many will
        stop adding items.

        If immediate is False (the default), and an item is currently
        in the mailbox, it will be returned by the next call to
        .get(), and the one after that will raise MailboxShutDown.

        It is safe to call this method multiple times, including to
        promote a non-immediate shutdown to an immediate one.
        """
        with self._condition:
            # We don't actually need to check whether we've been called already.
            self.is_shutdown = True
            if immediate:
                self._item = None
                self.has_item = False
            self._condition.notify_all()

    def __iter__(self) -> Iterator[T]:
        """Yield items as they appear in the mailbox.

        The iterator exits when the mailbox is shut down;
        MailboxShutDown is not raised into the caller.
        """
        with contextlib.suppress(MailboxShutDown):
            while True:
                yield self.get()


class PipelineStage(Thread, Generic[T, U]):
    """A stage of a multi-threaded pipeline.

    The target function will be called once, and should yield one
    value for each element.

    If an in_mailbox is provided, the function will get an iterable of
    its successive elements.  If an out_mailbox is provided, it will
    be supplied with the successive outputs of the target function.

    If the either mailbox is shut down, the target function's loop
    will stop being called.  Both mailboxes will be shut down when the
    target function ends.

    Note to readers adapting this class to their own programs:

    This is designed for linear pipelines: it is not meant to support
    fan-in (multiple stages feeding one mailbox) or fan-out (one
    mailbox feeding multiple stages).  The shutdown semantics of these
    sorts of pipelines will depend heavily on what it's used for, and
    this demo only needs a simple pipeline.
    """

    # Source stage
    @overload
    def __init__(
        self,
        target: Callable[[], Generator[U]],
        *,
        out_mailbox: Mailbox[U],
        name: str | None = None,
    ) -> None: ...

    # Transformer stage
    @overload
    def __init__(
        self,
        target: Callable[[Iterable[T]], Generator[U]],
        *,
        in_mailbox: Mailbox[T],
        out_mailbox: Mailbox[U],
        name: str | None = None,
    ) -> None: ...

    # Sink stage
    @overload
    def __init__(
        self,
        target: Callable[[Iterable[T]], None],
        *,
        in_mailbox: Mailbox[T],
        name: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        target: Callable[[], Generator[U]] | Callable[[Iterable[T]], Generator[U]] | Callable[[Iterable[T]], None],
        *,
        in_mailbox: Mailbox[T] | None = None,
        out_mailbox: Mailbox[U] | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize the PipelineStage.

        Either :param:`in_mailbox` or :param:`out_mailbox` is
        required.  Otherwise, it would be a pipeline stage that can't
        connect to anything else.  (You can always use
        :class:`threading.Thread` directly if you need that behavior.)

        :param target: Function to run during the stage.  This will be
            called once, in a separate thread.  This should take one
            argument if :param:`in_mailbox` is provided, or no
            arguments otherwise.  If you want additional arguments
            (such as configuration), use :func:`functools.partial`.
        :param in_mailbox: An optional :class:`Mailbox` to provide
            inputs to the target function.  The target function will
            be called with one argument, an iterable that you can use
            in a for loop or similar construct, to get the successive
            values.
        :param out_mailbox: An optional :class:`Mailbox` to receive
            outputs from the target function.  If this is provided,
            the target function must be a generator (a function that
            uses ``yield`` instead of ``return``).  The successive
            outputs from the function will be placed in
            :param:`out_mailbox`.
        :param name: An optional name for debugging purposes; see
            :attr:`threading.Thread.name`.
        """
        if in_mailbox is None and out_mailbox is None:
            msg = "Cannot have a pipeline stage with neither inputs nor outputs"
            raise ValueError(msg)
        self.in_mailbox = in_mailbox
        self.out_mailbox = out_mailbox
        self.target = target
        #: The exception (if any) raised by the target function
        self.exc: Exception | None = None
        super().__init__(name=name, daemon=True)

    def run(self) -> None:
        """Execute the pipeline stage.

        This should not be run directly.  Instead, use the start()
        method (inherited from threading.Thread) to run this in a
        background thread.

        This will run the target function, managing input and output
        mailboxes.  When the stage completes, whether normally or with
        an error, the mailboxes will be shut down.
        """
        try:
            if self.out_mailbox is None:
                # This is a sink function, the easiest to deal with.  Since a mailbox is iterable, we can just pass it
                # to the target function.
                assert self.in_mailbox is not None  # noqa: S101
                self.target(self.in_mailbox)  # type:ignore[call-arg]
                return
            # This is a source or transformation function.
            out_iterable = self.target() if self.in_mailbox is None else self.target(self.in_mailbox)  # type:ignore[call-arg]
            if not isinstance(out_iterable, Generator):
                msg = (
                    "Pipeline target function was expected to be a generator; "
                    f"instead, it returned a {type(out_iterable)}."
                )
                raise TypeError(msg)  # noqa: TRY301
            # Once a generator is closed, the yield call (where they block when they send an object downstream) will
            # raise GeneratorExit.  That lets finally: blocks, with: exits, etc. run.  This happens automatically when
            # out_iterable is garbage-collected.  We still close it explicitly to so it gets the GeneratorExit, in case
            # something (like an exception object) is holding a reference to out_iterable.
            with contextlib.closing(out_iterable):
                self.out_mailbox.put_many(out_iterable)
        except Exception as e:
            # We store the exception, so that our caller can choose what to do about it after they call join.
            self.exc = e
            raise
        finally:
            if self.in_mailbox is not None:
                self.in_mailbox.shutdown()
            if self.out_mailbox is not None:
                self.out_mailbox.shutdown()

    def __str__(self) -> str:
        return f"<PipelineStage {self.name} running={self.is_alive()} thread_id={self.native_id}>"
