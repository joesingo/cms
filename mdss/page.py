from collections import namedtuple

import yaml
import markdown

from mdss.exceptions import InvalidPageError


PageInfo = namedtuple("PageInfo", ["id", "title"])


class Page(object):
    """
    Class representing a page in the website. This may be a page corresponding
    to a source file, or an index page generated for a directory that contains
    source files
    """

    # string used to separate context and content
    SECTION_SEPARATOR = "---"

    def __init__(self, p_id, src_path=None, children=None):
        """
        p_id        - page ID
        src_path    - path on disk to content file (optional)
        children    - child pages (optional)
        """
        self.id = p_id
        self.src_path = src_path
        self.children = children or []
        self.parent = None

        # title may be overriden later in page context -- set default for now
        self.title = self.get_default_title(self.id)

    def breadcrumbs(self):
        """
        Return a path from the home page to this page through this page's
        parents.

        Return a list of PageInfo objects:
          [<home info>, <parent info>, ... , <this info>]
        """
        p_info = PageInfo(self.id, self.title)
        if self.parent is None:
            return [p_info]
        return self.parent.breadcrumbs() + [p_info]

    @classmethod
    def get_default_title(cls, p_id):
        """
        Return a default title from an ID
        """
        return p_id.replace("-", " ").capitalize()

    def add_child(self, new_page):
        """
        Insert a page beneath this one
        """
        new_page.parent = self
        self.children.append(new_page)

    @classmethod
    def content_to_html(cls, md_str):
        """
        Convert page content and return HTML as a string
        """
        return markdown.markdown(md_str)

    def parse_context(self, context_str):
        """
        Parse the context section and return a dict
        """
        try:
            context = yaml.load(context_str) or {}
        except yaml.scanner.ScannerError:
            raise InvalidPageError("Context was not valid YAML")

        if "title" in context:
            self.title = context["title"]

        return context

    def read_page_source(self):
        """
        Read the page context and contents from the file and return
        (context, content), where `context` is a dictionary and `content` is a
        string
        """
        if not self.src_path:
            return {}, ""

        context_str = ""
        md_content = ""
        context_section = True

        with open(self.src_path) as f:
            for line in f.readlines():
                if line.strip() == self.SECTION_SEPARATOR:
                    context_section = False
                    continue
                if context_section:
                    context_str += line
                else:
                    md_content += line
        context = self.parse_context(context_str)
        content = self.content_to_html(md_content)
        return context, content
