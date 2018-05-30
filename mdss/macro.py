import re
from html.parser import HTMLParser


class HTMLAttributeParser(HTMLParser):
    """
    HTML parser that converts a HTML attribute list to a dictionary
    """
    def __init__(self):
        super().__init__()
        self.attrs = None

    def handle_starttag(self, _tag, attrs):
        self.attrs = attrs

    def __call__(self, attrs_string):
        self.feed("<temp {}></temp>".format(attrs_string))
        return dict(self.attrs)


class MacroHandler(object):

    # regex to match macro invocations in page content
    macro_regex = re.compile(
        r"<\?"                     # open tag: <?
        r"(?P<name>[a-zA-Z0-9_]+)"  # capture macro name
        r"(?: (?P<kwargs>[^>]+))?"     # kwargs (optional)
        r">"                        # close tag
        r"(?P<string>[^<]+)"           # capture 'inner html'
        r"<\?/(?P=name)>",          # close tag: </? followed by name
        flags=re.DOTALL
    )

    def __init__(self, code_str, filename):
        """
        Parse function definitions from `code_str`
        """
        self.macros = MacroHandler.parse_string(code_str, filename)
        self.kwargs_parser = HTMLAttributeParser()

    @classmethod
    def parse_string(cls, code_str, filename):
        """
        Execute a string containing python code and return a dict mapping
        name: func for each function defined in the top-level scope in the
        exec'd code.

        `filename` is used in tracebacks should the exec'd code raise any
        exceptions
        """
        code = compile(code_str, filename, "exec")
        exec_ctx = {}
        exec(code, globals(), exec_ctx)
        return {name: value for name, value in exec_ctx.items()
                if callable(value)}

    def replace_all(self, content_str):
        """
        Find macro invocations in the given string, evalute the macros, and
        return the string with relacements made
        """
        return self.macro_regex.sub(self.replace_match, content_str)

    def replace_match(self, match):
        """
        A function to be used with re.sub to replace a macro incovation with
        macro output
        """
        try:
            func = self.macros[match["name"]]
        except KeyError:
            raise KeyError("Macro '{}' not found".format(match["name"]))

        kwargs = {}
        if match["kwargs"] is not None:
            kwargs = self.kwargs_parser(match["kwargs"])

        return func(match["string"], **kwargs)
