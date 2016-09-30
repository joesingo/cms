import yaml
import markdown
import os.path
import os

class Page(object):
    """A class to represent a web page. A page is loaded from a file that
    contains a YAML config section followed by the content as a markdown"""

    # The default context used for rendering the template
    DEFAULT_CONTEXT = {
        "title": "",
        "content": "",
        "extra_head": "",
        "extra_body": "",
        "extra_style": "",
        "js_scripts": [],
        "stylesheets": [],
        "users": "anon",
        "template": "base.tmpl",
        "tags": []
    }

    # The delimiter between the YAML config section and markdown content
    START_OF_CONTENT = "\n---\n"

    def __init__(self, filename):
        """Construct a Page object from a given file"""

        with open(filename) as f:
            file_contents = f.read()

        # Split the contents of the file into the config and contents sections
        config_str, contents_str = file_contents.split(Page.START_OF_CONTENT, 1)
        config = yaml.load(config_str) or {}

        self.context = Page.DEFAULT_CONTEXT.copy()

        # Copy config to the context
        for key in config:
            if key in self.context:
                self.context[key] = config[key]

        # Set title if it has not been set
        if not self.context["title"]:
            self.context["title"] = Page.format_page_name(os.path.basename(filename))

        # Replace custom elements with their HTML counterparts
        for custom_el, replacement in config["custom_elements"].items():
            start_tag = "<" + custom_el + ">"
            end_tag = "</" + custom_el + ">"

            new_start_tag, new_end_tag = replacement.split("$", 1)

            contents_str = contents_str.replace(start_tag, new_start_tag)
            contents_str = contents_str.replace(end_tag, new_end_tag)

        # Convert markdown to HTML
        self.context["content"] = markdown.markdown(contents_str)


    def to_html(self, env, global_context={}):
        """Return the entire HTML document as a string for this page"""
        template = env.get_template(self.context["template"])

        context = self.context.copy()
        context.update(global_context)

        return template.render(**context)

    @classmethod
    def format_page_name(cls, name):
        """Given the filename for a page, return a nicely formatted version by
        replacing hyphens with spaces and capitalising the first letter"""
        if name.endswith(".md"):
            name = name[:-3]
        return name.replace("-", " ").capitalize()


class IndexPage(Page):
    def __init__(self, path, index):
        self.context = Page.DEFAULT_CONTEXT.copy()
        self.context["title"] = Page.format_page_name(os.path.basename(path))
        self.context["template"] = "base.tmpl"
        self.context["index"] = index
