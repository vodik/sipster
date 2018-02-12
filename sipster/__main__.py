from argparse import ArgumentParser
import asyncio
import importlib
import sys


async def launcher(function, args):
    useragents = yield function(args=args)
    await asyncio.gather(*useragents)


def main(argv):
    arg_parser = ArgumentParser(
        description="sipster Application server",
        prog="sipster"
    )
    arg_parser.add_argument(
        "entry_func",
        help=("Callable returning the `sipster.UserAgent` instance to "
              "run. Should be specified in the 'module:function' syntax."),
        metavar="entry-func"
    )

    args, extra_argv = arg_parser.parse_known_args(argv)

    mod_str, _, func_str = args.entry_func.partition(":")
    if not func_str or not mod_str:
        arg_parser.error(
            "'entry-func' not in 'module:function' syntax"
        )
    if mod_str.startswith("."):
        arg_parser.error("relative module names not supported")

    try:
        module = importlib.import_module(mod_str)
    except ImportError as ex:
        arg_parser.error("unable to import %s: %s" % (mod_str, ex))
    try:
        func = getattr(module, func_str)
    except AttributeError:
        arg_parser.error("module %r has no attribute %r" % (mod_str, func_str))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(launcher(func, extra_argv))
    loop.close()


if __name__ == "__main__":  # pragma: no branch
    main(sys.argv[1:])  # pragma: no cover
