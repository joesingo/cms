import os

from jinja2 import Environment, FileSystemLoader
from flask import Flask, abort
import yaml

from page import Page, IndexPage

CONTENT_DIR = "content"
TEMPLATES_DIR = "cms/templates"
CONFIG_FILE = os.path.join(CONTENT_DIR, "config.yaml")

app = Flask(__name__)
# jinja2 environment for loading templates
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

# Load config file to get context that is to be passed to template for every
# page
with open(CONFIG_FILE) as f:
    global_context = yaml.load(f) or {}


@app.route("/<path:page>/")
@app.route("/", defaults={"page": ""})
def view_page(page):
    """Render the specified page"""

    page_path = CONTENT_DIR + os.sep + page
    suffixes = ["/index.md", ".md"]

    page_obj = None

    for suffix in suffixes:
        try:
            page_obj = Page(page_path + suffix)
            global_context["index"] = generate_index()

        except IOError:
            # If file was not found then do not give up yet, because we need to
            # try all suffixes first
            continue

        # except:
        #     # Any other exception means file was located but something else went
        #     # wrong, so abort 500
        #     abort(500)

        break

    # If this page is a directory but does not have an index.md, then show
    # index for this directory
    if page_obj is None and os.path.isdir(page_path):
        page_obj = IndexPage(page_path, generate_index(start_dir=page_path))

    # If the page has not been found abort 404
    if page_obj is None:
        abort(404)
    else:
        global_context["header_links"] = generate_index(depth=2)
        return page_obj.to_html(env, global_context)


def get_url_for(path):
    """Return the URL for the page at the specified path"""

    # Remove .md if present
    if path.endswith(".md"):
        path = path[:-3]

    # Split path by '/'s and go through each component, stopping after we reach
    # CONTENT_DIR
    split_path = path.split(os.sep)
    for i, k in enumerate(split_path):
        if k == CONTENT_DIR:
            i += 1
            break

    # Join together all components after CONTENT_DIR
    return "/" + "/".join(split_path[i:])


def generate_index(start_dir=CONTENT_DIR, depth=None):
    """Recursively generate a page index from the given starting directory.
    The listing is returned as an array of pages, where each page is represented
    in the form {"title": ..., "href": ..., children": [...]}, where the
    children array may contain other pages.

    The depth parameter specifies the number of levels to go down, or None to
    give the full index"""
    print("Generating index at {}, depth is {}".format(start_dir, depth))

    listing = []

    for entry in os.listdir(start_dir):
        path = os.path.join(start_dir, entry)
        if os.path.isdir(path):

            # Only recurse if depth > 1
            if depth is None or depth > 1:
                new_depth = None if depth is None else depth - 1
                children = generate_index(start_dir=path, depth=new_depth)
            else:
                children = []

            new_dir = {
                "title": Page.format_page_name(os.path.basename(path)),
                "href": get_url_for(path),
                "children": children
            }
            listing.append(new_dir)

        elif entry.endswith(".md") and entry != "index.md":
            listing.append({
                "title": Page.format_page_name(entry[:-3]),
                "href": get_url_for(path),
                "children": []
            })

    return listing