import yaml

from mdss.exceptions import InvalidPageError


class Page(object):

    # string used to separate context and content
    SECTION_SEPARATOR = "---"

    def __init__(self, name, breadcrumbs, src_path, children=None):
        """
        name        - page title
        breadcrumbs - list of names of parent pages, up to but not including
                      this one
        src_path    - path on disk to content file
        children    - child pages
        """
        self.name = name
        self.breadcrumbs = breadcrumbs
        self.src_path = src_path
        self.children = children or []

    def add_child(self, new_page):
        """
        Insert a page beneath this one
        """
        self.children.append(new_page)

    @classmethod
    def parse_context(cls, context_str):
        """
        Parse the context section and return a dict
        """
        try:
            return yaml.load(context_str)
        except yaml.scanner.ScannerError:
            raise InvalidPageError("Context was not valid YAML")

    def read_page_source(self):
        """
        Read the page context and contents from the file and return
        (context, content), where `context` is a dictionary and `content` is a
        string
        """
        if not self.src_path:
            return {}, ""

        context_str = ""
        content = ""
        context_section = True

        with open(self.src_path) as f:
            for line in f.readlines():
                if line.strip() == self.SECTION_SEPARATOR:
                    context_section = False
                    continue
                if context_section:
                    context_str += line
                else:
                    content += line
        context = self.parse_context(context_str)
        return context, content

