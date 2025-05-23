from typing import Annotated, Any, Callable, Union

import tyro
from tyro.conf import Suppress

NestedCallableDict = dict[str, Callable[..., Any] | "NestedCallableDict"]


def subcommand_cli_from_nested_dict(
    subcommands: NestedCallableDict,
) -> Any:
    # Called to specify the subcommand corresponding to each value in the
    # dictionary.
    def _make_constructor(v):
        return (
            # Call the function directly.
            v
            if isinstance(v, Callable)
            # If a dictionary: construct a struct type with one
            # field, which is a union representing the next level of
            # subcommands.
            else tuple[
                Annotated[
                    _make_recursive_union(v),
                    tyro.conf.arg(name=""),
                ]
            ]
        )

    def _make_recursive_union(subcommands: NestedCallableDict) -> type:
        return Union[  # type: ignore
            tuple(
                [
                    Annotated[
                        # The constructor function can return any object.
                        Any,
                        # We'll instantiate this object by invoking a subcommand with
                        # a custom constructor.
                        tyro.conf.subcommand(
                            name=k,
                            constructor=_make_constructor(v),
                        ),
                    ]
                    for k, v in subcommands.items()
                ]
                # Union types need at least two types. To support the case
                # where we only pass one subcommand in, we'll pad with `None`
                # but suppress it.
                + [Annotated[None, Suppress]]
            )
        ]

    # We need to form a union type, which requires at least two elements.
    return tyro.cli(
        _make_recursive_union(subcommands),
    )
