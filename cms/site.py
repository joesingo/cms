import os
import copy
import shutil

from jinja2 import Environment, FileSystemLoader
from flask import abort, send_from_directory
from werkzeug.exceptions import NotFound

from cms.page import Page


class Site(object):
    def __init__(self, config, app):
        self.content_dir = config["content_dir"]
        self.default_page_config = config["default_page_config"]
        self.static_dirs = config["static_dirs"]

        # jinja2 environment for loading templates
        self.env = Environment(loader=FileSystemLoader(config["template_dirs"]))

        self.home = self.generate_index()

        app.route("/<path:url>/")(self.handle_url)
        app.route("/", defaults={"url": ""})(self.handle_url)

    def handle_url(self, url):
        try:
            return self.view_page(url)
        except NotFound:
            return self.get_static_file(url)

    def generate_index(self, start_dir=None):
        """Recursively generate a page index from the given starting directory.
        Return the root page as a dictionary in the form:
            {"title": ..., "url": ..., children": [...]},
        where the children contains other pages represented in the same
        format"""
        start_dir = start_dir or self.content_dir

        root = {
            "title": Page.format_page_name(start_dir),
            "url": self.get_url_for(start_dir),
            "children": [],
            "path": os.path.join(start_dir, "index.md"),
            "index_page": True,
            "empty": True  # This is to keep track of whether this dict
                           # actually represents a page, i.e. if there is a .md
                           # file somewhere underneath it
        }

        # Home page is a special case where we need to set the title manually
        if start_dir == self.content_dir:
            root["title"] = "Home"

        dir_listing = os.listdir(start_dir)

        for entry in dir_listing:
            path = os.path.join(start_dir, entry)

            if os.path.isdir(path):

                # If this entry is a directory, then generate an index for this
                # directory
                sub_page = self.generate_index(start_dir=path)

                # If the index was not empty then this directory is an index
                # page, so add to listing
                if not sub_page["empty"]:
                    del sub_page["empty"]
                    root["children"].append(sub_page)
                    root["empty"] = False

            elif entry == "index.md":
                root["empty"] = False

            # If this page is a Markdown file then add to listing
            elif entry.endswith(".md"):
                root["children"].append({
                    "title": Page.format_page_name(path),
                    "url": self.get_url_for(path),
                    "children": [],
                    "path": path
                })
                root["empty"] = False

        # Sort child pages by order specified in page config (if present)
        if len(root["children"]) > 1:
            root_page = Page(root["path"], {}, content_dir=self.content_dir,
                             index_page=True, config_only=True)

            if "page_order" in root_page.config:
                ordered_pages = []

                for child_page_name in root_page.config["page_order"]:
                    for p in root["children"]:
                        if p["path"].endswith(child_page_name):
                            ordered_pages.append(p)

                # Put pages that were not specified in page_order at the end in
                # alphabetical order
                not_included = [p for p in root["children"]
                                if p not in ordered_pages]
                not_included.sort(key=lambda p: p["title"])

                root["children"] = ordered_pages + not_included

        return root

    def find_route_to_page(self, root, url):
        """Find a page by URL in the child pages of the root page provided.
        Return an route through the heirarchy of pages, e.g. for a page
        /articles/maths/calculus, the route would be:
            [/articles, /articles/maths, /articles/maths/calculus].
        Return False if the page is not found"""
        if root["url"] == url:
            return [root]

        for child in root["children"]:
            route = self.find_route_to_page(child, url)

            if route:
                return [root] + route

        return False

    def get_url_for(self, path):
        """Return the URL for the page at the specified path"""

        # Remove .md if present
        if path.endswith(".md"):
            path = path[:-3]

        # Return the part of the path after content directory
        url = path.split(self.content_dir, 1)[1].replace(os.sep, "/")
        return url or "/"

    def get_default_page_config(self):
        """Return the config that serves as a base for every page"""
        return copy.deepcopy(self.default_page_config)

    def view_page(self, url):
        """Render the specified page"""
        if not url.startswith("/"):
            url = "/" + url

        # Get the site index and find page by URL
        index = self.home["children"]
        route = self.find_route_to_page(self.home, url)  # Get breadcrumbs

        if route:
            default_config = self.get_default_page_config()

            # Set site index and header links
            default_config["site_index"] = index
            default_config["header_links"] = index
            default_config["breadcrumbs"] = route

            index_page = "index_page" in route[-1]
            if index_page:
                default_config["sub_index"] = route[-1]["children"]

            page = Page(route[-1]["path"], default_config,
                        content_dir=self.content_dir, index_page=index_page)
            return page.to_html(self.env)

        else:
            abort(404)

    def get_static_file(self, filename):
        """Serve a static file from one of the directories listed in
        self.static_dirs"""
        for static_dir in self.static_dirs:
            try:
                return send_from_directory(static_dir, filename)

            except NotFound as e:
                pass

        # If we reach here then file is not in any of the static dirs, so raise
        # NotFound exception
        raise e

    def export_static(self, export_dir):
        """Copy certain files from static dirs to the provided export directory
        """
        allowed_types = ["js", "css", "png", "jpg", "gif", "html"]

        for static_dir in self.static_dirs:
            for dirpath, _, filenames in os.walk(static_dir):
                for f in filenames:

                    # Check this file is of one of the allowed types to be
                    # copied
                    for ending in allowed_types:
                        if f.endswith("." + ending):
                            p = os.path.join(dirpath, f)

                            # Remove static dir part of path and leading slash
                            # if present
                            filename = p.replace(static_dir, "")
                            if filename.startswith(os.sep):
                                filename = filename[1:]

                            filename = os.path.join(export_dir, filename)
                            dirname = os.path.dirname(filename)

                            # Create directory if it does not exist
                            if not os.path.isdir(dirname):
                                os.makedirs(dirname)

                            # Copy the file
                            shutil.copy(p, filename)

    def export(self, export_dir, base_page=None):
        """Generate the HTML for all pages in the site and save them at the
        specified location"""
        if base_page is None:
            base_page = self.home

        # Get filename from base_page["path"]
        filename = base_page["path"].replace(self.content_dir, "")
        filename = filename.replace(".md", ".html")

        # Remove leading directory seperator if present
        if filename.startswith(os.sep):
            filename = filename[1:]

        filename = os.path.join(export_dir, filename)

        # If this page is not an index page, then put it in its own directory
        # so we do not have to add index.html
        if not filename.endswith(os.sep + "index.html"):
            # Remove .html
            filename = filename[:-len(".html")]
            filename = os.path.join(filename, "index.html")

        # Create the directory for this file if it does not exist
        dirname = os.path.dirname(filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        # Write the actual HTML for the page to the file
        with open(filename, "w") as f:
            f.write(self.view_page(base_page["url"]))

        for child in base_page["children"]:
            self.export(export_dir, base_page=child)
