import os
import shutil

from jinja2 import Environment, FileSystemLoader

from mdss.page import Page
from mdss.tree import SiteTree
from mdss.macro import MacroHandler


class SiteGenerator:
    """
    Handle generation of the website from source files
    """
    def __init__(self, content_dir, config):
        self.tree = SiteTree()
        self.content_dir = content_dir
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(self.config.templates_path)
        )

    @classmethod
    def split_path(cls, path):
        """
        Split a path by list into its components
        """
        head, tail = os.path.split(path)
        if head in ("", os.path.sep):
            return [tail]
        if tail:
            return cls.split_path(head) + [tail]
        return cls.split_path(head)

    def add_page(self, page_path):
        """
        Insert a page at the given source path (relative to content directory)
        into the site tree
        """
        full_path = os.path.join(self.content_dir, page_path)
        parts = SiteGenerator.split_path(page_path[:-3])

        # special case for home page
        if parts == ["index"]:
            self.tree.set_root_path(full_path)
        else:
            # remove trailing 'index'
            if parts[-1] == "index":
                parts.pop(-1)

            page_id = parts[-1]
            page = Page(page_id, src_path=full_path)

            self.tree.insert(page, location=parts[:-1])

    def gen_site(self, export_dir):
        """
        Find all content and write rendered pages
        """
        # export static files
        # go through template dirs backwards so that dirs earlier in the list
        # have priority when there are duplicate file names
        template_dirs = self.config.templates_path[::-1] + [self.content_dir]
        for d in template_dirs:
            static_files = self.walk_tree(d, self.config.static_filenames)
            for f in static_files:
                src = os.path.join(d, f)
                dest = os.path.join(export_dir, f)

                # make directories if dest dir doesn't not exist
                dest_dir = os.path.dirname(dest)
                if not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir)

                shutil.copyfile(src, dest)

        # build site tree
        for f in SiteGenerator.walk_tree(self.content_dir, ["md"]):
            self.add_page(f)

        self.render_all(export_dir)

    @classmethod
    def walk_tree(cls, start_dir, extensions):
        """
        Recursively walk `start_dir` and yield relative paths to all files
        whose extension is listed in `extensions`
        """
        for dirpath, _, filenames in os.walk(start_dir):
            for fname in filenames:
                ext = os.path.splitext(fname)[1][1:]
                if ext in extensions:
                    relpath = os.path.relpath(os.path.join(dirpath, fname),
                                              start=start_dir)
                    yield relpath

    def render_page(self, page):
        """
        Return a page HTML as a string
        """
        context = {}
        context.update(self.config.default_context)
        p_context, content = page.read_page_source()
        # modify context
        context.update(p_context)

        if "macros" in context:
            code_filename = "{}:<macro>".format(page.src_path)
            macro_handler = MacroHandler(context["macros"], code_filename)
            content = macro_handler.replace_all(content)

        context.update(content=Page.content_to_html(content))

        if "template" not in context:
            context["template"] = self.config.default_template

        if "title" not in context:
            context["title"] = page.title

        context["breadcrumbs"] = page.breadcrumbs
        context["children"] = page.child_listing()

        template = self.env.get_template(context.pop("template"))
        return template.render(**context)

    def render_all(self, export_dir):
        """
        Render each page in the tree and write it to a file
        """
        for page in self.tree:
            html = self.render_page(page)
            # remove leading / from path
            dest_path = os.path.join(export_dir, page.dest_path[1:],
                                     "index.html")

            # make sure containing directory exists
            par_dir = os.path.dirname(dest_path)
            if not os.path.isdir(par_dir):
                os.makedirs(par_dir)
            with open(dest_path, "w") as f:
                f.write(html)
