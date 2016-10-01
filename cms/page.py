import yaml
import markdown
import os

class Page(object):
    """A class to represent a web page. A page is loaded from a file that
    contains a YAML config section followed by the content as a markdown"""

    # The delimiter between the YAML config section and markdown content
    START_OF_CONTENT = "\n---\n"

    def __init__(self, filename, config):
        """Construct a Page object from a given file"""
        self.config = config

        # Set a flag in the config if this is an index page, as the template
        # may want to do something different in this case
        if filename.endswith("index.md"):
            self.config["index_page"] = True

        try:
            with open(filename) as f:
                file_contents = f.read()

                # Split the contents of the file into the config and contents
                # sections
                config_str, contents_str = file_contents.split(Page.START_OF_CONTENT, 1)

        except IOError:
            # If file does not exist then this must be an index page
            config_str, contents_str = "", ""

        this_config = yaml.load(config_str) or {}

        # TODO: If base_config has been specified, load and merge the base
        # config here

        # Copy config to the context
        # TODO: Append to config rather than overwriting, e.g. for extra styles
        for key in this_config:
            self.config[key] = this_config[key]

        # Replace custom elements with their HTML counterparts
        if "custom_elements" in self.config:
            for custom_el, replacement in self.config["custom_elements"].items():
                start_tag = "<" + custom_el + ">"
                end_tag = "</" + custom_el + ">"

                new_start_tag, new_end_tag = replacement.split("$", 1)

                contents_str = contents_str.replace(start_tag, new_start_tag)
                contents_str = contents_str.replace(end_tag, new_end_tag)

        # Convert markdown to HTML
        self.config["content"] = markdown.markdown(contents_str)

    def to_html(self, env):
        """Return the entire HTML document as a string for this page"""
        template = env.get_template(self.config["template"])
        return template.render(self.config)

    @classmethod
    def format_page_name(cls, file):
        """Given the filename or path to a page, return a nicely formatted
        version by replacing hyphens with spaces and capitalising the first
        letter"""
        if file.endswith(".md"):
            file = file[:-3]

        if file.endswith("/index"):
            file = file[:-6]

        name = os.path.basename(file)
        return name.replace("-", " ").capitalize()
